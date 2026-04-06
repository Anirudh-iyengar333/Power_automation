#!/usr/bin/env python3
"""
Power Sequencing Test

Verifies that all power rails on the DUT ramp in the correct order and reach
their nominal voltages within defined timing windows.

Test procedure (two scope capture configurations):

  Config 1  — Ch1: 1V0PL (TP8)  Ch2: 1V8 (TP6)  Ch3: 1V0PS (TP5)  Ch4: 1V35 (TP7)
              Confirm 3V6 with DMM.
  Config 2  — Ch1: 2V5   (TP9)  Ch2: 1V8 (TP6)  Ch3: 3V3   (TP10) Ch4: 1V35 (TP7)

For each configuration:
  1. PSU applies 5 V to DUT input (output currently OFF).
  2. Scope configured: 1 ms/div, trigger = rising edge on Ch1 at 20% of Ch1 nominal,
     single-shot, 20% pre-trigger.
  3. PSU output is turned ON → DUT rails begin to ramp → scope triggers.
  4. Waveform data downloaded from all four channels.
  5. 90% crossing time computed for each rail (T = 0 at trigger event).
  6. Cursors placed at T=0 and t_90 for each rail; screenshot saved.

Reports saved in a timestamped run folder:
    <output_dir>/run_YYYYMMDD_HHMMSS/
        power_sequencing_test.log
        screenshots/   — per-rail cursor screenshots + full display capture
        reports/
            power_sequencing_results_TIMESTAMP.csv
            power_sequencing_results_TIMESTAMP.json
            power_sequencing_summary_TIMESTAMP.txt

All settings are read from power_sequencing_config.json (same folder).
That file is mandatory — the program exits if it is missing or has invalid JSON.

Instruments:
    - Keithley Power Supply  (keithley_power_supply.KeithleyPowerSupply)
    - Keysight DSOX6004A     (keysight_oscilloscope.KeysightDSOX6004A)
"""

import sys
import csv
import json
import time
import shutil
import logging
import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from instrument_control.keithley_power_supply import KeithleyPowerSupply
from instrument_control.keysight_oscilloscope import KeysightDSOX6004A


# ═════════════════════════════════════════════════════════════════════════════
# CONFIG LOADING — reads power_sequencing_config.json once at startup
# ═════════════════════════════════════════════════════════════════════════════

_CONFIG_PATH = Path(__file__).parent / "power_sequencing_config.json"


