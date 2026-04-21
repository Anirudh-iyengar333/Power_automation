#!/usr/bin/env python3
# ↑ This tells the computer this is a Python program

"""
Digantara Test Automation — Gradio GUI Framework

╔══════════════════════════════════════════════════════════════════════════════╗
║                      COMPLETE DOCUMENTATION SUMMARY                          ║
║                    For Non-Technical Documentation Reviews                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

─────────────────────────────────────────────────────────────────────────────── 
WHAT THIS PROGRAM DOES (In Simple Terms)
───────────────────────────────────────────────────────────────────────────────

This program provides a user-friendly web interface to run different test suites
on circuit boards. It's like a dashboard where you can:
  • Select which board you want to test
  • Choose which test to run (Load Transient, Power Sequencing, etc.)
  • See live output as the test runs
  • Save or delete the results

WHY THIS MATTERS:
Instead of typing complicated commands in a terminal, engineers can use buttons
and dropdowns in a clean web interface to control all test automation.

───────────────────────────────────────────────────────────────────────────────
HOW IT WORKS (Step-by-Step)
───────────────────────────────────────────────────────────────────────────────

1. PROGRAM DISCOVERS BOARDS AUTOMATICALLY
   ├─ Scans each test suite folder for files like "CPU_config.json"
   ├─ File name pattern: <BOARDNAME>_config.json
   └─ To add a new board: just drop its config file in the suite folder
   
2. USER OPENS THE GUI IN WEB BROWSER
   ├─ Left panel: Board, Test Suite, and Options dropdowns
   ├─ Right panel: Live test output display
   └─ Buttons: Run, Stop, Send (to answer test prompts)

3. USER SELECTS BOARD AND TEST SUITE
   ├─ Board dropdown auto-populates from discovered boards
   ├─ Suite dropdown shows only tests available for that board
   └─ Instruments required for the test appear in sidebar

4. USER CLICKS "RUN"
   ├─ Program launches the test script as a subprocess
   ├─ Captures all output line-by-line in real-time
   ├─ Displays in scrollable log window
   └─ Can send text to test via "Send" button if test asks for input

5. TEST COMPLETES
   ├─ Status shows "PASS" or "FAIL"
   ├─ "Keep Results" / "Delete Results" buttons appear
   └─ User decides whether to save or discard outputs

───────────────────────────────────────────────────────────────────────────────
FILE STRUCTURE AND KEY COMPONENTS
───────────────────────────────────────────────────────────────────────────────

LINES 1: #!/usr/bin/env python3
   └─ Special line telling operating system this is a Python script

LINES 3-56: PROGRAM DESCRIPTION
   └─ Overview of what the program does and how the GUI works

LINES 60-100: IMPORT STATEMENTS
   └─ Brings in helper tools/libraries the program depends on
   └─ Examples: gradio (web UI framework), subprocess (running test scripts)

LINES 110-150: PROJECT LAYOUT
   └─ Defines where test suites are located and their names
   └─ Lists which tests support which test modes
   └─ Maps short names (psu, dmm, scope) to human-readable labels

LINES 160-190: BOARD & SUITE DISCOVERY FUNCTIONS
   └─ discover_boards(suite_dir): Scans folder for *_config.json files
   └─ get_available_boards(): Lists all boards across all test suites
   └─ get_suites_for_board(): Shows which tests support a given board
   └─ get_config_path(): Finds the config file for board+suite combination

LINES 200-250: CONFIGURATION READING
   └─ get_rails_for_suite(): Extracts voltage rails to test from config
   └─ _instrument_info_html(): Creates visual list of required instruments

LINES 260-290: LOG RENDERING
   └─ _log_html(): Converts test output lines into styled HTML display
   └─ Auto-scrolls log window to bottom on every update

LINES 300-330: SUBPROCESS STATE MANAGEMENT
   └─ _active_proc: Stores reference to currently running test process
   └─ _proc_lock: Prevents multiple tests from running simultaneously
   └─ _last_run_dir: Tracks where most recent test results were saved

LINES 340-370: COMMAND BUILDING
   └─ _build_cmd(): Constructs the Python command to launch test script
   └─ Includes arguments like --headless, --output, --mode, --rails

LINES 380-500: TEST LAUNCHER (Generator Function)
   └─ launch_test(): Main function that runs a selected test
   └─ Validates user selections (board and suite must be picked)
   └─ Builds subprocess with proper encoding (UTF-8) and stdio piping
   └─ Yields (html_output, status, save_button_state) on each line
   └─ Searches for "Results saved:" pattern to track output folder

LINES 510-550: TEST CONTROL FUNCTIONS
   └─ send_to_test(): Sends user text to test via stdin (for prompts)
   └─ stop_test(): Terminates currently running test process
   └─ keep_results(): Marks test results as approved (keeps them)
   └─ delete_results(): Removes test results folder (Windows or Python)

LINES 560-590: FOLDER BROWSER DIALOG
   └─ browse_output_dir(): Opens native folder-picker using tkinter
   └─ Returns chosen path or current path if dialog cancelled

LINES 600-630: CSS STYLING
   └─ Custom styles for status box, save buttons, layout spacing

LINES 640-800: GRADIO USER INTERFACE CONSTRUCTION
   └─ build_gui(): Creates web interface with all controls
   └─ Left column: Dropdowns, output directory, Run/Stop buttons
   └─ Right column: Status display, live log, Send box, Save/Delete buttons
   └─ Event handlers: Board/Suite changes trigger UI updates
   └─ Click handlers: Wire buttons to their functions

LINES 810-830: ENTRY POINT
   └─ if __name__ == "__main__": Launch the GUI in browser

───────────────────────────────────────────────────────────────────────────────
CONFIGURATION AUTO-DISCOVERY PATTERN
───────────────────────────────────────────────────────────────────────────────

To add a new board to the test framework:
  1. Create a config file: CPU_config.json (or SENSOR_config.json, etc.)
  2. Copy it to each test suite folder that supports this board:
     ├─ Input_Range_OVP/CPU_config.json
     ├─ Load_Transient/CPU_config.json
     ├─ Power_Sequencing/CPU_config.json
     └─ Steady_State_Ripple/CPU_config.json
  3. NO code changes needed — GUI auto-discovers the new board
  4. Board appears in dropdown immediately on next GUI restart

To remove a board:
  • Delete the *_config.json files from test suite folders
  • Board disappears from dropdown automatically

This design makes the system extensible without requiring programmer intervention.

───────────────────────────────────────────────────────────────────────────────
ENCODING NOTE
───────────────────────────────────────────────────────────────────────────────

Subprocess stdout is opened with encoding='utf-8' and errors='replace' to handle
international characters and binary data safely across Windows/Linux/Mac.
This prevents UnicodeDecodeError when test scripts output non-ASCII bytes.
"""

