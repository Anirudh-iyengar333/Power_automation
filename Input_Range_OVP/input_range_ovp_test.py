#!/usr/bin/env python3
"""
Input Range and OVP Test

Characterises the complete power input behaviour of the DUT:
  1. Prompts the operator to connect DMM probes on the DUT output.
  2. Fixed Vin tests — PSU holds each configured voltage, DMM reads Vout,
     Pass/Fail result recorded.
  3. Sweep test — PSU ramps 0 -> Vmax -> 0 in configurable steps. DMM reads
     continuously. Two graphs are saved.
  4. Reports generated in a timestamped run folder:
       reports/  — CSV, JSON, and TXT summary
       plots/    — PSU and DMM waveform graphs

All settings are read from input_range_ovp_config.json (same folder).
That file is mandatory — the program exits if it is missing or has invalid JSON.

Instruments:
  - Keithley Power Supply (keithley_power_supply.KeithleyPowerSupply)
  - Keithley DMM6500     (keithley_dmm.KeithleyDMM6500)
"""

import sys
import csv
import json
import time
import logging
import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False

from instrument_control.keithley_power_supply import KeithleyPowerSupply
from instrument_control.keithley_dmm import KeithleyDMM6500


# ═════════════════════════════════════════════════════════════════════════════
# CONFIG LOADING — reads input_range_ovp_config.json once at startup
# ═════════════════════════════════════════════════════════════════════════════

_CONFIG_PATH = Path(__file__).parent / "input_range_ovp_config.json"


