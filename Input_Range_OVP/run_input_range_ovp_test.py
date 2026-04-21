
# Tell the operating system to run this file using Python 3 if executed directly from a terminal
#!/usr/bin/env python3
"""
Input Range and OVP Test — Runner

Run this script to execute the full test sequence.

Usage:
    python run_input_range_ovp_test.py                  # Interactive mode selector
    python run_input_range_ovp_test.py --mode full       # Skip selector, run full test
    python run_input_range_ovp_test.py --mode fixed      # Skip selector, fixed Vin only
    python run_input_range_ovp_test.py --mode sweep      # Skip selector, sweep only
    python run_input_range_ovp_test.py --output PATH     # Override output directory
    python run_input_range_ovp_test.py --verbose         # Verbose instrument logging
"""

# Load the 'sys' library which allows the program to exit cleanly and manage module search paths
import sys
# Load the 'argparse' library which handles reading command-line flags the engineer types when launching the script
import argparse
# Load the 'logging' library which controls how debug and warning messages are written to the console
import logging
# Load the 'Path' class from 'pathlib' which makes working with file and folder paths easier across operating systems
from pathlib import Path

# Add the parent folder of this script to Python's search path so shared modules can be found
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add the folder that contains this script to Python's search path so local test modules can be imported
sys.path.insert(0, str(Path(__file__).parent))



# Define a helper function that switches on colour (ANSI) support in the Windows terminal
def _enable_ansi():
    """Enable ANSI escape codes on Windows 10+."""
    # Begin a block that tries to turn on ANSI colour codes — if it fails, the program carries on without colour
    try:
        # Import the 'ctypes' library which lets Python call low-level Windows operating system functions
        import ctypes
        # Call the Windows API to put the console into a mode that understands colour escape codes
        ctypes.windll.kernel32.SetConsoleMode(
            # Get a handle to the standard output stream (the console window), then set its mode to 7 (enables ANSI)
            ctypes.windll.kernel32.GetStdHandle(-11), 7
        )
    # If anything goes wrong (e.g. not running on Windows or no console attached), silently ignore the error
    except Exception:
        # Do nothing — the program will simply run without colour support
        pass



# Define a helper function that configures how detailed the log messages printed to the console will be
def _setup_logging(verbose: bool):
    # If the engineer passed --verbose, use DEBUG level (very detailed); otherwise only show WARNINGs and above
    level = logging.DEBUG if verbose else logging.WARNING
    # Apply the chosen log level and set the timestamp + message format for every log line
    logging.basicConfig(
        # Pass the chosen logging level so that only messages at that level or above are shown
        level=level,
        # Define the layout of each log message: time, severity label, module name, then the message text
        format='%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
        # Format the timestamp as hours:minutes:seconds
        datefmt='%H:%M:%S'
    )



