# Tell the operating system to run this file using Python 3
#!/usr/bin/env python3
"""
Power Sequencing Test — Runner

Run this script to execute the power sequencing test.

Usage:
    python run_power_sequencing_test.py                        # Interactive mode selector
    python run_power_sequencing_test.py --mode full            # Full test (Config 1 + Config 2)
    python run_power_sequencing_test.py --mode config1         # Config 1 rails only
    python run_power_sequencing_test.py --mode config2         # Config 2 rails only
    python run_power_sequencing_test.py --mode capture         # Power-cycle + screenshots, no analysis
    python run_power_sequencing_test.py --mode reanalyze       # Re-analyse without power-cycling
    python run_power_sequencing_test.py --output PATH          # Override output directory
    python run_power_sequencing_test.py --verbose              # Verbose instrument logging
"""

# [Blank line for visual separation]

# Load the 'sys' library which allows the program to exit cleanly and manage module paths
import sys
# Load the 'argparse' library which reads and validates command-line flags typed by the engineer
import argparse
# Load the 'logging' library which controls how diagnostic messages are recorded during the test
import logging
# Load 'Path' from the 'pathlib' library which makes it easy to build and navigate file-system paths
from pathlib import Path

# [Blank line for visual separation]

# Add the parent folder of this script to Python's search path so shared modules can be found
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add the folder that contains this script itself to Python's search path as well
sys.path.insert(0, str(Path(__file__).parent))

# [Blank line for visual separation]

# [Blank line for visual separation]

# Define a helper function that switches on colour/ANSI escape-code support in the Windows terminal
def _enable_ansi():
    """Enable ANSI escape codes on Windows 10+."""
    # Begin a block that tries to enable ANSI colour codes; if it fails the program continues silently
    try:
        # Import 'ctypes' which lets Python call low-level Windows system functions
        import ctypes
        # Call the Windows API to switch the console into a mode that understands colour escape codes
        ctypes.windll.kernel32.SetConsoleMode(
            # Get a handle to the standard output (stdout) stream, identified by the number -11
            ctypes.windll.kernel32.GetStdHandle(-11), 7
        )
    # Catch any error that occurs (e.g., running on an old Windows version that does not support this)
    except Exception:
        # Do nothing — just continue without colour support rather than crashing
        pass

# [Blank line for visual separation]

# [Blank line for visual separation]

# Define a helper function that configures how much detail the program prints to its log
def _setup_logging(verbose: bool):
    # If the engineer passed --verbose, use DEBUG level (maximum detail); otherwise only show warnings
    level = logging.DEBUG if verbose else logging.WARNING
    # Apply the chosen log level and a consistent timestamp-plus-message format to all log output
    logging.basicConfig(
        # Set the minimum severity of messages that will actually be shown
        level=level,
        # Define the layout of each log line: time, severity label, module name, and the message
        format='%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
        # Format the timestamp as hours:minutes:seconds (no date needed for a short test run)
        datefmt='%H:%M:%S'
    )

# [Blank line for visual separation]

# [Blank line for visual separation]

# Draw a decorative horizontal divider to separate this section of the file visually
# ─────────────────────────────────────────────────────────────────────────────
# Label this section of the file as the interactive mode selector
# Interactive mode selector
# Draw a closing decorative divider for this section header
# ─────────────────────────────────────────────────────────────────────────────

# [Blank line for visual separation]

