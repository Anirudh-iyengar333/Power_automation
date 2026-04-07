#!/usr/bin/env python3
"""
Steady-State Rail Verification and Ripple Test

Verifies that all selected power rails sit at correct DC voltage levels under
nominal input conditions, and that AC ripple on each rail does not exceed the
specified limit.

Test procedure per rail (scope CH1 used for every rail, one at a time):

  Phase 1 — DC Voltage:
    Probe:     DC coupling, 1:1, 20 MHz BW
    Timebase:  10 ms/div  (auto-trigger, free-run)
    Measure:   DC RMS full-screen  →  verify against expected voltage range

  Phase 2 — Ripple  (skipped for rails with no ripple spec):
    Operator:  Fit GND spring, position probe tip across LAST output capacitor
    Probe:     AC coupling, 1:1, 20 MHz BW
    Vertical:  50 mV/div
    Timebase:  100 ms/div
    Acquire:   Run → settle → STOP
    Measure:   Vpp  →  verify ≤ ripple limit

Reports saved in a timestamped run folder:
    <output_dir>/run_YYYYMMDD_HHMMSS/
        steady_state_ripple_test.log
        screenshots/
            <RAIL>_dc_voltage.png
            <RAIL>_ripple.png
        reports/
            steady_state_ripple_results_TIMESTAMP.csv
            steady_state_ripple_results_TIMESTAMP.json
            steady_state_ripple_summary_TIMESTAMP.txt

All settings are read from steady_state_ripple_config.json (same folder).
That file is mandatory — the program exits if it is missing or has invalid JSON.

Instruments:
    - Keysight DSOX6004A  (keysight_oscilloscope.KeysightDSOX6004A)
"""

import sys
import csv
import json
import time
import logging
import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from instrument_control.keysight_oscilloscope import KeysightDSOX6004A


# ═════════════════════════════════════════════════════════════════════════════
# CONFIG LOADING — reads steady_state_ripple_config.json once at startup
# ═════════════════════════════════════════════════════════════════════════════

_CONFIG_PATH = Path(__file__).parent / "steady_state_ripple_config.json"