# Define the function that displays an on-screen menu so the engineer can pick which test mode to run
def interactive_mode_selector():
    """
    Interactive test mode selector.

    Controls:
        UP / DOWN arrows  - Move between options
        TAB or SPACE      - Select the highlighted option
        ENTER             - Confirm and run
        Q or ESC          - Cancel

    Returns:
        "full", "fixed", or "sweep" — or None if cancelled.
    """
    # Import 'msvcrt' which allows the program to read individual key presses from the keyboard on Windows
    import msvcrt

    # Switch on ANSI colour support so the menu renders correctly in the Windows terminal
    _enable_ansi()

    # Build the list of test-mode choices that will appear in the on-screen menu
    options = [
        # First option: run the full test suite (both fixed-voltage tests and the sweep)
        {
            # Internal key used by the rest of the code to identify this choice
            'key':   'full',
            # Human-readable name shown on screen
            'label': 'Full Test',
            # Short description of what this mode does
            'desc':  'Fixed Vin tests  +  Sweep  (complete characterisation)',
        },
        # Second option: only apply the fixed input voltages and measure output, no sweep
        {
            # Internal key for the fixed-voltage-only mode
            'key':   'fixed',
            # Human-readable name shown on screen
            'label': 'Fixed Vin Only',
            # Short description of what this mode does
            'desc':  'Apply configured voltages, read Vout, skip sweep',
        },
        # Third option: only run the voltage ramp sweep, skip the fixed-voltage tests
        {
            # Internal key for the sweep-only mode
            'key':   'sweep',
            # Human-readable name shown on screen
            'label': 'Sweep Only',
            # Short description of what this mode does
            'desc':  'Vin ramp 0 -> Vmax -> 0 with continuous DMM capture, skip fixed tests',
        },
    ]

    # Track which option is currently ticked (radio-button selection), starting at the first item
    selected = 0   # index of currently selected option (radio button)
    # Track which row the highlight (cursor arrow) is sitting on, starting at the first row
    cursor   = 0   # index of highlighted row

    # Define an inner function that builds the list of text lines to display in the menu
    def render():
        # Start with an empty list that will collect each line of the menu display
        lines = []
        # Add a blank line at the top for visual breathing room
        lines.append("")
        # Add the menu title
        lines.append("  TEST MODE SELECTION")
        # Add a horizontal divider made of '=' characters
        lines.append("  " + "=" * 62)
        # Add the keyboard shortcut hint so the engineer knows how to navigate
        lines.append("  UP/DOWN: Navigate | TAB: Select | ENTER: Run | Q: Quit")
        # Add a blank line to separate the header from the option rows
        lines.append("")
        # Loop through every available test-mode option to build its display row
        for i, opt in enumerate(options):
            # Show a filled radio button '(X)' if this option is currently selected, otherwise show empty '( )'
            marker = "(X)" if i == selected else "( )"
            # Show '>>' next to the row the cursor is on, otherwise indent with spaces
            arrow  = ">>" if i == cursor else "  "
            # Combine the arrow, radio button, label, and description into a single formatted line
            lines.append(f"  {arrow} {marker}  {opt['label']:<18}  {opt['desc']}")
        # Add a blank line after the option rows
        lines.append("")
        # Show a summary line at the bottom telling the engineer which mode is currently selected
        lines.append(f"  Mode: {options[selected]['label']}")
        # Return the completed list of display lines
        return lines

    # Generate the initial set of menu lines ready for printing
    display_lines = render()
    # Print each line of the menu to the terminal one by one
    for line in display_lines:
        print(line)
    # Force the terminal output buffer to flush immediately so the menu appears right away
    sys.stdout.flush()

    # Enter an infinite loop that keeps waiting for key presses until the engineer confirms or cancels
    while True:
        # Read a single key press from the keyboard without waiting for the engineer to press Enter
        key = msvcrt.getch()

        # If the engineer pressed ENTER, confirm the current selection and return its key string
        if key == b'\r':                          # ENTER — confirm
            # Print a blank line to leave space after the menu before the next output
            print()
            # Return the internal key string (e.g. 'full', 'fixed', or 'sweep') for the selected option
            return options[selected]['key']

        # If the engineer pressed TAB or SPACE, tick the option that the cursor is currently on
        elif key in (b'\t', b' '):                # TAB / SPACE — select current
            # Set the selected (ticked) option to whichever row the cursor is sitting on
            selected = cursor

        # If the first byte of an arrow-key sequence is detected, read the second byte to identify which arrow
        elif key in (b'\xe0', b'\x00'):           # Arrow key prefix
            # Read the second byte of the two-byte arrow-key code
            key2 = msvcrt.getch()
            # If the second byte means UP arrow, move the cursor up one row (wrapping around to the bottom)
            if key2 == b'H':                      # UP
                cursor = (cursor - 1) % len(options)
            # If the second byte means DOWN arrow, move the cursor down one row (wrapping around to the top)
            elif key2 == b'P':                    # DOWN
                cursor = (cursor + 1) % len(options)

        # If the engineer pressed Q, the letter Q (uppercase), or the Escape key, cancel and exit the menu
        elif key in (b'q', b'Q', b'\x1b'):        # Q / ESC — cancel
            # Print a message to let the engineer know the selection was cancelled
            print("\n  Cancelled.")
            # Return None to signal to the calling code that no mode was chosen
            return None

        # If any other unrecognised key was pressed, ignore it and go back to waiting
        else:
            continue

        # Redraw in-place
        # Regenerate the menu lines to reflect any change in cursor position or selection
        display_lines = render()
        # Move the terminal cursor up by the same number of lines as the menu so it can be redrawn over itself
        sys.stdout.write(f"\033[{len(display_lines)}A")
        # Reprint each line of the menu, clearing whatever was there before with '\033[2K'
        for line in display_lines:
            sys.stdout.write(f"\033[2K{line}\n")
        # Flush the output buffer so the updated menu appears on screen immediately
        sys.stdout.flush()



