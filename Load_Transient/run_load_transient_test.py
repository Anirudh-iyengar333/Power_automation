#!/usr/bin/env python3
# This first line (called a "shebang") tells Linux/macOS that this file should be run using Python 3; it is harmless on Windows
"""
Load Transient Response Test Runner

Simple runner script for Load Transient transient response testing with auto-detection
of VISA instruments.

Usage:
    python run_load_transient_test.py                    # Interactive rail selection
    python run_load_transient_test.py --scope <addr>     # Specify scope address
    python run_load_transient_test.py --load <addr>      # Specify load address
    python run_load_transient_test.py --list             # List available instruments
    python run_load_transient_test.py --rails 3V6,3V3    # Test specific rails only (skip selector)
"""

# Load the 'sys' library, which gives access to system-level operations such as exiting the program and managing the Python module search path
import sys
# Load the 'os' library, which provides access to operating system functions such as reading environment variables and working with file paths
import os
# Load the 'argparse' library, which handles parsing command-line arguments so engineers can pass flags like --scope or --rails when starting the script
import argparse
# Load 'Path' from the 'pathlib' library, which provides an object-oriented way to work with file and directory paths on any operating system
from pathlib import Path

# Add the parent directory (one level up from this file's folder) to the Python module search path, so shared libraries in the project root can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add the current file's own directory to the Python module search path, allowing this script to import modules stored alongside it
sys.path.insert(0, str(Path(__file__).parent))

# [Blank line for visual separation]

# [Blank line for visual separation]
def _enable_ansi():
    # This function enables colour and formatting codes in the Windows terminal; without it, the interactive menus look broken on older Windows versions
    """Enable ANSI escape codes on Windows 10+"""
    # Begin a try block that attempts to enable ANSI support; if it fails (e.g. on an older system), the error is silently ignored
    try:
        # Load the 'ctypes' library, which allows Python to call Windows operating system functions directly
        import ctypes
        # Get a reference to the Windows kernel module, which manages low-level system operations
        kernel32 = ctypes.windll.kernel32
        # Call the Windows API to set the console output mode to '7', which enables ANSI escape code support for colour and cursor movement
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    # If any error occurs (e.g. the system does not support this API), silently continue — the terminal will still work, just without colour
    except Exception:
        # Do nothing — ANSI support is optional; the test will still run without it
        pass

# [Blank line for visual separation]