def _load_config(path: Path = _CONFIG_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        print(f"Loaded config from {path.name}")
        return cfg
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {path}")
        print("       steady_state_ripple_config.json is required in the same folder.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Config file has invalid JSON: {e}")
        print("       Fix steady_state_ripple_config.json before running the test.")
        sys.exit(1)


_CFG = _load_config()


# ═════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class RailConfig:
    """Configuration for one power rail under test."""
    name:            str
    test_point:      str
    nominal_v:       float
    min_v:           float
    max_v:           float
    dc_v_scale:      float
    ripple_max_mvpp: Optional[float]   # None = no ripple spec for this rail

    @classmethod
    def from_dict(cls, d: dict) -> 'RailConfig':
        return cls(
            name=d['name'],
            test_point=d['test_point'],
            nominal_v=d['nominal_v'],
            min_v=d['min_v'],
            max_v=d['max_v'],
            dc_v_scale=d['dc_v_scale'],
            ripple_max_mvpp=d.get('ripple_max_mvpp'),
        )


@dataclass
class RailResult:
    """Measurement result for one power rail."""
    name:                 str
    test_point:           str
    nominal_v:            float
    min_v:                float
    max_v:                float
    measured_dc_v:        Optional[float]   # DC RMS FS in V; None on instrument error
    dc_status:            str               # "PASS" | "FAIL" | "ERROR"
    ripple_max_mvpp:      Optional[float]
    measured_ripple_mvpp: Optional[float]   # Vpp in mV; None if skipped or error
    ripple_status:        str               # "PASS" | "FAIL" | "ERROR" | "N/A"

    def to_dict(self) -> dict:
        return {
            'rail_name':            self.name,
            'test_point':           self.test_point,
            'nominal_v':            self.nominal_v,
            'expected_range':       f"{self.min_v:.2f}–{self.max_v:.2f}V",
            'measured_dc_v':        round(self.measured_dc_v, 4) if self.measured_dc_v is not None else None,
            'dc_status':            self.dc_status,
            'ripple_max_mvpp':      self.ripple_max_mvpp,
            'measured_ripple_mvpp': round(self.measured_ripple_mvpp, 1) if self.measured_ripple_mvpp is not None else None,
            'ripple_status':        self.ripple_status,
        }


# ═════════════════════════════════════════════════════════════════════════════
# MAIN TEST CLASS
# ═════════════════════════════════════════════════════════════════════════════

class SteadyStateRippleTest:
    """
    Runs the Steady-State Rail Verification and Ripple test.

    All configuration is read from steady_state_ripple_config.json via _CFG.

    Output directory structure:

        <output_dir>/run_YYYYMMDD_HHMMSS/
            steady_state_ripple_test.log
            screenshots/
                <RAIL>_dc_voltage.png
                <RAIL>_ripple.png
            reports/
                steady_state_ripple_results_TIMESTAMP.csv
                steady_state_ripple_results_TIMESTAMP.json
                steady_state_ripple_summary_TIMESTAMP.txt

    Usage:
        test    = SteadyStateRippleTest(rails=selected_rails, output_dir=output_dir)
        passed  = test.run()
    """

    SCOPE_CHANNEL = 1   # CH1 used for every measurement; CH2–4 disabled

    # All rails available from config — exposed so the runner can build the selector
    ALL_RAILS: List[RailConfig] = [
        RailConfig.from_dict(r) for r in _CFG.get("rails", [])
    ]

    def __init__(self, rails: List[RailConfig], output_dir: str = None):
        self._test_start_time = datetime.datetime.now()
        self._test_end_time: Optional[datetime.datetime] = None
        self._rails = rails

        # ── Read config sections ──────────────────────────────────────────────
        instr   = _CFG.get("instrument_addresses", {})
        scp_cfg = _CFG.get("scope_settings", {})

        self._scope_address   = instr["scope"]
        self._probe_atten     = scp_cfg.get("probe_attenuation", 1.0)
        self._bw_20mhz        = scp_cfg.get("bandwidth_limit_20mhz", True)
        self._scope_timeout   = scp_cfg.get("timeout_ms", 30000)

        self._dc_timebase     = scp_cfg.get("dc_timebase_s_per_div", 0.01)
        self._ripple_timebase = scp_cfg.get("ripple_timebase_s_per_div", 0.1)
        self._ripple_vscale   = scp_cfg.get("ripple_v_scale_v_per_div", 0.05)
        self._ripple_coupling = scp_cfg.get("ripple_coupling", "AC")
        self._ripple_settle   = scp_cfg.get("ripple_settle_periods", 3)

        # ── Resolve output directory ──────────────────────────────────────────
        if output_dir is None:
            out_cfg = _CFG.get("output_dir", {})
            output_dir = (
                out_cfg.get("path", "steady_state_ripple_results")
                if isinstance(out_cfg, dict)
                else str(out_cfg)
            )

        timestamp = self._test_start_time.strftime("%Y%m%d_%H%M%S")
        self._timestamp = timestamp

        self._run_dir         = Path(output_dir) / f"run_{timestamp}"
        self._screenshots_dir = self._run_dir / "screenshots"
        self._reports_dir     = self._run_dir / "reports"

        try:
            for d in [self._run_dir, self._screenshots_dir, self._reports_dir]:
                d.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            fallback = Path(__file__).resolve().parent / "steady_state_ripple_results"
            self._run_dir         = fallback / f"run_{timestamp}"
            self._screenshots_dir = self._run_dir / "screenshots"
            self._reports_dir     = self._run_dir / "reports"
            for d in [self._run_dir, self._screenshots_dir, self._reports_dir]:
                d.mkdir(parents=True, exist_ok=True)
            print(f"  WARNING: Could not write to '{output_dir}' ({e}). Falling back to: {fallback}")

        # ── Logging ───────────────────────────────────────────────────────────
        self._logger = logging.getLogger(self.__class__.__name__)
        log_path = self._run_dir / "steady_state_ripple_test.log"
        if not self._logger.handlers:
            fh = logging.FileHandler(str(log_path), encoding="utf-8")
            fh.setFormatter(logging.Formatter(
                '%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
                datefmt='%H:%M:%S'
            ))
            self._logger.addHandler(fh)
            self._logger.setLevel(logging.DEBUG)
        self._logger.info(f"Run directory: {self._run_dir}")

        # ── Instrument handle ─────────────────────────────────────────────────
        self._scope: Optional[KeysightDSOX6004A] = None
        self._results: List[RailResult] = []

    # ─────────────────────────────────────────────────────────────────────────
    # Instrument helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _connect_scope(self) -> bool:
        print("\n  Connecting oscilloscope...")
        self._scope = KeysightDSOX6004A(self._scope_address, timeout_ms=self._scope_timeout)
        if not self._scope.connect():
            print(f"  ERROR: Failed to connect to scope at {self._scope_address}")
            return False
        info = self._scope.get_instrument_info() or {}
        print(f"  Scope connected — {info.get('model', 'Keysight DSOX')}")
        return True

    def _disconnect_scope(self):
        try:
            if self._scope and self._scope.is_connected:
                self._scope.disconnect()
        except Exception as e:
            self._logger.warning(f"Scope disconnect error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Scope configuration helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _configure_for_dc(self, rail: RailConfig) -> bool:
        """
        Set CH1 for DC voltage measurement:
          DC coupling · 20 MHz BW · appropriate V/div · 10 ms/div · auto-trigger.

        The vertical offset is set to nominal_v so the signal sits at screen centre.
        CH2–4 are disabled for a clean single-channel display.
        """
        ch = self.SCOPE_CHANNEL

        for c in [2, 3, 4]:
            self._scope.disable_channel(c)

        ok = self._scope.configure_channel(
            channel=ch,
            vertical_scale=rail.dc_v_scale,
            vertical_offset=rail.nominal_v,   # centre signal on screen
            coupling="DC",
            probe_attenuation=self._probe_atten,
        )
        if not ok:
            return False

        self._scope.set_bandwidth_limit(ch, self._bw_20mhz)

        ok = self._scope.configure_timebase(
            time_scale=self._dc_timebase,
            time_offset=0.0,
        )
        if not ok:
            return False

        # Auto trigger — free-run; no edge needed for steady-state DC
        try:
            self._scope._scpi_wrapper.write(":TRIGger:SWEep AUTO")
            time.sleep(0.1)
        except Exception as e:
            self._logger.warning(f"Trigger sweep AUTO failed: {e}")

        return True

    def _configure_for_ripple(self) -> bool:
        """
        Reconfigure CH1 for ripple measurement:
          AC coupling · 20 MHz BW · 50 mV/div · 100 ms/div · auto-trigger.

        Offset set to 0 V — DC component is blocked by AC coupling.
        """
        ch = self.SCOPE_CHANNEL

        ok = self._scope.configure_channel(
            channel=ch,
            vertical_scale=self._ripple_vscale,
            vertical_offset=0.0,
            coupling=self._ripple_coupling,   # "AC"
            probe_attenuation=self._probe_atten,
        )
        if not ok:
            return False

        self._scope.set_bandwidth_limit(ch, self._bw_20mhz)

        ok = self._scope.configure_timebase(
            time_scale=self._ripple_timebase,
            time_offset=0.0,
        )
        if not ok:
            return False

        try:
            self._scope._scpi_wrapper.write(":TRIGger:SWEep AUTO")
            time.sleep(0.1)
        except Exception as e:
            self._logger.warning(f"Trigger sweep AUTO failed: {e}")

        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 1 — DC voltage
    # ─────────────────────────────────────────────────────────────────────────

    def _measure_dc_voltage(self, rail: RailConfig) -> RailResult:
        """
        Acquire a DC-coupled waveform and measure DC RMS FS.
        Returns a RailResult with DC fields populated; ripple fields left as N/A.
        """
        ch = self.SCOPE_CHANNEL

        print()
        print(f"  {'─' * 64}")
        print(f"  RAIL: {rail.name}  ({rail.test_point})")
        print(f"  {'─' * 64}")
        print(f"  Nominal: {rail.nominal_v:.3f} V    Expected: {rail.min_v:.2f} – {rail.max_v:.2f} V")
        print()
        print(f"  STEP 1 of 2 — DC Voltage")
        print(f"  Connect probe tip (DC mode, 1:1) to  {rail.test_point}  ({rail.name} rail).")
        print(f"  Attach ground clip to nearest board GND.")
        input("  Press ENTER when probe is connected... ")

        print("  Configuring scope: DC coupling, 20 MHz BW, auto-trigger...")
        if not self._configure_for_dc(rail):
            print("  ERROR: Scope DC configuration failed.")
            return RailResult(
                name=rail.name, test_point=rail.test_point,
                nominal_v=rail.nominal_v, min_v=rail.min_v, max_v=rail.max_v,
                measured_dc_v=None, dc_status="ERROR",
                ripple_max_mvpp=rail.ripple_max_mvpp,
                measured_ripple_mvpp=None, ripple_status="ERROR",
            )

        # Acquire: run, wait for several timebase windows, stop
        print("  Acquiring waveform (scope running)...")
        self._scope.run()
        time.sleep(1.5)    # ~15 × 10 ms windows — ensures a stable averaged reading
        self._scope.stop()
        time.sleep(0.3)

        # Measure DC RMS full-screen  (:MEASure:VRMS? DISPlay,DC,CHANnelN)
        measured_v = self._scope.measure_dc_rms_fs(ch)

        if measured_v is None:
            print("  ERROR: DC RMS measurement returned no value.")
            dc_status = "ERROR"
        else:
            in_range  = rail.min_v <= measured_v <= rail.max_v
            dc_status = "PASS" if in_range else "FAIL"
            mark  = "\033[32mPASS\033[0m" if in_range else "\033[31mFAIL\033[0m"
            print(f"  Measured DC RMS:  {measured_v:.4f} V   [{mark}]")
            if not in_range:
                print(f"  Expected range:   {rail.min_v:.2f} – {rail.max_v:.2f} V   ← OUT OF RANGE")

        # Screenshot — scope is already stopped, so freeze_acquisition=False
        shot_path = str(self._screenshots_dir / f"{rail.name}_dc_voltage.png")
        saved = self._scope.get_screenshot(shot_path, freeze_acquisition=False)
        if saved:
            print(f"  Saved: {Path(saved).name}")
        else:
            print("  WARNING: Screenshot could not be saved.")

        self._logger.info(
            f"{rail.name} DC: measured={measured_v}V  range=[{rail.min_v},{rail.max_v}]  status={dc_status}"
        )

        return RailResult(
            name=rail.name, test_point=rail.test_point,
            nominal_v=rail.nominal_v, min_v=rail.min_v, max_v=rail.max_v,
            measured_dc_v=measured_v, dc_status=dc_status,
            ripple_max_mvpp=rail.ripple_max_mvpp,
            measured_ripple_mvpp=None, ripple_status="N/A",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 2 — Ripple
    # ─────────────────────────────────────────────────────────────────────────

    def _measure_ripple(self, result: RailResult, rail: RailConfig) -> RailResult:
        """
        Reconfigure CH1 for AC-coupled ripple measurement.
        Updates and returns the RailResult with ripple fields populated.
        """
        ch        = self.SCOPE_CHANNEL
        settle_s  = self._ripple_settle * 10 * self._ripple_timebase   # e.g. 3×10×0.1 = 3 s

        print()
        print(f"  STEP 2 of 2 — Ripple  (limit: < {rail.ripple_max_mvpp:.0f} mVpp)")
        print()
        print("  For accurate ripple measurement — SHORT GROUND PATH IS ESSENTIAL:")
        print(f"    1. Remove the alligator-clip ground lead from the probe.")
        print(f"    2. Fit a GND SPRING (coaxial spring tip) onto the probe barrel.")
        print(f"    3. Connect the GND spring to a board ground point closest to the {rail.name} rail.")
        print(f"    4. Place the probe tip directly across the LAST OUTPUT CAPACITOR of the {rail.name} rail.")
        print("       (Long ground leads add inductance — they inflate ripple readings.)")
        input("  Press ENTER when GND spring and probe tip are positioned... ")

        print(f"  Configuring scope: AC coupling, {self._ripple_vscale * 1000:.0f} mV/div, "
              f"{self._ripple_timebase * 1000:.0f} ms/div...")
        if not self._configure_for_ripple():
            print("  ERROR: Scope ripple configuration failed.")
            result.ripple_status = "ERROR"
            return result

        # Run → settle → stop
        print(f"  Running scope — waiting {settle_s:.0f} s for waveform to settle...")
        self._scope.run()
        time.sleep(settle_s)
        self._scope.stop()
        time.sleep(0.3)
        print("  Scope stopped. Measuring Vpp...")

        # Vpp returned in volts; convert to mV
        vpp_v = self._scope.measure_peak_to_peak(ch)

        if vpp_v is None:
            print("  ERROR: Vpp measurement returned no value.")
            result.ripple_status = "ERROR"
        else:
            vpp_mv    = vpp_v * 1000.0
            in_spec   = vpp_mv <= rail.ripple_max_mvpp
            result.measured_ripple_mvpp = vpp_mv
            result.ripple_status        = "PASS" if in_spec else "FAIL"
            mark = "\033[32mPASS\033[0m" if in_spec else "\033[31mFAIL\033[0m"
            print(f"  Measured Ripple:  {vpp_mv:.1f} mVpp   [{mark}]")
            if not in_spec:
                print(f"  Limit:            {rail.ripple_max_mvpp:.0f} mVpp   ← EXCEEDS LIMIT")

        # Screenshot
        shot_path = str(self._screenshots_dir / f"{rail.name}_ripple.png")
        saved = self._scope.get_screenshot(shot_path, freeze_acquisition=False)
        if saved:
            print(f"  Saved: {Path(saved).name}")
        else:
            print("  WARNING: Screenshot could not be saved.")

        self._logger.info(
            f"{rail.name} Ripple: measured={result.measured_ripple_mvpp}mVpp  "
            f"limit={rail.ripple_max_mvpp}mVpp  status={result.ripple_status}"
        )

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Reporting
    # ─────────────────────────────────────────────────────────────────────────

    def _print_summary(self):
        print()
        print("=" * 82)
        print("  RESULTS SUMMARY")
        print("=" * 82)
        print(
            f"  {'Rail':<10}  {'TP':<12}  {'Nominal':>8}  {'Measured DC':>12}  "
            f"{'Range':>13}  {'DC':>5}  {'Ripple mVpp':>12}  {'Limit':>7}  {'Ripple':>6}"
        )
        print("  " + "-" * 78)

        overall_pass = True
        for r in self._results:
            dc_str  = f"{r.measured_dc_v:.4f} V" if r.measured_dc_v is not None else "  ERROR  "
            rng_str = f"{r.min_v:.2f}–{r.max_v:.2f}V"
            rip_str = f"{r.measured_ripple_mvpp:.1f}" if r.measured_ripple_mvpp is not None else "—"
            lim_str = f"<{r.ripple_max_mvpp:.0f}" if r.ripple_max_mvpp is not None else "N/A"

            dc_ok   = r.dc_status  == "PASS"
            rip_ok  = r.ripple_status in ("PASS", "N/A")
            if not (dc_ok and rip_ok):
                overall_pass = False

            dc_mark  = " OK " if dc_ok  else "FAIL"
            rip_mark = r.ripple_status if len(r.ripple_status) <= 4 else r.ripple_status[:4]

            print(
                f"  {r.name:<10}  {r.test_point:<12}  {r.nominal_v:>7.3f}V  "
                f"{dc_str:>12}  {rng_str:>13}  {dc_mark:>5}  "
                f"{rip_str:>12}  {lim_str:>7}  {rip_mark:>6}"
            )

        print()
        if overall_pass:
            print("  OVERALL: \033[32mPASS\033[0m — all rails within specification")
        else:
            print("  OVERALL: \033[31mFAIL\033[0m — one or more rails outside specification")
        print("=" * 82)

    def _save_reports(self):
        ts = self._timestamp
        fields = [
            'rail_name', 'test_point', 'nominal_v', 'expected_range',
            'measured_dc_v', 'dc_status',
            'ripple_max_mvpp', 'measured_ripple_mvpp', 'ripple_status',
        ]

        # CSV
        csv_path = self._reports_dir / f"steady_state_ripple_results_{ts}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for r in self._results:
                writer.writerow(r.to_dict())
        print(f"  CSV  : {csv_path}")

        # JSON
        json_path = self._reports_dir / f"steady_state_ripple_results_{ts}.json"
        payload = {
            'test_name':    'Steady-State Rail Verification and Ripple',
            'timestamp':    ts,
            'rails_tested': len(self._results),
            'overall':      'PASS' if all(
                r.dc_status == 'PASS' and r.ripple_status in ('PASS', 'N/A')
                for r in self._results
            ) else 'FAIL',
            'results': [r.to_dict() for r in self._results],
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        print(f"  JSON : {json_path}")

        # TXT summary
        txt_path = self._reports_dir / f"steady_state_ripple_summary_{ts}.txt"
        lines = [
            "STEADY-STATE RAIL VERIFICATION AND RIPPLE TEST",
            f"Run timestamp : {ts}",
            f"Rails tested  : {len(self._results)}",
            "",
            f"{'Rail':<10}  {'TP':<12}  {'Measured DC':>12}  {'Range':>13}  "
            f"{'DC':>5}  {'Ripple mVpp':>12}  {'Limit':>7}  {'Ripple':>6}",
            "-" * 76,
        ]
        for r in self._results:
            dc_str  = f"{r.measured_dc_v:.4f} V" if r.measured_dc_v is not None else "ERROR"
            rip_str = f"{r.measured_ripple_mvpp:.1f}" if r.measured_ripple_mvpp is not None else "—"
            lim_str = f"<{r.ripple_max_mvpp:.0f}" if r.ripple_max_mvpp is not None else "N/A"
            rng_str = f"{r.min_v:.2f}–{r.max_v:.2f}V"
            lines.append(
                f"{r.name:<10}  {r.test_point:<12}  {dc_str:>12}  {rng_str:>13}  "
                f"{r.dc_status:>5}  {rip_str:>12}  {lim_str:>7}  {r.ripple_status:>6}"
            )
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print(f"  TXT  : {txt_path}")

    # ─────────────────────────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────────────────────────

    def run(self) -> bool:
        if not self._rails:
            print("  No rails selected — nothing to test.")
            return True

        if not self._connect_scope():
            return False

        try:
            print(f"\n  Testing {len(self._rails)} rail(s): "
                  + "  ".join(r.name for r in self._rails))

            for i, rail in enumerate(self._rails, 1):
                print(f"\n  ══ Rail {i} / {len(self._rails)} "
                      f"{'═' * max(0, 52 - len(rail.name))} {rail.name} ══")

                # Phase 1: DC voltage
                result = self._measure_dc_voltage(rail)

                # Phase 2: Ripple (only for rails that have a ripple spec)
                if rail.ripple_max_mvpp is not None:
                    result = self._measure_ripple(result, rail)
                else:
                    print()
                    print(f"  STEP 2 of 2 — Ripple:  No ripple spec for {rail.name} — skipped.")

                self._results.append(result)

        finally:
            self._disconnect_scope()

        self._test_end_time = datetime.datetime.now()
        self._print_summary()

        print()
        print("  Saving reports...")
        self._save_reports()
        print()
        print(f"  Results folder: {self._run_dir}")
        print()

        overall = all(
            r.dc_status == "PASS" and r.ripple_status in ("PASS", "N/A")
            for r in self._results
        )
        return overall