# Define the function that prints step-by-step physical wiring and setup instructions for the engineer
def print_setup_instructions(instr: dict, settings: dict, p: dict):
    """
    Print step-by-step physical setup instructions using the actual config values.
    Called after the config summary, before the mode selector.
    """
    # Read which PSU output channel to use from the instrument settings (defaulting to channel 1)
    ch          = settings.get("psu_channel", 1)
    # Read the maximum current limit the PSU should enforce, or use '?' if not configured
    i_lim       = p.get("psu_current_limit_a", "?")
    # Read the over-voltage protection threshold that will trip the PSU, or use '?' if not configured
    ovp         = p.get("psu_ovp_level_v", "?")
    # Read the highest voltage that will be applied during the sweep ramp, or use '?' if not configured
    sweep_max   = p.get("sweep_max_v", "?")
    # Read the VISA address string for the power supply instrument, or use '?' if not configured
    psu_addr    = instr.get("psu", "?")
    # Read the VISA address string for the digital multimeter, or use '?' if not configured
    dmm_addr    = instr.get("dmm", "?")

    # Print a blank line before the setup instructions block for visual separation
    print()
    # Print the top border of the instructions box
    print("=" * 70)
    # Print the heading that tells the engineer these are setup steps to complete before starting
    print("  SETUP INSTRUCTIONS — Complete these steps before starting")
    # Print the bottom border of the instructions box heading
    print("=" * 70)
    # Print a blank line after the heading
    print()
    # Print step 1: remind the engineer to power off the device under test before touching any wires
    print("  [ 1 ]  POWER OFF the DUT board before making any connections.")
    # Print a blank line after step 1
    print()
    # Print step 2 heading, showing which PSU channel to wire to
    print(f"  [ 2 ]  PSU wiring  (Keithley PSU, CH{ch}):")
    # Print the instruction for connecting the positive (red) lead to the DUT's positive input
    print(f"           + terminal  (red lead)    ->  DUT VIN  (positive input)")
    # Print the instruction for connecting the negative (black) lead to the DUT's ground/return
    print(f"           - terminal  (black lead)  ->  DUT GND  (input ground / return)")
    # Print the current limit and OVP settings that the software will apply to the PSU
    print(f"           The PSU will be limited to {i_lim} A with OVP set to {ovp} V.")
    # Print the voltage range the sweep will ramp through so the engineer knows the maximum hazard voltage
    print(f"           Voltage will ramp from 0 V up to {sweep_max} V during the sweep.")
    # Print a blank line after step 2
    print()
    # Print step 3 heading for the digital multimeter wiring
    print("  [ 3 ]  DMM wiring  (Keithley DMM6500):")
    # Explain that the software will prompt for DMM probe connection at the right time, so wait for that
    print("           You will be prompted to connect the DMM probes AFTER the")
    # Advise the engineer to keep the DMM probes safe at ground or disconnected for now
    print("           instruments connect. For now, leave the DMM probes at GND")
    # Warn the engineer not to connect DMM probes to the output yet
    print("           or disconnected — do NOT connect them to VOUT yet.")
    # Print a blank line after step 3
    print()
    # Print step 4 heading for USB connections between the instruments and the PC
    print("  [ 4 ]  USB connections to this PC:")
    # Show the configured VISA address for the power supply so the engineer can verify it
    print(f"           PSU  ->  {psu_addr}")
    # Show the configured VISA address for the DMM so the engineer can verify it
    print(f"           DMM  ->  {dmm_addr}")
    # Tell the engineer where to edit the addresses if they look wrong
    print("           If either address looks wrong, edit input_range_ovp_config.json")
    # Tell the engineer to restart the script after editing the config
    print("           and restart the script.")
    # Print a blank line after step 4
    print()
    # Print step 5: instruct the engineer to power on instruments but leave the DUT off
    print("  [ 5 ]  Power ON the PSU and DMM. Leave the DUT powered off —")
    # Clarify that the software will control when voltage is applied
    print("           the PSU will apply voltage when the test begins.")
    # Print a blank line after step 5
    print()
    # Print step 6: ask the engineer to check the PSU front panel before proceeding
    print("  [ 6 ]  Verify on the PSU front panel:")
    # Check that the output button for the correct channel is not lit (output is off)
    print(f"           - CH{ch} output is OFF (output button not lit)")
    # Check that there are no error indicators showing on the PSU screen
    print(f"           - No over-voltage or error indicators are showing")
    # Print a blank line after step 6
    print()
    # Print step 7: warn the engineer not to touch anything once the test is running
    print("  [ 7 ]  Do NOT touch the board, probes, or leads once the test starts.")
    # Reinforce the safety warning by stating the maximum voltage that will be applied
    print("           Voltages up to", sweep_max, "V will be applied to the DUT.")
    # Print a blank line after step 7
    print()
    # Print the closing border of the setup instructions box
    print("=" * 70)
    # Print a trailing blank line for visual separation before the next section
    print()



