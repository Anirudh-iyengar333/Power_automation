# This line tells the operating system to run this file using Python 3, making it directly executable on Linux/macOS
#!/usr/bin/env python3
# This is the module-level documentation string (docstring) that describes the overall purpose of this file to any developer who opens it
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

# Load the 'sys' library, which provides access to the Python interpreter itself — used here to modify the module search path and exit the program cleanly on errors
import sys
# Load the 'csv' library, which allows the program to read and write comma-separated values files — used here to save test results in spreadsheet format
import csv
# Load the 'json' library, which allows the program to read and write JSON (structured text) files — used here to load the configuration file and save result reports
import json
# Load the 'time' library, which provides time-related functions such as pausing the program for a fixed number of seconds — used here to wait for the oscilloscope to settle
import time
# Load the 'logging' library, which provides a structured way to write timestamped messages to a log file — used here to record instrument events and errors
import logging
# Load the 'datetime' library, which provides tools to read the current date and time — used here to create timestamps for run folders and reports
import datetime
# Load the 'Path' class from the 'pathlib' library, which provides an easy and cross-platform way to work with file and folder paths — used throughout to build output directory paths
from pathlib import Path
# Load the 'dataclass' decorator from the 'dataclasses' library, which automatically generates standard methods (such as __init__) for simple data-holding classes — used here to define rail configuration and result records
from dataclasses import dataclass
# Load 'List' and 'Optional' type hints from the 'typing' library — these are used to describe what type of values a variable or function parameter is expected to hold, making the code easier to read and check
from typing import List, Optional

# Insert the parent folder of this file's directory at the front of Python's module search path, so that the shared 'instrument_control' package can be found and imported
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the oscilloscope driver class from the shared instrument control package — this class handles all communication with the Keysight DSOX6004A oscilloscope over VISA
from instrument_control.keysight_oscilloscope import KeysightDSOX6004A

# [Blank line for visual separation between sections]

# This line is a decorative section header (a comment-only banner) marking the start of the configuration loading section
# ═════════════════════════════════════════════════════════════════════════════
# CONFIG LOADING — reads steady_state_ripple_config.json once at startup
# ═════════════════════════════════════════════════════════════════════════════

# If the DIGANTARA_CONFIG environment variable is set (e.g. by the Gradio GUI launching this
# module via subprocess), use that path so the correct board config (CPU, SENSOR, IAP, …) is
# loaded without modifying this file.  If the variable is absent the default CPU config in the
# same folder is used, so the runner still works when invoked directly from the terminal.
import os as _os
_env_cfg = _os.environ.get("DIGANTARA_CONFIG")
_CONFIG_PATH = Path(_env_cfg) if _env_cfg else Path(__file__).parent / "CPU_config.json"

# [Blank line for visual separation between sections]

# Define a function called '_load_config' that reads the JSON configuration file from disk; it accepts an optional path argument (defaulting to the standard config location above) and returns the parsed settings as a Python dictionary
def _load_config(path: Path = _CONFIG_PATH) -> dict:
    # Attempt to open and read the JSON file; if anything goes wrong (missing file, bad formatting), the program will stop and display a helpful error message
    try:
        # Open the configuration file at the given path in read mode using UTF-8 character encoding, then parse its JSON content into a Python dictionary
        with open(path, "r", encoding="utf-8") as f:
            # Parse the file contents from JSON text format into a Python dictionary so the rest of the program can access the settings by name
            cfg = json.load(f)
        # Print a confirmation message to the console showing that the config file was found and loaded successfully
        print(f"Loaded config from {path.name}")
        # Return the dictionary of settings so that the rest of the program can use them
        return cfg
    # If the configuration file does not exist at the expected location, catch that error here
    except FileNotFoundError:
        # Display a clear error message telling the operator that the required config file is missing
        print(f"ERROR: Config file not found: {path}")
        # Provide additional guidance explaining where the file must be placed
        print(f"       {_CONFIG_PATH.name} is required in the same folder.")
        # Terminate the program immediately with exit code 1 (indicating failure) because the test cannot run without its configuration
        sys.exit(1)
    # If the file exists but its contents are not valid JSON (e.g., a typo in the file), catch that formatting error here
    except json.JSONDecodeError as e:
        # Display an error message including the specific JSON syntax problem that was detected
        print(f"ERROR: Config file has invalid JSON: {e}")
        # Instruct the operator to fix the config file before trying again
        print(f"       Fix {_CONFIG_PATH.name} before running the test.")
        # Terminate the program immediately because invalid configuration would cause unpredictable behaviour during the test
        sys.exit(1)

# [Blank line for visual separation between sections]

# Call the config loading function immediately when the module is first imported, so the settings are ready before any test objects are created; the result is stored in the module-level variable '_CFG'
_CFG = _load_config()

# [Blank line for visual separation between sections]

# This line is a decorative section header marking the start of the data structure definitions
# ═════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═════════════════════════════════════════════════════════════════════════════