# Define the function that shows the engineer the 5-option test-mode menu and waits for a choice
def interactive_mode_selector() -> str:
    """
    Interactive 5-option test mode selector.

    Controls:
        UP / DOWN arrows  — Move between options
        TAB or SPACE      — Select the highlighted option
        ENTER             — Confirm and run
        Q or ESC          — Cancel

    Returns:
        One of: "full", "config1", "config2", "capture", "reanalyze"
        or None if cancelled.
    """
    # Import 'msvcrt' which is a Windows-only library for reading individual key presses without Enter
    import msvcrt

    # Switch on ANSI colour support so the menu arrows and highlights display correctly
    _enable_ansi()

    # Build a list of all five test modes that the engineer can choose from
    options = [
        # First option: run both Config 1 and Config 2 back-to-back (two power cycles)
        {
            # The internal key used by the rest of the program to identify this mode
            'key':   'full',
            # The short human-readable label shown in the menu
            'label': 'Full Test',
            # The longer description displayed next to the label in the menu
            'desc':  'Config 1 + Config 2  (complete power sequencing — 2 power cycles)',
        },
        # Second option: test only the lower-voltage rails in Config 1
        {
            # The internal key for Config 1 mode
            'key':   'config1',
            # The short label for Config 1
            'label': 'Config 1 Only',
            # Description listing the specific rails and number of power cycles
            'desc':  '1V0PL, 1V8, 1V0PS, 1V35  →  lower rails, 1 power cycle',
        },
        # Third option: test only the higher-voltage rails in Config 2
        {
            # The internal key for Config 2 mode
            'key':   'config2',
            # The short label for Config 2
            'label': 'Config 2 Only',
            # Description listing the specific rails and number of power cycles
            'desc':  '2V5, 1V8, 3V3, 1V35  →  higher rails, 1 power cycle',
        },
        # Fourth option: take oscilloscope screenshots but skip all numerical cursor analysis
        {
            # The internal key for capture-only mode
            'key':   'capture',
            # The short label for capture mode
            'label': 'Capture Only',
            # Description explaining that this mode skips the analysis step
            'desc':  'Power-cycle + full screenshots, skip cursor analysis',
        },
        # Fifth option: analyse a waveform already stored on the scope without power-cycling the DUT
        {
            # The internal key for re-analyse mode
            'key':   'reanalyze',
            # The short label for re-analyse mode
            'label': 'Re-analyse',
            # Description explaining that the scope keeps its current waveform
            'desc':  'Scope already triggered — skip power cycle, re-run analysis only',
        },
    ]

    # Track which option is currently marked as selected (the filled radio button), starting at index 0
    selected = 0   # index of currently selected option (radio button)
    # Track which row the highlight cursor is on; starts at the top row (index 0)
    cursor   = 0   # index of highlighted row

    # Define an inner function that builds the text lines for the menu display
    def render():
        # Start with an empty list that will hold each line of menu text
        lines = []
        # Add a blank line at the top for visual breathing room
        lines.append("")
        # Add the menu title so the engineer knows what they are looking at
        lines.append("  TEST MODE SELECTION")
        # Add a decorative horizontal rule under the title
        lines.append("  " + "=" * 66)
        # Add the keyboard control hint so the engineer knows which keys to press
        lines.append("  UP/DOWN: Navigate | TAB: Select | ENTER: Run | Q: Quit")
        # Add a blank line between the header and the list of options
        lines.append("")
        # Loop through each option and build the display line for that row
        for i, opt in enumerate(options):
            # Show a filled radio button "(X)" next to the currently selected option, empty "(  )" for all others
            marker = "(X)" if i == selected else "( )"
            # Show ">>" to indicate the row the keyboard cursor is currently on; "  " otherwise
            arrow  = ">>" if i == cursor else "  "
            # Combine the arrow, radio marker, label (padded to 18 characters), and description into one line
            lines.append(f"  {arrow} {marker}  {opt['label']:<18}  {opt['desc']}")
        # Add a blank line after the list of options
        lines.append("")
        # Show a one-line reminder of which mode is currently selected
        lines.append(f"  Mode: {options[selected]['label']}")
        # Return the completed list of lines ready for printing
        return lines

    # Call render() once to draw the menu for the first time
    display_lines = render()
    # Print each line of the menu to the terminal
    for line in display_lines:
        # Write one menu line to the screen
        print(line)
    # Force all buffered output to appear on screen immediately
    sys.stdout.flush()

    # Enter a loop that keeps waiting for key presses until the engineer confirms or cancels
    while True:
        # Read exactly one key press from the keyboard without waiting for Enter
        key = msvcrt.getch()

        # If the engineer pressed Enter, confirm the current selection and return its key string
        if key == b'\r':                          # ENTER — confirm
            # Print a blank line so the terminal looks tidy after the menu closes
            print()
            # Return the internal key string (e.g. "full", "config1") of the chosen option
            return options[selected]['key']

        # If the engineer pressed Tab or Space, mark the highlighted row as the chosen option
        elif key in (b'\t', b' '):                # TAB / SPACE — select current
            # Move the selection marker to whichever row the cursor is currently on
            selected = cursor

        # Windows sends a two-byte sequence for arrow keys; the first byte is a prefix
        elif key in (b'\xe0', b'\x00'):           # Arrow key prefix
            # Read the second byte which identifies which arrow key was actually pressed
            key2 = msvcrt.getch()
            # If the second byte means UP arrow, move the cursor one row higher (wrapping at the top)
            if key2 == b'H':                      # UP
                cursor = (cursor - 1) % len(options)
            # If the second byte means DOWN arrow, move the cursor one row lower (wrapping at the bottom)
            elif key2 == b'P':                    # DOWN
                cursor = (cursor + 1) % len(options)

        # If the engineer pressed Q, lowercase q, or Escape, cancel the menu and return nothing
        elif key in (b'q', b'Q', b'\x1b'):        # Q / ESC — cancel
            # Print a cancellation message so the engineer sees the program stopped cleanly
            print("\n  Cancelled.")
            # Return None to signal that no mode was chosen
            return None

        # Any other key press is ignored; jump back to the top of the loop without redrawing
        else:
            continue

        # Redraw in-place
        # Rebuild the menu lines with the updated cursor or selection state
        display_lines = render()
        # Move the terminal cursor up by the number of lines the menu occupies, to overwrite them
        sys.stdout.write(f"\033[{len(display_lines)}A")
        # Overwrite each existing menu line with the newly rendered version
        for line in display_lines:
            # Erase the current terminal line then write the updated content followed by a newline
            sys.stdout.write(f"\033[2K{line}\n")
        # Push all the redrawn lines to the screen immediately
        sys.stdout.flush()

# [Blank line for visual separation]

# [Blank line for visual separation]

# Draw a decorative divider to mark the start of the output-directory section
# ─────────────────────────────────────────────────────────────────────────────
# Label this section as the output directory prompt
# Output directory prompt
# Draw the closing divider for this section header
# ─────────────────────────────────────────────────────────────────────────────

# [Blank line for visual separation]

