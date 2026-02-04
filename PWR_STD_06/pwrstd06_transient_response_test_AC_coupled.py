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

    def configure_oscilloscope_for_rail(self, rail: RailConfig, fast_capture: bool = True) -> bool:
        """
        Configure oscilloscope for transient capture on specific rail

        VOLTAGE-ONLY SETUP (no current probe):
        - Ch1: Rail voltage (DC-coupled) - to see actual voltage level (e.g., 3.6V)
        - Timebase: 500ns/div for FAST capture, 1ms/div for slow
        - Trigger: Falling edge when voltage drops below nominal

        FAST CAPTURE MODE (default):
        - 500ns/div timebase captures fast transients (sub-microsecond)
        - Suitable for measuring droop and recovery in nanoseconds
        - Like your manual cursor measurement showing 280ns recovery time

        Example for 3V6 rail:
        - Nominal voltage: 3.6V
        - Expected droop: <50-75mV (so voltage might drop to ~3.525V)
        - Voltage scale: 1V/div (to see 3.6V signal clearly)
        - Trigger level: 3.54V (3.6V - 60mV) - triggers when voltage dips below this
        - Droop = 3.6V - minimum_voltage
        - Recovery = time to return to 3.6V

        Args:
            rail: Rail configuration
            fast_capture: If True, use 500ns/div for fast transients (default)
                         If False, use 1ms/div for slower analysis

        Returns:
            bool: True if configuration successful
        """
        if not self._scope:
            return False

        try:
            self._logger.info(f"Configuring oscilloscope for {rail.name}")
            self._logger.info(f"  Nominal voltage: {rail.expected_voltage_v}V")
            self._logger.info(f"  Mode: {'FAST CAPTURE (500ns/div)' if fast_capture else 'SLOW CAPTURE (1ms/div)'}")

            # ============================================================
            # CHANNEL 1: Rail Voltage - AC COUPLED
            # ============================================================
            # AC coupling: baseline sits at ~0V, droop goes NEGATIVE,
            # overshoot goes POSITIVE. Much easier to trigger on.
            #
            # ┌──────────────────────────────────────────────────────────────┐
            # │  VERTICAL SCALE AND OFFSET - EDIT HERE                       │
            # └──────────────────────────────────────────────────────────────┘
            voltage_scale_v = 2.0   # <-- 2V/div
            vertical_offset = 0.0   # <-- 0V offset

            self._scope.configure_channel(
                channel=1,
                vertical_scale=voltage_scale_v,
                vertical_offset=vertical_offset,
                coupling="AC",  # AC coupled: baseline at 0V, droop = negative, overshoot = positive
                probe_attenuation=10.0  # <-- 10:1 probe
            )
            self._logger.info(f"  Ch1 (Voltage): {voltage_scale_v}V/div, AC coupled")
            self._logger.info(f"  AC coupling: baseline~0V, droop=negative, overshoot=positive")

            # ============================================================
            # TIMEBASE
            # ============================================================
            # ┌──────────────────────────────────────────────────────────────┐
            # │  TIMEBASE - EDIT HERE                                        │
            # └──────────────────────────────────────────────────────────────┘
            time_scale = 5e-6  # <-- 5µs/div (5 microseconds)
            pre_trigger_offset = time_scale * 2  # 10µs offset (2 divisions pre-trigger)

            self._scope.configure_timebase(
                time_scale=time_scale,
                time_offset=pre_trigger_offset
            )
            self._logger.info(f"  Timebase: {time_scale*1e6:.0f}µs/div")
            self._logger.info(f"  Pre-trigger offset: {pre_trigger_offset*1e6:.1f}µs")

            # ============================================================
            # TRIGGER: Initial setup - reconfigured per step in perform_load_step
            # ============================================================
            # With AC coupling, baseline is ~0V.
            # Positive load step: droop goes negative -> trigger FALLING at -20mV
            # Negative load step: overshoot goes positive -> trigger RISING at +15mV
            #
            # Initial trigger set for positive (droop) capture
            # ┌──────────────────────────────────────────────────────────────┐
            # │  INITIAL TRIGGER LEVEL (mV) - EDIT HERE                      │
            # └──────────────────────────────────────────────────────────────┘
            initial_trigger_mv = -20  # <-- Falling edge at -20mV (for droop)

            self._scope.configure_trigger(
                channel=1,
                trigger_level=initial_trigger_mv / 1000.0,  # Convert mV to V
                trigger_slope="NEG",  # Falling edge for positive load step
                sweep_mode="NORMal"   # Wait for actual trigger, no auto-trigger
            )
            self._logger.info(f"  Trigger: FALLING edge at {initial_trigger_mv}mV (AC-coupled)")
            self._logger.info(f"  Trigger sweep: NORMAL (waits for actual trigger event)")

            self._logger.info(f"Oscilloscope configured for {rail.name}")
            self._logger.info(f"  Load step: {rail.low_current_ma}mA -> {rail.high_current_ma}mA")
            self._logger.info(f"  Limits: Droop<{rail.max_droop_mv}mV, Recovery<{rail.max_recovery_time_us}µs")
            return True

        except Exception as e:
            self._logger.error(f"Oscilloscope configuration failed: {e}")
            import traceback
            self._logger.error(traceback.format_exc())
            return False

    def _measure_transient_with_scope(self, rail: RailConfig, direction: LoadStepDirection) -> Dict[str, Any]:
        """
        Use oscilloscope's built-in measurements and cursors to measure transient parameters.

        This method uses the scope's hardware measurements for accuracy:
        - VMAX: Maximum voltage (for overshoot calculation)
        - VMIN: Minimum voltage (for droop calculation)
        - VTOP: Top voltage level (baseline for settled state)
        - VBASe: Base voltage level
        - OVERshoot: Built-in overshoot measurement
        - RISE/FALL: Rise/fall time measurements

        Then uses cursor delta for recovery time measurement.

        Args:
            rail: Rail configuration
            direction: Load step direction

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

            # Get VAVG (average - for AC coupling this is the baseline ~0V)
            v_avg = self._scope.measure_average(1)
            if v_avg is not None:
                calc_log.append(f"  VAVG (AC baseline): {v_avg:.4f}V ({v_avg*1000:.1f}mV)")

            # Get scope's built-in overshoot measurement
            scope_overshoot = self._scope.measure_overshoot(1)
            if scope_overshoot is not None:
                calc_log.append(f"  OVERshoot (scope %): {scope_overshoot:.2f}%")

            # ============================================================
            # STEP 2: Calculate DROOP and OVERSHOOT
            # ============================================================
            # AC COUPLING: baseline is ~0V (pre-step flat portion)
            # Droop (positive step):    goes NEGATIVE -> Droop = |VMIN|
            # Overshoot (negative step): goes POSITIVE -> Overshoot = VMAX
            calc_log.append("\n[STEP 2] CALCULATING DROOP AND OVERSHOOT (AC-coupled, baseline~0V)")

            # Baseline = average of pre-trigger portion (~0V for AC coupling)
            baseline = v_avg if v_avg is not None else 0.0
            results['baseline_v'] = baseline
            calc_log.append(f"  Baseline (AC average): {baseline*1000:.1f}mV")

            if direction == LoadStepDirection.POSITIVE:
                # Positive step: voltage goes NEGATIVE (droop)
                calc_log.append("  Direction: POSITIVE (load increased → voltage dips negative)")

                # DROOP = |VMIN - baseline| (VMIN is negative in AC mode)
                if v_min is not None:
                    droop_mv = abs(results['min_v'] - baseline) * 1000
                    results['droop_mv'] = droop_mv
                    calc_log.append(f"\n  DROOP = |VMIN - baseline|")
                    calc_log.append(f"        = |{results['min_v']*1000:.1f}mV - {baseline*1000:.1f}mV|")
                    calc_log.append(f"  ★ DROOP = {droop_mv:.1f}mV (Limit: <{rail.max_droop_mv}mV)")

                # OVERSHOOT = max positive excursion after droop recovery
                if v_max is not None and results['max_v'] > baseline:
                    overshoot_mv = (results['max_v'] - baseline) * 1000
                    results['overshoot_mv'] = overshoot_mv
                    calc_log.append(f"\n  OVERSHOOT = VMAX - baseline")
                    calc_log.append(f"            = {results['max_v']*1000:.1f}mV - {baseline*1000:.1f}mV")
                    calc_log.append(f"  ★ OVERSHOOT = {overshoot_mv:.1f}mV (Limit: <{rail.max_overshoot_mv}mV)")
                else:
                    results['overshoot_mv'] = 0.0
                    calc_log.append(f"\n  No overshoot (VMAX not above baseline)")

            else:
                # Negative step: voltage goes POSITIVE (overshoot)
                calc_log.append("  Direction: NEGATIVE (load decreased → voltage spikes positive)")

                # OVERSHOOT = VMAX - baseline (positive spike)
                if v_max is not None and results['max_v'] > baseline:
                    overshoot_mv = (results['max_v'] - baseline) * 1000
                    results['overshoot_mv'] = overshoot_mv
                    calc_log.append(f"\n  OVERSHOOT = VMAX - baseline")
                    calc_log.append(f"            = {results['max_v']*1000:.1f}mV - {baseline*1000:.1f}mV")
                    calc_log.append(f"  ★ OVERSHOOT = {overshoot_mv:.1f}mV (Limit: <{rail.max_overshoot_mv}mV)")
                else:
                    results['overshoot_mv'] = 0.0
                    calc_log.append(f"  No overshoot (VMAX not above baseline)")

                # DROOP (undershoot) for negative step = |VMIN - baseline|
                if v_min is not None and results['min_v'] < baseline:
                    droop_mv = abs(results['min_v'] - baseline) * 1000
                    results['droop_mv'] = droop_mv
                    calc_log.append(f"\n  UNDERSHOOT = |VMIN - baseline|")
                    calc_log.append(f"             = |{results['min_v']*1000:.1f}mV - {baseline*1000:.1f}mV|")
                    calc_log.append(f"  ★ UNDERSHOOT = {droop_mv:.1f}mV (Limit: <{rail.max_droop_mv}mV)")
                else:
                    results['droop_mv'] = 0.0

            # ============================================================
            # STEP 4: Calculate RECOVERY TIME using cursors or waveform
            # ============================================================
            calc_log.append("\n[STEP 4] CALCULATING RECOVERY TIME")
            calc_log.append("  Recovery = time for voltage to return within tolerance of baseline")

            # Try using cursor measurements if available
            try:
                # Set marker mode to manual for cursor measurements
                self._scope.set_marker_mode("MANual")
                time.sleep(0.1)

                # Get waveform data for cursor positioning
                waveform = self._scope.get_channel_data(1)
                if waveform is not None:
                    voltage_data = waveform['voltage']
                    time_data = waveform['time']
                    x_increment = waveform.get('x_increment', 1e-9)

                    calc_log.append(f"  Waveform samples: {len(voltage_data)} points")
                    calc_log.append(f"  Time resolution: {x_increment*1e9:.1f}ns per sample")

                    # Find trigger point (where transient starts)
                    derivative = np.diff(voltage_data)
                    if direction == LoadStepDirection.POSITIVE:
                        trigger_idx = np.argmin(derivative)  # Largest negative change
                    else:
                        trigger_idx = np.argmax(derivative)  # Largest positive change

                    trigger_time = time_data[trigger_idx]
                    calc_log.append(f"  Trigger point: index {trigger_idx}, time {trigger_time*1e9:.1f}ns")

                    # Find recovery point (when voltage returns to within tolerance of 0V)
                    # AC coupling: use fixed 5mV tolerance (baseline is ~0V)
                    tolerance = 0.005  # 5mV
                    calc_log.append(f"  Settlement tolerance: ±{tolerance*1000:.1f}mV")

                    post_trigger = voltage_data[trigger_idx:]
                    # Note: post_time can be used for absolute timing if needed
                    # post_time = time_data[trigger_idx:]

                    recovery_idx = None
                    for i in range(len(post_trigger)):
                        if abs(post_trigger[i] - baseline) <= tolerance:
                            # Check if it stays settled (next 50 samples)
                            if i + 50 < len(post_trigger):
                                if np.all(np.abs(post_trigger[i:i+50] - baseline) <= tolerance):
                                    recovery_idx = i
                                    break

                    if recovery_idx is not None:
                        recovery_time_s = recovery_idx * x_increment
                        recovery_us = recovery_time_s * 1e6
                        recovery_ns = recovery_time_s * 1e9

                        results['recovery_us'] = recovery_us
                        calc_log.append(f"\n  Recovery found at index: {recovery_idx}")
                        calc_log.append(f"  RECOVERY TIME = {recovery_idx} samples × {x_increment*1e9:.1f}ns")
                        calc_log.append(f"                = {recovery_ns:.1f}ns = {recovery_us:.3f}µs")
                        calc_log.append(f"  ★ RECOVERY TIME = {recovery_us:.1f}µs ({recovery_ns:.0f}ns)")
                        calc_log.append(f"    (Limit: <{rail.max_recovery_time_us}µs)")
                    else:
                        calc_log.append("  WARNING: Recovery point not found in capture window")
                        calc_log.append("  Using capture window duration as recovery time")
                        results['recovery_us'] = len(post_trigger) * x_increment * 1e6

            except Exception as cursor_err:
                calc_log.append(f"  Cursor measurement failed: {cursor_err}")
                calc_log.append("  Using waveform analysis for recovery time")

            results['method'] = 'SCOPE_MEASUREMENTS'

            # ============================================================
            # SUMMARY
            # ============================================================
            calc_log.append("\n" + "=" * 80)
            calc_log.append("MEASUREMENT SUMMARY (SCOPE HARDWARE)")
            calc_log.append("=" * 80)
            calc_log.append(f"Droop:     {results['droop_mv']:.1f}mV  (Limit: {rail.max_droop_mv}mV)  "
                          f"{'✓ PASS' if results['droop_mv'] <= rail.max_droop_mv else '✗ FAIL'}")
            calc_log.append(f"Overshoot: {results['overshoot_mv']:.1f}mV  (Limit: {rail.max_overshoot_mv}mV)  "
                          f"{'✓ PASS' if results['overshoot_mv'] <= rail.max_overshoot_mv else '✗ FAIL'}")
            calc_log.append(f"Recovery:  {results['recovery_us']:.1f}µs (Limit: {rail.max_recovery_time_us}µs) "
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

            self._logger.info(f"Performing {direction.value} load step: {step_desc}")  # Log what we're doing

            # *** STEP 1: SET UP THE STARTING CURRENT ***
            self._load.set_current_level(initial_ma / 1000.0)  # Set load to starting current (convert mA to A by ÷1000)
            self._load.enable_input()  # Turn on the electronic load (start pulling current)
            time.sleep(0.5)  # Wait 0.5 seconds for current to stabilize

            # *** STEP 2: CONFIGURE OSCILLOSCOPE TRIGGER FOR FAST TRANSIENT CAPTURE ***
            #
            # ╔════════════════════════════════════════════════════════════════════════════╗
            # ║  AC-COUPLED TRIGGER LEVELS (in millivolts, relative to 0V baseline)        ║
            # ╠════════════════════════════════════════════════════════════════════════════╣
            # ║  With AC coupling, the pre-step flat portion sits near 0V.                 ║
            # ║  Droop goes NEGATIVE, overshoot goes POSITIVE.                             ║
            # ║                                                                            ║
            # ║  POSITIVE step (droop):    Falling edge, trigger at NEGATIVE mV            ║
            # ║  NEGATIVE step (overshoot): Rising edge, trigger at POSITIVE mV            ║
            # ║                                                                            ║
            # ║  Set ~2-3x idle ripple so noise doesn't retrigger.                         ║
            # ╚════════════════════════════════════════════════════════════════════════════╝

            # ┌──────────────────────────────────────────────────────────────────────────┐
            # │  TRIGGER LEVELS BY RAIL GROUP (in millivolts) - EDIT HERE                │
            # │                                                                          │
            # │  Rail group          │ Droop trigger (mV) │ Overshoot trigger (mV)       │
            # │  3V3 / 3V6           │  -20               │  +15                         │
            # │  2V5 / 1V8           │  -15               │  +12                         │
            # │  Core 1V35/1V_PS/PL  │  -12               │  +10                         │
            # │  Other (E0 rails)    │  -10               │  +10                         │
            # └──────────────────────────────────────────────────────────────────────────┘
            if rail.name in ["3V3", "3V6"]:
                DROOP_TRIGGER_MV = -20    # Falling edge level for droop
                OVERSHOOT_TRIGGER_MV = 15  # Rising edge level for overshoot
            elif rail.name in ["2V5", "1V8"]:
                DROOP_TRIGGER_MV = -15
                OVERSHOOT_TRIGGER_MV = 12
            elif rail.name in ["1V35", "1V_PS", "1V_PL"]:
                DROOP_TRIGGER_MV = -12
                OVERSHOOT_TRIGGER_MV = 10
            else:
                # E0 rails and any others
                DROOP_TRIGGER_MV = -10
                OVERSHOOT_TRIGGER_MV = 10
            # └──────────────────────────────────────────────────────────────────────────┘

            # Apply trigger based on step direction
            if direction == LoadStepDirection.POSITIVE:
                # Droop: voltage goes NEGATIVE in AC mode -> trigger FALLING edge
                trigger_level_v = DROOP_TRIGGER_MV / 1000.0  # Convert mV to V
                trigger_slope_scope = "NEG"  # Falling edge
                self._logger.info(f"Positive step (droop): FALLING edge at {DROOP_TRIGGER_MV}mV")
            else:
                # Overshoot: voltage goes POSITIVE in AC mode -> trigger RISING edge
                trigger_level_v = OVERSHOOT_TRIGGER_MV / 1000.0  # Convert mV to V
                trigger_slope_scope = "POS"  # Rising edge
                self._logger.info(f"Negative step (overshoot): RISING edge at +{OVERSHOOT_TRIGGER_MV}mV")

            # Configure trigger with NORMAL sweep (waits for actual trigger event)
            self._scope.configure_trigger(
                channel=1,
                trigger_level=trigger_level_v,
                trigger_slope=trigger_slope_scope,
                sweep_mode="NORMal"  # Wait for actual trigger, no auto-trigger
            )
            self._logger.info(f"Trigger: {trigger_slope_scope} edge at {trigger_level_v*1000:.0f}mV (AC-coupled, 0V baseline)")
            self._logger.info(f"  Rail: {rail.name}, Sweep: NORMAL")

            # *** STEP 3: STABILIZE BEFORE ARMING ***
            # Wait for any existing transients to settle before arming
            time.sleep(0.5)

            # *** STEP 4: ARM THE OSCILLOSCOPE (get it ready to capture) ***
            self._scope.single()  # Set to single-shot mode (capture once when triggered)
            time.sleep(0.3)  # Wait for scope to be ready

            # *** STEP 5: EXECUTE THE LOAD STEP! ***
            # This is the actual test - suddenly change the current
            step_time = time.time()  # Record when we execute the step
            self._load.set_current_level(final_ma / 1000.0)  # Change to final current (the "step")
            # At this instant, the voltage should change, triggering the oscilloscope to capture
            self._logger.info(f"Load step executed at {step_time:.3f}")

            # *** STEP 6: WAIT FOR OSCILLOSCOPE TO TRIGGER AND CAPTURE ***
            # Wait for scope to trigger with timeout checking
            max_wait_time = 5.0  # Maximum 5 seconds to wait for trigger
            check_interval = 0.2  # Check every 200ms
            elapsed = 0.0
            triggered = False

            while elapsed < max_wait_time:
                time.sleep(check_interval)
                elapsed += check_interval

                # Check if scope has triggered (stopped acquiring)
                try:
                    # Query acquisition state - if stopped, trigger occurred
                    acq_state = self._scope._scpi_wrapper.query(":RSTate?").strip()
                    if acq_state == "STOP":
                        triggered = True
                        self._logger.info(f"Oscilloscope triggered after {elapsed:.1f}s")
                        break
                except:
                    pass  # Continue waiting if query fails

            # Prepare screenshot info
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_name = f"{rail.name}_{direction.value}_{timestamp}.png"
            screenshot_path = str(self.screenshot_dir / screenshot_name)
            actual_screenshot = None

            if triggered:
                # *** TRIGGER SUCCESSFUL - CAPTURE SCREENSHOT IMMEDIATELY ***
                self._logger.info("*** TRIGGER FIRED! Capturing screenshot NOW ***")
                time.sleep(0.1)  # Brief settling

                try:
                    actual_screenshot = self._scope.get_screenshot(screenshot_path, freeze_acquisition=True)
                    self._logger.info(f"Screenshot saved: {screenshot_name}")
                except Exception as screenshot_err:
                    self._logger.warning(f"Screenshot failed: {screenshot_err}")

            else:
                # *** TRIGGER DID NOT FIRE ***
                self._logger.warning(f"*** TRIGGER DID NOT FIRE (waited {elapsed:.1f}s) ***")
                self._logger.info(f"  Expected trigger level: {trigger_level_v:.3f}V")
                self._logger.info(f"  Check: Is voltage actually crossing this level?")

                # Force trigger to capture current screen
                try:
                    self._scope._scpi_wrapper.write(":TRIGger:FORCe")
                    time.sleep(0.3)
                    self._logger.info("Forced trigger - capturing current display")

                    actual_screenshot = self._scope.get_screenshot(screenshot_path, freeze_acquisition=True)
                    self._logger.info(f"Screenshot saved (forced): {screenshot_name}")
                except Exception as e:
                    self._logger.warning(f"Force trigger/screenshot failed: {e}")

            # Ensure scope is stopped before reading waveform data
            try:
                self._scope._scpi_wrapper.write(":STOP")
                time.sleep(0.2)
            except:
                pass

            # *** STEP 7: ANALYZE THE WAVEFORM (THIS IS WHERE MEASUREMENTS HAPPEN!) ***
            droop_mv, recovery_us, overshoot_mv, has_ringing, detailed_calculations = self._analyze_waveform(rail, direction)
            # This function (annotated above) downloads the waveform data and calculates all the measurements
            # NOW it also returns a detailed calculation log showing every step!

            # *** STEP 8: DETERMINE PASS/FAIL ***
            # Check if ALL criteria are met:
            passed = (
                droop_mv <= rail.max_droop_mv and              # Droop is within limit AND
                recovery_us <= rail.max_recovery_time_us and   # Recovery time is within limit AND
                overshoot_mv <= rail.max_overshoot_mv and      # Overshoot is within limit AND
                not has_ringing                                 # No ringing detected
            )
            # If ALL of the above are true, passed = True; if ANY fail, passed = False

            # *** STEP 9: CREATE RESULT OBJECT (package all the data) ***
            result = TransientResult(
                rail_name=rail.name,                    # Which rail
                step_direction=direction.value,         # POSITIVE or NEGATIVE
                load_step_description=step_desc,        # "100mA -> 800mA"
                droop_mv=droop_mv,                      # Measured droop
                recovery_time_us=recovery_us,           # Measured recovery time
                overshoot_mv=overshoot_mv,              # Measured overshoot
                has_ringing=has_ringing,                # True/False for ringing
                screenshot_path=actual_screenshot or screenshot_path,  # Path to screenshot
                timestamp=timestamp,                     # When test was done
                result="PASS" if passed else "FAIL",    # Overall result
                notes=self._generate_notes(rail, droop_mv, recovery_us, overshoot_mv, has_ringing),  # Notes
                detailed_calculations=detailed_calculations  # NEW: Complete calculation log showing every step!
            )

            # *** STEP 10: LOG THE RESULTS (write to logbook and show on screen) ***
            status = "PASS" if passed else "FAIL"
            self._logger.info(f"  {direction.value} step: {status}")  # Log overall result
            # Log each measurement with its limit
            self._logger.info(f"    Droop: {droop_mv:.1f}mV (limit: {rail.max_droop_mv:.1f}mV)")
            self._logger.info(f"    Recovery: {recovery_us:.1f}us (limit: {rail.max_recovery_time_us:.1f}us)")
            self._logger.info(f"    Overshoot: {overshoot_mv:.1f}mV (limit: {rail.max_overshoot_mv:.1f}mV)")
            self._logger.info(f"    Ringing: {'Yes' if has_ringing else 'No'}")

            # *** STEP 11: SAVE DETAILED CALCULATIONS TO FILE ***
            # Save the step-by-step calculation log to a separate text file
            calc_filename = f"{rail.name}_{direction.value}_{timestamp}_calculations.txt"
            calc_path = self.calculations_dir / calc_filename
            try:
                with open(calc_path, 'w', encoding='utf-8') as f:
                    f.write(detailed_calculations)
                self._logger.info(f"    Detailed calculations saved: {calc_filename}")
            except Exception as save_err:
                self._logger.warning(f"    Could not save calculation details: {save_err}")

            return result  # Return the result object

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

    def _analyze_waveform(self, rail: RailConfig, direction: LoadStepDirection) -> Tuple[float, float, float, bool, str]:
        """
        *** THIS IS WHERE THE MEASUREMENTS HAPPEN! ***
        Analyze captured waveform for transient parameters - this is the "measurement brain"

        TWO-STAGE MEASUREMENT APPROACH:
        1. FIRST: Try using oscilloscope's built-in hardware measurements (VMAX, VMIN, etc.)
           - More accurate as they use the scope's measurement engine
           - Directly measures droop, overshoot from the captured waveform
        2. SECOND: Fall back to waveform data analysis if hardware measurements fail
           - Downloads raw waveform data
           - Calculates droop, recovery time, overshoot from voltage samples

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
        calc_log.append("STAGE 1: OSCILLOSCOPE HARDWARE MEASUREMENTS")
        calc_log.append("(Using scope's built-in VMAX, VMIN, VTOP measurements)")
        calc_log.append("=" * 80)

        scope_measurements = self._measure_transient_with_scope(rail, direction)

        if scope_measurements['method'] == 'SCOPE_MEASUREMENTS':
            # Hardware measurements succeeded - use these values
            droop_mv = scope_measurements['droop_mv']
            overshoot_mv = scope_measurements['overshoot_mv']
            recovery_us = scope_measurements['recovery_us']
            calc_log.append("\n✓ Scope hardware measurements SUCCEEDED")
            calc_log.append(f"  Droop (VTOP - VMIN): {droop_mv:.1f}mV")
            calc_log.append(f"  Overshoot (VMAX - VTOP): {overshoot_mv:.1f}mV")
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
            # Droop = how much voltage drops FROM the baseline (nominal voltage)
            # Example: 3.6V baseline drops to 3.525V = 75mV droop
            calc_log.append("\n[STEP 5] MEASURING DROOP AND OVERSHOOT")
            if direction == LoadStepDirection.POSITIVE:  # If load INCREASED (voltage should drop)
                calc_log.append("  Direction: POSITIVE (Load increased → Voltage should DROP)")
                calc_log.append(f"  Baseline (nominal): {baseline:.4f}V")

                # MEASURE DROOP: Voltage drops when load increases - find the lowest point
                min_voltage = np.min(post_trigger)  # Find minimum voltage after trigger
                min_idx = np.argmin(post_trigger)  # Find position of minimum voltage
                min_time_us = (time_data[trigger_idx + min_idx] - time_data[trigger_idx]) * 1e6
                droop_mv = (baseline - min_voltage) * 1000  # Droop = baseline - minimum (in mV)

                calc_log.append(f"\n  DROOP CALCULATION:")
                calc_log.append(f"    Baseline voltage: {baseline:.4f}V ({baseline*1000:.1f}mV)")
                calc_log.append(f"    Minimum voltage: {min_voltage:.4f}V ({min_voltage*1000:.1f}mV)")
                calc_log.append(f"    Time to minimum: {min_time_us:.1f}µs after step")
                calc_log.append(f"    Droop = Baseline - Minimum = {baseline:.4f}V - {min_voltage:.4f}V = {droop_mv:.1f}mV")
                calc_log.append(f"    ★ DROOP = {droop_mv:.1f}mV (Limit: <{rail.max_droop_mv}mV) {'✓ PASS' if droop_mv <= rail.max_droop_mv else '✗ FAIL'}")

                # MEASURE OVERSHOOT: Find if voltage bounces UP after recovering
                if min_idx < len(post_trigger) - 100:  # If there's enough data after minimum
                    after_min = post_trigger[min_idx:]  # Get data after the minimum point
                    max_after = np.max(after_min)  # Find highest point after minimum
                    max_after_idx = np.argmax(after_min)
                    max_time_us = (time_data[trigger_idx + min_idx + max_after_idx] - time_data[trigger_idx]) * 1e6
                    overshoot_mv = max(0, (max_after - baseline) * 1000)  # How much it bounced above baseline

                    calc_log.append(f"\n  OVERSHOOT CALCULATION:")
                    calc_log.append(f"    Maximum voltage after recovery: {max_after:.4f}V ({max_after*1000:.1f}mV)")
                    calc_log.append(f"    Time to maximum: {max_time_us:.1f}µs after step")
                    calc_log.append(f"    Overshoot = Maximum - Baseline = {max_after:.4f}V - {baseline:.4f}V = {overshoot_mv:.1f}mV")
                    calc_log.append(f"    ★ OVERSHOOT = {overshoot_mv:.1f}mV (Limit: <{rail.max_overshoot_mv}mV) {'✓ PASS' if overshoot_mv <= rail.max_overshoot_mv else '✗ FAIL'}")
                else:
                    overshoot_mv = 0.0
                    calc_log.append(f"\n  OVERSHOOT: Not enough data after minimum point to measure")

            else:  # If load DECREASED (voltage should rise/overshoot then settle)
                calc_log.append("  Direction: NEGATIVE (Load decreased → Voltage should RISE)")
                calc_log.append(f"  Baseline (nominal): {baseline:.4f}V")

                # MEASURE OVERSHOOT: Voltage rises when load decreases - find the highest point
                max_voltage = np.max(post_trigger)  # Find maximum voltage after trigger
                max_idx = np.argmax(post_trigger)  # Find position of maximum voltage
                max_time_us = (time_data[trigger_idx + max_idx] - time_data[trigger_idx]) * 1e6
                overshoot_mv = (max_voltage - baseline) * 1000  # Overshoot = maximum - baseline

                calc_log.append(f"\n  OVERSHOOT CALCULATION:")
                calc_log.append(f"    Baseline voltage: {baseline:.4f}V ({baseline*1000:.1f}mV)")
                calc_log.append(f"    Maximum voltage: {max_voltage:.4f}V ({max_voltage*1000:.1f}mV)")
                calc_log.append(f"    Time to maximum: {max_time_us:.1f}µs after step")
                calc_log.append(f"    Overshoot = Maximum - Baseline = {max_voltage:.4f}V - {baseline:.4f}V = {overshoot_mv:.1f}mV")
                calc_log.append(f"    ★ OVERSHOOT = {overshoot_mv:.1f}mV (Limit: <{rail.max_overshoot_mv}mV) {'✓ PASS' if overshoot_mv <= rail.max_overshoot_mv else '✗ FAIL'}")

                # MEASURE DROOP/UNDERSHOOT: Find if voltage dips DOWN after the overshoot
                if max_idx < len(post_trigger) - 100:  # If there's enough data after maximum
                    after_max = post_trigger[max_idx:]  # Get data after the maximum point
                    min_after = np.min(after_max)  # Find lowest point after maximum
                    min_after_idx = np.argmin(after_max)
                    min_time_us = (time_data[trigger_idx + max_idx + min_after_idx] - time_data[trigger_idx]) * 1e6
                    droop_mv = max(0, (baseline - min_after) * 1000)  # Undershoot below baseline

                    calc_log.append(f"\n  UNDERSHOOT CALCULATION (droop after overshoot):")
                    calc_log.append(f"    Minimum voltage after peak: {min_after:.4f}V ({min_after*1000:.1f}mV)")
                    calc_log.append(f"    Time to minimum: {min_time_us:.1f}µs after step")
                    calc_log.append(f"    Undershoot = Baseline - Minimum = {baseline:.4f}V - {min_after:.4f}V = {droop_mv:.1f}mV")
                    calc_log.append(f"    ★ UNDERSHOOT = {droop_mv:.1f}mV (Limit: <{rail.max_droop_mv}mV) {'✓ PASS' if droop_mv <= rail.max_droop_mv else '✗ FAIL'}")
                else:
                    droop_mv = 0.0
                    calc_log.append(f"\n  UNDERSHOOT: Not enough data after maximum point to measure")

            # *** STEP 6: MEASURE RECOVERY TIME (how long to return to baseline/nominal) ***
            # Recovery = time for voltage to return to within tolerance of the baseline voltage
            calc_log.append("\n[STEP 6] MEASURING RECOVERY TIME")
            calc_log.append(f"  Recovery = time to return to baseline voltage ({baseline:.4f}V)")

            # Use 2% tolerance or 5mV, whichever is larger
            tolerance_percent = baseline * 0.02  # 2% of baseline
            tolerance_fixed = 0.005  # 5mV fixed
            tolerance = max(tolerance_percent, tolerance_fixed)

            calc_log.append(f"  Settlement tolerance: ±{tolerance*1000:.1f}mV (±{tolerance/baseline*100:.1f}% of baseline)")
            calc_log.append(f"  Target range: {baseline - tolerance:.4f}V to {baseline + tolerance:.4f}V")
            calc_log.append(f"               ({(baseline - tolerance)*1000:.1f}mV to {(baseline + tolerance)*1000:.1f}mV)")

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
            calc_log.append(f"Droop:        {droop_mv:.1f}mV  (Limit: {rail.max_droop_mv}mV)  {'✓ PASS' if droop_mv <= rail.max_droop_mv else '✗ FAIL'}")
            calc_log.append(f"Recovery:     {recovery_us:.1f}µs (Limit: {rail.max_recovery_time_us}µs) {'✓ PASS' if recovery_us <= rail.max_recovery_time_us else '✗ FAIL'}")
            calc_log.append(f"Overshoot:    {overshoot_mv:.1f}mV  (Limit: {rail.max_overshoot_mv}mV)  {'✓ PASS' if overshoot_mv <= rail.max_overshoot_mv else '✗ FAIL'}")
            calc_log.append(f"Ringing:      {'YES' if has_ringing else 'NO'}      (Required: NO)  {'✗ FAIL' if has_ringing else '✓ PASS'}")
            overall_pass = (droop_mv <= rail.max_droop_mv and recovery_us <= rail.max_recovery_time_us and
                          overshoot_mv <= rail.max_overshoot_mv and not has_ringing)
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
            overshoot_mv = rail.max_overshoot_mv * 2.0     # FAIL value
            has_ringing = True  # FAIL value
            calc_log.append(f"  FAIL Droop: {droop_mv:.1f}mV (2x limit)")
            calc_log.append(f"  FAIL Recovery: {recovery_us:.1f}µs (2x limit)")
            calc_log.append(f"  FAIL Overshoot: {overshoot_mv:.1f}mV (2x limit)")
            calc_log.append(f"  FAIL Ringing: YES")

        # Return all FIVE measurements as a package (tuple): measurements + detailed calculations
        return (droop_mv, recovery_us, overshoot_mv, has_ringing, "\n".join(calc_log))

    def _generate_notes(self, rail: RailConfig, droop: float, recovery: float, overshoot: float, ringing: bool) -> str:
        """Generate notes about the measurement"""
        notes = []

        if droop > rail.max_droop_mv:
            notes.append(f"Droop exceeds limit by {droop - rail.max_droop_mv:.1f}mV")
        if recovery > rail.max_recovery_time_us:
            notes.append(f"Recovery exceeds limit by {recovery - rail.max_recovery_time_us:.1f}us")
        if overshoot > rail.max_overshoot_mv:
            notes.append(f"Overshoot exceeds limit by {overshoot - rail.max_overshoot_mv:.1f}mV")
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
        self._logger.info(f"  Limits: Droop<{rail.max_droop_mv}mV, Recovery<{rail.max_recovery_time_us}us, Overshoot<{rail.max_overshoot_mv}mV")
        self._logger.info("=" * 60)

        result = RailTestResult(
            rail_name=rail.name,
            test_point=rail.test_point
        )

        # Configure instruments with FAST CAPTURE mode for sub-microsecond transients
        # This uses 500ns/div timebase to capture fast droop and recovery (like your 280ns example)
        if not self.configure_oscilloscope_for_rail(rail, fast_capture=True):
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
            rails_to_test = [r for r in self.RAIL_CONFIGS if r.name in rails]
        else:
            rails_to_test = self.RAIL_CONFIGS

        print(f"\nRails to test ({len(rails_to_test)}):")
        for i, rail in enumerate(rails_to_test, 1):
            print(f"  {i}. {rail.name} ({rail.test_point}): {rail.load_step_positive}")

        print("\n" + "-" * 70)
        print("INSTRUCTIONS:")
        print("  - For each rail, you will be asked to confirm connection")
        print("  - Type 'yes' or 'y' to proceed with testing")
        print("  - Type 'skip' to skip to the next rail")
        print("  - Type 'quit' to end the test")
        print("-" * 70 + "\n")

        # Test each rail
        for i, rail in enumerate(rails_to_test, 1):
            print(f"\n[{i}/{len(rails_to_test)}] Ready to test: {rail.name} ({rail.test_point})")
            print(f"    Expected voltage: {rail.expected_voltage_v}V")
            print(f"    Load step: {rail.load_step_positive}")
            print()
            print(f"    Connect electronic load and scope probe to {rail.test_point}")
            print(f"    - Scope CH1: Rail voltage (AC coupled)")
            print()

            while True:
                response = input(f"    Connected to {rail.name}? (yes/skip/quit): ").strip().lower()

                if response in ['yes', 'y']:
                    # Run the test
                    result = self.test_single_rail(rail)
                    self.results.append(result)

                    # Display quick result
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

        # CSV report (with reference to detailed calculation files)
        csv_path = self.reports_dir / f"pwrstd06_results_{timestamp}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Rail', 'Step', 'Load_Step_mA', 'Droop_mV', 'Recovery_us',
                'Overshoot_mV', 'Ringing', 'Result', 'Notes', 'Calculation_File'
            ])

            for result in self.results:
                for step in [result.positive_step, result.negative_step]:
                    if step:
                        # Generate calculation file reference
                        calc_file = f"{step.rail_name}_{step.step_direction}_{step.timestamp}_calculations.txt"
                        writer.writerow([
                            result.rail_name,
                            step.step_direction,
                            step.load_step_description,
                            f"{step.droop_mv:.1f}",
                            f"{step.recovery_time_us:.1f}",
                            f"{step.overshoot_mv:.1f}",
                            'Y' if step.has_ringing else 'N',
                            step.result,
                            step.notes,
                            f"../calculations/{calc_file}"  # Relative path to calculation file
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
            f.write("File naming format: <RAIL>_<DIRECTION>_<TIMESTAMP>_calculations.txt\n")
            f.write("  Example: 3V3_POSITIVE_20250122_143052_calculations.txt\n\n")
            f.write("=" * 80 + "\n")
            f.write("FILES IN THIS TEST RUN:\n")
            f.write("=" * 80 + "\n\n")

            for result in self.results:
                f.write(f"RAIL: {result.rail_name} ({result.test_point})\n")
                if result.positive_step:
                    calc_file = f"{result.positive_step.rail_name}_{result.positive_step.step_direction}_{result.positive_step.timestamp}_calculations.txt"
                    f.write(f"  ├─ POSITIVE: {calc_file}\n")
                    f.write(f"  │  Result: {result.positive_step.result}\n")
                if result.negative_step:
                    calc_file = f"{result.negative_step.rail_name}_{result.negative_step.step_direction}_{result.negative_step.timestamp}_calculations.txt"
                    f.write(f"  └─ NEGATIVE: {calc_file}\n")
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
        """Generate text summary of results"""
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

        # Positive load step results
        lines.append("-" * 80)
        lines.append("POSITIVE LOAD STEP RESULTS (Low -> High)")
        lines.append("-" * 80)
        lines.append(f"{'Rail':<10} {'Load Step':<15} {'Droop':<12} {'Recovery':<12} {'Overshoot':<12} {'Ringing':<8} {'Result':<8}")
        lines.append("-" * 80)

        for result in self.results:
            if result.positive_step:
                step = result.positive_step
                lines.append(
                    f"{result.rail_name:<10} {step.load_step_description:<15} "
                    f"{step.droop_mv:>6.1f}mV    {step.recovery_time_us:>6.1f}us    "
                    f"{step.overshoot_mv:>6.1f}mV    {'Y' if step.has_ringing else 'N':<8} {step.result:<8}"
                )
            else:
                lines.append(f"{result.rail_name:<10} {'NOT TESTED':<15}")

        lines.append("")

        # Negative load step results
        lines.append("-" * 80)
        lines.append("NEGATIVE LOAD STEP RESULTS (High -> Low)")
        lines.append("-" * 80)
        lines.append(f"{'Rail':<10} {'Load Step':<15} {'Droop':<12} {'Recovery':<12} {'Overshoot':<12} {'Ringing':<8} {'Result':<8}")
        lines.append("-" * 80)

        for result in self.results:
            if result.negative_step:
                step = result.negative_step
                lines.append(
                    f"{result.rail_name:<10} {step.load_step_description:<15} "
                    f"{step.droop_mv:>6.1f}mV    {step.recovery_time_us:>6.1f}us    "
                    f"{step.overshoot_mv:>6.1f}mV    {'Y' if step.has_ringing else 'N':<8} {step.result:<8}"
                )
            else:
                lines.append(f"{result.rail_name:<10} {'NOT TESTED':<15}")

        lines.append("")
        lines.append("=" * 80)

        # Overall assessment
        if failed == 0 and not_tested == 0:
            lines.append("OVERALL TEST RESULT: PASS")
            lines.append("All rails meet droop, recovery, and overshoot limits.")
            lines.append("No sustained ringing or oscillation detected.")
        elif failed > 0:
            lines.append("OVERALL TEST RESULT: FAIL")
            lines.append(f"{failed} rail(s) failed to meet specifications.")
        else:
            lines.append("OVERALL TEST RESULT: INCOMPLETE")
            lines.append(f"{not_tested} rail(s) were not tested.")

        lines.append("=" * 80)
        lines.append("")
        lines.append("DETAILED CALCULATION FILES:")
        lines.append("  For step-by-step calculation details showing exactly how each")
        lines.append("  measurement was derived from the waveform data, see the")
        lines.append("  'calculations' folder. Each test has a dedicated file with:")
        lines.append("    - Baseline voltage calculation")
        lines.append("    - Droop measurement (with actual min/max voltages)")
        lines.append("    - Recovery time calculation (settlement criteria)")
        lines.append("    - Overshoot measurement (with actual peak voltages)")
        lines.append("    - Ringing detection analysis (RMS/peak ratios)")
        lines.append("  See calculations/README.txt for a complete index.")
        lines.append("=" * 80)

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