def _load_config(path: Path = _CONFIG_PATH) -> dict:
    """
    Load the JSON config file. Exits the program if the file is missing or
    contains invalid JSON — the config is mandatory, not optional.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        print(f"Loaded config from {path.name}")
        return cfg
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {path}")
        print("       This file is required. Ensure input_range_ovp_config.json is in the same folder.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Config file has invalid JSON: {e}")
        print("       Fix input_range_ovp_config.json before running the test.")
        sys.exit(1)


_CFG = _load_config()   # loaded once; every class/function below uses _CFG


# ═════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class FixedVinPoint:
    vin_v: float
    expected_vout_v: float
    vout_tolerance_v: float = 0.1


@dataclass
class FixedVinResult:
    vin_v: float
    vout_v: Optional[float]
    expected_vout_v: float
    vout_tolerance_v: float
    status: str   # "PASS", "FAIL", or "ERROR"

    def to_dict(self) -> dict:
        return {
            'vin_v': self.vin_v,
            'vout_v': self.vout_v,
            'expected_vout_v': self.expected_vout_v,
            'vout_tolerance_v': self.vout_tolerance_v,
            'status': self.status,
        }


@dataclass
class SweepSample:
    elapsed_s: float
    real_time: datetime.datetime
    psu_setpoint_v: float
    psu_measured_v: float
    psu_current_a: float
    dmm_v: float


@dataclass
class SweepResult:
    vin_range: str
    vout_v: float
    expected_vout_v: float
    status: str   # "PASS", "FAIL", "ERROR", or "NOT_RUN"
    samples: List[SweepSample] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'vin_range': self.vin_range,
            'vout_v': self.vout_v,
            'expected_vout_v': self.expected_vout_v,
            'status': self.status,
            'sample_count': len(self.samples),
        }


# ═════════════════════════════════════════════════════════════════════════════
# CONFIG BUILDER HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _build_fixed_vin_tests(cfg: dict) -> List[FixedVinPoint]:
    """Build the fixed Vin test point list from the JSON config."""
    raw = cfg.get("fixed_vin_tests", [])
    if not raw:
        print("ERROR: 'fixed_vin_tests' section missing from input_range_ovp_config.json")
        sys.exit(1)
    return [
        FixedVinPoint(
            vin_v=pt["vin_v"],
            expected_vout_v=pt["expected_vout_v"],
            vout_tolerance_v=pt.get("vout_tolerance_v", 0.1),
        )
        for pt in raw
        if "vin_v" in pt   # skip comment-only entries that lack a vin_v key
    ]


# ═════════════════════════════════════════════════════════════════════════════
# MAIN TEST CLASS
# ═════════════════════════════════════════════════════════════════════════════

class InputRangeOVPTest:
    """
    Runs the Input Range and OVP test sequence.

    All configuration is read from input_range_ovp_config.json via _CFG.

    Output directory structure (mirrors Load Transient convention):

        <output_dir>/run_YYYYMMDD_HHMMSS/
            input_range_ovp_test.log
            reports/
                input_range_ovp_results_TIMESTAMP.csv
                input_range_ovp_results_TIMESTAMP.json
                input_range_ovp_summary_TIMESTAMP.txt
            plots/
                psu_sweep_TIMESTAMP.png
                dmm_sweep_TIMESTAMP.png

    Usage:
        test   = InputRangeOVPTest()
        passed = test.run()
    """

    # Class-level attributes loaded from JSON — available before instantiation
    # (used by the runner to display config without constructing the test object)
    FIXED_VIN_TESTS = _build_fixed_vin_tests(_CFG)

    def __init__(self, output_dir: str = None):
        self._test_start_time = datetime.datetime.now()
        self._test_end_time: Optional[datetime.datetime] = None

        # ── Read sections from _CFG ───────────────────────────────────────────
        instr    = _CFG.get("instrument_addresses", {})
        settings = _CFG.get("instrument_settings", {})
        p        = _CFG.get("test_parameters", {})

        self._psu_address       = instr["psu"]
        self._dmm_address       = instr["dmm"]
        self._psu_channel       = settings.get("psu_channel", 1)
        self._psu_timeout_ms    = settings.get("psu_timeout_ms", 10000)
        self._dmm_timeout_ms    = settings.get("dmm_timeout_ms", 30000)

        self._psu_current_limit_a    = p["psu_current_limit_a"]
        self._psu_ovp_level_v        = p["psu_ovp_level_v"]
        self._fixed_vin_settle_s     = p["fixed_vin_settle_time_s"]
        self._sweep_start_v          = p["sweep_start_v"]
        self._sweep_max_v            = p["sweep_max_v"]
        self._sweep_step_v           = p["sweep_step_v"]
        self._step_dwell_s           = p["step_dwell_time_s"]
        self._dmm_read_interval_s    = p["dmm_read_interval_s"]
        self._step_settle_s          = p["step_settle_time_s"]
        self._sweep_vin_min_op_v     = p["sweep_vin_min_operating_v"]
        self._sweep_expected_vout_v  = p["sweep_expected_vout_v"]
        self._sweep_vout_tolerance_v = p["sweep_vout_tolerance_v"]
        self._dmm_nplc               = p["dmm_nplc"]

        # ── Resolve output directory ──────────────────────────────────────────
        if output_dir is None:
            out_cfg = _CFG.get("output_dir", {})
            output_dir = (
                out_cfg.get("path", "input_range_ovp_results")
                if isinstance(out_cfg, dict)
                else str(out_cfg)
            )

        timestamp = self._test_start_time.strftime("%Y%m%d_%H%M%S")
        self._timestamp = timestamp

        self._run_dir    = Path(output_dir) / f"run_{timestamp}"
        self._reports_dir = self._run_dir / "reports"
        self._plots_dir   = self._run_dir / "plots"

        try:
            for d in [self._run_dir, self._reports_dir, self._plots_dir]:
                d.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            fallback = Path(__file__).resolve().parent / "input_range_ovp_results"
            self._run_dir     = fallback / f"run_{timestamp}"
            self._reports_dir = self._run_dir / "reports"
            self._plots_dir   = self._run_dir / "plots"
            for d in [self._run_dir, self._reports_dir, self._plots_dir]:
                d.mkdir(parents=True, exist_ok=True)
            print(f"  WARNING: Could not write to '{output_dir}' ({e}). Falling back to: {fallback}")

        # ── Logging ───────────────────────────────────────────────────────────
        self._logger = logging.getLogger(self.__class__.__name__)
        log_path = self._run_dir / "input_range_ovp_test.log"
        if not self._logger.handlers:
            fh = logging.FileHandler(str(log_path), encoding="utf-8")
            fh.setFormatter(logging.Formatter(
                '%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
                datefmt='%H:%M:%S'
            ))
            self._logger.addHandler(fh)
            self._logger.setLevel(logging.DEBUG)
        self._logger.info(f"Run directory: {self._run_dir}")

        # ── Instrument handles ────────────────────────────────────────────────
        self._psu: Optional[KeithleyPowerSupply] = None
        self._dmm: Optional[KeithleyDMM6500] = None

    # ─────────────────────────────────────────────────────────────
    # Instrument helpers
    # ─────────────────────────────────────────────────────────────

    def _connect_instruments(self) -> bool:
        print("\n  Connecting instruments...")

        self._psu = KeithleyPowerSupply(self._psu_address, timeout_ms=self._psu_timeout_ms)
        if not self._psu.connect():
            print(f"  ERROR: Failed to connect to PSU at {self._psu_address}")
            return False
        print(f"  PSU connected  — model: {self._psu.model}")

        self._dmm = KeithleyDMM6500(self._dmm_address, timeout_ms=self._dmm_timeout_ms)
        if not self._dmm.connect():
            print(f"  ERROR: Failed to connect to DMM at {self._dmm_address}")
            return False
        print("  DMM connected")

        ok = self._psu.configure_channel(
            channel=self._psu_channel,
            voltage=0.0,
            current_limit=self._psu_current_limit_a,
            ovp_level=self._psu_ovp_level_v,
            enable_output=False
        )
        if not ok:
            print("  ERROR: PSU channel configuration failed")
            return False

        print(f"  PSU CH{self._psu_channel} configured: 0 V / {self._psu_current_limit_a} A / OVP {self._psu_ovp_level_v} V")
        return True

    def _disconnect_instruments(self):
        try:
            if self._psu and self._psu.is_connected:
                self._psu.disable_all_outputs()
                self._psu.disconnect()
        except Exception as e:
            self._logger.warning(f"PSU disconnect error: {e}")
        try:
            if self._dmm and self._dmm._is_connected:
                self._dmm.disconnect()
        except Exception as e:
            self._logger.warning(f"DMM disconnect error: {e}")

    def _psu_set_v(self, voltage: float):
        self._psu.set_voltage(self._psu_channel, voltage)

    def _psu_measure(self) -> Tuple[float, float]:
        v = self._psu.measure_voltage(self._psu_channel)
        i = self._psu.measure_current(self._psu_channel)
        return (v or 0.0), (i or 0.0)

    def _dmm_read_fast(self) -> float:
        val = self._dmm.measure_dc_voltage_fast()
        return val if val is not None else 0.0

    # ─────────────────────────────────────────────────────────────
    # Operator prompt
    # ─────────────────────────────────────────────────────────────

    def _prompt_probe_setup(self):
        print()
        print("  " + "=" * 58)
        print("  PROBE SETUP — ACTION REQUIRED")
        print("  " + "=" * 58)
        print()
        print("  Connect DMM probes to the DUT OUTPUT:")
        print("    + (HI) lead  ->  VOUT positive terminal")
        print("    - (LO) lead  ->  GND / VOUT return")
        print()
        print("  PSU leads should already be on DUT INPUT (VIN).")
        print()
        input("  Press ENTER when probes are connected and ready... ")
        print()

    # ─────────────────────────────────────────────────────────────
    # Phase 1 — Fixed Vin tests
    # ─────────────────────────────────────────────────────────────

    def run_fixed_vin_tests(self) -> List[FixedVinResult]:
        results: List[FixedVinResult] = []

        print()
        print("  -- Phase 1: Fixed Vin Tests ----------------------------------------")
        print(f"  {'VIN (V)':<12} {'VOUT (V)':<14} {'EXPECTED (V)':<16} {'STATUS'}")
        print("  " + "-" * 54)

        self._psu_set_v(0.0)
        self._psu.enable_channel_output(self._psu_channel)
        time.sleep(0.5)

        for point in self.FIXED_VIN_TESTS:
            try:
                print(f"  Setting Vin = {point.vin_v:.1f} V ...", end='', flush=True)
                self._psu_set_v(point.vin_v)
                time.sleep(self._fixed_vin_settle_s)

                vout = self._dmm_read_fast()
                deviation = abs(vout - point.expected_vout_v)
                status = "PASS" if deviation <= point.vout_tolerance_v else "FAIL"

                results.append(FixedVinResult(
                    vin_v=point.vin_v, vout_v=vout,
                    expected_vout_v=point.expected_vout_v,
                    vout_tolerance_v=point.vout_tolerance_v,
                    status=status
                ))
                print(f"\r  {point.vin_v:<12.1f} {vout:<14.4f} {point.expected_vout_v:<16.1f} {status}")

            except Exception as e:
                self._logger.error(f"Fixed Vin test error at {point.vin_v} V: {e}")
                results.append(FixedVinResult(
                    vin_v=point.vin_v, vout_v=None,
                    expected_vout_v=point.expected_vout_v,
                    vout_tolerance_v=point.vout_tolerance_v,
                    status="ERROR"
                ))
                print(f"\r  {point.vin_v:<12.1f} {'N/A':<14} {point.expected_vout_v:<16.1f} ERROR")

        self._psu_set_v(0.0)
        time.sleep(0.5)
        self._psu.disable_channel_output(self._psu_channel)
        print("  " + "-" * 54)
        print()
        return results

    # ─────────────────────────────────────────────────────────────
    # Phase 2 — Sweep test
    # ─────────────────────────────────────────────────────────────

    def _build_sweep_setpoints(self) -> List[float]:
        setpoints_up: List[float] = []
        v = self._sweep_start_v
        while v <= self._sweep_max_v + 1e-9:
            setpoints_up.append(round(v, 6))
            v += self._sweep_step_v
        if setpoints_up[-1] < self._sweep_max_v:
            setpoints_up.append(round(self._sweep_max_v, 6))
        setpoints_down = list(reversed(setpoints_up[:-1]))
        return setpoints_up + setpoints_down

    def run_sweep_test(self) -> SweepResult:
        setpoints = self._build_sweep_setpoints()
        total_steps = len(setpoints)

        print()
        print("  -- Phase 2: Vin Sweep ----------------------------------------------")
        print(f"  {self._sweep_start_v:.0f} V  ->  {self._sweep_max_v:.0f} V  ->  {self._sweep_start_v:.0f} V")
        print(f"  Step: {self._sweep_step_v:.1f} V  |  Dwell: {self._step_dwell_s:.1f} s  |  DMM interval: {self._dmm_read_interval_s:.2f} s")
        print(f"  Total steps: {total_steps}")
        print()

        samples: List[SweepSample] = []
        sweep_start = time.monotonic()

        self._psu_set_v(0.0)
        self._psu.enable_channel_output(self._psu_channel)
        time.sleep(0.5)

        for idx, setpoint in enumerate(setpoints):
            self._psu_set_v(setpoint)
            time.sleep(self._step_settle_s)
            psu_v, psu_i = self._psu_measure()

            dwell_end = time.monotonic() + self._step_dwell_s
            while time.monotonic() < dwell_end:
                elapsed = time.monotonic() - sweep_start
                rt = datetime.datetime.now()
                dmm_v = self._dmm_read_fast()
                samples.append(SweepSample(
                    elapsed_s=elapsed, real_time=rt,
                    psu_setpoint_v=setpoint, psu_measured_v=psu_v,
                    psu_current_a=psu_i, dmm_v=dmm_v
                ))
                print(
                    f"\r  [{idx+1:>3}/{total_steps}] "
                    f"Vin set={setpoint:.1f}V  "
                    f"Vin meas={psu_v:.2f}V  "
                    f"Vout={dmm_v:.4f}V  ",
                    end='', flush=True
                )
                time.sleep(self._dmm_read_interval_s)

        print()

        self._psu_set_v(0.0)
        time.sleep(0.5)
        self._psu.disable_channel_output(self._psu_channel)

        op_samples = [s for s in samples if s.psu_setpoint_v >= self._sweep_vin_min_op_v]
        if op_samples:
            vout_vals = [s.dmm_v for s in op_samples]
            avg_vout  = sum(vout_vals) / len(vout_vals)
            in_spec   = all(abs(v - self._sweep_expected_vout_v) <= self._sweep_vout_tolerance_v for v in vout_vals)
            status    = "PASS" if in_spec else "FAIL"
        else:
            avg_vout, status = 0.0, "ERROR"

        vin_range = f"{int(self._sweep_start_v)} - {int(self._sweep_max_v)}V"
        print(f"  Sweep: VIN={vin_range}  Vout_avg={avg_vout:.4f}V  {status}")

        return SweepResult(
            vin_range=vin_range,
            vout_v=round(avg_vout, 4),
            expected_vout_v=self._sweep_expected_vout_v,
            status=status,
            samples=samples
        )

    # ─────────────────────────────────────────────────────────────
    # Plotting  (saved to plots/ subdirectory)
    # ─────────────────────────────────────────────────────────────

    def _plot_sweep(self, sweep: SweepResult):
        if not _MATPLOTLIB_AVAILABLE:
            print("  WARNING: matplotlib not installed — skipping plots")
            return
        if not sweep.samples:
            return

        samp       = sweep.samples
        times      = [s.elapsed_s      for s in samp]
        setpoints  = [s.psu_setpoint_v for s in samp]
        psu_v      = [s.psu_measured_v for s in samp]
        psu_i      = [s.psu_current_a  for s in samp]
        dmm_v      = [s.dmm_v          for s in samp]
        real_times = [s.real_time      for s in samp]

        sweep_title = f"{int(self._sweep_start_v)}-{int(self._sweep_max_v)}V Vin"

        fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        fig1.suptitle(sweep_title, fontweight='bold')
        ax1.plot(times, setpoints, '--', color='steelblue', linewidth=1.2, label='Setpoint', alpha=0.8)
        ax1.plot(times, psu_v,     '-',  color='steelblue', linewidth=1.5, label='Measured')
        ax1.set_xlabel("Time (s)"); ax1.set_ylabel("Voltage (V)")
        ax1.set_title("CH1 Voltage - Live Execution Data")
        ax1.legend(); ax1.grid(True, alpha=0.3); ax1.set_ylim(bottom=-0.5)
        ax2.plot(times, psu_i, '-', color='steelblue', linewidth=1.5)
        ax2.set_xlabel("Time (s)"); ax2.set_ylabel("Current (A)")
        ax2.set_title("CH1 Current - Live Execution Data")
        ax2.grid(True, alpha=0.3); ax2.set_ylim(bottom=0)
        plt.tight_layout()
        p1 = self._plots_dir / f"psu_sweep_{self._timestamp}.png"
        fig1.savefig(str(p1), dpi=150, bbox_inches='tight')
        plt.close(fig1)
        print(f"  Saved: plots/{p1.name}")

        fig2, ax3 = plt.subplots(figsize=(10, 5))
        fig2.suptitle(sweep_title, fontweight='bold')
        ax3.plot_date(real_times, dmm_v, '-', color='steelblue', linewidth=1.5, xdate=True)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        fig2.autofmt_xdate()
        ax3.set_xlabel("Time"); ax3.set_ylabel("Measurement Value (V)")
        ax3.set_title(f"DMM Output - {sweep_title}")
        ax3.grid(True, alpha=0.3); ax3.set_ylim(bottom=-0.05)
        plt.tight_layout()
        p2 = self._plots_dir / f"dmm_sweep_{self._timestamp}.png"
        fig2.savefig(str(p2), dpi=150, bbox_inches='tight')
        plt.close(fig2)
        print(f"  Saved: plots/{p2.name}")

    # ─────────────────────────────────────────────────────────────
    # Report generation  (CSV + JSON + TXT in reports/ subdir)
    # ─────────────────────────────────────────────────────────────

    def _generate_reports(self, fixed: List[FixedVinResult], sweep: SweepResult) -> str:
        """
        Generate three report files in reports/:
          - input_range_ovp_results_TIMESTAMP.csv
          - input_range_ovp_results_TIMESTAMP.json
          - input_range_ovp_summary_TIMESTAMP.txt
        Returns the overall verdict string ("PASS" / "FAIL").
        """
        self._test_end_time = datetime.datetime.now()
        ts = self._timestamp

        all_pass = (
            all(r.status == "PASS" for r in fixed)
            and sweep.status == "PASS"
        )
        verdict = "PASS" if all_pass else "FAIL"

        # ── CSV ───────────────────────────────────────────────────────────────
        csv_path = self._reports_dir / f"input_range_ovp_results_{ts}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['Phase', 'Vin_V', 'Vout_V', 'Expected_V', 'Tolerance_V', 'Status'])
            for r in fixed:
                vout_str = f"{r.vout_v:.4f}" if r.vout_v is not None else "N/A"
                w.writerow(['FIXED', r.vin_v, vout_str, r.expected_vout_v, r.vout_tolerance_v, r.status])
            w.writerow(['SWEEP', sweep.vin_range, f"{sweep.vout_v:.4f}",
                        sweep.expected_vout_v, self._sweep_vout_tolerance_v, sweep.status])
        self._logger.info(f"CSV report saved: {csv_path}")
        print(f"  Saved: reports/{csv_path.name}")

        # ── JSON ──────────────────────────────────────────────────────────────
        json_path = self._reports_dir / f"input_range_ovp_results_{ts}.json"
        duration = (self._test_end_time - self._test_start_time).total_seconds()
        report_data = {
            'test_info': {
                'test_name': 'Input Range and OVP Test',
                'start_time': self._test_start_time.isoformat(),
                'end_time': self._test_end_time.isoformat(),
                'duration_seconds': round(duration, 1),
                'psu_address': self._psu_address,
                'dmm_address': self._dmm_address,
                'psu_channel': self._psu_channel,
                'current_limit_a': self._psu_current_limit_a,
                'ovp_level_v': self._psu_ovp_level_v,
            },
            'fixed_vin_results': [r.to_dict() for r in fixed],
            'sweep_result': sweep.to_dict(),
            'overall_result': verdict,
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        self._logger.info(f"JSON report saved: {json_path}")
        print(f"  Saved: reports/{json_path.name}")

        # ── TXT summary ───────────────────────────────────────────────────────
        txt_path = self._reports_dir / f"input_range_ovp_summary_{ts}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            _w = f.write
            _w("=" * 65 + "\n")
            _w("  INPUT RANGE AND OVP TEST — RESULTS SUMMARY\n")
            _w("=" * 65 + "\n")
            _w(f"  Date / Time    : {self._test_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            _w(f"  PSU Address    : {self._psu_address}\n")
            _w(f"  DMM Address    : {self._dmm_address}\n")
            _w(f"  PSU Channel    : CH{self._psu_channel}\n")
            _w(f"  Current Limit  : {self._psu_current_limit_a:.2f} A\n")
            _w(f"  OVP Level      : {self._psu_ovp_level_v:.1f} V\n")
            _w("=" * 65 + "\n\n")

            _w("  Results\n")
            _w("  " + "-" * 60 + "\n")
            _w(f"  {'PHASE':<10} {'VIN (V)':<14} {'VOUT (V)':<14} {'EXPECTED (V)':<16} {'STATUS'}\n")
            _w("  " + "-" * 60 + "\n")
            for r in fixed:
                vout_str = f"{r.vout_v:.4f}" if r.vout_v is not None else "N/A"
                _w(f"  {'FIXED':<10} {str(r.vin_v):<14} {vout_str:<14} {r.expected_vout_v:<16.1f} {r.status}\n")
            _w(f"  {'SWEEP':<10} {sweep.vin_range:<14} {sweep.vout_v:<14.4f} {sweep.expected_vout_v:<16.1f} {sweep.status}\n")
            _w("  " + "-" * 60 + "\n\n")

            _w("  Sweep Configuration\n")
            _w("  " + "-" * 60 + "\n")
            _w(f"  Start voltage      : {self._sweep_start_v:.1f} V\n")
            _w(f"  Max voltage        : {self._sweep_max_v:.1f} V\n")
            _w(f"  Step size          : {self._sweep_step_v:.1f} V\n")
            _w(f"  Step dwell time    : {self._step_dwell_s:.2f} s\n")
            _w(f"  DMM read interval  : {self._dmm_read_interval_s:.2f} s\n")
            _w(f"  Total DMM samples  : {len(sweep.samples)}\n\n")

            _w("=" * 65 + "\n")
            _w(f"  OVERALL RESULT : {verdict}\n")
            _w("=" * 65 + "\n")

        self._logger.info(f"Summary saved: {txt_path}")
        print(f"  Saved: reports/{txt_path.name}")

        return verdict

    # ─────────────────────────────────────────────────────────────
    # Top-level entry point
    # ─────────────────────────────────────────────────────────────

    def run(self) -> bool:
        """Execute the full test sequence. Returns True if all tests pass."""
        print()
        print(f"  Run directory : {self._run_dir.resolve()}")

        try:
            if not self._connect_instruments():
                return False

            self._prompt_probe_setup()

            fixed_results = self.run_fixed_vin_tests()
            sweep_result  = self.run_sweep_test()

            print()
            print("  Generating plots...")
            self._plot_sweep(sweep_result)

            print()
            print("  Writing reports...")
            verdict = self._generate_reports(fixed_results, sweep_result)

            print()
            print("  " + "=" * 50)
            print(f"  OVERALL RESULT : {verdict}")
            print("  " + "=" * 50)
            print(f"  Run folder     : {self._run_dir}")
            print()
            return verdict == "PASS"

        except KeyboardInterrupt:
            print("\n\n  Test interrupted by user.")
            return False

        except Exception as e:
            self._logger.error(f"Unhandled exception: {e}", exc_info=True)
            print(f"\n  ERROR: {e}")
            return False

        finally:
            print("  Disconnecting instruments...")
            self._disconnect_instruments()