# Define the function that asks the engineer where to save the test results
def prompt_output_directory(cfg_output_dir: str = None) -> str:
    # Use the path from the config file if one was provided; otherwise fall back to a sensible default name
    default_path = cfg_output_dir or "power_sequencing_results"

    # Print a blank line before the section box for visual separation
    print()
    # Print the top border of the output directory selection box
    print("=" * 70)
    # Print the section title inside the box
    print("  OUTPUT DIRECTORY SELECTION")
    # Print the bottom border of the selection box
    print("=" * 70)
    # Print a blank line inside the box for spacing
    print()
    # Tell the engineer what the default save path is (taken from the config file)
    print(f"  Default path (from config): {default_path}")
    # Print a blank line for visual spacing
    print()
    # Print the heading for the list of choices
    print("  Options:")
    # Show option 1: accept the default path without typing anything
    print("    [1] Use default path")
    # Show option 2: type in a custom folder path
    print("    [2] Enter custom path")
    # Print a blank line after the options list
    print()

    # Keep asking until the engineer gives a valid answer
    while True:
        # Wait for the engineer to type "1" or "2" and press Enter; remove any surrounding whitespace
        choice = input("  Select option (1 or 2): ").strip()
        # If the engineer chose option 1, use the default path
        if choice == "1":
            # Confirm which path will be used
            print(f"  Using: {default_path}")
            # Print a blank line after the confirmation message
            print()
            # Return the default path to the caller
            return default_path
        # If the engineer chose option 2, ask them to type a custom folder path
        elif choice == "2":
            # Wait for the engineer to type the path and press Enter; trim whitespace from both ends
            custom_path = input("  Enter output directory path: ").strip()
            # If the engineer pressed Enter without typing anything, show an error and ask again
            if not custom_path:
                # Tell the engineer the path field cannot be left blank
                print("  ERROR: Path cannot be empty. Try again.")
                # Go back to the top of the loop to ask again
                continue
            # Confirm which custom path will be used
            print(f"  Using: {custom_path}")
            # Print a blank line after the confirmation message
            print()
            # Return the custom path to the caller
            return custom_path
        # If the engineer typed something other than "1" or "2", tell them and ask again
        else:
            # Inform the engineer that only "1" or "2" are valid inputs
            print("  Invalid choice. Please enter 1 or 2.")

# [Blank line for visual separation]

# [Blank line for visual separation]

# Draw a decorative divider to mark the start of the setup instructions section
# ─────────────────────────────────────────────────────────────────────────────
# Label this section as the detailed setup instructions printer
# Detailed setup instructions (mode-aware)
# Draw the closing divider for this section header
# ─────────────────────────────────────────────────────────────────────────────

# [Blank line for visual separation]