import html as _html                           # ← Library for escaping HTML special characters
import json                                     # ← Library for reading/writing JSON files (config loading)
import os                                       # ← Library for environment variables and file operations
import re                                       # ← Library for regular expressions (pattern matching in output)
import shutil                                   # ← Library for high-level file operations (folder deletion)
import subprocess                               # ← Library for launching and controlling external processes (test scripts)
import sys                                      # ← Library for system-specific parameters (Python executable path)
import threading                                # ← Library for thread-safe locks (prevent simultaneous tests)
from pathlib import Path                        # ← Library for modern file path handling (cross-platform)

import gradio as gr                             # ← Gradio library for building web UI with Python

# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Section explains where all test suites are located and how they're named
# ─────────────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent                    # ← Get the folder where this script is located

# ← Dictionary mapping user-friendly test names to their folder paths and launcher scripts
SUITES: dict[str, tuple[Path, str]] = {
    "Input Range / OVP":   (ROOT / "Input_Range_OVP",    "run_input_range_ovp_test.py"),      # ← Input Range test suite location
    "Load Transient":      (ROOT / "Load_Transient",      "run_load_transient_test.py"),       # ← Load Transient test suite location
    "Power Sequencing":    (ROOT / "Power_Sequencing",    "run_power_sequencing_test.py"),     # ← Power Sequencing test suite location
    "Steady-State Ripple": (ROOT / "Steady_State_Ripple", "run_steady_state_ripple_test.py"),  # ← Steady-State Ripple test suite location
}

# ← Dictionary mapping test suite names to their available test modes
SUITE_MODES: dict[str, list[str]] = {
    "Input Range / OVP":   ["full", "fixed", "sweep"],                           # ← OVP test can run full, fixed, or sweep mode
    "Power Sequencing":    ["full", "config1", "config2", "capture", "reanalyze"],  # ← Power Sequencing test modes
}

# ← Dictionary mapping short instrument names to human-readable labels for the sidebar
_INSTR_LABELS: dict[str, str] = {
    "psu":             "Power Supply",                   # ← Label for psu instrument
    "dmm":             "Digital Multimeter",             # ← Label for dmm instrument
    "scope":           "Oscilloscope",                   # ← Label for scope instrument
    "electronic_load": "Electronic Load",                # ← Label for electronic_load instrument
}

# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Functions that auto-scan folders for board config files
# ─────────────────────────────────────────────────────────────────────────────

def discover_boards(suite_dir: Path) -> dict[str, Path]:
    # ← Scan the test suite directory for all *_config.json files
    return {p.stem.replace("_config", ""): p  # ← Extract board name from filename, store Path object
            for p in sorted(suite_dir.glob("*_config.json"))}  # ← Find all config files and sort by name


def get_available_boards() -> list[str]:
    # ← Collect all unique boards across all test suites
    boards: set[str] = set()  # ← Use a set to avoid duplicate board names
    for suite_dir, _ in SUITES.values():  # ← Loop through each test suite's directory
        boards |= set(discover_boards(suite_dir).keys())  # ← Add boards from this suite to the set
    return sorted(boards)  # ← Return boards in alphabetical order


def get_suites_for_board(board: str) -> list[str]:
    # ← Find which test suites support a given board
    return [name for name, (d, _) in SUITES.items()  # ← Iterate through suite names and folders
            if board in discover_boards(d)]  # ← Only include suites that have this board's config


def get_config_path(board: str, suite: str) -> Path | None:
    # ← Find the config file path for a specific board+suite combination
    info = SUITES.get(suite)  # ← Look up the suite in the SUITES dictionary
    if not info:  # ← If suite not found, return None
        return None  # ← Exit early with None
    return discover_boards(info[0]).get(board)  # ← Find board config in suite folder


def get_rails_for_suite(suite: str, cfg_path: Path) -> list[str] | None:
    # ← Extract voltage rail names from config file (only for certain suites)
    if suite not in ("Load Transient", "Steady-State Ripple"):  # ← Check if suite supports rails
        return None  # ← Return None if this suite doesn't have rails
    try:  # ← Wrap in try-except to handle file reading errors
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))  # ← Read and parse JSON config file
        key = "rail_configs" if suite == "Load Transient" else "rails"  # ← Use correct key for suite type
        return [r["name"] for r in cfg.get(key, [])]  # ← Extract rail names from config, default to empty list
    except Exception:  # ← If anything fails
        return None  # ← Return None gracefully


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Reads config files and builds the HTML sidebar showing required instruments
# ─────────────────────────────────────────────────────────────────────────────

def _instrument_info_html(board: str, suite: str) -> str:
    # ← Build HTML showing which instruments are required for the test
    if not board or not suite:  # ← If board or suite not selected
        return ""  # ← Return empty string (nothing to display)
    
    cfg_path = get_config_path(board, suite)  # ← Get the config file path
    if cfg_path is None:  # ← If config doesn't exist
        return ""  # ← Return empty string
    
    try:  # ← Wrap in try-except for safety
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))  # ← Read and parse JSON config
    except Exception:  # ← If file read fails
        return ""  # ← Return empty string

    addrs: dict = cfg.get("instrument_addresses", {})  # ← Get instrument_addresses from config, default to empty dict
    if not addrs:  # ← If no instruments listed
        return ""  # ← Return empty string

    items = []  # ← List to accumulate HTML <li> items
    for key in addrs:  # ← Loop through each instrument key
        if key.startswith("_"):  # ← Skip private/internal keys (starting with _)
            continue  # ← Move to next key
        
        label = _INSTR_LABELS.get(key, key.replace("_", " ").title())  # ← Get human-readable label, or auto-format
        items.append(  # ← Add this instrument to the list
            f"<li style='padding:2px 0'>{label}</li>"  # ← Create HTML list item with styling
        )

    if not items:  # ← If no items were added
        return ""  # ← Return empty string

    # ← Return complete HTML widget showing required instruments
    return (
        "<div style='background:#1e2a3a;border:0px solid #2d4a6e;border-radius:6px;"  # ← Outer container with dark blue background
        "padding:10px 14px;margin-top:4px;font-size:0.85em'>"  # ← Padding, margin, and font size
        "<div style='color:#4fc3f7;font-weight:600;margin-bottom:6px'>Instruments Required</div>"  # ← Title in cyan blue
        "<ul style='margin:0;padding-left:18px;color:#d4d4d4'>"  # ← Unordered list styling
        + "".join(items)  # ← Join all instrument items into one string
        + "</ul></div>"  # ← Close list and container
    )


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Converts test output lines to styled HTML that auto-scrolls to bottom
# ─────────────────────────────────────────────────────────────────────────────