# Apply the '@dataclass' decorator to the class below, which tells Python to automatically generate an __init__ constructor and other boilerplate methods so we only need to list the fields
@dataclass
# Define the 'RailConfig' class, which is a simple data container holding all the configuration parameters for one power rail that will be tested (such as its name, test point, voltage range, and ripple limit)
class RailConfig:
    # This docstring describes what instances of this class represent — each instance holds the settings for one specific power rail
    """Configuration for one power rail under test."""
    # The human-readable name of the power rail (e.g. "3V6", "1V8") — used in reports and on-screen messages
    name:            str
    # The physical label of the test point on the circuit board where the probe should be placed (e.g. "TP1")
    test_point:      str
    # The ideal (nominal) voltage that this rail is designed to output, in volts — used to centre the oscilloscope display
    nominal_v:       float
    # The lowest voltage the rail is allowed to measure and still pass — anything below this is a failure
    min_v:           float
    # The highest voltage the rail is allowed to measure and still pass — anything above this is a failure
    max_v:           float
    # The oscilloscope vertical scale (volts per division) to use during the DC voltage measurement phase for this rail
    dc_v_scale:      float
    # The maximum allowed peak-to-peak ripple voltage for this rail in millivolts; a value of None means this rail has no ripple specification and the ripple phase will be skipped
    ripple_max_mvpp: Optional[float]   # None = no ripple spec for this rail

    # Apply the '@classmethod' decorator, which means this method belongs to the class itself (not to an individual instance) and can be called without creating an object first
    @classmethod
    # Define a factory method called 'from_dict' that creates a new RailConfig object by reading values from a plain Python dictionary (such as one loaded from the JSON config file)
    def from_dict(cls, d: dict) -> 'RailConfig':
        # Call the class constructor with each required field extracted from the dictionary by name, then return the newly created RailConfig object
        return cls(
            # Read the rail name string from the dictionary
            name=d['name'],
            # Read the test point label string from the dictionary
            test_point=d['test_point'],
            # Read the nominal voltage floating-point value from the dictionary
            nominal_v=d['nominal_v'],
            # Read the minimum acceptable voltage from the dictionary
            min_v=d['min_v'],
            # Read the maximum acceptable voltage from the dictionary
            max_v=d['max_v'],
            # Read the DC vertical scale setting from the dictionary
            dc_v_scale=d['dc_v_scale'],
            # Read the ripple limit if it exists in the dictionary; if it is absent, store None (meaning no ripple spec)
            ripple_max_mvpp=d.get('ripple_max_mvpp'),
        )

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Apply the '@dataclass' decorator to the class below so Python automatically generates its constructor and comparison methods
@dataclass
# Define the 'RailResult' class, which is a data container that holds all the measurement results and pass/fail verdicts for one power rail after it has been tested
class RailResult:
    # This docstring describes what instances of this class represent — each instance stores the outcome of testing one power rail
    """Measurement result for one power rail."""
    # The name of the rail that was tested (copied from RailConfig for traceability in reports)
    name:                 str
    # The test point label on the board where the probe was placed (copied from RailConfig)
    test_point:           str
    # The nominal (ideal) voltage of the rail, copied from the configuration (used in reports)
    nominal_v:            float
    # The lower boundary of the acceptable voltage range (used when checking whether the measurement passed)
    min_v:                float
    # The upper boundary of the acceptable voltage range (used when checking whether the measurement passed)
    max_v:                float
    # The DC RMS voltage actually measured by the oscilloscope in volts; set to None if the instrument could not return a reading
    measured_dc_v:        Optional[float]   # DC RMS FS in V; None on instrument error
    # A string indicating whether the DC voltage measurement passed or failed: either "PASS", "FAIL", or "ERROR"
    dc_status:            str               # "PASS" | "FAIL" | "ERROR"
    # The maximum allowed peak-to-peak ripple for this rail in millivolts (copied from the config); None if no ripple spec exists
    ripple_max_mvpp:      Optional[float]
    # The peak-to-peak ripple actually measured by the oscilloscope in millivolts; None if the ripple phase was skipped or errored
    measured_ripple_mvpp: Optional[float]   # Vpp in mV; None if skipped or error
    # A string indicating whether the ripple measurement passed or failed: "PASS", "FAIL", "ERROR", or "N/A" (when no spec exists)
    ripple_status:        str               # "PASS" | "FAIL" | "ERROR" | "N/A"

    # Define a method called 'to_dict' that converts this result object into a plain Python dictionary so it can be written to CSV, JSON, or text report files
    def to_dict(self) -> dict:
        # Build and return a dictionary containing all measurement fields and results, formatting numbers for readability
        return {
            # The rail name used as a key in the output dictionary
            'rail_name':            self.name,
            # The test point label included for traceability
            'test_point':           self.test_point,
            # The nominal voltage value
            'nominal_v':            self.nominal_v,
            # The voltage acceptance range formatted as a readable string (e.g. "3.42–3.78V")
            'expected_range':       f"{self.min_v:.2f}–{self.max_v:.2f}V",
            # The measured DC voltage rounded to 4 decimal places, or None if no reading was obtained
            'measured_dc_v':        round(self.measured_dc_v, 4) if self.measured_dc_v is not None else None,
            # The DC pass/fail status string
            'dc_status':            self.dc_status,
            # The ripple specification limit in mVpp, or None if no spec exists
            'ripple_max_mvpp':      self.ripple_max_mvpp,
            # The measured ripple rounded to 1 decimal place, or None if not measured
            'measured_ripple_mvpp': round(self.measured_ripple_mvpp, 1) if self.measured_ripple_mvpp is not None else None,
            # The ripple pass/fail status string
            'ripple_status':        self.ripple_status,
        }

# [Blank line for visual separation between sections]

# This line is a decorative section header marking the start of the main test class definition
# ═════════════════════════════════════════════════════════════════════════════
# MAIN TEST CLASS
# ═════════════════════════════════════════════════════════════════════════════

