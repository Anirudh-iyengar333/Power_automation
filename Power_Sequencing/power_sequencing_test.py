# This line tells the operating system to run this file using Python 3, making it directly executable on Linux/macOS.
#!/usr/bin/env python3
# This is the module-level documentation string (docstring) that explains the overall purpose of this file to any developer or auditor who opens it.
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

# [Blank line for visual separation between sections]

# Load the 'sys' module, which allows the script to interact with the Python runtime — used here to add folders to the search path and to exit the program on fatal errors.
import sys
# Load the 'csv' module, which provides tools for reading and writing comma-separated value files — used to save the test results spreadsheet.
import csv
# Load the 'json' module, which can read and write data in JSON format — used to load the configuration file and save the JSON results report.
import json
# Load the 'time' module, which provides functions for pausing execution and measuring elapsed time — used for wait delays between instrument commands.
import time
# Load the 'shutil' module, which provides high-level file operations — used to delete the run folder if the operator chooses to discard results.
import shutil
# Load the 'logging' module, which provides a structured way to write diagnostic messages to a log file throughout the test.
import logging
# Load the 'datetime' module, which provides date and time objects — used to timestamp the run folder name and report files.
import datetime
# Import the 'Path' class from the 'pathlib' module — Path objects make it easy to build file and folder paths in a cross-platform way.
from pathlib import Path
# Import 'dataclass' and 'field' from the 'dataclasses' module — these decorators let us define simple data-holding classes without writing boilerplate constructor code.
from dataclasses import dataclass, field
# Import type-hint helpers: 'List' for lists of objects, 'Optional' for values that might be absent (None), and 'Dict' for key-value mappings — these improve code readability and editor support.
from typing import List, Optional, Dict

# [Blank line for visual separation between sections]

# Import the 'numpy' library and give it the short alias 'np' — numpy provides fast numerical array operations needed to convert raw oscilloscope byte data into physical voltage and time values.
import numpy as np

# [Blank line for visual separation between sections]

# Add the parent folder of this file's directory to Python's module search path so that the shared instrument_control package (one level up) can be found and imported.
sys.path.insert(0, str(Path(__file__).parent.parent))

# [Blank line for visual separation between sections]

# Import the KeithleyPowerSupply class from the instrument_control package — this class handles all communication with the Keithley bench power supply (connecting, setting voltage, turning output on/off, etc.).
from instrument_control.keithley_power_supply import KeithleyPowerSupply
# Import the KeysightDSOX6004A class from the instrument_control package — this class handles all communication with the Keysight DSOX6004A oscilloscope (configuring channels, triggering, downloading waveform data, taking screenshots, etc.).
from instrument_control.keysight_oscilloscope import KeysightDSOX6004A

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# This is a visual section divider comment that marks the start of the configuration-loading section of the code.
# ═════════════════════════════════════════════════════════════════════════════
# CONFIG LOADING — reads power_sequencing_config.json once at startup
# ═════════════════════════════════════════════════════════════════════════════

# [Blank line for visual separation between sections]

# If the DIGANTARA_CONFIG environment variable is set (e.g. by the Gradio GUI launching this
# module via subprocess), use that path so the correct board config (CPU, SENSOR, IAP, …) is
# loaded without modifying this file.  If the variable is absent the default CPU config in the
# same folder is used, so the runner still works when invoked directly from the terminal.
import os as _os
_env_cfg = _os.environ.get("DIGANTARA_CONFIG")
_CONFIG_PATH = Path(_env_cfg) if _env_cfg else Path(__file__).parent / "CPU_config.json"

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a function called '_load_config' that reads and parses the JSON configuration file; it accepts an optional custom file path and returns the parsed settings as a Python dictionary.
def _load_config(path: Path = _CONFIG_PATH) -> dict:
    # This docstring explains what the function does, what happens when the file is missing or corrupt, and why the program exits instead of continuing.
    """
    Load the JSON config file.  Exits the program if the file is missing or
    contains invalid JSON — the config is mandatory, not optional.
    """
    # Begin a protected block — the code inside will be attempted, and any errors will be caught by the 'except' blocks below instead of crashing the program immediately.
    try:
        # Open the configuration file in read mode using UTF-8 text encoding, and assign it to the variable 'f' for reading.
        with open(path, "r", encoding="utf-8") as f:
            # Parse the contents of the file as JSON and store the resulting Python dictionary in the variable 'cfg'.
            cfg = json.load(f)
        # Print a confirmation message so the operator knows which config file was successfully loaded.
        print(f"Loaded config from {path.name}")
        # Return the parsed configuration dictionary to the caller so it can be used throughout the rest of the program.
        return cfg
    # If the file does not exist at the expected path, catch that specific error here.
    except FileNotFoundError:
        # Tell the operator which file could not be found.
        print(f"ERROR: Config file not found: {path}")
        # Explain that the file is required and that the operator must place it in the correct folder.
        print(f"       This file is required. Ensure {_CONFIG_PATH.name} is in the same folder.")
        # Stop the program immediately with exit code 1, indicating a fatal error — the test cannot run without this file.
        sys.exit(1)
    # If the file exists but its contents are not valid JSON (e.g. a syntax error in the file), catch that specific error here.
    except json.JSONDecodeError as e:
        # Tell the operator that the JSON in the config file is malformed, and show the specific error detail.
        print(f"ERROR: Config file has invalid JSON: {e}")
        # Instruct the operator to correct the file before trying again.
        print(f"       Fix {_CONFIG_PATH.name} before running the test.")
        # Stop the program immediately — a broken config file must be fixed before the test can proceed.
        sys.exit(1)

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Call the '_load_config' function immediately when this module is first imported, and store the resulting configuration dictionary in '_CFG'. This means the config is read exactly once; every class and function that follows reads from this single shared dictionary.
_CFG = _load_config()   # loaded once; every class/function below uses _CFG

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# This is a visual section divider comment marking the start of the data structure definitions.
# ═════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═════════════════════════════════════════════════════════════════════════════

# [Blank line for visual separation between sections]

# The '@dataclass' decorator automatically generates the constructor (__init__), comparison, and other standard methods for the class below — this removes the need to write repetitive setup code manually.
@dataclass
# Define the 'ScopeChannelConfig' class — each instance of this class holds the full settings for one oscilloscope channel in one capture configuration (channel number, rail name, test point label, target voltage, and vertical display settings).
class ScopeChannelConfig:
    # This docstring briefly describes what the class stores.
    """Holds scope channel assignment and rail parameters for one capture config."""
    # 'channel' stores the oscilloscope channel number (1, 2, 3, or 4) that this rail is connected to.
    channel:      int
    # 'name' stores the human-readable name of the power rail, e.g. "1V0PL" or "3V3".
    name:         str
    # 'test_point' stores the label of the physical test point on the circuit board where the probe is connected, e.g. "TP8".
    test_point:   str
    # 'nominal_v' stores the expected (target) voltage of this rail in volts, e.g. 1.0 for the 1V0PL rail.
    nominal_v:    float
    # 'v_scale' stores the vertical scale setting for this channel on the oscilloscope, in volts per division, so the waveform fits clearly on screen.
    v_scale:      float
    # 'v_offset' stores the vertical offset applied to this channel on the scope display so the waveform is positioned centrally in the viewing area.
    v_offset:     float

    # The '@property' decorator turns the method below into a read-only attribute — calling 'channel_config.threshold_90pct_v' returns a calculated value without needing to call it as a function with parentheses.
    @property
    # Define a computed property 'threshold_90pct_v' that returns the voltage value at which this rail is considered to have successfully ramped up — defined as 90% of the nominal (target) voltage, rounded to 4 decimal places.
    def threshold_90pct_v(self) -> float:
        # Calculate 90% of the nominal voltage and round it to 4 decimal places to match typical oscilloscope precision.
        return round(0.9 * self.nominal_v, 4)

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# The '@dataclass' decorator automatically generates constructor and utility methods for the result class defined below.
@dataclass
# Define the 'RailTimingResult' class — each instance stores the complete test outcome for one power rail after waveform analysis: the rail's identity, target voltage, measured ramp time, the time limit it must meet, whether it passed or failed, and which measurement configuration it belongs to.
class RailTimingResult:
    # This docstring explains what the class represents.
    """Result for one rail after the 90% timing measurement."""
    # 'rail_name' stores the name of the power rail that was tested, e.g. "1V0PL".
    rail_name:       str
    # 'test_point' stores the board label for the physical probe connection point, e.g. "TP8".
    test_point:      str
    # 'nominal_v' stores the full target voltage of this rail in volts.
    nominal_v:       float
    # 'threshold_90pct_v' stores the voltage level (90% of nominal) that the rail must reach before its ramp-up time is recorded.
    threshold_90pct_v: float
    # 'measured_time_ms' stores how many milliseconds after power-on (the trigger event) the rail reached 90% of its target voltage; it is None if the waveform analysis could not determine this value.
    measured_time_ms: Optional[float]   # None if waveform analysis failed
    # 'max_time_ms' stores the maximum number of milliseconds this rail is allowed to take to reach 90% — used to determine PASS or FAIL.
    max_time_ms:     float
    # 'status' stores the final verdict for this rail: "PASS" if the measured time is within the limit, "FAIL" if it exceeded the limit, or "ERROR" if the measurement could not be completed.
    status:          str   # "PASS", "FAIL", or "ERROR"
    # 'config_label' stores the measurement configuration that produced this result: "Config 1" or "Config 2".
    config_label:    str   # "Config 1" or "Config 2"

    # Define a method 'to_dict' that converts this result object into a plain Python dictionary — this makes it easy to write the result to a JSON or CSV file.
    def to_dict(self) -> dict:
        # Return a dictionary containing all fields of this result, using descriptive string keys so the output files are self-explanatory.
        return {
            # Include the rail name under the key 'rail_name'.
            'rail_name':          self.rail_name,
            # Include the test point label under the key 'test_point'.
            'test_point':         self.test_point,
            # Include the nominal target voltage under the key 'nominal_v'.
            'nominal_v':          self.nominal_v,
            # Include the 90% threshold voltage under the key 'threshold_90pct_v'.
            'threshold_90pct_v':  self.threshold_90pct_v,
            # Include the measured ramp time (in milliseconds, or None) under the key 'measured_time_ms'.
            'measured_time_ms':   self.measured_time_ms,
            # Include the maximum allowed ramp time under the key 'max_time_ms'.
            'max_time_ms':        self.max_time_ms,
            # Include the pass/fail/error verdict under the key 'status'.
            'status':             self.status,
            # Include the configuration label (Config 1 or Config 2) under the key 'config_label'.
            'config_label':       self.config_label,
        }

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# This is a visual section divider comment marking the start of helper functions that build configuration objects from the loaded JSON.
# ═════════════════════════════════════════════════════════════════════════════
# CONFIG BUILDER HELPERS
# ═════════════════════════════════════════════════════════════════════════════

# [Blank line for visual separation between sections]