# Define the function that prints all the wiring and instrument setup steps the engineer must follow
def print_setup_instructions(instr: dict, psu_cfg: dict, scp_cfg: dict, mode: str):
    # Pull the PSU's VISA address string from the instruments dictionary; default to "?" if missing
    psu_addr   = instr.get("psu", "?")
    # Pull the oscilloscope's VISA address string from the instruments dictionary; default to "?" if missing
    scp_addr   = instr.get("scope", "?")
    # Read the PSU output channel number (e.g. 1) from the PSU settings config block
    ch         = psu_cfg.get("channel", 1)
    # Read the input voltage the PSU will apply to the DUT (e.g. 5.0 V)
    vin        = psu_cfg.get("vin_v", 5.0)
    # Read the current limit the PSU will enforce to protect the DUT
    i_lim      = psu_cfg.get("current_limit_a", "?")
    # Read the over-voltage protection trip level from the PSU settings
    ovp        = psu_cfg.get("ovp_level_v", "?")
    # Read the scope timebase in seconds-per-division and convert it to milliseconds for the display
    tb_ms      = scp_cfg.get("timebase_s_per_div", 1e-3) * 1e3
    # Read the pre-trigger percentage (how much of the waveform is captured before the trigger event)
    pre_trig   = scp_cfg.get("pretrigger_pct", 20)

    # Work out whether the PSU will be used: it is not needed for re-analyse mode
    need_psu      = mode != "reanalyze"
    # Work out whether Config 1 probe wiring instructions are needed for the chosen mode
    need_config1  = mode in ("full", "config1", "capture")
    # Work out whether Config 2 probe wiring instructions are needed for the chosen mode
    need_config2  = mode in ("full", "config2", "capture")
    # Work out whether a manual DMM reading will be required (only for full test and Config 1)
    need_dmm      = mode in ("full", "config1")

    # Print a blank line before the setup instructions box
    print()
    # Print the top border of the setup instructions box
    print("=" * 70)
    # Print the section title so the engineer knows these are the steps to complete before starting
    print("  SETUP INSTRUCTIONS — Complete these steps before starting")
    # Print the bottom border of the setup instructions box
    print("=" * 70)

    # Print a blank line before Step 1
    print()
    # Print the Step 1 heading about the DUT's initial power state
    print("  STEP 1 — DUT State")
    # Print a short horizontal rule under the step heading
    print("  " + "-" * 60)
    # If re-analyse mode was chosen, the DUT is already powered from a previous run
    if mode == "reanalyze":
        # Remind the engineer the DUT should already have been powered during the earlier capture run
        print("  The DUT should already be powered from a previous capture.")
        # Warn the engineer that the scope must still have the waveform from that earlier capture
        print("  The scope must be in STOP state with a valid waveform acquired.")
        # Make clear that the engineer must NOT power-cycle the DUT before re-analysis
        print("  Do NOT power-cycle the DUT — the script will skip the trigger step.")
    # For all other modes, the DUT must start powered off so the script can control the power-on moment
    else:
        # Instruct the engineer to make sure the DUT is off before any probes or leads are touched
        print("  Ensure the DUT board is POWERED OFF before making connections.")
        # Explain that the script itself will apply power at the correct point in the test sequence
        print("  The script will apply power automatically at the correct moment.")

    # Print a blank line before Step 2
    print()
    # Print the Step 2 heading about wiring the power supply to the DUT
    print("  STEP 2 — PSU Wiring  (Keithley Power Supply)")
    # Print a short horizontal rule under the step heading
    print("  " + "-" * 60)
    # Only show PSU wiring details if the mode actually uses the PSU
    if need_psu:
        # Tell the engineer which PSU output channel the leads must be connected to
        print(f"  Channel : CH{ch}")
        # Tell the engineer to connect the red (positive) lead to the DUT's VIN input
        print(f"  + terminal  (red lead)    →  DUT VIN positive input")
        # Tell the engineer to connect the black (negative) lead to the DUT's GND return
        print(f"  − terminal  (black lead)  →  DUT GND / return")
        # Print a blank line before the list of PSU settings
        print()
        # Heading for the programmatic PSU settings that the script will apply automatically
        print(f"  Settings applied by script:")
        # Show the voltage the script will program onto the PSU output
        print(f"    Output voltage   : {vin} V")
        # Show the current limit the script will program to protect the DUT
        print(f"    Current limit    : {i_lim} A")
        # Show the over-voltage protection level the script will configure
        print(f"    OVP level        : {ovp} V")
        # Print a blank line before the manual verification checklist
        print()
        # Heading for the items the engineer should visually check on the PSU front panel
        print(f"  Verify on PSU front panel:")
        # Remind the engineer to confirm the PSU channel output is currently switched off
        print(f"    CH{ch} output is OFF (output button NOT lit)")
        # Remind the engineer to check there are no fault lights or over-voltage warnings showing
        print(f"    No over-voltage or fault indicators showing")
        # Display the VISA address so the engineer can verify the cable goes to the correct instrument
        print(f"  VISA address : {psu_addr}")
    # If re-analyse mode was chosen, the PSU is not needed so skip the wiring step
    else:
        # Tell the engineer to skip the PSU step because it is not used in re-analyse mode
        print("  PSU not used in Re-analyse mode — skip this step.")

    # Print a blank line before Step 3
    print()
    # Print the Step 3 heading about connecting the oscilloscope probes to the DUT test points
    print("  STEP 3 — Oscilloscope Probe Connections")
    # Print a short horizontal rule under the step heading
    print("  " + "-" * 60)

    # Only show Config 1 probe table if the current mode needs Config 1 measurements
    if need_config1:
        # Print a blank line before the Config 1 probe table
        print()
        # Heading telling the engineer these are the Config 1 probe positions
        print("  CONFIG 1  (connect these probes now):")
        # Print the top border of the probe-mapping table
        print("  ┌─────────────────────────────────────────────────────┐")
        # Print the column headers of the probe-mapping table
        print("  │  Scope CH  │  Rail   │  Test Point  │  Note         │")
        # Print the header separator row
        print("  ├─────────────────────────────────────────────────────┤")
        # Row for Channel 1: the 1V0PL rail at test point TP8, which is also the trigger source
        print("  │  CH1       │  1V0PL  │  TP8         │  ← TRIGGER   │")
        # Row for Channel 2: the 1V8 rail at test point TP6
        print("  │  CH2       │  1V8    │  TP6         │               │")
        # Row for Channel 3: the 1V0PS rail at test point TP5
        print("  │  CH3       │  1V0PS  │  TP5         │               │")
        # Row for Channel 4: the 1V35 rail at test point TP7
        print("  │  CH4       │  1V35   │  TP7         │               │")
        # Print the bottom border of the probe-mapping table
        print("  └─────────────────────────────────────────────────────┘")
        # Print a blank line after the probe table
        print()
        # Heading for probe hardware settings that the engineer must configure manually before connecting
        print("  Probe settings (all channels) — set BEFORE connecting:")
        # Instruct the engineer to set the slide switch on every probe body to the ×10 attenuation position
        print("    Attenuation : 10×  ← slide switch on probe body to ×10")
        # Note that DC coupling will be set automatically by the script; the engineer does not need to do this
        print("    Coupling    : DC   (configured automatically by script)")
        # Note that the 20 MHz bandwidth limit will be applied automatically by the script
        print("    BW limit    : 20 MHz  (configured automatically by script)")
        # Tell the engineer to clip the probe ground lead to the nearest ground point on the DUT board
        print("    Ground clip : nearest GND via / plane on DUT board")
        # Print a blank line before the trigger settings
        print()
        # Heading for the oscilloscope trigger settings that the script will configure automatically
        print(f"  Trigger (set automatically by script):")
        # State that the trigger source will be CH1, which measures the 1V0PL rail at TP8
        print(f"    Source : CH1  (1V0PL, TP8)")
        # State that the trigger edge direction is rising (voltage going up)
        print(f"    Edge   : Rising")
        # State the trigger threshold voltage (20% of the 1.0 V nominal rail)
        print(f"    Level  : 0.20 V  (20% of 1.0 V nominal)")
        # Show the trigger mode, pre-trigger percentage, and time base in a single summary line
        print(f"    Mode   : Single-shot  |  {pre_trig}% pre-trigger")
        # Show the timebase and calculated pre/post trigger window durations in milliseconds
        print(f"    Time base : {tb_ms:.0f} ms/div  "
              f"({int(pre_trig * tb_ms / 10)} ms pre-trigger  "
              f"{int((100 - pre_trig) * tb_ms / 10)} ms post-trigger)")

    # Show Config 2 probe instructions only if Config 2 is needed AND this is not a full test
    # (the full-test case is handled separately below with its own move-probes instruction)
    if need_config2 and mode != "full":
        # Print a blank line before the Config 2 probe table
        print()
        # Heading telling the engineer these are the Config 2 probe positions
        print("  CONFIG 2  (connect these probes now):")
        # Print the top border of the Config 2 probe-mapping table
        print("  ┌─────────────────────────────────────────────────────┐")
        # Print the column headers of the Config 2 probe table
        print("  │  Scope CH  │  Rail   │  Test Point  │  Note         │")
        # Print the header separator row
        print("  ├─────────────────────────────────────────────────────┤")
        # Row for Channel 1: the 2V5 rail at test point TP9, which is the Config 2 trigger source
        print("  │  CH1       │  2V5    │  TP9         │  ← TRIGGER   │")
        # Row for Channel 2: the 1V8 rail at test point TP6 (same as Config 1)
        print("  │  CH2       │  1V8    │  TP6         │               │")
        # Row for Channel 3: the 3V3 rail at test point TP10
        print("  │  CH3       │  3V3    │  TP10        │               │")
        # Row for Channel 4: the 1V35 rail at test point TP7 (same as Config 1)
        print("  │  CH4       │  1V35   │  TP7         │               │")
        # Print the bottom border of the Config 2 probe-mapping table
        print("  └─────────────────────────────────────────────────────┘")
        # Print a blank line after the Config 2 probe table
        print()
        # Heading for Config 2 probe hardware settings the engineer must configure before connecting
        print("  Probe settings (all channels) — set BEFORE connecting:")
        # Instruct the engineer to set all probe slide switches to the ×10 position
        print("    Attenuation : 10×  ← slide switch on probe body to ×10")
        # DC coupling will be configured by the script automatically
        print("    Coupling    : DC   (configured automatically by script)")
        # 20 MHz BW limit will be configured by the script automatically
        print("    BW limit    : 20 MHz  (configured automatically by script)")
        # Remind the engineer to clip probe grounds to the nearest GND point on the DUT
        print("    Ground clip : nearest GND via / plane on DUT board")
        # Print a blank line before the Config 2 trigger settings
        print()
        # Heading for the Config 2 trigger settings that the script will apply
        print(f"  Trigger (set automatically by script):")
        # State that CH1 (2V5 at TP9) will be the trigger source for Config 2
        print(f"    Source : CH1  (2V5, TP9)")
        # State the trigger edge direction for Config 2
        print(f"    Edge   : Rising")
        # State the Config 2 trigger threshold voltage (20% of 2.5 V nominal)
        print(f"    Level  : 0.50 V  (20% of 2.5 V nominal)")
        # Show the trigger mode and pre-trigger percentage for Config 2
        print(f"    Mode   : Single-shot  |  {pre_trig}% pre-trigger")
        # Show the Config 2 timebase and pre/post trigger window durations
        print(f"    Time base : {tb_ms:.0f} ms/div  "
              f"({int(pre_trig * tb_ms / 10)} ms pre-trigger  "
              f"{int((100 - pre_trig) * tb_ms / 10)} ms post-trigger)")

    # For full-test mode, explain that the engineer will be asked to move probes between the two configs
    if mode == "full":
        # Print a blank line before the full-test probe-move instructions
        print()
        # Tell the engineer to start with Config 1 probes and that the script will pause before Config 2
        print("  CONFIG 1 first — after Config 1 capture is complete, the script")
        # Explain that the script will prompt the engineer to re-connect probes before the second power cycle
        print("  will prompt you to move the probes to CONFIG 2 before the second")
        # Explain where to move power cycle. Config 2 probe positions:
        print("  power cycle. Config 2 probe positions:")
        # List the Config 2 probe-to-test-point assignments compactly for quick reference
        print("    CH1 → 2V5 (TP9)    CH2 → 1V8 (TP6)")
        # Continue the compact probe list for CH3 and CH4
        print("    CH3 → 3V3 (TP10)   CH4 → 1V35 (TP7)")

    # For re-analyse mode, remind the engineer to have probes connected for the config they want to re-check
    if mode == "reanalyze":
        # Print a blank line before the re-analyse probe note
        print()
        # Instruct the engineer to connect probes for whichever config was captured earlier
        print("  Connect probes for whichever config is currently under test.")
        # Explain that the script will ask which config is connected before it starts the analysis
        print("  The script will ask which config is connected before analysing.")

    # Print a blank line before Step 4
    print()
    # Print the Step 4 heading about the optional DMM measurement of the 3V6 rail
    print("  STEP 4 — DMM Measurement  (3V6 confirmation)")
    # Print a short horizontal rule under the step heading
    print("  " + "-" * 60)
    # Show DMM instructions only for modes that include the 3V6 manual check
    if need_dmm:
        # Tell the engineer where to connect the DMM probes on the DUT
        print("  Connect DMM probes to the 3V6 output rail on the DUT.")
        # Explain that the engineer will be prompted to read and type in the DMM value manually
        print("  The script will ask you to read and enter this value manually")
        # State the expected voltage range and clarify that the DMM is read by eye, not by USB
        print("  after Config 1 is captured. Expected: 3.50 V – 3.70 V.")
        # Confirm that the DMM does not need to be connected to the PC via USB
        print("  The DMM does NOT need to be connected to the PC.")
    # If the mode does not include a DMM check, tell the engineer to skip the step
    else:
        # Inform the engineer that this mode skips the DMM check entirely
        print("  DMM check not included in this mode — skip this step.")

    # Print a blank line before Step 5
    print()
    # Print the Step 5 heading about verifying the VISA (USB/LAN) connections to the instruments
    print("  STEP 5 — PC Connections via VISA")
    # Print a short horizontal rule under the step heading
    print("  " + "-" * 60)
    # Show the VISA address for the power supply so the engineer can confirm the cable is correct
    print(f"  PSU VISA address   : {psu_addr}")
    # Show the VISA address for the oscilloscope so the engineer can confirm the cable is correct
    print(f"  Scope VISA address : {scp_addr}")
    # Print a blank line after the VISA address list
    print()
    # Tell the engineer how to fix wrong VISA addresses
    print("  If either address looks wrong, edit power_sequencing_config.json")
    # Instruct the engineer to restart the script after editing the config file
    print("  and restart the script.")
    # Print a blank line before the instrument-discovery hint
    print()
    # Label the next line as a helpful command the engineer can run to list connected instruments
    print("  To list detected instruments:")
    # Print the one-line Python command that scans VISA and lists all found instruments
    print("    python -c \"import pyvisa; print(pyvisa.ResourceManager().list_resources())\"")

    # Print a blank line before Step 6
    print()
    # Print the Step 6 heading about physically powering on the instruments
    print("  STEP 6 — Power ON Instruments")
    # Print a short horizontal rule under the step heading
    print("  " + "-" * 60)
    # Tell the engineer to switch on both the PSU and the oscilloscope
    print("  Power on the Keithley PSU and the Keysight Oscilloscope.")
    # If the PSU will be used, remind the engineer to leave the DUT off until the script controls it
    if need_psu:
        # Remind the engineer to keep the DUT powered off; the script will turn the PSU output on at the right moment
        print("  Leave the DUT powered off — the PSU output will be controlled")
        # Clarify that the script toggles the PSU output channel at the exact moment required by the test
        print("  by the script. The script will toggle it at the correct moment.")
    # Warn the engineer not to arm the scope manually, because the script does this automatically
    print("  Do NOT press RUN or SINGLE on the scope manually —")
    # Explain that the script sends all scope configuration commands over VISA
    print("  the script configures and arms the scope automatically.")

    # Print a blank line before Step 7
    print()
    # Print the Step 7 heading about safety reminders
    print("  STEP 7 — Safety Reminders")
    # Print a short horizontal rule under the step heading
    print("  " + "-" * 60)
    # Remind the engineer of the maximum voltage that will be present on the DUT during the test
    print(f"  Voltages up to {vin} V will be applied to the DUT input.")
    # Warn the engineer not to touch the board or any leads once the test is running
    print("  Do NOT touch the board, leads, or probe tips once the test starts.")
    # Remind the engineer to physically check that all probe ground clips are firmly attached
    print("  Verify probe ground clips are securely attached before starting.")
    # Warn the engineer to keep all cables away from fans or any moving mechanical parts
    print("  Keep leads clear of fans or moving parts.")

    # Print a blank line before the closing border
    print()
    # Print the bottom border of the entire setup instructions box
    print("=" * 70)
    # Print a final blank line after the instructions box so the next output has breathing room
    print()