# ← CSS styling for the log display area (height, colors, fonts, scrolling)
_LOG_STYLE = (
    "height:500px;overflow-y:auto;background:#1e1e1e;color:#d4d4d4;"  # ← Set height, enable vertical scroll, dark background, light text
    "font-family:'Consolas','Courier New',monospace;font-size:0.84em;"  # ← Use monospace font for code display
    "padding:12px;white-space:pre-wrap;border:1px solid #555;"  # ← Add padding, preserve whitespace, add border
    "border-radius:6px;line-height:1.45;"  # ← Round corners, set line spacing
)

# ← JavaScript snippet that auto-scrolls the log to the bottom when content updates
# The <img onerror> fires synchronously the moment the HTML is inserted into
# the DOM, scrolling the log div to the very bottom on every single update.
_SCROLL_SNIPPET = (
    '<img src="#" style="display:none" onerror="'  # ← Invisible image that triggers onerror handler
    "(function(){var d=document.getElementById('_diglog');"  # ← Get the log div by ID
    "if(d){d.scrollTop=d.scrollHeight;}})()"  # ← Scroll to bottom (scrollHeight = bottom)
    '">'  # ← Close the onerror attribute
)

def _log_html(lines: list[str], placeholder: str = "(No output yet)") -> str:
    # ← Convert a list of output lines into styled HTML that auto-scrolls
    body = _html.escape("".join(lines)) if lines else placeholder  # ← Join lines, escape HTML, or use placeholder
    return (
        f'<div id="_diglog" style="{_LOG_STYLE}">{body}</div>'  # ← Create div with ID and styling, insert body
        + _SCROLL_SNIPPET  # ← Add JavaScript snippet for auto-scroll
    )


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Tracks which test process is currently running (prevents multiple simultaneous tests)
# ─────────────────────────────────────────────────────────────────────────────

_active_proc: subprocess.Popen | None = None  # ← Stores the currently running test process (or None if idle)
_proc_lock    = threading.Lock()              # ← Lock to prevent race conditions between threads
_last_run_dir: Path | None = None             # ← Stores the path to the most recent test results folder


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Builds the command-line arguments passed to test suite launcher scripts
# ─────────────────────────────────────────────────────────────────────────────

def _build_cmd(suite: str, mode: str | None, rails: list[str] | None,
               output_dir: str) -> list[str]:
    # ← Construct the command-line arguments to run the test suite script
    suite_dir, runner = SUITES[suite]  # ← Get test suite folder and runner script name
    cmd = [sys.executable, str(suite_dir / runner),  # ← Start with Python executable and script path
           "--headless", "--output", output_dir or "gui_results"]  # ← Add headless mode and output directory
    
    if mode and suite in SUITE_MODES:  # ← If a test mode is selected and this suite supports modes
        cmd += ["--mode", mode]  # ← Add the mode argument
    
    if rails and suite == "Load Transient":  # ← If rails selected and this is Load Transient test
        cmd += ["--rails", ",".join(rails)]  # ← Add rails as comma-separated list
    elif rails and suite == "Steady-State Ripple":  # ← If rails selected and this is Steady-State Ripple test
        cmd += ["--rails"] + rails  # ← Add each rail as separate argument
    
    return cmd  # ← Return the complete command list


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Main test launcher - spawns subprocess and streams output in real-time
# ─────────────────────────────────────────────────────────────────────────────

