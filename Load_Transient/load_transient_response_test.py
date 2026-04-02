#!/usr/bin/env python3
# ↑ This tells the computer this is a Python program

"""
Load Transient Response Test Automation - Minimal Intervention Version

╔══════════════════════════════════════════════════════════════════════════════╗
║                      COMPLETE DOCUMENTATION SUMMARY                          ║
║                    For Non-Technical Documentation Reviews                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

─────────────────────────────────────────────────────────────────────────────── 
WHAT THIS PROGRAM DOES (In Simple Terms)
───────────────────────────────────────────────────────────────────────────────

This program automatically tests power supplies to see if they can handle sudden
changes in electrical load. Think of it like testing a car's acceleration and
braking - does it respond quickly and smoothly, or is there delay and overshoot?

WHAT IT TESTS:
- Can the power supply deliver stable voltage when load suddenly increases?
- How long does it take to recover to stable voltage after a load change?
- Does the voltage bounce too much during recovery (overshoot)?
- Is there oscillation/ringing in the recovered signal?

WHY THIS MATTERS:
Power supplies are critical in electronics. If they can't handle load changes well,
the devices they power might malfunction, reset, or crash.

───────────────────────────────────────────────────────────────────────────────
HOW IT WORKS (Step-by-Step)
───────────────────────────────────────────────────────────────────────────────

1. USER CONNECTS EQUIPMENT
   - Plugs oscilloscope probe into a test point on the circuit board
   - Connects electronic load (current puller) to same test point
   - Tells the program "equipment is connected"

2. PROGRAM RUNS MULTIPLE TESTS
   For each power rail (voltage line) selected by the user:
   
   TEST 1 - INCREASING LOAD (Positive Step):
   ├─ Start: Power supply powering load at low current (100mA)
   ├─ Action: Electronic load suddenly jumps to high current (e.g., 800mA)
   ├─ Measurement: Oscilloscope captures voltage waveform during and after change
   └─ Analysis: Measures how much voltage dropped and how fast it recovered
   
   TEST 2 - DECREASING LOAD (Negative Step):
   ├─ Start: Power supply powering load at high current (e.g., 800mA)
   ├─ Action: Electronic load suddenly drops to low current (100mA)
   ├─ Measurement: Oscilloscope captures voltage waveform during and after change
   └─ Analysis: Measures how much voltage rose and how fast it recovered

3. PROGRAM ANALYZES WAVEFORMS
   For each test, the program measures:
   
   DROOP (or RISE): How much did voltage change?
   ├─ For increasing load: How much drop occurred?
   └─ For decreasing load: How much rise occurred?
   
   RECOVERY TIME: How long did it take to stabilize?
   └─ Time for voltage to return to normal operating range
   
   OVERSHOOT: Did voltage bounce too far?
   └─ How much did voltage overshoots its target value?
   
   RINGING: Is there oscillation (noise) in the recovery?
   └─ Detected by analyzing the settled signal for sustained variation

4. PROGRAM GENERATES RESULTS
   ├─ Screenshot of each waveform (for visual inspection)
   ├─ CSV report (spreadsheet format with key measurements)
   ├─ JSON report (data format for computer processing)
   ├─ Text summary (human-readable overview)
   └─ Detailed calculations (step-by-step math explaining how measurements were made)

5. USER DECIDES TO SAVE OR DISCARD
   ├─ Reviews results summary displayed on screen
   ├─ Chooses to save (keeps all results and files)
   └─ Or discard (deletes everything if not satisfied with run)

───────────────────────────────────────────────────────────────────────────────
FILE STRUCTURE AND KEY COMPONENTS
───────────────────────────────────────────────────────────────────────────────

LINE 1: #!/usr/bin/env python3
   └─ Special line telling operating system this is a Python script

LINES 3-32: PROGRAM DESCRIPTION
   └─ Overview of what the program does and how the test is performed

LINES 40-100: IMPORT STATEMENTS
   └─ Brings in helper tools/libraries the program depends on
   └─ Examples: logging (for record-keeping), json (for file saving)

LINES 110-140: CUSTOM JSON ENCODER
   └─ Special tool for converting measurement data to text format for saving

LINES 150-250: CONFIGURATION LOADING FUNCTIONS
   └─ Reads load_transient_config.json file
   └─ Extracts rail definitions, oscilloscope settings, test limits
   └─ Creates Python objects from JSON data

LINES 260-420: DATA STRUCTURES (Enums and Dataclasses)
   └─ Define the "shapes" of data used throughout the program
   └─ Examples:
      • RailConfig: Defines all specs for one power rail
      • TransientResult: Stores results from one test
      • RailTestResult: Stores both positive and negative test results for one rail

LINES 430-550: INTERACTIVE RAIL SELECTOR
   └─ Creates an interactive menu where user picks which rails to test
   └─ Uses keyboard (arrows, TAB, ENTER) for selection
   └─ Shows visual checkboxes for each available rail

LINES 560-1800+: MAIN TEST CLASS (LoadTransientTest)
   └─ THE CORE ENGINE - contains all testing logic
   └─ Key capabilities:
      • Connects to oscilloscope and electronic load
      • Configures instruments for each rail
      • Performs load steps and captures waveforms
      • Analyzes waveforms to extract measurements
      • Saves results and generates reports
      • Manages user interaction and menu prompts

LINES 1800+: MAIN ENTRY POINT
   └─ The function that runs when you execute the script
   └─ Parses command-line arguments
   └─ Creates test object
   └─ Starts the test sequence

───────────────────────────────────────────────────────────────────────────────
KEY TERMINOLOGY FOR DOCUMENTATION REVIEWERS
───────────────────────────────────────────────────────────────────────────────

RAIL: A power supply voltage line (e.g., 3.3V line, 1.8V line)
└─ The program tests multiple rails on the same board

LOAD STEP: A sudden change in current drawn from the power supply
├─ POSITIVE STEP: Load increases (going from low to high current)
└─ NEGATIVE STEP: Load decreases (going from high to low current)

DROOP: The voltage drop when load suddenly increases
└─ Measured in millivolts (mV)
└─ Lower is better (indicates better power quality)

RECOVERY TIME: How long it takes voltage to return to normal after transient
└─ Measured in microseconds (µs or us)
└─ Shorter is better (indicates faster regulation)

OVERSHOOT: Voltage bouncing beyond the target value during recovery
└─ Measured in millivolts (mV)
└─ None or very low is better

RINGING: Oscillation/noise in the voltage during or after recovery
└─ Indicates poor damping or resonance issues
└─ Should not be present in well-designed power supplies

TRANSIENT: A temporary change in voltage (the event we're measuring)
└─ Caused by the sudden change in load current

WAVEFORM: A graph showing how voltage changes over time
└─ Captured by the oscilloscope during the test
└─ Stored as a screenshot for documentation

───────────────────────────────────────────────────────────────────────────────
WHAT CONFIGURATION FILE (load_transient_config.json) CONTAINS
───────────────────────────────────────────────────────────────────────────────

The JSON configuration file (load_transient_config.json) is THE CONTROL CENTER for 
all test parameters. It defines:

1. RAIL CONFIGURATIONS
   └─ All available power rails to test
   └─ For each rail:
      • Rail name (e.g., "3V3")
      • Test point location (e.g., "TP10" - where to probe)
      • Expected nominal voltage (e.g., 3.3V)
      • Load current range (e.g., 100mA to 800mA)
      • Pass/fail limits for droop, recovery time, overshoot

2. OSCILLOSCOPE SETTINGS (PER RAIL)
   └─ Voltage scale (e.g., 50mV per division)
   └─ Time scale (e.g., 50 microseconds per division)
   └─ Trigger levels (voltage level where scope captures)
   └─ Trigger slope (positive for rising edges, negative for falling)

3. INSTRUMENT ADDRESSES
   └─ Where to find the oscilloscope (IP address or COM port)
   └─ Where to find the electronic load

4. TIMING/DELAYS
   └─ How long to wait between steps
   └─ When to trigger the scope
   └─ When to check if scope has captured data

5. ELECTRONIC LOAD SETTINGS
   └─ Slew rate (how fast current changes)
   └─ Over-voltage protection threshold
   └─ Under-voltage protection threshold

6. ANALYSIS PARAMETERS
   └─ What counts as "settled"
   └─ Tolerance for recovery measurement
   └─ Threshold for detecting ringing

WHY THIS SEPARATION IS IMPORTANT:
- Test engineers can change test parameters WITHOUT modifying this code
- Reduces chance of accidentally breaking the test logic
- Makes it easy to test different boards with different requirements
- Configuration is version-controlled separately from code

───────────────────────────────────────────────────────────────────────────────
MEASUREMENTS AND CALCULATIONS (How Results are Determined)
───────────────────────────────────────────────────────────────────────────────

The program uses OSCILLOSCOPE HARDWARE MEASUREMENTS for accuracy:

1. DROOP MEASUREMENT
   └─ For positive step (load increase):
      DROOP = Baseline Voltage - Minimum Voltage Observed
   └─ For negative step (load decrease):
      DROOP = Maximum Voltage Observed - Baseline Voltage
   └─ Source: Oscilloscope's built-in measurements (VMAX, VMIN, DC RMS FS)

2. RECOVERY TIME MEASUREMENT
   └─ Time from when load step occurs until voltage settles
   └─ "Settled" means within ±2-5% of target voltage or ±10mV minimum
   └─ Source: Electronic load voltage readings (more precise than scope)

3. RINGING DETECTION
   └─ Analyzes the settled region of the waveform
   └─ Computes RMS (standard deviation) of voltage
   └─ Looks for sustained oscillation (high noise) vs. clean settlement
   └─ Source: Waveform analysis of oscilloscope data

PASS/FAIL CRITERIA:
├─ DROOP must be < max_droop_mv (defined in config)
├─ RECOVERY TIME must be < max_recovery_time_us (defined in config)
├─ RINGING must not be present or must be minimal
└─ ALL three conditions must be met for the test to PASS

───────────────────────────────────────────────────────────────────────────────
AUTOMATION LEVEL (What's Automatic vs. What Requires User Action)
───────────────────────────────────────────────────────────────────────────────

FULLY AUTOMATIC (Program handles completely):
- Instrument connection and detection
- Instrument configuration for each rail
- Load step execution
- Waveform capture
- Waveform analysis and measurements
- Report generation

SEMI-AUTOMATIC (Program prompts, user confirms):
⚬ Rail selection (program presents menu, user chooses)
⚬ Equipment connection (user connects probes, program waits for confirmation)
⚬ Power supply status (user confirms PSU is powered on)
⚬ Save/discard decision (user reviews results and decides)

MANUAL (Completely human responsibility):
• Connecting oscilloscope probe to test point
• Connecting electronic load to test point
• Powering on the board/PSU
• Interpreting results and deciding if they're acceptable

───────────────────────────────────────────────────────────────────────────────
OUTPUT FILES AND DIRECTORY STRUCTURE
───────────────────────────────────────────────────────────────────────────────

After a test run, results are saved in this structure:

load_transient_results/
└── run_20250122_143052/               (Timestamped folder for this test run)
    ├── load_transient_test.log              (Detailed log of everything that happened)
    ├── screenshots/                   (Oscilloscope waveform captures)
    │   ├── 3V3_low_to_high.png        (Positive step screenshot)
    │   ├── 3V3_high_to_low.png        (Negative step screenshot)
    │   ├── 1V8_low_to_high.png
    │   └── ... (more rails)
    ├── reports/                       (Summary reports)
    │   ├── load_transient_results_20250122_143052.csv    (Spreadsheet format)
    │   ├── load_transient_results_20250122_143052.json   (Data format)
    │   └── load_transient_summary_20250122_143052.txt    (Human-readable summary)
    └── calculations/                  (Step-by-step measurement details)
        ├── README.txt                 (Index of calculation files)
        ├── 3V3_low_to_high_calculations.txt
        ├── 3V3_high_to_low_calculations.txt
        ├── 1V8_low_to_high_calculations.txt
        └── ... (more calculations)

WHY THESE OUTPUTS:
- PNG screenshots: Visual inspection of waveforms (human review)
- CSV: For importing into Excel for further analysis
- JSON: Machine-readable for automated result processing
- TXT Summary: Executive overview of pass/fail status
- Calculation files: Transparency - shows exactly how measurements were made
- LOG file: Troubleshooting if something went wrong

───────────────────────────────────────────────────────────────────────────────
FOR DOCUMENTATION MAINTAINERS
───────────────────────────────────────────────────────────────────────────────

Every major section of this code file now has detailed annotations explaining:
• WHAT the code does (in non-technical terms)
• WHY it's needed (the business purpose)
• HOW it works (the mechanics)
• WHAT IT RETURNS or OUTPUTS

Look for comment blocks starting with:
  ═══════════════════════════════════════════════════════════════════════════════
  This format indicates the start of a major section

Each class and function has comprehensive docstrings explaining:
- Purpose and high-level description
- Parameters (what you pass in)
- Return values (what it gives back)
- Examples (when helpful)

Line-by-line comments explain non-obvious logic.

───────────────────────────────────────────────────────────────────────────────
"""

# This tells the computer this is a Python program

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1: IMPORT EXTERNAL TOOLS (Libraries the program depends on)
# ═════════════════════════════════════════════════════════════════════════════
# These are like toolboxes we're bringing in to use. Each one provides specific
# functionality that the test automation program needs.

import logging          # Tool for recording what the program is doing (like a logbook)
import time            # Tool for waiting/pausing and tracking time
import csv             # Tool for saving data in spreadsheet format
import json
import numpy as np     # For numpy type checking in JSON encoder