# [Blank line for visual separation]

# [Blank line for visual separation]

# Draw a decorative divider to mark the start of the banner section
# ─────────────────────────────────────────────────────────────────────────────
# Label this section as the banner printer
# Banner
# Draw the closing divider for this section header
# ─────────────────────────────────────────────────────────────────────────────

# [Blank line for visual separation]

# Define the function that prints the large introductory banner shown when the script first starts
def print_banner():
    # Print a blank line above the banner for visual separation
    print()
    # Print the top border of the banner box
    print("=" * 70)
    # Print the main test name in the banner
    print("  POWER SEQUENCING TEST")
    # Print a one-sentence description of what the test verifies
    print("  Verifies all power rails ramp in correct order within timing windows")
    # Print the bottom border of the banner box
    print("=" * 70)
    # Print a blank line inside the banner for spacing
    print()
    # List the instruments the test requires
    print("  Instruments : Keithley Power Supply  +  Keysight Oscilloscope")
    # Print a blank line before the modes list
    print()
    # Print the heading for the available test modes
    print("  Modes available:")
    # Describe Full Test mode
    print("    Full Test    — Config 1 + Config 2  (2 power cycles, all 6 rails)")
    # Describe Config 1 mode
    print("    Config 1     — 1V0PL, 1V8, 1V0PS, 1V35  (1 power cycle)")
    # Describe Config 2 mode
    print("    Config 2     — 2V5, 1V8, 3V3, 1V35  (1 power cycle)")
    # Describe Capture Only mode
    print("    Capture Only — Power-cycle + screenshots only, no cursor analysis")
    # Describe Re-analyse mode
    print("    Re-analyse   — Skip power cycle, analyse current scope waveform")
    # Print a blank line before the config-file reminder
    print()
    # Tell the engineer which file to edit to change instrument addresses or test parameters
    print("  Edit  power_sequencing_config.json  to change instrument addresses,")
    # List what can be changed in the config file
    print("  timing limits, vertical scales, and output directory.")
    # Print a blank line before the closing border
    print()
    # Print the bottom border of the banner box
    print("=" * 70)