# [Blank line for visual separation]
def interactive_rail_selector(rail_configs):
    # This function displays a keyboard-navigable menu on screen so the engineer can choose which power rails to test without editing any files
    """
    Interactive multi-select rail selector.

    Controls:
        UP/DOWN arrows  - Navigate between rails
        TAB or SPACE    - Toggle selection on/off
        A               - Select all / Deselect all
        ENTER           - Confirm and run selected rails
        Q or ESC        - Cancel

    Args:
        rail_configs: List of RailConfig objects from the test class

    Returns:
        List of selected rail names, or None if cancelled
    """
    # Load 'msvcrt', the Microsoft Visual C Runtime library, which provides functions for reading individual key presses from the keyboard without waiting for Enter
    import msvcrt

    # Call the function that enables ANSI colour codes in the Windows terminal
    _enable_ansi()

    # Build the list of rail display entries from the rail configuration objects provided
    rails = []
    # Loop through each rail configuration object in the provided list
    for r in rail_configs:
        # Add a dictionary containing only the display-relevant fields for this rail to the rails list
        rails.append({
            # Store the rail name (e.g. "3V3") for display in the menu
            'name': r.name,
            # Store the test point location (e.g. "TP10") so the engineer knows where to connect the probe
            'tp': r.test_point,
            # Store the expected nominal voltage for display
            'voltage': r.expected_voltage_v,
            # Store the low current level used at the start of the load step
            'low': r.low_current_ma,
            # Store the high current level that the load will jump to during the transient test
            'high': r.high_current_ma,
        })

    # Create a list of boolean flags, one per rail, all starting as True meaning all rails are selected by default
    selected = [True] * len(rails)
    # Set the cursor position to the first rail (index 0) so the menu starts with the top item highlighted
    cursor = 0

    # Define the inner function that builds the text lines for the display
    def render():
        # This inner function generates the full list of text lines that make up the interactive menu display
        """Build display lines for the selector"""
        # Create an empty list to hold all the text lines that will be printed to the screen
        lines = []
        # Add a blank line at the top for visual spacing
        lines.append("")
        # Add the menu title
        lines.append("  RAIL SELECTION")
        # Add a horizontal separator line made of equals signs
        lines.append("  " + "=" * 62)
        # Add the keyboard shortcut help line
        lines.append("  UP/DOWN: Navigate | TAB: Toggle | ENTER: Run | A: All | Q: Quit")
        # Add another blank line for spacing before the rail list
        lines.append("")

        # Loop through each rail and build its display row
        for i, r in enumerate(rails):
            # Choose the checkbox marker: "[X]" if selected, "[ ]" if not selected
            marker = "[X]" if selected[i] else "[ ]"
            # Choose the cursor arrow: ">>" if this row is under the cursor, "  " otherwise
            arrow = ">>" if i == cursor else "  "
            # Build the complete display row showing the arrow, checkbox, rail name, test point, voltage, and current range
            line = (
                f"  {arrow} {marker} {r['name']:<10} ({r['tp']:<5}) "
                f"{r['voltage']:>5.2f}V   {r['low']} -> {r['high']}mA"
            )
            # Add the completed rail row to the list of display lines
            lines.append(line)

        # Build a list of the names of all currently selected rails
        sel_names = [rails[i]['name'] for i in range(len(rails)) if selected[i]]
        # Add a blank line before the selection summary
        lines.append("")
        # Check if at least one rail is selected
        if sel_names:
            # Show the names and count of all selected rails
            lines.append(f"  Selected: {', '.join(sel_names)}  ({len(sel_names)} rails)")
        else:
            # Show a hint to the engineer that no rails are selected and TAB is needed
            lines.append("  Selected: None  (use TAB to select rails)")
        # Return the complete list of text lines for rendering
        return lines

    # Render the initial display and print it line by line to the terminal
    display_lines = render()
    # Loop through each generated display line and print it to the screen
    for line in display_lines:
        print(line)
    # Force the terminal to immediately output all buffered text so the menu appears without delay
    sys.stdout.flush()

    # Enter the main keyboard input loop that runs until the engineer confirms or cancels
    while True:
        # Read one key press from the keyboard (this blocks until a key is pressed)
        key = msvcrt.getch()

        # Check if the key pressed is Enter (byte code '\r'), which confirms the selection
        if key == b'\r':  # Enter - confirm selection
            # Build the final list of selected rail names based on which checkboxes are ticked
            sel = [rails[i]['name'] for i in range(len(rails)) if selected[i]]
            # If no rails are selected, do nothing and wait for another key press
            if not sel:
                # Flash a message - need at least one rail
                continue
            # Print a blank line after the menu for visual separation before the test starts
            print()
            # Return the list of selected rail names to the calling function
            return sel

        # Check if the key pressed is Tab or Space, which toggles the current rail's selection
        elif key == b'\t' or key == b' ':  # Tab or Space - toggle current rail
            # Flip the selection state of the rail under the cursor (True becomes False, False becomes True)
            selected[cursor] = not selected[cursor]

        # Check if the key pressed is 'A' or 'a', which toggles all rails at once
        elif key in (b'a', b'A'):  # Toggle all
            # If all rails are currently selected, deselect all; otherwise select all
            if all(selected):
                # Deselect all rails
                selected = [False] * len(rails)
            else:
                # Select all rails
                selected = [True] * len(rails)

        # Check if the key pressed is the special key prefix for arrow keys (sent as a two-byte sequence on Windows)
        elif key == b'\xe0' or key == b'\x00':  # Special key prefix (arrows)
            # Read the second byte of the arrow key sequence to determine which arrow was pressed
            key2 = msvcrt.getch()
            # Check if the second byte indicates the Up arrow key
            if key2 == b'H':  # Up arrow
                # Move the cursor one position up, wrapping around to the bottom if at the top
                cursor = (cursor - 1) % len(rails)
            # Check if the second byte indicates the Down arrow key
            elif key2 == b'P':  # Down arrow
                # Move the cursor one position down, wrapping around to the top if at the bottom
                cursor = (cursor + 1) % len(rails)

        # Check if the key pressed is 'Q', 'q', or Escape, which cancels the selection
        elif key in (b'q', b'Q', b'\x1b'):  # Quit or Escape
            # Print a cancellation message to inform the engineer
            print("\n  Selection cancelled.")
            # Return None to signal that the test was cancelled
            return None

        # For any other key press that has no defined action, skip redrawing and wait for the next key
        else:
            continue

        # Redraw the menu in-place by moving the cursor back up over the existing lines and overwriting them
        display_lines = render()
        # Move the terminal cursor up by the number of lines in the display so the menu overwrites itself
        sys.stdout.write(f"\033[{len(display_lines)}A")
        # Loop through each updated display line and overwrite the corresponding terminal line
        for line in display_lines:
            # Clear the current terminal line (\033[2K) and then write the new content
            sys.stdout.write(f"\033[2K{line}\n")
        # Force the terminal to output all buffered text immediately so the update appears instantly
        sys.stdout.flush()