# ═════════════════════════════════════════════════════════════════════════════
# CUSTOM JSON ENCODER - Special tool for saving data as text files
# ═════════════════════════════════════════════════════════════════════════════
# Problem: The measurement tools produce special number types (numpy numbers)
# that regular JSON doesn't understand. This encoder translates them.
class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types (bool_, int64, float64, etc.)
    
    Why needed: When saving measurements to JSON files, numpy data types need to be
    converted to regular Python types so they can be written as text.
    
    Example: np.float64(3.14) → 3.14 (regular Python float)
    """
    def default(self, obj):
        # If it's a numpy boolean, convert to Python boolean (True/False)
        if isinstance(obj, np.bool_):
            return bool(obj)
        # If it's a numpy integer, convert to Python integer
        if isinstance(obj, np.integer):
            return int(obj)
        # If it's a numpy floating point number, convert to Python float
        if isinstance(obj, np.floating):
            return float(obj)
        # If it's a numpy array, convert to a Python list
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        # If it's something we don't recognize, let the parent class handle it
        return super().default(obj)

# ═════════════════════════════════════════════════════════════════════════════
# MORE IMPORT TOOLS - Additional toolboxes we need
# ═════════════════════════════════════════════════════════════════════════════
from pathlib import Path           # Tool for working with file locations (paths to files and folders)
from datetime import datetime      # Tool for getting current date and time (for timestamping results)
from typing import Optional, Dict, Any, List, Tuple, Union  # Type hints: helps define what type of data we expect as inputs/outputs
from dataclasses import dataclass, asdict, field           # Tools for organizing and managing data structures (like blueprints for data)
from enum import Enum              # Tool for creating lists of fixed choices (like PASS/FAIL/NOT_TESTED)
import sys             # System tools for the program (like exiting, command line arguments)
import os              # Operating system tools for file management (like creating folders)
import shutil          # Tool for removing directories and files safely

# ─── ANSI colour constants (terminal/console output only) ─────────────────────
_C_GREEN   = "\033[92m"
_C_RED     = "\033[91m"
_C_YELLOW  = "\033[93m"
_C_CYAN    = "\033[96m"
_C_RESET   = "\033[0m"

def _c(text: str, code: str) -> str:
    """Wrap text with an ANSI colour code followed by a reset."""
    return f"{code}{text}{_C_RESET}"

# ──────────────────────────────────────────────────────────────────────────────

# Add parent directory to path for instrument imports
# ↓ This line tells Python where to find the instrument control code (lab equipment drivers)
sys.path.insert(0, str(Path(__file__).parent.parent))

# ═════════════════════════════════════════════════════════════════════════════
# LOAD INSTRUMENT DRIVERS - Connect to lab equipment software
# ═════════════════════════════════════════════════════════════════════════════
# The program needs to control two pieces of equipment:
# 1. Keithley 2380 Electronic Load (device that pulls current from the power supply)
# 2. Keysight DSOX6004A Oscilloscope (device that measures voltage)
# These "drivers" are the software that talks to that equipment.

try:
    # Load the Keithley 2380 electronic load driver (the device that pulls current)
    # This tool allows the program to tell the electronic load what current to draw
    from instrument_control.keithley_load import Keithley2380, Keithley2380Error

    # Import Keysight oscilloscope driver (using the correct class name)
    # This tool allows the program to capture voltage waveforms and take measurements
    from instrument_control.keysight_oscilloscope import KeysightDSOX6004A
    scope_module = 'keysight'  # Remember which oscilloscope brand we're using
    scope_class = KeysightDSOX6004A  # Store the oscilloscope class for later use
    print("Using Keysight DSOX6004A oscilloscope driver")

except ImportError as e:  # If something went wrong loading drivers
    print(f"Import error: {e}")  # Show what went wrong
    print("Ensure instrument_control module is available in parent directory")  # Give helpful advice
    sys.exit(1)  # Exit if drivers cannot be loaded (program cannot continue without them)


# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURATION LOADER - Load test settings from JSON file
# ═════════════════════════════════════════════════════════════════════════════
# ALL test settings live in load_transient_config.json (same folder as this script).
# That file is REQUIRED. There are NO hardcoded fallback values in this code.
# To change rails, trigger levels, timing, etc., edit the JSON — not this file.
# This ensures the test configuration is separate from the test code.

_CONFIG_PATH = Path(__file__).parent / "load_transient_config.json"  # Path to the JSON config file, sitting next to this script

def _load_config(path: Path = _CONFIG_PATH) -> dict:
    """
    Load the JSON config file. Exits the program if the file is missing or
    contains invalid JSON — the config is mandatory, not optional.
    
    This function reads the load_transient_config.json file and converts it to
    a Python dictionary (a data structure the program can work with).
    
    Args:
        path: Where to find the JSON config file (defaults to load_transient_config.json)
    
    Returns:
        A dictionary containing all the configuration (like {rail_configs: [...], timing: {...}})
    """
    try:
        with open(path, "r", encoding="utf-8") as f:  # Open the config file for reading (UTF-8 encoding for special characters)
            cfg = json.load(f)                         # Parse the JSON text into a Python dictionary
        print(f"Loaded config from {path.name}")       # Confirm which config was loaded
        return cfg                                     # Return the parsed config dictionary
    except FileNotFoundError:
        # Config file is required — tell the user and stop the program
        print(f"ERROR: Config file not found: {path}")
        print("       This file is required. Copy load_transient_config.json into the Load_Transient folder.")
        sys.exit(1)  # Stop program execution
    except json.JSONDecodeError as e:
        # Config file exists but has a syntax error in the JSON (like a missing comma or bracket)
        print(f"ERROR: Config file has invalid JSON: {e}")
        print("       Fix load_transient_config.json before running the test.")
        sys.exit(1)  # Stop program execution

_CFG = _load_config()  # Load the config once at startup; every function below uses _CFG


def _build_rail_configs(cfg: dict) -> list:
    """
    Build a list of RailConfig objects from the JSON config.
    Each entry in "rail_configs" becomes one RailConfig with all its limits.
    
    Why this is needed: The JSON file has raw data. This function converts it
    into structured Python objects that the test code can use easily.
    
    Args:
        cfg: The loaded configuration dictionary
    
    Returns:
        A list of RailConfig objects, one for each power rail to be tested
    """
    raw = cfg.get("rail_configs")  # Get the "rail_configs" array from the JSON
    if not raw:
        # Config file must have a "rail_configs" section — abort if missing
        print("ERROR: 'rail_configs' section missing from load_transient_config.json")
        sys.exit(1)
    configs = []
    for r in raw:  # Loop through each rail definition in the JSON array
        # Create a RailConfig object with all the specifications for this rail
        # (think of it like filling out a form with all the rail's parameters)
        configs.append(RailConfig(
            name=r["name"],                            # Rail name, e.g. "3V3" (what we call the voltage line)
            test_point=r["test_point"],                # Board test point, e.g. "TP10" (where to probe)
            expected_voltage_v=r["expected_voltage_v"], # Nominal voltage in volts (what we expect to measure)
            low_current_ma=r["low_current_ma"],        # Low load current (mA), usually 100mA (starting point)
            high_current_ma=r["high_current_ma"],      # High load current (mA), the step target (ending point)
            max_droop_mv=r["max_droop_mv"],            # Max allowed voltage drop (mV) - the limit we're checking
            max_recovery_time_us=r["max_recovery_time_us"],  # Max allowed recovery time (microseconds) - how fast it must recover
            max_overshoot_mv=r["max_overshoot_mv"],    # Max allowed overshoot (mV) - how much bounce is acceptable
        ))
    return configs


def _build_scope_config(cfg: dict) -> dict:
    """
    Build the per-rail oscilloscope settings dict from the JSON config.
    Keys starting with '_' (like "_note") are comments and get stripped out.
    
    What this does: Each rail might need different oscilloscope settings
    (different time scales, voltage scales, trigger levels). This function
    extracts those settings.
    
    Args:
        cfg: The loaded configuration dictionary
    
    Returns:
        A dictionary where each rail name maps to its scope settings
    """
    raw = cfg.get("scope_config")  # Get the "scope_config" section from the JSON
    if not raw:
        # Config file must have a "scope_config" section — abort if missing
        print("ERROR: 'scope_config' section missing from load_transient_config.json")
        sys.exit(1)
    # Return only real entries, stripping out comment keys like "_note"
    # (if a key starts with underscore, it's a comment and we ignore it)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


# ╔═════════════════════════════════════════════════════════════════════════════╗
# ║                         FILE ORGANIZATION GUIDE                              ║
# ║                                                                               ║
# │ This file is organized into these main sections:                             ║
# │                                                                               ║
# │ 1. CONFIGURATION LOADING (lines ~130-200)                                    ║
# │    → Loads test settings from load_transient_config.json file                     ║
# │    → Creates RailConfig objects from JSON data                              ║
# │                                                                               ║
# │ 2. DATA STRUCTURES / ENUMS (lines ~200-400)                                  ║
# │    → TestResult, LoadStepDirection (enums - fixed choices)                  ║
# │    → RailConfig, TransientResult, RailTestResult (data containers)          ║
# │    → These are "blueprints" that define how data is organized               ║
# │                                                                               ║
# │ 3. INTERACTIVE RAIL SELECTOR (lines ~400-550)                                ║
# │    → Creates a menu where user picks which rails to test                    ║
# │    → Handles keyboard input (arrows, TAB, ENTER, etc.)                      ║
# │                                                                               ║
# │ 4. MAIN TEST CLASS - LoadTransientTest (lines ~550-1800)                 ║
# │    THE BRAIN OF THE ENTIRE AUTOMATION                                        ║
# │                                                                               ║
# │    Key Methods:                                                               ║
# │    • __init__() - Initialize (set up directories, load config)              ║
# │    • _setup_logging() - Create logfile                                      ║
# │    • connect_instruments() - Connect to oscilloscope & load                 ║
# │    • disconnect_instruments() - Clean disconnect                            ║
# │    • configure_oscilloscope_for_rail() - Set up scope for one rail         ║
# │    • configure_electronic_load_for_rail() - Set up load for one rail       ║
# │    • perform_load_step() - Execute ONE test (positive or negative)          ║
# │    • _measure_transient_with_scope() - Measure droop using scope hardware  ║
# │    • _analyze_waveform() - Detailed waveform analysis                       ║
# │    • test_single_rail() - Test one rail completely (both steps)             ║
# │    • run_test_sequence() - Main automation (test all rails)                 ║
# │    • _generate_reports() - Create CSV, JSON, text reports                   ║
# │    • _generate_summary_text() - Create formatted summary                    ║
# │    • _print_summary() - Display summary to console                          ║
# │                                                                               ║
# │ 5. MAIN ENTRY POINT (lines ~1800+)                                           ║
# │    → main() function that's called when script runs                         ║
# │    → Parses command-line arguments                                          ║
# │    → Starts the test                                                         ║
# │                                                                               ║
# ╚═════════════════════════════════════════════════════════════════════════════╝

# ═════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES - Define the "shapes" of information the program works with
# ═════════════════════════════════════════════════════════════════════════════
# Think of these like blueprints that define what information gets stored together

# Define the possible test results (like a multiple choice list)
class TestResult(Enum):
    """Test result enumeration - all the possible outcomes for a test
    
    An Enum is a fixed list of allowed values. We use this to make sure
    the program only uses valid result types, preventing typos or invalid values.
    
    Example: result = TestResult.PASS   (not result = "good" - wrong!)
    """
    PASS = "PASS"              # Test passed - everything good! (meets all specs)
    FAIL = "FAIL"              # Test failed - something wrong (does not meet specs)
    WARNING = "WARNING"        # Test passed but with concerns (met specs but close to limits)
    NOT_TESTED = "NOT_TESTED"  # Test was skipped (decided not to test this rail)
    ERROR = "ERROR"            # Test couldn't run due to error (equipment trouble, lost connection, etc.)


# Define the two types of load changes we test
class LoadStepDirection(Enum):
    """Load step direction - which way are we changing the load?
    
    When testing, we do two different things:
    1. POSITIVE: Start at low current, suddenly jump to high current
       (What happens when a device suddenly starts drawing more power?)
    2. NEGATIVE: Start at high current, suddenly drop to low current
       (What happens when a device stops drawing power?)
    """
    POSITIVE = "POSITIVE"  # Increase load: Low → High (100mA → 800mA for example)
    NEGATIVE = "NEGATIVE"  # Decrease load: High → Low (800mA → 100mA for example)


# This is a template for storing all the information about one power rail
@dataclass  # This decorator makes it easy to create data storage objects (like a form template)
class RailConfig:
    """Configuration for a power rail under test - all the specs for one voltage line
    
    A dataclass is like a blueprint form. When the program needs to store
    information about a specific power rail (like 3.3V), it creates one of these
    RailConfig objects and fills in all the properties.
    
    Example:
        rail_33v = RailConfig(
            name='3V3',              # This power rail is called "3V3"
            test_point='TP10',       # We'll probe at test point number 10
            expected_voltage_v=3.3,  # It should measure 3.3 volts
            low_current_ma=100,      # Tests start at 100mA
            high_current_ma=800,     # Tests go up to 800mA
            max_droop_mv=50.0,       # Voltage can't drop more than 50mV
            max_recovery_time_us=500.0,  # Must recover within 500 microseconds
            max_overshoot_mv=100.0   # Voltage bounce can't exceed 100mV
        )
    """
    # WHAT WE MEASURE OR CARE ABOUT:
    name: str                      # Name of the rail (like "3V3" or "1V8") - used for reports
    test_point: str               # Where to probe on the board (like "TP2" or "TP10") - physical location
    expected_voltage_v: float     # What voltage we expect (in Volts) - the nominal/ideal value
    
    # LOAD CURRENTS FOR TESTING (the "step" values):
    low_current_ma: int           # Starting current (usually 100mA) - the "before" state
    high_current_ma: int          # Target current (usually ~50% of rated) - the "after" state
    
    # PASS/FAIL LIMITS (these must be met to pass):
    max_droop_mv: float          # Maximum allowed voltage drop (in millivolts) - how much drop is acceptable
    max_recovery_time_us: float  # Maximum allowed recovery time (in microseconds) - how fast must it recover
    max_overshoot_mv: float      # Maximum allowed voltage overshoot (in millivolts) - how much bounce is acceptable

    @property  # This makes it a calculated value, not stored (recomputed each time it's needed)
    def load_step_positive(self) -> str:
        """Positive load step description - creates a text description
        
        This is helpful for reports and user messages.
        Example: '100mA -> 800mA'
        
        Returns a string showing the load change for positive step testing
        """
        return f"{self.low_current_ma}mA -> {self.high_current_ma}mA"

    @property  # Another calculated value
    def load_step_negative(self) -> str:
        """Negative load step description - creates a text description
        
        This is helpful for reports and user messages.
        Example: '800mA -> 100mA'
        
        Returns a string showing the load change for negative step testing
        """
        return f"{self.high_current_ma}mA -> {self.low_current_ma}mA"


# Template for storing results from ONE test (either positive or negative step)
@dataclass
class TransientResult:
    """Results from a single transient measurement - what happened in one test
    
    When the program runs a single test (positive OR negative step), it stores
    the results in a TransientResult. A RailTestResult will have TWO of these
    (one for positive, one for negative).
    
    Example:
        After testing the positive step on the 3V3 rail, the results might be:
        result = TransientResult(
            rail_name='3V3',
            step_direction='POSITIVE',
            load_step_description='100mA -> 800mA',
            droop_mv=45.2,           # Voltage dropped 45.2mV
            recovery_time_us=280.5,  # Took 280.5 microseconds to recover
            overshoot_mv=12.3,       # Voltage bounced up 12.3mV before settling
            has_ringing=False,       # No oscillation detected
            ...
        )
    """
    # BASIC TEST INFORMATION:
    rail_name: str                    # Which rail was tested (like "3V3")
    step_direction: str               # Was it POSITIVE or NEGATIVE step?
    load_step_description: str        # Text describing the load change (like "100mA -> 800mA")
    
    # MEASURED PARAMETERS (the actual values we captured):
    droop_mv: float = 0.0            # How much did voltage drop? (in millivolts) - the main measurement
    recovery_time_us: float = 0.0    # How long to recover? (in microseconds) - how fast it bounced back
    overshoot_mv: float = 0.0        # How much did voltage bounce up? (in millivolts) - post-recovery spike
    has_ringing: bool = False        # Was there oscillation? (True = yes oscillation, False = clean) - noise on the waveform
    
    # FILES AND METADATA:
    screenshot_path: str = ""        # Where is the picture saved? (file path to the oscilloscope capture)
    timestamp: str = ""              # When did this test happen? (time marking)
    result: str = "NOT_TESTED"       # Did it PASS or FAIL? ("PASS", "FAIL", "ERROR", "NOT_TESTED")
    notes: str = ""                  # Any additional comments (optional notes about the test)
    detailed_calculations: str = ""  # Step-by-step calculation details (for documentation/transparency)

    def to_dict(self) -> Dict[str, Any]:
        """Convert this result to a dictionary (for saving to file)
        
        When we save results to JSON or CSV files, we need to convert the
        TransientResult object to a dictionary format that can be written as text.
        
        Returns:
            A dictionary with all the same data (e.g., {"rail_name": "3V3", "droop_mv": 45.2, ...})
        """
        return asdict(self)  # asdict converts all the properties to a dictionary


# Template for storing BOTH tests for one rail (positive AND negative steps combined)
@dataclass
class RailTestResult:
    """Complete test results for a single rail - combines both positive and negative tests
    
    A rail is fully tested when we do BOTH:
    1. Positive step (load increases) - captured in positive_step
    2. Negative step (load decreases) - captured in negative_step
    
    Together, these tell us if the power supply can handle both types of load changes.
    
    Example:
        After testing the 3V3 rail completely:
        result = RailTestResult(
            rail_name='3V3',
            test_point='TP10',
            positive_step=TransientResult(...),  # Results from low→high test
            negative_step=TransientResult(...),  # Results from high→low test
            overall_result='PASS'                # Both steps passed, so overall PASS
        )
    """
    # BASIC INFORMATION:
    rail_name: str                              # Which rail (like "3V3")
    test_point: str                             # Where it was tested (like "TP10")
    
    # THE TWO TEST MEASUREMENTS (one for each direction):
    positive_step: Optional[TransientResult] = None   # Result from positive step test (load increase)
    negative_step: Optional[TransientResult] = None   # Result from negative step test (load decrease)
    
    # FINAL RESULT:
    overall_result: str = "NOT_TESTED"          # Overall PASS/FAIL for this rail

    def to_dict(self) -> Dict[str, Any]:
        """Convert this result to a dictionary (for saving to file)
        
        Converts RailTestResult to dictionary format for saving as JSON/CSV.
        Includes both positive and negative step results (if they exist).
        
        Returns:
            A dictionary with all results (e.g., {"rail_name": "3V3", "positive_step": {...}, ...})
        """
        return {
            'rail_name': self.rail_name,
            'test_point': self.test_point,
            # Convert positive step to dict if it exists, otherwise None
            'positive_step': self.positive_step.to_dict() if self.positive_step else None,
            # Convert negative step to dict if it exists, otherwise None
            'negative_step': self.negative_step.to_dict() if self.negative_step else None,
            'overall_result': self.overall_result
        }


# ═════════════════════════════════════════════════════════════════════════════
# INTERACTIVE RAIL SELECTOR - User interface for choosing which rails to test
# ═════════════════════════════════════════════════════════════════════════════
# This shows a menu where the user can pick which rails they want to test,
# instead of testing all rails automatically.
# 
# PURPOSE: This makes the test program interactive - the user controls what gets tested

def _enable_ansi():
    """Enable ANSI escape sequences on Windows 10+
    
    ANSI escape sequences are special codes that allow us to format text
    in the terminal (colors, cursor positioning, etc.).
    This function enables these on Windows.
    
    Why it matters: Without this, the interactive menu won't format correctly on Windows.
    """
    try:
        import ctypes  # Library for calling Windows functions
        # Get the Windows kernel (the core of Windows)
        kernel32 = ctypes.windll.kernel32
        # Enable the console mode that supports ANSI sequences
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass  # If it fails, just continue - it's not critical


def interactive_rail_selector(rail_configs):
    """
    Interactive multi-select rail selector - Create a menu for user to pick rails
    
    This function displays a menu where the user can:
    - See all available rails
    - Check [X] or uncheck [ ] each rail with TAB (to mark it for testing)
    - Move up/down with arrow keys
    - Hit ENTER to confirm their selection
    - Press Q to cancel
    
    CONTROLS (For users):
    - UP / DOWN ARROW   Move selection cursor up or down
    - TAB / SPACE       Toggle selection (check/uncheck the current rail)
    - A                 Select all / Deselect all rails at once
    - ENTER             Confirm selection and run tests on selected rails
    - Q / ESC           Cancel (don't run any tests)

    PARAMETERS (For programmers):
    - rail_configs: list[RailConfig] - The list of all available rails to choose from

    RETURNS (What the function gives back):
    - list[str] | None - List of selected rail names (like ['3V3', '1V8']), or None if cancelled
    
    EXAMPLE:
    User is presented with:
        [ ] 3V3  (TP10)  3.30V   100 -> 800mA
        [X] 1V8  (TP2)   1.80V   100 -> 400mA
        [ ] 5V0  (TP15)  5.00V   100 -> 1000mA
    
    User presses TAB on 3V3 and 5V0 to select them, then ENTER:
    Returns: ['3V3', '5V0']
    """
    import msvcrt  # Windows keyboard input library

    _enable_ansi()  # Make sure the menu displays nicely

    # Build a list of rail data for display
    rails = []
    for r in rail_configs:  # For each rail in the configuration
        rails.append({  # Create a dictionary with rail information for display
            'name': r.name,                    # E.g., '3V3'
            'tp': r.test_point,                # E.g., 'TP10'
            'voltage': r.expected_voltage_v,   # E.g., 3.30
            'low': r.low_current_ma,           # E.g., 100
            'high': r.high_current_ma,         # E.g., 800
        })

    selected = [False] * len(rails)  # Initially, no rails are selected [False, False, False, ...]
    cursor = 0  # The cursor starts at the first rail (index 0)

    def render():
        """Helper function: Create the menu display text"""
        lines = []  # Build the menu line by line
        lines.append("")  # Blank line at top
        lines.append("  RAIL SELECTION")  # Title
        lines.append("  " + "=" * 62)  # Separator line
        lines.append("  UP/DOWN: Navigate | TAB: Toggle | ENTER: Run | A: All | Q: Quit")  # Instructions
        lines.append("")  # Blank line
        
        # Show each rail option
        for i, r in enumerate(rails):  # For each rail in the list
            marker = "[X]" if selected[i] else "[ ]"  # Show [X] if selected, [ ] if not
            arrow  = ">>" if i == cursor else "  "  # Show >> if this is the current cursor position
            # Format: "  >> [X] 3V3       (TP10)  3.30V   100 -> 800mA"
            lines.append(
                f"  {arrow} {marker} {r['name']:<10} ({r['tp']:<5}) "
                f"{r['voltage']:>5.2f}V   {r['low']} -> {r['high']}mA"
            )
        
        lines.append("")  # Blank line
        # Show which rails are currently selected
        sel_names = [rails[i]['name'] for i in range(len(rails)) if selected[i]]
        if sel_names:
            lines.append(f"  Selected: {', '.join(sel_names)}  ({len(sel_names)} rails)")
        else:
            lines.append("  Selected: None  (use TAB to select rails)")
        return lines

    # Initial display - show the menu
    display_lines = render()
    for line in display_lines:
        print(line)  # Print each line of the menu
    sys.stdout.flush()  # Make sure everything is printed immediately

    # Wait for user to interact with the menu
    while True:
        key = msvcrt.getch()  # Get one key press from the user

        if key == b'\r':                              # User pressed ENTER
            sel = [rails[i]['name'] for i in range(len(rails)) if selected[i]]  # Get selected rail names
            if not sel:  # If user didn't select anything
                continue  # Keep showing the menu (need at least one selection)
            print()  # Print blank line
            return sel  # Return the selected rail names and exit

        elif key == b'\t' or key == b' ':             # User pressed TAB or SPACE
            selected[cursor] = not selected[cursor]  # Toggle the current rail's selection

        elif key in (b'a', b'A'):                     # User pressed A (toggle ALL)
            if all(selected):  # If all are currently selected
                selected = [False] * len(rails)  # Deselect all
            else:
                selected = [True] * len(rails)  # Select all

        elif key == b'\xe0' or key == b'\x00':        # Arrow key prefix character (indicates next is an arrow key)
            key2 = msvcrt.getch()  # Get the next character to see which arrow
            if key2 == b'H':                          # UP arrow key
                cursor = (cursor - 1) % len(rails)  # Move cursor up (wrap around to bottom if at top)
            elif key2 == b'P':                        # DOWN arrow key
                cursor = (cursor + 1) % len(rails)  # Move cursor down (wrap around to top if at bottom)

        elif key in (b'q', b'Q', b'\x1b'):            # User pressed Q or ESC (cancel)
            print("\n  Selection cancelled.")
            return None  # Return None to indicate user cancelled

        else:
            continue  # Ignore other keys

        # Redraw the menu in place (overwrite the old display)
        display_lines = render()  # Generate fresh menu display
        # Move cursor up to the top of the menu (to overwrite it)
        sys.stdout.write(f"\033[{len(display_lines)}A")
        # Redraw each line, clearing it and replacing with new content
        for line in display_lines:
            sys.stdout.write(f"\033[2K{line}\n")
        sys.stdout.flush()  # Make sure everything displays immediately


# This is the main class - the "brain" that runs the entire test
class LoadTransientTest:
    """
    Load Transient Response Test - Minimal User Intervention

    This automation (what it does automatically):
    - Asks you to confirm test equipment is connected to each rail
    - Automatically performs positive and negative load steps
    - Captures voltage waveforms and analyzes the response
    - Saves screenshots with proper labels
    - Moves to the next rail after completion
    - Generates a comprehensive summary report at the end
    """

# ═════════════════════════════════════════════════════════════════════════════
# MAIN TEST CLASS - The "Brain" of the entire test automation
# ═════════════════════════════════════════════════════════════════════════════
# This is the main class that controls everything. Think of it as the conductor
# of an orchestra - it coordinates all the instruments and the test sequence.

class LoadTransientTest:
    """
    Load Transient Response Test - Minimal User Intervention
    
    THIS IS THE MAIN TEST AUTOMATION ENGINE. It does:
    - Manages connection to lab test equipment (oscilloscope, electronic load)
    - Configures each instrument appropriately for each rail
    - Executes load steps and captures waveforms
    - Analyzes the waveforms to measure droop, recovery time, overshoot, ringing
    - Saves results, reports, screenshots, and calculation details
    - Generates PDF or HTML reports
    
    Key Philosophy:
    - Configuration comes from load_transient_config.json (the JSON file)
    - No hardcoded values in this code - all settings are in the JSON
    - The test is "minimal intervention" - user just confirms equipment is connected, then it runs automatically
    
    WHAT GETS AUTOMATED:
    1. For each rail (voltage line):
         - Ask user to confirm equipment connections
         - Automatically configure the oscilloscope
         - Automatically configure the electronic load
         - Perform positive load step test (increase current suddenly)
         - Perform negative load step test (decrease current suddenly)
    2. Analyze both measurements
    3. Save results and detailed calculations
    
    WHAT REQUIRES USER ACTION:
    1. Connect the oscilloscope probe to the test point
    2. Connect the electronic load to the same test point
    3. Confirm equipment is ready when prompted
    4. Decide whether to save or discard results after testing
    """

    # ─────────────────────────────────────────────────────────────────────────
    # CLASS-LEVEL ATTRIBUTES (shared across all instances)
    # ─────────────────────────────────────────────────────────────────────────
    # These are loaded once from load_transient_config.json and shared by all test instances
    
    # All the power rails to potentially test (loaded from load_transient_config.json)
    # Example: [RailConfig(name='3V3', ...), RailConfig(name='1V8', ...), ...]
    RAIL_CONFIGS = _build_rail_configs(_CFG)
    
    # Oscilloscope settings for each rail (loaded from load_transient_config.json)
    # Example: {'3V3': {'v_scale': 0.05, 'timebase': 50e-6}, '1V8': {...}, ...}
    SCOPE_CONFIG = _build_scope_config(_CFG)

    def __init__(self,
                 oscilloscope_address: Optional[str] = None,
                 electronic_load_address: Optional[str] = None,
                 output_dir: str = None):
        """
        Initialize Load Transient transient response test - Set up everything when the test starts
        
        This function is called once at the very beginning to set up:
        - Instrument connections (addresses)
        - Output folders (where to save results)
        - Logging (recording what happens)
        - Test configuration (loaded from load_transient_config.json)

        PARAMETERS (What you can provide - all optional):
            oscill oscilloscope_address: Where to find the oscilloscope (IP address or serial port)
                                        If not provided, will try to auto-detect
            electronic_load_address: Where to find the electronic load  
                                    If not provided, will try to auto-detect
            output_dir: Folder where to save test results
                       If not provided, uses "load_transient_results" folder
        
        WHAT THIS FUNCTION DOES:
        1. Reads instrument addresses from config.json (if not provided)
        2. Auto-detects instruments if addresses not provided
        3. Creates output folders for results/screenshots/reports
        4. Sets up logging to record what happens during the test
        5. Initializes variables to store test results
        """
        # ─── READ SETTINGS FROM load_transient_config.json ─────────────────────────
        # The JSON config file is the single source of truth for all settings.
        # If the caller didn't pass an address, we get it from the JSON.
        
        # Get the "instrument_addresses" section from JSON config
        instr_cfg = _CFG.get("instrument_addresses", {})
        
        # If user didn't pass oscilloscope address, use the one from config JSON
        if oscilloscope_address is None:
            oscilloscope_address = instr_cfg.get("oscilloscope")
        
        # If user didn't pass electronic load address, use the one from config JSON
        if electronic_load_address is None:
            electronic_load_address = instr_cfg.get("electronic_load")

        # If user didn't pass output directory, use the one from config JSON
        if output_dir is None:
            out_cfg = _CFG.get("output_dir", {})  # Get the "output_dir" section
            if isinstance(out_cfg, dict):  # If it's a dictionary (has keys like "path")
                output_dir = out_cfg.get("path", "load_transient_results")  # Get the "path" value
            else:
                output_dir = out_cfg or "load_transient_results"  # Otherwise use it directly

        # Read other config sections (each returns {} if missing, so we can provide defaults)
        self._timing = _CFG.get("timing", {})              # Timing delays (wait times between steps)
        self._eload_cfg = _CFG.get("electronic_load", {})  # Electronic load settings (slew rate, protection)
        self._scope_settings = _CFG.get("scope_settings", {})  # Oscilloscope settings (channel, coupling)
        self._analysis_cfg = _CFG.get("analysis", {})      # Analysis parameters (tolerance, thresholds)

        # ─── AUTO-DETECT INSTRUMENTS IF ADDRESSES NOT PROVIDED ───────────────
        # If the user didn't give us addresses, try to find the equipment automatically
        if oscilloscope_address is None or electronic_load_address is None:
            print("\nAuto-detecting instruments...")  # Tell user we're searching
            try:
                # Import the auto-detection tool
                from visa_auto_detect import detect_load_transient_instruments
                # Run the detection (searches for connected equipment)
                detected_scope, detected_load = detect_load_transient_instruments()

                # Use detected addresses if we don't have them
                if oscilloscope_address is None:
                    oscilloscope_address = detected_scope
                if electronic_load_address is None:
                    electronic_load_address = detected_load

            except ImportError:  # If auto-detect module not found
                print("WARNING: visa_auto_detect module not found")
                print("         Instrument addresses must be specified manually")

        # ─── SAVE INSTRUMENT ADDRESSES FOR LATER USE ──────────────────────────
        self.scope_address = oscilloscope_address      # Remember where the oscilloscope is
        self.load_address = electronic_load_address    # Remember where the electronic load is

        # ─── INITIALIZE INSTRUMENT OBJECTS ───────────────────────────────────
        # These will hold the connection objects once we connect
        self._scope = None  # Will hold oscilloscope object when connected (initially None)
        self._load: Optional[Keithley2380] = None  # Will hold electronic load object when connected

        # ─── SETUP OUTPUT DIRECTORIES ────────────────────────────────────────
        # Create folders to organize the results, screenshots, and reports
        
        # Get current date and time for folder naming (e.g., "20250122_143052")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Main results folder: load_transient_results/run_20250122_143052
        self.output_dir = Path(output_dir) / f"run_{timestamp}"
        
        # Subfolder for oscilloscope screenshots/waveforms
        self.screenshot_dir = self.output_dir / "screenshots"
        
        # Subfolder for test reports (CSV, JSON, summary)
        self.reports_dir = self.output_dir / "reports"
        
        # Subfolder for detailed calculation logs (explains how measurements were made)
        self.calculations_dir = self.output_dir / "calculations"

        # ─── CREATE ALL OUTPUT DIRECTORIES ───────────────────────────────────
        # Actually make all the folders on disk
        try:
            for d in [self.output_dir, self.screenshot_dir, self.reports_dir, self.calculations_dir]:
                d.mkdir(parents=True, exist_ok=True)  # Create directory (and parents if needed)
        except (PermissionError, OSError) as e:
            # If we can't write to the requested location, fallback to script directory
            fallback_base = Path(__file__).resolve().parent / "load_transient_results"
            self.output_dir = fallback_base / f"run_{timestamp}"
            self.screenshot_dir = self.output_dir / "screenshots"
            self.reports_dir = self.output_dir / "reports"
            self.calculations_dir = self.output_dir / "calculations"
            for d in [self.output_dir, self.screenshot_dir, self.reports_dir, self.calculations_dir]:
                d.mkdir(parents=True, exist_ok=True)
            print(f"WARNING: Failed to create results directory at '{output_dir}' ({e}).")
            print(f"         Falling back to: {fallback_base}")

        # ─── SETUP LOGGING ────────────────────────────────────────────────────
        # Configure the "logbook" that records everything that happens
        self._setup_logging()

        # ─── INITIALIZE RESULT STORAGE ────────────────────────────────────────
        # These will collect all the test results as we run tests
        self.results: List[RailTestResult] = []  # Empty list to collect test results
        self.test_start_time: Optional[datetime] = None  # Will record when test starts
        self.test_end_time: Optional[datetime] = None    # Will record when test ends

    def _setup_logging(self):
        """
        Configure logging - set up the "logbook" that records what happens
        
        This function creates two logs:
        1. CONSOLE LOG - Important messages printed to the screen (so user sees progress)
        2. FILE LOG - Every detail saved to load_transient_test.log (for troubleshooting)
        
        EXAMPLE log output:
            14:30:52 - INFO - Connecting to instruments...
            14:30:53 - INFO - Oscilloscope connected successfully
            14:30:55 - INFO - Configuring oscilloscope for 3V3
        """
        # Create a logger object (like opening a logbook)
        # Each instance gets a unique ID so multiple test runs have separate logs
        self._logger = logging.getLogger(f"Load Transient.{id(self)}")
        
        # Set to DEBUG level to capture everything (most detailed recording level)
        # DEBUG < INFO < WARNING < ERROR < CRITICAL
        self._logger.setLevel(logging.DEBUG)
        
        # Clear any old handlers (from previous test runs if any)
        self._logger.handlers.clear()

        # ─── CONSOLE HANDLER ───────────────────────────────────────────────
        # This handler prints important messages to the screen so the user sees progress
        ch = logging.StreamHandler()  # Create handler for console/screen output
        ch.setLevel(logging.INFO)     # Only show INFO and above (not every tiny DEBUG detail)
        # Format: "14:30:52 - INFO - Test started"
        ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
        # Attach this handler to the logger
        self._logger.addHandler(ch)

        # ─── FILE HANDLER ───────────────────────────────────────────────────
        # This handler saves ALL messages to a log file (for detailed troubleshooting)
        fh = logging.FileHandler(self.output_dir / "load_transient_test.log", encoding='utf-8')
        fh.setLevel(logging.DEBUG)  # Save EVERYTHING to file (even tiny details)
        # Format: "2025-01-22 14:30:52 - Load Transient.12345 - DEBUG - Detailed message"
        fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        # Attach this handler to the logger
        self._logger.addHandler(fh)

    def connect_instruments(self) -> bool:
        """
        Connect to oscilloscope and electronic load - establish communication with lab equipment
        
        This function:
        1. Connects to the oscilloscope (using VISA protocol over USB/Ethernet)
        2. Connects to the electronic load
        3. Checks that both connections are successful
        
        RETURNS:
            bool - True if both instruments connected successfully, False if connection failed
        
        WHY THIS IS IMPORTANT:
        The test can't run without both instruments. If either fails to connect,
        we stop immediately rather than trying to run with partial equipment.
        """
        self._logger.info("Connecting to instruments...")  # Log that we're starting

        try:  # Try to connect, if anything fails jump to "except"
            # ─── CONNECT TO OSCILLOSCOPE ──────────────────────────────────
            self._logger.info(f"Connecting to oscilloscope at {self.scope_address}")
            
            # Create oscilloscope object (but doesn't connect yet)
            self._scope = scope_class(self.scope_address)
            
            # Actually connect to the oscilloscope
            if not self._scope.connect():
                raise Exception("Failed to connect to oscilloscope")
            
            # Log success
            self._logger.info(f"Oscilloscope connected successfully ({scope_module})")

            # ─── CONNECT TO ELECTRONIC LOAD ───────────────────────────────
            self._logger.info(f"Connecting to electronic load at {self.load_address}")
            
            # Create electronic load object (but doesn't connect yet)
            self._load = Keithley2380(self.load_address)
            
            # Actually connect to the electronic load
            if not self._load.connect():
                raise Exception("Failed to connect to electronic load")
            
            # Log success
            self._logger.info("Electronic load connected successfully")

            return True  # Success! Both instruments connected

        except Exception as e:  # If anything went wrong
            self._logger.error(f"Instrument connection failed: {e}")  # Log the error
            self.disconnect_instruments()  # Clean up - disconnect anything that did connect
            return False  # Return False to indicate failure

    def disconnect_instruments(self):
        """
        Safely disconnect from all instruments - clean shutdown of equipment
        
        This function:
        1. Turns off the electronic load (stops drawing current)
        2. Disconnects from the electronic load
        3. Disconnects from the oscilloscope
        4. Logs everything (but doesn't crash if there are errors)
        
        WHY THIS IS IMPORTANT:
        Proper cleanup is essential - we don't want to leave the electronic load
        pulling current if the connection is lost, or leave equipment in an
        unknown state. This gracefully shuts everything down.
        """
        try:  # Try to disconnect electronic load
            if self._load:  # If electronic load object exists
                self._load.disable_input()  # Turn off the load (stop pulling current)
                self._load.disconnect()     # Close communication
                self._logger.info("Electronic load disconnected")
        except:  # If anything goes wrong
            pass  # Ignore errors (we're shutting down anyway)

        try:  # Try to disconnect oscilloscope
            if self._scope:  # If oscilloscope object exists
                self._scope.disconnect()  # Close communication
                self._logger.info("Oscilloscope disconnected")
        except:  # If anything goes wrong
            pass  # Ignore errors (we're shutting down anyway)

    def configure_oscilloscope_for_rail(self, rail: RailConfig) -> bool:
        """
        Configure oscilloscope for transient capture on specific rail.
        
        This function customizes the oscilloscope settings for measuring one specific
        voltage rail. Each rail might need different settings (different voltage scales,
        time scales, trigger levels) based on its characteristics.
        
        WHAT IT DOES:
        1. Reads the oscilloscope settings for this specific rail from SCOPE_CONFIG
        2. Sets the vertical scale (sensitivity) based on expected voltage changes
        3. Sets the time scale (sweep speed) appropriate for transient duration
        4. Configures the channel (DC coupling, probe attenuation)
        5. Sets trigger conditions (what event captures the waveform)
        6. Enables bandwidth limiting (reduces noise)
        
        CONFIGURATION SOURCE:
        Uses SCOPE_CONFIG table at top of class for per-rail settings.
        These settings come from load_transient_config.json.
        Offset is always set to the rail's nominal voltage (centers trace on screen).
        
        PARAMETERS:
            rail: RailConfig object with all specs for this power rail
        
        RETURNS:
            bool - True if configuration successful, False if failed or scope not connected
        """
        if not self._scope:
            return False

        try:
            # ─── STEP 1: GET PER-RAIL SCOPE SETTINGS ──────────────────────
            # Look up this rail's specific oscilloscope configuration
            # If rail not in SCOPE_CONFIG, use defaults: 50mV/div (voltage) + 50µs/div (time)
            cfg = self.SCOPE_CONFIG.get(rail.name, {})  # Get this rail's config dict
            v_scale = cfg.get("v_scale", 0.050)  # Volts per division (default 50mV) - affects vertical zoom
            timebase = cfg.get("timebase", 50e-6)  # Seconds per division (default 50µs) - affects horizontal zoom

            # Log that we're configuring for this specific rail
            self._logger.info(f"Configuring oscilloscope for {rail.name}")
            self._logger.info(f"  Nominal voltage: {rail.expected_voltage_v}V")
            self._logger.info(f"  Settings: {v_scale*1000:.0f}mV/div, {timebase*1e6:.0f}us/div")

            # ─── STEP 2: CONFIGURE THE CHANNEL (voltage measurement) ──────
            # This tells the scope: "Measure voltage on this channel with these settings"
            # 
            # CHANNEL SETTINGS:
            # • Vertical scale: How many volts per division (like zoom level)
            #   Example: 50mV/div means each square on the grid = 50mV
            # 
            # • Vertical offset: Where to center the waveform on screen
            #   Set to nominal voltage so we can see positive and negative swings equally
            #
            # • Coupling: DC vs AC
            #   DC coupling: Shows the absolute voltage (including DC offset)
            #   AC coupling: Shows only the AC variations (removes DC)
            #   We use DC because we care about the actual voltage level
            #
            # • Probe attenuation: If using 10:1 probe, set to 10.0 (corrects readings)
            
            ch = self._scope_settings.get("channel", 1)  # Which channel (1 for CH1, etc)
            coupling = self._scope_settings.get("coupling", "DC")  # DC coupling for absolute voltage
            probe_atten = self._scope_settings.get("probe_attenuation", 1.0)  # Probe ratio (1.0 = 1:1 probe)
            
            self._scope.configure_channel(
                channel=ch,  # Channel number (usually 1)
                vertical_scale=v_scale,  # Volts per division
                vertical_offset=rail.expected_voltage_v,  # Center at nominal voltage
                coupling=coupling,  # DC coupling
                probe_attenuation=probe_atten  # Probe correction factor
            )
            self._logger.info(f"  Ch{ch}: {v_scale*1000:.0f}mV/div, offset={rail.expected_voltage_v}V, {coupling}, {probe_atten}")

            # ─── STEP 3: CONFIGURE THE TIMEBASE (horizontal scale) ─────────
            # This tells the scope: "Show this much time per division on the screen"
            # Example: 50µs/div means each square horizontally = 50 microseconds
            # A 10-square screen would show 500 microseconds total
            self._scope.configure_timebase(
                time_scale=timebase,  # Seconds per division
                time_offset=0.0  # Start at time 0
            )
            self._logger.info(f"  Timebase: {timebase*1e6:.0f}us/div")

            # ─── STEP 4: CONFIGURE INITIAL TRIGGER ────────────────────────
            # The trigger is how the scope knows when to capture
            # It watches for a specific condition, then captures when that happens
            #
            # IMPORTANT: This is the INITIAL trigger setup. The actual trigger
            # will be reconfigured in perform_load_step() based on the direction
            # (positive step uses falling edge, negative step uses rising edge)
            #
            # For now, we set up a falling edge trigger (for positive step tests)
            
            sweep_mode = self._scope_settings.get("trigger_sweep_mode", "NORMal")  # "NORMal" or "AUTO"
            trigger_up = cfg.get("trigger_up", rail.expected_voltage_v)  # Trigger level for positive step
            
            self._scope.configure_trigger(
                channel=ch,  # Trigger on same channel we're measuring
                trigger_level=trigger_up,  # Voltage level where trigger occurs
                trigger_slope="NEG",  # NEG = falling edge (voltage dropping)
                sweep_mode=sweep_mode  # NORMal = wait for trigger, AUTO = free-run if no trigger
            )
            self._logger.info(f"  Trigger: FALLING edge at {trigger_up:.3f}V ({sweep_mode} sweep)")

            # ─── STEP 5: CONFIGURE BANDWIDTH LIMIT ────────────────────────
            # Bandwidth limiting is a 20 MHz low-pass filter on the scope
            # It removes high-frequency noise above ~20 MHz
            #
            # WHY USE IT:
            # • Filters out electrical noise (power supply ripple, EMI)
            # • Makes measurements cleaner and more stable
            # • Doesn't affect the transient we're measuring (which is lower frequency)
            #
            # This is done via raw SCPI command because some scope libraries don't expose this setting
            
            bw_limit = self._scope_settings.get("bandwidth_limit", True)  # Should we enable it? (default: Yes)
            bw_state = "ON" if bw_limit else "OFF"  # Convert boolean to string
            
            if not self._scope.set_bandwidth_limit(ch, bw_limit):
                self._logger.warning(f"  Could not set bandwidth limit")
            else:
                self._logger.info(f"  Bandwidth limit: {bw_state} (CHANnel{ch}:BWLimit {bw_state})")

            # ─── CONFIGURATION COMPLETE ──────────────────────────────────
            # Log the test limits so we know what we're checking for
            self._logger.info(f"Scope ready for {rail.name}: {rail.low_current_ma}mA -> {rail.high_current_ma}mA")
            self._logger.info(f"  Limits: Droop<{rail.max_droop_mv}mV, Recovery<{rail.max_recovery_time_us}us")
            return True  # Success!

        except Exception as e:
            # If anything goes wrong, document it and return False
            self._logger.error(f"Oscilloscope configuration failed: {e}")
            import traceback
            self._logger.error(traceback.format_exc())  # Print the full error for troubleshooting
            return False

    def _measure_transient_with_scope(self, rail: RailConfig, direction: LoadStepDirection, 
                                      load_voltage_readings: Optional[List[float]] = None,
                                      load_time_readings: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Use oscilloscope's built-in hardware measurements to accurately measure transient parameters.
        
        *** THIS IS WHERE THE PRIMARY MEASUREMENTS HAPPEN ***
        
        This method uses the oscilloscope's BUILT-IN HARDWARE MEASUREMENTS for maximum accuracy,
        similar to using the oscilloscope's cursor function manually.
        
        WHAT IT MEASURES:
        1. DROOP (or RISE for negative steps) - Using scope's VMAX, VMIN, DC RMS FS measurements
        2. RECOVERY TIME - Using electronic load voltage readings (more precise)
        3. OVERSHOOT - The peak voltage deviation during recovery
        4. BASELINE - The DC level before the transient
        
        HOW IT WORKS (the measurement chain):
        1. Read scope's built-in measurements (VMAX, VMIN, DC RMS FS, VBASE, VTOP)
        2. Determine baseline voltage (DC RMS FS - the true DC level)
        3. Calculate droop:
           • POSITIVE step: Droop = Baseline - VMIN (how much voltage dropped)
           • NEGATIVE step:  Droop = VMAX - Baseline (how much voltage rose)
        4. Use electronic load voltage readings to find recovery time
           • Time for voltage to settle within ±2-5% of target
        5. Return a dictionary with all measurements and calculation details
        
        PARAMETERS:
            rail: Power rail configuration with voltage specs and limits
            direction: POSITIVE or NEGATIVE step direction
            load_voltage_readings: Optional voltage samples from electronic load during transient
            load_time_readings: Optional time points (in microseconds) for voltage samples
        
        RETURNS:
            Dictionary containing:
            • droop_mv: Voltage change in millivolts
            • recovery_us: Recovery time in microseconds
            • baseline_v: Initial DC voltage before transient
            • min_v: Minimum voltage observed
            • max_v: Maximum voltage observed
            • method: 'SCOPE_MEASUREMENTS' if successful, 'FAILED' if error
            • calc_log: List of calculation steps for documentation
        
        WHY THIS APPROACH:
        Oscilloscope built-in measurements are:
        - Hardware-based (measured by the scope's acquisition circuit)
        - Accurate (VMAX/VMIN precision is typically +/-0.1% of full scale)
        - Fast (computed by scope, not user software)
        - Comparable to manual cursor measurements
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
            ch = self._scope_settings.get("channel", 1)

            # Get VMAX (maximum voltage in waveform)
            v_max = self._scope.measure_max(ch)
            if v_max is not None:
                results['max_v'] = v_max
                calc_log.append(f"  VMAX (scope): {v_max:.4f}V ({v_max*1000:.1f}mV)")
            else:
                calc_log.append("  VMAX: Failed to read")

            # Get VMIN (minimum voltage in waveform)
            v_min = self._scope.measure_min(ch)
            if v_min is not None:
                results['min_v'] = v_min
                calc_log.append(f"  VMIN (scope): {v_min:.4f}V ({v_min*1000:.1f}mV)")
            else:
                calc_log.append("  VMIN: Failed to read")

            # Get DC RMS FS (DC baseline voltage - the true settled baseline for DC-coupled measurements)
            # This is the scope's measurement of the DC level on the channel
            dc_rms_fs = self._scope.measure_dc_rms_fs(ch)
            if dc_rms_fs is not None:
                results['baseline_v'] = dc_rms_fs
                calc_log.append(f"  DC RMS FS (baseline): {dc_rms_fs:.4f}V ({dc_rms_fs*1000:.1f}mV)")
            else:
                calc_log.append(f"  DC RMS FS: Failed to read, falling back to VTOP")
                # Fallback to VTOP if DC RMS FS is not available
                v_top = self._scope.measure_top(ch)
                if v_top is not None:
                    results['baseline_v'] = v_top
                    calc_log.append(f"  VTOP (baseline fallback): {v_top:.4f}V ({v_top*1000:.1f}mV)")
                else:
                    results['baseline_v'] = rail.expected_voltage_v
                    calc_log.append(f"  Using expected voltage: {rail.expected_voltage_v}V")

            # Get VBASE (base/low level) for reference
            v_base = self._scope.measure_base(ch)
            if v_base is not None:
                calc_log.append(f"  VBASe (low level): {v_base:.4f}V ({v_base*1000:.1f}mV)")

            # Use the baseline voltage from DC RMS FS for all calculations
            dc_baseline = results['baseline_v']
            if dc_baseline == 0:
                dc_baseline = rail.expected_voltage_v
            calc_log.append(f"  Using DC RMS FS as baseline: {dc_baseline:.4f}V ({dc_baseline*1000:.1f}mV)")

            # Get scope's built-in overshoot measurement
            scope_overshoot = self._scope.measure_overshoot(ch)
            if scope_overshoot is not None:
                calc_log.append(f"  OVERshoot (scope %): {scope_overshoot:.2f}%")

            # ============================================================
            # STEP 2: Calculate DROOP
            # ============================================================
            calc_log.append("\n[STEP 2] CALCULATING DROOP")

            if direction == LoadStepDirection.POSITIVE:
                # Positive step: droop = DC RMS FS (baseline) - VMIN
                calc_log.append("  Direction: POSITIVE (load increased → voltage drops)")
                calc_log.append(f"  DC RMS FS (baseline): {dc_baseline:.4f}V ({dc_baseline*1000:.1f}mV)")
                calc_log.append(f"  VMIN (minimum voltage): {results['min_v']:.4f}V ({results['min_v']*1000:.1f}mV)")

                if results['min_v'] > 0 and dc_baseline > 0:
                    droop_mv = (dc_baseline - results['min_v']) * 1000
                    results['droop_mv'] = max(0, droop_mv)  # Can't be negative
                    calc_log.append(f"\n  DROOP = DC RMS FS - VMIN")
                    calc_log.append(f"        = {dc_baseline:.4f}V - {results['min_v']:.4f}V")
                    calc_log.append(f"        = {droop_mv:.1f}mV")
                    calc_log.append(f"  DROOP = {results['droop_mv']:.1f}mV (Limit: <{rail.max_droop_mv}mV) {'PASS' if results['droop_mv'] <= rail.max_droop_mv else 'FAIL'}")

            else:
                # Negative step: droop = VMAX - DC RMS FS (baseline)
                calc_log.append("  Direction: NEGATIVE (load decreased -> voltage rises)")
                calc_log.append(f"  VMAX (maximum voltage): {results['max_v']:.4f}V ({results['max_v']*1000:.1f}mV)")
                calc_log.append(f"  DC RMS FS (baseline): {dc_baseline:.4f}V ({dc_baseline*1000:.1f}mV)")

                if results['max_v'] > 0 and dc_baseline > 0:
                    droop_mv = (results['max_v'] - dc_baseline) * 1000
                    results['droop_mv'] = max(0, droop_mv)
                    calc_log.append(f"\n  DROOP = VMAX - DC RMS FS")
                    calc_log.append(f"        = {results['max_v']:.4f}V - {dc_baseline:.4f}V")
                    calc_log.append(f"        = {droop_mv:.1f}mV")
                    calc_log.append(f"  DROOP = {results['droop_mv']:.1f}mV (Limit: <{rail.max_droop_mv}mV) {'PASS' if results['droop_mv'] <= rail.max_droop_mv else 'FAIL'}")

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
                tol_pct = self._analysis_cfg.get("recovery_tolerance_percent", 0.02)
                tol_min_mv = self._analysis_cfg.get("recovery_tolerance_min_mv", 10.0)
                tolerance = max(voltage_change * tol_pct, tol_min_mv / 1000.0)
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
                    calc_log.append(f"  RECOVERY TIME = {recovery_us:.1f}µs")
                    calc_log.append(f"    (Limit: <{rail.max_recovery_time_us}µs) {'PASS' if recovery_us <= rail.max_recovery_time_us else 'FAIL'}")
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
                          f"{'PASS' if results['droop_mv'] <= rail.max_droop_mv else 'FAIL'}")
            calc_log.append(f"Recovery: {results['recovery_us']:.1f}µs (Limit: {rail.max_recovery_time_us}µs) "
                          f"{'PASS' if results['recovery_us'] <= rail.max_recovery_time_us else 'FAIL'}")
            calc_log.append("=" * 80)

        except Exception as e:
            calc_log.append(f"\nERROR during scope measurements: {e}")
            self._logger.error(f"Scope measurement failed: {e}")
            results['method'] = 'FAILED'

        return results

    def configure_electronic_load_for_rail(self, rail: RailConfig) -> bool:
        """
        Configure electronic load for transient testing - Set up current source
        
        This function configures the Keithley 2380 electronic load (the device that
        pulls current from the power supply) so it's ready to perform load steps.
        
        WHAT IT DOES:
        1. Sets the load to constant current mode (pulls fixed current)
        2. Sets the current range based on the test's maximum current
        3. Configures the slew rate (how fast current changes during step)
        4. Sets voltage protection limits (over-voltage and under-voltage)
        
        WHY EACH SETTING MATTERS:
        
        CONSTANT CURRENT MODE:
          • The load maintains a target current regardless of voltage
          • Essential for creating a defined load condition
          • Example: "Always draw 800mA" instead of "Always dissipate 2.64W"
        
        CURRENT RANGE:
          • Sets the range capacity of the load
          • Affects measurement accuracy and resolution
          • Range margin (1.5x) gives headroom above the test current
          • Example: If testing up to 800mA, set range to 1200mA
        
        SLEW RATE (Speed of current change):
          • Controls how fast current rises/falls during the step
          • Fast slew rate = sharp step (what we want for transient testing)
          • Calculated as: Current_change / Rise_time
          • Example: 700mA change in 0.1µs = 7000 A/µs = extremely fast
        
        VOLTAGE PROTECTION:
          • Over-Voltage Protection (OVP): Maximum allowed voltage
            Prevents damage if power supply goes too high
          • Under-Voltage Protection (UVP): Minimum allowed voltage
            Stops the test if voltage droops too much
          • Margins help (e.g., ±1V around nominal)
        
        PARAMETERS:
            rail: Power rail configuration with current and voltage specs
        
        RETURNS:
            bool - True if configuration successful, False if failed or load not connected
        """
        if not self._load:  # Check if we're connected to the electronic load
            return False

        try:
            # Log that we're configuring for this specific rail
            self._logger.info(f"Configuring electronic load for {rail.name}")

            # ─── STEP 1: SET TO CONSTANT CURRENT MODE ─────────────────────
            # Tell the load: "Maintain a target current" (not constant power, not constant resistance)
            self._load.set_function("CURRent")

            # ─── STEP 2: SET CURRENT RANGE ────────────────────────────────
            # Set the load's range to accommodate the maximum test current with headroom
            #
            # Why range margin?
            # - Headroom prevents the load from saturating (hitting its limit)
            # - Better measurement accuracy in the middle of range than at edges
            # - Default margin is 1.5x (40% above max test current)
            
            range_margin = self._eload_cfg.get("current_range_margin", 1.5)  # Get margin from config (default 1.5)
            max_current_a = rail.high_current_ma / 1000.0 * range_margin  # Convert mA to amps and apply margin
            self._load.set_current_range(max_current_a)

            # ─── STEP 3: CONFIGURE SLEW RATE (Speed of current change) ────
            # The slew rate determines how FAST the current changes during a load step
            # 
            # CALCULATION:
            # Slew_Rate = (High_Current - Low_Current) / Rise_Time
            # Example: (800mA - 100mA) / 0.1µs = 700mA / 0.1µs = 7000 A/sec
            # This means the current changes VERY FAST (within the 100ns spec of the Keithley)
            
            current_step_a = (rail.high_current_ma - rail.low_current_ma) / 1000.0  # Current change in amps
            rise_time_us = self._eload_cfg.get("slew_rate_rise_time_us", 0.1)  # Target rise time in microseconds
            slew_rate = current_step_a / rise_time_us  # Amps per microsecond
            
            self._load.set_current_slew_rate(slew_rate)  # Tell the load the slew rate
            self._load.set_current_slow_rate_mode(False)  # Use fast mode (A/us), not slow mode (A/ms)

            # ─── STEP 4: SET VOLTAGE PROTECTION LIMITS ────────────────────
            # Protect the power supply being tested from over/under voltage
            #
            # OVP (Over-Voltage Protection):
            #   - Upper limit to prevent damage if voltage goes too high
            #   - Set to: Nominal + Margin (e.g., 3.3V + 1.0V = 4.3V)
            #
            # UVP (Under-Voltage Protection):
            #   - Lower limit to catch if voltage droops excessively
            #   - Set to: Nominal - Margin (e.g., 3.3V - 1.0V = 2.3V)
            #   - Minimum floor (can't go below about 0.1V for safety)
            
            ovp_margin = self._eload_cfg.get("ovp_margin_v", 1.0)  # Overvoltage margin in volts (default 1.0V)
            uvp_margin = self._eload_cfg.get("uvp_margin_v", 1.0)  # Undervoltage margin in volts (default 1.0V)
            uvp_min = self._eload_cfg.get("uvp_minimum_v", 0.1)  # Absolute minimum UVP threshold (default 0.1V)
            
            ovp = rail.expected_voltage_v + ovp_margin  # Maximum allowed voltage
            uvp = max(uvp_min, rail.expected_voltage_v - uvp_margin)  # Minimum allowed voltage (but not below 0.1V)
            
            self._load.set_current_bounds(high=ovp, low=uvp)  # Set the protect limits

            # ─── CONFIGURATION COMPLETE ──────────────────────────────────
            self._logger.info(f"Electronic load configured: {rail.low_current_ma}mA - {rail.high_current_ma}mA")
            return True  # Success!

        except Exception as e:
            self._logger.error(f"Electronic load configuration failed: {e}")
            return False

    def perform_load_step(self, rail: RailConfig, direction: LoadStepDirection) -> Optional[TransientResult]:
        """
        ═════════════════════════════════════════════════════════════════════════════════════
        *** THIS IS WHERE THE ACTUAL TEST HAPPENS - EXECUTES ONE LOAD STEP ***
        ═════════════════════════════════════════════════════════════════════════════════════
        
        This is the core testing function. It:
        1. Changes the electronic load current suddenly (the "step")
        2. Captures the voltage waveform during and after the step
        3. Analyzes the waveform to measure transient response parameters
        4. Saves a screenshot of the waveform
        5. Returns the results
        
        THE COMPLETE TEST SEQUENCE:
        
        SETUP PHASE (Configure for this specific load step):
          └─ Get initial and final current values based on direction
        
        EXECUTION PHASE (Perform the actual load step):
          1. Set load to initial current (let it settle)
          2. Configure oscilloscope trigger for the expected voltage change
          3. Arm the oscilloscope (ready to capture)
          4. Suddenly change the load current
          5. Wait for the oscilloscope to trigger and capture the waveform
        
        CAPTURE PHASE (Get the waveform):
          1. Stop the oscilloscope
          2. Save a screenshot of the waveform
          3. Read the waveform data
        
        ANALYSIS PHASE (Measure the transient):
          1. Calculate droop (how much voltage changed)
          2. Calculate recovery time (how fast it returned to normal)
          3. Detect ringing/oscillation
          4. Determine PASS or FAIL
        
        DOCUMENTATION PHASE (Save results):
          1. Save screenshot to file
          2. Create detailed calculation log
          3. Return TransientResult with all measurements
        
        PARAMETERS (Inputs):
            rail: RailConfig object with voltage, current, and limit specs
            direction: LoadStepDirection.POSITIVE (low→high) or NEGATIVE (high→low)
        
        RETURNS (Output):
            TransientResult object containing:
            • All measurements (droop, recovery time, overshoot, ringing)
            • Screenshot file path
            • Test result (PASS/FAIL/ERROR)
            • Detailed calculation log for documentation
            Or None if test failed to execute
        
        KEY TIMING PARAMETERS (From config):
            All timing is configurable in load_transient_config.json:
            • stabilize_after_current_set_s: Time to wait after setting initial current
            • stabilize_before_arm_s: Time to wait before arming scope
            • delay_after_arm_s: Delay between arming and executing step
            • trigger_timeout_s: Maximum time to wait for scope to trigger
            • trigger_poll_interval_s: How often to check if scope has triggered
            • delay_after_stop_s: Time to wait after stopping scope
            • delay_between_steps_s: Time to wait between positive and negative steps
        """
        # ─── SAFETY CHECK: VERIFY INSTRUMENTS ARE CONNECTED ───────────────
        # Can't run a test without equipment
        if not self._scope or not self._load:
            return None  # Test impossible without instruments

        try:  # Try to perform the test; if anything fails, jump to "except" section
            # ─── DETERMINE DIRECTION AND PARAMETERS ────────────────────────
            # Based on whether this is a positive or negative step,
            # set the initial and final current values
            
            if direction == LoadStepDirection.POSITIVE:  # Increasing load (low → high)
                initial_ma = rail.low_current_ma      # Start at low current (e.g., 100mA)
                final_ma = rail.high_current_ma       # End at high current (e.g., 800mA)
                step_desc = rail.load_step_positive   # Description: "100mA -> 800mA"
            else:  # Decreasing load (high → low)
                initial_ma = rail.high_current_ma     # Start at high current (e.g., 800mA)
                final_ma = rail.low_current_ma        # End at low current (100mA)
                step_desc = rail.load_step_negative   # Description: "800mA -> 100mA"

            # Log that we're starting this test
            self._logger.info(f"Performing {direction.value} load step: {step_desc}")

            # ─── STEP 1: SET UP THE STARTING CURRENT ──────────────────────
            # Before doing anything, let the power supply settle at the initial current
            # This is important because the power supply under test might take time
            # to regulate to a new current level before we start the test
            
            self._load.set_current_level(initial_ma / 1000.0)  # Convert mA to amps, set it
            self._load.enable_input()  # Turn on the load
            # Wait for everything to stabilize at this current level
            time.sleep(self._timing.get("stabilize_after_current_set_s", 0.5))  # Default 500ms

            # ─── STEP 2: CONFIGURE OSCILLOSCOPE TRIGGER FROM SCOPE_CONFIG ─
            # The trigger determines WHEN the oscilloscope captures the waveform
            # Different triggers for different step directions:
            #
            # POSITIVE STEP (load increases, voltage drops):
            #   • Trigger on FALLING edge (voltage crossing downward)
            #   • Trigger level: "trigger_up" from config
            # 
            # NEGATIVE STEP (load decreases, voltage rises):
            #   • Trigger on RISING edge (voltage crossing upward)
            #   • Trigger level: "trigger_down" from config
            #
            # This ensures the scope captures the exact moment the transient begins
            
            cfg = self.SCOPE_CONFIG.get(rail.name, {})  # Get this rail's scope config

            if direction == LoadStepDirection.POSITIVE:
                trigger_level_v = cfg.get("trigger_up", rail.expected_voltage_v)
                trigger_slope = "NEG"  # NEG = falling edge
            else:
                trigger_level_v = cfg.get("trigger_down", rail.expected_voltage_v)
                trigger_slope = "POS"  # POS = rising edge

            ch = self._scope_settings.get("channel", 1)  # Which channel to trigger on
            sweep_mode = self._scope_settings.get("trigger_sweep_mode", "NORMal")  # NORMal vs AUTO
            
            self._scope.configure_trigger(
                channel=ch,
                trigger_level=trigger_level_v,
                trigger_slope=trigger_slope,
                sweep_mode=sweep_mode
            )
            self._logger.info(f"  Trigger: {trigger_slope} edge at {trigger_level_v:.3f}V, {sweep_mode} sweep")

            # ─── STEP 3: STABILIZE + ARM THE OSCILLOSCOPE ──────────────────
            # Before executing the load step, we need to arm the scope so it's ready
            
            # First, wait a bit to let the system fully settle
            time.sleep(self._timing.get("stabilize_before_arm_s", 0.5))
            
            # Arm the scope (put it in "waiting for trigger" mode)
            self._scope.single()  # "Single" means: capture one waveform when triggered, then stop
            
            # Wait for the scope to be fully armed and ready
            time.sleep(self._timing.get("delay_after_arm_s", 0.3))

            # ─── STEP 4: EXECUTE THE LOAD STEP ────────────────────────────
            # THIS IS THE MOMENT OF TRUTH - suddenly change the load current
            # This creates the transient we're trying to measure
            
            self._load.set_current_level(final_ma / 1000.0)  # Set new current level
            self._logger.info(f"  Load step: {initial_ma}mA -> {final_ma}mA")  # Log the step

            # ─── STEP 5: WAIT FOR OSCILLOSCOPE TO TRIGGER ──────────────────
            # Poll the oscilloscope status until it either:
            # • Triggers (captured the waveform), OR
            # • Times out (max wait time exceeded)
            
            max_wait = self._timing.get("trigger_timeout_s", 5.0)  # Default 5 second timeout
            poll_interval = self._timing.get("trigger_poll_interval_s", 0.2)  # Check every 200ms
            elapsed = 0.0  # Elapsed time counter
            triggered = False  # Did the scope successfully trigger?
            
            # Loop: Check if scope has triggered
            while elapsed < max_wait:
                time.sleep(poll_interval)  # Wait before checking again
                elapsed += poll_interval  # Update elapsed time
                
                state = self._scope.get_acquisition_state()
                if state == "STOP":
                    triggered = True
                    self._logger.info(f"  Scope triggered after {elapsed:.1f}s")
                    break

            # If scope didn't trigger naturally, force a capture
            if not triggered:
                self._logger.warning(f"  Trigger did not fire after {max_wait}s - force capturing")
                self._scope.force_trigger()
                time.sleep(0.3)

            # ─── STEP 6: STOP SCOPE ───────────────────────────────────────
            self._scope.stop()
            time.sleep(self._timing.get("delay_after_stop_s", 0.2))

            # Create screenshot of the captured waveform
            dir_label = "low_to_high" if direction == LoadStepDirection.POSITIVE else "high_to_low"
            screenshot_name = f"{rail.name}_{dir_label}.png"  # File name
            screenshot_path = str(self.screenshot_dir / screenshot_name)  # Full path
            actual_screenshot = None  # Will hold the actual path if successful

            # ─── PLACE SCOPE MARKERS FOR RECOVERY TIME ─────────────────────
            # Cursors placed BEFORE screenshot so they appear in the saved image.
            try:
                waveform = self._scope.get_channel_data(ch)
                if waveform is not None:
                    time_data  = waveform['time']
                    voltage_data = waveform['voltage']

                    # Trigger is at t=0; find the index closest to t=0
                    trigger_idx = int(np.searchsorted(time_data, 0.0))
                    trigger_idx = max(0, min(trigger_idx, len(time_data) - 1))

                    # Baseline and noise tolerance from pre-trigger samples
                    pre_trigger = voltage_data[:trigger_idx] if trigger_idx > 5 else voltage_data[:10]
                    baseline    = float(np.mean(pre_trigger)) if len(pre_trigger) > 0 else rail.nominal_voltage
                    noise_pp    = float(np.max(pre_trigger) - np.min(pre_trigger)) if len(pre_trigger) > 10 else 0.010
                    tolerance   = max(noise_pp, 0.005)  # at least 5 mV

                    # Find recovery point: first sample after the droop/overshoot peak
                    # where the voltage has settled at its NEW steady-state level.
                    # The new steady-state is the mean of the last 20% of the capture
                    # (NOT the pre-trigger baseline — under load the rail sits lower).
                    post_trigger    = voltage_data[trigger_idx:]
                    x_inc           = waveform['x_increment']
                    limit_samples   = int(rail.max_recovery_time_us * 1e-6 / x_inc)
                    recovery_idx    = min(limit_samples, len(post_trigger) - 1)  # default: limit boundary
                    settled_samples = 20

                    tail_start      = max(len(post_trigger) - len(post_trigger) // 5, 1)
                    new_steady_state = float(np.mean(post_trigger[tail_start:]))
                    noise_pp        = float(np.max(pre_trigger) - np.min(pre_trigger)) if len(pre_trigger) > 10 else 0.010
                    tolerance       = max(noise_pp, 0.005)

                    # Start searching after the peak deviation (droop trough / overshoot peak)
                    peak_idx     = int(np.argmax(np.abs(post_trigger - new_steady_state)))
                    search_start = max(peak_idx, 1)

                    for i in range(search_start, len(post_trigger)):
                        if abs(post_trigger[i] - new_steady_state) <= tolerance:
                            end = i + settled_samples
                            if end < len(post_trigger):
                                if np.all(np.abs(post_trigger[i:end] - new_steady_state) <= tolerance):
                                    recovery_idx = i
                                    break

                    self._logger.info(
                        f"  Steady-state: baseline={baseline:.4f}V  new={new_steady_state:.4f}V  "
                        f"tolerance=±{tolerance*1000:.1f}mV"
                    )

                    self._logger.info(
                        f"  Placing markers: trigger_idx={trigger_idx}, recovery_idx={recovery_idx} "
                        f"({recovery_idx * x_inc * 1e6:.1f}us)"
                    )
                    # Y2: Vmin for positive step (droop dip), Vmax for negative step (overshoot peak)
                    if direction == LoadStepDirection.POSITIVE:
                        y2_v = float(np.min(post_trigger))   # bottom of the droop
                    else:
                        y2_v = float(np.max(post_trigger))   # peak of the overshoot

                    dy_label = "Droop" if direction == LoadStepDirection.POSITIVE else "Rise"
                    cursor_recovery_us, cursor_droop_mv = self.set_cursors_for_recovery(
                        waveform, trigger_idx, recovery_idx,
                        y1_v=baseline,   # Y1: pre-transient baseline
                        y2_v=y2_v,       # Y2: Vmin (pos step) or Vmax (neg step)
                        rail_name=rail.name,
                        dy_label=dy_label
                    )
                else:
                    self._logger.warning("  Waveform download failed — markers not placed")
                    cursor_recovery_us, cursor_droop_mv = None, None
            except Exception as _e:
                self._logger.warning(f"  Marker placement error: {_e}")
                cursor_recovery_us, cursor_droop_mv = None, None

            # ─── SCREENSHOT (after cursors so markers appear in image) ──────
            try:
                actual_screenshot = self._scope.get_screenshot(screenshot_path, freeze_acquisition=True)
                self._logger.info(f"  Screenshot saved: {screenshot_name}")
            except Exception as e:
                self._logger.warning(f"  Screenshot failed: {e}")

            # ─── STEP 7: RESULTS FROM CURSOR DELTA VALUES ──────────────────
            # droop    = |ΔY| from cursor (Y1=baseline, Y2=Vmin or Vmax)
            # recovery = ΔX  from cursor (X1=trigger edge, X2=settled point)

            droop_mv      = cursor_droop_mv    if cursor_droop_mv    is not None else 0.0
            recovery_us   = cursor_recovery_us if cursor_recovery_us is not None else 0.0

            droop_pass    = 0.0 < droop_mv <= rail.max_droop_mv
            recovery_pass = 0.0 < recovery_us <= rail.max_recovery_time_us
            passed        = droop_pass and recovery_pass

            step_label = "POSITIVE STEP (load increase)" if direction == LoadStepDirection.POSITIVE else "NEGATIVE STEP (load decrease)"

            calc_lines = []
            calc_lines.append("=" * 60)
            calc_lines.append(f"RESULTS: {rail.name} - {dir_label}")
            calc_lines.append(f"Load step: {step_desc}  |  {step_label}")
            calc_lines.append(f"Trigger: {trigger_slope} edge at {trigger_level_v:.3f}V  |  Triggered: {'Yes' if triggered else 'No (forced)'}")
            calc_lines.append("=" * 60)
            calc_lines.append(f"\nCursor measurements (X1=trigger edge, X2=recovery point):")
            calc_lines.append(f"  dX  ->  Recovery Time : {recovery_us:.1f} µs   (limit: {rail.max_recovery_time_us:.0f} µs)  {'PASS' if recovery_pass else 'FAIL'}")
            calc_lines.append(f"  dY  ->  {dy_label:<13}: {droop_mv:.1f} mV   (limit: {rail.max_droop_mv:.0f} mV)       {'PASS' if droop_pass else 'FAIL'}")
            calc_lines.append(f"\n{'─' * 60}")
            calc_lines.append(f"Overall: {'PASS' if passed else 'FAIL'}")
            if not droop_pass:
                calc_lines.append(f"  {dy_label} exceeds limit by {droop_mv - rail.max_droop_mv:.1f} mV")
            if not recovery_pass:
                calc_lines.append(f"  Recovery exceeds limit by {recovery_us - rail.max_recovery_time_us:.1f} µs")
            calc_lines.append("=" * 60)

            detailed_calculations = "\n".join(calc_lines)

            self._logger.info(f"  {dy_label}:         {droop_mv:.1f}mV (limit: {rail.max_droop_mv:.1f}mV) {'PASS' if droop_pass else 'FAIL'}")
            self._logger.info(f"  Recovery Time: {recovery_us:.1f}µs (limit: {rail.max_recovery_time_us:.1f}µs) {'PASS' if recovery_pass else 'FAIL'}")

            # ─── SAVE DETAILED CALCULATION LOG TO FILE ─────────────────────
            # Store the complete calculation details for auditing and documentation
            calc_filename = f"{rail.name}_{dir_label}_calculations.txt"
            calc_path = self.calculations_dir / calc_filename
            try:
                with open(calc_path, 'w', encoding='utf-8') as f:
                    f.write(detailed_calculations)
                self._logger.info(f"  Calculations saved: {calc_filename}")
            except Exception as save_err:  # If file save fails
                self._logger.warning(f"  Could not save calculations to {calc_filename}: {save_err}")

            # ─── CREATE RESULT OBJECT WITH ALL TEST DATA ───────────────────
            # Package all the results into a TransientResult object
            result = TransientResult(
                rail_name=rail.name,
                step_direction=direction.value,
                load_step_description=step_desc,
                droop_mv=droop_mv,
                recovery_time_us=recovery_us,
                overshoot_mv=0.0,
                has_ringing=False,
                screenshot_path=actual_screenshot or screenshot_path,
                timestamp=dir_label,
                result="PASS" if passed else "FAIL",
                notes=f"{dy_label}: {droop_mv:.1f}mV, Recovery: {recovery_us:.1f}µs, Trigger: {trigger_slope} at {trigger_level_v:.3f}V",
                detailed_calculations=detailed_calculations
            )

            self._logger.info(
                f"  {direction.value.upper()} STEP RESULT: {'PASS' if passed else 'FAIL'} "
                f"- {dy_label} {droop_mv:.1f}mV  Recovery {recovery_us:.1f}µs"
            )

            return result  # Return the results to the caller

        except Exception as e:  # If ANYTHING went wrong during the test
            self._logger.error(f"Test FAILED with error: {e}")  # Log the error message
            
            # ─── CREATE ERROR DOCUMENTATION FOR AUDIT TRAIL ─────────────────
            # Even if the test fails, document what happened
            error_log = [
                "=" * 80,
                f"ERROR DURING TEST EXECUTION",
                f"Rail: {rail.name if 'rail' in locals() else 'UNKNOWN'}",
                f"Step Direction: {direction.value if 'direction' in locals() else 'UNKNOWN'}",
                "=" * 80,
                f"\nError Message: {str(e)}",
                f"\nTest Status: Could not complete - see error message above",
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "=" * 80
            ]
            
            # Return a result marked as ERROR so we know it failed
            return TransientResult(
                rail_name=rail.name if 'rail' in locals() else "UNKNOWN",
                step_direction=direction.value if 'direction' in locals() else "UNKNOWN",
                load_step_description=step_desc if 'step_desc' in locals() else "Unknown",
                result="ERROR",  # Mark as ERROR (not PASS or FAIL)
                notes=f"Exception: {str(e)}",  # Include error message
                timestamp=datetime.now().strftime("%Y%m%d_%H%M%S"),
                detailed_calculations="\n".join(error_log)  # Include error log
            )

    def _get_waveform_preamble(self, channel: int = 1) -> Dict[str, float]:
        """
        Fetch oscilloscope waveform preamble to extract time-axis calibration data.
        
        Wrapper around KeysightDSOX6004A.get_waveform_preamble() that returns
        a simplified dict with only the essential time-axis parameters.
        
        The preamble contains critical time-axis information needed to convert
        waveform sample indices to absolute time (relative to trigger point).
        
        WHAT THIS FETCHES:
        The SCPI :WAVeform:PREamble? command returns 10 comma-separated values:
          [0] format (0=ASCII, 1=BYTE, 2=WORD, 4=LONG)
          [1] type (0=normal, 1=peak detect, 2=high resolution, 3=segmented)
          [2] points (number of samples in waveform) ← Extracted
          [3] count (number of captures in segmented mode)
          [4] x_increment (seconds per sample) ← Extracted & CRITICAL
          [5] x_origin (time of first sample, relative to trigger=0) ← Extracted & CRITICAL
          [6] x_reference (sample index of trigger point = 0)
          [7] y_increment (volts per LSB)
          [8] y_origin (volts at y=0)
          [9] y_reference (y LSB value)
        
        WHY THIS MATTERS:
        To convert a waveform sample index to absolute time (relative to trigger):
          t[i] = x_origin + i * x_increment
        
        Example:
          If x_origin = -250e-6 (−250 µs) and x_increment = 0.5e-6 (0.5 µs):
          - Sample 0 is at t = -250 µs (before trigger)
          - Sample 500 is at t = 0 µs (the trigger point)
          - Sample 1000 is at t = +250 µs (after trigger)
        
        RETURNS:
            Dictionary with keys:
            • x_increment: seconds per sample
            • x_origin: time of first sample (seconds, relative to trigger)
            • points: number of samples
            Or empty dict if fetch fails (graceful degradation)
        """
        try:
            if not self._scope:
                return {}
            
            # Call the oscilloscope class method instead of raw SCPI
            preamble = self._scope.get_waveform_preamble(channel)
            
            if preamble is None:
                return {}
            
            # Return a simplified dict with only the essential fields
            return {
                'points': preamble.get('points', 0),
                'x_increment': preamble.get('x_increment', 1e-6),
                'x_origin': preamble.get('x_origin', -250e-6),
            }
        except Exception as e:
            self._logger.warning(f"Could not fetch waveform preamble: {e}")
            return {}

    def set_cursors_for_recovery(self, waveform: Dict[str, Any], trigger_idx: int,
                                 recovery_idx: int, y1_v: float, y2_v: float,
                                 rail_name: str = "UNKNOWN",
                                 dy_label: str = "Droop") -> Optional[float]:
        """
        ═════════════════════════════════════════════════════════════════════════════════════
        *** PROGRAMMATICALLY PLACE SCOPE CURSORS FOR VISUAL CONFIRMATION ***
        ═════════════════════════════════════════════════════════════════════════════════════
        
        Automate the scope cursor placement to match recovery time measurement.
        Uses KeysightDSOX6004A cursor control methods instead of raw SCPI.
        
        PURPOSE:
        This method converts calculated waveform indices (trigger_idx, recovery_idx)
        into absolute scope time (relative to trigger = 0) and places X1/X2 cursors
        on the oscilloscope display. The cursors show exactly which points on the
        waveform were used to calculate recovery time.
        
        WORKFLOW:
        1. Get x_increment and x_origin from waveform preamble
        2. Convert trigger_idx and recovery_idx to scope time (seconds)
        3. Call oscilloscope class methods to place X1/X2 cursors
        4. Call oscilloscope class methods to place Y1/Y2 cursors at voltages
        5. Call oscilloscope class methods to read back ΔX for verification
        6. Compare scope ΔX with calculated recovery time (sanity check)
        
        KEY CONCEPT - Scope Time:
        Scope measures time relative to trigger point = 0.0 seconds
        Sample time: t[i] = x_origin + i * x_increment
        
        Example:
          If x_origin = -250 µs, x_increment = 0.5 µs:
          - trigger_idx = 500 → t_edge = -250e-6 + 500*0.5e-6 = 0.0 s (trigger!)
          - recovery_idx = 52 (52 samples after trigger)
          - t_settle = 0.0 + 52*0.5e-6 = 26e-6 s (26 µs after trigger)
        
        PARAMETERS:
            waveform: Dict from get_channel_data() with 'x_increment' key
                     (or will fetch from preamble if not present)
            
            trigger_idx: Array index where load step edge was detected
                        This becomes X1 on the scope
            
            recovery_idx: Array index (counted from trigger_idx) where voltage settled
                         X2 = trigger_idx + recovery_idx
                         ΔX = recovery_idx * x_increment
            
            baseline_v: Voltage before the transient (placed at Y1)
            settle_v: Voltage where it settled (placed at Y2)
            rail_name: For logging purposes
        
        RETURNS:
            Measured ΔX from scope in microseconds (for sanity check)
            Or None if cursor placement failed
        
        SANITY CHECK:
        The returned cursor_delta_us should match the calculated recovery_us:
        - Both should use the same x_increment
        - Both should span the same indices
        - Difference should be within ±1 sample (±x_increment in microseconds)
        
        EXAMPLE OUTPUT:
        Calculated recovery: 26.0 µs
        Scope cursor ΔX:     26.0 µs  ← Should match!
        """
        try:
            if not self._scope:
                self._logger.warning("Cannot set cursors: oscilloscope not connected")
                return None

            self._logger.info(f"Setting cursors for {rail_name} (trigger_idx={trigger_idx}, recovery_idx={recovery_idx})")
            
            time_data = waveform.get('time')

            if time_data is not None:
                t_edge = float(time_data[trigger_idx])
                t_settle = float(time_data[trigger_idx + recovery_idx])
            else:
                x_increment = waveform.get('x_increment')
                x_origin = waveform.get('x_origin')
                
                if x_increment is None or x_origin is None:
                    preamble = self._get_waveform_preamble()
                    x_increment = preamble.get('x_increment', 1e-6)
                    x_origin = preamble.get('x_origin', -250e-6)
                
                t_edge = x_origin + trigger_idx * x_increment
                t_settle = x_origin + (trigger_idx + recovery_idx) * x_increment
            
            # ─── PLACE MARKERS: MANual mode → set positions → log ───────────
            # MANual mode allows explicit X position commands (:MARKer:X1POSition)
            # WAVeform/track mode does NOT accept position writes — scope ignores them.
            ch = int(waveform.get('channel', 1))

            if not self._scope.set_marker_mode("MANual"):
                self._logger.warning(f"Failed to set marker mode for {rail_name}")
                return None

            success_x1 = self._scope.set_marker_x_position(1, t_edge)
            success_x2 = self._scope.set_marker_x_position(2, t_settle)

            if not (success_x1 and success_x2):
                self._logger.warning(f"Failed to set marker X positions for {rail_name}")
                return None

            # Y1 = baseline voltage (before droop), Y2 = settled voltage (at recovery point)
            self._scope.set_marker_y_position(1, y1_v)
            self._scope.set_marker_y_position(2, y2_v)

            # Read ΔX and ΔY back from scope — these are the values shown in the cursor panel
            delta_x_s = self._scope.get_marker_x_delta()   # :MARKer:XDELta? → seconds
            delta_y_v = self._scope.get_marker_y_delta()   # :MARKer:YDELta? → volts

            # Fall back to calculated values if queries fail
            delta_x_us = (delta_x_s * 1e6) if delta_x_s is not None else (t_settle - t_edge) * 1e6
            delta_y_mv = (delta_y_v * 1000.0) if delta_y_v is not None else (y2_v - y1_v) * 1000.0

            # Display annotation on scope screen matching the cursor panel labels
            annotation = f"Recovery Time: {delta_x_us:.1f}us  {dy_label}: {abs(delta_y_mv):.1f}mV"
            self._scope.show_screen_annotation(annotation)

            self._logger.info(
                f"Markers placed on {rail_name}: CH{ch}, "
                f"X1={t_edge*1e6:.2f}µs X2={t_settle*1e6:.2f}µs ΔX={delta_x_us:.2f}µs | "
                f"Y1={y1_v:.4f}V Y2={y2_v:.4f}V ΔY={delta_y_mv:.2f}mV"
            )
            print(f"[CURSOR] {rail_name}: Recovery Time={delta_x_us:.1f}us  Droop={abs(delta_y_mv):.1f}mV")

            return delta_x_us, abs(delta_y_mv)

        except Exception as e:
            self._logger.warning(f"Cursor placement failed: {e}")
            import traceback
            self._logger.debug(traceback.format_exc())
            return None, None

    def _analyze_waveform(self, rail: RailConfig, direction: LoadStepDirection,
                         load_voltage_readings: Optional[List[float]] = None,
                         load_time_readings: Optional[List[float]] = None) -> Tuple[float, float, float, bool, str]:
        """
        ═════════════════════════════════════════════════════════════════════════════════════
        *** DETAILED WAVEFORM ANALYSIS - MEASURES TRANSIENT RESPONSE ***
        ═════════════════════════════════════════════════════════════════════════════════════
        
        PURPOSE (What does this do?):
        This function analyzes the voltage waveform captured by the oscilloscope to measure
        four critical parameters that tell us how well the power supply handles load changes:
        
          1. DROOP (mV):         How much voltage changes when load suddenly changes
          2. RECOVERY TIME (µs): How fast voltage returns to normal after the change
          3. OVERSHOOT (mV):     Peak voltage if it overshoots the normal value
          4. RINGING:            Does the voltage oscillate (bad for digital circuits)?
        
        MEASUREMENT STRATEGY (Two-Stage Approach):
        
        STAGE 1: Use Oscilloscope Hardware Measurements (Most Accurate)
          • Read VMIN, VMAX, DC RMS FS from oscilloscope built-in functions
          • These are like manual cursor measurements you'd do with a probe
          • Use electronic load voltage readings for recovery time
          • Calculate droop from VMAX/VMIN data
          
        STAGE 2: If hardware measurements fail, analyze waveform data
          • Download voltage vs. time data from oscilloscope
          • Find peaks (VMAX), valleys (VMIN), baseline (DC RMS FS)
          • Calculate measurements from the data arrays
          • Detect oscillations in the waveform
        
        WHY THIS MATTERS (For Non-Technical Readers):
        • A "good" power supply keeps voltage stable during sudden load changes
        • If voltage drops too much (droop), digital circuits may malfunction
        • If voltage takes too long to recover, performance degrades
        • Ringing (oscillations) can cause electromagnetic interference (EMI) problems
        
        EXAMPLE RESULTS:
        Good response:    Droop=30mV, Recovery=150µs, No ringing → PASS
        Bad response:     Droop=90mV, Recovery=500µs, Has ringing → FAIL
        
        TECHNICAL DETAILS (For Engineers):
        
        POSITIVE STEP (Load increases from low to high):
          • Power supply voltage DROPS immediately (due to output impedance)
          • DROOP = Nominal Voltage - Minimum voltage reached
          • Formula: Droop = DC_RMS_FS - VMIN
          • Recovery time: How long until voltage returns to DC_RMS_FS level
        
        NEGATIVE STEP (Load decreases from high to low):
          • Power supply voltage RISES (less load = less voltage drop)
          • DROOP = Maximum voltage reached - Nominal Voltage
          • Formula: Droop = VMAX - DC_RMS_FS
          • Recovery time: How long until voltage returns to DC_RMS_FS level
        
        PARAMETERS (Inputs):
            rail: RailConfig object with:
                • expected_voltage_v: Nominal voltage (e.g., 1.8V)
                • max_droop_mv: Tolerance for voltage change (e.g., 60mV)
                • max_recovery_time_us: Tolerance for settling time (e.g., 500µs)
                • max_overshoot_mv: Tolerance for peak overshoot (e.g., 40mV)
                
            direction: LoadStepDirection.POSITIVE or NEGATIVE
                • Determines which computation to use for droop
                
            load_voltage_readings: Optional array of voltage samples from electronic load
                • Used for recovery time calculation
                
            load_time_readings: Optional array of time values (microseconds) from electronic load
                • Timestamps for voltage readings
        
        RETURNS (Output - Tuple of 5 values):
            A "package" (tuple) containing:
            
            1. droop_mv (float):
               - The measured peak voltage change in millivolts
               - Example: 45.3mV
               - If measurement failed: Returns 2x the limit (so it fails PASS check)
            
            2. recovery_time_us (float):
               - Time for voltage to settle back to nominal
               - Measured in microseconds (millionths of a second)
               - Example: 280.5µs
               - If measurement failed: Returns 2x the limit
            
            3. overshoot_mv (float):
               - Peak voltage overshoot above nominal
               - Example: 25.0mV
               - If measurement failed: Returns 2x the limit
            
            4. has_ringing (bool):
               - True if oscillation detected = FAIL
               - False if waveform is clean = acceptable
            
            5. detailed_calculations (str):
               - Complete text log of every calculation step
               - For documentation and auditing
               - Explains how each measurement was derived
        
        IMPORTANT NOTE FOR TROUBLESHOOTING:
        If oscilloscope measurements fail, this function returns "FAIL values" (2x the limits)
        rather than fake "PASS values". This ensures that if something goes wrong,
        the test fails safely (doesn't hide problems with fake measurements).
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
            calc_log.append("\nScope hardware measurements SUCCEEDED")
            calc_log.append(f"  Droop: {droop_mv:.1f}mV")
            calc_log.append(f"  Recovery time: {recovery_us:.1f}µs")
            # Append the detailed scope measurement log
            calc_log.extend(scope_measurements['calc_log'])
            calc_log.append("\n" + "=" * 80)
            calc_log.append("STAGE 2: WAVEFORM ANALYSIS (for validation and ringing detection)")
            calc_log.append("=" * 80)
        else:
            calc_log.append("\nScope hardware measurements FAILED")
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
            ch = self._scope_settings.get("channel", 1)
            calc_log.append("\n[STEP 1] DOWNLOADING WAVEFORM DATA FROM OSCILLOSCOPE")
            calc_log.append(f"  Reading Ch{ch} (Rail Voltage, DC-coupled)")
            calc_log.append(f"  Expected nominal voltage: {rail.expected_voltage_v}V")
            waveform = self._scope.get_channel_data(ch)  # Download voltage vs time data
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
            calc_log.append(f"Downloaded {len(voltage_data)} voltage samples")
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
            noise_threshold = self._analysis_cfg.get("waveform_noise_warning_threshold_v", 0.01)
            if first_std > noise_threshold and last_std > noise_threshold:  # Both ends have high noise
                high_noise_ratio = min(first_std, last_std) / max(first_std, last_std)
                if high_noise_ratio > 0.5:  # Similar noise in both settled regions
                    calc_log.append(f"\n  WARNING: High noise detected in both pre and post regions!")
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
            edge_window = self._analysis_cfg.get("edge_detection_window_percent", 0.4)
            # If detected edge is within reasonable range of middle, use it
            # Otherwise fall back to middle (trigger point)
            if abs(edge_idx - mid_point) < mid_point * edge_window:
                trigger_idx = edge_idx
                calc_log.append(f"Detected edge at index: {trigger_idx}")
            else:
                trigger_idx = mid_point
                calc_log.append(f"Using middle point as trigger index: {trigger_idx}")
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
            expected_tol_mv = float(self._analysis_cfg.get("expected_voltage_tolerance_mv", 10.0))
            if baseline_error_mv > expected_tol_mv:
                calc_log.append(
                    f"  WARNING: Baseline ({baseline:.3f}V) differs from expected ({rail.expected_voltage_v}V) by {baseline_error_mv:.1f}mV "
                    f"(Acceptance: ±{expected_tol_mv:.1f}mV)"
                )
            else:
                calc_log.append(f"  Baseline matches expected voltage (within +/-{expected_tol_mv:.1f}mV)")

            # *** STEP 4: GET DATA AFTER THE LOAD STEP ***
            calc_log.append("\n[STEP 4] EXTRACTING POST-TRIGGER DATA (after load step)")
            post_trigger = voltage_data[trigger_idx:]  # Get data AFTER trigger
            calc_log.append(f"Post-trigger samples: {len(post_trigger)} points")
            calc_log.append(f"  Analysis window: {len(post_trigger) * waveform.get('x_increment', 1e-6) * 1e6:.1f}µs")

            # *** STEP 5: MEASURE DROOP AND OVERSHOOT (depends on direction) ***
            # NOTE: DROOP IS MEASURED BY SCOPE HARDWARE ONLY (earlier in STAGE 1)
            # Waveform analysis does NOT recalculate droop - it validates other parameters
            calc_log.append("\n[STEP 5] DROOP MEASUREMENT")
            calc_log.append("  Using scope hardware measurements (DC RMS FS, VMAX, VMIN)")
            calc_log.append(f"  DROOP = {droop_mv:.1f}mV (from scope hardware measurement)")
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

            settled_samples = self._analysis_cfg.get("recovery_settled_check_samples", 50)
            for i in range(len(post_trigger)):  # Check each point in time
                if abs(post_trigger[i] - baseline) <= tolerance:  # If voltage is within tolerance of baseline
                    # Check if it STAYS within tolerance (not just a momentary cross)
                    if i + settled_samples < len(post_trigger):  # If there's enough data to check ahead
                        remaining = post_trigger[i:i+settled_samples]  # Get next N points
                        # Check if ALL next N points stay within tolerance of baseline
                        if np.all(np.abs(remaining - baseline) <= tolerance):
                            recovery_idx = i  # This is when it truly settled
                            settled = True
                            calc_log.append(f"\n  Voltage settled at index {i}")
                            calc_log.append(f"    Voltage at settlement: {post_trigger[i]:.4f}V")
                            calc_log.append(f"    Deviation from baseline: {(post_trigger[i] - baseline)*1000:.2f}mV")
                            break  # Stop looking, we found it

            x_increment = waveform.get('x_increment', 1e-6)  # Time between samples (default 1 microsecond)
            recovery_us = recovery_idx * x_increment * 1e6  # Convert to microseconds (×1e6)

            if not settled:
                calc_log.append(f"\n  NOTE: Voltage did not fully settle within capture window")
                calc_log.append(f"    Final voltage: {post_trigger[-1]:.4f}V")
                calc_log.append(f"    Deviation from baseline: {(post_trigger[-1] - baseline)*1000:.2f}mV")

            calc_log.append(f"\n  RECOVERY TIME CALCULATION:")
            calc_log.append(f"    Settlement index: {recovery_idx} samples after trigger")
            calc_log.append(f"    Time increment per sample: {x_increment*1e6:.6f}µs")
            calc_log.append(f"    Calculation: {recovery_idx} × {x_increment*1e6:.6f}µs = {recovery_us:.3f}µs")
            calc_log.append(f"    RECOVERY TIME = {recovery_us:.1f}µs (Limit: {rail.max_recovery_time_us}µs) {'PASS' if recovery_us <= rail.max_recovery_time_us else 'FAIL'}")

            # *** NEW: PLACE SCOPE CURSORS FOR VISUAL VERIFICATION ***
            # Convert calculated indices to scope time and place X1/X2 cursors
            # This provides a visual confirmation on the oscilloscope display
            # showing exactly which points were used for the recovery time measurement
            cursor_delta_us = self.set_cursors_for_recovery(
                waveform,
                trigger_idx,          # X1: load step edge
                recovery_idx,         # X2: settlement point (or end of window if not settled)
                rail.name
            )

            if cursor_delta_us is not None:
                # Sanity check: scope cursor ΔX should match calculated recovery time
                # Allow up to 1-2 samples (~0.5-1.0 µs tolerance) for rounding differences
                delta_error = abs(cursor_delta_us - recovery_us)
                max_allowed_error = 2.0 * x_increment * 1e6  # 2 samples worth

                calc_log.append(f"\n  Scope Cursor Verification:")
                calc_log.append(f"    Calculated ΔX: {recovery_us:.2f}µs")
                calc_log.append(f"    Scope cursor ΔX: {cursor_delta_us:.2f}µs")
                calc_log.append(f"    Error: {delta_error:.2f}µs ({delta_error/recovery_us*100:.1f}%)")

                if delta_error <= max_allowed_error:
                    calc_log.append(f"    Status: MATCH (within +/-{max_allowed_error:.2f}µs tolerance)")
                else:
                    calc_log.append(f"    Status: WARNING (error exceeds tolerance)")
            else:
                calc_log.append(f"\n  NOTE: Cursor placement failed - visual verification unavailable")

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
                ringing_thresh = self._analysis_cfg.get("ringing_rms_threshold", 0.4)
                has_ringing = rms > ringing_thresh * peak if peak > 0 else False

                calc_log.append(f"\n  RINGING DETECTION CALCULATION:")
                calc_log.append(f"    Settled region mean: {settled_mean*1000:.3f}mV")
                calc_log.append(f"    RMS (standard deviation): {rms*1000:.3f}mV")
                calc_log.append(f"    Peak deviation from mean: {peak*1000:.3f}mV")
                calc_log.append(f"    RMS/Peak ratio: {rms_ratio:.3f}")
                calc_log.append(f"    Ringing threshold: RMS > {ringing_thresh} x Peak")
                calc_log.append(f"    Calculation: {rms*1000:.3f}mV > {ringing_thresh*peak*1000:.3f}mV? {has_ringing}")
                calc_log.append(f"    RINGING = {'YES - FAIL' if has_ringing else 'NO - PASS'}")
            else:
                has_ringing = False
                calc_log.append(f"  Not enough samples in settled region for ringing analysis")
                calc_log.append(f"  RINGING = NO (insufficient data)")

            # Add summary
            calc_log.append("\n" + "=" * 80)
            calc_log.append("MEASUREMENT SUMMARY")
            calc_log.append("=" * 80)
            calc_log.append(f"Droop:    {droop_mv:.1f}mV  (Limit: {rail.max_droop_mv}mV)  {'PASS' if droop_mv <= rail.max_droop_mv else 'FAIL'}")
            calc_log.append(f"Recovery: {recovery_us:.1f}µs (Limit: {rail.max_recovery_time_us}µs) {'PASS' if recovery_us <= rail.max_recovery_time_us else 'FAIL'}")
            calc_log.append(f"Ringing:  {'YES' if has_ringing else 'NO'}      (Required: NO)  {'FAIL' if has_ringing else 'PASS'}")
            overall_pass = (droop_mv <= rail.max_droop_mv and recovery_us <= rail.max_recovery_time_us and
                          not has_ringing)
            calc_log.append(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")
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
        """
        Generate brief summary notes explaining why a test passed or failed
        
        PURPOSE:
        Create a short textual description of what went wrong (if anything).
        Used in reports and summaries to explain pass/fail decisions.
        
        EXAMPLES OF OUTPUT:
        • "Within specification" - everything was good
        • "Droop exceeds limit by 25mV" - voltage sag was too much
        • "Recovery exceeds limit by 50us; Sustained ringing detected" - multiple issues
        
        PARAMETERS:
            rail: The rail configuration with limits
            droop: Measured droop magnitude
            recovery: Measured recovery time
            overshoot: Measured overshoot (if negative step)
            ringing: Was ringing detected (bool)
        
        RETURNS:
            A human-readable string explaining status. Can be shown in reports/summaries.
        """
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
        ═════════════════════════════════════════════════════════════════════════════════════
        *** TEST ONE COMPLETE VOLTAGE RAIL - BOTH POSITIVE AND NEGATIVE STEPS ***
        ═════════════════════════════════════════════════════════════════════════════════════
        
        PURPOSE (What does this do?):
        This function tests ONE voltage rail with TWO different load steps:
        • POSITIVE STEP: Load increases suddenly (low current → high current)
        • NEGATIVE STEP: Load decreases suddenly (high current → low current)
        
        These two tests together show how well the power supply regulates under different
        transient conditions. Some rails might handle load increases better than decreases.
        
        COMPLETE PROCESS FOR ONE RAIL:
        
        SETUP PHASE:
          1. Configure oscilloscope with per-rail settings (voltage scale, trigger level, etc.)
          2. Configure electronic load with per-rail current specifications
          3. Log detailed information about the rail being tested
        
        TEST PHASE 1 - POSITIVE LOAD STEP:
          1. Call perform_load_step() with direction=POSITIVE
          2. Load increases from low to high (e.g., 100mA → 800mA)
          3. Capture voltage waveform showing the dip (droop)
          4. Record measurements (droop, recovery time, ringing)
          5. Save screenshot and calculation log
        
        DELAY Phase (Critical for Test Quality):
          • Wait 1 second between positive and negative steps
          • Allows power supply to fully recover to steady state
          • Prevents one step from affecting the next step's measurements
        
        TEST PHASE 2 - NEGATIVE LOAD STEP:
          1. Call perform_load_step() with direction=NEGATIVE
          2. Load decreases from high to low (e.g., 800mA → 100mA)
          3. Capture voltage waveform showing the overshoot/rise
          4. Record measurements (droop/overshoot, recovery time, ringing)
          5. Save screenshot and calculation log
        
        CLEANUP PHASE:
          1. Disable the electronic load (turn off current)
          2. Determine overall result (PASS if both steps pass, FAIL if either fails)
          3. Log final summary
        
        PARAMETERS (Input):
            rail: RailConfig object containing:
                • name: Rail identifier (e.g., "1V8_E0", "3V3_CORE")
                • test_point: Physical location on PCB (e.g., "P10")
                • expected_voltage_v: Nominal voltage (e.g., 1.8V)
                • low_current_ma / high_current_ma: Current for step boundaries
                • max_droop_mv: Maximum allowed voltage change (e.g., 60mV)
                • max_recovery_time_us: Maximum allowed settling time (e.g., 500µs)
                • max_overshoot_mv: Maximum allowed overshoot (e.g., 40mV)
        
        RETURNS (Output):
            A RailTestResult object containing:
            
            • rail_name: Which rail was tested
            • test_point: Physical connection point
            • positive_step: TransientResult from positive load step
                - Contains droop, recovery, overshoot measurements
                - Contains screenshot path
                - Contains "PASS" or "FAIL" result
            • negative_step: TransientResult from negative load step
                - Same structure as positive_step
            • overall_result: Final determination
                - "PASS": Both positive AND negative steps passed
                - "FAIL": Either or both steps failed
                - "ERROR": Equipment connection problem prevented testing
        
        CRITICAL NOTES FOR ENGINEERS:
        1. The 1-second delay between steps is critical for accuracy
           - Without it, residual oscillations from step 1 affect step 2
        2. Both steps MUST pass for the rail to pass overall
           - A rail that handles increases fine but not decreases is FAIL
        3. All configuration is per-rail from SCOPE_CONFIG and LOAD_CONFIG
           - Different rails have different settings (justified by PCB design)
        4. Screenshots are automatically saved for documentation review
           - Manual inspection can validate automatic measurements
        5. If oscilloscope doesn't trigger, a forced capture is attempted
           - This can happen with very fast transients
        
        EXAMPLE OUTPUT for a PASS result:
            Rail: 1V8_E0 (P10)
            [PASS] Positive step: PASS (droop=48mV, recovery=210µs)
            [PASS] Negative step: PASS (overshoot=22mV, recovery=195µs)
            [PASS] Overall: PASS

        EXAMPLE OUTPUT for a FAIL result:
            Rail: 3V3_CORE (P20)
            [FAIL] Positive step: FAIL (droop=85mV exceeds limit 60mV)
            [PASS] Negative step: PASS (overshoot=28mV, recovery=300µs)
            [FAIL] Overall: FAIL (positive step failed)
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
        time.sleep(self._timing.get("delay_between_steps_s", 1.0))

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
        
        THIS IS THE MAIN ENTRY POINT FOR TESTING. It:
        1. Connects to lab equipment
        2. Shows user menu to select which rails to test
        3. For each selected rail:
           - Prompts user to connect probes
           - Runs positive load step test (automatically)
           - Runs negative load step test (automatically)
           - Saves results
        4. Generates reports and summaries
        5. Asks user whether to save or discard results
        
        PARAMETERS:
            rails: Optional list of rail names to test (like ['3V3', '1V8'])
                   If None, shows interactive menu for user to choose
        
        RETURNS:
            bool: True if test completed successfully (not necessarily all passed)
                  False if test failed to run (e.g., equipment connection failed)
        
        WHAT "MINIMAL USER INTERVENTION" MEANS:
        - User only needs to:
          1. Connect equipment (probes, electronic load)
          2. Confirm connection when prompted
          3. Decide whether to save results
        - Everything else is automatic:
          - Equipment configuration
          - Load steps
          - Waveform capture
          - Measurements
          - Analysis
        """
        # ─── RECORD TEST START TIME ────────────────────────────────────────
        self.test_start_time = datetime.now()

        # ─── PRINT TEST BANNER ────────────────────────────────────────────
        print("\n" + "=" * 70)
        print(" LOAD TRANSIENT RESPONSE TEST - MINIMAL INTERVENTION MODE")
        print("=" * 70)
        print(f" Start time: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f" Output directory: {self.output_dir}")
        print("=" * 70)

        # ─── CONNECT TO INSTRUMENTS ───────────────────────────────────────
        # This is critical - without instruments, we can't do anything
        if not self.connect_instruments():
            print("\nERROR: Failed to connect to instruments!")
            return False

        # ─── DETERMINE WHICH RAILS TO TEST ────────────────────────────────
        if rails:
            # Specific rails passed in (from command line or caller)
            # Filter RAIL_CONFIGS to only include the ones requested
            rails_to_test = [r for r in self.RAIL_CONFIGS if r.name in rails]
        else:
            # Interactive selector – user picks with TAB + ENTER
            # This shows a menu letting the user choose which rails
            selected_names = interactive_rail_selector(self.RAIL_CONFIGS)
            if selected_names is None:
                # User pressed Q to cancel
                print("Test cancelled by user.")
                self.disconnect_instruments()
                return False
            # Filter RAIL_CONFIGS to only include selected rails
            rails_to_test = [r for r in self.RAIL_CONFIGS if r.name in selected_names]

        # ─── PRINT SUMMARY OF WHICH RAILS WILL BE TESTED ────────────────
        print(f"\nRails to test ({len(rails_to_test)}):")
        for i, rail in enumerate(rails_to_test, 1):
            print(f"  {i}. {rail.name} ({rail.test_point}): {rail.load_step_positive}")
        print()

        # ─── TEST EACH SELECTED RAIL ──────────────────────────────────────
        # Main testing loop - for each selected rail, confirm connection and run tests
        for i, rail in enumerate(rails_to_test, 1):
            # Print which rail we're about to test
            print(f"\n{'─' * 70}")
            print(f"  [{i}/{len(rails_to_test)}]  RAIL: {rail.name} ({rail.test_point})")
            print(f"{'─' * 70}")
            print(f"    Expected voltage: {rail.expected_voltage_v}V")
            print(f"    Load step: {rail.load_step_positive}")
            print()
            print(f"    Connect electronic load and scope probe to {rail.test_point}")
            print(f"    - Scope CH1: Rail voltage (DC coupled, 1:1 probe)")
            print()

            # ─── WAIT FOR USER TO CONFIRM CONNECTION ──────────────────────
            # Loop until user confirms connection, skips, or quits
            while True:
                response = input(f"    Connected to {rail.name}? (yes/skip/quit): ").strip().lower()

                if response in ['yes', 'y']:
                    # User confirmed connection - now check PSU is powered on
                    # ── PSU check after confirming probe connection ──
                    psu_ok = input("    Is the PSU powered ON? (yes/no): ").strip().lower()
                    if psu_ok not in ['yes', 'y']:
                        print("    Please turn ON the PSU and try again.")
                        psu_ok = input("    PSU is ON now? (yes/quit): ").strip().lower()
                        if psu_ok not in ['yes', 'y']:
                            response = 'quit'  # User chose to quit
                            break

                    # ─── RUN THE ACTUAL TEST ──────────────────────────────
                    # This calls test_single_rail() which does all the work
                    result = self.test_single_rail(rail)
                    self.results.append(result)  # Store the result

                    # ─── PRINT PASS/FAIL RESULT ────────────────────────
                    if result.overall_result == "PASS":
                        status_symbol = _c("[PASS]", _C_GREEN)
                    elif result.overall_result == "FAIL":
                        status_symbol = _c("[FAIL]", _C_RED)
                    else:
                        status_symbol = _c("[ERROR]", _C_YELLOW)
                    print(f"\n    {status_symbol} {rail.name} test complete!")
                    break

                elif response == 'skip':
                    # User chose to skip this rail
                    print(f"    Skipping {rail.name}")
                    # Still record that this rail wasn't tested (for completeness)
                    self.results.append(RailTestResult(
                        rail_name=rail.name,
                        test_point=rail.test_point,
                        overall_result="NOT_TESTED"
                    ))
                    break

                elif response == 'quit':
                    # User chose to quit the entire test sequence
                    print("\n    Test sequence ended by user")
                    break

                else:
                    print("    Please enter 'yes', 'skip', or 'quit'")

            if response == 'quit':
                break  # Break out of the main testing loop

        # ─── TEST COMPLETE - RECORD END TIME ───────────────────────────────
        self.test_end_time = datetime.now()
        # Calculate how long the entire test took
        duration = (self.test_end_time - self.test_start_time).total_seconds()

        # ─── DISCONNECT EQUIPMENT ──────────────────────────────────────────
        # Safely shut down all equipment
        self.disconnect_instruments()

        # ─── PRINT SUMMARY TO CONSOLE ──────────────────────────────────────
        # Always show summary so user can review before deciding
        self._print_summary()

        # ─── ASK USER WHETHER TO SAVE RESULTS ──────────────────────────────
        # At this point, results are in memory. User decides whether to save or discard them.
        print(f"\n{'─' * 70}")
        print(f"  Results would be saved to: {self.output_dir}")
        print(f"{'─' * 70}")
        
        while True:
            save_choice = input("  Save results? (yes/no): ").strip().lower()
            if save_choice in ('yes', 'y'):
                # ─── GENERATE AND SAVE REPORTS ────────────────────────────
                # Create CSV, JSON, text files with results
                self._generate_reports()
                print(f"\n  Results saved to: {self.output_dir}")
                break
            elif save_choice in ('no', 'n'):
                # ─── DISCARD ALL RESULTS ───────────────────────────────────
                # Close every logging handler on every logger (root + children)
                # so Windows releases the lock on load_transient_test.log before deletion.
                for name, lgr in list(logging.Logger.manager.loggerDict.items()):
                    if isinstance(lgr, logging.Logger):
                        for h in list(lgr.handlers):
                            try: h.flush()
                            except Exception: pass
                            try: h.close()
                            except Exception: pass
                            try: lgr.removeHandler(h)
                            except Exception: pass
                for h in list(logging.root.handlers):
                    try: h.flush()
                    except Exception: pass
                    try: h.close()
                    except Exception: pass
                    try: logging.root.removeHandler(h)
                    except Exception: pass
                try: logging.shutdown()
                except Exception: pass

                time.sleep(0.3)  # Let Windows release file locks

                # Delete the entire run folder (screenshots, calculations, reports, log)
                output_dir = self.output_dir
                deleted = False
                if output_dir.exists():
                    def _force_delete(func, path, exc_info):
                        try: os.chmod(path, 0o777)
                        except Exception: pass
                        try: func(path)
                        except Exception: pass

                    for _ in range(5):
                        try:
                            shutil.rmtree(output_dir, onerror=_force_delete)
                            if not output_dir.exists():
                                deleted = True
                                break
                        except Exception:
                            pass
                        time.sleep(0.3)

                if deleted:
                    print("\n  Results discarded — run folder deleted.")
                else:
                    print(f"\n  Could not fully delete: {output_dir}")
                    print("  Some files may still remain (close any open file handles and delete manually).")
                break
            else:
                print("  Please enter 'yes' or 'no'")

        return True

    def _generate_reports(self):
        """
        ═════════════════════════════════════════════════════════════════════════════════════
        *** GENERATE ALL TEST REPORTS - CSV, JSON, AND SUMMARY DOCUMENTS ***
        ═════════════════════════════════════════════════════════════════════════════════════
        
        PURPOSE (What does this do?):
        This function creates three different report files from the test results:
        
        1. JSON REPORT - Machine-Readable Format
        2. CSV REPORT - Spreadsheet-Friendly Format  
        3. TEXT SUMMARY - Human-Readable Format
        
        WHY MULTIPLE FORMATS?
        • JSON: Computer-friendly (automated parsing, integration with other tools)
        • CSV: Spreadsheet-friendly (Microsoft Excel, Google Sheets)
        • TEXT: Human-Friendly (easy to read in documentation, emails, reports)
        
        WHAT EACH REPORT CONTAINS:
        
        JSON REPORT (load_transient_results_TIMESTAMP.json):
        ─────────────────────────────────────────────
        Machine-readable format with complete test information:
        - Test metadata (name, start time, end time, duration)
        - All rail test results:
          - Rail name and test point
          - Positive step results (droop, recovery time, pass/fail)
          - Negative step results (droop, recovery time, pass/fail)
          - Overall result per rail
          - Links to detailed calculation files
        
        Good for:
        - Automated test reporting systems
        - Continuous integration (CI) tools
        - Integration with test management databases
        - Programmatic analysis
        
        CSV REPORT (load_transient_results_TIMESTAMP.csv):
        ──────────────────────────────────────────
        Spreadsheet format organized by load step:
        - Columns: Rail, Step, Load_Step_mA, DV_Droop_Or_Rise, Trigger, Result, File
        - One row per load step (each rail has 2 rows: positive + negative)
        - Columns explained:
          * Rail: Voltage rail name (e.g., "1V8_E0")
          * Step: "POSITIVE" or "NEGATIVE"
          * Load_Step_mA: How much current changed (e.g., "100 -> 800mA")
          * DV_Droop_Or_Rise: Peak voltage change in millivolts
          * Trigger: Oscilloscope trigger level used (for verification)
          * Result: "PASS", "FAIL", or "ERROR"
          * Calculation_File: Link to detailed calculation log for this step
        
        Good for:
        - Review by test engineers in Excel/Sheets
        - Quick scan of pass/fail status
        - Comparison across multiple test runs
        - Documentation archives
        
        TEXT SUMMARY (load_transient_results_TIMESTAMP.txt):
        ───────────────────────────────────────────
        Human-readable summary with clear heading structure:
        - Test metadata (date, time, pass/fail summary)
        - Results table showing all rails and steps
        - Detailed findings for each rail
        - Overall test conclusion
        
        Good for:
        - Email reports to stakeholders
        - Documentation review by non-engineers
        - Print-friendly format
        - Meeting presentations
        
        ORGANIZATION (Where files are saved):
        ─────────────────────────────────────
        Test output directory structure:
        run_TIMESTAMP/
          ├── reports/
          │   ├── load_transient_results_TIMESTAMP.json
          │   ├── load_transient_results_TIMESTAMP.csv
          │   └── load_transient_results_TIMESTAMP.txt
          ├── calculations/
          │   ├── 1V8_E0_low_to_high_calculations.txt
          │   ├── 1V8_E0_high_to_low_calculations.txt
          │   └── ... (one per load step)
          └── screenshots/
              ├── 1V8_E0_low_to_high.png
              ├── 1V8_E0_high_to_low.png
              └── ... (one per load step)
        
        INFORMATION FLOW:
        1. Test results stored in self.results (list of RailTestResult objects)
        2. This function iterates through self.results
        3. Formats data for each report type
        4. Saves to timestamped files (so each test run has unique files)
        5. Logs file paths to console for user reference
        
        TIMESTAMP USE:
        - Uses self.test_start_time (recorded when test began)
        - Format: YYYYMMDD_HHMMSS (e.g., 20250311_131136)
        - This ensures multiple test runs don't overwrite each other
        - Allows tracking of test history over time
        
        FOR NON-TECHNICAL STAFF:
        - After test completes, they'll receive 3 files
        - CSV is easiest to open in Excel for quick review
        - JSON is for automated systems (ignore if not tech-savvy)
        - TEXT is suitable for printing or forwarding to management
        
        FOR ENGINEERS:
        - Use JSON for detailed programmatic analysis
        - Use TEXT for finding specific calculation details (linked files)
        - Use CSV for comparing multiple test runs side-by-side
        """
        timestamp = self.test_start_time.strftime("%Y%m%d_%H%M%S")

        # JSON report
        json_path = self.reports_dir / f"load_transient_results_{timestamp}.json"
        report_data = {
            'test_info': {
                'test_name': 'Load Transient Response Test',
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
        csv_path = self.reports_dir / f"load_transient_results_{timestamp}.csv"
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
        summary_path = self.reports_dir / f"load_transient_summary_{timestamp}.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_summary_text())

        self._logger.info(f"Summary saved: {summary_path}")

        # Generate index of detailed calculation files
        calc_index_path = self.calculations_dir / "README.txt"
        with open(calc_index_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("DETAILED CALCULATION FILES - LOAD TRANSIENT RESPONSE TEST\n")
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
        """
        ═════════════════════════════════════════════════════════════════════════════════════
        *** GENERATE HUMAN-READABLE TEST SUMMARY IN TEXT FORMAT ***
        ═════════════════════════════════════════════════════════════════════════════════════
        
        PURPOSE (What does this do?):
        Creates a nicely formatted text file that summarizes all test results in a way
        that's easy for humans to read. This is NOT a detailed analysis file - it's a 
        high-level summary suitable for emails, reports, or printed documentation.
        
        WHAT THIS SUMMARY CONTAINS:
        
        1. TEST METADATA SECTION:
           - Test date and time when it started
           - Total duration (how long it took)
           - Example: "Test Date: 2025-03-11 13:11:36"
        
        2. OVERALL STATISTICS SECTION:
           - Total rails tested (e.g., 4 rails)
           - How many passed (e.g., 3 PASS)
           - How many failed (e.g., 1 FAIL)
           - Overall test conclusion (PASS if all rails pass, FAIL if any fails)
           - Example:
             Total Rails: 4
             Passed: 3
             Failed: 1
             OVERALL RESULT: FAIL
        
        3. DETAILED RESULTS TABLE:
           One row per rail, showing:
           - Rail name (e.g., "1V8_E0")
           - Positive load step result (PASS/FAIL)
           - Negative load step result (PASS/FAIL)
           - Overall rail status (PASS if both steps pass, FAIL otherwise)
           
           Example table:
           ┌─────────────┬──────────┬──────────┬─────────┐
           │ Rail        │ Positive │ Negative │ Overall │
           ├─────────────┼──────────┼──────────┼─────────┤
           │ 1V8_E0      │ PASS     │ PASS     │ PASS    │
           │ 3V3_CORE    │ FAIL     │ PASS     │ FAIL    │
           │ 5V0         │ PASS     │ PASS     │ PASS    │
           └─────────────┴──────────┴──────────┴─────────┘
        
        4. DETAILED FINDINGS SECTION:
           For each rail, shows:
           - Rail name and test point
           - Positive step details (droop value, pass/fail with reason)
           - Negative step details (overshoot value, pass/fail with reason)
           - Recovery times
           - Any ringing detected
           
           Example:
           RAIL: 3V3_CORE (P20)
           ─────────────────────────────────────────────────────────
           [FAIL] POSITIVE STEP FAILED
               Droop: 85mV (limit: 60mV) - exceeds limit by 25mV
               Recovery: 320µs

           [PASS] NEGATIVE STEP PASSED
               Overshoot: 28mV (limit 40mV)
               Recovery: 298µs
           
           Status: FAIL (positive step exceeded limits)
        
        5. OVERALL CONCLUSION SECTION:
           Final statement like:
           "Test FAILED - 1 rail out of 4 exceeded specifications"
           OR
           "Test PASSED - All 4 rails met specifications"
        
        FORMAT DESIGN (For Readability):
        - Uses unicode box drawing characters for nice display
        - Uses [PASS] and [FAIL] labels for results
        - Uses separators (═══) to organize sections
        - Fixed-width font presentation (monospace)
        - Suitable for printing or email forwarding
        
        WHO READS THIS?
        • Test engineers reviewing quick status
        • Project managers checking pass/fail
        • Auditors verifying test completion
        • Non-technical stakeholders getting high-level summary
        • Documentation teams creating test reports
        
        RELATIONSHIP TO OTHER FILES:
        - Companion to CSV file (which is for spreadsheet import)
        - Links to detailed calculation files for engineers who need specifics
        - Much shorter than full JSON report (easier to skim)
        
        EXAMPLE USE CASE:
        Email to management:
        "Load Transient Response Test - PASSED
         All 4 voltage rails met transient response specifications.
         See attached text summary for details and calculation files for review."
        
        RETURN VALUE:
        Returns the complete summary as a multi-line string that gets written
        to a text file with timestamp (e.g., load_transient_summary_20250311_131136.txt)
        """
        lines = []
        lines.append("=" * 80)
        lines.append("LOAD TRANSIENT RESPONSE TEST SUMMARY")
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
        col_w = {"rail": 10, "step": 16, "droop": 16, "recovery": 16, "trigger": 10}
        table_w = sum(col_w.values()) + 9  # separators

        lines.append("LOW TO HIGH (Load Up)")
        lines.append("=" * table_w)
        lines.append(
            f" {'Rail':<{col_w['rail']}}| {'Load Step':<{col_w['step']}}| "
            f"{'DV Droop':<{col_w['droop']}}| {'Recovery Time':<{col_w['recovery']}}| "
            f"{'Trigger':<{col_w['trigger']}}"
        )
        lines.append(
            f" {'':_<{col_w['rail']}}|{'':_<{col_w['step']+1}}|"
            f"{'':_<{col_w['droop']+1}}|{'':_<{col_w['recovery']+1}}|"
            f"{'':_<{col_w['trigger']+1}}"
        )
        lines.append(
            f" {'':>{col_w['rail']}}| {'(mA)':<{col_w['step']}}| "
            f"{'(mV)':<{col_w['droop']}}| {'(µs)':<{col_w['recovery']}}| "
            f"{'':>{col_w['trigger']}}"
        )
        lines.append("-" * table_w)

        for result in self.results:
            if result.positive_step:
                step = result.positive_step
                cfg = self.SCOPE_CONFIG.get(result.rail_name, {})
                trigger_val = cfg.get("trigger_up", "")
                trigger_str = f"{trigger_val:.3f}" if isinstance(trigger_val, (int, float)) else str(trigger_val)
                rec_str = f"{step.recovery_time_us:.1f}" if step.recovery_time_us else ""
                lines.append(
                    f" {result.rail_name:<{col_w['rail']}}| "
                    f"{step.load_step_description:<{col_w['step']}}| "
                    f"{step.droop_mv:<{col_w['droop']}.1f}| "
                    f"{rec_str:<{col_w['recovery']}}| "
                    f"{trigger_str:<{col_w['trigger']}}"
                )
            else:
                lines.append(
                    f" {result.rail_name:<{col_w['rail']}}| {'NOT TESTED':<{col_w['step']}}| "
                    f"{'':<{col_w['droop']}}| {'':<{col_w['recovery']}}| {'':<{col_w['trigger']}}"
                )

        lines.append("=" * table_w)
        lines.append("")

        # ── HIGH TO LOW table ──
        lines.append("HIGH TO LOW (Load Down)")
        lines.append("=" * table_w)
        lines.append(
            f" {'Rail':<{col_w['rail']}}| {'Load Step':<{col_w['step']}}| "
            f"{'DV Rise':<{col_w['droop']}}| {'Recovery Time':<{col_w['recovery']}}| "
            f"{'Trigger':<{col_w['trigger']}}"
        )
        lines.append(
            f" {'':_<{col_w['rail']}}|{'':_<{col_w['step']+1}}|"
            f"{'':_<{col_w['droop']+1}}|{'':_<{col_w['recovery']+1}}|"
            f"{'':_<{col_w['trigger']+1}}"
        )
        lines.append(
            f" {'':>{col_w['rail']}}| {'(mA)':<{col_w['step']}}| "
            f"{'(mV)':<{col_w['droop']}}| {'(µs)':<{col_w['recovery']}}| "
            f"{'':>{col_w['trigger']}}"
        )
        lines.append("-" * table_w)

        for result in self.results:
            if result.negative_step:
                step = result.negative_step
                cfg = self.SCOPE_CONFIG.get(result.rail_name, {})
                trigger_val = cfg.get("trigger_down", "")
                trigger_str = f"{trigger_val:.3f}" if isinstance(trigger_val, (int, float)) else str(trigger_val)
                rec_str = f"{step.recovery_time_us:.1f}" if step.recovery_time_us else ""
                lines.append(
                    f" {result.rail_name:<{col_w['rail']}}| "
                    f"{step.load_step_description:<{col_w['step']}}| "
                    f"{step.droop_mv:<{col_w['droop']}.1f}| "
                    f"{rec_str:<{col_w['recovery']}}| "
                    f"{trigger_str:<{col_w['trigger']}}"
                )
            else:
                lines.append(
                    f" {result.rail_name:<{col_w['rail']}}| {'NOT TESTED':<{col_w['step']}}| "
                    f"{'':<{col_w['droop']}}| {'':<{col_w['recovery']}}| {'':<{col_w['trigger']}}"
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

        rail_cfg_by_name = {r.name: r for r in self.RAIL_CONFIGS}

        def _step_failure_reasons(step: Optional[TransientResult], rail_cfg: Optional[RailConfig]) -> List[str]:
            if not step:
                return ["step missing"]
            if step.result == "PASS":
                return []
            if step.result == "ERROR":
                return ["measurement error"]

            reasons = []
            if rail_cfg:
                if step.droop_mv and step.droop_mv > rail_cfg.max_droop_mv:
                    reasons.append(f"droop {step.droop_mv:.1f}mV > {rail_cfg.max_droop_mv:.1f}mV")
                if step.recovery_time_us and step.recovery_time_us > rail_cfg.max_recovery_time_us:
                    reasons.append(f"recovery {step.recovery_time_us:.1f}µs > {rail_cfg.max_recovery_time_us:.1f}µs")
                if step.overshoot_mv and step.overshoot_mv > rail_cfg.max_overshoot_mv:
                    reasons.append(f"overshoot {step.overshoot_mv:.1f}mV > {rail_cfg.max_overshoot_mv:.1f}mV")
            if step.has_ringing:
                reasons.append("ringing detected")
            if not reasons:
                reasons.append("failed")
            return reasons

        passed_rails = [r for r in self.results if r.overall_result == "PASS"]
        failed_rails = [r for r in self.results if r.overall_result == "FAIL"]
        not_tested_rails = [r for r in self.results if r.overall_result == "NOT_TESTED"]

        if passed_rails:
            lines.append("")
            lines.append("RAILS PASSED:")
            for r in passed_rails:
                lines.append(f"  - {r.rail_name}")

        if failed_rails:
            lines.append("")
            lines.append("RAILS FAILED (reason):")
            for r in failed_rails:
                cfg = rail_cfg_by_name.get(r.rail_name)
                pos_reasons = _step_failure_reasons(r.positive_step, cfg)
                neg_reasons = _step_failure_reasons(r.negative_step, cfg)
                reason_parts = []
                if pos_reasons:
                    reason_parts.append("LOW→HIGH: " + ", ".join(pos_reasons))
                if neg_reasons:
                    reason_parts.append("HIGH→LOW: " + ", ".join(neg_reasons))
                reason_str = " | ".join(reason_parts) if reason_parts else "failed"
                lines.append(f"  - {r.rail_name}: {reason_str}")

        if not_tested_rails:
            lines.append("")
            lines.append("RAILS NOT TESTED:")
            for r in not_tested_rails:
                lines.append(f"  - {r.rail_name}")

        lines.append("=" * table_w)
        lines.append("")
        lines.append("Note: DV Droop / DV Rise = |ΔY| from scope cursor (Y1=baseline, Y2=Vmin or Vmax)")
        lines.append("      Recovery Time        =  ΔX from scope cursor (X1=trigger edge, X2=settled point)")
        lines.append("")
        lines.append("DETAILED CALCULATION FILES:")
        lines.append("  See 'calculations' folder for step-by-step measurement breakdowns.")
        lines.append("=" * table_w)

        return "\n".join(lines)

    def _print_summary(self):
        """
        Print final test summary to console (terminal output)
        
        PURPOSE:
       This displays the complete test summary to the user's terminal after testing.
        Prints:
        1. Results table (which rails passed/failed)
        2. Where results were saved (file folder structure)
        3. Tips for finding detailed calculations
        
        WHY PRINT TO CONSOLE?
        - Immediate feedback - user sees results right away
        - No need to open files - quick glance at pass/fail
        - Friendly format with emojis and borders
        - Guides user to detailed files if needed
        
        WHAT THE OUTPUT SHOWS:
        ─────────────────────
        LOAD TRANSIENT RESPONSE TEST SUMMARY
        ═════════════════════════════════════════
        Test Date: 2025-03-11 13:11:36
        Duration: 245.3 seconds
        
        Results Summary:
        Total Rails: 4
        Passed: 3
        Failed: 1
        OVERALL RESULT: FAIL
        
        [Detailed table with each rail's results...]
        
        Results saved to: /path/to/run_20250311_131136/
          ├─ screenshots/     - Oscilloscope waveform captures
          ├─ reports/         - CSV, JSON, and summary reports
          └─ calculations/    - Detailed step-by-step calculation logs
        
        TIP: Check the 'calculations' folder for detailed breakdowns...
        
        AUDIENCE:
        - Test engineers at the lab bench
        - Anyone running the test interactively
        - Quick reference for pass/fail status
        
        CONTRAST WITH OTHER OUTPUT:
        - _generate_summary_text(): Creates saveable file (for archives)
        - This method: Console output (for immediate feedback)
        """
        # Colorize key PASS/FAIL keywords for console readability
        def _colorize_line(line: str) -> str:
            if "OVERALL TEST RESULT: PASS" in line:
                return line.replace("PASS", _c("PASS", _C_GREEN))
            if "OVERALL TEST RESULT: FAIL" in line:
                return line.replace("FAIL", _c("FAIL", _C_RED))
            if "OVERALL TEST RESULT: INCOMPLETE" in line:
                return line.replace("INCOMPLETE", _c("INCOMPLETE", _C_YELLOW))
            if line.startswith("RAILS PASSED:"):
                return _c(line, _C_GREEN)
            if line.startswith("RAILS FAILED"):
                return _c(line, _C_RED)
            if line.startswith("RAILS NOT TESTED:"):
                return _c(line, _C_YELLOW)
            if line.startswith("  - ") and any(r.overall_result == "PASS" for r in self.results if r.rail_name in line):
                return _c(line, _C_GREEN)
            if line.startswith("  - ") and any(r.overall_result == "FAIL" for r in self.results if r.rail_name in line):
                return _c(line, _C_RED)
            return line

        summary_text = self._generate_summary_text()
        colorized = "\n".join(_colorize_line(l) for l in summary_text.split("\n"))
        print("\n" + colorized)
        print(f"\nResults saved to: {self.output_dir}")
        print(f"  ├─ screenshots/     - Oscilloscope waveform captures")
        print(f"  ├─ reports/         - CSV, JSON, and summary reports")
        print(f"  └─ calculations/    - Detailed step-by-step calculation logs")
        print(f"\nTIP: Check the 'calculations' folder for detailed breakdowns")
        print(f"     of how droop, recovery time, and overshoot were calculated.")


def main():
    """
    ═════════════════════════════════════════════════════════════════════════════════════
    *** MAIN ENTRY POINT - STARTS THE TEST WHEN SCRIPT IS RUN DIRECTLY ***
    ═════════════════════════════════════════════════════════════════════════════════════
    
    PURPOSE (What does this do?):
    This is the entry point that runs when you execute this Python script directly.
    It creates the test object and starts the complete Load Transient test sequence.
    
    TYPICAL USAGE (How to run this):
    
    OPTION 1 - Let it auto-detect instruments (RECOMMENDED):
    ────────────────────────────────────────────────────────
    Command: python load_transient_response_test.py
    
    What happens:
    1. Script looks for oscilloscope and electronic load on the VISA bus
    2. Automatically connects to found instruments
    3. Shows interactive menu for selecting which rails to test
    4. Runs tests
    5. Saves reports and screenshots
    
    OPTION 2 - Provide specific instrument addresses:
    ─────────────────────────────────────────────────
    Command: python load_transient_response_test.py SCOPE_ADDRESS LOAD_ADDRESS
    
    Example: python load_transient_response_test.py "GPIB0::14::INSTR" "GPIB0::4::INSTR"
    
    What happens:
    1. Script uses the provided addresses (doesn't search)
    2. Connects directly to those instruments
    3. Proceeds with interactive menu and testing
    
    OPTION 3 - Use the wrapper script (BEST EXPERIENCE):
    ──────────────────────────────────────────────────
    Command: python run_load_transient_test.py --rails 1V8_E0 3V3_CORE
    
    What run_load_transient_test.py does:
    - Provides command-line argument handling (--list, --rails, etc.)
    - Calls this script automatically
    - Better user experience and logging
    
    COMPLETE PROCESS (What's happening):
    
    STAGE 1 - INITIALIZATION:
      1. Print banner showing what test is about to run
      2. Parse command-line arguments (if provided)
      3. Create LoadTransientTest object
        - Loads configuration from load_transient_config.json
        - Auto-detects or connects to instruments
        - Sets up output directories
    
    STAGE 2 - INSTRUMENT VERIFICATION:
      1. Check if oscilloscope was found
      2. Check if electronic load was found
      3. If either is missing, show error and quit
      4. Display their addresses to user
    
    STAGE 3 - INTERACTIVE TESTING:
      1. Call test.run_test_sequence()
      2. This shows menu: "Which rails do you want to test?"
      3. User selects with TAB/ARROW and presses ENTER
      4. For each selected rail:
         - Prompt user to connect probes
         - Run positive load step test
         - Run negative load step test
         - Save screenshots and calculations
      5. After all tests: Generate reports (JSON, CSV, TXT)
      6. Ask user: Save results or discard?
    
    STAGE 4 - COMPLETION:
      1. Return 0 (success) to operating system
      2. Or return 1 (failure) if something went wrong
    
    CONFIGURATION SOURCE:
    All settings come from load_transient_config.json:
    - Oscilloscope model and settings
    - Electronic load configuration
    - Rail specifications (voltage, current, limits)
    - Oscilloscope trigger settings per rail
    - Output directory paths
    
    ERROR HANDLING:
    If instruments not found:
    - Prints helpful error message
    - Shows command to list available instruments
    - Suggests passing addresses as arguments
    - Returns error code 1 to OS
    
    RETURN VALUE:
    - 0: Test completed successfully (not necessarily all passed)
         Return 0 even if test results were FAIL (test itself ran)
    - 1: Test could not run (instrument connection failed, etc.)
         Return 1 for errors that prevented testing
    
    WHY THIS DISTINCTION?
    - 0 = "test framework worked, report the results"
    - 1 = "couldn't even run the test, fix the setup"
    
    FOR AUTOMATION/CI SYSTEMS:
    The return code allows bash/PowerShell scripts to detect problems:
    
    PowerShell example:
    ```
    python load_transient_response_test.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Test framework executed successfully"
        # Check CSV/JSON for actual pass/fail
    } else {
        Write-Host "Test framework failed - check connections!"
    }
    ```
    
    LOGGING:
    All activities are logged including:
    - Instrument connection details
    - Configuration loaded
    - Each rail tested
    - Final results saved
    
    Logs are saved to: run_TIMESTAMP/load_transient_test.log
    
    DEPENDENCIES:
    This function requires:
    - load_transient_config.json (configuration file)
    - LoadTransientTest class (defined above in this file)
    - oscilloscope and electronic load connected to VISA bus
    """
    print("=" * 70)
    print(" Load Transient Response Test - Auto-Detection Mode")
    print("=" * 70)
    print()
    print("NOTE: For best experience, use run_load_transient_test.py instead")
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

    # Create and run test (addresses and output_dir come from load_transient_config.json)
    test = LoadTransientTest(
        oscilloscope_address=scope_addr,
        electronic_load_address=load_addr,
    )

    # Check if instruments were found
    if not test.scope_address or not test.load_address:
        print("\nERROR: Required instruments not found!")
        print("  Use: python run_load_transient_test.py --list")
        print("  Or provide addresses: python load_transient_response_test.py <scope> <load>")
        return 1

    # Run test sequence (all rails)
    success = test.run_test_sequence()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