def launch_test(board, suite, mode, rails, output_dir):
    """
    Generator → yields (log_html, status, save_row_update) on every new line.
    stdin is piped so the user can unblock in-test prompts via the Send button.
    """
    global _active_proc, _last_run_dir  # ← Declare as global so we can modify them

    # ← Validate that user has selected both board and test suite
    if not board or not suite:  # ← Check if board or suite is empty
        yield _log_html([], "Select a board and suite first."), "Error", gr.update(visible=False)  # ← Show error and exit
        return  # ← Stop execution

    # ← Get the config file for this board+suite combination
    cfg_path = get_config_path(board, suite)  # ← Look up config file path
    if cfg_path is None:  # ← If config doesn't exist
        yield (_log_html([], f"No config for {board} / {suite}."),  # ← Show error message with details
               "Error", gr.update(visible=False))  # ← Set status to Error
        return  # ← Stop execution

    # ← Check if another test is already running
    with _proc_lock:  # ← Acquire lock for thread safety
        if _active_proc is not None and _active_proc.poll() is None:  # ← If process exists and is still running
            yield (_log_html([], "A test is already running — click Stop first."),  # ← Show error message
                   "Running", gr.update(visible=False))  # ← Status stays "Running"
            return  # ← Stop execution

    # ← Build the command-line arguments for the test script
    cmd = _build_cmd(suite, mode, rails, output_dir)  # ← Get command list
    env = {**os.environ, "DIGANTARA_CONFIG": str(cfg_path), "PYTHONUTF8": "1"}  # ← Set up environment variables

    # ← Create the header text that displays test configuration
    header = [
        f"Board      : {board}\n",  # ← Show selected board name
        f"Suite      : {suite}\n",  # ← Show selected test suite name
        f"Config     : {cfg_path.name}\n",  # ← Show config filename
        f"Output dir : {output_dir or 'gui_results'}\n",  # ← Show output directory
        f"Command    : {' '.join(cmd[2:])}\n",  # ← Show the command being run (skip python exe and path)
        "─" * 60 + "\n",  # ← Draw a line separator
    ]
    yield _log_html(header), "Running", gr.update(visible=False)  # ← Display header and set status to Running

    # ← Spawn the test process
    try:  # ← Wrap in try-except to catch subprocess errors
        with _proc_lock:  # ← Acquire lock for thread safety
            _active_proc = subprocess.Popen(
                cmd,  # ← Command list to run
                stdout=subprocess.PIPE,  # ← Capture stdout as pipe
                stderr=subprocess.STDOUT,  # ← Redirect stderr to stdout
                stdin=subprocess.PIPE,  # ← lets Send button reply to in-test prompts
                text=True, bufsize=1,  # ← Treat output as text, line-buffered
                encoding='utf-8', errors='replace',  # ← Use UTF-8 encoding, replace invalid chars
                env=env, cwd=str(ROOT),  # ← Set environment and working directory
            )
    except Exception as exc:  # ← If subprocess launch fails
        yield _log_html(header + [f"\nFailed to launch: {exc}\n"]), "Error", gr.update(visible=False)  # ← Show error
        return  # ← Stop execution

    # ← Read output from the test process line-by-line
    log_lines = list(header)  # ← Start log with header
    _last_run_dir = None  # ← Initialize last run directory to None

    for line in _active_proc.stdout:  # ← Loop through each line of output
        log_lines.append(line)  # ← Add this line to the log
        m = re.search(r"Results saved[:\s]+(.+)", line)  # ← Search for "Results saved:" pattern
        if m:  # ← If pattern found
            p = Path(m.group(1).strip())  # ← Extract path from the match
            _last_run_dir = p if p.is_absolute() else ROOT / p  # ← Store path (absolute or relative to ROOT)
        yield _log_html(log_lines), "Running", gr.update(visible=False)  # ← Update display with new line

    # ← Wait for process to complete and check exit code
    _active_proc.wait()  # ← Wait for process to finish
    rc = _active_proc.returncode  # ← Get the exit code (0 = success, non-zero = failure)
    status = "PASS" if rc == 0 else "FAIL"  # ← Set status based on exit code

    # ← Add exit information to log
    log_lines += ["\n" + "─" * 60 + "\n", f"Process exited with code {rc}\n"]  # ← Show exit code

    # ← Determine if we should show the Save/Delete buttons
    show_save = bool(_last_run_dir and _last_run_dir.exists())  # ← Show buttons only if results folder exists
    if show_save:  # ← If results folder exists
        log_lines += [
            f"\nRun folder : {_last_run_dir}\n",  # ← Show results folder path
            "Choose below whether to keep or delete the results.\n",  # ← Instructions
        ]

    yield _log_html(log_lines), status, gr.update(visible=show_save)  # ← Final yield with status and buttons visibility

    # ← Clean up: mark process as None so a new test can run
    with _proc_lock:  # ← Acquire lock for thread safety
        _active_proc = None  # ← Clear the process reference


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Sends user input to test process stdin (for answering in-test prompts)
# ─────────────────────────────────────────────────────────────────────────────

def send_to_test(text: str) -> str:
    # ← Send user input to the test process to answer prompts
    """Write user text (+ newline) to subprocess stdin — unblocks in-test input() calls."""
    with _proc_lock:  # ← Acquire lock for thread safety
        proc = _active_proc  # ← Get reference to active process
    
    if proc and proc.poll() is None:  # ← If process exists and is still running
        try:  # ← Wrap in try-except for error handling
            proc.stdin.write((text or "") + "\n")  # ← Write text and newline to stdin
            proc.stdin.flush()  # ← Flush buffer to ensure data is sent immediately
        except Exception:  # ← If write fails
            pass  # ← Silently ignore the error
    
    return ""  # ← Return empty string to clear the input box


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Stop button handler - terminates running test process
# ─────────────────────────────────────────────────────────────────────────────