# Define a function '_build_channel_configs' that reads one scope configuration section from the loaded JSON config and converts it into a sorted list of ScopeChannelConfig objects, one per oscilloscope channel.
def _build_channel_configs(cfg_key: str) -> List[ScopeChannelConfig]:
    # This docstring explains what the function does in one sentence.
    """Build the list of ScopeChannelConfig objects from a scope config section."""
    # Look up the named section in the global config dictionary and retrieve the 'channels' sub-dictionary; if either is missing, 'raw' will be an empty dict.
    raw = _CFG.get(cfg_key, {}).get("channels", {})
    # If no channel data was found in the config, the test cannot proceed — print an error message explaining what is missing and stop the program.
    if not raw:
        # Tell the operator which specific key is missing from the config file.
        print(f"ERROR: '{cfg_key}.channels' missing from power_sequencing_config.json")
        # Exit immediately because the test cannot be configured without this data.
        sys.exit(1)
    # Create an empty list that will be filled with ScopeChannelConfig objects, one for each channel entry in the config.
    out = []
    # Loop through each channel entry in the raw dictionary; 'ch_str' is the channel number as a string (e.g. "1"), and 'ch_data' is the dictionary of settings for that channel.
    for ch_str, ch_data in raw.items():
        # Create a ScopeChannelConfig object from the raw data for this channel and add it to the output list; the channel number string is converted to an integer.
        out.append(ScopeChannelConfig(
            # Convert the channel number from a string key (e.g. "1") to an integer (e.g. 1).
            channel=int(ch_str),
            # Copy the rail name from the config data (e.g. "1V0PL").
            name=ch_data["name"],
            # Copy the test point label from the config data (e.g. "TP8").
            test_point=ch_data["test_point"],
            # Copy the nominal (target) voltage for this rail from the config data.
            nominal_v=ch_data["nominal_v"],
            # Copy the oscilloscope vertical scale (volts per division) for this channel from the config data.
            v_scale=ch_data["v_scale"],
            # Copy the oscilloscope vertical offset for this channel from the config data.
            v_offset=ch_data["v_offset"],
        ))
    # Sort the list of channel config objects by channel number (1, 2, 3, 4) so they are always processed in order regardless of how they appear in the JSON file.
    out.sort(key=lambda c: c.channel)
    # Return the sorted list of channel configuration objects to the caller.
    return out

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# This is a visual section divider comment marking the start of the main test class definition.
# ═════════════════════════════════════════════════════════════════════════════
# MAIN TEST CLASS
# ═════════════════════════════════════════════════════════════════════════════

# [Blank line for visual separation between sections]