def _load_config(path: Path = _CONFIG_PATH) -> dict:
    """
    Load the JSON config file.  Exits the program if the file is missing or
    contains invalid JSON — the config is mandatory, not optional.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        print(f"Loaded config from {path.name}")
        return cfg
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {path}")
        print("       This file is required. Ensure power_sequencing_config.json is in the same folder.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Config file has invalid JSON: {e}")
        print("       Fix power_sequencing_config.json before running the test.")
        sys.exit(1)


_CFG = _load_config()   # loaded once; every class/function below uses _CFG


# ═════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class ScopeChannelConfig:
    """Holds scope channel assignment and rail parameters for one capture config."""
    channel:      int
    name:         str
    test_point:   str
    nominal_v:    float
    v_scale:      float
    v_offset:     float

    @property
    def threshold_90pct_v(self) -> float:
        return round(0.9 * self.nominal_v, 4)


@dataclass
class RailTimingResult:
    """Result for one rail after the 90% timing measurement."""
    rail_name:       str
    test_point:      str
    nominal_v:       float
    threshold_90pct_v: float
    measured_time_ms: Optional[float]   # None if waveform analysis failed
    max_time_ms:     float
    status:          str   # "PASS", "FAIL", or "ERROR"
    config_label:    str   # "Config 1" or "Config 2"

    def to_dict(self) -> dict:
        return {
            'rail_name':          self.rail_name,
            'test_point':         self.test_point,
            'nominal_v':          self.nominal_v,
            'threshold_90pct_v':  self.threshold_90pct_v,
            'measured_time_ms':   self.measured_time_ms,
            'max_time_ms':        self.max_time_ms,
            'status':             self.status,
            'config_label':       self.config_label,
        }


# ═════════════════════════════════════════════════════════════════════════════
# CONFIG BUILDER HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _build_channel_configs(cfg_key: str) -> List[ScopeChannelConfig]:
    """Build the list of ScopeChannelConfig objects from a scope config section."""
    raw = _CFG.get(cfg_key, {}).get("channels", {})
    if not raw:
        print(f"ERROR: '{cfg_key}.channels' missing from power_sequencing_config.json")
        sys.exit(1)
    out = []
    for ch_str, ch_data in raw.items():
        out.append(ScopeChannelConfig(
            channel=int(ch_str),
            name=ch_data["name"],
            test_point=ch_data["test_point"],
            nominal_v=ch_data["nominal_v"],
            v_scale=ch_data["v_scale"],
            v_offset=ch_data["v_offset"],
        ))
    out.sort(key=lambda c: c.channel)
    return out


# ═════════════════════════════════════════════════════════════════════════════
# MAIN TEST CLASS
# ═════════════════════════════════════════════════════════════════════════════

class PowerSequencingTest:
    """
    Runs the Power Sequencing test sequence.

    All configuration is read from power_sequencing_config.json via _CFG.

    Output directory structure:

        <output_dir>/run_YYYYMMDD_HHMMSS/
            power_sequencing_test.log
            screenshots/
                config1_<RAIL>_cursor.png   ← per-rail cursor shots, Config 1
                config1_full.png            ← full four-channel waveform, Config 1
                config2_<RAIL>_cursor.png   ← per-rail cursor shots, Config 2
                config2_full.png            ← full four-channel waveform, Config 2
            reports/
                power_sequencing_results_TIMESTAMP.csv
                power_sequencing_results_TIMESTAMP.json
                power_sequencing_summary_TIMESTAMP.txt

    Usage:
        test   = PowerSequencingTest()
        passed = test.run()
    """

    # Class-level channel config lists — available before instantiation
    # (used by the runner to display a config summary)
    CONFIG1_CHANNELS = _build_channel_configs("scope_config_1")
    CONFIG2_CHANNELS = _build_channel_configs("scope_config_2")

    def __init__(self, output_dir: str = None):
        self._test_start_time = datetime.datetime.now()
        self._test_end_time: Optional[datetime.datetime] = None

        # ── Read sections from _CFG ───────────────────────────────────────────
        instr    = _CFG.get("instrument_addresses", {})
        psu_cfg  = _CFG.get("psu_settings", {})
        scp_cfg  = _CFG.get("scope_settings", {})

        self._psu_address     = instr["psu"]
        self._scope_address   = instr["scope"]

        self._psu_channel     = psu_cfg.get("channel", 1)
        self._vin_v           = psu_cfg.get("vin_v", 5.0)
        self._current_limit_a = psu_cfg.get("current_limit_a", 2.0)
        self._ovp_level_v     = psu_cfg.get("ovp_level_v", 6.0)
        self._psu_timeout_ms  = psu_cfg.get("timeout_ms", 10000)
        self._pre_poweroff_s  = psu_cfg.get("pre_poweroff_wait_s", 2.0)
        self._post_poweron_s  = psu_cfg.get("post_poweron_wait_s", 0.5)

        self._timebase_s        = scp_cfg.get("timebase_s_per_div", 1e-3)
        self._pretrigger_pct    = scp_cfg.get("pretrigger_pct", 20)
        self._trigger_slope     = scp_cfg.get("trigger_slope", "POS")
        self._sweep_mode        = scp_cfg.get("sweep_mode", "NORMal")
        self._coupling          = scp_cfg.get("coupling", "DC")
        self._probe_attenuation = scp_cfg.get("probe_attenuation", 10.0)
        self._bw_limit_20mhz   = scp_cfg.get("bandwidth_limit_20mhz", True)
        self._scope_timeout_ms  = scp_cfg.get("timeout_ms", 60000)
        self._trigger_wait_s    = scp_cfg.get("trigger_wait_s", 15.0)

        self._cfg1_trigger_ch = _CFG.get("scope_config_1", {}).get("trigger_channel", 1)
        self._cfg2_trigger_ch = _CFG.get("scope_config_2", {}).get("trigger_channel", 1)

        self._limits          = _CFG.get("rail_timing_limits", {})
        self._dmm_3v6_cfg     = _CFG.get("dmm_3v6_check", {})

        # Pre-trigger offset: positions trigger at pretrigger_pct% from left edge
        # offset = (total_window / 2) - pre_trigger_time
        total_window_s       = 10 * self._timebase_s
        pre_trigger_s        = (self._pretrigger_pct / 100.0) * total_window_s
        self._timebase_offset_s = (total_window_s / 2.0) - pre_trigger_s

        # ── Resolve output directory ──────────────────────────────────────────
        if output_dir is None:
            out_cfg = _CFG.get("output_dir", {})
            output_dir = (
                out_cfg.get("path", "power_sequencing_results")
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
            fallback = Path(__file__).resolve().parent / "power_sequencing_results"
            self._run_dir         = fallback / f"run_{timestamp}"
            self._screenshots_dir = self._run_dir / "screenshots"
            self._reports_dir     = self._run_dir / "reports"
            for d in [self._run_dir, self._screenshots_dir, self._reports_dir]:
                d.mkdir(parents=True, exist_ok=True)
            print(f"  WARNING: Could not write to '{output_dir}' ({e}). Falling back to: {fallback}")

        # ── Logging ───────────────────────────────────────────────────────────
        self._logger = logging.getLogger(self.__class__.__name__)
        log_path = self._run_dir / "power_sequencing_test.log"
        if not self._logger.handlers:
            fh = logging.FileHandler(str(log_path), encoding="utf-8")
            fh.setFormatter(logging.Formatter(
                '%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
                datefmt='%H:%M:%S'
            ))
            self._logger.addHandler(fh)
            self._logger.setLevel(logging.DEBUG)
        self._logger.info(f"Run directory: {self._run_dir}")

        # Override scope's built-in screenshot dir to our run folder
        self._scope_screenshot_dir = self._screenshots_dir

        # ── Instrument handles ────────────────────────────────────────────────
        self._psu:   Optional[KeithleyPowerSupply] = None
        self._scope: Optional[KeysightDSOX6004A]  = None

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

        self._scope = KeysightDSOX6004A(self._scope_address, timeout_ms=self._scope_timeout_ms)
        if not self._scope.connect():
            print(f"  ERROR: Failed to connect to scope at {self._scope_address}")
            return False
        print(f"  Scope connected — {self._scope.get_instrument_info().get('model', 'Keysight')}")

        # Point the scope's screenshot directory at our run folder
        self._scope.screenshot_dir = self._screenshots_dir

        # Configure PSU (output OFF, voltage set, limits in place)
        ok = self._psu.configure_channel(
            channel=self._psu_channel,
            voltage=self._vin_v,
            current_limit=self._current_limit_a,
            ovp_level=self._ovp_level_v,
            enable_output=False
        )
        if not ok:
            print("  ERROR: PSU channel configuration failed")
            return False
        print(f"  PSU CH{self._psu_channel} configured: {self._vin_v} V / {self._current_limit_a} A / OVP {self._ovp_level_v} V  (output OFF)")
        return True

    def _disconnect_instruments(self):
        try:
            if self._psu and self._psu.is_connected:
                self._psu.disable_all_outputs()
                self._psu.disconnect()
        except Exception as e:
            self._logger.warning(f"PSU disconnect error: {e}")
        try:
            if self._scope and self._scope.is_connected:
                self._scope.disconnect()
        except Exception as e:
            self._logger.warning(f"Scope disconnect error: {e}")

    # ─────────────────────────────────────────────────────────────
    # Scope configuration
    # ─────────────────────────────────────────────────────────────

    def _configure_scope(self, channels: List[ScopeChannelConfig], trigger_ch: int) -> bool:
        """
        Apply full scope setup for a capture configuration:
          - All four channels scaled and coupled
          - Timebase with 20% pre-trigger offset
          - Rising-edge trigger on trigger_ch at 20% of its nominal voltage
          - NORMal sweep mode (waits for real trigger event)
        """
        print()
        print("  Configuring scope...")

        # Timebase
        if not self._scope.configure_timebase(self._timebase_s, self._timebase_offset_s):
            print("  ERROR: Could not set scope timebase")
            return False
        print(f"  Timebase : {self._timebase_s * 1e3:.0f} ms/div  |  offset {self._timebase_offset_s * 1e3:.1f} ms  ({self._pretrigger_pct}% pre-trigger)")

        # Channels
        for ch in channels:
            ok = self._scope.configure_channel(
                channel=ch.channel,
                vertical_scale=ch.v_scale,
                vertical_offset=ch.v_offset,
                coupling=self._coupling,
                probe_attenuation=self._probe_attenuation
            )
            if not ok:
                print(f"  ERROR: Could not configure CH{ch.channel} ({ch.name})")
                return False

            # 20 MHz bandwidth limit — suppresses high-frequency noise on slow ramps
            self._scope.set_bandwidth_limit(ch.channel, self._bw_limit_20mhz)

            print(f"  CH{ch.channel} : {ch.name:<8} ({ch.test_point})  "
                  f"scale={ch.v_scale} V/div  offset={ch.v_offset} V  "
                  f"probe={int(self._probe_attenuation)}×  "
                  f"BW={'20 MHz' if self._bw_limit_20mhz else 'full'}")

        # Trigger channel nominal and threshold
        trig_ch_cfg = next((c for c in channels if c.channel == trigger_ch), channels[0])
        trigger_level = round(0.2 * trig_ch_cfg.nominal_v, 4)

        ok = self._scope.configure_trigger(
            channel=trigger_ch,
            trigger_level=trigger_level,
            trigger_slope=self._trigger_slope,
            sweep_mode=self._sweep_mode
        )
        if not ok:
            print(f"  ERROR: Could not configure trigger on CH{trigger_ch}")
            return False
        print(f"  Trigger  : CH{trigger_ch} ({trig_ch_cfg.name})  rising edge at {trigger_level} V  (20% of {trig_ch_cfg.nominal_v} V)")
        return True

    # ─────────────────────────────────────────────────────────────
    # Power-cycle and single-shot capture
    # ─────────────────────────────────────────────────────────────

    def _arm_and_capture(self) -> bool:
        """
        Power-cycle the DUT and capture one single-shot waveform:
          1. Ensure PSU output is OFF (DUT powered down).
          2. Wait for rails to collapse.
          3. Arm scope for single acquisition.
          4. Turn PSU output ON → DUT powers up → scope triggers on Ch1 rising edge.
          5. Wait for scope to reach STOP (acquisition complete).
        Returns True if scope triggered successfully within the timeout.
        """
        print()
        print("  -- Power-cycle and capture -----------------------------------------")

        # Step 1: PSU off
        print(f"  Turning PSU CH{self._psu_channel} output OFF (DUT power down)...")
        self._psu.disable_channel_output(self._psu_channel)
        time.sleep(self._pre_poweroff_s)

        # Step 2: Arm scope for single acquisition
        print("  Arming scope for single-shot acquisition...")
        if not self._scope.single():
            print("  ERROR: Could not arm scope for single acquisition")
            return False
        time.sleep(0.3)   # brief arm settle

        # Step 3: PSU on → DUT begins to ramp
        print(f"  Turning PSU CH{self._psu_channel} output ON ({self._vin_v} V) — watching for trigger...")
        self._psu.enable_channel_output(self._psu_channel)

        # Step 4: Wait for scope to trigger and complete acquisition
        triggered = self._wait_for_trigger(timeout_s=self._trigger_wait_s)
        if not triggered:
            print(f"  ERROR: Scope did not trigger within {self._trigger_wait_s:.0f} s")
            print("         Check probe connections and trigger level in config.")
            return False

        time.sleep(self._post_poweron_s)
        print("  Scope triggered — acquisition complete.")
        return True

    def _wait_for_trigger(self, timeout_s: float = 15.0) -> bool:
        """Poll scope acquisition state until STOP (triggered + acquired) or timeout."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            state = self._scope.get_acquisition_state()
            if state == "STOP":
                return True
            time.sleep(0.25)
        return False

    # ─────────────────────────────────────────────────────────────
    # Waveform analysis — 90% crossing time
    # ─────────────────────────────────────────────────────────────

    def _extract_90pct_time(self, channel: int, nominal_v: float) -> Optional[float]:
        """
        Download waveform from the scope (scope must already be stopped),
        convert raw data to physical units, and find the first time after T=0
        at which the signal crosses 90% of nominal_v.

        Returns time in seconds (positive = after trigger), or None if the
        waveform did not reach threshold within the captured window.
        """
        # Get preamble (contains all scaling info for this channel)
        preamble = self._scope.get_waveform_preamble(channel)
        if preamble is None:
            self._logger.error(f"CH{channel}: failed to get waveform preamble")
            return None

        # Get raw byte data — scope already stopped so freeze_acquisition=False
        raw = self._scope.get_waveform_data(channel, freeze_acquisition=False)
        if raw is None or len(raw) == 0:
            self._logger.error(f"CH{channel}: no waveform data returned")
            return None

        x_inc = preamble['x_increment']
        x_orig = preamble['x_origin']
        x_ref  = preamble['x_reference']
        y_inc  = preamble['y_increment']
        y_orig = preamble['y_origin']
        y_ref  = preamble['y_reference']

        # Physical time and voltage arrays
        indices = np.arange(len(raw), dtype=float)
        times   = x_inc * (indices - x_ref) + x_orig   # seconds, T=0 at trigger
        volts   = y_inc * (raw.astype(float) - y_ref) + y_orig

        threshold = 0.9 * nominal_v

        # Find first sample after T=0 where voltage >= threshold
        for t, v in zip(times, volts):
            if t >= 0.0 and v >= threshold:
                return float(t)

        self._logger.warning(
            f"CH{channel}: threshold {threshold:.4f} V not reached within captured window "
            f"(max post-trigger time = {float(times[-1])*1e3:.2f} ms)"
        )
        return None

    # ─────────────────────────────────────────────────────────────
    # Cursor / marker placement and screenshot
    # ─────────────────────────────────────────────────────────────

    def _place_cursors_and_screenshot(self, ch_cfg: ScopeChannelConfig,
                                      t_90_s: Optional[float],
                                      filename_prefix: str) -> Optional[str]:
        """
        Place scope markers for this rail and capture a screenshot.

        Marker X1 is always placed at T = 0 (trigger / power-on event).
        Marker X2 is placed at t_90_s (90% threshold crossing) when a valid
        time is available.  If t_90_s is None (threshold not reached within
        the capture window) only X1 is placed so the screenshot still shows
        where T = 0 falls on the waveform.

        Both markers are sourced from ch_cfg.channel so the Y readout on
        the scope display shows the voltage on that specific rail.

        Returns path to the saved screenshot, or None on failure.
        """
        ch = ch_cfg.channel
        try:
            self._scope.set_marker_mode("WAVeform")
            time.sleep(0.1)

            # X1 — always at T = 0 (trigger point)
            self._scope.set_marker_x1y1_source(ch)
            self._scope.set_marker_x_position(1, 0.0)

            # X2 — at 90% crossing when available
            if t_90_s is not None:
                self._scope.set_marker_x2y2_source(ch)
                self._scope.set_marker_x_position(2, t_90_s)

            time.sleep(0.15)

            # Filename suffix indicates whether the 90% point was found
            suffix = "cursor" if t_90_s is not None else "cursor_no90pct"
            fname  = f"{filename_prefix}_{ch_cfg.name}_{suffix}.png"
            path   = self._scope.capture_screenshot(
                filename=fname, freeze_acquisition=False
            )
            if path:
                self._logger.info(f"Screenshot saved: {path}")
                print(f"  Screenshot : screenshots/{fname}")
            return path
        except Exception as e:
            self._logger.error(f"Cursor/screenshot error for {ch_cfg.name}: {e}")
            return None
        finally:
            # Clear markers so they do not bleed into the next rail's screenshot
            try:
                self._scope.set_marker_mode("OFF")
            except Exception:
                pass

    def _capture_full_screenshot(self, filename: str) -> Optional[str]:
        """Save a full four-channel waveform screenshot (no cursors)."""
        try:
            path = self._scope.capture_screenshot(filename=filename, freeze_acquisition=False)
            if path:
                print(f"  Screenshot : screenshots/{filename}")
            return path
        except Exception as e:
            self._logger.error(f"Full screenshot error: {e}")
            return None

    # ─────────────────────────────────────────────────────────────
    # Per-configuration measurement loop
    # ─────────────────────────────────────────────────────────────

    def _measure_channels(self, channels: List[ScopeChannelConfig],
                          config_label: str, screenshot_prefix: str) -> List[RailTimingResult]:
        """
        For each channel in `channels` — one at a time:
          1. Extract 90% crossing time from the captured waveform.
          2. Place cursor X1 at T=0 and cursor X2 at the 90% time (X2 omitted
             if the threshold was not reached within the capture window).
          3. Capture a per-rail screenshot with the cursors visible.
          4. Build a RailTimingResult with PASS / FAIL / ERROR.

        Cursor placement and screenshot happen for every rail regardless of
        whether the 90% threshold was reached.

        Returns list of RailTimingResult, one per channel.
        """
        results: List[RailTimingResult] = []

        print()
        print(f"  -- {config_label} : Rail Ramp Timing Measurements ------------------")
        print(f"  {'Rail':<10} {'TP':<6} {'90% (V)':<10} {'Time (ms)':<14} {'Limit (ms)':<13} {'Status'}")
        print("  " + "-" * 62)

        for ch_cfg in channels:
            rail_name = ch_cfg.name
            nominal_v = ch_cfg.nominal_v
            threshold = ch_cfg.threshold_90pct_v
            limit_ms  = self._limits.get(rail_name, {}).get("max_time_ms", None)

            # ── 1. Waveform analysis ──────────────────────────────────────────
            t_90_s = self._extract_90pct_time(ch_cfg.channel, nominal_v)

            # ── 2+3. Cursor placement + screenshot (always, for every rail) ───
            print(f"  Placing cursors for {rail_name} (CH{ch_cfg.channel})...")
            self._place_cursors_and_screenshot(ch_cfg, t_90_s, screenshot_prefix)

            # ── 4. Build result ───────────────────────────────────────────────
            if t_90_s is None:
                status   = "ERROR"
                t_ms_str = "N/A"
                measured_ms = None
            else:
                t_ms        = round(t_90_s * 1e3, 3)
                measured_ms = t_ms
                if limit_ms is None:
                    status = "PASS"   # no limit defined → informational only
                else:
                    status = "PASS" if t_ms <= limit_ms else "FAIL"
                t_ms_str = f"{t_ms:.3f}"

            results.append(RailTimingResult(
                rail_name=rail_name, test_point=ch_cfg.test_point,
                nominal_v=nominal_v, threshold_90pct_v=threshold,
                measured_time_ms=measured_ms,
                max_time_ms=limit_ms if limit_ms else float('inf'),
                status=status, config_label=config_label
            ))

            limit_str = f"{limit_ms:.1f}" if limit_ms else "—"
            print(f"  {rail_name:<10} {ch_cfg.test_point:<6} {threshold:<10.3f} {t_ms_str:<14} {limit_str:<13} {status}")

        print("  " + "-" * 62)
        return results

    # ─────────────────────────────────────────────────────────────
    # Operator prompts
    # ─────────────────────────────────────────────────────────────

    def _prompt_scope_config_1(self):
        print()
        print("  " + "=" * 58)
        print("  SCOPE SETUP — CONFIG 1   (ACTION REQUIRED)")
        print("  " + "=" * 58)
        print()
        print("  Connect oscilloscope probes:")
        print("    CH1  →  1V0PL  (TP8)    [trigger channel]")
        print("    CH2  →  1V8    (TP6)")
        print("    CH3  →  1V0PS  (TP5)")
        print("    CH4  →  1V35   (TP7)")
        print()
        print("  Connect DMM probes to 3V6 output to confirm voltage.")
        print()
        print("  Timebase : 1 ms/div   Pre-trigger : 20%")
        print("  Trigger  : Rising edge on CH1 at 20% of 1 V (= 0.20 V)")
        print()
        input("  Press ENTER when all probes are connected and ready... ")
        print()

    def _prompt_scope_config_2(self):
        print()
        print("  " + "=" * 58)
        print("  SCOPE SETUP — CONFIG 2   (ACTION REQUIRED)")
        print("  " + "=" * 58)
        print()
        print("  Reconnect oscilloscope probes:")
        print("    CH1  →  2V5    (TP9)    [trigger channel]")
        print("    CH2  →  1V8    (TP6)")
        print("    CH3  →  3V3    (TP10)")
        print("    CH4  →  1V35   (TP7)")
        print()
        print("  Timebase : 1 ms/div   Pre-trigger : 20%")
        print("  Trigger  : Rising edge on CH1 at 20% of 2.5 V (= 0.50 V)")
        print()
        input("  Press ENTER when all probes are reconnected and ready... ")
        print()

    def _prompt_dmm_3v6(self) -> str:
        """Prompt operator to read DMM and enter the 3V6 measurement."""
        expected = self._dmm_3v6_cfg.get("expected_v", 3.6)
        tol      = self._dmm_3v6_cfg.get("tolerance_v", 0.1)
        print()
        print(f"  DMM check: confirm 3V6 rail is in range {expected - tol:.2f} V – {expected + tol:.2f} V")
        raw = input("  Enter DMM reading (V) and press ENTER: ").strip()
        try:
            v = float(raw)
            result = "PASS" if abs(v - expected) <= tol else "FAIL"
            print(f"  3V6 DMM: {v:.4f} V  →  {result}")
            return raw
        except ValueError:
            print("  WARNING: Could not parse DMM reading — recorded as entered.")
            return raw

    # ─────────────────────────────────────────────────────────────
    # Report generation  (CSV + JSON + TXT in reports/ subdir)
    # ─────────────────────────────────────────────────────────────

    def _generate_reports(self, all_results: List[RailTimingResult],
                          dmm_3v6_reading: str) -> str:
        """
        Generate three report files in reports/:
          - power_sequencing_results_TIMESTAMP.csv
          - power_sequencing_results_TIMESTAMP.json
          - power_sequencing_summary_TIMESTAMP.txt
        Returns the overall verdict string ("PASS" / "FAIL").
        """
        self._test_end_time = datetime.datetime.now()
        ts = self._timestamp

        all_pass = all(r.status == "PASS" for r in all_results)
        verdict  = "PASS" if all_pass else "FAIL"

        # ── CSV ───────────────────────────────────────────────────────────────
        csv_path = self._reports_dir / f"power_sequencing_results_{ts}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['Config', 'Rail', 'Test_Point', 'Nominal_V',
                        'Threshold_90pct_V', 'Measured_Time_ms', 'Max_Time_ms', 'Status'])
            for r in all_results:
                t_str = f"{r.measured_time_ms:.3f}" if r.measured_time_ms is not None else "N/A"
                lim   = f"{r.max_time_ms:.1f}" if r.max_time_ms != float('inf') else "—"
                w.writerow([r.config_label, r.rail_name, r.test_point,
                             r.nominal_v, r.threshold_90pct_v, t_str, lim, r.status])
        self._logger.info(f"CSV report saved: {csv_path}")
        print(f"  Saved: reports/{csv_path.name}")

        # ── JSON ──────────────────────────────────────────────────────────────
        json_path = self._reports_dir / f"power_sequencing_results_{ts}.json"
        duration  = (self._test_end_time - self._test_start_time).total_seconds()
        report_data = {
            'test_info': {
                'test_name':       'Power Sequencing Test',
                'start_time':      self._test_start_time.isoformat(),
                'end_time':        self._test_end_time.isoformat(),
                'duration_seconds': round(duration, 1),
                'psu_address':     self._psu_address,
                'scope_address':   self._scope_address,
                'psu_channel':     self._psu_channel,
                'vin_v':           self._vin_v,
                'timebase_ms_per_div': self._timebase_s * 1e3,
                'pretrigger_pct':  self._pretrigger_pct,
                'dmm_3v6_reading': dmm_3v6_reading,
            },
            'rail_results':   [r.to_dict() for r in all_results],
            'overall_result': verdict,
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        self._logger.info(f"JSON report saved: {json_path}")
        print(f"  Saved: reports/{json_path.name}")

        # ── TXT summary ───────────────────────────────────────────────────────
        txt_path = self._reports_dir / f"power_sequencing_summary_{ts}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            _w = f.write
            _w("=" * 70 + "\n")
            _w("  POWER SEQUENCING TEST — RESULTS SUMMARY\n")
            _w("=" * 70 + "\n")
            _w(f"  Date / Time    : {self._test_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            _w(f"  PSU Address    : {self._psu_address}\n")
            _w(f"  Scope Address  : {self._scope_address}\n")
            _w(f"  PSU Channel    : CH{self._psu_channel}  ({self._vin_v} V)\n")
            _w(f"  Timebase       : {self._timebase_s * 1e3:.0f} ms/div  |  Pre-trigger: {self._pretrigger_pct}%\n")
            _w(f"  3V6 DMM check  : {dmm_3v6_reading} V\n")
            _w("=" * 70 + "\n\n")

            _w("  Rail Ramp Timing Measurements\n")
            _w("  (T = 0 when 5 V input begins rising, i.e. scope trigger event)\n\n")
            _w("  " + "-" * 65 + "\n")
            _w(f"  {'Rail':<10} {'TP':<6} {'90% V':<10} {'Measured (ms)':<16} {'Limit (ms)':<13} {'Status'}\n")
            _w("  " + "-" * 65 + "\n")
            for r in all_results:
                t_str   = f"{r.measured_time_ms:.3f}" if r.measured_time_ms is not None else "N/A"
                lim_str = f"{r.max_time_ms:.1f}" if r.max_time_ms != float('inf') else "—"
                _w(f"  {r.rail_name:<10} {r.test_point:<6} {r.threshold_90pct_v:<10.3f} {t_str:<16} {lim_str:<13} {r.status}\n")
            _w("  " + "-" * 65 + "\n\n")

            _w("  Scope Configuration 1:\n")
            for ch in self.CONFIG1_CHANNELS:
                _w(f"    CH{ch.channel}: {ch.name:<8} ({ch.test_point})  nominal={ch.nominal_v} V  90%={ch.threshold_90pct_v:.3f} V\n")
            _w("\n  Scope Configuration 2:\n")
            for ch in self.CONFIG2_CHANNELS:
                _w(f"    CH{ch.channel}: {ch.name:<8} ({ch.test_point})  nominal={ch.nominal_v} V  90%={ch.threshold_90pct_v:.3f} V\n")

            _w("\n" + "=" * 70 + "\n")
            _w(f"  OVERALL RESULT : {verdict}\n")
            _w("=" * 70 + "\n")

        self._logger.info(f"Summary saved: {txt_path}")
        print(f"  Saved: reports/{txt_path.name}")

        return verdict

    # ─────────────────────────────────────────────────────────────
    # Per-configuration phase runners
    # ─────────────────────────────────────────────────────────────

    def _run_config1_phase(self, skip_capture: bool = False,
                           capture_only: bool = False) -> List[RailTimingResult]:
        """
        Execute the Config 1 measurement phase.

        Args:
            skip_capture : If True, skip the PSU power-cycle and scope arm step
                           (scope must already be in STOP with a valid waveform).
            capture_only : If True, take a full screenshot but skip cursor analysis.

        Returns list of RailTimingResult (empty if capture_only=True).
        """
        self._prompt_scope_config_1()

        if not self._configure_scope(self.CONFIG1_CHANNELS, self._cfg1_trigger_ch):
            raise RuntimeError("Config 1 scope configuration failed")

        if not skip_capture:
            if not self._arm_and_capture():
                raise RuntimeError("Config 1 capture failed — scope did not trigger")

        self._capture_full_screenshot("config1_full.png")

        if capture_only:
            return []

        results = self._measure_channels(self.CONFIG1_CHANNELS, "Config 1", "config1")
        return results

    def _run_config2_phase(self, skip_capture: bool = False,
                           capture_only: bool = False) -> List[RailTimingResult]:
        """
        Execute the Config 2 measurement phase.

        Args:
            skip_capture : If True, skip the PSU power-cycle and scope arm step.
            capture_only : If True, take a full screenshot but skip cursor analysis.

        Returns list of RailTimingResult (empty if capture_only=True).
        """
        self._prompt_scope_config_2()

        if not self._configure_scope(self.CONFIG2_CHANNELS, self._cfg2_trigger_ch):
            raise RuntimeError("Config 2 scope configuration failed")

        if not skip_capture:
            if not self._arm_and_capture():
                raise RuntimeError("Config 2 capture failed — scope did not trigger")

        self._capture_full_screenshot("config2_full.png")

        if capture_only:
            return []

        results = self._measure_channels(self.CONFIG2_CHANNELS, "Config 2", "config2")
        return results

    def _prompt_reanalyze_config_select(self) -> str:
        """
        Ask which scope configuration is currently connected when running in
        re-analyse mode (no power cycle, operator chose which probes are on board).

        Returns "config1", "config2", or "both".
        """
        print()
        print("  " + "=" * 58)
        print("  RE-ANALYSE MODE — Which config is currently connected?")
        print("  " + "=" * 58)
        print()
        print("    [1]  Config 1  —  CH1:1V0PL(TP8)  CH2:1V8(TP6)")
        print("                      CH3:1V0PS(TP5)   CH4:1V35(TP7)")
        print()
        print("    [2]  Config 2  —  CH1:2V5(TP9)    CH2:1V8(TP6)")
        print("                      CH3:3V3(TP10)    CH4:1V35(TP7)")
        print()
        while True:
            choice = input("  Enter 1 or 2: ").strip()
            if choice == "1":
                print("  Analysing Config 1 channels.")
                return "config1"
            elif choice == "2":
                print("  Analysing Config 2 channels.")
                return "config2"
            else:
                print("  Invalid — enter 1 or 2.")

    # ─────────────────────────────────────────────────────────────
    # Save / discard prompt
    # ─────────────────────────────────────────────────────────────

    def _prompt_save_results(self):
        """
        Ask the operator whether to keep the run folder.
        If they answer 'no', the entire run directory is deleted.
        """
        print()
        print("  " + "─" * 54)
        while True:
            choice = input("  Save results? [Y/n]: ").strip().lower()
            if choice in ("", "y", "yes"):
                print(f"  Results saved in: {self._run_dir}")
                print()
                return
            elif choice in ("n", "no"):
                try:
                    shutil.rmtree(self._run_dir)
                    print(f"  Run folder deleted: {self._run_dir}")
                except Exception as e:
                    print(f"  WARNING: Could not delete run folder: {e}")
                print()
                return
            else:
                print("  Please enter Y or N.")

    # ─────────────────────────────────────────────────────────────
    # Top-level entry point
    # ─────────────────────────────────────────────────────────────

    def run(self, mode: str = "full") -> bool:
        """
        Execute the power sequencing test in one of five modes.

        Modes
        -----
        "full"       — Config 1 + Config 2  (2 power cycles, all rails)
        "config1"    — Config 1 only  (1V0PL, 1V8, 1V0PS, 1V35)
        "config2"    — Config 2 only  (2V5, 1V8, 3V3, 1V35)
        "capture"    — Power-cycle + full screenshots only, skip cursor analysis
        "reanalyze"  — Skip power cycle; analyse current scope waveform

        Returns True if all measured rails pass their timing limits.
        """
        print()
        print(f"  Mode          : {mode}")
        print(f"  Run directory : {self._run_dir.resolve()}")

        try:
            if not self._connect_instruments():
                return False

            all_results: List[RailTimingResult] = []
            dmm_3v6_reading = "N/A"

            # ── FULL ──────────────────────────────────────────────────────────
            if mode == "full":
                results_1 = self._run_config1_phase()
                all_results.extend(results_1)
                dmm_3v6_reading = self._prompt_dmm_3v6()
                results_2 = self._run_config2_phase()
                all_results.extend(results_2)

            # ── CONFIG 1 ONLY ─────────────────────────────────────────────────
            elif mode == "config1":
                results_1 = self._run_config1_phase()
                all_results.extend(results_1)
                dmm_3v6_reading = self._prompt_dmm_3v6()

            # ── CONFIG 2 ONLY ─────────────────────────────────────────────────
            elif mode == "config2":
                results_2 = self._run_config2_phase()
                all_results.extend(results_2)

            # ── CAPTURE ONLY ──────────────────────────────────────────────────
            elif mode == "capture":
                self._run_config1_phase(capture_only=True)
                self._run_config2_phase(capture_only=True)
                print()
                print("  Capture complete — screenshots saved, no analysis performed.")
                print(f"  Run folder : {self._run_dir}")
                self._prompt_save_results()
                return True   # nothing to PASS/FAIL in capture-only mode

            # ── RE-ANALYSE ────────────────────────────────────────────────────
            elif mode == "reanalyze":
                active = self._prompt_reanalyze_config_select()
                if active == "config1":
                    results_1 = self._run_config1_phase(skip_capture=True)
                    all_results.extend(results_1)
                    dmm_3v6_reading = self._prompt_dmm_3v6()
                else:
                    results_2 = self._run_config2_phase(skip_capture=True)
                    all_results.extend(results_2)

            else:
                print(f"  ERROR: Unknown mode '{mode}'")
                return False

            # ── Reports ───────────────────────────────────────────────────────
            if all_results:
                print()
                print("  Writing reports...")
                verdict = self._generate_reports(all_results, dmm_3v6_reading)
            else:
                verdict = "PASS"

            print()
            print("  " + "=" * 54)
            print(f"  OVERALL RESULT : {verdict}")
            print("  " + "=" * 54)
            print(f"  Run folder     : {self._run_dir}")
            self._prompt_save_results()
            return verdict == "PASS"

        except KeyboardInterrupt:
            print("\n\n  Test interrupted by user.")
            self._prompt_save_results()
            return False

        except Exception as e:
            self._logger.error(f"Unhandled exception: {e}", exc_info=True)
            print(f"\n  ERROR: {e}")
            self._prompt_save_results()
            return False

        finally:
            print("  Disconnecting instruments...")
            self._disconnect_instruments()