def stop_test() -> str:
    # ← Terminate the currently running test
    with _proc_lock:  # ← Acquire lock for thread safety
        if _active_proc and _active_proc.poll() is None:  # ← If process exists and is still running
            _active_proc.terminate()  # ← Send SIGTERM to terminate process gracefully
            return _log_html([], "Test stopped by user.")  # ← Return stop message
    
    return _log_html([], "No test is running.")  # ← Return message if no test running


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Keep results button - saves test output folder and metadata
# ─────────────────────────────────────────────────────────────────────────────

def keep_results() -> tuple[str, gr.update]:
    # ← User chose to keep the test results
    path = _last_run_dir  # ← Get the results folder path
    return _log_html([], f"Results kept:\n{path}"), gr.update(visible=False)  # ← Show message and hide buttons


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Delete results button - removes test output folder (with OS compatibility)
# ─────────────────────────────────────────────────────────────────────────────

def delete_results() -> tuple[str, gr.update]:
    # ← User chose to delete the test results
    global _last_run_dir  # ← Declare as global so we can modify it
    
    path = _last_run_dir  # ← Get the results folder path
    if not path or not path.exists():  # ← If path doesn't exist
        return _log_html([], "Run folder not found — nothing to delete."), gr.update(visible=False)  # ← Show error
    
    try:  # ← Try Windows-specific deletion first (more reliable on network drives)
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(path)],  # ← Use Windows rmdir command
                       capture_output=True, timeout=5)  # ← Suppress output, wait up to 5 seconds
    except Exception:  # ← If Windows method fails
        pass  # ← Continue to Python method
    
    if path.exists():  # ← If folder still exists (Windows delete failed)
        shutil.rmtree(path, ignore_errors=True)  # ← Use Python's rmtree to delete recursively
    
    # ← Create message based on whether deletion succeeded
    msg = (f"Could not fully delete {path}\n(OneDrive still syncing — delete manually)"  # ← If OneDrive is syncing
           if path.exists() else f"Results deleted:\n{path}")  # ← Or success message
    
    if not path.exists():  # ← If deletion succeeded
        _last_run_dir = None  # ← Clear the global variable
    
    return _log_html([], msg), gr.update(visible=False)  # ← Return message and hide buttons


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Native folder browser dialog using tkinter (Windows/Mac/Linux compatible)
# ─────────────────────────────────────────────────────────────────────────────

def browse_output_dir(current: str) -> str:
    # ← Open a native folder browser dialog and return the chosen path
    """Open a native folder-picker dialog and return the chosen path."""
    try:  # ← Wrap in try-except in case tkinter is not available
        import tkinter as tk  # ← Import tkinter for native dialogs
        from tkinter import filedialog  # ← Import file dialog module
        
        root = tk.Tk()  # ← Create a root window
        root.withdraw()  # ← Hide the root window (we only want the dialog)
        root.wm_attributes("-topmost", True)  # ← Make dialog appear on top of other windows
        
        initial = current.strip() if current.strip() else str(ROOT)  # ← Use current dir or ROOT as default
        
        folder = filedialog.askdirectory(  # ← Show folder picker dialog
            title="Select folder to save test results",  # ← Dialog title
            initialdir=initial,  # ← Start in this directory
        )
        
        root.destroy()  # ← Clean up the root window
        
        if folder:  # ← If user selected a folder (not cancelled)
            return folder  # ← Return the chosen folder path
    except Exception:  # ← If tkinter is unavailable or something fails
        pass  # ← Silently ignore and fall through
    
    return current  # ← Return unchanged if cancelled or tkinter unavailable


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: CSS styling rules for Gradio UI elements (status box, buttons, layout)
# ─────────────────────────────────────────────────────────────────────────────

# ← CSS styling rules for Gradio components
_CSS = """
#status-box textarea {
    font-size: 1.15em;                  /* ← Make status text larger */
    font-weight: bold;                  /* ← Make status text bold */
    text-align: center;                 /* ← Center-align status text */
}
#save-row { margin-top: 10px; }         /* ← Add space above save/delete buttons */
"""

# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Constructs the web interface using Gradio framework
# ─────────────────────────────────────────────────────────────────────────────

