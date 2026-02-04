#!/usr/bin/env python3
"""
PWRSTD06: Transient Response Test Runner

Simple runner script for PWRSTD06 transient response testing with auto-detection
of VISA instruments.

Usage:
    python run_pwrstd06_test.py                    # Auto-detect instruments
    python run_pwrstd06_test.py --scope <addr>     # Specify scope address
    python run_pwrstd06_test.py --load <addr>      # Specify load address
    python run_pwrstd06_test.py --list             # List available instruments
    python run_pwrstd06_test.py --rails 3V6,3V3    # Test specific rails only
"""

import sys
import argparse
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))


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
    print(" PWRSTD06: TRANSIENT RESPONSE TEST")
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
        description="PWRSTD06 Transient Response Test Runner",
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
    parser.add_argument('--output', type=str, default='pwrstd06_results',
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

    # Parse rails to test
    rails_to_test = None
    if args.rails:
        rails_to_test = [r.strip() for r in args.rails.split(',')]
        print(f"\nRails to test: {', '.join(rails_to_test)}")

    # Import the test module
    try:
        from pwrstd06_transient_response_test import PWRSTD06TransientTest
    except ImportError as e:
        print(f"\nERROR: Failed to import test module: {e}")
        print("Make sure pwrstd06_transient_response_test.py is in the same directory")
        return 1

    # Create test instance (auto-detection happens here if addresses are None)
    try:
        test = PWRSTD06TransientTest(
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

        print(f"\n✓ Instruments ready:")
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

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
