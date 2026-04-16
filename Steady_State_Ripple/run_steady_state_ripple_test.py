#!/usr/bin/env python3
"""
Steady-State Rail Verification and Ripple Test — Runner

Run this script to execute the steady-state DC voltage and ripple test.

Usage:
    python run_steady_state_ripple_test.py                       # Interactive rail selector
    python run_steady_state_ripple_test.py --rails all           # Test all rails
    python run_steady_state_ripple_test.py --rails 3V6 2V5 1V8   # Test specific rails
    python run_steady_state_ripple_test.py --output PATH          # Override output directory
    python run_steady_state_ripple_test.py --verbose              # Verbose instrument logging
"""

# [Blank line for visual separation]
# Load the 'sys' library which lets the program exit cleanly and manage where Python looks for modules
import sys
# Load the 'argparse' library which reads and understands command-line flags the engineer types
import argparse
# Load the 'logging' library which controls how diagnostic messages are written to the console
import logging
# Load the 'Path' tool from the 'pathlib' library which makes it easy to work with file and folder paths
from pathlib import Path

# Add the parent folder (one level up from this script) to the list of places Python searches for modules
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add the same folder as this script to the list of places Python searches for modules
sys.path.insert(0, str(Path(__file__).parent))

# [Blank line for visual separation]
# [Blank line for visual separation]
# Define a helper function that turns on colour and special text formatting in the Windows terminal
def _enable_ansi():
    """Enable ANSI escape codes on Windows 10+."""
# Begin a protected block — if anything inside goes wrong the program carries on rather than crashing
    try:
# Load the 'ctypes' library which lets Python call low-level Windows system functions
        import ctypes
# Call the Windows API to switch the terminal into a mode that understands colour escape codes; handle -11 is STDOUT
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7
        )
# If the system call fails for any reason (e.g. running in a non-Windows terminal), silently ignore the error
    except Exception:
# Do nothing — the program will still run, just without colour formatting
        pass

# [Blank line for visual separation]
# [Blank line for visual separation]
# Define a helper function that configures how log messages are displayed; 'verbose' controls the level of detail
def _setup_logging(verbose: bool):
# Choose DEBUG level (very detailed) when verbose mode is on, otherwise WARNING level (errors and warnings only)
    level = logging.DEBUG if verbose else logging.WARNING