# [Blank line for visual separation]

# [Blank line for visual separation]

# Draw a decorative divider to mark the start of the main function section
# ─────────────────────────────────────────────────────────────────────────────
# Label this section as the main entry point
# Main
# Draw the closing divider for this section header
# ─────────────────────────────────────────────────────────────────────────────

# [Blank line for visual separation]

# Define the main function that orchestrates the entire test run from start to finish
def main():
    # Switch on ANSI colour codes so banners and menus display correctly in the terminal
    _enable_ansi()

    # Create the command-line argument parser that will read flags typed after the script name
    parser = argparse.ArgumentParser(
        # Brief description shown when the engineer runs the script with --help
        description="Power Sequencing Test Runner",
        # Use the raw formatter so the epilog examples are printed exactly as typed
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # Multi-line usage examples shown at the bottom of the --help output
        epilog="""
Examples:
  python run_power_sequencing_test.py
  python run_power_sequencing_test.py --mode full
  python run_power_sequencing_test.py --mode config1
  python run_power_sequencing_test.py --mode config2
  python run_power_sequencing_test.py --mode capture
  python run_power_sequencing_test.py --mode reanalyze
  python run_power_sequencing_test.py --output D:/Results/Board_SN001
  python run_power_sequencing_test.py --verbose
        """
    )
    # Add the --mode flag which lets the engineer skip the interactive menu and specify a mode directly
    parser.add_argument(
        # The flag name as it must be typed on the command line
        '--mode',
        # Only these five strings are valid; anything else causes an error
        choices=['full', 'config1', 'config2', 'capture', 'reanalyze'],
        # If --mode is not provided, leave it as None so the interactive selector will run instead
        default=None,
        # Short description shown in the --help output
        help='Test mode (default: interactive selector)'
    )
    # Add the --output flag which lets the engineer specify a custom results folder from the command line
    parser.add_argument(
        # The flag name and its expected data type (a plain string path)
        '--output', type=str, default=None,
        # Short description shown in the --help output
        help='Base directory for results (default: path from power_sequencing_config.json)'
    )
    # Add the --verbose flag which switches on detailed instrument-level debug logging
    parser.add_argument(
        # The flag name; it takes no value — its presence alone switches verbose mode on
        '--verbose', action='store_true',
        # Short description shown in the --help output
        help='Enable verbose instrument-level logging'
    )

    # Parse the flags the engineer typed on the command line and store the results in 'args'
    args = parser.parse_args()
    # Configure the logging system using the verbosity the engineer requested
    _setup_logging(args.verbose)

    # Display the large introductory banner so the engineer can see the test name and available modes
    print_banner()

    # Try to import the main test module; if it is missing, show a clear error and exit
    try:
        # Import the test class and the loaded config dictionary from the test module
        from power_sequencing_test import PowerSequencingTest, _CFG
    # If the import fails (e.g. the file is missing or has a syntax error), catch the error
    except ImportError as e:
        # Tell the engineer which module could not be loaded and why
        print(f"\n  ERROR: Could not import test module: {e}")
        # Remind the engineer that the test module must live in the same folder as this script
        print("  Make sure power_sequencing_test.py is in the same directory.")
        # Return exit code 1 to indicate failure
        return 1

    # ── Config summary ────────────────────────────────────────────────────────
    # Extract the instrument addresses sub-dictionary from the loaded config
    instr   = _CFG.get("instrument_addresses", {})
    # Extract the PSU settings sub-dictionary from the loaded config
    psu_cfg = _CFG.get("psu_settings", {})
    # Extract the scope settings sub-dictionary from the loaded config
    scp_cfg = _CFG.get("scope_settings", {})
    # Extract the rail timing limits sub-dictionary from the loaded config
    limits  = _CFG.get("rail_timing_limits", {})

    # Print the section heading for the compact configuration summary
    print("  Configuration summary:")
    # Show the PSU VISA address from the config so the engineer can confirm it is correct
    print(f"    PSU address   : {instr.get('psu')}")
    # Show the scope VISA address from the config so the engineer can confirm it is correct
    print(f"    Scope address : {instr.get('scope')}")
    # Show the PSU channel number and the voltage it will supply to the DUT
    print(f"    PSU channel   : CH{psu_cfg.get('channel', 1)}  →  {psu_cfg.get('vin_v', 5.0)} V")
    # Show the oscilloscope timebase setting and pre-trigger percentage on a single line
    print(f"    Timebase      : {scp_cfg.get('timebase_s_per_div', 1e-3) * 1e3:.0f} ms/div  |  "
          f"Pre-trigger: {scp_cfg.get('pretrigger_pct', 20)}%")
    # Print a blank line before the Config 1 channel list
    print()
    # Print the heading for the Config 1 channel mapping table
    print("  Scope Config 1 channels:")
    # Loop through every channel defined for Config 1 and print its details
    for ch in PowerSequencingTest.CONFIG1_CHANNELS:
        # Look up the maximum allowed rise time for this rail; use None if not configured
        lim     = limits.get(ch.name, {}).get("max_time_ms", None)
        # Format the limit as a string with one decimal place, or "—" if no limit is set
        lim_str = f"{lim:.1f} ms" if lim else "—"
        # Print the channel number, rail name, test point, 90% threshold voltage, and timing limit
        print(f"    CH{ch.channel}: {ch.name:<8} ({ch.test_point})  "
              f"90% @ {ch.threshold_90pct_v:.3f} V  limit {lim_str}")
    # Print a blank line before the Config 2 channel list
    print()
    # Print the heading for the Config 2 channel mapping table
    print("  Scope Config 2 channels:")
    # Loop through every channel defined for Config 2 and print its details
    for ch in PowerSequencingTest.CONFIG2_CHANNELS:
        # Look up the maximum allowed rise time for this Config 2 rail
        lim     = limits.get(ch.name, {}).get("max_time_ms", None)
        # Format the limit as a string with one decimal place, or "—" if not configured
        lim_str = f"{lim:.1f} ms" if lim else "—"
        # Print the channel number, rail name, test point, 90% threshold voltage, and timing limit
        print(f"    CH{ch.channel}: {ch.name:<8} ({ch.test_point})  "
              f"90% @ {ch.threshold_90pct_v:.3f} V  limit {lim_str}")
    # Print a blank line after the configuration summary
    print()

    # ── Mode selection ────────────────────────────────────────────────────────
    # Check whether the engineer provided a --mode flag on the command line
    if args.mode:
        # Use the mode string exactly as typed on the command line
        mode = args.mode
        # Confirm to the engineer which mode was selected and that it came from the command-line flag
        print(f"  Mode: {mode}  (from --mode flag)")
        # Print a blank line after the mode confirmation
        print()
    # If no --mode flag was given, show the interactive menu so the engineer can choose
    else:
        # Show the 5-option interactive menu and wait for the engineer to choose which test mode to run
        mode = interactive_mode_selector()
        # If the engineer pressed Q or Escape to cancel, exit cleanly with success code 0
        if mode is None:
            return 0
        # Confirm which mode the engineer selected from the interactive menu
        print(f"  Running: {mode}")

    # ── Setup instructions (mode-aware) ───────────────────────────────────────
    # Print all the step-by-step wiring and instrument setup instructions tailored to the chosen mode
    print_setup_instructions(instr, psu_cfg, scp_cfg, mode)

    # ── Output directory selection ────────────────────────────────────────────
    # Start by checking whether the engineer specified a results folder with the --output flag
    output_dir = args.output
    # If no --output flag was given, ask the engineer to choose or confirm the output folder interactively
    if output_dir is None:
        # Read the output directory setting from the config file
        cfg_out = _CFG.get("output_dir", {})
        # If the config value is a dictionary extract the "path" key; if it is a plain string use it directly
        cfg_dir = (
            # Pull the "path" key from the dictionary form of the output_dir setting
            cfg_out.get("path", "power_sequencing_results")
            # Use isinstance to decide whether cfg_out is a dict or a plain string
            if isinstance(cfg_out, dict)
            # Convert the plain string value to a string (it may already be one, but this is safe)
            else str(cfg_out)
        )
        # Show the interactive output directory prompt and store what the engineer chooses
        output_dir = prompt_output_directory(cfg_dir)

    # ── Start confirmation ────────────────────────────────────────────────────
    # Ask the engineer to confirm all connections are in place before the test begins; allow quitting
    response = input("  All connections made? Press ENTER to start (or 'q' to quit): ").strip().lower()
    # If the engineer typed q, quit, or exit, cancel the test and exit cleanly
    if response in ('q', 'quit', 'exit'):
        # Print a cancellation message so the terminal does not look abandoned
        print("  Cancelled.")
        # Return exit code 0 to indicate a clean, user-requested exit
        return 0

    # ── Create test instance and run ──────────────────────────────────────────
    # Create the main test object which connects instruments and prepares to run the power sequencing test
    test    = PowerSequencingTest(output_dir=output_dir)
    # Execute the test in the chosen mode and capture whether it passed (True) or failed (False)
    success = test.run(mode=mode)

    # ── Save or discard prompt ────────────────────────────────────────────────
    # Print a blank line before the save/discard prompt
    print()
    # Loop until the engineer gives a valid yes or no answer
    while True:
        # Ask the engineer whether to keep the results folder that was just created
        save_resp = input("  Save results? [Y/n]: ").strip().lower()
        # If the engineer pressed Enter (blank), typed y, or typed yes, keep the results
        if save_resp in ('', 'y', 'yes'):
            # Tell the engineer exactly which folder the results were saved to
            print(f"  Results saved: {test._run_dir}")
            # Print a blank line after the confirmation message
            print()
            # Exit the save/discard loop
            break
        # If the engineer typed n or no, delete the results folder
        elif save_resp in ('n', 'no'):
            # Import 'shutil' which provides a function to delete entire folder trees
            import shutil
            # Import 'subprocess' which lets Python run external system commands
            import subprocess
            # Loop through all file handlers attached to the test logger so they can be closed cleanly
            for handler in list(test._logger.handlers):
                # Try to close the file handler so it releases its lock on any open log files
                try:
                    # Close this individual log handler
                    handler.close()
                # If closing fails (e.g. the handler was already closed), ignore the error
                except Exception:
                    # Do nothing — continue closing remaining handlers
                    pass
                # Remove this handler from the logger so it no longer writes to the (now closed) file
                test._logger.removeHandler(handler)
            # Try to delete the run folder using the Windows rmdir command (handles OneDrive-synced folders better)
            try:
                # Run the Windows command-line rmdir with /s (delete contents) and /q (no confirmation prompts)
                subprocess.run(
                    # Build the command as a list: cmd /c rmdir /s /q <folder path>
                    ['cmd', '/c', 'rmdir', '/s', '/q', str(test._run_dir)],
                    # Suppress the command's own output so it does not clutter the terminal
                    capture_output=True, timeout=5
                )
            # If the subprocess call itself fails (e.g. timeout or permission error), ignore and try shutil next
            except Exception:
                # Do nothing — fall through to the shutil.rmtree attempt below
                pass
            # If the folder still exists after the rmdir command, try again using Python's own shutil
            if test._run_dir.exists():
                # Delete the folder and all its contents; ignore any individual file errors
                shutil.rmtree(test._run_dir, ignore_errors=True)
            # Check one final time whether the folder was successfully removed
            if test._run_dir.exists():
                # Warn the engineer that the folder could not be fully deleted (likely due to OneDrive sync locks)
                print(f"  WARNING: Could not fully delete run folder (OneDrive may still be syncing).")
                # Tell the engineer the exact path so they can delete it manually later
                print(f"  Delete manually: {test._run_dir}")
            # If the folder no longer exists, confirm that the deletion succeeded
            else:
                # Confirm to the engineer that the results have been discarded and the folder is gone
                print("  Results discarded — run folder deleted.")
            # Print a blank line after the discard confirmation
            print()
            # Exit the save/discard loop
            break

    # Return 0 if the test passed, or 1 if it failed, so the calling shell can detect success or failure
    return 0 if success else 1

# [Blank line for visual separation]

# [Blank line for visual separation]

# This block runs only when the script is launched directly (not when imported as a module)
if __name__ == "__main__":
    # Run the main function and pass its return code to the operating system so CI tools can detect failures
    sys.exit(main())