# Define the function that asks the engineer where to save test result files
def prompt_output_directory(cfg_output_dir: str = None):
    """
    Prompt user to select or confirm output directory for test results.

    Returns:
        str: The output directory path (either default or custom)
    """
    # Determine the default save path: use the value from the config file, or fall back to a sensible folder name
    default_path = cfg_output_dir or "input_range_ovp_results"

    # Print a blank line before the directory selection box
    print()
    # Print the top border of the output directory selection box
    print("=" * 70)
    # Print the section heading
    print("  OUTPUT DIRECTORY SELECTION")
    # Print the bottom border of the section heading
    print("=" * 70)
    # Print a blank line after the heading
    print()
    # Show the engineer what the default save path is (taken from the config file)
    print(f"  Default path (from config): {default_path}")
    # Print a blank line before the options list
    print()
    # Print the label for the options list
    print("  Options:")
    # Print option 1: accept the default path without typing anything
    print("    [1] Use default path")
    # Print option 2: type a custom path manually
    print("    [2] Enter custom path")
    # Print a blank line after the options list
    print()

    # Keep asking until the engineer gives a valid response
    while True:
        # Ask the engineer to type 1 or 2 and remove any leading/trailing whitespace from the input
        choice = input("  Select option (1 or 2): ").strip()

        # If the engineer chose option 1, use the default path from the config
        if choice == "1":
            # Store the default path as the chosen output directory
            selected_path = default_path
            # Confirm to the engineer which path will be used
            print(f"  Using: {selected_path}")
            # Print a blank line after the confirmation message
            print()
            # Return the chosen path so the rest of the program knows where to save files
            return selected_path
        # If the engineer chose option 2, ask them to type a custom folder path
        elif choice == "2":
            # Ask the engineer to type the custom path and remove surrounding whitespace
            custom_path = input("  Enter output directory path: ").strip()
            # If the engineer pressed Enter without typing anything, show an error and ask again
            if not custom_path:
                # Tell the engineer the path cannot be empty
                print("  ERROR: Path cannot be empty. Try again.")
                # Go back to the top of the loop to ask again
                continue
            # Store the custom path the engineer typed as the chosen output directory
            selected_path = custom_path
            # Confirm to the engineer which path will be used
            print(f"  Using: {selected_path}")
            # Print a blank line after the confirmation message
            print()
            # Return the custom path so the rest of the program knows where to save files
            return selected_path
        # If the engineer typed anything other than 1 or 2, explain the valid choices and ask again
        else:
            # Tell the engineer their input was not recognised
            print("  Invalid choice. Please enter 1 or 2.")