# [Blank line for visual separation]

# [Blank line for visual separation]
def list_visa_resources():
    # This function scans the PC's USB ports for connected instruments and prints a list of everything found
    """List all available VISA resources with auto-identification"""
    # Begin a try block to attempt auto-detection; if the required module is missing, report the error and return False
    try:
        # Import the auto-detection function from the local visa_auto_detect module
        from visa_auto_detect import detect_all_instruments
        # Call the detection function to scan all USB/GPIB ports for instruments
        instruments = detect_all_instruments()
        # Return True if at least one instrument was found, False if none were detected
        return bool(instruments)
    # Handle the case where the visa_auto_detect module file is not found in the project folder
    except ImportError:
        # Print an error message telling the engineer that the detection module is missing
        print("ERROR: visa_auto_detect module not found")
        # Return False to indicate that instrument listing failed
        return False
    # Handle any other unexpected error during detection
    except Exception as e:
        # Print a descriptive error message showing what went wrong
        print(f"ERROR: Failed to detect instruments: {e}")
        # Return False to indicate that instrument listing failed
        return False

# [Blank line for visual separation]

# [Blank line for visual separation]
def print_banner():
    # This function prints the test title and a brief description of what the test does, shown at startup before any interaction
    """Print test banner"""
    # Print a blank line for visual separation
    print()
    # Print a horizontal separator line to frame the banner
    print("=" * 70)
    # Print the test name as a bold title
    print(" LOAD TRANSIENT RESPONSE TEST")
    # Print a one-line description of what this test validates
    print(" Validates regulator control loop bandwidth, damping, and oscillation")
    # Print a closing separator line
    print("=" * 70)
    # Print a blank line for spacing
    print()
    # Print a heading for the test procedure description
    print(" Test Procedure for Each Rail:")
    # Print step 1: the engineer confirms the probe is connected at the rail test point
    print("   1. Confirm probe connection to rail")
    # Print step 2: the positive load step (current increases suddenly)
    print("   2. Automatic positive load step (100mA -> half rated)")
    # Print step 3: the oscilloscope captures and the program analyses the waveform
    print("   3. Capture and analyze waveform")
    # Print step 4: the negative load step (current drops back to low)
    print("   4. Automatic negative load step (half rated -> 100mA)")
    # Print step 5: same capture and analysis for the decreasing load step
    print("   5. Capture and analyze waveform")
    # Print step 6: the test automatically moves on to the next rail
    print("   6. Auto-advance to next rail")
    # Print a blank line for spacing
    print()
    # Print the list of all power rails that this test covers
    print(" Rails to be tested:")
    # List each rail by name on one line
    print("   3V6, 3V3, 2V5, 1V8, 1V35, 1V_PS, 1V_PL, 1V1_E0, 2V5_E0, 1V8_E0")
    # Print a blank line for spacing
    print()
    # Print a closing separator line to end the banner
    print("=" * 70)

# [Blank line for visual separation]