# Define the 'PowerSequencingTest' class — this is the central class that manages the entire power sequencing test: connecting instruments, configuring the oscilloscope, power-cycling the board, capturing waveforms, measuring ramp times, and saving all results and screenshots.
class PowerSequencingTest:
    # This docstring explains the overall purpose of the class, describes the output folder structure it creates, and shows a minimal usage example.
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

    # This comment explains that the two lines below are class-level constants available before any test object is created — used by the runner script to display a channel summary.
    # Class-level channel config lists — available before instantiation
    # (used by the runner to display a config summary)
    # Build and store the list of channel configurations for the first scope setup (Config 1: lower voltage rails) by reading from the JSON config — this is calculated once when the class is defined.
    CONFIG1_CHANNELS = _build_channel_configs("scope_config_1")
    # Build and store the list of channel configurations for the second scope setup (Config 2: higher voltage rails) by reading from the JSON config — also calculated once at class definition time.
    CONFIG2_CHANNELS = _build_channel_configs("scope_config_2")

    # Define the constructor method '__init__' that is called when a new PowerSequencingTest object is created; it accepts an optional output directory path and sets up all test parameters, folder structure, logging, and instrument handles.
    def __init__(self, output_dir: str = None):
        # Record the exact date and time when this test object was created — used to name the run folder and timestamp all report files.
        self._test_start_time = datetime.datetime.now()
        # Set the test end time to None for now; it will be filled in when the reports are generated at the end of the test.
        self._test_end_time: Optional[datetime.datetime] = None

        # This comment marks the start of reading individual setting groups from the global config dictionary.
        # ── Read sections from _CFG ───────────────────────────────────────────
        # Read the 'instrument_addresses' section from the config — contains the VISA addresses for the power supply and oscilloscope.
        instr    = _CFG.get("instrument_addresses", {})
        # Read the 'psu_settings' section from the config — contains the voltage, current limit, OVP, channel, and timing settings for the power supply.
        psu_cfg  = _CFG.get("psu_settings", {})
        # Read the 'scope_settings' section from the config — contains the timebase, trigger, coupling, bandwidth, and timing settings for the oscilloscope.
        scp_cfg  = _CFG.get("scope_settings", {})

        # ── VISA auto-detection ───────────────────────────────────────────────
        # Try to auto-detect the PSU and oscilloscope on the VISA bus first.
        # Falls back to the config address if detection fails.
        _detected_psu_addr: Optional[str]   = None
        _detected_scope_addr: Optional[str] = None
        try:
            from visa_auto_detect import detect_power_sequencing_instruments
            print("\nAuto-detecting instruments on VISA bus...")
            _detected_psu_addr, _detected_scope_addr = detect_power_sequencing_instruments()
        except ImportError:
            pass  # visa_auto_detect not available — use config addresses

        self._psu_address   = _detected_psu_addr   if _detected_psu_addr   else instr.get("psu")
        self._scope_address = _detected_scope_addr if _detected_scope_addr else instr.get("scope")

        # Store which output channel on the power supply to use (typically 1).
        self._psu_channel     = psu_cfg.get("channel", 1)
        # Store the voltage the power supply should output to power the DUT (typically 5 V).
        self._vin_v           = psu_cfg.get("vin_v", 5.0)
        # Store the maximum current the power supply is allowed to deliver — protects the DUT from excessive current.
        self._current_limit_a = psu_cfg.get("current_limit_a", 2.0)
        # Store the over-voltage protection threshold — the power supply will shut down if its output exceeds this level, protecting the DUT.
        self._ovp_level_v     = psu_cfg.get("ovp_level_v", 6.0)
        # Store how long (in milliseconds) to wait before declaring the power supply has timed out when sending a command.
        self._psu_timeout_ms  = psu_cfg.get("timeout_ms", 10000)
        # Store how many seconds to wait after turning the PSU output OFF before arming the scope — allows the DUT rails to fully collapse.
        self._pre_poweroff_s  = psu_cfg.get("pre_poweroff_wait_s", 2.0)
        # Store how many seconds to wait after turning the PSU output ON before checking the scope state — allows initial transient settling.
        self._post_poweron_s  = psu_cfg.get("post_poweron_wait_s", 0.5)

        # Store the oscilloscope horizontal timebase setting in seconds per division (e.g. 1 ms/div = 0.001).
        self._timebase_s        = scp_cfg.get("timebase_s_per_div", 1e-3)
        # Store the percentage of the total capture window that appears before the trigger event — 20% means the waveform starts 20% before the power-on moment.
        self._pretrigger_pct    = scp_cfg.get("pretrigger_pct", 20)
        # Store the direction of the trigger edge — "POS" means the scope triggers when the signal is rising (going from low to high).
        self._trigger_slope     = scp_cfg.get("trigger_slope", "POS")
        # Store the oscilloscope sweep mode — "NORMal" means the scope will wait for a real trigger signal and only capture once (single-shot).
        self._sweep_mode        = scp_cfg.get("sweep_mode", "NORMal")
        # Store the signal coupling type — "DC" means the scope measures the true DC+AC voltage without filtering out the DC component.
        self._coupling          = scp_cfg.get("coupling", "DC")
        # Store the probe attenuation factor — 10.0 means 10:1 probes are used, which the scope uses to scale its voltage readings correctly.
        self._probe_attenuation = scp_cfg.get("probe_attenuation", 10.0)
        # Store whether to enable the 20 MHz bandwidth limit on the oscilloscope channels — True reduces high-frequency noise on the slowly-rising power rail signals.
        self._bw_limit_20mhz   = scp_cfg.get("bandwidth_limit_20mhz", True)
        # Store how long (in milliseconds) to wait before declaring the oscilloscope has timed out on a command.
        self._scope_timeout_ms  = scp_cfg.get("timeout_ms", 60000)
        # Store the maximum number of seconds to wait for the oscilloscope to trigger after the PSU is turned on — if no trigger occurs within this time, the test reports an error.
        self._trigger_wait_s    = scp_cfg.get("trigger_wait_s", 15.0)

        # Store which oscilloscope channel is the trigger source for Config 1 (typically channel 1, connected to the 1V0PL rail).
        self._cfg1_trigger_ch = _CFG.get("scope_config_1", {}).get("trigger_channel", 1)
        # Store which oscilloscope channel is the trigger source for Config 2 (typically channel 1, connected to the 2V5 rail).
        self._cfg2_trigger_ch = _CFG.get("scope_config_2", {}).get("trigger_channel", 1)

        # Store the dictionary of rail timing limits from the config — each rail's entry specifies the maximum time (in ms) it is allowed to take to reach 90% of its target voltage.
        self._limits          = _CFG.get("rail_timing_limits", {})
        # Store the DMM 3V6 check settings from the config — contains the expected voltage and tolerance for the manual multimeter confirmation step.
        self._dmm_3v6_cfg     = _CFG.get("dmm_3v6_check", {})

        # This comment explains the mathematics used to calculate the time-axis offset that positions the trigger event at the correct percentage from the left edge of the scope display.
        # Pre-trigger offset: positions trigger at pretrigger_pct% from left edge
        # offset = (total_window / 2) - pre_trigger_time
        # Calculate the total captured time window in seconds — for a 10-division display at 1 ms/div, this is 10 ms.
        total_window_s       = 10 * self._timebase_s
        # Calculate how much time before the trigger event should be visible on screen (e.g. 20% of 10 ms = 2 ms).
        pre_trigger_s        = (self._pretrigger_pct / 100.0) * total_window_s
        # Calculate the horizontal offset to send to the oscilloscope so that the trigger event lands at the correct position on the display.
        self._timebase_offset_s = (total_window_s / 2.0) - pre_trigger_s

        # This comment marks the block that determines where test result files will be saved.
        # ── Resolve output directory ──────────────────────────────────────────
        # If no output directory was passed to the constructor, read the default path from the config file.
        if output_dir is None:
            # Read the 'output_dir' section from the config — it may be either a dictionary with a 'path' key or a plain string.
            out_cfg = _CFG.get("output_dir", {})
            # Extract the directory path string from the config, falling back to "power_sequencing_results" if the setting is absent.
            output_dir = (
                out_cfg.get("path", "power_sequencing_results")
                if isinstance(out_cfg, dict)
                else str(out_cfg)
            )

        # Format the test start time as a compact string (e.g. "20260408_143022") to use in folder and file names.
        timestamp = self._test_start_time.strftime("%Y%m%d_%H%M%S")
        # Store the timestamp string as an instance attribute so report-generation methods can use it later.
        self._timestamp = timestamp

        # Build the full path to the unique run folder for this test execution (e.g. "power_sequencing_results/run_20260408_143022").
        self._run_dir         = Path(output_dir) / f"run_{timestamp}"
        # Build the path to the screenshots sub-folder inside the run folder — all oscilloscope images will be saved here.
        self._screenshots_dir = self._run_dir / "screenshots"
        # Build the path to the reports sub-folder inside the run folder — CSV, JSON, and text summary files will be saved here.
        self._reports_dir     = self._run_dir / "reports"

        # Attempt to create the run folder and all its sub-folders; if any already exist, that is acceptable and no error is raised.
        try:
            # Loop through the three directories that need to be created: the run folder, the screenshots folder, and the reports folder.
            for d in [self._run_dir, self._screenshots_dir, self._reports_dir]:
                # Create the directory and any necessary parent directories; do not raise an error if the directory already exists.
                d.mkdir(parents=True, exist_ok=True)
        # If the folder cannot be created due to a permissions problem or other OS-level error, catch it here and fall back to a safe location.
        except (PermissionError, OSError) as e:
            # Build a fallback output path in the same folder as this script file, which should always be writable.
            fallback = Path(__file__).resolve().parent / "power_sequencing_results"
            # Redefine the run folder path using the fallback location.
            self._run_dir         = fallback / f"run_{timestamp}"
            # Redefine the screenshots sub-folder path under the fallback run folder.
            self._screenshots_dir = self._run_dir / "screenshots"
            # Redefine the reports sub-folder path under the fallback run folder.
            self._reports_dir     = self._run_dir / "reports"
            # Create all three directories under the fallback location.
            for d in [self._run_dir, self._screenshots_dir, self._reports_dir]:
                # Create the directory and any missing parent directories.
                d.mkdir(parents=True, exist_ok=True)
            # Warn the operator that the requested output folder could not be used and show them where results are actually being saved.
            print(f"  WARNING: Could not write to '{output_dir}' ({e}). Falling back to: {fallback}")

        # This comment marks the block that sets up the log file for this test run.
        # ── Logging ───────────────────────────────────────────────────────────
        # Create (or retrieve an existing) logger named after this class — all log messages from this object will be tagged with the class name.
        self._logger = logging.getLogger(self.__class__.__name__)
        # Build the full file path for the log file that will be written inside the run folder.
        log_path = self._run_dir / "power_sequencing_test.log"
        # Only add a file handler if none has been added yet — prevents duplicate log entries if the test object is recreated.
        if not self._logger.handlers:
            # Create a file handler that writes log messages to the log file using UTF-8 encoding.
            fh = logging.FileHandler(str(log_path), encoding="utf-8")
            # Set the log message format to include the time, severity level, logger name, and message text.
            fh.setFormatter(logging.Formatter(
                # This format string defines the layout of each log line: timestamp, severity, logger name, and message.
                '%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
                # Format the timestamp as hours:minutes:seconds.
                datefmt='%H:%M:%S'
            ))
            # Attach the file handler to the logger so that log messages are written to the file.
            self._logger.addHandler(fh)
            # Set the minimum severity level that will be recorded — DEBUG means all messages (debug, info, warning, error, critical) are logged.
            self._logger.setLevel(logging.DEBUG)
        # Write the first log entry recording the path of the run folder so the log is self-documenting.
        self._logger.info(f"Run directory: {self._run_dir}")

        # Tell the scope object where to save screenshots — override its default directory with our run-specific screenshots folder.
        # Override scope's built-in screenshot dir to our run folder
        self._scope_screenshot_dir = self._screenshots_dir

        # This comment marks the block that initialises the instrument connection handles to None — they will be assigned when '_connect_instruments' is called.
        # ── Instrument handles ────────────────────────────────────────────────
        # Initialise the power supply handle to None — it will be assigned to a live KeithleyPowerSupply object when instruments are connected.
        self._psu:   Optional[KeithleyPowerSupply] = None
        # Initialise the oscilloscope handle to None — it will be assigned to a live KeysightDSOX6004A object when instruments are connected.
        self._scope: Optional[KeysightDSOX6004A]  = None

    # This comment marks a group of methods responsible for opening and closing the connections to both instruments.
    # ─────────────────────────────────────────────────────────────
    # Instrument helpers
    # ─────────────────────────────────────────────────────────────

    # Define the '_connect_instruments' method — this method opens VISA connections to both the power supply and the oscilloscope, confirms they responded, and pre-configures the power supply channel (voltage set, output OFF).
    def _connect_instruments(self) -> bool:
        # Print a status message so the operator knows the connection attempt is starting.
        print("\n  Connecting instruments...")

        # Create a new KeithleyPowerSupply connection object using the stored VISA address and timeout, and store it as the PSU handle.
        self._psu = KeithleyPowerSupply(self._psu_address, timeout_ms=self._psu_timeout_ms)
        # Attempt to open the VISA connection to the power supply and check whether it succeeded.
        if not self._psu.connect():
            # If the connection failed, print an error message identifying which address could not be reached.
            print(f"  ERROR: Failed to connect to PSU at {self._psu_address}")
            # Return False to signal to the caller that instruments could not be connected and the test should not proceed.
            return False
        # Print a confirmation message that the PSU is online, including its model identifier for verification.
        print(f"  PSU connected  — model: {self._psu.model}")

        # Create a new KeysightDSOX6004A connection object using the stored VISA address and timeout, and store it as the scope handle.
        self._scope = KeysightDSOX6004A(self._scope_address, timeout_ms=self._scope_timeout_ms)
        # Attempt to open the VISA connection to the oscilloscope and check whether it succeeded.
        if not self._scope.connect():
            # If the connection failed, print an error message identifying which address could not be reached.
            print(f"  ERROR: Failed to connect to scope at {self._scope_address}")
            # Return False to signal to the caller that instruments could not be connected.
            return False
        # Print a confirmation message that the oscilloscope is online, including its model identifier for verification.
        print(f"  Scope connected — {self._scope.get_instrument_info().get('model', 'Keysight')}")

        # Direct the oscilloscope object to save all screenshots into our run-specific screenshots folder rather than its default location.
        # Point the scope's screenshot directory at our run folder
        self._scope.screenshot_dir = self._screenshots_dir

        # Configure the power supply channel: set the output voltage, current limit, and OVP level, but keep the output switched OFF so the DUT does not receive power yet.
        # Configure PSU (output OFF, voltage set, limits in place)
        ok = self._psu.configure_channel(
            # Specify which channel on the PSU to configure.
            channel=self._psu_channel,
            # Set the output voltage to the DUT input voltage specified in the config.
            voltage=self._vin_v,
            # Set the maximum current the PSU will deliver before limiting (protects the DUT).
            current_limit=self._current_limit_a,
            # Set the over-voltage protection threshold (PSU shuts off if output exceeds this).
            ovp_level=self._ovp_level_v,
            # Leave the output disabled — the DUT must not be powered until the scope is armed.
            enable_output=False
        )
        # Check whether the PSU configuration command succeeded.
        if not ok:
            # If configuration failed, print an error message and signal failure to the caller.
            print("  ERROR: PSU channel configuration failed")
            # Return False to abort instrument setup.
            return False
        # Print a confirmation message summarising the PSU settings that were applied, confirming the output is currently off.
        print(f"  PSU CH{self._psu_channel} configured: {self._vin_v} V / {self._current_limit_a} A / OVP {self._ovp_level_v} V  (output OFF)")
        # Return True to confirm that both instruments are connected and the PSU is configured correctly.
        return True

    # Define the '_disconnect_instruments' method — this method safely turns off the power supply output and closes the VISA connections to both instruments at the end of the test or in case of an error.
    def _disconnect_instruments(self):
        # Begin a protected block for the PSU disconnection — if anything goes wrong here it should not crash the program.
        try:
            # Only attempt to disconnect the PSU if it was previously connected.
            if self._psu and self._psu.is_connected:
                # Turn off all PSU output channels before disconnecting to ensure the DUT is not left powered.
                self._psu.disable_all_outputs()
                # Close the VISA connection to the power supply.
                self._psu.disconnect()
        # If anything goes wrong during PSU disconnection, log a warning but do not stop the program.
        except Exception as e:
            # Log the PSU disconnection error at WARNING level so it appears in the log file without stopping the program.
            self._logger.warning(f"PSU disconnect error: {e}")
        # Begin a protected block for the oscilloscope disconnection.
        try:
            # Only attempt to disconnect the scope if it was previously connected.
            if self._scope and self._scope.is_connected:
                # Close the VISA connection to the oscilloscope.
                self._scope.disconnect()
        # If anything goes wrong during scope disconnection, log a warning but do not stop the program.
        except Exception as e:
            # Log the scope disconnection error at WARNING level.
            self._logger.warning(f"Scope disconnect error: {e}")

    # This comment marks a group of methods responsible for configuring the oscilloscope before each capture.
    # ─────────────────────────────────────────────────────────────
    # Scope configuration
    # ─────────────────────────────────────────────────────────────

    # Define the '_configure_scope' method — this method applies the full oscilloscope setup for one capture configuration: sets the timebase and pre-trigger offset, configures the vertical scale and coupling for each of the four channels, and arms the trigger on the designated channel at 20% of its nominal voltage.
    def _configure_scope(self, channels: List[ScopeChannelConfig], trigger_ch: int) -> bool:
        # This docstring explains the four things this method does in plain terms.
        """
        Apply full scope setup for a capture configuration:
          - All four channels scaled and coupled
          - Timebase with 20% pre-trigger offset
          - Rising-edge trigger on trigger_ch at 20% of its nominal voltage
          - NORMal sweep mode (waits for real trigger event)
        """
        # Print a blank line for visual separation, then announce that scope configuration is starting.
        print()
        # Announce that scope configuration is in progress.
        print("  Configuring scope...")

        # This comment marks the timebase configuration step.
        # Timebase
        # Send the horizontal timebase and offset settings to the oscilloscope; if the command fails, abort the configuration.
        if not self._scope.configure_timebase(self._timebase_s, self._timebase_offset_s):
            # Print an error message so the operator knows the timebase could not be set.
            print("  ERROR: Could not set scope timebase")
            # Return False to signal that scope configuration failed.
            return False
        # Print a confirmation line showing the timebase, offset, and pre-trigger percentage that were applied.
        print(f"  Timebase : {self._timebase_s * 1e3:.0f} ms/div  |  offset {self._timebase_offset_s * 1e3:.1f} ms  ({self._pretrigger_pct}% pre-trigger)")

        # This comment marks the channel-by-channel configuration step.
        # Channels
        # Loop through each channel configuration object in the list to configure them one at a time.
        for ch in channels:
            # Send the vertical scale, offset, coupling, and probe attenuation settings for this channel to the oscilloscope.
            ok = self._scope.configure_channel(
                # Specify the channel number to configure.
                channel=ch.channel,
                # Set the vertical scale (volts per division) for this channel.
                vertical_scale=ch.v_scale,
                # Set the vertical position offset for this channel.
                vertical_offset=ch.v_offset,
                # Set the signal coupling (DC passes both AC and DC components).
                coupling=self._coupling,
                # Inform the scope of the probe attenuation so voltage readings are scaled correctly.
                probe_attenuation=self._probe_attenuation
            )
            # Check whether the channel configuration command succeeded.
            if not ok:
                # Print an error message identifying which channel and rail name could not be configured.
                print(f"  ERROR: Could not configure CH{ch.channel} ({ch.name})")
                # Return False to signal that scope configuration failed.
                return False

            # Enable the 20 MHz bandwidth limit on this channel — this reduces electrical noise from the high-speed switching circuits without affecting the slow power-rail ramps being measured.
            # 20 MHz bandwidth limit — suppresses high-frequency noise on slow ramps
            self._scope.set_bandwidth_limit(ch.channel, self._bw_limit_20mhz)

            # Print a summary line confirming the settings applied to this channel.
            print(f"  CH{ch.channel} : {ch.name:<8} ({ch.test_point})  "
                  f"scale={ch.v_scale} V/div  offset={ch.v_offset} V  "
                  f"probe={int(self._probe_attenuation)}×  "
                  f"BW={'20 MHz' if self._bw_limit_20mhz else 'full'}")

        # This comment marks the trigger configuration step.
        # Trigger channel nominal and threshold
        # Find the configuration object for the designated trigger channel; fall back to the first channel if not found.
        trig_ch_cfg = next((c for c in channels if c.channel == trigger_ch), channels[0])
        # Calculate the trigger voltage level as 20% of the trigger channel's nominal voltage, rounded to 4 decimal places.
        trigger_level = round(0.2 * trig_ch_cfg.nominal_v, 4)

        # Send the trigger settings to the oscilloscope: source channel, threshold voltage, edge direction, and sweep mode.
        ok = self._scope.configure_trigger(
            # Set the trigger source to the designated trigger channel.
            channel=trigger_ch,
            # Set the voltage threshold at which the trigger fires (20% of nominal).
            trigger_level=trigger_level,
            # Set the trigger edge direction (rising edge = positive slope).
            trigger_slope=self._trigger_slope,
            # Set the sweep mode (NORMal = wait for a real trigger, single acquisition).
            sweep_mode=self._sweep_mode
        )
        # Check whether the trigger configuration command succeeded.
        if not ok:
            # Print an error message identifying which channel the trigger could not be set on.
            print(f"  ERROR: Could not configure trigger on CH{trigger_ch}")
            # Return False to signal that scope configuration failed.
            return False
        # Print a confirmation line showing which channel the trigger is set on, the threshold voltage, and the percentage of nominal it represents.
        print(f"  Trigger  : CH{trigger_ch} ({trig_ch_cfg.name})  rising edge at {trigger_level} V  (20% of {trig_ch_cfg.nominal_v} V)")
        # Return True to confirm that all scope configuration steps completed successfully.
        return True

    # This comment marks a group of methods responsible for power-cycling the DUT and capturing the single-shot waveform.
    # ─────────────────────────────────────────────────────────────
    # Power-cycle and single-shot capture
    # ─────────────────────────────────────────────────────────────

    # Define the '_arm_and_capture' method — this method turns the PSU output off to ensure the DUT is de-powered, then arms the oscilloscope for a single-shot acquisition, then turns the PSU back on so the DUT powers up and the rising rails trigger the scope.
    def _arm_and_capture(self) -> bool:
        # This docstring lists the five sequential steps the method performs and states what it returns.
        """
        Power-cycle the DUT and capture one single-shot waveform:
          1. Ensure PSU output is OFF (DUT powered down).
          2. Wait for rails to collapse.
          3. Arm scope for single acquisition.
          4. Turn PSU output ON → DUT powers up → scope triggers on Ch1 rising edge.
          5. Wait for scope to reach STOP (acquisition complete).
        Returns True if scope triggered successfully within the timeout.
        """
        # Print a blank line and a section banner to clearly indicate in the console output that the power-cycle and capture step is starting.
        print()
        # Print a visual banner to clearly mark this phase in the terminal output.
        print("  -- Power-cycle and capture -----------------------------------------")

        # This comment marks Step 1: turning the PSU off to de-power the DUT.
        # Step 1: PSU off
        # Print a message telling the operator what is happening: the DUT is being powered down.
        print(f"  Turning PSU CH{self._psu_channel} output OFF (DUT power down)...")
        # Send the command to the power supply to turn its output channel off.
        self._psu.disable_channel_output(self._psu_channel)
        # Pause for the pre-power-off wait time to allow the DUT's power rails to fully discharge before the scope is armed.
        time.sleep(self._pre_poweroff_s)

        # This comment marks Step 2: arming the oscilloscope to wait for the next trigger event.
        # Step 2: Arm scope for single acquisition
        # Tell the operator the scope is being armed.
        print("  Arming scope for single-shot acquisition...")
        # Send the SINGLE command to the oscilloscope — it will now wait for the next rising edge trigger before capturing.
        if not self._scope.single():
            # If the SINGLE command failed, print an error message.
            print("  ERROR: Could not arm scope for single acquisition")
            # Return False to signal that the capture setup failed.
            return False
        # Wait a short time after arming to allow the scope's internal state to settle before powering on the DUT.
        time.sleep(0.3)   # brief arm settle

        # This comment marks Step 3: turning the PSU on so the DUT begins to power up and the scope can trigger.
        # Step 3: PSU on → DUT begins to ramp
        # Tell the operator the PSU output is being turned on and which voltage is being applied.
        print(f"  Turning PSU CH{self._psu_channel} output ON ({self._vin_v} V) — watching for trigger...")
        # Send the command to the power supply to turn its output channel on, supplying voltage to the DUT.
        self._psu.enable_channel_output(self._psu_channel)

        # This comment marks Step 4: waiting for the oscilloscope to confirm that it has triggered and captured the waveform.
        # Step 4: Wait for scope to trigger and complete acquisition
        # Poll the oscilloscope repeatedly until it reports that acquisition is complete (STOP state) or the timeout expires.
        triggered = self._wait_for_trigger(timeout_s=self._trigger_wait_s)
        # Check whether the scope triggered successfully within the allowed time.
        if not triggered:
            # Print an error message stating that the scope did not trigger and how long it waited.
            print(f"  ERROR: Scope did not trigger within {self._trigger_wait_s:.0f} s")
            # Suggest to the operator what to check: probe connections and trigger voltage level in the config.
            print("         Check probe connections and trigger level in config.")
            # Return False to signal that the capture failed.
            return False

        # Wait a short additional time after the trigger to allow any post-trigger settling before reading the waveform.
        time.sleep(self._post_poweron_s)
        # Print a success message confirming the scope has triggered and the waveform has been captured.
        print("  Scope triggered — acquisition complete.")
        # Return True to confirm that the power-cycle and capture completed successfully.
        return True

    # Define the '_wait_for_trigger' method — this method repeatedly asks the oscilloscope for its current acquisition status and returns True as soon as it reports STOP (meaning a trigger occurred and the waveform was captured), or returns False if the timeout expires first.
    def _wait_for_trigger(self, timeout_s: float = 15.0) -> bool:
        # This docstring explains what the method does and what each return value means.
        """Poll scope acquisition state until STOP (triggered + acquired) or timeout."""
        # Calculate the absolute time at which the wait should be abandoned — current time plus the timeout duration.
        deadline = time.monotonic() + timeout_s
        # Keep looping until the deadline is reached.
        while time.monotonic() < deadline:
            # Ask the oscilloscope for its current acquisition state (e.g. "RUN", "WAIT", "STOP").
            state = self._scope.get_acquisition_state()
            # If the state is STOP, the scope has triggered and the waveform is ready — return True immediately.
            if state == "STOP":
                return True
            # Wait 250 milliseconds before asking again to avoid flooding the instrument with queries.
            time.sleep(0.25)
        # If the loop exits without finding a STOP state, the timeout expired — return False to indicate no trigger occurred.
        return False

    # This comment marks a group of methods responsible for downloading waveform data and computing the 90% rise time.
    # ─────────────────────────────────────────────────────────────
    # Waveform analysis — 90% crossing time
    # ─────────────────────────────────────────────────────────────

    # Define the '_extract_90pct_time' method — this method downloads the raw waveform from one oscilloscope channel, converts the raw byte values to real voltage and time values using the scope's scaling factors, and then searches for the first moment after the trigger (T=0) when the signal reaches 90% of the rail's target voltage.
    def _extract_90pct_time(self, channel: int, nominal_v: float) -> Optional[float]:
        # This docstring explains what the method downloads, how it converts the data, what it searches for, and what it returns when the threshold is not reached.
        """
        Download waveform from the scope (scope must already be stopped),
        convert raw data to physical units, and find the first time after T=0
        at which the signal crosses 90% of nominal_v.

        Returns time in seconds (positive = after trigger), or None if the
        waveform did not reach threshold within the captured window.
        """
        # This comment explains that the preamble contains all the scaling constants needed to convert raw byte values to real volts and seconds.
        # Get preamble (contains all scaling info for this channel)
        # Request the waveform preamble (metadata) from the oscilloscope for this channel — it contains scaling factors for both axes.
        preamble = self._scope.get_waveform_preamble(channel)
        # If the preamble could not be retrieved, log an error and return None to indicate the measurement failed.
        if preamble is None:
            # Log an error message identifying which channel failed to return a preamble.
            self._logger.error(f"CH{channel}: failed to get waveform preamble")
            # Return None to signal that the 90% time could not be determined.
            return None

        # This comment explains that the raw data is retrieved without re-freezing the acquisition because the scope is already stopped.
        # Get raw byte data — scope already stopped so freeze_acquisition=False
        # Download the raw waveform byte array from the oscilloscope for this channel.
        raw = self._scope.get_waveform_data(channel, freeze_acquisition=False)
        # If no data was returned, log an error and return None.
        if raw is None or len(raw) == 0:
            # Log an error indicating the channel returned an empty waveform.
            self._logger.error(f"CH{channel}: no waveform data returned")
            # Return None to signal that the 90% time could not be determined.
            return None

        # Extract the horizontal increment (time per sample step, in seconds) from the preamble.
        x_inc = preamble['x_increment']
        # Extract the horizontal origin (time value of the reference sample, in seconds) from the preamble.
        x_orig = preamble['x_origin']
        # Extract the horizontal reference sample index from the preamble (used as the pivot for the time axis calculation).
        x_ref  = preamble['x_reference']
        # Extract the vertical increment (voltage per raw data unit) from the preamble.
        y_inc  = preamble['y_increment']
        # Extract the vertical origin (voltage offset applied to the raw data) from the preamble.
        y_orig = preamble['y_origin']
        # Extract the vertical reference value (raw data value that corresponds to the zero-offset point) from the preamble.
        y_ref  = preamble['y_reference']

        # This comment explains that the following two lines convert raw sample indices into real physical units using the scope's preamble scaling constants.
        # Physical time and voltage arrays
        # Create an array of sample index numbers (0, 1, 2, ...) as floating-point values — these are the positions of each data point in the raw array.
        indices = np.arange(len(raw), dtype=float)
        # Convert the sample indices to real time values in seconds, where T=0 corresponds to the trigger event.
        times   = x_inc * (indices - x_ref) + x_orig   # seconds, T=0 at trigger
        # Convert the raw byte values to real voltage values using the scope's vertical scaling constants.
        volts   = y_inc * (raw.astype(float) - y_ref) + y_orig

        # Calculate the 90% threshold voltage that the rail must reach — this is the target voltage we are looking for in the waveform.
        threshold = 0.9 * nominal_v

        # This comment explains the search logic: scan forward in time starting from T=0 and stop as soon as the voltage exceeds the threshold.
        # Find first sample after T=0 where voltage >= threshold
        # Iterate through each pair of (time, voltage) values from the waveform.
        for t, v in zip(times, volts):
            # Only consider samples that occur at or after the trigger event (T=0 or later).
            if t >= 0.0 and v >= threshold:
                # Return the time (in seconds) of the first sample that meets both conditions — this is the 90% crossing time.
                return float(t)

        # If we reach here, the waveform never reached the threshold within the captured time window — log a warning with diagnostic details.
        self._logger.warning(
            # Include the channel number, the threshold voltage, and the last available time in the captured window.
            f"CH{channel}: threshold {threshold:.4f} V not reached within captured window "
            f"(max post-trigger time = {float(times[-1])*1e3:.2f} ms)"
        )
        # Return None to indicate that the 90% crossing time could not be determined from this waveform.
        return None

    # This comment marks a group of methods responsible for placing oscilloscope cursor markers and capturing screenshots.
    # ─────────────────────────────────────────────────────────────
    # Cursor / marker placement and screenshot
    # ─────────────────────────────────────────────────────────────

    # Define the '_place_cursors_and_screenshot' method — this method positions two time-axis markers on the oscilloscope display (one at T=0 for power-on, one at the 90% crossing time) and then captures a screenshot showing the waveform with those markers visible.
    def _place_cursors_and_screenshot(self, ch_cfg: ScopeChannelConfig,
                                      t_90_s: Optional[float],
                                      filename_prefix: str) -> Optional[str]:
        # This docstring explains the marker placement logic, the special case when the 90% time is not available, and what the method returns.
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
        # Store the channel number in a short local variable for convenience.
        ch = ch_cfg.channel
        # Begin a protected block — if any step in the marker or screenshot sequence fails, the error is caught and logged rather than crashing the test.
        try:
            # Set the oscilloscope's marker mode to "WAVeform" so the X markers track the waveform being displayed.
            self._scope.set_marker_mode("WAVeform")
            # Wait a brief moment to allow the scope to apply the marker mode change.
            time.sleep(0.1)

            # This comment marks the placement of the first cursor (X1) at the trigger/power-on moment.
            # X1 — always at T = 0 (trigger point)
            # Set the source channel for the X1 and Y1 markers to the current rail's channel so the Y readout shows the voltage of this specific rail.
            self._scope.set_marker_x1y1_source(ch)
            # Position the X1 marker at T = 0, which represents the exact moment the power supply turned on and the scope triggered.
            self._scope.set_marker_x_position(1, 0.0)

            # This comment marks the conditional placement of the second cursor (X2) at the 90% crossing time.
            # X2 — at 90% crossing when available
            # Only place the X2 marker if a valid 90% crossing time was found (i.e. t_90_s is not None).
            if t_90_s is not None:
                # Set the source channel for the X2 and Y2 markers to the same rail's channel.
                self._scope.set_marker_x2y2_source(ch)
                # Position the X2 marker at the measured 90% crossing time so the display shows the ramp duration.
                self._scope.set_marker_x_position(2, t_90_s)

            # Wait a brief moment to allow the scope display to update with the marker positions before capturing the screenshot.
            time.sleep(0.15)

            # This comment explains that the filename suffix differs depending on whether the 90% crossing was found.
            # Filename suffix indicates whether the 90% point was found
            # Choose the filename suffix: "cursor" if the 90% time was found, or "cursor_no90pct" if the threshold was never reached.
            suffix = "cursor" if t_90_s is not None else "cursor_no90pct"
            # Build the full filename for this screenshot, combining the config prefix, rail name, and suffix.
            fname  = f"{filename_prefix}_{ch_cfg.name}_{suffix}.png"
            # Capture the screenshot from the oscilloscope and save it to the screenshots folder; the scope is already stopped so freeze_acquisition is not needed.
            path   = self._scope.capture_screenshot(
                # Pass the constructed filename so the image is saved with the correct descriptive name.
                filename=fname, freeze_acquisition=False
            )
            # If the screenshot was saved successfully, log the path and print a short confirmation message.
            if path:
                # Write the saved file path to the test log.
                self._logger.info(f"Screenshot saved: {path}")
                # Print a short message to the terminal confirming which file was saved.
                print(f"  Saved: screenshots/{fname}")
            # Return the file path of the saved screenshot (or None if the capture failed) to the caller.
            return path
        # If any exception occurs during marker placement or screenshot capture, log it and return None rather than crashing.
        except Exception as e:
            # Log the error at ERROR level, including the rail name and the exception details.
            self._logger.error(f"Cursor/screenshot error for {ch_cfg.name}: {e}")
            # Return None to indicate the screenshot was not saved.
            return None
        # The 'finally' block runs whether or not an exception occurred — used here to clear the markers so they do not appear on the next rail's screenshot.
        finally:
            # This comment explains why the markers must always be cleared after each screenshot.
            # Clear markers so they do not bleed into the next rail's screenshot
            # Attempt to turn off the markers — this runs even if an exception was raised above.
            try:
                # Turn the marker mode off to clear all markers from the scope display.
                self._scope.set_marker_mode("OFF")
            # If turning off markers fails, silently ignore it — the test can still continue.
            except Exception:
                # No action needed; marker clearing failure is not critical.
                pass

    # Define the '_capture_full_screenshot' method — this method captures a screenshot of the entire oscilloscope display (all four channels, no cursors) and saves it with the given filename.
    def _capture_full_screenshot(self, filename: str) -> Optional[str]:
        # This docstring briefly explains the method's purpose.
        """Save a full four-channel waveform screenshot (no cursors)."""
        # Begin a protected block for the screenshot capture.
        try:
            # Request the oscilloscope to capture and save the full display as an image with the given filename.
            path = self._scope.capture_screenshot(filename=filename, freeze_acquisition=False)
            # If the screenshot was saved successfully, print a short confirmation message.
            if path:
                # Tell the operator which file was saved.
                print(f"  Saved: screenshots/{filename}")
            # Return the file path of the saved screenshot to the caller.
            return path
        # If the screenshot capture fails for any reason, log the error and return None.
        except Exception as e:
            # Log the error at ERROR level with the exception details.
            self._logger.error(f"Full screenshot error: {e}")
            # Return None to indicate the screenshot could not be saved.
            return None

    # This comment marks a group of methods responsible for running the measurement loop over all channels in one capture configuration.
    # ─────────────────────────────────────────────────────────────
    # Per-configuration measurement loop
    # ─────────────────────────────────────────────────────────────

    # Define the '_measure_channels' method — this method processes each oscilloscope channel one at a time: it extracts the 90% rise time from the stored waveform, places markers and takes a screenshot, and builds a pass/fail result object for each rail.
    def _measure_channels(self, channels: List[ScopeChannelConfig],
                          config_label: str, screenshot_prefix: str) -> List[RailTimingResult]:
        # This docstring describes all four steps the method performs for each channel and notes when the screenshot is taken regardless of whether the threshold was reached.
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
        # Create an empty list to accumulate the result object for each rail as the loop processes them.
        results: List[RailTimingResult] = []

        # Print a blank line for spacing, then a section banner identifying which configuration is being measured.
        print()
        # Print a banner showing the configuration label (e.g. "Config 1 : Rail Ramp Timing Measurements").
        print(f"  -- {config_label} : Rail Ramp Timing Measurements ------------------")
        # Print the column headers for the results table that will be printed to the terminal.
        print(f"  {'Rail':<10} {'TP':<6} {'90% (V)':<10} {'Time (ms)':<14} {'Limit (ms)':<13} {'Status'}")
        # Print a horizontal separator line under the column headers.
        print("  " + "-" * 62)

        # Loop through each channel configuration in the list, processing one rail at a time.
        for ch_cfg in channels:
            # Store the rail name in a local variable for cleaner code.
            rail_name = ch_cfg.name
            # Store the nominal voltage for this rail in a local variable.
            nominal_v = ch_cfg.nominal_v
            # Store the pre-calculated 90% threshold voltage for this rail.
            threshold = ch_cfg.threshold_90pct_v
            # Look up the timing limit for this rail in the limits dictionary; if none is defined, limit_ms will be None.
            limit_ms  = self._limits.get(rail_name, {}).get("max_time_ms", None)

            # This comment marks the first sub-step: extracting the 90% crossing time from the waveform.
            # ── 1. Waveform analysis ──────────────────────────────────────────
            # Call the waveform analysis method to find the time (in seconds) when this rail reached 90% of its target voltage.
            t_90_s = self._extract_90pct_time(ch_cfg.channel, nominal_v)

            # This comment marks the second and third sub-steps combined: placing cursors and taking a screenshot.
            # ── 2+3. Cursor placement + screenshot (always, for every rail) ───
            # Tell the operator which rail is being processed and which channel it is on.
            print(f"  Placing cursors for {rail_name} (CH{ch_cfg.channel})...")
            # Call the cursor and screenshot method — this runs for every rail regardless of whether the 90% time was found.
            self._place_cursors_and_screenshot(ch_cfg, t_90_s, screenshot_prefix)

            # [Blank line for visual separation between sections]

            # This comment marks the fourth sub-step: building the result object with a PASS, FAIL, or ERROR verdict.
            # ── 4. Build result ───────────────────────────────────────────────
            # If the 90% crossing time was not found (waveform did not reach threshold), record the result as ERROR.
            if t_90_s is None:
                # Set the status to ERROR because the measurement could not be completed.
                status   = "ERROR"
                # Use "N/A" as the display string for the measured time since no valid time was found.
                t_ms_str = "N/A"
                # Store None as the measured time in milliseconds since the threshold was not reached.
                measured_ms = None
            # If the 90% crossing time was successfully measured, determine PASS or FAIL based on the timing limit.
            else:
                # Convert the measured time from seconds to milliseconds and round to 3 decimal places.
                t_ms        = round(t_90_s * 1e3, 3)
                # Store the measured time in milliseconds for inclusion in the result object.
                measured_ms = t_ms
                # If no timing limit is defined for this rail, it always passes (the measurement is recorded for information only).
                if limit_ms is None:
                    status = "PASS"   # no limit defined → informational only
                # If a timing limit is defined, compare the measured time to it and assign PASS or FAIL.
                else:
                    # PASS if measured time is within the limit; FAIL if it exceeds the limit.
                    status = "PASS" if t_ms <= limit_ms else "FAIL"
                # Format the measured time as a string with 3 decimal places for display in the results table.
                t_ms_str = f"{t_ms:.3f}"

            # Create a RailTimingResult object with all the collected data for this rail and add it to the results list.
            results.append(RailTimingResult(
                # Store the rail name in the result.
                rail_name=rail_name, test_point=ch_cfg.test_point,
                # Store the nominal and threshold voltages in the result.
                nominal_v=nominal_v, threshold_90pct_v=threshold,
                # Store the measured time in milliseconds (or None if not measured).
                measured_time_ms=measured_ms,
                # Store the timing limit — use infinity if no limit was defined so comparisons remain valid.
                max_time_ms=limit_ms if limit_ms else float('inf'),
                # Store the pass/fail/error verdict.
                status=status, config_label=config_label
            ))

            # Format the timing limit as a string with one decimal place, or "—" if no limit is defined.
            limit_str = f"{limit_ms:.1f}" if limit_ms else "—"
            # Print a results table row showing all key values for this rail in a neatly aligned format.
            print(f"  {rail_name:<10} {ch_cfg.test_point:<6} {threshold:<10.3f} {t_ms_str:<14} {limit_str:<13} {status}")

        # Print a closing horizontal separator line to complete the results table.
        print("  " + "-" * 62)
        # Return the list of result objects (one per channel) to the caller for report generation.
        return results

    # This comment marks a group of methods that display step-by-step instructions to the operator and prompt them to confirm before the test continues.
    # ─────────────────────────────────────────────────────────────
    # Operator prompts
    # ─────────────────────────────────────────────────────────────

    # Define the '_prompt_scope_config_1' method — this method displays a step-by-step instruction panel telling the operator exactly which oscilloscope probes to connect to which test points for the Config 1 measurement, then waits for the operator to press ENTER before continuing.
    def _prompt_scope_config_1(self):
        # Print a blank line for visual separation.
        print()
        # Print a visual box border to draw the operator's attention to the instruction panel.
        print("  " + "=" * 58)
        # Print the title of the instruction panel indicating which config is being set up and that action is required.
        print("  SCOPE SETUP — CONFIG 1   (ACTION REQUIRED)")
        # Print the closing border of the title box.
        print("  " + "=" * 58)
        # Print a blank line for visual separation inside the panel.
        print()
        # Print the header for the probe connection instructions.
        print("  Connect oscilloscope probes:")
        # Instruct the operator to connect Channel 1 to the 1V0PL rail at test point TP8 — this is the trigger channel.
        print("    CH1  →  1V0PL  (TP8)    [trigger channel]")
        # Instruct the operator to connect Channel 2 to the 1V8 rail at test point TP6.
        print("    CH2  →  1V8    (TP6)")
        # Instruct the operator to connect Channel 3 to the 1V0PS rail at test point TP5.
        print("    CH3  →  1V0PS  (TP5)")
        # Instruct the operator to connect Channel 4 to the 1V35 rail at test point TP7.
        print("    CH4  →  1V35   (TP7)")
        # Print a blank line.
        print()
        # Remind the operator to connect the DMM probes so they can confirm the 3V6 rail voltage after this capture.
        print("  Connect DMM probes to 3V6 output to confirm voltage.")
        # Print a blank line.
        print()
        # State the timebase and pre-trigger settings that will be applied automatically.
        print("  Timebase : 1 ms/div   Pre-trigger : 20%")
        # State the trigger settings that will be applied automatically: rising edge on CH1 at 20% of 1 V.
        print("  Trigger  : Rising edge on CH1 at 20% of 1 V (= 0.20 V)")
        # Print a blank line.
        print()
        # Wait for the operator to press ENTER — the test will not proceed until the operator has confirmed the probes are in place.
        input("  Press ENTER when all probes are connected and ready... ")
        # Print a blank line after the prompt.
        print()

    # Define the '_prompt_scope_config_2' method — this method displays instructions telling the operator to move the oscilloscope probes to the Config 2 test points (higher-voltage rails), then waits for the operator to confirm before continuing.
    def _prompt_scope_config_2(self):
        # Print a blank line for visual separation.
        print()
        # Print a visual box border to draw the operator's attention to the instruction panel.
        print("  " + "=" * 58)
        # Print the title of the instruction panel indicating Config 2 setup is required.
        print("  SCOPE SETUP — CONFIG 2   (ACTION REQUIRED)")
        # Print the closing border of the title box.
        print("  " + "=" * 58)
        # Print a blank line for visual separation inside the panel.
        print()
        # Tell the operator to move (reconnect) the probes to the Config 2 test points.
        print("  Reconnect oscilloscope probes:")
        # Instruct the operator to move Channel 1 to the 2V5 rail at TP9 — this is the trigger channel for Config 2.
        print("    CH1  →  2V5    (TP9)    [trigger channel]")
        # Instruct the operator to move Channel 2 to the 1V8 rail at TP6.
        print("    CH2  →  1V8    (TP6)")
        # Instruct the operator to move Channel 3 to the 3V3 rail at TP10.
        print("    CH3  →  3V3    (TP10)")
        # Instruct the operator to move Channel 4 to the 1V35 rail at TP7.
        print("    CH4  →  1V35   (TP7)")
        # Print a blank line.
        print()
        # State the timebase and pre-trigger settings for Config 2.
        print("  Timebase : 1 ms/div   Pre-trigger : 20%")
        # State the trigger settings for Config 2: rising edge on CH1 at 20% of 2.5 V = 0.50 V.
        print("  Trigger  : Rising edge on CH1 at 20% of 2.5 V (= 0.50 V)")
        # Print a blank line.
        print()
        # Wait for the operator to press ENTER confirming all probes have been reconnected.
        input("  Press ENTER when all probes are reconnected and ready... ")
        # Print a blank line after the prompt.
        print()

    # Define the '_prompt_dmm_3v6' method — this method displays the expected voltage range for the 3V6 rail, asks the operator to read their multimeter and type in the measured value, then evaluates and prints whether it is within the acceptable tolerance.
    def _prompt_dmm_3v6(self) -> str:
        # This docstring explains the method's purpose.
        """Prompt operator to read DMM and enter the 3V6 measurement."""
        # Read the expected 3V6 voltage from the DMM config section; default to 3.6 V if not specified.
        expected = self._dmm_3v6_cfg.get("expected_v", 3.6)
        # Read the allowed tolerance (plus or minus) from the DMM config section; default to ±0.1 V.
        tol      = self._dmm_3v6_cfg.get("tolerance_v", 0.1)
        # Print a blank line for visual separation.
        print()
        # Display the acceptable voltage range to the operator so they know what counts as a pass.
        print(f"  DMM check: confirm 3V6 rail is in range {expected - tol:.2f} V – {expected + tol:.2f} V")
        # Prompt the operator to type in the voltage reading from their multimeter and press ENTER.
        raw = input("  Enter DMM reading (V) and press ENTER: ").strip()
        # Attempt to convert the operator's input to a floating-point number for comparison.
        try:
            # Parse the entered text as a decimal number representing the measured voltage.
            v = float(raw)
            # Determine whether the measured voltage is within the allowed tolerance of the expected value.
            result = "PASS" if abs(v - expected) <= tol else "FAIL"
            # Print the measured value and the pass/fail verdict.
            print(f"  3V6 DMM: {v:.4f} V  →  {result}")
            # Return the raw input string so it can be stored in the reports exactly as the operator entered it.
            return raw
        # If the operator entered something that cannot be converted to a number, handle it gracefully.
        except ValueError:
            # Warn the operator that the entry could not be parsed but will be recorded as-is.
            print("  WARNING: Could not parse DMM reading — recorded as entered.")
            # Return the unparsed string so it is still recorded in the report.
            return raw

    # This comment marks a group of methods responsible for writing all test results to CSV, JSON, and text report files.
    # ─────────────────────────────────────────────────────────────
    # Report generation  (CSV + JSON + TXT in reports/ subdir)
    # ─────────────────────────────────────────────────────────────

    # Define the '_generate_reports' method — this method takes the complete list of rail results and the DMM reading, then writes three report files (CSV spreadsheet, JSON data file, and plain-text summary) into the reports sub-folder, and returns the overall PASS or FAIL verdict.
    def _generate_reports(self, all_results: List[RailTimingResult],
                          dmm_3v6_reading: str) -> str:
        # This docstring lists the three files that will be written and states that the method returns the overall verdict.
        """
        Generate three report files in reports/:
          - power_sequencing_results_TIMESTAMP.csv
          - power_sequencing_results_TIMESTAMP.json
          - power_sequencing_summary_TIMESTAMP.txt
        Returns the overall verdict string ("PASS" / "FAIL").
        """
        # Record the exact date and time when report generation started — used as the test end time in the reports.
        self._test_end_time = datetime.datetime.now()
        # Retrieve the timestamp string that was created during initialisation to use in file names.
        ts = self._timestamp

        # Check whether every single rail result has a "PASS" status — if any is FAIL or ERROR, the overall result is FAIL.
        all_pass = all(r.status == "PASS" for r in all_results)
        # Set the overall verdict to "PASS" if all rails passed, otherwise "FAIL".
        verdict  = "PASS" if all_pass else "FAIL"

        # This comment marks the CSV report writing section.
        # ── CSV ───────────────────────────────────────────────────────────────
        # Build the file path for the CSV results file using the timestamp in the filename.
        csv_path = self._reports_dir / f"power_sequencing_results_{ts}.csv"
        # Open the CSV file for writing with UTF-8 encoding and no extra blank lines between rows (required for CSV on Windows).
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            # Create a CSV writer object that will format and write data rows.
            w = csv.writer(f)
            # Write the header row with descriptive column names.
            w.writerow(['Config', 'Rail', 'Test_Point', 'Nominal_V',
                        'Threshold_90pct_V', 'Measured_Time_ms', 'Max_Time_ms', 'Status'])
            # Loop through each rail result and write one data row per rail.
            for r in all_results:
                # Format the measured time as a 3-decimal string, or "N/A" if the measurement failed.
                t_str = f"{r.measured_time_ms:.3f}" if r.measured_time_ms is not None else "N/A"
                # Format the timing limit as a 1-decimal string, or "—" if no limit was defined.
                lim   = f"{r.max_time_ms:.1f}" if r.max_time_ms != float('inf') else "—"
                # Write the row for this rail with all relevant data fields.
                w.writerow([r.config_label, r.rail_name, r.test_point,
                             r.nominal_v, r.threshold_90pct_v, t_str, lim, r.status])
        # Log that the CSV file was successfully written, including its full path.
        self._logger.info(f"CSV report saved: {csv_path}")
        # Print a short confirmation message to the terminal showing just the filename.
        print(f"  Saved: reports/{csv_path.name}")

        # This comment marks the JSON report writing section.
        # ── JSON ──────────────────────────────────────────────────────────────
        # Build the file path for the JSON results file using the timestamp in the filename.
        json_path = self._reports_dir / f"power_sequencing_results_{ts}.json"
        # Calculate the total test duration in seconds.
        duration  = (self._test_end_time - self._test_start_time).total_seconds()
        # Build the complete data structure that will be written to the JSON file.
        report_data = {
            # The 'test_info' section contains metadata about the test run itself.
            'test_info': {
                # Store the name of the test for identification.
                'test_name':       'Power Sequencing Test',
                # Store the ISO-formatted start time.
                'start_time':      self._test_start_time.isoformat(),
                # Store the ISO-formatted end time.
                'end_time':        self._test_end_time.isoformat(),
                # Store the rounded test duration in seconds.
                'duration_seconds': round(duration, 1),
                # Store the VISA address of the power supply used.
                'psu_address':     self._psu_address,
                # Store the VISA address of the oscilloscope used.
                'scope_address':   self._scope_address,
                # Store the PSU channel number used.
                'psu_channel':     self._psu_channel,
                # Store the input voltage applied to the DUT.
                'vin_v':           self._vin_v,
                # Store the timebase setting in milliseconds per division.
                'timebase_ms_per_div': self._timebase_s * 1e3,
                # Store the pre-trigger percentage setting.
                'pretrigger_pct':  self._pretrigger_pct,
                # Store the DMM reading entered by the operator.
                'dmm_3v6_reading': dmm_3v6_reading,
            },
            # The 'rail_results' section contains a list of dictionaries, one per rail.
            'rail_results':   [r.to_dict() for r in all_results],
            # The 'overall_result' field contains the top-level PASS or FAIL verdict.
            'overall_result': verdict,
        }
        # Open the JSON file for writing with UTF-8 encoding.
        with open(json_path, 'w', encoding='utf-8') as f:
            # Write the report data dictionary to the file as formatted JSON with 2-space indentation for readability.
            json.dump(report_data, f, indent=2)
        # Log that the JSON file was successfully written.
        self._logger.info(f"JSON report saved: {json_path}")
        # Print a short confirmation message to the terminal.
        print(f"  Saved: reports/{json_path.name}")

        # This comment marks the plain-text summary report writing section.
        # ── TXT summary ───────────────────────────────────────────────────────
        # Build the file path for the plain-text summary file using the timestamp in the filename.
        txt_path = self._reports_dir / f"power_sequencing_summary_{ts}.txt"
        # Open the text file for writing with UTF-8 encoding.
        with open(txt_path, 'w', encoding='utf-8') as f:
            # Create a short alias '_w' for the file write method to reduce repetition in the lines below.
            _w = f.write
            # Write the top border of the summary report.
            _w("=" * 70 + "\n")
            # Write the report title.
            _w("  POWER SEQUENCING TEST — RESULTS SUMMARY\n")
            # Write the bottom border of the title section.
            _w("=" * 70 + "\n")
            # Write the test start date and time.
            _w(f"  Date / Time    : {self._test_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            # Write the VISA address of the power supply.
            _w(f"  PSU Address    : {self._psu_address}\n")
            # Write the VISA address of the oscilloscope.
            _w(f"  Scope Address  : {self._scope_address}\n")
            # Write the PSU channel and voltage setting.
            _w(f"  PSU Channel    : CH{self._psu_channel}  ({self._vin_v} V)\n")
            # Write the timebase and pre-trigger settings.
            _w(f"  Timebase       : {self._timebase_s * 1e3:.0f} ms/div  |  Pre-trigger: {self._pretrigger_pct}%\n")
            # Write the DMM reading entered by the operator.
            _w(f"  3V6 DMM check  : {dmm_3v6_reading} V\n")
            # Write a section separator line followed by a blank line.
            _w("=" * 70 + "\n\n")

            # Write the section heading for the measurements table.
            _w("  Rail Ramp Timing Measurements\n")
            # Write a note explaining what T=0 means in the context of these measurements.
            _w("  (T = 0 when 5 V input begins rising, i.e. scope trigger event)\n\n")
            # Write the top border of the measurements table.
            _w("  " + "-" * 65 + "\n")
            # Write the column header row for the measurements table.
            _w(f"  {'Rail':<10} {'TP':<6} {'90% V':<10} {'Measured (ms)':<16} {'Limit (ms)':<13} {'Status'}\n")
            # Write the separator line under the column headers.
            _w("  " + "-" * 65 + "\n")
            # Loop through each rail result and write one formatted row per rail.
            for r in all_results:
                # Format the measured time as a 3-decimal string, or "N/A" if the measurement failed.
                t_str   = f"{r.measured_time_ms:.3f}" if r.measured_time_ms is not None else "N/A"
                # Format the timing limit as a 1-decimal string, or "—" if no limit was defined.
                lim_str = f"{r.max_time_ms:.1f}" if r.max_time_ms != float('inf') else "—"
                # Write the data row for this rail.
                _w(f"  {r.rail_name:<10} {r.test_point:<6} {r.threshold_90pct_v:<10.3f} {t_str:<16} {lim_str:<13} {r.status}\n")
            # Write the closing border of the measurements table followed by a blank line.
            _w("  " + "-" * 65 + "\n\n")

            # Write the section header for the Config 1 channel details.
            _w("  Scope Configuration 1:\n")
            # Loop through each Config 1 channel and write its details (channel number, rail name, test point, nominal voltage, 90% threshold).
            for ch in self.CONFIG1_CHANNELS:
                # Write a summary line for this channel.
                _w(f"    CH{ch.channel}: {ch.name:<8} ({ch.test_point})  nominal={ch.nominal_v} V  90%={ch.threshold_90pct_v:.3f} V\n")
            # Write the section header for the Config 2 channel details, preceded by a blank line.
            _w("\n  Scope Configuration 2:\n")
            # Loop through each Config 2 channel and write its details.
            for ch in self.CONFIG2_CHANNELS:
                # Write a summary line for this channel.
                _w(f"    CH{ch.channel}: {ch.name:<8} ({ch.test_point})  nominal={ch.nominal_v} V  90%={ch.threshold_90pct_v:.3f} V\n")

            # Write the final section of the summary: the overall result.
            _w("\n" + "=" * 70 + "\n")
            # Write the overall PASS or FAIL verdict prominently.
            _w(f"  OVERALL RESULT : {verdict}\n")
            # Write the closing border.
            _w("=" * 70 + "\n")

        # Log that the text summary file was successfully written.
        self._logger.info(f"Summary saved: {txt_path}")
        # Print a short confirmation message to the terminal.
        print(f"  Saved: reports/{txt_path.name}")

        # Return the overall verdict string ("PASS" or "FAIL") to the caller.
        return verdict

    # This comment marks a group of methods that run each measurement configuration as a complete phase (configure scope, capture, analyse, screenshot).
    # ─────────────────────────────────────────────────────────────
    # Per-configuration phase runners
    # ─────────────────────────────────────────────────────────────

    # Define the '_run_config1_phase' method — this method runs the complete Config 1 measurement phase: it prompts the operator to connect the probes, configures the oscilloscope, optionally power-cycles the DUT and captures a waveform, saves a full screenshot, and optionally runs the full channel-by-channel analysis.
    def _run_config1_phase(self, skip_capture: bool = False,
                           capture_only: bool = False) -> List[RailTimingResult]:
        # This docstring explains what the two optional flags do and what the method returns.
        """
        Execute the Config 1 measurement phase.

        Args:
            skip_capture : If True, skip the PSU power-cycle and scope arm step
                           (scope must already be in STOP with a valid waveform).
            capture_only : If True, take a full screenshot but skip cursor analysis.

        Returns list of RailTimingResult (empty if capture_only=True).
        """
        # Display the Config 1 probe connection instructions and wait for the operator to press ENTER.
        self._prompt_scope_config_1()

        # Configure the oscilloscope with the Config 1 channel settings and trigger — raise an error if this fails.
        if not self._configure_scope(self.CONFIG1_CHANNELS, self._cfg1_trigger_ch):
            # Raise a RuntimeError to propagate the failure up to the run() method where it will be caught.
            raise RuntimeError("Config 1 scope configuration failed")

        # If 'skip_capture' is False (the normal case), perform the power-cycle and wait for the scope to trigger.
        if not skip_capture:
            # Arm the scope, turn on the PSU, and wait for the scope to trigger on the rising power rail.
            if not self._arm_and_capture():
                # Raise a RuntimeError if the scope did not trigger within the allowed time.
                raise RuntimeError("Config 1 capture failed — scope did not trigger")

        # Save a full screenshot of all four channels (no cursors) as the Config 1 overview image.
        self._capture_full_screenshot("config1_full.png")

        # If 'capture_only' is True (no analysis requested), return an empty list and stop here.
        if capture_only:
            # Return an empty list because no rail timing results were generated in capture-only mode.
            return []

        # Run the full channel-by-channel analysis: extract 90% times, place cursors, take screenshots, and build result objects.
        results = self._measure_channels(self.CONFIG1_CHANNELS, "Config 1", "config1")
        # Return the list of result objects (one per channel) to the caller.
        return results

    # Define the '_run_config2_phase' method — this method runs the complete Config 2 measurement phase (higher-voltage rails): it prompts the operator to reconnect the probes, configures the oscilloscope for Config 2, optionally power-cycles and captures, saves a full screenshot, and optionally runs the full channel analysis.
    def _run_config2_phase(self, skip_capture: bool = False,
                           capture_only: bool = False) -> List[RailTimingResult]:
        # This docstring explains the two optional flags and what the method returns.
        """
        Execute the Config 2 measurement phase.

        Args:
            skip_capture : If True, skip the PSU power-cycle and scope arm step.
            capture_only : If True, take a full screenshot but skip cursor analysis.

        Returns list of RailTimingResult (empty if capture_only=True).
        """
        # Display the Config 2 probe reconnection instructions and wait for the operator to press ENTER.
        self._prompt_scope_config_2()

        # Configure the oscilloscope with the Config 2 channel settings and trigger — raise an error if this fails.
        if not self._configure_scope(self.CONFIG2_CHANNELS, self._cfg2_trigger_ch):
            # Raise a RuntimeError to propagate the failure up to the run() method where it will be caught.
            raise RuntimeError("Config 2 scope configuration failed")

        # If 'skip_capture' is False (the normal case), perform the power-cycle and wait for the scope to trigger.
        if not skip_capture:
            # Arm the scope, turn on the PSU, and wait for the scope to trigger on the rising power rail.
            if not self._arm_and_capture():
                # Raise a RuntimeError if the scope did not trigger within the allowed time.
                raise RuntimeError("Config 2 capture failed — scope did not trigger")

        # Save a full screenshot of all four channels for the Config 2 overview image.
        self._capture_full_screenshot("config2_full.png")

        # If 'capture_only' is True, return an empty list without running analysis.
        if capture_only:
            # Return an empty list because no rail timing results were generated in capture-only mode.
            return []

        # Run the full channel-by-channel analysis for the Config 2 rails.
        results = self._measure_channels(self.CONFIG2_CHANNELS, "Config 2", "config2")
        # Return the list of result objects to the caller.
        return results

    # Define the '_prompt_reanalyze_config_select' method — this method asks the operator which oscilloscope configuration is currently connected (Config 1 or Config 2) when running in re-analyse mode (where the scope already has a waveform and no new power cycle is needed).
    def _prompt_reanalyze_config_select(self) -> str:
        # This docstring explains the purpose of the prompt and lists the possible return values.
        """
        Ask which scope configuration is currently connected when running in
        re-analyse mode (no power cycle, operator chose which probes are on board).

        Returns "config1", "config2", or "both".
        """
        # Print a blank line for visual separation.
        print()
        # Print the top border of the selection panel.
        print("  " + "=" * 58)
        # Print the title of the panel.
        print("  RE-ANALYSE MODE — Which config is currently connected?")
        # Print the closing border of the title.
        print("  " + "=" * 58)
        # Print a blank line.
        print()
        # Show option 1: Config 1 channel assignment (lower voltage rails).
        print("    [1]  Config 1  —  CH1:1V0PL(TP8)  CH2:1V8(TP6)")
        # Continue the description of Config 1 on the second line.
        print("                      CH3:1V0PS(TP5)   CH4:1V35(TP7)")
        # Print a blank line between options.
        print()
        # Show option 2: Config 2 channel assignment (higher voltage rails).
        print("    [2]  Config 2  —  CH1:2V5(TP9)    CH2:1V8(TP6)")
        # Continue the description of Config 2 on the second line.
        print("                      CH3:3V3(TP10)    CH4:1V35(TP7)")
        # Print a blank line.
        print()
        # Keep asking until a valid choice is made.
        while True:
            # Prompt the operator to type 1 or 2 and press ENTER.
            choice = input("  Enter 1 or 2: ").strip()
            # If the operator chose 1, select Config 1 and return.
            if choice == "1":
                # Confirm the selection.
                print("  Analysing Config 1 channels.")
                # Return the string "config1" to the caller.
                return "config1"
            # If the operator chose 2, select Config 2 and return.
            elif choice == "2":
                # Confirm the selection.
                print("  Analysing Config 2 channels.")
                # Return the string "config2" to the caller.
                return "config2"
            # If neither 1 nor 2 was entered, ask again.
            else:
                # Tell the operator their input was invalid.
                print("  Invalid — enter 1 or 2.")

    # This comment marks the group of methods responsible for asking the operator whether to keep or delete the result files.
    # ─────────────────────────────────────────────────────────────
    # Save / discard prompt
    # ─────────────────────────────────────────────────────────────

    # Define the '_prompt_save_results' method — this method asks the operator whether they want to keep the run folder containing all logs, screenshots, and reports; if they answer 'no', the entire folder is permanently deleted.
    def _prompt_save_results(self):
        # This docstring explains the two outcomes: keep the folder or delete it.
        """
        Ask the operator whether to keep the run folder.
        If they answer 'no', the entire run directory is deleted.
        """
        # Print a blank line for visual separation.
        print()
        # Print a horizontal separator line to visually separate this prompt from other output.
        print("  " + "─" * 54)
        # Keep asking until a valid Y or N answer is given.
        while True:
            # Ask the operator to confirm whether results should be saved; ENTER or 'Y' means yes, 'N' means discard.
            choice = input("  Save results? [Y/n]: ").strip().lower()
            # If the operator pressed ENTER (empty input), typed 'y', or typed 'yes', keep the results.
            if choice in ("", "y", "yes"):
                # Print the path of the saved run folder so the operator knows where to find the files.
                print(f"  Results saved in: {self._run_dir}")
                # Print a blank line.
                print()
                # Exit the method — results are saved.
                return
            # If the operator typed 'n' or 'no', delete the run folder.
            elif choice in ("n", "no"):
                # Attempt to delete the entire run folder and all its contents.
                try:
                    # Recursively delete the run folder using shutil.rmtree.
                    shutil.rmtree(self._run_dir)
                    # Confirm that the folder was successfully deleted.
                    print(f"  Run folder deleted: {self._run_dir}")
                # If deletion fails (e.g. a file is locked by OneDrive), catch the error and warn the operator.
                except Exception as e:
                    # Warn the operator that the folder could not be deleted and show the error reason.
                    print(f"  WARNING: Could not delete run folder: {e}")
                # Print a blank line.
                print()
                # Exit the method.
                return
            # If neither a valid yes nor no was entered, ask again.
            else:
                # Tell the operator to enter Y or N.
                print("  Please enter Y or N.")

    # This comment marks the top-level entry point method that orchestrates the entire test sequence based on the selected mode.
    # ─────────────────────────────────────────────────────────────
    # Top-level entry point
    # ─────────────────────────────────────────────────────────────

    # Define the 'run' method — this is the main entry point for executing the test; the caller passes a mode string to select which rails to test and whether to power-cycle or only re-analyse, and the method returns True if all rails passed or False if any failed or an error occurred.
    def run(self, mode: str = "full") -> bool:
        # This docstring lists all five valid modes with a plain description of each, and states what the return value means.
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
        # Print a blank line for visual separation before the run starts.
        print()
        # Print the selected mode so the operator can confirm the correct mode is running.
        print(f"  Mode          : {mode}")
        # Print the absolute path of the run folder where all results will be saved.
        print(f"  Run directory : {self._run_dir.resolve()}")

        # Begin the main protected block — catches keyboard interrupts (Ctrl+C) and unexpected runtime errors separately.
        try:
            # Attempt to connect to both instruments; if this fails, return False immediately without running any test steps.
            if not self._connect_instruments():
                # Return False to indicate the test could not start because instruments could not be connected.
                return False

            # Create an empty list to collect all rail timing results as each configuration phase is completed.
            all_results: List[RailTimingResult] = []
            # Set the DMM reading to "N/A" by default; it will be updated if the selected mode includes a 3V6 DMM check.
            dmm_3v6_reading = "N/A"

            # This comment marks the branch for the 'full' mode: run both Config 1 and Config 2 with 2 power cycles.
            # ── FULL ──────────────────────────────────────────────────────────
            # If the selected mode is "full", run both measurement configurations in sequence.
            if mode == "full":
                # Run the Config 1 phase (lower voltage rails: 1V0PL, 1V8, 1V0PS, 1V35) and collect the results.
                results_1 = self._run_config1_phase()
                # Add the Config 1 results to the combined results list.
                all_results.extend(results_1)
                # After Config 1 is complete, prompt the operator to enter the DMM reading for the 3V6 rail.
                dmm_3v6_reading = self._prompt_dmm_3v6()
                # Run the Config 2 phase (higher voltage rails: 2V5, 1V8, 3V3, 1V35) after the operator has moved the probes.
                results_2 = self._run_config2_phase()
                # Add the Config 2 results to the combined results list.
                all_results.extend(results_2)

            # This comment marks the branch for the 'config1' mode: run only Config 1 with 1 power cycle.
            # ── CONFIG 1 ONLY ─────────────────────────────────────────────────
            # If the selected mode is "config1", run only the Config 1 phase.
            elif mode == "config1":
                # Run the Config 1 phase and collect the results.
                results_1 = self._run_config1_phase()
                # Add the Config 1 results to the combined results list.
                all_results.extend(results_1)
                # Prompt the operator to enter the DMM reading for the 3V6 rail after Config 1 is complete.
                dmm_3v6_reading = self._prompt_dmm_3v6()

            # This comment marks the branch for the 'config2' mode: run only Config 2 with 1 power cycle.
            # ── CONFIG 2 ONLY ─────────────────────────────────────────────────
            # If the selected mode is "config2", run only the Config 2 phase.
            elif mode == "config2":
                # Run the Config 2 phase and collect the results.
                results_2 = self._run_config2_phase()
                # Add the Config 2 results to the combined results list.
                all_results.extend(results_2)

            # This comment marks the branch for the 'capture' mode: take screenshots only without any waveform analysis.
            # ── CAPTURE ONLY ──────────────────────────────────────────────────
            # If the selected mode is "capture", run both configuration phases but skip cursor analysis — only save full screenshots.
            elif mode == "capture":
                # Run Config 1 in capture-only mode — power-cycles the DUT and saves a full screenshot, no analysis.
                self._run_config1_phase(capture_only=True)
                # Run Config 2 in capture-only mode — power-cycles the DUT again and saves a full screenshot.
                self._run_config2_phase(capture_only=True)
                # Print a blank line for spacing.
                print()
                # Inform the operator that the capture phase is complete and no analysis was performed.
                print("  Capture complete — screenshots saved, no analysis performed.")
                # Show the operator where the screenshots were saved.
                print(f"  Run folder : {self._run_dir}")
                # Ask the operator whether to keep or discard the run folder.
                self._prompt_save_results()
                # Return True because capture-only mode has no pass/fail criteria.
                return True   # nothing to PASS/FAIL in capture-only mode

            # This comment marks the branch for the 're-analyse' mode: re-run analysis on an existing scope waveform without a new power cycle.
            # ── RE-ANALYSE ────────────────────────────────────────────────────
            # If the selected mode is "reanalyze", skip the power-cycle step and analyse the waveform currently stored in the scope.
            elif mode == "reanalyze":
                # Ask the operator which configuration is currently connected to the oscilloscope.
                active = self._prompt_reanalyze_config_select()
                # If the operator indicated Config 1 is connected, run the Config 1 phase without a new power cycle.
                if active == "config1":
                    # Run Config 1 analysis only — skip_capture=True means no PSU output toggle or scope arming.
                    results_1 = self._run_config1_phase(skip_capture=True)
                    # Add the Config 1 results to the combined results list.
                    all_results.extend(results_1)
                    # Prompt the operator for the DMM reading.
                    dmm_3v6_reading = self._prompt_dmm_3v6()
                # If the operator indicated Config 2 is connected, run the Config 2 phase without a new power cycle.
                else:
                    # Run Config 2 analysis only — skip_capture=True means no PSU output toggle or scope arming.
                    results_2 = self._run_config2_phase(skip_capture=True)
                    # Add the Config 2 results to the combined results list.
                    all_results.extend(results_2)

            # This comment marks the fallback branch for any unrecognised mode string.
            else:
                # Print an error message identifying the unrecognised mode.
                print(f"  ERROR: Unknown mode '{mode}'")
                # Return False to indicate the test could not run because an invalid mode was specified.
                return False

            # This comment marks the report generation step that runs after all measurement phases are complete.
            # ── Reports ───────────────────────────────────────────────────────
            # Only generate reports if at least one rail result was collected (not in capture-only mode).
            if all_results:
                # Print a blank line for spacing.
                print()
                # Tell the operator that the report files are being written.
                print("  Writing reports...")
                # Call the report generation method, passing all results and the DMM reading; it returns the overall verdict.
                verdict = self._generate_reports(all_results, dmm_3v6_reading)
            # If no results were collected (e.g. capture-only mode somehow reached here), default to PASS.
            else:
                # No measurable results means no failures — default verdict is PASS.
                verdict = "PASS"

            # Print a blank line for spacing.
            print()
            # Print a visual border before the final verdict.
            print("  " + "=" * 54)
            # Print the overall PASS or FAIL verdict prominently.
            print(f"  OVERALL RESULT : {verdict}")
            # Print a visual border after the final verdict.
            print("  " + "=" * 54)
            # Print the location of the run folder for the operator's reference.
            print(f"  Run folder     : {self._run_dir}")
            # Ask the operator whether to save or discard the run folder.
            self._prompt_save_results()
            # Return True if the overall verdict is PASS, False if it is FAIL.
            return verdict == "PASS"

        # If the operator presses Ctrl+C to interrupt the test at any point, catch it here and handle it gracefully.
        except KeyboardInterrupt:
            # Print a message indicating the test was stopped by the operator.
            print("\n\n  Test interrupted by user.")
            # Ask the operator whether to save the partial results before exiting.
            self._prompt_save_results()
            # Return False because the test did not complete normally.
            return False

        # [Blank line for visual separation between sections]

        # If any other unexpected exception occurs during the test (e.g. an instrument communication error), catch it here.
        except Exception as e:
            # Log the full exception details (including stack trace) at ERROR level for diagnosis.
            self._logger.error(f"Unhandled exception: {e}", exc_info=True)
            # Print a brief error message to the terminal so the operator is aware.
            print(f"\n  ERROR: {e}")
            # Ask the operator whether to save the partial results before exiting.
            self._prompt_save_results()
            # Return False because the test did not complete successfully.
            return False

        # The 'finally' block always runs after the try/except, regardless of whether the test passed, failed, or raised an exception — used here to ensure instruments are always disconnected cleanly.
        finally:
            # Inform the operator that instruments are being disconnected.
            print("  Disconnecting instruments...")
            # Call the disconnect method to safely turn off the PSU output and close both VISA connections.
            self._disconnect_instruments()