# Define the 'SteadyStateRippleTest' class, which contains all the logic needed to connect to the oscilloscope, configure it correctly for each measurement phase, measure the DC voltage and ripple on each rail, save screenshots, and produce the final reports
class SteadyStateRippleTest:
    # This docstring explains how to use the class and describes the folder structure it creates when saving results
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

    # Define a class-level constant specifying that oscilloscope Channel 1 is always used for all measurements; Channels 2, 3, and 4 are disabled to keep the display clean
    SCOPE_CHANNEL = 1   # CH1 used for every measurement; CH2–4 disabled

    # Define a class-level list of all available rails loaded directly from the configuration file; this is accessible before any test instance is created, which allows the runner script to display the rail selector without creating a test object
    # All rails available from config — exposed so the runner can build the selector
    ALL_RAILS: List[RailConfig] = [
        # For each raw dictionary in the "rails" section of the config file, create a RailConfig object using the 'from_dict' factory method
        RailConfig.from_dict(r) for r in _CFG.get("rails", [])
    ]

    # Define the constructor method that runs when a new SteadyStateRippleTest object is created; it accepts the list of rails to test and an optional output directory path
    def __init__(self, rails: List[RailConfig], output_dir: str = None):
        # Record the exact date and time when this test object was created — this becomes the timestamp used for all output files and folders
        self._test_start_time = datetime.datetime.now()
        # Initialise the end-time field as None; it will be filled in when the test finishes, so the duration can be calculated
        self._test_end_time: Optional[datetime.datetime] = None
        # Store the list of RailConfig objects that the test will iterate through — only these rails will be measured
        self._rails = rails

        # This comment marks the start of the section that reads individual settings sections from the loaded config dictionary
        # ── Read config sections ──────────────────────────────────────────────
        # Extract the 'instrument_addresses' section from the config dictionary, which holds the VISA addresses needed to connect to the instruments; default to an empty dict if the section is absent
        instr   = _CFG.get("instrument_addresses", {})
        # Extract the 'scope_settings' section from the config dictionary, which holds all oscilloscope timing and measurement parameters
        scp_cfg = _CFG.get("scope_settings", {})

        # ── VISA auto-detection ───────────────────────────────────────────────
        # Try to auto-detect the oscilloscope on the VISA bus first.
        # Falls back to the config address if detection fails.
        _detected_scope_addr: Optional[str] = None
        try:
            from visa_auto_detect import detect_steady_state_ripple_instruments
            print("\nAuto-detecting instruments on VISA bus...")
            (_detected_scope_addr,) = detect_steady_state_ripple_instruments()
        except ImportError:
            pass  # visa_auto_detect not available — use config address

        self._scope_address = _detected_scope_addr if _detected_scope_addr else instr.get("scope")
        # Store the probe attenuation ratio (e.g. 1.0 for a 1:1 probe); this is sent to the oscilloscope so it can correctly scale the voltage readings
        self._probe_atten     = scp_cfg.get("probe_attenuation", 1.0)
        # Store whether the 20 MHz bandwidth limit should be enabled on the oscilloscope; limiting the bandwidth reduces high-frequency noise in the measurement
        self._bw_20mhz        = scp_cfg.get("bandwidth_limit_20mhz", True)
        # Store the VISA communication timeout in milliseconds; if the oscilloscope does not respond within this time, an error is raised
        self._scope_timeout   = scp_cfg.get("timeout_ms", 30000)

        # Store the oscilloscope timebase setting for DC voltage measurements in seconds per division (e.g. 0.01 = 10 ms/div)
        self._dc_timebase     = scp_cfg.get("dc_timebase_s_per_div", 0.01)
        # Store the oscilloscope timebase setting for ripple measurements in seconds per division (e.g. 0.1 = 100 ms/div)
        self._ripple_timebase = scp_cfg.get("ripple_timebase_s_per_div", 0.1)
        # Store the oscilloscope vertical scale for ripple measurements in volts per division (e.g. 0.05 = 50 mV/div)
        self._ripple_vscale   = scp_cfg.get("ripple_v_scale_v_per_div", 0.05)
        # Store the coupling mode for ripple measurements — should be "AC" so the DC component of the signal is blocked and only the noise is visible
        self._ripple_coupling = scp_cfg.get("ripple_coupling", "AC")
        # Store the number of ripple settle periods to wait after starting the scope before stopping and measuring; longer wait times give more stable readings
        self._ripple_settle   = scp_cfg.get("ripple_settle_periods", 3)

        # This comment marks the start of the section that determines where test results will be saved
        # ── Resolve output directory ──────────────────────────────────────────
        # If the caller did not specify an output directory, read the default path from the config file
        if output_dir is None:
            # Extract the output directory settings from the config file
            out_cfg = _CFG.get("output_dir", {})
            # Handle two config formats: the path may be stored as a nested object with a 'path' key, or as a plain string
            output_dir = (
                # If the config value is a dictionary, read the 'path' key; if that key is also absent, fall back to the default folder name
                out_cfg.get("path", "steady_state_ripple_results")
                if isinstance(out_cfg, dict)
                # If the config value is already a plain string, convert it directly
                else str(out_cfg)
            )

        # Format the current date and time as a compact string (e.g. "20260408_143022") that will be embedded in all output folder and file names so each test run is uniquely identified
        timestamp = self._test_start_time.strftime("%Y%m%d_%H%M%S")
        # Store the timestamp so it can be used later when naming report files inside the _save_reports method
        self._timestamp = timestamp

        # Build the path to the unique run folder by combining the base output directory with a prefix and the timestamp
        self._run_dir         = Path(output_dir) / f"run_{timestamp}"
        # Build the path to the screenshots sub-folder where oscilloscope screen captures will be saved
        self._screenshots_dir = self._run_dir / "screenshots"
        # Build the path to the reports sub-folder where CSV, JSON, and TXT result files will be saved
        self._reports_dir     = self._run_dir / "reports"

        # Attempt to create all three output folders on disk; if the location is not writeable, fall back to a safe default location next to this script
        try:
            # Loop over each folder path and create it, including any missing parent directories; 'exist_ok=True' means no error is raised if the folder already exists
            for d in [self._run_dir, self._screenshots_dir, self._reports_dir]:
                # Create this individual folder and any required parent folders
                d.mkdir(parents=True, exist_ok=True)
        # If a permission error or other OS-level error prevents folder creation (e.g., the drive is full or access is denied), catch that error and try an alternative location
        except (PermissionError, OSError) as e:
            # Build a fallback output path next to this script file — this path should always be writable
            fallback = Path(__file__).resolve().parent / "steady_state_ripple_results"
            # Rebuild the run folder path using the fallback base directory
            self._run_dir         = fallback / f"run_{timestamp}"
            # Rebuild the screenshots path under the fallback run folder
            self._screenshots_dir = self._run_dir / "screenshots"
            # Rebuild the reports path under the fallback run folder
            self._reports_dir     = self._run_dir / "reports"
            # Create all three fallback directories on disk
            for d in [self._run_dir, self._screenshots_dir, self._reports_dir]:
                # Create this individual fallback folder and any required parent folders
                d.mkdir(parents=True, exist_ok=True)
            # Warn the operator that the originally configured output path could not be used and explain where results will be saved instead
            print(f"  WARNING: Could not write to '{output_dir}' ({e}). Falling back to: {fallback}")

        # This comment marks the start of the section that sets up the log file
        # ── Logging ───────────────────────────────────────────────────────────
        # Create a logger object named after this class; all timestamped messages recorded during the test will go through this logger
        self._logger = logging.getLogger(self.__class__.__name__)
        # Build the full file path for the log file inside the run folder
        log_path = self._run_dir / "steady_state_ripple_test.log"
        # Only add a new file handler if the logger does not already have one — this prevents duplicate log entries if the class is instantiated more than once in the same Python session
        if not self._logger.handlers:
            # Create a file handler that writes log messages to the log file using UTF-8 encoding
            fh = logging.FileHandler(str(log_path), encoding="utf-8")
            # Set the log message format to include a human-readable timestamp, the severity level, the logger name, and the message text
            fh.setFormatter(logging.Formatter(
                # Format string: time (HH:MM:SS), level padded to 8 chars, logger name, then the message
                '%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
                # Use a compact hours:minutes:seconds format for the timestamp
                datefmt='%H:%M:%S'
            ))
            # Attach the file handler to the logger so all log calls write to the file
            self._logger.addHandler(fh)
            # Set the minimum logging level to DEBUG so that all messages (including verbose debug-level ones) are recorded in the log file
            self._logger.setLevel(logging.DEBUG)
        # Write the run directory path to the log file as the very first entry, so there is a clear record of where output files were saved
        self._logger.info(f"Run directory: {self._run_dir}")

        # This comment marks the start of the section that initialises the instrument connection handles
        # ── Instrument handle ─────────────────────────────────────────────────
        # Initialise the oscilloscope connection object as None; the actual connection is established later by the _connect_scope method when the test begins
        self._scope: Optional[KeysightDSOX6004A] = None
        # Initialise the results list as empty; RailResult objects will be appended here after each rail is tested, and the list will be used to generate reports at the end
        self._results: List[RailResult] = []

    # This comment is a decorative section divider marking the instrument helper methods
    # ─────────────────────────────────────────────────────────────────────────
    # Instrument helpers
    # ─────────────────────────────────────────────────────────────────────────

    # Define a method that opens a VISA connection to the Keysight oscilloscope; it returns True if the connection was successful, or False if it failed
    def _connect_scope(self) -> bool:
        # Print a status message to the console so the operator knows the program is attempting to connect to the oscilloscope
        print("\n  Connecting oscilloscope...")
        # Create a new oscilloscope driver object using the configured VISA address and timeout; this does not yet open the connection
        self._scope = KeysightDSOX6004A(self._scope_address, timeout_ms=self._scope_timeout)
        # Attempt to open the VISA connection to the oscilloscope; if the connection fails, return False immediately
        if not self._scope.connect():
            # Print a clear error message showing which address the connection attempt was made to
            print(f"  ERROR: Failed to connect to scope at {self._scope_address}")
            # Return False to signal to the caller that the test cannot proceed without an instrument connection
            return False
        # Query the oscilloscope for its identification information (manufacturer, model, serial number); use an empty dictionary if the query returns nothing
        info = self._scope.get_instrument_info() or {}
        # Print a confirmation message showing the oscilloscope model that responded, so the operator can verify the correct instrument was connected
        print(f"  Scope connected — {info.get('model', 'Keysight DSOX')}")
        # Return True to signal that the connection was opened successfully
        return True

    # Define a method that safely closes the connection to the oscilloscope when the test has finished or if an error occurred
    def _disconnect_scope(self):
        # Wrap the disconnect call in a try/except block so that if the connection has already dropped or the instrument is unresponsive, the program does not crash
        try:
            # Only attempt to disconnect if the oscilloscope object exists and the connection is currently open
            if self._scope and self._scope.is_connected:
                # Send the disconnect command to the oscilloscope driver to cleanly close the VISA session
                self._scope.disconnect()
        # If any error occurs during disconnection (e.g., the cable was unplugged), log a warning but do not raise the error — cleanup should never stop the program
        except Exception as e:
            # Record the disconnection error in the log file as a warning-level message for later review
            self._logger.warning(f"Scope disconnect error: {e}")

    # This comment is a decorative section divider marking the scope configuration helper methods
    # ─────────────────────────────────────────────────────────────────────────
    # Scope configuration helpers
    # ─────────────────────────────────────────────────────────────────────────

    # Define a method that configures Channel 1 of the oscilloscope for the DC voltage measurement phase; it sends all necessary instrument settings and returns True if everything succeeded
    def _configure_for_dc(self, rail: RailConfig) -> bool:
        # This docstring describes exactly what oscilloscope settings are applied when this method is called
        """
        Set CH1 for DC voltage measurement:
          DC coupling · 20 MHz BW · appropriate V/div · 10 ms/div · auto-trigger.

        The vertical offset is set to nominal_v so the signal sits at screen centre.
        CH2–4 are disabled for a clean single-channel display.
        """
        # Read the channel number from the class constant so the same variable is used consistently throughout this method
        ch = self.SCOPE_CHANNEL

        # Loop through channels 2, 3, and 4 and disable each one so they do not appear on the oscilloscope screen and do not interfere with the measurement
        for c in [2, 3, 4]:
            # Send the command to turn off this channel on the oscilloscope
            self._scope.disable_channel(c)

        # Configure Channel 1 with the vertical scale, vertical offset, coupling mode, and probe attenuation appropriate for measuring this rail's DC voltage
        ok = self._scope.configure_channel(
            # Specify that Channel 1 should be configured
            channel=ch,
            # Set the vertical scale to the value defined in the rail's configuration (e.g. 1 V/div for a 5 V rail)
            vertical_scale=rail.dc_v_scale,
            # Centre the waveform on screen by setting the vertical offset to the rail's nominal voltage so the signal appears in the middle of the display
            vertical_offset=rail.nominal_v,   # centre signal on screen
            # Use DC coupling so the full voltage level (including the DC component) is visible on screen
            coupling="DC",
            # Set the probe attenuation ratio to match the physical probe being used
            probe_attenuation=self._probe_atten,
        )
        # If the channel configuration command failed (e.g., the oscilloscope returned an error), return False immediately
        if not ok:
            # Signal to the caller that this setup step did not complete successfully
            return False

        # Apply the configured bandwidth limit setting to Channel 1 — 20 MHz is used to reduce high-frequency interference that could inflate the DC reading
        self._scope.set_bandwidth_limit(ch, self._bw_20mhz)

        # Configure the oscilloscope timebase (horizontal time scale) to the value specified in the config (e.g. 10 ms/div) and set the horizontal offset to zero so the trace is centred
        ok = self._scope.configure_timebase(
            # Set the time per division for DC measurements
            time_scale=self._dc_timebase,
            # Set the horizontal offset to zero — no time shift needed for a steady DC signal
            time_offset=0.0,
        )
        # If the timebase configuration failed, return False to indicate that this setup step was unsuccessful
        if not ok:
            # Signal to the caller that the timebase configuration did not succeed
            return False

        # Set the oscilloscope trigger mode to AUTO (free-run) so the scope continuously updates the waveform display without waiting for a specific trigger edge — this is appropriate for stable DC signals
        # Auto trigger — free-run; no edge needed for steady-state DC
        try:
            # Send the SCPI command directly to the oscilloscope to enable the free-running trigger mode
            self._scope._scpi_wrapper.write(":TRIGger:SWEep AUTO")
            # Wait 100 milliseconds for the oscilloscope to process the trigger mode change before proceeding
            time.sleep(0.1)
        # If sending the trigger command fails (e.g., due to a communication timeout), log a warning but do not abort — the scope may still work adequately without this setting
        except Exception as e:
            # Record the warning in the log file so the issue can be investigated if the measurement looks wrong
            self._logger.warning(f"Trigger sweep AUTO failed: {e}")

        # Return True to indicate that all DC configuration steps completed successfully
        return True

    # Define a method that reconfigures Channel 1 for the AC-coupled ripple measurement phase after the DC voltage phase has already been completed
    def _configure_for_ripple(self) -> bool:
        # This docstring describes the specific oscilloscope settings applied during the ripple configuration phase
        """
        Reconfigure CH1 for ripple measurement:
          AC coupling · 20 MHz BW · 50 mV/div · 100 ms/div · auto-trigger.

        Offset set to 0 V — DC component is blocked by AC coupling.
        """
        # Read the channel number from the class constant
        ch = self.SCOPE_CHANNEL

        # Configure Channel 1 for ripple measurement: small vertical scale to make the tiny ripple visible, AC coupling to block the DC level, and zero offset since there is no DC component to centre
        ok = self._scope.configure_channel(
            # Specify Channel 1 for configuration
            channel=ch,
            # Set the vertical scale to the ripple measurement scale (e.g. 50 mV/div) so small voltage fluctuations fill the screen
            vertical_scale=self._ripple_vscale,
            # Set the vertical offset to zero because AC coupling removes the DC component, so the waveform is naturally centred around 0 V
            vertical_offset=0.0,
            # Use AC coupling to block the large DC voltage and show only the small ripple noise on top of it
            coupling=self._ripple_coupling,   # "AC"
            # Set the probe attenuation to match the physical probe
            probe_attenuation=self._probe_atten,
        )
        # If the channel configuration failed, return False immediately
        if not ok:
            # Signal failure to the caller
            return False

        # Apply the 20 MHz bandwidth limit to Channel 1 to reduce high-frequency interference that could inflate the ripple reading
        self._scope.set_bandwidth_limit(ch, self._bw_20mhz)

        # Configure the timebase for ripple measurements — a slower timebase (e.g. 100 ms/div) captures several ripple cycles within the screen window
        ok = self._scope.configure_timebase(
            # Set the time per division for ripple measurements
            time_scale=self._ripple_timebase,
            # No horizontal offset needed
            time_offset=0.0,
        )
        # If the timebase configuration failed, return False
        if not ok:
            # Signal failure to the caller
            return False

        # Set the oscilloscope trigger mode to AUTO (free-run) so the waveform updates continuously, which is needed to let the AC coupling settle to a stable ripple display
        try:
            # Send the SCPI trigger mode command to the oscilloscope
            self._scope._scpi_wrapper.write(":TRIGger:SWEep AUTO")
            # Wait 100 milliseconds for the oscilloscope to apply the new trigger setting
            time.sleep(0.1)
        # If the trigger command fails, log a warning but continue — the measurement may still work
        except Exception as e:
            # Record the warning so it can be reviewed if ripple values look suspicious
            self._logger.warning(f"Trigger sweep AUTO failed: {e}")

        # Return True to indicate all ripple configuration steps completed successfully
        return True

    # This comment is a decorative section divider marking the Phase 1 DC voltage measurement methods
    # ─────────────────────────────────────────────────────────────────────────
    # Phase 1 — DC voltage
    # ─────────────────────────────────────────────────────────────────────────

    # Define a method that performs the complete DC voltage measurement sequence for one rail: it configures the scope, runs and stops the acquisition, reads the measurement, captures a screenshot, and returns a RailResult containing all findings
    def _measure_dc_voltage(self, rail: RailConfig) -> RailResult:
        # This docstring summarises what measurement this method performs and what it returns
        """
        Acquire a DC-coupled waveform and measure DC RMS FS.
        Returns a RailResult with DC fields populated; ripple fields left as N/A.
        """
        # Store the oscilloscope channel number in a short local variable for convenience
        ch = self.SCOPE_CHANNEL

        # Print a blank line for visual spacing in the console output
        print()
        # Print a horizontal separator line to visually separate this rail's section from the previous one
        print(f"  {'─' * 64}")
        # Print the name and test point of the rail currently being measured so the operator knows where to place the probe
        print(f"  RAIL: {rail.name}  ({rail.test_point})")
        # Print another horizontal separator
        print(f"  {'─' * 64}")
        # Print the nominal voltage and the acceptable measurement range so the operator can verify the setup before starting
        print(f"  Nominal: {rail.nominal_v:.3f} V    Expected: {rail.min_v:.2f} – {rail.max_v:.2f} V")
        # Print a blank line for spacing
        print()
        # Print a step counter so the operator knows they are on Step 1 of 2 for this rail
        print(f"  STEP 1 of 2 — DC Voltage")
        # Instruct the operator to connect the probe tip to the correct test point for this rail
        print(f"  Connect probe tip (DC mode, 1:1) to  {rail.test_point}  ({rail.name} rail).")
        # Instruct the operator to attach the probe ground clip to the nearest board ground point
        print(f"  Attach ground clip to nearest board GND.")
        # Pause the program and wait for the operator to press ENTER, confirming that the probe has been connected and they are ready to proceed
        input("  Press ENTER when probe is connected... ")

        # Print a status message indicating the oscilloscope is being configured for DC measurement
        print("  Configuring scope: DC coupling, 20 MHz BW, auto-trigger...")
        # Call the DC configuration method; if it fails, create and return an error result immediately without attempting to measure
        if not self._configure_for_dc(rail):
            # Print an error message to the console
            print("  ERROR: Scope DC configuration failed.")
            # Return a RailResult with "ERROR" status and no measured values, so the test can continue with the next rail
            return RailResult(
                # Include the rail's identification fields for traceability
                name=rail.name, test_point=rail.test_point,
                # Include the voltage range fields
                nominal_v=rail.nominal_v, min_v=rail.min_v, max_v=rail.max_v,
                # Set the measured DC value to None and mark the DC status as ERROR
                measured_dc_v=None, dc_status="ERROR",
                # Include the ripple limit from the config
                ripple_max_mvpp=rail.ripple_max_mvpp,
                # Set the ripple measurement to None and mark the ripple status as ERROR since the whole rail test failed
                measured_ripple_mvpp=None, ripple_status="ERROR",
            )

        # Inform the operator that the oscilloscope is now running and acquiring the waveform
        # Acquire: run, wait for several timebase windows, stop
        print("  Acquiring waveform (scope running)...")
        # Send the run command to start the oscilloscope acquisition
        self._scope.run()
        # Wait 1.5 seconds while the oscilloscope captures and averages approximately 15 successive 10 ms timebase windows, ensuring the DC reading is stable
        time.sleep(1.5)    # ~15 × 10 ms windows — ensures a stable averaged reading
        # Send the stop command to freeze the waveform on screen so the measurement can be taken from a stable trace
        self._scope.stop()
        # Wait an additional 0.3 seconds for the oscilloscope to fully process the stop command before attempting to read the measurement
        time.sleep(0.3)

        # Send the DC RMS full-screen measurement command to the oscilloscope and read back the result in volts
        # Measure DC RMS full-screen  (:MEASure:VRMS? DISPlay,DC,CHANnelN)
        measured_v = self._scope.measure_dc_rms_fs(ch)

        # Check whether the instrument returned a valid voltage value
        if measured_v is None:
            # Print an error message if no measurement value was returned
            print("  ERROR: DC RMS measurement returned no value.")
            # Set the DC status to ERROR since we have no value to compare against the specification
            dc_status = "ERROR"
        # If a valid measurement was returned, compare it against the acceptable range
        else:
            # Check whether the measured voltage falls within the specified minimum and maximum range for this rail
            in_range  = rail.min_v <= measured_v <= rail.max_v
            # Determine the pass/fail status based on whether the voltage is in range
            dc_status = "PASS" if in_range else "FAIL"
            # Choose a colour-coded status label: green "PASS" or red "FAIL" using ANSI terminal colour codes
            mark  = "\033[32mPASS\033[0m" if in_range else "\033[31mFAIL\033[0m"
            # Print the measured DC voltage and its pass/fail result on the console
            print(f"  Measured DC RMS:  {measured_v:.4f} V   [{mark}]")
            # If the measurement is out of range, print the expected range again with a clear out-of-range warning
            if not in_range:
                # Print the specification range and a warning that the result exceeded those limits
                print(f"  Expected range:   {rail.min_v:.2f} – {rail.max_v:.2f} V   ← OUT OF RANGE")

        # Build the path for the DC voltage screenshot file using the rail name as part of the filename
        # Screenshot — scope is already stopped, so freeze_acquisition=False
        shot_path = str(self._screenshots_dir / f"{rail.name}_dc_voltage.png")
        # Capture a screenshot from the oscilloscope and save it to the file path above; 'freeze_acquisition=False' means the scope display is not changed before capturing
        saved = self._scope.get_screenshot(shot_path, freeze_acquisition=False)
        # If the screenshot was saved successfully, print the filename to the console
        if saved:
            # Print just the filename (not the full path) to keep the console output concise
            print(f"  Saved: {Path(saved).name}")
        # If the screenshot could not be saved (e.g., instrument error or disk full), print a warning
        else:
            # Warn the operator that the screenshot was not captured; the test will still continue
            print("  WARNING: Screenshot could not be saved.")

        # Write a detailed measurement entry to the log file so the result is permanently recorded
        self._logger.info(
            # Log the rail name, the measured DC voltage, the acceptable range, and the pass/fail status
            f"{rail.name} DC: measured={measured_v}V  range=[{rail.min_v},{rail.max_v}]  status={dc_status}"
        )

        # Build and return a RailResult object containing all the DC measurement findings; the ripple fields are left as None/"N/A" and will be populated in the next phase if a ripple spec exists
        return RailResult(
            # Set the rail identification fields
            name=rail.name, test_point=rail.test_point,
            # Set the voltage range fields
            nominal_v=rail.nominal_v, min_v=rail.min_v, max_v=rail.max_v,
            # Set the measured DC voltage and the pass/fail status from the measurement above
            measured_dc_v=measured_v, dc_status=dc_status,
            # Copy the ripple limit from the config for inclusion in the result record
            ripple_max_mvpp=rail.ripple_max_mvpp,
            # Leave the ripple measurement as None and mark the status as "N/A" — the ripple phase has not run yet
            measured_ripple_mvpp=None, ripple_status="N/A",
        )

    # This comment is a decorative section divider marking the Phase 2 ripple measurement methods
    # ─────────────────────────────────────────────────────────────────────────
    # Phase 2 — Ripple
    # ─────────────────────────────────────────────────────────────────────────

    # Define a method that performs the AC ripple measurement for one rail; it takes the RailResult from the DC phase and updates it with the ripple measurement outcome, then returns the updated result
    def _measure_ripple(self, result: RailResult, rail: RailConfig) -> RailResult:
        # This docstring summarises what this method does
        """
        Reconfigure CH1 for AC-coupled ripple measurement.
        Updates and returns the RailResult with ripple fields populated.
        """
        # Store the oscilloscope channel number in a short local variable
        ch        = self.SCOPE_CHANNEL
        # Calculate the total settle time in seconds by multiplying the configured number of settle periods by 10 (screen widths per settle period) by the timebase in seconds per division — this ensures the AC coupling on the scope fully settles before measuring
        settle_s  = self._ripple_settle * 10 * self._ripple_timebase   # e.g. 3×10×0.1 = 3 s

        # Print a blank line for spacing
        print()
        # Print a step header showing the ripple limit for this rail so the operator knows what the measurement will be compared against
        print(f"  STEP 2 of 2 — Ripple  (limit: < {rail.ripple_max_mvpp:.0f} mVpp)")
        # Print a blank line
        print()
        # Print a header warning the operator about the importance of a short ground path for accurate ripple measurements
        print("  For accurate ripple measurement — SHORT GROUND PATH IS ESSENTIAL:")
        # Instruct the operator to remove the long alligator-clip ground lead, which adds inductance and inflates readings
        print(f"    1. Remove the alligator-clip ground lead from the probe.")
        # Instruct the operator to fit a coaxial GND spring tip onto the probe barrel as a low-inductance ground connection
        print(f"    2. Fit a GND SPRING (coaxial spring tip) onto the probe barrel.")
        # Instruct the operator to connect the GND spring to the closest ground point to the rail under test
        print(f"    3. Connect the GND spring to a board ground point closest to the {rail.name} rail.")
        # Instruct the operator to place the probe tip directly across the last output capacitor of the rail, which is where ripple is most accurately measured
        print(f"    4. Place the probe tip directly across the LAST OUTPUT CAPACITOR of the {rail.name} rail.")
        # Explain why the short ground path matters
        print("       (Long ground leads add inductance — they inflate ripple readings.)")
        # Pause and wait for the operator to confirm that the GND spring and probe tip have been correctly positioned
        input("  Press ENTER when GND spring and probe tip are positioned... ")

        # Print a status message showing the exact oscilloscope settings being applied for this measurement
        print(f"  Configuring scope: AC coupling, {self._ripple_vscale * 1000:.0f} mV/div, "
              f"{self._ripple_timebase * 1000:.0f} ms/div...")
        # Call the ripple configuration method; if it fails, mark the ripple status as ERROR and return the result without measuring
        if not self._configure_for_ripple():
            # Print an error message to the console
            print("  ERROR: Scope ripple configuration failed.")
            # Update the ripple status in the result object to reflect the configuration error
            result.ripple_status = "ERROR"
            # Return the partially-completed result so the test can continue with the next rail
            return result

        # Print a status message informing the operator how long the scope will run before stopping
        # Run → settle → stop
        print(f"  Running scope — waiting {settle_s:.0f} s for waveform to settle...")
        # Start the oscilloscope acquisition — the waveform will update continuously until stopped
        self._scope.run()
        # Wait for the calculated settle time so that the AC coupling capacitor inside the scope can charge fully and the displayed waveform stabilises to the true ripple shape
        time.sleep(settle_s)
        # Stop the oscilloscope acquisition to freeze the settled waveform so the Vpp measurement can be taken
        self._scope.stop()
        # Wait 0.3 seconds for the oscilloscope to fully process the stop command before reading the measurement
        time.sleep(0.3)
        # Print a status message indicating the measurement is being taken
        print("  Scope stopped. Measuring Vpp...")

        # Request the peak-to-peak voltage measurement from the oscilloscope; the value is returned in volts
        # Vpp returned in volts; convert to mV
        vpp_v = self._scope.measure_peak_to_peak(ch)

        # Check whether the instrument returned a valid measurement value
        if vpp_v is None:
            # Print an error message if no value was returned
            print("  ERROR: Vpp measurement returned no value.")
            # Mark the ripple status as ERROR since we cannot compare a missing value against the specification
            result.ripple_status = "ERROR"
        # If a valid value was returned, compare it against the ripple limit
        else:
            # Convert the Vpp value from volts to millivolts by multiplying by 1000, since the ripple specification is in mVpp
            vpp_mv    = vpp_v * 1000.0
            # Check whether the measured ripple is within the specified limit
            in_spec   = vpp_mv <= rail.ripple_max_mvpp
            # Store the measured ripple value in millivolts in the result object
            result.measured_ripple_mvpp = vpp_mv
            # Set the ripple pass/fail status in the result object
            result.ripple_status        = "PASS" if in_spec else "FAIL"
            # Choose a colour-coded status label for the console output
            mark = "\033[32mPASS\033[0m" if in_spec else "\033[31mFAIL\033[0m"
            # Print the measured ripple and the pass/fail verdict
            print(f"  Measured Ripple:  {vpp_mv:.1f} mVpp   [{mark}]")
            # If the ripple exceeds the limit, print a clear warning showing the limit that was exceeded
            if not in_spec:
                # Print the limit and a warning flag
                print(f"  Limit:            {rail.ripple_max_mvpp:.0f} mVpp   ← EXCEEDS LIMIT")

        # Build the file path for the ripple screenshot using the rail name
        # Screenshot
        shot_path = str(self._screenshots_dir / f"{rail.name}_ripple.png")
        # Capture the oscilloscope screen and save it as a PNG file
        saved = self._scope.get_screenshot(shot_path, freeze_acquisition=False)
        # If saved successfully, print just the filename as confirmation
        if saved:
            # Print the screenshot filename to the console
            print(f"  Saved: {Path(saved).name}")
        # If the screenshot could not be saved, print a warning
        else:
            # Warn the operator that the screenshot was not captured
            print("  WARNING: Screenshot could not be saved.")

        # Write the ripple measurement details to the log file for a permanent record
        self._logger.info(
            # Log the rail name, the measured ripple, the limit, and the pass/fail status
            f"{rail.name} Ripple: measured={result.measured_ripple_mvpp}mVpp  "
            f"limit={rail.ripple_max_mvpp}mVpp  status={result.ripple_status}"
        )

        # Return the updated RailResult object with both DC and ripple fields fully populated
        return result

    # This comment is a decorative section divider marking the reporting methods
    # ─────────────────────────────────────────────────────────────────────────
    # Reporting
    # ─────────────────────────────────────────────────────────────────────────

    # Define a method that prints a formatted summary table of all rail measurement results to the console after all rails have been tested
    def _print_summary(self):
        # Print a blank line for spacing before the summary table
        print()
        # Print the top border of the summary table
        print("=" * 82)
        # Print the title of the summary section
        print("  RESULTS SUMMARY")
        # Print the bottom border of the title
        print("=" * 82)
        # Print the column header row with fixed-width formatting for alignment
        print(
            # Each column header is given a specific width so the data rows below it align correctly
            f"  {'Rail':<10}  {'TP':<12}  {'Nominal':>8}  {'Measured DC':>12}  "
            f"{'Range':>13}  {'DC':>5}  {'Ripple mVpp':>12}  {'Limit':>7}  {'Ripple':>6}"
        )
        # Print a horizontal separator line under the column headers
        print("  " + "-" * 78)

        # Initialise a flag to track whether every rail passed both tests; it will be set to False if any rail fails
        overall_pass = True
        # Loop through every RailResult stored in the results list and print a summary row for each one
        for r in self._results:
            # Format the measured DC voltage as a string; show "  ERROR  " if no value was obtained
            dc_str  = f"{r.measured_dc_v:.4f} V" if r.measured_dc_v is not None else "  ERROR  "
            # Format the voltage acceptance range as a compact string (e.g. "3.42–3.78V")
            rng_str = f"{r.min_v:.2f}–{r.max_v:.2f}V"
            # Format the measured ripple as a string with 1 decimal place, or show a dash if no ripple measurement was taken
            rip_str = f"{r.measured_ripple_mvpp:.1f}" if r.measured_ripple_mvpp is not None else "—"
            # Format the ripple limit as a string prefixed with "<", or show "N/A" if no ripple spec exists
            lim_str = f"<{r.ripple_max_mvpp:.0f}" if r.ripple_max_mvpp is not None else "N/A"

            # Check whether the DC measurement passed
            dc_ok   = r.dc_status  == "PASS"
            # Check whether the ripple measurement passed or was not applicable (N/A)
            rip_ok  = r.ripple_status in ("PASS", "N/A")
            # If either measurement failed, update the overall pass flag to False
            if not (dc_ok and rip_ok):
                # Mark the overall test as failed because at least one rail did not meet its specification
                overall_pass = False

            # Choose a compact label for the DC status column: " OK " for pass, "FAIL" for any other status
            dc_mark  = " OK " if dc_ok  else "FAIL"
            # Choose a compact label for the ripple status column, truncating to 4 characters if the status string is longer
            rip_mark = r.ripple_status if len(r.ripple_status) <= 4 else r.ripple_status[:4]

            # Print the data row for this rail, with all values aligned to their respective column widths
            print(
                # Print all fields formatted consistently for readability
                f"  {r.name:<10}  {r.test_point:<12}  {r.nominal_v:>7.3f}V  "
                f"{dc_str:>12}  {rng_str:>13}  {dc_mark:>5}  "
                f"{rip_str:>12}  {lim_str:>7}  {rip_mark:>6}"
            )

        # Print a blank line after the data rows
        print()
        # If every rail passed, print a green "PASS" overall verdict; otherwise print a red "FAIL" verdict
        if overall_pass:
            # Print the green PASS verdict using ANSI colour codes
            print("  OVERALL: \033[32mPASS\033[0m — all rails within specification")
        else:
            # Print the red FAIL verdict using ANSI colour codes
            print("  OVERALL: \033[31mFAIL\033[0m — one or more rails outside specification")
        # Print the closing border of the summary table
        print("=" * 82)

    # Define a method that saves the test results to three report files (CSV, JSON, and plain-text summary) in the reports sub-folder
    def _save_reports(self):
        # Store the timestamp string in a short local variable to avoid repeated attribute lookups
        ts = self._timestamp
        # Define the list of field names that will appear as column headers in the CSV file and as keys in the JSON result objects
        fields = [
            # The rail name identifier
            'rail_name', 'test_point', 'nominal_v', 'expected_range',
            # The DC measurement value and verdict
            'measured_dc_v', 'dc_status',
            # The ripple limit, measurement, and verdict
            'ripple_max_mvpp', 'measured_ripple_mvpp', 'ripple_status',
        ]

        # This comment marks the CSV file saving block
        # CSV
        # Build the file path for the CSV report file using the timestamp in the name
        csv_path = self._reports_dir / f"steady_state_ripple_results_{ts}.csv"
        # Open the CSV file for writing; 'newline=""' prevents Python from inserting extra blank lines on Windows
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            # Create a DictWriter object that maps result dictionaries to the specified column fields
            writer = csv.DictWriter(f, fieldnames=fields)
            # Write the header row containing all column names at the top of the CSV file
            writer.writeheader()
            # Loop through each RailResult and write one row per rail to the CSV file
            for r in self._results:
                # Convert the result object to a plain dictionary and write it as a row
                writer.writerow(r.to_dict())
        # Print the full path of the saved CSV file to the console
        print(f"  CSV  : {csv_path}")

        # This comment marks the JSON file saving block
        # JSON
        # Build the file path for the JSON report file
        json_path = self._reports_dir / f"steady_state_ripple_results_{ts}.json"
        # Assemble the complete data payload to be saved in JSON format, including test metadata and all individual results
        payload = {
            # The name of the test for identification purposes
            'test_name':    'Steady-State Rail Verification and Ripple',
            # The timestamp string identifying when this run was performed
            'timestamp':    ts,
            # The number of rails that were tested in this run
            'rails_tested': len(self._results),
            # The overall pass/fail verdict: "PASS" only if every rail passed both the DC and ripple checks
            'overall':      'PASS' if all(
                # Check that every result has a "PASS" DC status and either a "PASS" or "N/A" ripple status
                r.dc_status == 'PASS' and r.ripple_status in ('PASS', 'N/A')
                # Apply this check to every result in the list
                for r in self._results
            ) else 'FAIL',
            # The list of individual rail result dictionaries
            'results': [r.to_dict() for r in self._results],
        }
        # Open the JSON file for writing and save the payload with 2-space indentation for human readability
        with open(json_path, 'w', encoding='utf-8') as f:
            # Write the dictionary to the file as formatted JSON text
            json.dump(payload, f, indent=2)
        # Print the full path of the saved JSON file to the console
        print(f"  JSON : {json_path}")

        # This comment marks the plain-text summary file saving block
        # TXT summary
        # Build the file path for the plain-text summary file
        txt_path = self._reports_dir / f"steady_state_ripple_summary_{ts}.txt"
        # Build the list of lines that will be written to the text file, starting with the header section
        lines = [
            # The title line of the text report
            "STEADY-STATE RAIL VERIFICATION AND RIPPLE TEST",
            # The run timestamp so the report is self-identifying
            f"Run timestamp : {ts}",
            # The total number of rails tested
            f"Rails tested  : {len(self._results)}",
            # A blank line for visual spacing
            "",
            # The column header row formatted to align with the data rows below
            f"{'Rail':<10}  {'TP':<12}  {'Measured DC':>12}  {'Range':>13}  "
            f"{'DC':>5}  {'Ripple mVpp':>12}  {'Limit':>7}  {'Ripple':>6}",
            # A separator line between the headers and the data
            "-" * 76,
        ]
        # Loop through each result and add a formatted data row to the lines list
        for r in self._results:
            # Format the measured DC voltage or show "ERROR" if no value was obtained
            dc_str  = f"{r.measured_dc_v:.4f} V" if r.measured_dc_v is not None else "ERROR"
            # Format the ripple measurement or show a dash if not measured
            rip_str = f"{r.measured_ripple_mvpp:.1f}" if r.measured_ripple_mvpp is not None else "—"
            # Format the ripple limit or show "N/A"
            lim_str = f"<{r.ripple_max_mvpp:.0f}" if r.ripple_max_mvpp is not None else "N/A"
            # Format the voltage range string
            rng_str = f"{r.min_v:.2f}–{r.max_v:.2f}V"
            # Append the formatted data row to the lines list
            lines.append(
                # Format the row with fixed widths matching the header columns
                f"{r.name:<10}  {r.test_point:<12}  {dc_str:>12}  {rng_str:>13}  "
                f"{r.dc_status:>5}  {rip_str:>12}  {lim_str:>7}  {r.ripple_status:>6}"
            )
        # Open the text file and write all the assembled lines, joined with newlines, followed by a final newline
        with open(txt_path, 'w', encoding='utf-8') as f:
            # Write the complete text content to the file
            f.write('\n'.join(lines) + '\n')
        # Print the full path of the saved text file to the console
        print(f"  TXT  : {txt_path}")

    # This comment is a decorative section divider marking the main entry point method
    # ─────────────────────────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────────────────────────

    # Define the main 'run' method that orchestrates the entire test sequence: it connects to the oscilloscope, tests each rail in order, prints the summary, saves the reports, and returns True if all rails passed or False if any failed
    def run(self) -> bool:
        # If the rails list is empty (no rails were selected), print a message and return True immediately with no measurements taken
        if not self._rails:
            # Inform the operator that no rails were selected
            print("  No rails selected — nothing to test.")
            # Return True because there was nothing to fail
            return True

        # Attempt to connect to the oscilloscope; if the connection fails, abort the test immediately
        if not self._connect_scope():
            # Return False to indicate the test could not run
            return False

        # Use a try/finally block to ensure the oscilloscope is always disconnected at the end, even if an error occurs during the test
        try:
            # Print a header line showing how many rails will be tested and listing their names
            print(f"\n  Testing {len(self._rails)} rail(s): "
                  + "  ".join(r.name for r in self._rails))

            # Loop through each selected rail, numbering them starting from 1
            for i, rail in enumerate(self._rails, 1):
                # Print a formatted banner line showing the current rail number and name as a progress indicator
                print(f"\n  ══ Rail {i} / {len(self._rails)} "
                      f"{'═' * max(0, 52 - len(rail.name))} {rail.name} ══")

                # Perform Phase 1 (DC voltage measurement) for this rail and store the result
                # Phase 1: DC voltage
                result = self._measure_dc_voltage(rail)

                # Only perform Phase 2 (ripple measurement) if this rail has a ripple specification defined
                # Phase 2: Ripple (only for rails that have a ripple spec)
                if rail.ripple_max_mvpp is not None:
                    # Perform the ripple measurement and update the result object with the ripple findings
                    result = self._measure_ripple(result, rail)
                # If this rail has no ripple specification, skip the ripple phase entirely
                else:
                    # Print a blank line for spacing
                    print()
                    # Print a message explaining that the ripple phase is being skipped for this rail because no limit is defined
                    print(f"  STEP 2 of 2 — Ripple:  No ripple spec for {rail.name} — skipped.")

                # Append the completed result (with both DC and ripple fields populated) to the results list
                self._results.append(result)

        # The 'finally' block runs whether the loop completed normally or an exception occurred — this guarantees the oscilloscope connection is always closed cleanly
        finally:
            # Close the VISA connection to the oscilloscope to release the communication resource
            self._disconnect_scope()

        # Record the date and time when the test finished so the duration can be calculated and reported
        self._test_end_time = datetime.datetime.now()
        # Print the formatted results summary table to the console
        self._print_summary()

        # Print a blank line for spacing
        print()
        # Print a heading before the list of saved report files
        print("  Saving reports...")
        # Call the report saving method to write CSV, JSON, and TXT files to the reports sub-folder
        self._save_reports()
        # Print a blank line for spacing
        print()
        # Print the path to the run folder so the operator knows exactly where to find all the output files
        print(f"  Results folder: {self._run_dir}")
        # Print a final blank line for spacing
        print()

        # Calculate the overall pass/fail result: True only if every rail has a "PASS" DC status and either "PASS" or "N/A" ripple status
        overall = all(
            # Each rail must have passed DC and either passed or been exempt from the ripple check
            r.dc_status == "PASS" and r.ripple_status in ("PASS", "N/A")
            # Apply this check to all results
            for r in self._results
        )
        # Return the overall verdict so the caller (e.g. the run script) knows whether the test as a whole passed or failed
        return overall