# [Blank line for visual separation]
def main():
    # This is the main entry point — the function that runs when the engineer launches this script from the terminal
    """Main entry point"""
    # Create an argument parser object that will handle command-line flags passed by the engineer
    parser = argparse.ArgumentParser(
        # Set the description text shown in the help output
        description="Load Transient Response Test Runner",
        # Use raw description formatting so that the epilog text preserves newlines
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # Define the examples section shown at the bottom of the help output
        epilog="""
Examples:
  %(prog)s                          Auto-detect and run all rails
  %(prog)s --list                   List available VISA instruments
  %(prog)s --rails 3V6,3V3,1V8      Test only specific rails
  %(prog)s --scope USB0::... --load USB0::...   Specify instrument addresses
        """
    )

    # Add the --list flag; when provided, the script lists all detected instruments and exits without running a test
    parser.add_argument('--list', action='store_true',
                        help='List available VISA instruments and exit')
    # Add the --scope flag; the engineer can provide the exact VISA address of the oscilloscope to skip auto-detection
    parser.add_argument('--scope', type=str, default=None,
                        help='Oscilloscope VISA address')
    # Add the --load flag; the engineer can provide the exact VISA address of the electronic load to skip auto-detection
    parser.add_argument('--load', type=str, default=None,
                        help='Electronic load VISA address')
    # Add the --rails flag; the engineer can provide a comma-separated list of rail names to test only specific rails
    parser.add_argument('--rails', type=str, default=None,
                        help='Comma-separated list of rails to test (e.g., "3V6,3V3,1V8")')
    # Add the --output flag; the engineer can specify a custom folder path where all test results and screenshots are saved
    parser.add_argument('--output', type=str, default='load_transient_results',
                        help='Output directory for results')

    # Parse all command-line arguments provided when the script was launched and store them in 'args'
    args = parser.parse_args()

    # Print the startup banner with the test name and description
    print_banner()

    # Check if the engineer used the --list flag to request a list of available instruments
    if args.list:
        # Call the function that scans for and lists all connected VISA instruments
        list_visa_resources()
        # Exit after listing instruments — no test is run
        return 0

    # Store the oscilloscope address from the command-line flag (None if not provided, which triggers auto-detection)
    scope_addr = args.scope
    # Store the electronic load address from the command-line flag (None if not provided)
    load_addr = args.load

    # Inform the engineer how instruments will be found — either from provided addresses or auto-detection
    if scope_addr and load_addr:
        # Both addresses were provided, so print them for confirmation
        print(f"\nUsing specified instruments:")
        # Print the oscilloscope address
        print(f"  Oscilloscope:    {scope_addr}")
        # Print the electronic load address
        print(f"  Electronic Load: {load_addr}")
    else:
        # At least one address is missing, so inform the engineer that auto-detection will be attempted
        print("\nAuto-detection will be performed during initialization...")

    # Attempt to import the main test class from the test module file in the same folder
    try:
        # Import the LoadTransientTest class from the load_transient_response_test.py file
        from load_transient_response_test import LoadTransientTest
    # Handle the case where the test module cannot be found or imported
    except ImportError as e:
        # Print the exact import error so the engineer can diagnose what is missing
        print(f"\nERROR: Failed to import test module: {e}")
        # Print a suggestion to check the file location
        print("Make sure load_transient_response_test.py is in the same directory")
        # Return error code 1 to signal that the script failed before running any tests
        return 1

    # Determine which rails the engineer wants to test
    rails_to_test = None
    # Check if the engineer provided a specific list of rails via the --rails flag
    if args.rails:
        # Rails specified via command line - use directly
        # Split the comma-separated string and strip any extra whitespace from each rail name
        rails_to_test = [r.strip() for r in args.rails.split(',')]
        # Print the list of rails to confirm what will be tested
        print(f"\nRails to test: {', '.join(rails_to_test)}")
    else:
        # No rails were specified; show the interactive menu so the engineer can select them
        rails_to_test = interactive_rail_selector(LoadTransientTest.RAIL_CONFIGS)
        # Check if the engineer cancelled the selection (returned None)
        if rails_to_test is None:
            # Print a cancellation message
            print("Test cancelled.")
            # Exit cleanly with code 0 (no error)
            return 0
        # Check if the engineer confirmed but left all rails deselected
        if not rails_to_test:
            # Inform the engineer that nothing was selected
            print("No rails selected. Exiting.")
            # Exit cleanly with code 0
            return 0
        # Print the selected rails to confirm what will be tested
        print(f"\nRails to test: {', '.join(rails_to_test)}")

    # Create the main test object (this also triggers instrument auto-detection if addresses are None)
    try:
        # Instantiate the LoadTransientTest class with the oscilloscope address, load address, and output directory
        test = LoadTransientTest(
            # Pass the oscilloscope VISA address (may be None to trigger auto-detection)
            oscilloscope_address=scope_addr,
            # Pass the electronic load VISA address (may be None to trigger auto-detection)
            electronic_load_address=load_addr,
            # Pass the output directory where results, screenshots, and reports will be saved
            output_dir=args.output
        )

        # Verify that both required instruments were found (either manually specified or auto-detected)
        if not test.scope_address or not test.load_address:
            # Print an error block explaining which instruments are missing
            print("\n" + "=" * 70)
            print("ERROR: Required instruments not found!")
            print("=" * 70)
            # If the oscilloscope was not found, say so and tell the engineer how to fix it
            if not test.scope_address:
                print("\n  Missing: Oscilloscope")
                print("    Use --scope <address> to specify manually")
            # If the electronic load was not found, say so and tell the engineer how to fix it
            if not test.load_address:
                print("\n  Missing: Electronic Load (Keithley 2380)")
                print("    Use --load <address> to specify manually")
            # Suggest running with --list to see all available instruments
            print("\n  Use --list to see all available instruments")
            print("=" * 70)
            # Return error code 1 because the test cannot proceed without both instruments
            return 1

        # Print the addresses of both instruments to confirm they are ready
        print(f"\n  Instruments ready:")
        # Print the detected or specified oscilloscope address
        print(f"  Oscilloscope:    {test.scope_address}")
        # Print the detected or specified electronic load address
        print(f"  Electronic Load: {test.load_address}")

    # Handle any unexpected error that occurs during test object creation or instrument detection
    except Exception as e:
        # Print the error message so the engineer can see what went wrong
        print(f"\nERROR: Failed to initialize test: {e}")
        # Return error code 1 to indicate failure
        return 1

    # Print safety reminders before the test begins
    print("\n" + "-" * 70)
    # Print a bold safety heading
    print("SAFETY REMINDER:")
    # Remind the engineer that the device under test must already be powered and stable before the test starts
    print("  - Ensure DUT is powered and stable")
    # Remind the engineer to verify all probe connections before starting
    print("  - Verify probe connections and ground references")
    # Warn the engineer about the maximum current the electronic load will draw during the test
    print("  - Electronic load will draw up to 1.5A during testing")
    # Print a closing divider
    print("-" * 70)

    # Wait for the engineer to confirm all connections are made before starting the test
    response = input("\nPress ENTER to start the test sequence (or 'q' to quit): ").strip().lower()
    # Check if the engineer typed 'q', 'quit', or 'exit' to cancel the test
    if response in ['q', 'quit', 'exit']:
        # Print a cancellation message
        print("Test cancelled.")
        # Return 0 to exit cleanly
        return 0

    # Run the full test sequence for all selected rails and store the overall pass/fail result
    success = test.run_test_sequence(rails=rails_to_test)

    # Print a blank line after the test finishes before the save/discard prompt
    print()
    # Enter a loop that repeatedly asks the engineer whether to keep or delete the test results
    while True:
        # Ask the engineer whether to save or discard the results
        save_resp = input("  Save results? [Y/n]: ").strip().lower()
        # Check if the engineer pressed Enter (accept default 'yes'), typed 'y', or typed 'yes'
        if save_resp in ('', 'y', 'yes'):
            # Print the path where results have been saved
            print(f"  Results saved: {test.output_dir}")
            # Print a blank line for spacing
            print()
            # Exit the save/discard loop
            break
        # Check if the engineer typed 'n' or 'no' to discard the results
        elif save_resp in ('n', 'no'):
            # Import the shutil library which provides high-level file operations including folder deletion
            import shutil
            # Import the subprocess library which allows Python to run shell commands like 'rmdir'
            import subprocess
            # Close all open log file handlers to release the log file before attempting to delete it
            for handler in list(test._logger.handlers):
                # Attempt to close each handler that is managing a log file
                try:
                    # Close the log file handler, releasing the file lock
                    handler.close()
                # If closing a handler fails, ignore the error and continue
                except Exception:
                    pass
                # Remove the handler from the logger so it no longer writes to the file
                test._logger.removeHandler(handler)
            # Attempt to delete the entire results folder using the Windows 'rmdir' command (more reliable than Python's shutil on OneDrive-synced folders)
            try:
                subprocess.run(
                    # Run the Windows command-line rmdir command with /s (recursive) and /q (quiet/no prompts)
                    ['cmd', '/c', 'rmdir', '/s', '/q', str(test.output_dir)],
                    # Suppress the command's own output so it doesn't clutter the terminal
                    capture_output=True, timeout=5
                )
            # If the subprocess command fails for any reason, silently continue and try Python's shutil instead
            except Exception:
                pass
            # If the folder still exists after the Windows command, try deleting it with Python's shutil library
            if test.output_dir.exists():
                shutil.rmtree(test.output_dir, ignore_errors=True)
            # Check if the folder was successfully deleted
            if test.output_dir.exists():
                # Warn the engineer that the folder could not be fully deleted, possibly because OneDrive is still syncing it
                print(f"  WARNING: Could not fully delete run folder (OneDrive may still be syncing).")
                # Tell the engineer to delete it manually and show the path
                print(f"  Delete manually: {test.output_dir}")
            else:
                # Confirm to the engineer that the results have been discarded and the folder is gone
                print("  Results discarded — run folder deleted.")
            # Print a blank line for spacing
            print()
            # Exit the save/discard loop
            break

    # Return 0 if the overall test passed, or 1 if it failed, so the calling process or CI system can detect the result
    return 0 if success else 1

# [Blank line for visual separation]

# [Blank line for visual separation]
# This block ensures that the main() function is only called when this script is run directly,
# not when it is imported as a module by another Python file
if __name__ == "__main__":
    # Call main() and pass its return code to sys.exit(), which sets the process exit code
    # (0 = success, 1 = failure) so that automated systems and CI pipelines can detect the test result
    sys.exit(main())
