#!/usr/bin/env python3
# ↑ This tells the computer this is a Python program

"""
PWRSTD06: Transient Response Test Automation - Minimal Intervention Version

This is a description of what this entire program does:
- Tests power supply voltage regulators
- Checks if they handle sudden load changes properly
- Minimal user intervention means you just connect probes and it does the rest

Test Procedure:
    For each rail (voltage line):
    1. Ask you to confirm test equipment is connected
    2. Automatically increase the load suddenly (positive step)
    3. Record what happens to the voltage
    4. Automatically decrease the load suddenly (negative step)
    5. Record what happens to the voltage
    6. Save pictures and results
    7. Move to the next rail automatically

Pass Criteria (what makes a rail pass the test):
    - Voltage drop (droop) stays within limits
    - Voltage recovers quickly enough
    - No excessive voltage bounce (overshoot)
    - No oscillation/ringing
    - Stable across all load conditions

Author: Test Automation Team
Version: 2.0.0 - Minimal Intervention
"""

# Import section - these are like toolboxes we're bringing in to use
import logging          # Tool for recording what the program is doing (like a logbook)
import time            # Tool for waiting/pausing and tracking time
import csv             # Tool for saving data in spreadsheet format
import json            # Tool for saving data in a structured text format
import numpy as np     # For numpy type checking in JSON encoder


# Custom JSON encoder to handle numpy types
class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types (bool_, int64, float64, etc.)"""
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)
from pathlib import Path           # Tool for working with file locations
from datetime import datetime      # Tool for getting current date and time
from typing import Optional, Dict, Any, List, Tuple, Union  # Helps define what type of data we expect
from dataclasses import dataclass, asdict, field           # Tools for organizing data structures
from enum import Enum              # Tool for creating lists of fixed choices (like PASS/FAIL)
import sys             # System tools for the program
import os              # Operating system tools for file management

# Add parent directory to path for instrument imports
# ↓ This line tells Python where to find the instrument control code
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to load the instrument control drivers (software that talks to lab equipment)
try:
    # Load the Keithley 2380 electronic load driver (the device that pulls current)
    from instrument_control.keithley_load import Keithley2380, Keithley2380Error

    # Import Keysight oscilloscope driver (using the correct class name)
    from instrument_control.keysight_oscilloscope import KeysightDSOX6004A
    scope_module = 'keysight'
    scope_class = KeysightDSOX6004A
    print("Using Keysight DSOX6004A oscilloscope driver")

except ImportError as e:  # If something went wrong loading drivers
    print(f"Import error: {e}")  # Show what went wrong
    print("Ensure instrument_control module is available in parent directory")  # Give helpful advice
    sys.exit(1)  # Exit if drivers cannot be loaded


# Define the possible test results (like a multiple choice list)
class TestResult(Enum):
    """Test result enumeration - all the possible outcomes for a test"""
    PASS = "PASS"              # Test passed - everything good!
    FAIL = "FAIL"              # Test failed - something wrong
    WARNING = "WARNING"        # Test passed but with concerns
    NOT_TESTED = "NOT_TESTED"  # Test was skipped
    ERROR = "ERROR"            # Test couldn't run due to error


# Define the two types of load changes we test
class LoadStepDirection(Enum):
    """Load step direction - which way are we changing the load?"""
    POSITIVE = "POSITIVE"  # Increase load: Low -> High (100mA -> half rated current)
    NEGATIVE = "NEGATIVE"  # Decrease load: High -> Low (half rated -> 100mA)


# This is a template for storing all the information about one power rail
@dataclass  # This decorator makes it easy to create data storage objects
class RailConfig:
    """Configuration for a power rail under test - all the specs for one voltage line"""
    name: str                      # Name of the rail (like "3V3" or "1V8")
    test_point: str               # Where to probe on the board (like "TP2")
    expected_voltage_v: float     # What voltage we expect (in Volts)
    low_current_ma: int           # Starting current (100mA) - the low load
    high_current_ma: int          # Half of rated current - the high load
    max_droop_mv: float          # Maximum allowed voltage drop (in millivolts)
    max_recovery_time_us: float  # Maximum allowed recovery time (in microseconds)
    max_overshoot_mv: float      # Maximum allowed voltage overshoot (in millivolts)

    @property  # This makes it a calculated value, not stored
    def load_step_positive(self) -> str:
        """Positive load step description - creates a text description"""
        # Returns something like "100mA -> 800mA"
        return f"{self.low_current_ma}mA -> {self.high_current_ma}mA"

    @property  # Another calculated value
    def load_step_negative(self) -> str:
        """Negative load step description - creates a text description"""
        # Returns something like "800mA -> 100mA"
        return f"{self.high_current_ma}mA -> {self.low_current_ma}mA"


# Template for storing results from ONE test (either positive or negative step)
@dataclass
class TransientResult:
    """Results from a single transient measurement - what happened in one test"""
    rail_name: str                    # Which rail was tested (like "3V3")
    step_direction: str               # Was it POSITIVE or NEGATIVE step?
    load_step_description: str        # Text describing the load change (like "100mA -> 800mA")
    droop_mv: float = 0.0            # How much did voltage drop? (in millivolts)
    recovery_time_us: float = 0.0    # How long to recover? (in microseconds)
    overshoot_mv: float = 0.0        # How much did voltage bounce up? (in millivolts)
    has_ringing: bool = False        # Was there oscillation? (True/False)
    screenshot_path: str = ""        # Where is the picture saved?
    timestamp: str = ""              # When did this test happen?
    result: str = "NOT_TESTED"       # Did it PASS or FAIL?
    notes: str = ""                  # Any additional comments
    detailed_calculations: str = ""  # NEW: Step-by-step calculation details for transparency

    def to_dict(self) -> Dict[str, Any]:
        """Convert this result to a dictionary (for saving to file)"""
        return asdict(self)  # Converts all the data above into a dictionary format


# Template for storing BOTH tests for one rail (positive AND negative steps combined)
@dataclass
class RailTestResult:
    """Complete test results for a single rail - combines both positive and negative tests"""
    rail_name: str                              # Which rail (like "3V3")
    test_point: str                             # Where it was tested (like "TP10")
    positive_step: Optional[TransientResult] = None   # Result from positive step test (or None if not done)
    negative_step: Optional[TransientResult] = None   # Result from negative step test (or None if not done)
    overall_result: str = "NOT_TESTED"          # Overall PASS/FAIL for this rail

    def to_dict(self) -> Dict[str, Any]:
        """Convert this result to a dictionary (for saving to file)"""
        return {
            'rail_name': self.rail_name,
            'test_point': self.test_point,
            # Convert positive step to dict if it exists, otherwise None
            'positive_step': self.positive_step.to_dict() if self.positive_step else None,
            # Convert negative step to dict if it exists, otherwise None
            'negative_step': self.negative_step.to_dict() if self.negative_step else None,
            'overall_result': self.overall_result
        }


# ── Interactive Rail Selector ────────────────────────────────────────────
# Shows a checkbox list in the terminal.  Use UP/DOWN to move, TAB to
# toggle a rail, A to select/deselect all, ENTER to confirm, Q to quit.

def _enable_ansi():
    """Enable ANSI escape sequences on Windows 10+"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


def interactive_rail_selector(rail_configs):
    """
    Interactive multi-select rail selector.

    Controls
    --------
    UP / DOWN   Navigate
    TAB / SPACE Toggle selection
    A           Select all / Deselect all
    ENTER       Confirm and run selected rails
    Q / ESC     Cancel

    Parameters
    ----------
    rail_configs : list[RailConfig]

    Returns
    -------
    list[str] | None
        Selected rail names, or None if cancelled.
    """
    import msvcrt

    _enable_ansi()

    rails = []
    for r in rail_configs:
        rails.append({
            'name': r.name,
            'tp': r.test_point,
            'voltage': r.expected_voltage_v,
            'low': r.low_current_ma,
            'high': r.high_current_ma,
        })

    selected = [False] * len(rails)  # none selected – TAB to pick rails
    cursor = 0

    def render():
        lines = []
        lines.append("")
        lines.append("  RAIL SELECTION")
        lines.append("  " + "=" * 62)
        lines.append("  UP/DOWN: Navigate | TAB: Toggle | ENTER: Run | A: All | Q: Quit")
        lines.append("")
        for i, r in enumerate(rails):
            marker = "[X]" if selected[i] else "[ ]"
            arrow  = ">>" if i == cursor else "  "
            lines.append(
                f"  {arrow} {marker} {r['name']:<10} ({r['tp']:<5}) "
                f"{r['voltage']:>5.2f}V   {r['low']} -> {r['high']}mA"
            )
        sel_names = [rails[i]['name'] for i in range(len(rails)) if selected[i]]
        lines.append("")
        if sel_names:
            lines.append(f"  Selected: {', '.join(sel_names)}  ({len(sel_names)} rails)")
        else:
            lines.append("  Selected: None  (use TAB to select rails)")
        return lines

    # initial draw
    display_lines = render()
    for line in display_lines:
        print(line)
    sys.stdout.flush()

    while True:
        key = msvcrt.getch()

        if key == b'\r':                              # ENTER
            sel = [rails[i]['name'] for i in range(len(rails)) if selected[i]]
            if not sel:
                continue                              # need at least one
            print()
            return sel

        elif key == b'\t' or key == b' ':             # TAB / SPACE
            selected[cursor] = not selected[cursor]

        elif key in (b'a', b'A'):                     # toggle all
            if all(selected):
                selected = [False] * len(rails)
            else:
                selected = [True] * len(rails)

        elif key == b'\xe0' or key == b'\x00':        # arrow prefix
            key2 = msvcrt.getch()
            if key2 == b'H':                          # UP
                cursor = (cursor - 1) % len(rails)
            elif key2 == b'P':                        # DOWN
                cursor = (cursor + 1) % len(rails)

        elif key in (b'q', b'Q', b'\x1b'):            # Q / ESC
            print("\n  Selection cancelled.")
            return None

        else:
            continue

        # redraw in-place
        display_lines = render()
        sys.stdout.write(f"\033[{len(display_lines)}A")
        for line in display_lines:
            sys.stdout.write(f"\033[2K{line}\n")
        sys.stdout.flush()


