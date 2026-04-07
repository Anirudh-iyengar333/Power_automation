#!/usr/bin/env python3
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

import sys
import os
import argparse
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))


def _enable_ansi():
    """Enable ANSI escape codes on Windows 10+"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


def interactive_rail_selector(rail_configs):
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

    selected = [True] * len(rails)  # All selected by default
    cursor = 0

    def render():
        """Build display lines for the selector"""
        lines = []
        lines.append("")
        lines.append("  RAIL SELECTION")
        lines.append("  " + "=" * 62)
        lines.append("  UP/DOWN: Navigate | TAB: Toggle | ENTER: Run | A: All | Q: Quit")
        lines.append("")

        for i, r in enumerate(rails):
            marker = "[X]" if selected[i] else "[ ]"
            arrow = ">>" if i == cursor else "  "
            line = (
                f"  {arrow} {marker} {r['name']:<10} ({r['tp']:<5}) "
                f"{r['voltage']:>5.2f}V   {r['low']} -> {r['high']}mA"
            )
            lines.append(line)

        sel_names = [rails[i]['name'] for i in range(len(rails)) if selected[i]]
        lines.append("")
        if sel_names:
            lines.append(f"  Selected: {', '.join(sel_names)}  ({len(sel_names)} rails)")
        else:
            lines.append("  Selected: None  (use TAB to select rails)")
        return lines

    # Initial draw
    display_lines = render()
    for line in display_lines:
        print(line)
    sys.stdout.flush()

    while True:
        key = msvcrt.getch()

        if key == b'\r':  # Enter - confirm selection
            sel = [rails[i]['name'] for i in range(len(rails)) if selected[i]]
            if not sel:
                # Flash a message - need at least one rail
                continue
            print()
            return sel

        elif key == b'\t' or key == b' ':  # Tab or Space - toggle current rail
            selected[cursor] = not selected[cursor]

        elif key in (b'a', b'A'):  # Toggle all
            if all(selected):
                selected = [False] * len(rails)
            else:
                selected = [True] * len(rails)

        elif key == b'\xe0' or key == b'\x00':  # Special key prefix (arrows)
            key2 = msvcrt.getch()
            if key2 == b'H':  # Up arrow
                cursor = (cursor - 1) % len(rails)
            elif key2 == b'P':  # Down arrow
                cursor = (cursor + 1) % len(rails)

        elif key in (b'q', b'Q', b'\x1b'):  # Quit or Escape
            print("\n  Selection cancelled.")
            return None

        else:
            continue

        # Redraw: move cursor up and overwrite each line
        display_lines = render()
        sys.stdout.write(f"\033[{len(display_lines)}A")
        for line in display_lines:
            sys.stdout.write(f"\033[2K{line}\n")
        sys.stdout.flush()


def list_visa_resources():
    """List all available VISA resources with auto-identification"""
    try:
        from visa_auto_detect import detect_all_instruments
        instruments = detect_all_instruments()
        return bool(instruments)
    except ImportError:
        print("ERROR: visa_auto_detect module not found")
        return False
    except Exception as e:
        print(f"ERROR: Failed to detect instruments: {e}")
        return False


def print_banner():
    """Print test banner"""
    print()
    print("=" * 70)
    print(" LOAD TRANSIENT RESPONSE TEST")
    print(" Validates regulator control loop bandwidth, damping, and oscillation")
    print("=" * 70)
    print()
    print(" Test Procedure for Each Rail:")
    print("   1. Confirm probe connection to rail")
    print("   2. Automatic positive load step (100mA -> half rated)")
    print("   3. Capture and analyze waveform")
    print("   4. Automatic negative load step (half rated -> 100mA)")
    print("   5. Capture and analyze waveform")
    print("   6. Auto-advance to next rail")
    print()
    print(" Rails to be tested:")
    print("   3V6, 3V3, 2V5, 1V8, 1V35, 1V_PS, 1V_PL, 1V1_E0, 2V5_E0, 1V8_E0")
    print()
    print("=" * 70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Load Transient Response Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Auto-detect and run all rails
  %(prog)s --list                   List available VISA instruments
  %(prog)s --rails 3V6,3V3,1V8      Test only specific rails
  %(prog)s --scope USB0::... --load USB0::...   Specify instrument addresses
        """
    )

    parser.add_argument('--list', action='store_true',
                        help='List available VISA instruments and exit')
    parser.add_argument('--scope', type=str, default=None,
                        help='Oscilloscope VISA address')
    parser.add_argument('--load', type=str, default=None,
                        help='Electronic load VISA address')
    parser.add_argument('--rails', type=str, default=None,
                        help='Comma-separated list of rails to test (e.g., "3V6,3V3,1V8")')
    parser.add_argument('--output', type=str, default='load_transient_results',
                        help='Output directory for results')

    args = parser.parse_args()

    # Print banner
    print_banner()

    # List resources and exit if requested
    if args.list:
        list_visa_resources()
        return 0

    # Get instrument addresses (None will trigger auto-detection in the test class)
    scope_addr = args.scope
    load_addr = args.load

    # Show what we're doing
    if scope_addr and load_addr:
        print(f"\nUsing specified instruments:")
        print(f"  Oscilloscope:    {scope_addr}")
        print(f"  Electronic Load: {load_addr}")
    else:
        print("\nAuto-detection will be performed during initialization...")

    # Import the test module
    try:
        from load_transient_response_test import LoadTransientTest
    except ImportError as e:
        print(f"\nERROR: Failed to import test module: {e}")
        print("Make sure load_transient_response_test.py is in the same directory")
        return 1

    # Determine which rails to test
    rails_to_test = None
    if args.rails:
        # Rails specified via command line - use directly
        rails_to_test = [r.strip() for r in args.rails.split(',')]
        print(f"\nRails to test: {', '.join(rails_to_test)}")
    else:
        # Interactive rail selection
        rails_to_test = interactive_rail_selector(LoadTransientTest.RAIL_CONFIGS)
        if rails_to_test is None:
            print("Test cancelled.")
            return 0
        if not rails_to_test:
            print("No rails selected. Exiting.")
            return 0
        print(f"\nRails to test: {', '.join(rails_to_test)}")

    # Create test instance (auto-detection happens here if addresses are None)
    try:
        test = LoadTransientTest(
            oscilloscope_address=scope_addr,
            electronic_load_address=load_addr,
            output_dir=args.output
        )

        # Verify instruments were found
        if not test.scope_address or not test.load_address:
            print("\n" + "=" * 70)
            print("ERROR: Required instruments not found!")
            print("=" * 70)
            if not test.scope_address:
                print("\n  Missing: Oscilloscope")
                print("    Use --scope <address> to specify manually")
            if not test.load_address:
                print("\n  Missing: Electronic Load (Keithley 2380)")
                print("    Use --load <address> to specify manually")
            print("\n  Use --list to see all available instruments")
            print("=" * 70)
            return 1

        print(f"\n  Instruments ready:")
        print(f"  Oscilloscope:    {test.scope_address}")
        print(f"  Electronic Load: {test.load_address}")

    except Exception as e:
        print(f"\nERROR: Failed to initialize test: {e}")
        return 1

    # Confirm start
    print("\n" + "-" * 70)
    print("SAFETY REMINDER:")
    print("  - Ensure DUT is powered and stable")
    print("  - Verify probe connections and ground references")
    print("  - Electronic load will draw up to 1.5A during testing")
    print("-" * 70)

    response = input("\nPress ENTER to start the test sequence (or 'q' to quit): ").strip().lower()
    if response in ['q', 'quit', 'exit']:
        print("Test cancelled.")
        return 0

    # Run the test
    success = test.run_test_sequence(rails=rails_to_test)

    # ── Save or discard prompt ────────────────────────────────────────────────
    print()
    while True:
        save_resp = input("  Save results? [Y/n]: ").strip().lower()
        if save_resp in ('', 'y', 'yes'):
            print(f"  Results saved: {test.output_dir}")
            print()
            break
        elif save_resp in ('n', 'no'):
            import shutil
            import subprocess
            for handler in list(test._logger.handlers):
                try:
                    handler.close()
                except Exception:
                    pass
                test._logger.removeHandler(handler)
            try:
                subprocess.run(
                    ['cmd', '/c', 'rmdir', '/s', '/q', str(test.output_dir)],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass
            if test.output_dir.exists():
                shutil.rmtree(test.output_dir, ignore_errors=True)
            if test.output_dir.exists():
                print(f"  WARNING: Could not fully delete run folder (OneDrive may still be syncing).")
                print(f"  Delete manually: {test.output_dir}")
            else:
                print("  Results discarded — run folder deleted.")
            print()
            break

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