# Define the function that prints the large banner displayed at the very start of the script
def print_banner():
    # Print a blank line before the banner
    print()
    # Print the top border of the banner box
    print("=" * 70)
    # Print the test name as the main banner title
    print("  INPUT RANGE AND OVP TEST")
    # Print a brief description of what this test characterises
    print("  Characterises DUT input behaviour, operating range, and protections")
    # Print the bottom border of the banner title area
    print("=" * 70)
    # Print a blank line after the title
    print()
    # Print the names of the two instruments used in this test
    print("  Instruments : Keithley Power Supply  +  Keithley DMM6500")
    # Print a blank line before the test phases list
    print()
    # Print the heading for the numbered test phase list
    print("  Test phases:")
    # Print phase 1: asking the engineer to physically connect DMM probes to the DUT output
    print("    1. Prompt operator to connect DMM probes on DUT output")
    # Print phase 2: applying fixed known voltages and checking the output passes or fails tolerance
    print("    2. Fixed Vin tests — apply configured voltages, read Vout, Pass/Fail")
    # Print phase 3: ramping the input voltage up and down while the DMM continuously captures readings
    print("    3. Sweep test     — ramp 0 -> Vmax -> 0, capture DMM, generate plots")
    # Print phase 4: saving all result files into a timestamped folder
    print("    4. Save reports (CSV + JSON + TXT summary) in a timestamped run folder")
    # Print a blank line after the phase list
    print()
    # Print a hint telling the engineer which file to edit if they want to change any test settings
    print("  Edit  input_range_ovp_config.json  to change addresses, voltages,")
    # Continue the hint on the next line listing what else can be changed in the config
    print("  step size, dwell time, and DMM read interval.")
    # Print a blank line before the closing border
    print()
    # Print the closing border of the banner
    print("=" * 70)