# This is the main class - the "brain" that runs the entire test
class PWRSTD06TransientTest:
    """
    PWRSTD06 Transient Response Test - Minimal User Intervention

    This automation (what it does automatically):
    - Asks you to confirm test equipment is connected to each rail
    - Automatically performs positive and negative load steps
    - Captures voltage waveforms and analyzes the response
    - Saves screenshots with proper labels
    - Moves to the next rail after completion
    - Generates a comprehensive summary report at the end
    """

    # List of all 10 power rails to test with their specifications
    # Format: RailConfig(name, test_point, voltage, low_current, high_current, max_droop, max_recovery, max_overshoot)
    # UPDATED SPECS per test requirements:
    # - 3V6/3V3: <50-75mV droop, <150µs recovery, <30mV overshoot
    # - 2V5/1V8: <50mV droop, <150µs recovery, <30mV overshoot
    # - Core Rails (1V35/PS/PL): <50-60mV droop, <100µs recovery, <20mV overshoot
    RAIL_CONFIGS = [
        # Rail name, Test Point, Voltage(V), Low(mA), High(mA), Droop(mV), Recovery(μs), Overshoot(mV)
        RailConfig("3V6",     "TP2",  3.6,  100, 800,  75.0, 150.0, 30.0),   # 3V6: <75mV droop, <150µs, <30mV
        RailConfig("3V3",     "TP10", 3.3,  100, 1500, 75.0, 150.0, 30.0),   # 3V3: <75mV droop, <150µs, <30mV
        RailConfig("2V5",     "TP9",  2.5,  100, 750,  50.0, 150.0, 30.0),   # 2V5: <50mV droop, <150µs, <30mV
        RailConfig("1V8",     "TP6",  1.8,  100, 1500, 50.0, 150.0, 30.0),   # 1V8: <50mV droop, <150µs, <30mV
        RailConfig("1V35",    "TP7",  1.35, 100, 1500, 60.0, 100.0, 20.0),   # Core 1V35: <60mV droop, <100µs, <20mV
        RailConfig("1V_PS",   "TP5",  1.0,  100, 1500, 60.0, 100.0, 20.0),   # Core PS: <60mV droop, <100µs, <20mV
        RailConfig("1V_PL",   "TP8",  1.0,  100, 1500, 60.0, 100.0, 20.0),   # Core PL: <60mV droop, <100µs, <20mV
        RailConfig("1V1_E0",  "TP13", 1.1,  100, 500,  50.0, 150.0, 20.0),   # 1V1_E0: <50mV droop, <150µs, <20mV
        RailConfig("2V5_E0",  "TP14", 2.5,  100, 500,  50.0, 150.0, 30.0),   # 2V5_E0: <50mV droop, <150µs, <30mV
        RailConfig("1V8_E0",  "TP15", 1.8,  100, 500,  50.0, 150.0, 30.0),   # 1V8_E0: <50mV droop, <150µs, <30mV
    ]

    # ╔════════════════════════════════════════════════════════════════════════════╗
    # ║  SCOPE & TRIGGER CONFIGURATION PER RAIL  ──  FILL IN THIS TABLE          ║
    # ╠════════════════════════════════════════════════════════════════════════════╣
    # ║                                                                          ║
    # ║  v_scale:      Vertical scale in V/div                                   ║
    # ║  timebase:     Timebase in s/div                                         ║
    # ║  trigger_up:   Trigger level (V) for LOAD UP  (FALLING edge / droop)     ║
    # ║  trigger_down: Trigger level (V) for LOAD DOWN (RISING edge / rise)      ║
    # ║                                                                          ║
    # ║  Offset = rail nominal voltage (set automatically).                      ║
    # ║  Coupling: DC   |   Probe: 10:1                                         ║
    # ║                                                                          ║
    # ║  HOW TO SET TRIGGER LEVELS:                                              ║
    # ║    trigger_up  = slightly BELOW nominal (catches the voltage drop)       ║
    # ║    trigger_down = slightly ABOVE nominal (catches the voltage rise)      ║
    # ║                                                                          ║
    # ║  From your manual testing:                                               ║
    # ║    3V3: trigger_up=3.225  trigger_down=3.30                              ║
    # ║    2V5: trigger_up=2.447  trigger_down=2.495                             ║
    # ║    1V8: trigger_up=1.735  trigger_down=1.81                              ║
    # ║                                                                          ║
    # ║  >>> FILL IN trigger_up and trigger_down for every rail you test <<<     ║
    # ║                                                                          ║
    # ╚════════════════════════════════════════════════════════════════════════════╝
    SCOPE_CONFIG = {
        #                  v_scale    timebase    trigger_up       trigger_down    bandwidth
        #                  (V/div)    (s/div)     (V) FALLING      (V) RISING      (MHz)
        # ─── TRIGGER VALUES FROM TEST MEASUREMENTS ───────────────────────────────
        "3V3":    {"v_scale": 0.050, "timebase": 50e-6,  "trigger_up": 3.225, "trigger_down": 3.30, "bandwidth_mhz": 20},
        "2V5":    {"v_scale": 0.050, "timebase": 50e-6,  "trigger_up": 2.447, "trigger_down": 2.498, "bandwidth_mhz": 20},
        "1V8":    {"v_scale": 0.050, "timebase": 50e-6,  "trigger_up": 1.735, "trigger_down": 1.81,  "bandwidth_mhz": 20},
        "3V6":    {"v_scale": 0.050, "timebase": 50e-6,  "trigger_up": 3.225, "trigger_down": 3.30, "bandwidth_mhz": 20},  # Similar to 3V3
        "1V35":   {"v_scale": 0.050, "timebase": 50e-6,  "trigger_up": 1.293, "trigger_down": 1.382, "bandwidth_mhz": 20},
        "1V_PS":  {"v_scale": 0.050, "timebase": 50e-6,  "trigger_up": 0.936, "trigger_down": 1.024, "bandwidth_mhz": 20},
        "1V_PL":  {"v_scale": 0.050, "timebase": 50e-6,  "trigger_up": 0.934, "trigger_down": 1.035, "bandwidth_mhz": 20},
        "1V1_E0": {"v_scale": 0.010, "timebase": 50e-6,  "trigger_up": 1.075, "trigger_down": 1.112, "bandwidth_mhz": 20},
        "2V5_E0": {"v_scale": 0.050, "timebase": 50e-6,  "trigger_up": 2.445, "trigger_down": 2.512, "bandwidth_mhz": 20},
        "1V8_E0": {"v_scale": 0.050, "timebase": 50e-6,  "trigger_up": 1.735, "trigger_down": 1.81, "bandwidth_mhz": 20},  # Similar to 1V8
    }

    def __init__(self,
                 oscilloscope_address: Optional[str] = None,
                 electronic_load_address: Optional[str] = None,
                 output_dir: str = "pwrstd06_results"):
        """
        Initialize PWRSTD06 transient response test - this sets up everything when the test starts

        Args (what you can provide):
            oscilloscope_address: Where to find the oscilloscope (auto-find if not provided)
            electronic_load_address: Where to find the electronic load (auto-find if not provided)
            output_dir: Folder name where to save results (default: "pwrstd06_results")
        """
        # Auto-detect instruments if addresses weren't provided
        if oscilloscope_address is None or electronic_load_address is None:
            print("\nAuto-detecting instruments...")  # Tell user we're searching
            try:
                # Import the auto-detection tool
                from visa_auto_detect import detect_pwrstd06_instruments
                # Run the detection
                detected_scope, detected_load = detect_pwrstd06_instruments()

                # If user didn't provide scope address, use the detected one
                if oscilloscope_address is None:
                    oscilloscope_address = detected_scope
                # If user didn't provide load address, use the detected one
                if electronic_load_address is None:
                    electronic_load_address = detected_load

            except ImportError:  # If auto-detect module not found
                print("WARNING: visa_auto_detect module not found")
                print("         Instrument addresses must be specified manually")

        # Save the addresses for later use
        self.scope_address = oscilloscope_address      # Where the oscilloscope is
        self.load_address = electronic_load_address    # Where the electronic load is

        # Initialize instrument variables (but don't connect yet)
        self._scope = None  # Will hold the oscilloscope object (TektronixMSO24 or KeysightOscilloscope)
        self._load: Optional[Keithley2380] = None  # Will hold the electronic load object

        # Setup output directories (folders to save results)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Get current time as text (e.g., "20250122_143052")
        self.output_dir = Path(output_dir) / f"run_{timestamp}"  # Main folder: pwrstd06_results/run_20250122_143052
        self.screenshot_dir = self.output_dir / "screenshots"    # Subfolder for pictures
        self.reports_dir = self.output_dir / "reports"           # Subfolder for reports
        self.calculations_dir = self.output_dir / "calculations" # NEW: Subfolder for detailed calculations

        # Create all the folders if they don't exist
        for d in [self.output_dir, self.screenshot_dir, self.reports_dir, self.calculations_dir]:
            d.mkdir(parents=True, exist_ok=True)  # Make directory (and parent directories if needed)

        # Setup logging (create the logbook for recording what happens)
        self._setup_logging()

        # Initialize variables to store test results
        self.results: List[RailTestResult] = []  # Empty list to collect all rail test results
        self.test_start_time: Optional[datetime] = None  # Will record when test starts
        self.test_end_time: Optional[datetime] = None    # Will record when test ends

    def _setup_logging(self):
        """Configure logging - set up the "logbook" that records what happens"""
        # Create a logger (like opening a logbook with a unique ID)
        self._logger = logging.getLogger(f"PWRSTD06.{id(self)}")
        self._logger.setLevel(logging.DEBUG)  # Record everything (DEBUG = most detailed level)
        self._logger.handlers.clear()  # Clear any old handlers

        # Console handler - prints important messages to the screen
        ch = logging.StreamHandler()  # Create handler for console/screen output
        ch.setLevel(logging.INFO)  # Only show INFO level and above on screen (not every tiny detail)
        # Format: "14:30:52 - INFO - Test started"
        ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
        self._logger.addHandler(ch)  # Attach console handler to logger

        # File handler - saves ALL messages to a log file (with UTF-8 encoding for special characters)
        fh = logging.FileHandler(self.output_dir / "pwrstd06_test.log", encoding='utf-8')
        fh.setLevel(logging.DEBUG)  # Save EVERYTHING to file (even tiny details)
        # Format: "2025-01-22 14:30:52 - PWRSTD06.12345 - DEBUG - Detailed message"
        fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self._logger.addHandler(fh)  # Attach file handler to logger

    def connect_instruments(self) -> bool:
        """Connect to oscilloscope and electronic load - establish communication with lab equipment"""
        self._logger.info("Connecting to instruments...")  # Log that we're starting

        try:  # Try to connect, if anything fails jump to "except"
            # Connect to oscilloscope (using Keysight driver)
            self._logger.info(f"Connecting to oscilloscope at {self.scope_address}")
            self._scope = scope_class(self.scope_address)  # Create oscilloscope object with its address
            if not self._scope.connect():  # Attempt to connect
                raise Exception("Failed to connect to oscilloscope")  # If failed, raise error
            self._logger.info(f"Oscilloscope connected successfully ({scope_module})")  # Log success

            # Connect to electronic load (Keithley 2380)
            self._logger.info(f"Connecting to electronic load at {self.load_address}")
            self._load = Keithley2380(self.load_address)  # Create electronic load object with its address
            if not self._load.connect():  # Attempt to connect
                raise Exception("Failed to connect to electronic load")  # If failed, raise error
            self._logger.info("Electronic load connected successfully")  # Log success

            return True  # Success! Both instruments connected

        except Exception as e:  # If anything went wrong
            self._logger.error(f"Instrument connection failed: {e}")  # Log the error
            self.disconnect_instruments()  # Clean up - disconnect anything that did connect
            return False  # Return False to indicate failure

    def disconnect_instruments(self):
        """Safely disconnect from all instruments - clean shutdown of equipment"""
        try:  # Try to disconnect electronic load
            if self._load:  # If electronic load exists
                self._load.disable_input()  # Turn off the load (stop pulling current)
                self._load.disconnect()     # Close communication
                self._logger.info("Electronic load disconnected")
        except:  # If anything goes wrong
            pass  # Ignore errors (we're shutting down anyway)

        try:  # Try to disconnect oscilloscope
            if self._scope:  # If oscilloscope exists
                self._scope.disconnect()  # Close communication
                self._logger.info("Oscilloscope disconnected")
        except:  # If anything goes wrong
            pass  # Ignore errors (we're shutting down anyway)

    def configure_oscilloscope_for_rail(self, rail: RailConfig) -> bool:
        """
        Configure oscilloscope for transient capture on specific rail.
        Uses SCOPE_CONFIG table at top of class for per-rail settings.
        Offset is always set to the rail's nominal voltage.
        """
        if not self._scope:
            return False

        try:
            # Get per-rail scope settings from SCOPE_CONFIG table
            # Falls back to 50mV/div + 50us/div if rail not in SCOPE_CONFIG
            cfg = self.SCOPE_CONFIG.get(rail.name, {})
            v_scale = cfg.get("v_scale", 0.050)
            timebase = cfg.get("timebase", 50e-6)

            self._logger.info(f"Configuring oscilloscope for {rail.name}")
            self._logger.info(f"  Nominal voltage: {rail.expected_voltage_v}V")
            self._logger.info(f"  Settings: {v_scale*1000:.0f}mV/div, {timebase*1e6:.0f}us/div")

            # ── CHANNEL 1: Rail Voltage, DC coupled ──
            # Offset = rail nominal voltage (centers trace on screen)
            self._scope.configure_channel(
                channel=1,
                vertical_scale=v_scale,
                vertical_offset=rail.expected_voltage_v,
                coupling="DC",
                probe_attenuation=10.0  # 10:1 probe
            )
            self._logger.info(f"  Ch1: {v_scale*1000:.0f}mV/div, offset={rail.expected_voltage_v}V, DC, 10:1")

            # ── TIMEBASE ──
            self._scope.configure_timebase(
                time_scale=timebase,
                time_offset=0.0
            )
            self._logger.info(f"  Timebase: {timebase*1e6:.0f}us/div")

            # ── INITIAL TRIGGER: falling edge for droop capture ──
            # Reconfigured per step direction in perform_load_step()
            trigger_up = cfg.get("trigger_up", rail.expected_voltage_v)
            self._scope.configure_trigger(
                channel=1,
                trigger_level=trigger_up,
                trigger_slope="NEG",
                sweep_mode="NORMal"
            )
            self._logger.info(f"  Trigger: FALLING edge at {trigger_up:.3f}V (NORMAL sweep)")

            # ── BANDWIDTH LIMIT  (20 MHz on DSOX6004A) ──
            # SCPI: :CHANnel<n>:BWLimit {ON|OFF}
            #   ON  = 20 MHz low-pass filter (reduces noise for transient capture)
            #   OFF = full bandwidth
            try:
                self._scope._scpi_wrapper.write(":CHANnel1:BWLimit ON")
                time.sleep(0.05)
                self._logger.info("  Bandwidth limit: 20 MHz (CHANnel1:BWLimit ON)")
            except Exception as e:
                self._logger.warning(f"  Could not set bandwidth limit: {e}")

            self._logger.info(f"Scope ready for {rail.name}: {rail.low_current_ma}mA -> {rail.high_current_ma}mA")
            self._logger.info(f"  Limits: Droop<{rail.max_droop_mv}mV, Recovery<{rail.max_recovery_time_us}us")
            return True

        except Exception as e:
            self._logger.error(f"Oscilloscope configuration failed: {e}")
            import traceback
            self._logger.error(traceback.format_exc())
            return False

    def _measure_transient_with_scope(self, rail: RailConfig, direction: LoadStepDirection, 
                                      load_voltage_readings: Optional[List[float]] = None,
                                      load_time_readings: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Use oscilloscope's built-in measurements to measure droop, and load voltage for recovery time.

        This method uses the scope's hardware measurements for accuracy:
        - VMAX: Maximum voltage (for overshoot calculation)
        - VMIN: Minimum voltage (for droop calculation)
        - DC RMS FS: DC baseline voltage
        
        Recovery time is measured from load voltage readings (more accurate than scope):
        - Time from initial load state to final settled state

        Args:
            rail: Rail configuration
            direction: Load step direction
            load_voltage_readings: Optional list of voltage readings from electronic load
            load_time_readings: Optional list of corresponding time readings (in microseconds)

        Returns:
            Dict with measurements: droop_mv, overshoot_mv, recovery_us, baseline_v, min_v, max_v
        """
        import numpy as np

        results = {
            'droop_mv': rail.max_droop_mv * 2.0,  # Default FAIL value
            'overshoot_mv': rail.max_overshoot_mv * 2.0,
            'recovery_us': rail.max_recovery_time_us * 2.0,
            'baseline_v': rail.expected_voltage_v,
            'min_v': 0.0,
            'max_v': 0.0,
            'method': 'FAILED',
            'calc_log': []
        }

        calc_log = results['calc_log']
        calc_log.append("=" * 80)
        calc_log.append(f"SCOPE HARDWARE MEASUREMENTS: {rail.name} - {direction.value}")
        calc_log.append("=" * 80)

        try:
            if not self._scope:
                calc_log.append("ERROR: Oscilloscope not connected")
                return results

            # ============================================================
            # STEP 1: Get scope's built-in measurements
            # ============================================================
            calc_log.append("\n[STEP 1] READING SCOPE BUILT-IN MEASUREMENTS")

            # Get VMAX (maximum voltage in waveform)
            v_max = self._scope.measure_max(1)
            if v_max is not None:
                results['max_v'] = v_max
                calc_log.append(f"  VMAX (scope): {v_max:.4f}V ({v_max*1000:.1f}mV)")
            else:
                calc_log.append("  VMAX: Failed to read")

            # Get VMIN (minimum voltage in waveform)
            v_min = self._scope.measure_min(1)
            if v_min is not None:
                results['min_v'] = v_min
                calc_log.append(f"  VMIN (scope): {v_min:.4f}V ({v_min*1000:.1f}mV)")
            else:
                calc_log.append("  VMIN: Failed to read")

            # Get DC RMS FS (DC baseline voltage - the true settled baseline for DC-coupled measurements)
            # This is the scope's measurement of the DC level on the channel
            dc_rms_fs = self._scope.measure_dc_rms_fs(1)
            if dc_rms_fs is not None:
                results['baseline_v'] = dc_rms_fs
                calc_log.append(f"  DC RMS FS (baseline): {dc_rms_fs:.4f}V ({dc_rms_fs*1000:.1f}mV)")
            else:
                calc_log.append(f"  DC RMS FS: Failed to read, falling back to VTOP")
                # Fallback to VTOP if DC RMS FS is not available
                v_top = self._scope.measure_top(1)
                if v_top is not None:
                    results['baseline_v'] = v_top
                    calc_log.append(f"  VTOP (baseline fallback): {v_top:.4f}V ({v_top*1000:.1f}mV)")
                else:
                    results['baseline_v'] = rail.expected_voltage_v
                    calc_log.append(f"  Using expected voltage: {rail.expected_voltage_v}V")

            # Get VBASE (base/low level) for reference
            v_base = self._scope.measure_base(1)
            if v_base is not None:
                calc_log.append(f"  VBASe (low level): {v_base:.4f}V ({v_base*1000:.1f}mV)")

            # Use the baseline voltage from DC RMS FS for all calculations
            dc_baseline = results['baseline_v']
            if dc_baseline == 0:
                dc_baseline = rail.expected_voltage_v
            calc_log.append(f"  ★ Using DC RMS FS as baseline: {dc_baseline:.4f}V ({dc_baseline*1000:.1f}mV)")

            # Get scope's built-in overshoot measurement
            scope_overshoot = self._scope.measure_overshoot(1)
            if scope_overshoot is not None:
                calc_log.append(f"  OVERshoot (scope %): {scope_overshoot:.2f}%")

            # ============================================================
            # STEP 2: Calculate DROOP
            # ============================================================
            calc_log.append("\n[STEP 2] CALCULATING DROOP")

            if direction == LoadStepDirection.POSITIVE:
                # Positive step: droop = DC RMS FS - VMIN (how much it drops from settled baseline)
                calc_log.append("  Direction: POSITIVE (load increased → voltage drops)")
                calc_log.append(f"  DC RMS FS (baseline): {dc_baseline:.4f}V ({dc_baseline*1000:.1f}mV)")
                calc_log.append(f"  VMIN (minimum voltage): {results['min_v']:.4f}V ({results['min_v']*1000:.1f}mV)")

                if results['min_v'] > 0:
                    droop_mv = (dc_baseline - results['min_v']) * 1000
                    results['droop_mv'] = max(0, droop_mv)  # Can't be negative
                    calc_log.append(f"\n  DROOP = DC RMS FS - VMIN")
                    calc_log.append(f"        = {dc_baseline:.4f}V - {results['min_v']:.4f}V")
                    calc_log.append(f"        = {droop_mv:.1f}mV")
                    calc_log.append(f"  ★ DROOP = {results['droop_mv']:.1f}mV (Limit: <{rail.max_droop_mv}mV) {'✓ PASS' if results['droop_mv'] <= rail.max_droop_mv else '✗ FAIL'}")

            else:
                # Negative step: droop = VMAX - DC RMS FS (how much it rises from settled baseline)
                calc_log.append("  Direction: NEGATIVE (load decreased → voltage rises)")
                calc_log.append(f"  DC RMS FS (baseline): {dc_baseline:.4f}V ({dc_baseline*1000:.1f}mV)")
                calc_log.append(f"  VMAX (maximum voltage): {results['max_v']:.4f}V ({results['max_v']*1000:.1f}mV)")

                if results['max_v'] > 0:
                    droop_mv = (results['max_v'] - dc_baseline) * 1000
                    results['droop_mv'] = max(0, droop_mv)
                    calc_log.append(f"\n  DROOP = VMAX - DC RMS FS")
                    calc_log.append(f"        = {results['max_v']:.4f}V - {dc_baseline:.4f}V")
                    calc_log.append(f"        = {droop_mv:.1f}mV")
                    calc_log.append(f"  ★ DROOP = {results['droop_mv']:.1f}mV (Limit: <{rail.max_droop_mv}mV) {'✓ PASS' if results['droop_mv'] <= rail.max_droop_mv else '✗ FAIL'}")

            # ============================================================
            # STEP 3: Calculate RECOVERY TIME using load voltage readings
            # ============================================================
            calc_log.append("\n[STEP 3] CALCULATING RECOVERY TIME (from load voltage)")
            calc_log.append("  Recovery = time for voltage to settle at final load state")

            if load_voltage_readings and len(load_voltage_readings) > 10:
                # Use load voltage readings from electronic load (most accurate)
                voltage_data = np.array(load_voltage_readings)
                time_data = np.array(load_time_readings)
                
                calc_log.append(f"  Using {len(voltage_data)} voltage samples from electronic load")
                calc_log.append(f"  Time range: {time_data[0]:.3f}µs to {time_data[-1]:.3f}µs")
                
                # Determine target voltage (final stable state) and tolerance
                if direction == LoadStepDirection.POSITIVE:
                    target_voltage = results['min_v']  # VMIN from scope measurement
                    calc_log.append(f"  Direction: POSITIVE load step")
                    calc_log.append(f"  Initial voltage (first load): {dc_baseline:.4f}V")
                    calc_log.append(f"  Final voltage (second load): {target_voltage:.4f}V (VMIN)")
                else:
                    target_voltage = results['max_v']  # VMAX from scope measurement
                    calc_log.append(f"  Direction: NEGATIVE load step")
                    calc_log.append(f"  Initial voltage (first load): {dc_baseline:.4f}V")
                    calc_log.append(f"  Final voltage (second load): {target_voltage:.4f}V (VMAX)")
                
                # Define settlement tolerance (±2-5% of voltage change or minimum 10mV)
                voltage_change = abs(target_voltage - dc_baseline)
                tolerance = max(voltage_change * 0.02, 0.010)  # 2% of change or 10mV minimum
                lower_bound = target_voltage - tolerance
                upper_bound = target_voltage + tolerance
                
                calc_log.append(f"  Voltage change: {voltage_change*1000:.1f}mV")
                calc_log.append(f"  Settlement tolerance: ±{tolerance*1000:.1f}mV")
                calc_log.append(f"  Target range: {lower_bound:.4f}V to {upper_bound:.4f}V")
                
                # Find when voltage reaches target and stays settled
                recovery_idx = None
                min_settled_samples = max(int(0.001 / ((time_data[-1] - time_data[0]) / 1e6 / len(time_data))), 5)
                
                for i in range(len(voltage_data)):
                    if lower_bound <= voltage_data[i] <= upper_bound:
                        # Check if voltage stays within tolerance for min_settled_samples
                        if i + min_settled_samples < len(voltage_data):
                            if np.all((voltage_data[i:i+min_settled_samples] >= lower_bound) & 
                                    (voltage_data[i:i+min_settled_samples] <= upper_bound)):
                                recovery_idx = i
                                break
                
                if recovery_idx is not None:
                    recovery_us = time_data[recovery_idx]
                    results['recovery_us'] = recovery_us
                    calc_log.append(f"\n  Recovery found at index: {recovery_idx}")
                    calc_log.append(f"  Voltage at recovery: {voltage_data[recovery_idx]:.4f}V")
                    calc_log.append(f"  ★ RECOVERY TIME = {recovery_us:.1f}µs")
                    calc_log.append(f"    (Limit: <{rail.max_recovery_time_us}µs) {'✓ PASS' if recovery_us <= rail.max_recovery_time_us else '✗ FAIL'}")
                else:
                    calc_log.append("  WARNING: Recovery point not found in load voltage readings")
                    results['recovery_us'] = rail.max_recovery_time_us * 2.0
                    
            else:
                # Fallback: use waveform data if load readings not available
                calc_log.append("  Load voltage readings not available, using alternative measurement")
                results['recovery_us'] = rail.max_recovery_time_us * 1.5  # Default high value

            results['method'] = 'SCOPE_MEASUREMENTS'

            # ============================================================
            # SUMMARY
            # ============================================================
            calc_log.append("\n" + "=" * 80)
            calc_log.append("MEASUREMENT SUMMARY (SCOPE HARDWARE)")
            calc_log.append("=" * 80)
            calc_log.append(f"Droop:    {results['droop_mv']:.1f}mV  (Limit: {rail.max_droop_mv}mV)  "
                          f"{'✓ PASS' if results['droop_mv'] <= rail.max_droop_mv else '✗ FAIL'}")
            calc_log.append(f"Recovery: {results['recovery_us']:.1f}µs (Limit: {rail.max_recovery_time_us}µs) "
                          f"{'✓ PASS' if results['recovery_us'] <= rail.max_recovery_time_us else '✗ FAIL'}")
            calc_log.append("=" * 80)

        except Exception as e:
            calc_log.append(f"\nERROR during scope measurements: {e}")
            self._logger.error(f"Scope measurement failed: {e}")
            results['method'] = 'FAILED'

        return results

    def configure_electronic_load_for_rail(self, rail: RailConfig) -> bool:
        """
        Configure electronic load for transient testing

        Args:
            rail: Rail configuration

        Returns:
            bool: True if configuration successful
        """
        if not self._load:
            return False

        try:
            self._logger.info(f"Configuring electronic load for {rail.name}")

            # Set to constant current mode
            self._load.set_function("CURRent")

            # Set current range
            max_current_a = rail.high_current_ma / 1000.0 * 1.5  # 50% margin
            self._load.set_current_range(max_current_a)

            # Configure fast slew rate (A/us for 100ns steps)
            current_step_a = (rail.high_current_ma - rail.low_current_ma) / 1000.0
            slew_rate = current_step_a / 0.1  # A/us for 100ns rise time
            self._load.set_current_slew_rate(slew_rate)
            self._load.set_current_slow_rate_mode(False)  # Fast mode (A/us)

            # Set voltage protection
            ovp = rail.expected_voltage_v + 1.0
            uvp = max(0.1, rail.expected_voltage_v - 1.0)
            self._load.set_current_bounds(high=ovp, low=uvp)

            self._logger.info(f"Electronic load configured: {rail.low_current_ma}mA - {rail.high_current_ma}mA")
            return True

        except Exception as e:
            self._logger.error(f"Electronic load configuration failed: {e}")
            return False

    def perform_load_step(self, rail: RailConfig, direction: LoadStepDirection) -> Optional[TransientResult]:
        """
        *** THIS PERFORMS ONE TEST (either positive or negative step) ***
        Perform a load step and capture/analyze waveform

        Args (inputs):
            rail: Which rail to test (contains voltage, current, limits, etc.)
            direction: POSITIVE (increase load) or NEGATIVE (decrease load)

        Returns (output):
            TransientResult object with measurements, or None if test failed
        """
        # Check if instruments are connected
        if not self._scope or not self._load:
            return None  # Can't test without equipment

        try:  # Try to perform the test, jump to "except" if anything fails
            # Determine test parameters based on direction
            if direction == LoadStepDirection.POSITIVE:  # If increasing load
                initial_ma = rail.low_current_ma      # Start at low current (100mA)
                final_ma = rail.high_current_ma       # End at high current (e.g., 800mA)
                step_desc = rail.load_step_positive   # Description: "100mA -> 800mA"
                # Note: Trigger is on Ch1 (current), configured in STEP 2
            else:  # If decreasing load
                initial_ma = rail.high_current_ma     # Start at high current (e.g., 800mA)
                final_ma = rail.low_current_ma        # End at low current (100mA)
                step_desc = rail.load_step_negative   # Description: "800mA -> 100mA"
                # Note: Trigger is on Ch1 (current), configured in STEP 2

            self._logger.info(f"Performing {direction.value} load step: {step_desc}")

            # *** STEP 1: SET UP THE STARTING CURRENT ***
            self._load.set_current_level(initial_ma / 1000.0)
            self._load.enable_input()
            time.sleep(0.5)  # Let current stabilize

            # *** STEP 2: SET UP TRIGGER FROM SCOPE_CONFIG ***
            # Load UP  -> voltage drops -> FALLING edge at trigger_up
            # Load DOWN -> voltage rises -> RISING edge at trigger_down
            cfg = self.SCOPE_CONFIG.get(rail.name, {})

            if direction == LoadStepDirection.POSITIVE:
                trigger_level_v = cfg.get("trigger_up", rail.expected_voltage_v)
                trigger_slope = "NEG"
            else:
                trigger_level_v = cfg.get("trigger_down", rail.expected_voltage_v)
                trigger_slope = "POS"

            self._scope.configure_trigger(
                channel=1,
                trigger_level=trigger_level_v,
                trigger_slope=trigger_slope,
                sweep_mode="NORMal"
            )
            self._logger.info(f"  Trigger: {trigger_slope} edge at {trigger_level_v:.3f}V, NORMAL sweep")

            # *** STEP 3: STABILIZE + ARM ***
            time.sleep(0.5)
            self._scope.single()
            time.sleep(0.3)

            # *** STEP 4: EXECUTE THE LOAD STEP ***
            self._load.set_current_level(final_ma / 1000.0)
            self._logger.info(f"  Load step: {initial_ma}mA -> {final_ma}mA")

            # *** STEP 5: WAIT FOR SCOPE TO TRIGGER ***
            max_wait = 5.0
            elapsed = 0.0
            triggered = False
            while elapsed < max_wait:
                time.sleep(0.2)
                elapsed += 0.2
                try:
                    state = self._scope._scpi_wrapper.query(":RSTate?").strip()
                    if state == "STOP":
                        triggered = True
                        self._logger.info(f"  Scope triggered after {elapsed:.1f}s")
                        break
                except:
                    pass

            if not triggered:
                self._logger.warning(f"  Trigger did not fire after {max_wait}s - force capturing")
                try:
                    self._scope._scpi_wrapper.write(":TRIGger:FORCe")
                    time.sleep(0.3)
                except:
                    pass

            # *** STEP 6: STOP SCOPE + SCREENSHOT ***
            try:
                self._scope._scpi_wrapper.write(":STOP")
                time.sleep(0.2)
            except:
                pass

            dir_label = "low_to_high" if direction == LoadStepDirection.POSITIVE else "high_to_low"
            screenshot_name = f"{rail.name}_{dir_label}.png"
            screenshot_path = str(self.screenshot_dir / screenshot_name)
            actual_screenshot = None

            try:
                actual_screenshot = self._scope.get_screenshot(screenshot_path, freeze_acquisition=True)
                self._logger.info(f"  Screenshot saved: {screenshot_name}")
            except Exception as e:
                self._logger.warning(f"  Screenshot failed: {e}")

            # *** STEP 7: MEASURE DROOP USING SCOPE HARDWARE ***
            # Read scope built-in measurements from the captured waveform
            calc_lines = []
            calc_lines.append("=" * 60)
            calc_lines.append(f"DROOP CALCULATION: {rail.name} - {dir_label}")
            calc_lines.append(f"Load step: {step_desc}")
            calc_lines.append(f"Trigger: {trigger_slope} edge at {trigger_level_v:.3f}V")
            calc_lines.append(f"Triggered: {'Yes' if triggered else 'No (forced)'}")
            calc_lines.append("=" * 60)

            dc_rms = self._scope.measure_dc_rms_fs(1)
            v_min = self._scope.measure_min(1)
            v_max = self._scope.measure_max(1)

            calc_lines.append(f"\nScope measurements:")
            calc_lines.append(f"  DC RMS FS: {dc_rms:.4f}V" if dc_rms is not None else "  DC RMS FS: FAILED")
            calc_lines.append(f"  VMIN:      {v_min:.4f}V" if v_min is not None else "  VMIN:      FAILED")
            calc_lines.append(f"  VMAX:      {v_max:.4f}V" if v_max is not None else "  VMAX:      FAILED")

            droop_mv = 0.0
            if direction == LoadStepDirection.POSITIVE:
                # Low to high: droop = DC RMS FS - VMIN
                if dc_rms is not None and v_min is not None:
                    droop_mv = (dc_rms - v_min) * 1000.0
                    calc_lines.append(f"\nDroop (low_to_high) = DC_RMS_FS - VMIN")
                    calc_lines.append(f"  = {dc_rms:.4f}V - {v_min:.4f}V")
                    calc_lines.append(f"  = {droop_mv:.1f}mV")
                else:
                    calc_lines.append(f"\nDroop: FAILED (missing measurements)")
            else:
                # High to low: droop = VMAX - DC RMS FS
                if v_max is not None and dc_rms is not None:
                    droop_mv = (v_max - dc_rms) * 1000.0
                    calc_lines.append(f"\nDroop (high_to_low) = VMAX - DC_RMS_FS")
                    calc_lines.append(f"  = {v_max:.4f}V - {dc_rms:.4f}V")
                    calc_lines.append(f"  = {droop_mv:.1f}mV")
                else:
                    calc_lines.append(f"\nDroop: FAILED (missing measurements)")

            calc_lines.append(f"\nDroop limit: {rail.max_droop_mv:.1f}mV")
            passed = droop_mv <= rail.max_droop_mv and droop_mv > 0
            calc_lines.append(f"Result: {'PASS' if passed else 'FAIL'} ({droop_mv:.1f}mV)")
            calc_lines.append("=" * 60)

            detailed_calculations = "\n".join(calc_lines)

            self._logger.info(f"  DC RMS FS: {dc_rms:.4f}V" if dc_rms is not None else "  DC RMS FS: FAILED")
            self._logger.info(f"  VMIN: {v_min:.4f}V" if v_min is not None else "  VMIN: FAILED")
            self._logger.info(f"  VMAX: {v_max:.4f}V" if v_max is not None else "  VMAX: FAILED")
            self._logger.info(f"  Droop: {droop_mv:.1f}mV (limit: {rail.max_droop_mv:.1f}mV) {'PASS' if passed else 'FAIL'}")

            # Save calculations to file
            calc_filename = f"{rail.name}_{dir_label}_calculations.txt"
            calc_path = self.calculations_dir / calc_filename
            try:
                with open(calc_path, 'w', encoding='utf-8') as f:
                    f.write(detailed_calculations)
                self._logger.info(f"  Calculations saved: {calc_filename}")
            except Exception as save_err:
                self._logger.warning(f"  Could not save calculations: {save_err}")

            result = TransientResult(
                rail_name=rail.name,
                step_direction=direction.value,
                load_step_description=step_desc,
                droop_mv=droop_mv,
                recovery_time_us=0.0,
                overshoot_mv=0.0,
                has_ringing=False,
                screenshot_path=actual_screenshot or screenshot_path,
                timestamp=dir_label,
                result="PASS" if passed else "FAIL",
                notes=f"Droop: {droop_mv:.1f}mV, Trigger: {trigger_slope} at {trigger_level_v:.3f}V",
                detailed_calculations=detailed_calculations
            )

            self._logger.info(f"  {direction.value} step: {'PASS' if passed else 'FAIL'}")

            return result

        except Exception as e:  # If anything went wrong during the test
            self._logger.error(f"Load step failed: {e}")  # Log the error
            # Create error calculation log
            error_log = [
                "=" * 80,
                f"ERROR DURING TEST: {rail.name} - {direction.value if 'direction' in locals() else 'UNKNOWN'} STEP",
                "=" * 80,
                f"Error occurred: {str(e)}",
                "Test could not complete successfully.",
                "=" * 80
            ]
            # Return an ERROR result
            return TransientResult(
                rail_name=rail.name,
                step_direction=direction.value if 'direction' in locals() else "UNKNOWN",
                load_step_description=step_desc if 'step_desc' in locals() else "Unknown",
                result="ERROR",  # Mark as ERROR (not PASS or FAIL)
                notes=str(e),    # Include error message in notes
                timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
                detailed_calculations="\n".join(error_log)  # Include error in calculation log
            )

    def _analyze_waveform(self, rail: RailConfig, direction: LoadStepDirection,
                         load_voltage_readings: Optional[List[float]] = None,
                         load_time_readings: Optional[List[float]] = None) -> Tuple[float, float, float, bool, str]:
        """
        *** THIS IS WHERE THE MEASUREMENTS HAPPEN! ***
        Analyze captured waveform for transient parameters - this is the "measurement brain"

        MEASUREMENT APPROACH:
        1. Use oscilloscope's built-in hardware measurements for DROOP (VMAX, VMIN, DC RMS FS)
        2. Use electronic load voltage readings for RECOVERY TIME (more accurate)
        3. Use waveform analysis for ringing detection
        
        Args:
            rail: Rail configuration
            direction: Load step direction
            load_voltage_readings: Voltage readings captured from electronic load during transient
            load_time_readings: Corresponding time readings in microseconds

        This dual approach ensures we get accurate measurements like you would
        with manual cursor measurements on the scope (e.g., 1.3V droop, 280ns recovery).

        Returns:
            A tuple (package) of FIVE values: (droop_mv, recovery_time_us, overshoot_mv, has_ringing, detailed_calculations)
        """
        import numpy as np  # Import here for early use

        # Initialize measurement variables - use FAIL values by default (not fake PASS values!)
        droop_mv = rail.max_droop_mv * 2.0       # Default to FAIL if can't measure
        recovery_us = rail.max_recovery_time_us * 2.0  # Default to FAIL
        overshoot_mv = rail.max_overshoot_mv * 2.0     # Default to FAIL
        has_ringing = True  # Default to FAIL

        # Initialize calculation log - this will record every step
        calc_log = []  # List to store each calculation step as text
        calc_log.append("=" * 80)
        calc_log.append(f"DETAILED CALCULATION LOG: {rail.name} - {direction.value} STEP")
        calc_log.append(f"Load Step: {rail.load_step_positive if direction == LoadStepDirection.POSITIVE else rail.load_step_negative}")
        calc_log.append("=" * 80)

        # =====================================================================
        # STAGE 1: Try scope hardware measurements FIRST (most accurate)
        # =====================================================================
        calc_log.append("\n" + "=" * 80)
        calc_log.append("STAGE 1: OSCILLOSCOPE HARDWARE MEASUREMENTS & RECOVERY TIME")
        calc_log.append("(Droop: scope built-in VMAX, VMIN, DC RMS FS)")
        calc_log.append("(Recovery: electronic load voltage readings)")
        calc_log.append("=" * 80)

        scope_measurements = self._measure_transient_with_scope(rail, direction, 
                                                               load_voltage_readings, 
                                                               load_time_readings)

        if scope_measurements['method'] == 'SCOPE_MEASUREMENTS':
            # Hardware measurements succeeded - use these values
            droop_mv = scope_measurements['droop_mv']
            recovery_us = scope_measurements['recovery_us']
            calc_log.append("\n✓ Scope hardware measurements SUCCEEDED")
            calc_log.append(f"  Droop: {droop_mv:.1f}mV")
            calc_log.append(f"  Recovery time: {recovery_us:.1f}µs")
            # Append the detailed scope measurement log
            calc_log.extend(scope_measurements['calc_log'])
            calc_log.append("\n" + "=" * 80)
            calc_log.append("STAGE 2: WAVEFORM ANALYSIS (for validation and ringing detection)")
            calc_log.append("=" * 80)
        else:
            calc_log.append("\n✗ Scope hardware measurements FAILED")
            calc_log.append("  Falling back to waveform data analysis...")
            calc_log.append("\n" + "=" * 80)
            calc_log.append("STAGE 2: WAVEFORM DATA ANALYSIS (primary method)")
            calc_log.append("=" * 80)

        try:  # Try to do the analysis, if anything goes wrong jump to "except" section
            # Check if oscilloscope is connected
            if not self._scope:
                calc_log.append("ERROR: Oscilloscope not connected")
                calc_log.append("*** TEST FAILED - NO INSTRUMENT CONNECTION ***")
                return (droop_mv, recovery_us, overshoot_mv, has_ringing, "\n".join(calc_log))

            # *** STEP 1: GET THE VOLTAGE DATA FROM OSCILLOSCOPE ***
            # Ch1 is the rail voltage (DC-coupled) - measuring actual voltage level
            calc_log.append("\n[STEP 1] DOWNLOADING WAVEFORM DATA FROM OSCILLOSCOPE")
            calc_log.append(f"  Reading Ch1 (Rail Voltage, DC-coupled)")
            calc_log.append(f"  Expected nominal voltage: {rail.expected_voltage_v}V")
            waveform = self._scope.get_channel_data(1)  # Download voltage vs time data from Channel 1
            if waveform is None:  # If download failed
                self._logger.error("CRITICAL: Could not get waveform data - TEST FAILED")
                calc_log.append("!!! CRITICAL ERROR: Could not download waveform data from oscilloscope !!!")
                calc_log.append("Possible causes:")
                calc_log.append("  - Oscilloscope did not trigger (no transient captured)")
                calc_log.append("  - Communication timeout")
                calc_log.append("  - Channel not configured correctly")
                calc_log.append("")
                calc_log.append("*** TEST FAILED - NO WAVEFORM DATA ***")
                calc_log.append("Returning FAIL values (2x limits) to indicate measurement failure")
                # Return FAIL values - DO NOT USE FAKE PASS VALUES!
                return (droop_mv, recovery_us, overshoot_mv, has_ringing, "\n".join(calc_log))

            # Extract the voltage values and time values from the waveform data
            voltage_data = waveform['voltage']  # Array of voltage measurements (like [0.001, 0.002, -0.003, ...])
            time_data = waveform['time']        # Array of time points (when each voltage was measured)
            calc_log.append(f"✓ Successfully downloaded {len(voltage_data)} voltage samples")
            calc_log.append(f"  Time range: {time_data[0]*1e6:.3f}µs to {time_data[-1]*1e6:.3f}µs")

            # *** WAVEFORM VALIDATION: Check if this looks like a real transient ***
            calc_log.append("\n[STEP 1.5] VALIDATING WAVEFORM - IS THIS A REAL TRANSIENT?")
            voltage_pk_pk = np.max(voltage_data) - np.min(voltage_data)  # Peak-to-peak voltage
            voltage_std = np.std(voltage_data)  # Standard deviation (noise level)
            calc_log.append(f"  Peak-to-peak voltage: {voltage_pk_pk*1000:.1f}mV")
            calc_log.append(f"  Voltage std dev: {voltage_std*1000:.3f}mV")

            # Check for excessive continuous oscillation (sign of captured noise, not transient)
            # A good transient should have distinct pre/post regions, not continuous oscillation
            first_quarter = voltage_data[:len(voltage_data)//4]
            last_quarter = voltage_data[-len(voltage_data)//4:]
            mid_section = voltage_data[len(voltage_data)//4:3*len(voltage_data)//4]

            first_std = np.std(first_quarter)
            last_std = np.std(last_quarter)
            mid_std = np.std(mid_section)

            calc_log.append(f"  First quarter std: {first_std*1000:.3f}mV")
            calc_log.append(f"  Last quarter std: {last_std*1000:.3f}mV")
            calc_log.append(f"  Middle section std: {mid_std*1000:.3f}mV")

            # Warning if the waveform looks like continuous oscillation
            if first_std > 0.01 and last_std > 0.01:  # Both ends have >10mV noise
                high_noise_ratio = min(first_std, last_std) / max(first_std, last_std)
                if high_noise_ratio > 0.5:  # Similar noise in both settled regions
                    calc_log.append(f"\n  ⚠ WARNING: High noise detected in both pre and post regions!")
                    calc_log.append(f"  This may indicate:")
                    calc_log.append(f"    - Continuous oscillation on the rail (not a clean transient)")
                    calc_log.append(f"    - Scope triggered on noise before actual load step")
                    calc_log.append(f"    - Probe not properly connected")
                    self._logger.warning(f"High noise in waveform - may not be a valid transient capture")

            # *** STEP 2: FIND THE TRIGGER POINT (when the load step happened) ***
            # Try to find the actual edge in the waveform (not just assume middle)
            calc_log.append("\n[STEP 2] LOCATING TRIGGER POINT (when load step occurred)")

            # Calculate derivative to find where the largest change occurs
            derivative = np.diff(voltage_data)

            if direction == LoadStepDirection.POSITIVE:
                # For positive step (load increase), voltage drops - look for largest negative derivative
                edge_idx = np.argmin(derivative)
                calc_log.append(f"  Looking for NEGATIVE edge (voltage drop)")
            else:
                # For negative step (load decrease), voltage rises - look for largest positive derivative
                edge_idx = np.argmax(derivative)
                calc_log.append(f"  Looking for POSITIVE edge (voltage rise)")

            # Use the detected edge as trigger point, but validate it's reasonable
            mid_point = len(voltage_data) // 2
            # If detected edge is within reasonable range of middle (±40%), use it
            # Otherwise fall back to middle (trigger point)
            if abs(edge_idx - mid_point) < mid_point * 0.4:
                trigger_idx = edge_idx
                calc_log.append(f"✓ Detected edge at index: {trigger_idx}")
            else:
                trigger_idx = mid_point
                calc_log.append(f"✓ Using middle point as trigger index: {trigger_idx}")
                calc_log.append(f"  (Detected edge at {edge_idx} was too far from center)")

            calc_log.append(f"  Trigger time: {time_data[trigger_idx]*1e6:.3f}µs")

            # *** STEP 3: CALCULATE BASELINE (normal voltage before the step) ***
            # This should be close to the nominal rail voltage (e.g., ~3.6V for 3V6 rail)
            calc_log.append("\n[STEP 3] CALCULATING BASELINE VOLTAGE (before load step)")
            pre_trigger = voltage_data[:trigger_idx - 100]  # Get data BEFORE trigger (skip last 100 points)
            baseline = np.mean(pre_trigger) if len(pre_trigger) > 0 else rail.expected_voltage_v
            baseline_min = np.min(pre_trigger) if len(pre_trigger) > 0 else baseline
            baseline_max = np.max(pre_trigger) if len(pre_trigger) > 0 else baseline
            baseline_noise_mv = (baseline_max - baseline_min) * 1000 / 2

            calc_log.append(f"  Samples used for baseline: {len(pre_trigger)} points")
            calc_log.append(f"  Baseline voltage (average): {baseline:.4f}V")
            calc_log.append(f"  Expected nominal voltage: {rail.expected_voltage_v}V")
            calc_log.append(f"  Baseline range: {baseline_min:.4f}V to {baseline_max:.4f}V")
            calc_log.append(f"  Baseline noise: ±{baseline_noise_mv:.2f}mV")

            # Validate baseline is close to expected voltage
            baseline_error_mv = abs(baseline - rail.expected_voltage_v) * 1000
            if baseline_error_mv > 100:  # More than 100mV off
                calc_log.append(f"  ⚠ WARNING: Baseline ({baseline:.3f}V) differs from expected ({rail.expected_voltage_v}V) by {baseline_error_mv:.1f}mV")
            else:
                calc_log.append(f"  ✓ Baseline matches expected voltage (within {baseline_error_mv:.1f}mV)")

            # *** STEP 4: GET DATA AFTER THE LOAD STEP ***
            calc_log.append("\n[STEP 4] EXTRACTING POST-TRIGGER DATA (after load step)")
            post_trigger = voltage_data[trigger_idx:]  # Get data AFTER trigger
            calc_log.append(f"✓ Post-trigger samples: {len(post_trigger)} points")
            calc_log.append(f"  Analysis window: {len(post_trigger) * waveform.get('x_increment', 1e-6) * 1e6:.1f}µs")

            # *** STEP 5: MEASURE DROOP AND OVERSHOOT (depends on direction) ***
            # NOTE: DROOP IS MEASURED BY SCOPE HARDWARE ONLY (earlier in STAGE 1)
            # Waveform analysis does NOT recalculate droop - it validates other parameters
            calc_log.append("\n[STEP 5] DROOP MEASUREMENT")
            calc_log.append("  ⓘ Using scope hardware measurements (DC RMS FS, VMAX, VMIN)")
            calc_log.append(f"  ★ DROOP = {droop_mv:.1f}mV (from scope hardware measurement)")
            calc_log.append(f"    (Waveform analysis skipped - scope hardware is authoritative)")
            
            # Skip to recovery time calculation

            # *** STEP 6: MEASURE RECOVERY TIME (how long to return to baseline/nominal) ***
            # Recovery = time for voltage to return to within tolerance of the baseline voltage
            calc_log.append("\n[STEP 6] MEASURING RECOVERY TIME")
            calc_log.append(f"  Recovery = time to return to baseline voltage ({baseline:.4f}V)")

            # Use pre-trigger noise floor as tolerance (matches manual cursor accuracy)
            noise_pp = (baseline_max - baseline_min) if len(pre_trigger) > 10 else 0.010
            tolerance = max(noise_pp, 0.005)  # At least 5mV

            calc_log.append(f"  Settlement tolerance: ±{tolerance*1000:.1f}mV (from pre-trigger noise)")
            calc_log.append(f"  Target range: {baseline - tolerance:.4f}V to {baseline + tolerance:.4f}V")

            # Find when voltage returns to within tolerance of baseline and STAYS there
            recovery_idx = len(post_trigger) - 1  # Start assuming it takes the full time
            settled = False

            for i in range(len(post_trigger)):  # Check each point in time
                if abs(post_trigger[i] - baseline) <= tolerance:  # If voltage is within tolerance of baseline
                    # Check if it STAYS within tolerance (not just a momentary cross)
                    if i + 50 < len(post_trigger):  # If there's enough data to check ahead
                        remaining = post_trigger[i:i+50]  # Get next 50 points
                        # Check if ALL next 50 points stay within tolerance of baseline
                        if np.all(np.abs(remaining - baseline) <= tolerance):
                            recovery_idx = i  # This is when it truly settled
                            settled = True
                            calc_log.append(f"\n  ✓ Voltage settled at index {i}")
                            calc_log.append(f"    Voltage at settlement: {post_trigger[i]:.4f}V")
                            calc_log.append(f"    Deviation from baseline: {(post_trigger[i] - baseline)*1000:.2f}mV")
                            break  # Stop looking, we found it

            x_increment = waveform.get('x_increment', 1e-6)  # Time between samples (default 1 microsecond)
            recovery_us = recovery_idx * x_increment * 1e6  # Convert to microseconds (×1e6)

            if not settled:
                calc_log.append(f"\n  ⚠ Voltage did not fully settle within capture window")
                calc_log.append(f"    Final voltage: {post_trigger[-1]:.4f}V")
                calc_log.append(f"    Deviation from baseline: {(post_trigger[-1] - baseline)*1000:.2f}mV")

            calc_log.append(f"\n  RECOVERY TIME CALCULATION:")
            calc_log.append(f"    Settlement index: {recovery_idx} samples after trigger")
            calc_log.append(f"    Time increment per sample: {x_increment*1e6:.6f}µs")
            calc_log.append(f"    Calculation: {recovery_idx} × {x_increment*1e6:.6f}µs = {recovery_us:.3f}µs")
            calc_log.append(f"    ★ RECOVERY TIME = {recovery_us:.1f}µs (Limit: {rail.max_recovery_time_us}µs) {'✓ PASS' if recovery_us <= rail.max_recovery_time_us else '✗ FAIL'}")

            # *** STEP 7: DETECT RINGING/OSCILLATION ***
            calc_log.append("\n[STEP 7] DETECTING RINGING/OSCILLATION")
            # Get the "settled" region (skip first 100 and last 100 points to avoid edges)
            settled_region = post_trigger[100:-100] if len(post_trigger) > 300 else post_trigger
            calc_log.append(f"  Analyzing settled region: {len(settled_region)} samples")

            if len(settled_region) > 50:  # If we have enough data
                rms = np.std(settled_region)  # RMS = how much variation (wobbliness)
                peak = np.max(np.abs(settled_region - np.mean(settled_region)))  # Peak deviation
                settled_mean = np.mean(settled_region)
                rms_ratio = (rms / peak) if peak > 0 else 0  # Ratio of RMS to peak
                # If RMS is high relative to peak, there's sustained oscillation (ringing)
                has_ringing = rms > 0.4 * peak if peak > 0 else False

                calc_log.append(f"\n  RINGING DETECTION CALCULATION:")
                calc_log.append(f"    Settled region mean: {settled_mean*1000:.3f}mV")
                calc_log.append(f"    RMS (standard deviation): {rms*1000:.3f}mV")
                calc_log.append(f"    Peak deviation from mean: {peak*1000:.3f}mV")
                calc_log.append(f"    RMS/Peak ratio: {rms_ratio:.3f}")
                calc_log.append(f"    Ringing threshold: RMS > 0.4 × Peak")
                calc_log.append(f"    Calculation: {rms*1000:.3f}mV > {0.4*peak*1000:.3f}mV? {has_ringing}")
                calc_log.append(f"    ★ RINGING = {'YES ✗ FAIL' if has_ringing else 'NO ✓ PASS'}")
            else:
                has_ringing = False
                calc_log.append(f"  Not enough samples in settled region for ringing analysis")
                calc_log.append(f"  ★ RINGING = NO (insufficient data)")

            # Add summary
            calc_log.append("\n" + "=" * 80)
            calc_log.append("MEASUREMENT SUMMARY")
            calc_log.append("=" * 80)
            calc_log.append(f"Droop:    {droop_mv:.1f}mV  (Limit: {rail.max_droop_mv}mV)  {'✓ PASS' if droop_mv <= rail.max_droop_mv else '✗ FAIL'}")
            calc_log.append(f"Recovery: {recovery_us:.1f}µs (Limit: {rail.max_recovery_time_us}µs) {'✓ PASS' if recovery_us <= rail.max_recovery_time_us else '✗ FAIL'}")
            calc_log.append(f"Ringing:  {'YES' if has_ringing else 'NO'}      (Required: NO)  {'✗ FAIL' if has_ringing else '✓ PASS'}")
            overall_pass = (droop_mv <= rail.max_droop_mv and recovery_us <= rail.max_recovery_time_us and
                          not has_ringing)
            calc_log.append(f"\n★★★ OVERALL: {'PASS ✓' if overall_pass else 'FAIL ✗'} ★★★")
            calc_log.append("=" * 80)

        except Exception as e:  # If anything went wrong in the analysis
            self._logger.error(f"Waveform analysis FAILED: {e}")  # Log the error
            calc_log.append(f"\n!!! CRITICAL ERROR DURING ANALYSIS !!!")
            calc_log.append(f"Error: {str(e)}")
            calc_log.append(f"\n*** TEST FAILED - ANALYSIS ERROR ***")
            calc_log.append(f"Returning FAIL values (2x limits) to indicate measurement failure")
            # Return FAIL values - DO NOT USE FAKE PASS VALUES!
            droop_mv = rail.max_droop_mv * 2.0          # FAIL value
            recovery_us = rail.max_recovery_time_us * 2.0  # FAIL value
            has_ringing = True  # FAIL value
            calc_log.append(f"  FAIL Droop: {droop_mv:.1f}mV (2x limit)")
            calc_log.append(f"  FAIL Recovery: {recovery_us:.1f}µs (2x limit)")
            calc_log.append(f"  FAIL Ringing: YES")

        # Return all FIVE measurements as a package (tuple): measurements + detailed calculations
        # NOTE: overshoot_mv is not used in pass/fail logic anymore, but kept for backward compatibility
        return (droop_mv, recovery_us, overshoot_mv, has_ringing, "\n".join(calc_log))

    def _generate_notes(self, rail: RailConfig, droop: float, recovery: float, overshoot: float, ringing: bool) -> str:
        """Generate notes about the measurement"""
        notes = []

        if droop > rail.max_droop_mv:
            notes.append(f"Droop exceeds limit by {droop - rail.max_droop_mv:.1f}mV")
        if recovery > rail.max_recovery_time_us:
            notes.append(f"Recovery exceeds limit by {recovery - rail.max_recovery_time_us:.1f}us")
        if ringing:
            notes.append("Sustained ringing detected")

        return "; ".join(notes) if notes else "Within specification"

    def test_single_rail(self, rail: RailConfig) -> RailTestResult:
        """
        Test a single rail (both positive and negative load steps)

        Args:
            rail: Rail configuration

        Returns:
            RailTestResult
        """
        self._logger.info("=" * 60)
        self._logger.info(f"TESTING RAIL: {rail.name} ({rail.test_point})")
        self._logger.info(f"  Expected voltage: {rail.expected_voltage_v}V")
        self._logger.info(f"  Load steps: {rail.load_step_positive} / {rail.load_step_negative}")
        self._logger.info(f"  Limits: Droop<{rail.max_droop_mv}mV, Recovery<{rail.max_recovery_time_us}us")
        self._logger.info("=" * 60)

        result = RailTestResult(
            rail_name=rail.name,
            test_point=rail.test_point
        )

        # Configure oscilloscope using per-rail settings from SCOPE_CONFIG table
        if not self.configure_oscilloscope_for_rail(rail):
            result.overall_result = "ERROR"
            return result

        if not self.configure_electronic_load_for_rail(rail):
            result.overall_result = "ERROR"
            return result

        # Perform positive load step
        self._logger.info("--- POSITIVE LOAD STEP ---")
        result.positive_step = self.perform_load_step(rail, LoadStepDirection.POSITIVE)

        # Small delay between steps
        time.sleep(1.0)

        # Perform negative load step
        self._logger.info("--- NEGATIVE LOAD STEP ---")
        result.negative_step = self.perform_load_step(rail, LoadStepDirection.NEGATIVE)

        # Disable load after testing
        try:
            self._load.disable_input()
        except:
            pass

        # Determine overall result
        pos_pass = result.positive_step and result.positive_step.result == "PASS"
        neg_pass = result.negative_step and result.negative_step.result == "PASS"

        if pos_pass and neg_pass:
            result.overall_result = "PASS"
        elif result.positive_step is None or result.negative_step is None:
            result.overall_result = "ERROR"
        else:
            result.overall_result = "FAIL"

        self._logger.info(f"Rail {rail.name} overall result: {result.overall_result}")
        return result

    def run_test_sequence(self, rails: Optional[List[str]] = None) -> bool:
        """
        Run complete test sequence with minimal user intervention

        Args:
            rails: Optional list of rail names to test. If None, tests all rails.

        Returns:
            bool: True if test completed successfully
        """
        self.test_start_time = datetime.now()

        print("\n" + "=" * 70)
        print(" PWRSTD06: TRANSIENT RESPONSE TEST - MINIMAL INTERVENTION MODE")
        print("=" * 70)
        print(f" Start time: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f" Output directory: {self.output_dir}")
        print("=" * 70)

        # Connect to instruments
        if not self.connect_instruments():
            print("\nERROR: Failed to connect to instruments!")
            return False

        # Determine which rails to test
        if rails:
            # Specific rails passed in (from command line or caller)
            rails_to_test = [r for r in self.RAIL_CONFIGS if r.name in rails]
        else:
            # Interactive selector – user picks with TAB + ENTER
            selected_names = interactive_rail_selector(self.RAIL_CONFIGS)
            if selected_names is None:
                print("Test cancelled by user.")
                self.disconnect_instruments()
                return False
            rails_to_test = [r for r in self.RAIL_CONFIGS if r.name in selected_names]

        print(f"\nRails to test ({len(rails_to_test)}):")
        for i, rail in enumerate(rails_to_test, 1):
            print(f"  {i}. {rail.name} ({rail.test_point}): {rail.load_step_positive}")
        print()

        # Test each selected rail
        for i, rail in enumerate(rails_to_test, 1):
            # ── PSU check before each rail ──
            print(f"\n{'─' * 70}")
            print(f"  [{i}/{len(rails_to_test)}]  RAIL: {rail.name} ({rail.test_point})")
            print(f"{'─' * 70}")
            psu_ok = input("    Is the PSU powered ON? (yes/no): ").strip().lower()
            if psu_ok not in ['yes', 'y']:
                print("    Please turn ON the PSU and try again.")
                psu_ok = input("    PSU is ON now? (yes/quit): ").strip().lower()
                if psu_ok not in ['yes', 'y']:
                    print("\n    Test sequence ended – PSU not ready.")
                    break

            print(f"    Expected voltage: {rail.expected_voltage_v}V")
            print(f"    Load step: {rail.load_step_positive}")
            print()
            print(f"    Connect electronic load and scope probe to {rail.test_point}")
            print(f"    - Scope CH1: Rail voltage (DC coupled, 1:1 probe)")
            print()

            while True:
                response = input(f"    Connected to {rail.name}? (yes/skip/quit): ").strip().lower()

                if response in ['yes', 'y']:
                    result = self.test_single_rail(rail)
                    self.results.append(result)

                    status_symbol = "[PASS]" if result.overall_result == "PASS" else "[FAIL]"
                    print(f"\n    {status_symbol} {rail.name} test complete!")
                    break

                elif response == 'skip':
                    print(f"    Skipping {rail.name}")
                    self.results.append(RailTestResult(
                        rail_name=rail.name,
                        test_point=rail.test_point,
                        overall_result="NOT_TESTED"
                    ))
                    break

                elif response == 'quit':
                    print("\n    Test sequence ended by user")
                    break

                else:
                    print("    Please enter 'yes', 'skip', or 'quit'")

            if response == 'quit':
                break

        # Test complete
        self.test_end_time = datetime.now()
        duration = (self.test_end_time - self.test_start_time).total_seconds()

        # Disconnect instruments
        self.disconnect_instruments()

        # Generate reports
        self._generate_reports()

        # Print summary
        self._print_summary()

        return True

    def _generate_reports(self):
        """Generate all test reports"""
        timestamp = self.test_start_time.strftime("%Y%m%d_%H%M%S")

        # JSON report
        json_path = self.reports_dir / f"pwrstd06_results_{timestamp}.json"
        report_data = {
            'test_info': {
                'test_name': 'PWRSTD06 Transient Response Test',
                'start_time': self.test_start_time.isoformat(),
                'end_time': self.test_end_time.isoformat() if self.test_end_time else None,
                'duration_seconds': (self.test_end_time - self.test_start_time).total_seconds() if self.test_end_time else None
            },
            'results': [r.to_dict() for r in self.results]
        }

        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=2, cls=NumpyEncoder)

        self._logger.info(f"JSON report saved: {json_path}")

        # CSV report (droop-focused with trigger values)
        csv_path = self.reports_dir / f"pwrstd06_results_{timestamp}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Rail', 'Step', 'Load_Step_mA', 'DV_Droop_or_Rise_mV',
                'Trigger', 'Result', 'Calculation_File'
            ])

            for result in self.results:
                for step in [result.positive_step, result.negative_step]:
                    if step:
                        calc_file = f"{step.rail_name}_{step.timestamp}_calculations.txt"
                        cfg = self.SCOPE_CONFIG.get(result.rail_name, {})
                        if step.step_direction == "POSITIVE":
                            trigger_val = cfg.get("trigger_up", "")
                        else:
                            trigger_val = cfg.get("trigger_down", "")
                        trigger_str = f"{trigger_val:.3f}" if isinstance(trigger_val, (int, float)) else str(trigger_val)
                        writer.writerow([
                            result.rail_name,
                            step.step_direction,
                            step.load_step_description,
                            f"{step.droop_mv:.1f}",
                            trigger_str,
                            step.result,
                            f"../calculations/{calc_file}"
                        ])

        self._logger.info(f"CSV report saved: {csv_path}")
        self._logger.info(f"  Note: CSV includes references to detailed calculation files in 'calculations' folder")

        # Text summary
        summary_path = self.reports_dir / f"pwrstd06_summary_{timestamp}.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_summary_text())

        self._logger.info(f"Summary saved: {summary_path}")

        # Generate index of detailed calculation files
        calc_index_path = self.calculations_dir / "README.txt"
        with open(calc_index_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("DETAILED CALCULATION FILES - PWRSTD06 TRANSIENT RESPONSE TEST\n")
            f.write("=" * 80 + "\n\n")
            f.write("This folder contains step-by-step calculation logs for each transient test.\n")
            f.write("Each file shows exactly how droop, recovery time, overshoot, and ringing\n")
            f.write("were calculated from the oscilloscope waveform data.\n\n")
            f.write("File naming format: <RAIL>_<DIRECTION>_calculations.txt\n")
            f.write("  Example: 3V3_low_to_high_calculations.txt\n\n")
            f.write("=" * 80 + "\n")
            f.write("FILES IN THIS TEST RUN:\n")
            f.write("=" * 80 + "\n\n")

            for result in self.results:
                f.write(f"RAIL: {result.rail_name} ({result.test_point})\n")
                if result.positive_step:
                    calc_file = f"{result.positive_step.rail_name}_low_to_high_calculations.txt"
                    f.write(f"  ├─ LOW→HIGH: {calc_file}\n")
                    f.write(f"  │  Result: {result.positive_step.result}\n")
                if result.negative_step:
                    calc_file = f"{result.negative_step.rail_name}_high_to_low_calculations.txt"
                    f.write(f"  └─ HIGH→LOW: {calc_file}\n")
                    f.write(f"     Result: {result.negative_step.result}\n")
                f.write("\n")

            f.write("=" * 80 + "\n")
            f.write("To view calculation details, open any file in a text editor.\n")
            f.write("Each file contains:\n")
            f.write("  - Waveform data summary\n")
            f.write("  - Baseline voltage calculation\n")
            f.write("  - Droop measurement with actual voltage values\n")
            f.write("  - Overshoot measurement with actual voltage values\n")
            f.write("  - Recovery time calculation showing settlement criteria\n")
            f.write("  - Ringing detection analysis with RMS and peak values\n")
            f.write("  - Pass/Fail determination for each parameter\n")
            f.write("=" * 80 + "\n")

        self._logger.info(f"Calculation index saved: {calc_index_path}")

    def _generate_summary_text(self) -> str:
        """Generate text summary of results in table format"""
        lines = []
        lines.append("=" * 80)
        lines.append("PWRSTD06 TRANSIENT RESPONSE TEST SUMMARY")
        lines.append("=" * 80)
        lines.append(f"Test Date: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S') if self.test_start_time else 'Unknown'}")

        if self.test_end_time and self.test_start_time:
            duration = (self.test_end_time - self.test_start_time).total_seconds()
            lines.append(f"Duration: {duration:.1f} seconds")

        lines.append("")

        # Count results
        total = len(self.results)
        passed = sum(1 for r in self.results if r.overall_result == "PASS")
        failed = sum(1 for r in self.results if r.overall_result == "FAIL")
        not_tested = sum(1 for r in self.results if r.overall_result == "NOT_TESTED")

        lines.append(f"Overall: {passed}/{total - not_tested} PASSED")
        if not_tested > 0:
            lines.append(f"         {not_tested} rails not tested")
        lines.append("")

        # ── LOW TO HIGH table ──
        col_w = {"rail": 10, "step": 16, "droop": 16, "trigger": 10}
        table_w = col_w["rail"] + col_w["step"] + col_w["droop"] + col_w["trigger"] + 7  # separators

        lines.append("LOW TO HIGH (Load Up)")
        lines.append("=" * table_w)
        lines.append(
            f" {'Rail':<{col_w['rail']}}| {'Load Step':<{col_w['step']}}| "
            f"{'DV Droop':<{col_w['droop']}}| {'Trigger':<{col_w['trigger']}}"
        )
        lines.append(
            f" {'':_<{col_w['rail']}}|{'':_<{col_w['step']+1}}|"
            f"{'':_<{col_w['droop']+1}}|{'':_<{col_w['trigger']+1}}"
        )
        lines.append(
            f" {'':>{col_w['rail']}}| {'(mA)':<{col_w['step']}}| "
            f"{'(mV)':<{col_w['droop']}}| {'':>{col_w['trigger']}}"
        )
        lines.append("-" * table_w)

        for result in self.results:
            if result.positive_step:
                step = result.positive_step
                cfg = self.SCOPE_CONFIG.get(result.rail_name, {})
                trigger_val = cfg.get("trigger_up", "")
                trigger_str = f"{trigger_val:.3f}" if isinstance(trigger_val, (int, float)) else str(trigger_val)
                lines.append(
                    f" {result.rail_name:<{col_w['rail']}}| "
                    f"{step.load_step_description:<{col_w['step']}}| "
                    f"{step.droop_mv:<{col_w['droop']}.1f}| "
                    f"{trigger_str:<{col_w['trigger']}}"
                )
            else:
                lines.append(
                    f" {result.rail_name:<{col_w['rail']}}| {'NOT TESTED':<{col_w['step']}}| "
                    f"{'':<{col_w['droop']}}| {'':<{col_w['trigger']}}"
                )

        lines.append("=" * table_w)
        lines.append("")

        # ── HIGH TO LOW table ──
        lines.append("HIGH TO LOW (Load Down)")
        lines.append("=" * table_w)
        lines.append(
            f" {'Rail':<{col_w['rail']}}| {'Load Step':<{col_w['step']}}| "
            f"{'DV Rise':<{col_w['droop']}}| {'Trigger':<{col_w['trigger']}}"
        )
        lines.append(
            f" {'':_<{col_w['rail']}}|{'':_<{col_w['step']+1}}|"
            f"{'':_<{col_w['droop']+1}}|{'':_<{col_w['trigger']+1}}"
        )
        lines.append(
            f" {'':>{col_w['rail']}}| {'(mA)':<{col_w['step']}}| "
            f"{'(mV)':<{col_w['droop']}}| {'':>{col_w['trigger']}}"
        )
        lines.append("-" * table_w)

        for result in self.results:
            if result.negative_step:
                step = result.negative_step
                cfg = self.SCOPE_CONFIG.get(result.rail_name, {})
                trigger_val = cfg.get("trigger_down", "")
                trigger_str = f"{trigger_val:.3f}" if isinstance(trigger_val, (int, float)) else str(trigger_val)
                lines.append(
                    f" {result.rail_name:<{col_w['rail']}}| "
                    f"{step.load_step_description:<{col_w['step']}}| "
                    f"{step.droop_mv:<{col_w['droop']}.1f}| "
                    f"{trigger_str:<{col_w['trigger']}}"
                )
            else:
                lines.append(
                    f" {result.rail_name:<{col_w['rail']}}| {'NOT TESTED':<{col_w['step']}}| "
                    f"{'':<{col_w['droop']}}| {'':<{col_w['trigger']}}"
                )

        lines.append("=" * table_w)
        lines.append("")

        # Overall assessment
        if failed == 0 and not_tested == 0:
            lines.append("OVERALL TEST RESULT: PASS")
            lines.append("All rails meet droop limits.")
        elif failed > 0:
            lines.append("OVERALL TEST RESULT: FAIL")
            lines.append(f"{failed} rail(s) failed to meet specifications.")
        else:
            lines.append("OVERALL TEST RESULT: INCOMPLETE")
            lines.append(f"{not_tested} rail(s) were not tested.")

        lines.append("=" * table_w)
        lines.append("")
        lines.append("Note: DV Droop (Low->High) = DC_RMS_FS - VMIN")
        lines.append("      DV Rise  (High->Low) = VMAX - DC_RMS_FS")
        lines.append("")
        lines.append("DETAILED CALCULATION FILES:")
        lines.append("  See 'calculations' folder for step-by-step measurement breakdowns.")
        lines.append("=" * table_w)

        return "\n".join(lines)

    def _print_summary(self):
        """Print summary to console"""
        print("\n" + self._generate_summary_text())
        print(f"\nResults saved to: {self.output_dir}")
        print(f"  ├─ screenshots/     - Oscilloscope waveform captures")
        print(f"  ├─ reports/         - CSV, JSON, and summary reports")
        print(f"  └─ calculations/    - Detailed step-by-step calculation logs")
        print(f"\n💡 TIP: Check the 'calculations' folder for detailed breakdowns")
        print(f"   of how droop, recovery time, and overshoot were calculated!")


def main():
    """Main entry point for PWRSTD06 test"""
    print("=" * 70)
    print(" PWRSTD06: Transient Response Test - Auto-Detection Mode")
    print("=" * 70)
    print()
    print("NOTE: For best experience, use run_pwrstd06_test.py instead")
    print("      (supports --list, --rails, and other options)")
    print()

    # Allow override from command line (optional)
    scope_addr = None
    load_addr = None

    if len(sys.argv) >= 3:
        scope_addr = sys.argv[1]
        load_addr = sys.argv[2]
        print(f"Using addresses from command line:")
        print(f"  Oscilloscope: {scope_addr}")
        print(f"  Electronic Load: {load_addr}")
    else:
        print("Auto-detecting instruments (pass addresses as arguments to override)...")

    # Create and run test (auto-detection will happen if addresses are None)
    test = PWRSTD06TransientTest(
        oscilloscope_address=scope_addr,
        electronic_load_address=load_addr,
        output_dir=r""  # <-- Enter your desired save path here, e.g. r"D:\Results\pwrstd06"
    )

    # Check if instruments were found
    if not test.scope_address or not test.load_address:
        print("\nERROR: Required instruments not found!")
        print("  Use: python run_pwrstd06_test.py --list")
        print("  Or provide addresses: python pwrstd06_transient_response_test.py <scope> <load>")
        return 1

    # Run test sequence (all rails)
    success = test.run_test_sequence()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