def build_gui() -> gr.Blocks:
    # ← Build the Gradio web interface with all controls and layouts
    all_boards     = get_available_boards()  # ← Get list of all discovered boards
    default_board  = all_boards[0] if all_boards else None  # ← Use first board as default
    default_suites = get_suites_for_board(default_board) if default_board else []  # ← Get suites for default board
    default_suite  = default_suites[0] if default_suites else None  # ← Use first suite as default

    with gr.Blocks(  # ← Create the main Gradio interface
        title="Digantara Test Automation",  # ← Browser tab title
        theme=gr.themes.Base(primary_hue="blue", neutral_hue="slate"),  # ← Set color theme (blue primary, slate neutral)
        css=_CSS,  # ← Apply custom CSS styling
    ) as demo:  # ← Store interface as 'demo' for later use

        # ← Display title and instructions
        gr.Markdown(
            "# Digantara Test Automation Framework\n"  # ← Main title
            "Select a board and test suite, configure options, then click **Run**."  # ← Instructions
        )

        with gr.Row():  # ← Create horizontal layout for left and right panels

            # ── Left panel (Controls) ─────────────────────────────────────────
            with gr.Column(scale=1, min_width=10):  # ← Left column with controls (1x width, min 300px)

                # ← Board selection dropdown
                board_dd = gr.Dropdown(
                    choices=all_boards, value=default_board,  # ← Populate with boards
                    label="Board Under Test",  # ← Label above dropdown
                    info="Auto-detected from *_config.json files",  # ← Helpful info text
                )
                
                # ← Test suite selection dropdown
                suite_dd = gr.Dropdown(
                    choices=default_suites, value=default_suite,  # ← Populate with default suites
                    label="Test Suite",  # ← Label above dropdown
                    info="Only suites with a config for the selected board appear here",  # ← Helpful info
                )

                # ← Required instruments sidebar widget
                instr_html = gr.HTML(value="")  # ← Will be populated dynamically when board/suite changes

                # ← Test mode dropdown (only visible for certain suites)
                mode_dd = gr.Dropdown(
                    choices=[], label="Test Mode", visible=False,  # ← Hidden by default, shown when suite supports modes
                )
                
                # ← Voltage rails selection (only visible for certain suites)
                rails_cb = gr.CheckboxGroup(
                    choices=[], label="Rails to Test", visible=False,  # ← Hidden by default, shown when suite supports rails
                )

                # ← Output directory section
                gr.Markdown("---")  # ← Visual separator
                gr.Markdown("**Output Directory**")  # ← Section title

                with gr.Row():  # ← Horizontal layout for textbox and button
                    output_tb = gr.Textbox(
                        value="gui_results",  # ← Default output directory
                        placeholder="Folder path for results…",  # ← Placeholder text
                        show_label=False,  # ← Don't show label (it's in Markdown above)
                        lines=1,  # ← Single line textbox
                        scale=4,  # ← Takes 4x space
                    )
                    browse_btn = gr.Button("Browse…", scale=1, size="sm")  # ← Browse button (1x space, small size)

                # ← Run/Stop buttons
                gr.Markdown("---")  # ← Visual separator

                with gr.Row():  # ← Horizontal layout for buttons
                    run_btn  = gr.Button("Run",  variant="primary", size="lg")  # ← Run button (primary color, large)
                    stop_btn = gr.Button("Stop", variant="stop",    size="lg")  # ← Stop button (stop color, large)

            # ── Right panel (Output & Status) ──────────────────────────────────
            with gr.Column(scale=2):  # ← Right column (2x width of left column)

                # ← Status display
                status_tb = gr.Textbox(
                    label="Status", value="Ready",  # ← Label and initial value
                    interactive=False, lines=1,  # ← Read-only, single line
                    elem_id="status-box",  # ← CSS ID for styling
                )

                # ← Test output log (HTML div with auto-scrolling)
                # gr.HTML for the log — gives full scroll control via inline JS
                log_html = gr.HTML(
                    value=_log_html([], "(No output yet)"),  # ← Initial empty log message
                    label="Test Output",  # ← Label
                )

                # ← Send box for answering in-test prompts
                # Send box — unblocks any in-test input() prompts
                with gr.Row():  # ← Horizontal layout
                    send_tb = gr.Textbox(
                        placeholder="Type a response and click Send  "  # ← Helpful placeholder
                                    "(leave blank = press ENTER / continue probe prompt)",
                        label="Send to test",  # ← Label
                        lines=1, scale=5,  # ← Single line, takes 5x space
                    )
                    send_btn = gr.Button("Send ↵", scale=1, size="sm")  # ← Send button (1x space, small)

                # ← Save/Delete buttons (hidden until test completes)
                # Save / Delete — appears only after a test finishes
                with gr.Row(elem_id="save-row", visible=False) as save_row:  # ← Horizontal row, initially hidden
                    keep_btn   = gr.Button("Keep Results ✓",  variant="primary")  # ← Keep button (primary color)
                    delete_btn = gr.Button("Delete Results ✗", variant="stop")  # ← Delete button (stop color)

        # ── Event handlers and wiring ──────────────────────────────────────────

        # ← Handler function when board dropdown changes
        def on_board_change(board):
            # ← Update suite dropdown when board selection changes
            suites = get_suites_for_board(board)  # ← Get suites available for this board
            new_suite = suites[0] if suites else None  # ← Select first suite as default
            return (
                gr.update(choices=suites, value=new_suite),  # ← Update suite dropdown
                _instrument_info_html(board, new_suite),  # ← Update instruments sidebar
            )

        # ← Handler function when suite dropdown changes
        def on_suite_change(board, suite):
            # ← Update mode and rails dropdowns when suite selection changes
            if not board or not suite:  # ← If board or suite not selected
                return (gr.update(choices=[], value=None,  visible=False),  # ← Clear mode dropdown
                        gr.update(choices=[], value=[],    visible=False),  # ← Clear rails checkboxes
                        "")  # ← Clear instruments sidebar
            
            modes  = SUITE_MODES.get(suite)  # ← Get available modes for this suite
            cfgp   = get_config_path(board, suite)  # ← Get config path
            rails  = get_rails_for_suite(suite, cfgp) if cfgp else None  # ← Get available rails from config
            return (
                gr.update(choices=modes or [], value=modes[0] if modes else None,  # ← Update modes dropdown
                          visible=bool(modes)),  # ← Show only if suite has modes
                gr.update(choices=rails or [], value=rails or [],  # ← Update rails checkboxes
                          visible=bool(rails)),  # ← Show only if suite has rails
                _instrument_info_html(board, suite),  # ← Update instruments sidebar
            )

        # ← Wire board dropdown change event to handler
        board_dd.change(on_board_change,  inputs=board_dd,            outputs=[suite_dd, instr_html])
        
        # ← Wire suite dropdown change event to handler
        suite_dd.change(on_suite_change,  inputs=[board_dd, suite_dd], outputs=[mode_dd, rails_cb, instr_html])

        # ← Wire browse button to folder picker
        browse_btn.click(browse_output_dir, inputs=output_tb, outputs=output_tb)

        # ← Wire Run button to test launcher
        run_btn.click(
            fn=launch_test,  # ← Call launch_test function
            inputs=[board_dd, suite_dd, mode_dd, rails_cb, output_tb],  # ← Pass these inputs to function
            outputs=[log_html, status_tb, save_row],  # ← Update these outputs from function
        )
        
        # ← Wire Stop button to test stopper
        stop_btn.click(fn=stop_test, outputs=log_html)  # ← Update log with stop message

        # ← Wire Send button to input handler
        send_btn.click(fn=send_to_test, inputs=send_tb, outputs=send_tb)  # ← Send input and clear box
        
        # ← Wire textbox Enter key to input handler (same function)
        send_tb.submit( fn=send_to_test, inputs=send_tb, outputs=send_tb)  # ← Send on Enter key

        # ← Wire Keep Results button
        keep_btn.click(  fn=keep_results,   outputs=[log_html, save_row])  # ← Show kept message and hide buttons
        
        # ← Wire Delete Results button
        delete_btn.click(fn=delete_results, outputs=[log_html, save_row])  # ← Delete and hide buttons

        # ← Initialize interface when page loads
        demo.load(fn=on_suite_change, inputs=[board_dd, suite_dd],  # ← Call suite change handler with default values
                  outputs=[mode_dd, rails_cb, instr_html])  # ← Update these outputs

    return demo  # ← Return the completed interface


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Entry point - initializes and launches the web application
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # ← Script entry point (runs when file is executed directly)
    print("Digantara Test Automation GUI")  # ← Print startup message
    print(f"Project root : {ROOT}")  # ← Print the project folder location
    boards = get_available_boards()  # ← Scan for available boards
    print(f"Boards found : {', '.join(boards) if boards else 'none'}")  # ← Print discovered boards
    build_gui().launch(inbrowser=True)  # ← Build the interface and launch in default web browser