# Apply the chosen log level and a standard message format that includes the time, severity, module name, and message text
    logging.basicConfig(
        level=level,
        format='%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )

# [Blank line for visual separation]
# [Blank line for visual separation]
# ─────────────────────────────────────────────────────────────────────────────
# Interactive rail selector  (multi-select with TAB / SPACE toggle)
# ─────────────────────────────────────────────────────────────────────────────
# [Blank line for visual separation]
# Define the interactive menu function that lets the engineer tick or untick power rails using the keyboard
def interactive_rail_selector(all_rails) -> list:
    """
    Interactive multi-select rail picker using keyboard navigation.

    Controls:
        UP / DOWN      — Move the cursor between rails
        SPACE / TAB    — Toggle the highlighted rail  (check / uncheck)
        A              — Select ALL rails
        N              — Deselect ALL rails  (none)
        ENTER          — Confirm selection and proceed
        Q or ESC       — Cancel

    Returns a list of selected RailConfig objects, or None if cancelled.
    """
# Load 'msvcrt', a Windows-only library that can read individual key presses from the keyboard without waiting for ENTER
    import msvcrt

# Turn on ANSI colour support so the menu renders correctly in the Windows terminal
    _enable_ansi()

# Create a list of True values — one per rail — meaning every rail starts out ticked (selected)
    selected = [True] * len(all_rails)   # start with everything checked
# Set the cursor position to the first rail (index 0) so navigation starts at the top of the list
    cursor   = 0

# [Blank line for visual separation]
# Define an inner function that builds the current menu display as a list of text lines
    def render():
# Start with an empty list that will hold each line of the menu
        lines = []
# Add a blank line at the top for spacing
        lines.append("")
# Add the menu title
        lines.append("  RAIL SELECTION")
# Add a horizontal divider line made of equals signs
        lines.append("  " + "=" * 70)
# Add the keyboard controls hint so the engineer knows which keys to press
        lines.append("  UP/DOWN: Navigate   SPACE/TAB: Toggle   A: All   N: None   ENTER: Run   Q: Quit")
# Add a blank line for visual breathing room
        lines.append("")
# Loop over every rail in the list, keeping track of both the position (i) and the rail object itself
        for i, rail in enumerate(all_rails):
# Show "[X]" if this rail is ticked, or "[ ]" if it is unticked
            check  = "[X]" if selected[i] else "[ ]"
# Show ">>" next to the rail the cursor is currently on, or spaces for all other rails
            arrow  = ">>" if i == cursor else "  "
# Build the ripple spec text — if there is a ripple limit show it, otherwise say there is no spec
            ripple = (f"ripple < {rail.ripple_max_mvpp:.0f} mVpp"
                      if rail.ripple_max_mvpp is not None else "no ripple spec")
# Add one formatted line per rail showing its tick state, cursor arrow, name, test point, voltage range, and ripple spec
            lines.append(
                f"  {arrow} {check}  {rail.name:<10}  {rail.test_point:<12}  "
                f"{rail.min_v:.2f} – {rail.max_v:.2f} V    {ripple}"
            )
# Add a blank line after the rail list for spacing
        lines.append("")
# Count how many rails are currently ticked
        n = sum(selected)
# Add a summary line showing how many rails the engineer has selected so far
        lines.append(f"  Selected: {n} rail{'s' if n != 1 else ''}")
# Return the completed list of display lines
        return lines

# Render the menu for the first time and store the resulting lines
    display_lines = render()
# Print each line of the initial menu to the terminal
    for line in display_lines:
        print(line)
# Flush the output buffer to make sure everything appears on screen immediately
    sys.stdout.flush()

# [Blank line for visual separation]
# Start the main keyboard input loop — keep reading key presses until the engineer confirms or cancels
    while True:
# Read a single key press from the keyboard without waiting for ENTER
        key = msvcrt.getch()

# If the key is ENTER (carriage return byte), the engineer has confirmed their selection
        if key == b'\r':                            # ENTER — confirm
# Print a blank line to separate the menu from what comes next
            print()
# Build the final list of rails by keeping only those that are ticked
            picks = [r for r, s in zip(all_rails, selected) if s]
# Return the selected rails if any were chosen, or None if the list is empty
            return picks if picks else None

# If the key is SPACE or TAB, toggle the tick state of the rail the cursor is on
        elif key in (b' ', b'\t'):                  # SPACE / TAB — toggle current row
# Flip the ticked state of the currently highlighted rail
            selected[cursor] = not selected[cursor]

# If the engineer pressed A (uppercase or lowercase), select every rail
        elif key in (b'a', b'A'):                   # A — select all
# Set every entry in the selected list to True so all rails are ticked
            selected = [True] * len(all_rails)

# If the engineer pressed N (uppercase or lowercase), deselect every rail
        elif key in (b'n', b'N'):                   # N — deselect all
# Set every entry in the selected list to False so no rails are ticked
            selected = [False] * len(all_rails)

# If the key starts with a special prefix byte, this is an arrow key — read the second byte to find out which one
        elif key in (b'\xe0', b'\x00'):             # Arrow key prefix
# Read the second byte of the arrow key sequence
            key2 = msvcrt.getch()
# If the second byte means UP arrow, move the cursor one row up (wrap around to the bottom if already at the top)
            if key2 == b'H':                        # UP
                cursor = (cursor - 1) % len(all_rails)
# If the second byte means DOWN arrow, move the cursor one row down (wrap around to the top if already at the bottom)
            elif key2 == b'P':                      # DOWN
                cursor = (cursor + 1) % len(all_rails)

# If the engineer pressed Q, lowercase q, or Escape, cancel the selection
        elif key in (b'q', b'Q', b'\x1b'):          # Q / ESC — cancel
# Print a cancellation message and a blank line for spacing
            print("\n  Cancelled.")
# Return None to tell the calling code that the engineer cancelled
            return None

# For any other unrecognised key, do nothing and loop back to wait for the next key press
        else:
            continue

# After any valid key press that changes the display, re-render and redraw the menu in-place
        # Redraw in-place
# Generate a fresh set of display lines reflecting the new state
        display_lines = render()
# Move the terminal cursor upward by exactly the number of lines the menu occupies, so the old text can be overwritten
        sys.stdout.write(f"\033[{len(display_lines)}A")
# Overwrite each line: clear it first (\033[2K) then write the new content
        for line in display_lines:
            sys.stdout.write(f"\033[2K{line}\n")
# Flush the output buffer so the redrawn menu appears on screen instantly
        sys.stdout.flush()

# [Blank line for visual separation]
# [Blank line for visual separation]
# ─────────────────────────────────────────────────────────────────────────────
# Output directory prompt
# ─────────────────────────────────────────────────────────────────────────────
# [Blank line for visual separation]
# Define a function that asks the engineer where test results should be saved; the config can supply a default path
def prompt_output_directory(cfg_output_dir: str = None) -> str:
# Use the path from the config file if one was provided, otherwise fall back to a sensible default folder name
    default_path = cfg_output_dir or "steady_state_ripple_results"

# Print a blank line before the section header for visual spacing
    print()
# Print a full-width divider line to visually separate this section
    print("=" * 70)
# Print the section heading so the engineer knows what this prompt is about
    print("  OUTPUT DIRECTORY SELECTION")
# Print the closing divider line
    print("=" * 70)
# Print a blank line for spacing
    print()
# Show the engineer what the default output path is (taken from the config file)
    print(f"  Default path (from config): {default_path}")
# Print a blank line for spacing
    print()
# Print the heading for the list of choices
    print("  Options:")
# Show option 1 — use the default path without changing it
    print("    [1] Use default path")
# Show option 2 — let the engineer type in a different folder path
    print("    [2] Enter custom path")
# Print a blank line before the input prompt
    print()

# Keep asking until the engineer gives a valid answer
    while True:
# Ask the engineer to type 1 or 2 and remove any accidental leading or trailing spaces
        choice = input("  Select option (1 or 2): ").strip()
# If the engineer chose option 1, use the default path
        if choice == "1":
# Confirm to the engineer which path will be used
            print(f"  Using: {default_path}")
# Print a blank line before continuing
            print()
# Return the default path to the calling code
            return default_path
# If the engineer chose option 2, ask them to type a custom path
        elif choice == "2":
# Read the custom path the engineer types in and remove surrounding whitespace
            custom_path = input("  Enter output directory path: ").strip()
# If the engineer left the path blank, show an error and ask again
            if not custom_path:
                print("  ERROR: Path cannot be empty. Try again.")
# Skip the rest of this loop iteration and ask for the choice again
                continue
# Confirm to the engineer which custom path will be used
            print(f"  Using: {custom_path}")
# Print a blank line before continuing
            print()
# Return the custom path to the calling code
            return custom_path
# If the engineer typed something other than 1 or 2, explain the valid options and ask again
        else:
            print("  Invalid choice. Please enter 1 or 2.")

# [Blank line for visual separation]
# [Blank line for visual separation]
# ─────────────────────────────────────────────────────────────────────────────
# Setup instructions
# ─────────────────────────────────────────────────────────────────────────────
# [Blank line for visual separation]
# Define a function that prints the step-by-step hardware setup guide before the test begins
def print_setup_instructions(instr: dict, psu_cfg: dict, scp_cfg: dict, selected_rails: list):
# Pull the PSU VISA address out of the instrument addresses dictionary, defaulting to '?' if it is missing
    psu_addr = instr.get("psu", "?")
# Pull the oscilloscope VISA address out of the instrument addresses dictionary, defaulting to '?' if it is missing
    scp_addr = instr.get("scope", "?")
# Pull the PSU channel number from the PSU settings, defaulting to channel 1 if not specified
    ch       = psu_cfg.get("channel", 1)
# Pull the input voltage setting from the PSU config, defaulting to 5.0 V if not specified
    vin      = psu_cfg.get("vin_v", 5.0)
# Pull the current limit setting from the PSU config, defaulting to '?' if not specified
    i_lim    = psu_cfg.get("current_limit_a", "?")
# Pull the over-voltage protection level from the PSU config, defaulting to '?' if not specified
    ovp      = psu_cfg.get("ovp_level_v", "?")
# Convert the DC timebase setting from seconds-per-division to milliseconds-per-division for display
    tb_dc_ms = scp_cfg.get("dc_timebase_s_per_div", 0.01) * 1000
# Convert the ripple timebase setting from seconds-per-division to milliseconds-per-division for display
    tb_rp_ms = scp_cfg.get("ripple_timebase_s_per_div", 0.1) * 1000
# Convert the ripple voltage scale from volts-per-division to millivolts-per-division for display
    rp_mv    = scp_cfg.get("ripple_v_scale_v_per_div", 0.05) * 1000

# Check whether any of the selected rails have a ripple limit defined — this determines whether Step 4 is relevant
    has_ripple = any(r.ripple_max_mvpp is not None for r in selected_rails)

# Print a blank line before the setup instructions section
    print()
# Print the top divider for the setup instructions block
    print("=" * 70)
# Print the section heading
    print("  SETUP INSTRUCTIONS — Complete these steps before starting")
# Print the bottom divider
    print("=" * 70)

# Print a blank line before Step 1
    print()
# Print the Step 1 heading
    print("  STEP 1 — DUT State")
# Print a sub-divider under the step heading
    print("  " + "-" * 60)
# Tell the engineer that the Device Under Test must already be powered on and running normally
    print("  The DUT must be POWERED ON and fully stable at nominal conditions.")
# Tell the engineer that all rails must be active and that this test does not reset or power-cycle the board
    print("  All power rails should be up. This test does NOT power-cycle the DUT.")

# Print a blank line before Step 2
    print()
# Print the Step 2 heading covering PSU verification
    print("  STEP 2 — PSU Verification  (Keithley Power Supply)")
# Print a sub-divider under the step heading
    print("  " + "-" * 60)
# Tell the engineer the expected PSU channel, voltage, current, and over-voltage protection settings
    print(f"  Confirm PSU CH{ch} is outputting  {vin} V / {i_lim} A  (OVP: {ovp} V)")
# Tell the engineer to connect the positive (red) lead to the DUT's positive input terminal
    print(f"  + lead (red)   →  DUT VIN positive")
# Tell the engineer to connect the negative (black) lead to the DUT's ground return terminal
    print(f"  − lead (black) →  DUT GND / return")
# Show the PSU VISA address for reference — note the script does not send commands to the PSU
    print(f"  VISA address   :  {psu_addr}  (for reference only — script does not control PSU)")

# Print a blank line before Step 3
    print()
# Print the Step 3 heading covering oscilloscope probe setup
    print("  STEP 3 — Oscilloscope Probe  (CH1 only)")
# Print a sub-divider under the step heading
    print("  " + "-" * 60)
# Remind the engineer that only Channel 1 is used and that the script tests one rail at a time
    print("  Use CH1 for ALL measurements — the script tests one rail at a time.")
# Tell the engineer to set the probe attenuation switch to 1× before starting
    print("  Before starting, set the probe slide switch to:  1×  (1:1 attenuation)")
# Explain that the script will set coupling and bandwidth automatically — no manual scope adjustment needed
    print("  Coupling and BW are configured automatically by the script.")
# Print a blank line for spacing
    print()
# Show the oscilloscope settings that will be applied during the DC voltage measurement phase
    print(f"  DC Voltage phase:   DC coupling  ·  20 MHz BW  ·  {tb_dc_ms:.0f} ms/div")
# Show the oscilloscope settings that will be applied during the ripple measurement phase
    print(f"  Ripple phase:       AC coupling  ·  20 MHz BW  ·  {rp_mv:.0f} mV/div  ·  {tb_rp_ms:.0f} ms/div")
# Print a blank line for spacing
    print()
# Tell the engineer that the script will instruct them when to move the probe to each new test point
    print("  The script will prompt you to move the probe for each rail.")

# Only show Step 4 ground-spring instructions if at least one selected rail has a ripple limit
    if has_ripple:
# Print a blank line before Step 4
        print()
# Print the Step 4 heading about the coaxial ground spring
        print("  STEP 4 — GND Spring  (required for ripple measurements)")
# Print a sub-divider under the step heading
        print("  " + "-" * 60)
# Tell the engineer to have a coaxial ground spring tip ready and explain how it attaches to the probe
        print("  Have a COAXIAL GND SPRING tip ready.  It fits over the probe barrel")
# Explain that the ground spring replaces the long alligator-clip ground lead
        print("  and replaces the long alligator-clip ground lead.")
# Explain why the ground spring matters — long leads add inductance which inflates ripple readings
        print("  Long ground leads add inductance — they inflate ripple readings.")
# Tell the engineer the script will remind them to fit the spring before each ripple measurement
        print("  The script will ask you to fit the spring before the ripple phase")
# Tell the engineer where to position the spring tip — across the last output capacitor on the board
        print("  of each rail and position the tip across the last output capacitor.")
# If no selected rails have a ripple limit, tell the engineer the ground spring is not needed
    else:
# Print a blank line before the skipped-step note
        print()
# Inform the engineer that Step 4 is not applicable for the rails they have chosen
        print("  STEP 4 — GND Spring:  Not required for the selected rails.")

# Print a blank line before Step 5
    print()
# Print the Step 5 heading covering PC-to-instrument connections
    print("  STEP 5 — PC Connections via VISA")
# Print a sub-divider under the step heading
    print("  " + "-" * 60)
# Show the oscilloscope VISA address the PC will use to communicate with the scope
    print(f"  Scope VISA address : {scp_addr}")
# Print a blank line for spacing
    print()
# Tell the engineer how to fix an incorrect VISA address — edit the config file and restart
    print("  If the address looks wrong, edit steady_state_ripple_config.json")
# Continue the previous sentence on the next line
    print("  and restart the script.")
# Print a blank line for spacing
    print()
# Explain how the engineer can list all VISA instruments currently detected by the PC
    print("  To list detected instruments:")
# Show the exact Python one-liner command the engineer should run in a terminal
    print("    python -c \"import pyvisa; print(pyvisa.ResourceManager().list_resources())\"")

# Print a blank line before Step 6
    print()
# Print the Step 6 heading about powering on the instruments
    print("  STEP 6 — Power ON Instruments")
# Print a sub-divider under the step heading
    print("  " + "-" * 60)
# Tell the engineer to power on the oscilloscope
    print("  Power on the Keysight Oscilloscope.")
# Warn the engineer NOT to press RUN on the scope manually — the script arms it for each measurement itself
    print("  Do NOT press RUN on the scope manually — the script arms it for each")
# Continue the previous sentence on the next line
    print("  measurement phase automatically.")

# Print a blank line before Step 7
    print()
# Print the Step 7 heading for safety reminders
    print("  STEP 7 — Safety Reminders")
# Print a sub-divider under the step heading
    print("  " + "-" * 60)
# Show the DUT input voltage and current limit as a quick safety reference
    print(f"  DUT input: {vin} V / {i_lim} A")
# Remind the engineer to lift the probe tip clear of the current test point before moving to the next
    print("  Remove the probe tip from one test point before moving to the next.")
# Warn the engineer never to short the probe tip against neighbouring pads on the board
    print("  Do NOT short probe tip to adjacent pads.")
# Warn the engineer to keep the probe cable away from any fans or moving parts
    print("  Keep probe lead clear of rotating components.")
# Print a blank line after the safety reminders
    print()
# Print the closing divider for the entire setup instructions section
    print("=" * 70)
# Print a blank line after the section to separate it from what follows
    print()

# [Blank line for visual separation]
# [Blank line for visual separation]
# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────
# [Blank line for visual separation]
# Define the function that prints the opening title banner when the script first starts
def print_banner():
# Print a blank line before the banner for spacing
    print()
# Print the top border of the banner
    print("=" * 70)
# Print the main test name title
    print("  STEADY-STATE RAIL VERIFICATION AND RIPPLE TEST")
# Print a one-line description of what the test does
    print("  Verify DC levels and AC ripple on selected power rails")
# Print the bottom border of the banner header
    print("=" * 70)
# Print a blank line for spacing
    print()
# List the instruments used by this test and clarify that only Channel 1 is used, one rail at a time
    print("  Instruments : Keysight Oscilloscope  (CH1, one rail at a time)")
# Print a blank line for spacing
    print()
# Print the heading for the per-rail procedure summary
    print("  Per-rail procedure:")
# Describe Phase 1 — the DC voltage measurement step
    print("    Phase 1 — DC Voltage  : DC coupling · 20 MHz BW · measure DC RMS FS")
# Describe Phase 2 — the ripple measurement step with its scope settings
    print("    Phase 2 — Ripple      : AC coupling · 50 mV/div · 100 ms/div · measure Vpp")
# Note that a ground spring must be positioned across the last output capacitor during the ripple phase
    print("                            (GND spring placed across last output capacitor)")
# Print a blank line for spacing
    print()
# Tell the engineer which file to edit if they need to change any settings
    print("  Edit  steady_state_ripple_config.json  to change instrument addresses,")
# Continue the previous sentence listing the kinds of settings that can be changed
    print("  rail voltage ranges, ripple limits, and output directory.")
# Print a blank line before the closing border
    print()
# Print the closing border of the banner
    print("=" * 70)

# [Blank line for visual separation]
# [Blank line for visual separation]
# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
# [Blank line for visual separation]
# Define the main function — this is the central entry point that orchestrates the entire test run
def main():
# Enable ANSI colour codes in the Windows terminal so text formatting works correctly throughout the script
    _enable_ansi()

# Create an argument parser that will read and understand any flags the engineer types after the script name
    parser = argparse.ArgumentParser(
        description="Steady-State Rail Verification and Ripple Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_steady_state_ripple_test.py
  python run_steady_state_ripple_test.py --rails all
  python run_steady_state_ripple_test.py --rails 3V6 2V5 1V8
  python run_steady_state_ripple_test.py --output D:/Results/Board_SN001
  python run_steady_state_ripple_test.py --verbose
        """
    )
# Register the '--rails' flag which accepts one or more rail names, or the word 'all', to skip the interactive menu
    parser.add_argument(
        '--rails', nargs='+', default=None,
        help='Rail names to test, or "all". Default: interactive selector.'
    )
# Register the '--output' flag which lets the engineer override the results folder path from the command line
    parser.add_argument(
        '--output', type=str, default=None,
        help='Base directory for results (default: path from config)'
    )
# Register the '--verbose' flag which, when present, turns on detailed instrument-level log messages
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable verbose instrument-level logging'
    )

# Parse all the flags the engineer typed and store them in the 'args' object for easy access
    args = parser.parse_args()
# Configure the logging system now that we know whether the engineer wants verbose output or not
    _setup_logging(args.verbose)

# Display the opening banner so the engineer can see the test name and a summary of what it does
    print_banner()

# Attempt to import the core test module; if it cannot be found, show a helpful error and stop
    try:
# Import the main test class and the loaded configuration dictionary from the test module
        from steady_state_ripple_test import SteadyStateRippleTest, _CFG
# If the import fails (e.g. the file is missing or has a syntax error), catch the error and explain it
    except ImportError as e:
# Print a clear error message telling the engineer what went wrong
        print(f"\n  ERROR: Could not import test module: {e}")
# Tell the engineer where the missing file should be located
        print("  Make sure steady_state_ripple_test.py is in the same directory.")
# Return exit code 1 to signal that the script failed
        return 1

# Retrieve the full list of all available power rails defined in the test class
    all_rails = SteadyStateRippleTest.ALL_RAILS

# ── Config summary ────────────────────────────────────────────────────────
# Extract the instrument VISA addresses section from the loaded configuration dictionary
    instr   = _CFG.get("instrument_addresses", {})
# Extract the PSU settings section from the loaded configuration dictionary
    psu_cfg = _CFG.get("psu_settings", {})
# Extract the oscilloscope settings section from the loaded configuration dictionary
    scp_cfg = _CFG.get("scope_settings", {})

# Print a one-line heading for the configuration summary that follows
    print("  Configuration summary:")
# Print the oscilloscope VISA address so the engineer can verify it matches their instrument
    print(f"    Scope address    : {instr.get('scope')}")
# Print the PSU channel, voltage, and current settings — noting the script does not command the PSU directly
    print(f"    PSU ref          : CH{psu_cfg.get('channel',1)}  {psu_cfg.get('vin_v',5.0)} V / "
          f"{psu_cfg.get('current_limit_a',2.0)} A  (pre-configured — not controlled by test)")
# Print the DC timebase setting that will be applied to the oscilloscope during DC voltage measurements
    print(f"    DC timebase      : {scp_cfg.get('dc_timebase_s_per_div',0.01)*1000:.0f} ms/div")
# Print the ripple timebase and voltage scale settings that will be applied during ripple measurements
    print(f"    Ripple timebase  : {scp_cfg.get('ripple_timebase_s_per_div',0.1)*1000:.0f} ms/div  "
          f"at {scp_cfg.get('ripple_v_scale_v_per_div',0.05)*1000:.0f} mV/div  AC coupling")
# Print a blank line after the configuration summary
    print()
# Print a heading showing how many rails are available in total
    print(f"  Available rails ({len(all_rails)}):")
# Loop over every available rail and print its name, test point location, voltage range, and ripple spec
    for r in all_rails:
# Format the ripple spec as a limit string if one exists, or as 'no spec' if the rail has no ripple requirement
        ripple = f"< {r.ripple_max_mvpp:.0f} mVpp" if r.ripple_max_mvpp is not None else "no spec"
# Print the formatted summary line for this rail
        print(f"    {r.name:<10}  {r.test_point:<12}  "
              f"{r.min_v:.2f} – {r.max_v:.2f} V    ripple: {ripple}")
# Print a blank line after the rails listing
    print()

# ── Rail selection ────────────────────────────────────────────────────────
# Check whether the engineer supplied a '--rails' flag on the command line
    if args.rails:
# Check if the engineer typed '--rails all' to request every available rail
        if args.rails == ['all']:
# Set the selected rails to the complete list of all available rails
            selected_rails = all_rails
# Confirm to the engineer that all rails will be tested
            print(f"  Rails: all ({len(selected_rails)})  (from --rails flag)")
# If the engineer listed specific rail names rather than 'all', look each one up
        else:
# Build a dictionary that maps each rail's name string to the corresponding rail object for fast lookup
            name_map = {r.name: r for r in all_rails}
# Start with an empty list that will be filled with the matching rail objects
            selected_rails = []
# Loop over each rail name the engineer typed on the command line
            for name in args.rails:
# If this name exists in the available rails, add the corresponding rail object to the selection
                if name in name_map:
                    selected_rails.append(name_map[name])
# If the name is not recognised, warn the engineer and skip it rather than crashing
                else:
                    print(f"  WARNING: Unknown rail '{name}' — skipped. "
                          f"Available: {[r.name for r in all_rails]}")
# If none of the names matched any known rails, show an error and stop the script
            if not selected_rails:
                print("  ERROR: No valid rails selected.")
# Return exit code 1 to signal that the script failed due to invalid input
                return 1
# Confirm to the engineer which specific rails will be tested
            print(f"  Rails: {[r.name for r in selected_rails]}  (from --rails flag)")
# Print a blank line after the rail selection summary
        print()
# If no '--rails' flag was given, show the interactive keyboard menu so the engineer can pick rails visually
    else:
# Show the interactive checkbox menu and wait for the engineer to select which rails to test
        selected_rails = interactive_rail_selector(all_rails)
# If the engineer pressed Q or Escape to cancel the menu, exit the script cleanly with no error
        if selected_rails is None:
            return 0
# If the engineer confirmed but had nothing ticked, explain there is nothing to test and exit
        if not selected_rails:
            print("  No rails selected — nothing to test.")
# Return exit code 0 because this is a clean exit, not an error
            return 0
# Print a summary of how many rails were chosen and list their names
        print(f"  Running {len(selected_rails)} rail(s): "
              + "  ".join(r.name for r in selected_rails))

# ── Setup instructions ────────────────────────────────────────────────────
# Print the full step-by-step hardware setup guide using the config values and the list of selected rails
    print_setup_instructions(instr, psu_cfg, scp_cfg, selected_rails)

# ── Output directory selection ────────────────────────────────────────────
# Read the output directory override from the command-line flag (will be None if not provided)
    output_dir = args.output
# If no output directory was given on the command line, ask the engineer interactively
    if output_dir is None:
# Read the output directory section from the config file
        cfg_out = _CFG.get("output_dir", {})
# Extract the path string whether the config value is a dictionary with a 'path' key or a plain string
        cfg_dir = (
            cfg_out.get("path", "steady_state_ripple_results")
            if isinstance(cfg_out, dict)
            else str(cfg_out)
        )
# Show the output directory prompt and return whatever path the engineer chooses
        output_dir = prompt_output_directory(cfg_dir)

# ── Start confirmation ────────────────────────────────────────────────────
# Ask the engineer to confirm that hardware setup is complete; allow them to quit at this point if needed
    response = input("  All setup complete? Press ENTER to start (or 'q' to quit): ").strip().lower()
# If the engineer typed q, quit, or exit, cancel the test run cleanly
    if response in ('q', 'quit', 'exit'):
# Print a cancellation message
        print("  Cancelled.")
# Return exit code 0 because the engineer deliberately chose to stop, not an error
        return 0

# ── Run ───────────────────────────────────────────────────────────────────
# Create a new test instance configured with the selected rails and the chosen output directory
    test    = SteadyStateRippleTest(rails=selected_rails, output_dir=output_dir)
# Execute the full test sequence and capture whether it passed (True) or failed (False)
    success = test.run()

# ── Save or discard prompt ────────────────────────────────────────────────
# Print a blank line before the save/discard prompt for visual spacing
    print()
# Keep asking until the engineer gives a clear yes or no answer about saving the results
    while True:
# Ask the engineer whether to keep or throw away the results folder; default is Yes if they just press ENTER
        save_resp = input("  Save results? [Y/n]: ").strip().lower()
# If the engineer pressed ENTER (empty), or typed y or yes, keep the results
        if save_resp in ('', 'y', 'yes'):
# Print the path to the saved results folder so the engineer knows where to find them
            print(f"  Results saved: {test._run_dir}")
# Print a blank line after the confirmation
            print()
# Exit the loop — the save decision is made
            break
# If the engineer typed n or no, delete the results folder
        elif save_resp in ('n', 'no'):
# Import the 'shutil' library which provides tools for deleting directory trees
            import shutil
# Import the 'subprocess' library which lets Python run external system commands
            import subprocess
# Close the log file handler so Windows releases the file lock
            for handler in list(test._logger.handlers):
# Try to close this log handler cleanly so its file is released
                try:
                    handler.close()
# If closing the handler raises an error, ignore it and move on to the next handler
                except Exception:
                    pass
# Remove this handler from the logger so it is fully detached
                test._logger.removeHandler(handler)
# Use Windows rmdir /s /q — handles OneDrive-locked dirs that
# shutil.rmtree silently fails on
# Run the Windows 'rmdir /s /q' command to forcefully delete the results folder and all its contents
            try:
                subprocess.run(
                    ['cmd', '/c', 'rmdir', '/s', '/q', str(test._run_dir)],
                    capture_output=True, timeout=5
                )
# If the subprocess command itself raises any error, silently ignore it and fall through to the shutil fallback
            except Exception:
                pass
# Fallback: shutil in case subprocess didn't finish cleanly
# If the folder still exists after the Windows rmdir command, try again using Python's own directory removal tool
            if test._run_dir.exists():
                shutil.rmtree(test._run_dir, ignore_errors=True)
# Check once more whether the folder is truly gone after both deletion attempts
            if test._run_dir.exists():
# Warn the engineer that the folder could not be fully deleted — this often happens when OneDrive is syncing the files
                print(f"  WARNING: Could not fully delete run folder (OneDrive may still be syncing).")
# Tell the engineer the exact folder path so they can delete it themselves
                print(f"  Delete manually: {test._run_dir}")
# If the folder no longer exists, confirm to the engineer that it was successfully deleted
            else:
                print("  Results discarded — run folder deleted.")
# Print a blank line after the discard confirmation
            print()
# Exit the loop — the discard decision is made
            break

# Return exit code 0 if all rails passed, or exit code 1 if any rail failed
    return 0 if success else 1

# [Blank line for visual separation]
# [Blank line for visual separation]
# Check whether this script is being run directly (rather than imported as a module by another script)
if __name__ == "__main__":
# Run the main function and pass its return value to sys.exit so the operating system gets the correct exit code
    sys.exit(main())