# Define the main function that runs everything in the correct order when the script is launched
def main():
    # Force UTF-8 output so Unicode characters (arrows, tick marks, etc.) print correctly on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    # Enable ANSI colour codes in the terminal so any coloured output renders correctly from the start
    _enable_ansi()

    # Create an argument parser so the script can read command-line flags the engineer typed
    parser = argparse.ArgumentParser(
        # Short description of the script shown in the --help output
        description="Input Range and OVP Test Runner",
        # Use a formatter that preserves line breaks in the help text epilog
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # Provide usage examples that appear at the bottom of the --help output
        epilog="""
Examples:
  python run_input_range_ovp_test.py
  python run_input_range_ovp_test.py --mode full
  python run_input_range_ovp_test.py --mode fixed
  python run_input_range_ovp_test.py --mode sweep
  python run_input_range_ovp_test.py --output C:/results/pwr_test
  python run_input_range_ovp_test.py --verbose
        """
    )
    # Register the --mode flag that lets the engineer skip the interactive menu and go straight to a specific mode
    parser.add_argument(
        # The flag name and the three allowed values the engineer can pass
        '--mode', choices=['full', 'fixed', 'sweep'], default=None,
        # Help text shown in --help output explaining what this flag does
        help='Test mode: full / fixed / sweep  (default: interactive selector)'
    )
    # Register the --output flag that lets the engineer override the results folder path from the command line
    parser.add_argument(
        # The flag name and that it expects a string value (folder path)
        '--output', type=str, default=None,
        # Help text explaining what this flag does and what the default is
        help='Base directory for results (default: path from input_range_ovp_config.json)'
    )
    # Register the --verbose flag which, when present, turns on detailed instrument-level debug logging
    parser.add_argument(
        # The flag name; 'store_true' means it acts as an on/off switch — no value needed after the flag
        '--verbose', action='store_true',
        # Help text explaining what this flag does
        help='Enable verbose instrument-level logging'
    )
    # Register the --headless flag used by the Gradio GUI and CI pipelines to bypass all interactive
    # prompts — output directory comes from the config default, start confirmation is skipped, and
    # results are always saved automatically.
    parser.add_argument(
        '--headless', action='store_true',
        help='Skip all interactive prompts (GUI / CI mode). Auto-saves results.'
    )

    # Parse all the flags the engineer typed and store the results in the 'args' object
    args = parser.parse_args()
    # Configure the logging system using the verbosity level the engineer requested
    _setup_logging(args.verbose)

    # Display the big banner at the top of the console so the engineer knows the test script has started
    print_banner()

    # Scan the VISA bus and show which required instruments are connected before proceeding
    try:
        from visa_auto_detect import show_instrument_status
        show_instrument_status([
            ("Power Supply (PSU)", "power_supply"),
            ("DMM",                "dmm"),
        ])
    except ImportError:
        pass

    # Attempt to import the main test class and related objects from the test module
    try:
        # Import the test runner class, the sweep result data structure, and the loaded config dictionary
        from input_range_ovp_test import InputRangeOVPTest, SweepResult, _CFG
    # If the import fails (e.g. the file is missing or has a syntax error), catch the error
    except ImportError as e:
        # Tell the engineer exactly which import error occurred
        print(f"\n  ERROR: Could not import test module: {e}")
        # Give the engineer a hint about what to check
        print("  Make sure input_range_ovp_test.py is in the same directory.")
        # Exit the script with code 1 to signal that something went wrong
        return 1

    # Display config summary
    # Extract the instrument address settings (PSU and DMM VISA addresses) from the loaded config
    instr    = _CFG.get("instrument_addresses", {})
    # Extract the instrument behaviour settings (e.g. PSU channel number) from the loaded config
    settings = _CFG.get("instrument_settings", {})
    # Extract the test parameter settings (voltages, current limits, sweep steps, etc.) from the loaded config
    p        = _CFG.get("test_parameters", {})

    # Print the heading for the configuration summary section
    print("  Configuration summary:")
    # Print the VISA address of the power supply so the engineer can confirm it is correct
    print(f"    PSU address    : {instr.get('psu')}")
    # Print the VISA address of the DMM so the engineer can confirm it is correct
    print(f"    DMM address    : {instr.get('dmm')}")
    # Print which output channel on the PSU will be used during the test
    print(f"    PSU channel    : CH{settings.get('psu_channel', 1)}")
    # Print the current limit that will be programmed into the PSU
    print(f"    Current limit  : {p.get('psu_current_limit_a', '?')} A")
    # Print a blank line after the instrument summary
    print()
    # Print the heading for the fixed-voltage test points section
    print("  Fixed Vin test points:")
    # Loop through every fixed-voltage test point defined in the test class and print its expected values
    for pt in InputRangeOVPTest.FIXED_VIN_TESTS:
        # Print the input voltage, expected output voltage, and acceptable tolerance for this test point
        print(f"    Vin={pt.vin_v:.1f} V  ->  expected Vout={pt.expected_vout_v:.1f} V"
              f"  +/-{pt.vout_tolerance_v:.2f} V")
    # Print a blank line after the fixed-voltage test points
    print()
    # Print the heading for the sweep summary
    print("  Sweep:")
    # Print the start, maximum, and return voltages of the sweep ramp
    print(f"    {p.get('sweep_start_v', 0):.0f} V  ->  {p.get('sweep_max_v', 30):.0f} V  ->  {p.get('sweep_start_v', 0):.0f} V")
    # Print the step size, dwell time at each step, and how often the DMM takes a reading during the sweep
    print(f"    Step: {p.get('sweep_step_v', '?')} V  |  "
          f"Dwell: {p.get('step_dwell_time_s', '?')} s  |  "
          f"DMM interval: {p.get('dmm_read_interval_s', '?')} s")
    # Print a blank line after the sweep summary
    print()

    # ── Setup instructions ────────────────────────────────────────────────────
    # Call the function that prints detailed physical wiring instructions for the engineer
    print_setup_instructions(instr, settings, p)

    # ── Mode selection ────────────────────────────────────────────────────────
    # Check whether the engineer specified a mode on the command line (bypassing the interactive menu)
    if args.mode:
        # Use the mode the engineer specified via the --mode flag directly
        mode = args.mode
        # Print a confirmation showing which mode was selected and that it came from the command-line flag
        print(f"  Mode: {mode}  (from --mode flag)")
        # Print a blank line after the mode confirmation
        print()
        # In headless mode (GUI / CI) skip the connection confirmation prompt and proceed directly
        if not args.headless:
            # Ask the engineer to confirm that all physical connections are ready before the test begins
            response = input("  All connections made? Press ENTER to start (or 'q' to quit): ").strip().lower()
            # If the engineer typed q, quit, or exit, cancel the run gracefully
            if response in ('q', 'quit', 'exit'):
                # Tell the engineer the test was cancelled
                print("  Cancelled.")
                # Return 0 to signal a clean (non-error) exit
                return 0
    # If no --mode flag was given, check headless before falling through to the interactive menu
    elif args.headless:
        # Headless mode with no --mode flag — default to 'full' so the GUI always has a runnable action
        mode = 'full'
        print("  Headless mode: defaulting to --mode full")
        print()
    # If no --mode flag was given and not headless, show the interactive menu so the engineer can choose
    else:
        # Display the on-screen menu and wait for the engineer to pick a mode; store the returned choice
        mode = interactive_mode_selector()
        # If the engineer cancelled the menu (pressed Q or Escape), exit the script cleanly
        if mode is None:
            # Return 0 to signal a clean (non-error) exit
            return 0
        # Print which mode the engineer selected so there is a clear record in the console output
        print(f"  Running: {mode}")

    # ── Output directory selection ────────────────────────────────────────────
    # Check if the engineer supplied a results folder path via the --output command-line flag
    output_dir = args.output
    # If no --output flag was given, determine the output path
    if output_dir is None:
        # Read the output directory setting from the loaded config file
        cfg_output_path = _CFG.get("output_dir", {})
        # Handle the case where 'output_dir' in the config is a dictionary with a 'path' key, or just a plain string
        cfg_output_dir = (
            cfg_output_path.get("path", "input_range_ovp_results")
            if isinstance(cfg_output_path, dict)
            else str(cfg_output_path)
        )
        if args.headless:
            # In headless mode use the config default directly — no interactive prompt
            output_dir = cfg_output_dir
            print(f"  Output directory: {output_dir}")
            print()
        else:
            # Show the interactive directory prompt and store the path the engineer confirms or types
            output_dir = prompt_output_directory(cfg_output_dir)

    # ── Create test instance ──────────────────────────────────────────────────
    # Create a new test runner object, telling it which folder to save results into
    test = InputRangeOVPTest(output_dir=output_dir)

    # ── Run selected mode ─────────────────────────────────────────────────────
    # Set the overall success flag to False until the test proves otherwise
    success = False

    # If the engineer chose 'fixed' mode, run only the fixed-voltage point tests
    if mode == 'fixed':
        # Print a message confirming that only the fixed-voltage tests will be run
        print("\n  Running Fixed Vin tests only.")
        # Try to connect to both instruments; if connection fails, exit immediately with error code 1
        if not test._connect_instruments():
            return 1
        # Run the fixed-voltage tests and clean up instruments whether they pass or fail
        try:
            # Ask the engineer to physically connect the DMM probes to the DUT output before measuring
            test._prompt_probe_setup()
            # Run all the fixed-voltage point tests and store the individual pass/fail results
            fixed_results = test.run_fixed_vin_tests()
            # Create a placeholder sweep result object marked as 'NOT_RUN' since the sweep was skipped
            empty_sweep = SweepResult(
                # Label the voltage range as not applicable since no sweep was performed
                vin_range="N/A", vout_v=0.0,
                # Use the configured expected output voltage even though no sweep was run
                expected_vout_v=p.get("sweep_expected_vout_v", 0.0),
                # Mark the sweep portion of the report as not executed
                status="NOT_RUN"
            )
            # Generate and save the test reports using the fixed results and the empty sweep placeholder
            verdict = test._generate_reports(fixed_results, empty_sweep)
            # Set success to True only if the overall verdict string from the reports is "PASS"
            success = (verdict == "PASS")
        # Always disconnect from the instruments when done, even if an error occurred during the tests
        finally:
            # Release the connections to the PSU and DMM so they are left in a safe state
            test._disconnect_instruments()

    # If the engineer chose 'sweep' mode, run only the voltage ramp sweep test
    elif mode == 'sweep':
        # Print a message confirming that only the sweep test will be run
        print("\n  Running Sweep test only.")
        # Try to connect to both instruments; if connection fails, exit immediately with error code 1
        if not test._connect_instruments():
            return 1
        # Run the sweep test and clean up instruments whether the test passes or fails
        try:
            # Ask the engineer to physically connect the DMM probes to the DUT output before the sweep
            test._prompt_probe_setup()
            # Execute the sweep ramp and collect all the voltage readings into a result object
            sweep_result = test.run_sweep_test()
            # Inform the engineer that the plot images are being generated
            print("\n  Generating plots...")
            # Generate and save the sweep plots (graphs of Vin vs Vout over the ramp)
            test._plot_sweep(sweep_result)
            # Inform the engineer that the report files are being written
            print("\n  Writing reports...")
            # Generate and save the CSV, JSON, and text summary reports (passing an empty fixed-results list)
            test._generate_reports([], sweep_result)
            # Set success to True only if the sweep result status is "PASS"
            success = (sweep_result.status == "PASS")
        # Always disconnect from the instruments when done, even if an error occurred during the sweep
        finally:
            # Release the connections to the PSU and DMM so they are left in a safe state
            test._disconnect_instruments()

    # If the mode is anything else (i.e. 'full'), run the complete test sequence
    else:  # full
        # Run the full test (fixed-voltage tests + sweep) using the test object's built-in run method
        success = test.run()

    # ── Save or discard prompt ────────────────────────────────────────────────
    # Print a blank line before the save/discard prompt for visual separation
    print()
    # In headless mode (GUI / CI) always save results automatically — no prompt
    if args.headless:
        print(f"  Results saved: {test._run_dir}")
        print()
        return 0 if success else 1
    # Keep asking until the engineer gives a valid yes or no answer
    while True:
        # Ask the engineer whether to keep the result files, defaulting to yes if they just press Enter
        save_resp = input("  Save results? [Y/n]: ").strip().lower()
        # If the engineer pressed Enter (empty), typed 'y', or typed 'yes', save the results
        if save_resp in ('', 'y', 'yes'):
            # Print the path to the run folder so the engineer knows where to find the saved files
            print(f"  Results saved: {test._run_dir}")
            # Print a blank line after the confirmation message
            print()
            # Exit the save/discard loop since the engineer has made their choice
            break
        # If the engineer typed 'n' or 'no', delete the result files to discard the run
        elif save_resp in ('n', 'no'):
            # Import the 'shutil' library which provides a function to delete entire directory trees
            import shutil
            # Import the 'subprocess' library which allows running system commands to help remove locked files
            import subprocess
            # Loop through all log file handlers attached to the test logger so they can be closed properly
            for handler in list(test._logger.handlers):
                # Try to close each log file handler so the log files are no longer locked
                try:
                    # Close the handler to release its file lock
                    handler.close()
                # If closing a handler fails (e.g. it was already closed), silently ignore the error
                except Exception:
                    # Do nothing — continue trying to close other handlers
                    pass
                # Remove the handler from the logger so it is fully detached
                test._logger.removeHandler(handler)
            # Try using Windows' built-in rmdir command to force-delete the run folder (handles OneDrive locks)
            try:
                # Run the Windows 'rmdir /s /q' command silently to delete the folder and all its contents
                subprocess.run(
                    # Build the command as a list of strings: cmd /c rmdir /s /q <path>
                    ['cmd', '/c', 'rmdir', '/s', '/q', str(test._run_dir)],
                    # Capture any command output so it does not clutter the terminal
                    capture_output=True, timeout=5
                )
            # If the subprocess command itself fails for any reason, silently ignore the error
            except Exception:
                # Do nothing — fall through to the shutil fallback below
                pass
            # If the folder still exists after the rmdir command, try Python's shutil as a fallback
            if test._run_dir.exists():
                # Use shutil to recursively delete the run folder; ignore individual file errors
                shutil.rmtree(test._run_dir, ignore_errors=True)
            # If the folder still exists even after both deletion attempts, warn the engineer
            if test._run_dir.exists():
                # Warn the engineer that the folder could not be fully removed (OneDrive may be holding files)
                print(f"  WARNING: Could not fully delete run folder (OneDrive may still be syncing).")
                # Tell the engineer to delete it manually and give them the path to find it
                print(f"  Delete manually: {test._run_dir}")
            # If the folder no longer exists, confirm to the engineer that the results were discarded
            else:
                # Confirm that the run folder was successfully deleted and the results are gone
                print("  Results discarded — run folder deleted.")
            # Print a blank line after the discard confirmation message
            print()
            # Exit the save/discard loop since the engineer has made their choice
            break

    # Return 0 if the test passed (success is True), or 1 if the test failed, so automation tools can detect the outcome
    return 0 if success else 1



# This block only runs when the script is executed directly (not when it is imported as a module)
if __name__ == "__main__":
    # Run the main function and pass its return code to sys.exit so the operating system receives the correct exit status
    sys.exit(main())
