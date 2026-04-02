    
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

import sys
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))


def _enable_ansi():
    """Enable ANSI escape codes on Windows 10+."""
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7
        )
    except Exception:
        pass


def _setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )


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
    import msvcrt

    _enable_ansi()

    options = [
        {
            'key':   'full',
            'label': 'Full Test',
            'desc':  'Fixed Vin tests  +  Sweep  (complete characterisation)',
        },
        {
            'key':   'fixed',
            'label': 'Fixed Vin Only',
            'desc':  'Apply configured voltages, read Vout, skip sweep',
        },
        {
            'key':   'sweep',
            'label': 'Sweep Only',
            'desc':  'Vin ramp 0 -> Vmax -> 0 with continuous DMM capture, skip fixed tests',
        },
    ]

    selected = 0   # index of currently selected option (radio button)
    cursor   = 0   # index of highlighted row

    def render():
        lines = []
        lines.append("")
        lines.append("  TEST MODE SELECTION")
        lines.append("  " + "=" * 62)
        lines.append("  UP/DOWN: Navigate | TAB: Select | ENTER: Run | Q: Quit")
        lines.append("")
        for i, opt in enumerate(options):
            marker = "(X)" if i == selected else "( )"
            arrow  = ">>" if i == cursor else "  "
            lines.append(f"  {arrow} {marker}  {opt['label']:<18}  {opt['desc']}")
        lines.append("")
        lines.append(f"  Mode: {options[selected]['label']}")
        return lines

    display_lines = render()
    for line in display_lines:
        print(line)
    sys.stdout.flush()

    while True:
        key = msvcrt.getch()

        if key == b'\r':                          # ENTER — confirm
            print()
            return options[selected]['key']

        elif key in (b'\t', b' '):                # TAB / SPACE — select current
            selected = cursor

        elif key in (b'\xe0', b'\x00'):           # Arrow key prefix
            key2 = msvcrt.getch()
            if key2 == b'H':                      # UP
                cursor = (cursor - 1) % len(options)
            elif key2 == b'P':                    # DOWN
                cursor = (cursor + 1) % len(options)

        elif key in (b'q', b'Q', b'\x1b'):        # Q / ESC — cancel
            print("\n  Cancelled.")
            return None

        else:
            continue

        # Redraw in-place
        display_lines = render()
        sys.stdout.write(f"\033[{len(display_lines)}A")
        for line in display_lines:
            sys.stdout.write(f"\033[2K{line}\n")
        sys.stdout.flush()


def print_setup_instructions(instr: dict, settings: dict, p: dict):
    """
    Print step-by-step physical setup instructions using the actual config values.
    Called after the config summary, before the mode selector.
    """
    ch          = settings.get("psu_channel", 1)
    i_lim       = p.get("psu_current_limit_a", "?")
    ovp         = p.get("psu_ovp_level_v", "?")
    sweep_max   = p.get("sweep_max_v", "?")
    psu_addr    = instr.get("psu", "?")
    dmm_addr    = instr.get("dmm", "?")

    print()
    print("=" * 70)
    print("  SETUP INSTRUCTIONS — Complete these steps before starting")
    print("=" * 70)
    print()
    print("  [ 1 ]  POWER OFF the DUT board before making any connections.")
    print()
    print(f"  [ 2 ]  PSU wiring  (Keithley PSU, CH{ch}):")
    print(f"           + terminal  (red lead)    ->  DUT VIN  (positive input)")
    print(f"           - terminal  (black lead)  ->  DUT GND  (input ground / return)")
    print(f"           The PSU will be limited to {i_lim} A with OVP set to {ovp} V.")
    print(f"           Voltage will ramp from 0 V up to {sweep_max} V during the sweep.")
    print()
    print("  [ 3 ]  DMM wiring  (Keithley DMM6500):")
    print("           You will be prompted to connect the DMM probes AFTER the")
    print("           instruments connect. For now, leave the DMM probes at GND")
    print("           or disconnected — do NOT connect them to VOUT yet.")
    print()
    print("  [ 4 ]  USB connections to this PC:")
    print(f"           PSU  ->  {psu_addr}")
    print(f"           DMM  ->  {dmm_addr}")
    print("           If either address looks wrong, edit input_range_ovp_config.json")
    print("           and restart the script.")
    print()
    print("  [ 5 ]  Power ON the PSU and DMM. Leave the DUT powered off —")
    print("           the PSU will apply voltage when the test begins.")
    print()
    print("  [ 6 ]  Verify on the PSU front panel:")
    print(f"           - CH{ch} output is OFF (output button not lit)")
    print(f"           - No over-voltage or error indicators are showing")
    print()
    print("  [ 7 ]  Do NOT touch the board, probes, or leads once the test starts.")
    print("           Voltages up to", sweep_max, "V will be applied to the DUT.")
    print()
    print("=" * 70)
    print()


def prompt_output_directory(cfg_output_dir: str = None):
    """
    Prompt user to select or confirm output directory for test results.
    
    Returns:
        str: The output directory path (either default or custom)
    """
    default_path = cfg_output_dir or "input_range_ovp_results"
    
    print()
    print("=" * 70)
    print("  OUTPUT DIRECTORY SELECTION")
    print("=" * 70)
    print()
    print(f"  Default path (from config): {default_path}")
    print()
    print("  Options:")
    print("    [1] Use default path")
    print("    [2] Enter custom path")
    print()
    
    while True:
        choice = input("  Select option (1 or 2): ").strip()
        
        if choice == "1":
            selected_path = default_path
            print(f"  Using: {selected_path}")
            print()
            return selected_path
        elif choice == "2":
            custom_path = input("  Enter output directory path: ").strip()
            if not custom_path:
                print("  ERROR: Path cannot be empty. Try again.")
                continue
            selected_path = custom_path
            print(f"  Using: {selected_path}")
            print()
            return selected_path
        else:
            print("  Invalid choice. Please enter 1 or 2.")


def print_banner():
    print()
    print("=" * 70)
    print("  INPUT RANGE AND OVP TEST")
    print("  Characterises DUT input behaviour, operating range, and protections")
    print("=" * 70)
    print()
    print("  Instruments : Keithley Power Supply  +  Keithley DMM6500")
    print()
    print("  Test phases:")
    print("    1. Prompt operator to connect DMM probes on DUT output")
    print("    2. Fixed Vin tests — apply configured voltages, read Vout, Pass/Fail")
    print("    3. Sweep test     — ramp 0 -> Vmax -> 0, capture DMM, generate plots")
    print("    4. Save reports (CSV + JSON + TXT summary) in a timestamped run folder")
    print()
    print("  Edit  input_range_ovp_config.json  to change addresses, voltages,")
    print("  step size, dwell time, and DMM read interval.")
    print()
    print("=" * 70)


def main():
    _enable_ansi()

    parser = argparse.ArgumentParser(
        description="Input Range and OVP Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
    parser.add_argument(
        '--mode', choices=['full', 'fixed', 'sweep'], default=None,
        help='Test mode: full / fixed / sweep  (default: interactive selector)'
    )
    parser.add_argument(
        '--output', type=str, default=None,
        help='Base directory for results (default: path from input_range_ovp_config.json)'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable verbose instrument-level logging'
    )

    args = parser.parse_args()
    _setup_logging(args.verbose)

    print_banner()

    try:
        from input_range_ovp_test import InputRangeOVPTest, SweepResult, _CFG
    except ImportError as e:
        print(f"\n  ERROR: Could not import test module: {e}")
        print("  Make sure input_range_ovp_test.py is in the same directory.")
        return 1

    # Display config summary
    instr    = _CFG.get("instrument_addresses", {})
    settings = _CFG.get("instrument_settings", {})
    p        = _CFG.get("test_parameters", {})

    print("  Configuration summary:")
    print(f"    PSU address    : {instr.get('psu')}")
    print(f"    DMM address    : {instr.get('dmm')}")
    print(f"    PSU channel    : CH{settings.get('psu_channel', 1)}")
    print(f"    Current limit  : {p.get('psu_current_limit_a', '?')} A")
    print()
    print("  Fixed Vin test points:")
    for pt in InputRangeOVPTest.FIXED_VIN_TESTS:
        print(f"    Vin={pt.vin_v:.1f} V  ->  expected Vout={pt.expected_vout_v:.1f} V"
              f"  +/-{pt.vout_tolerance_v:.2f} V")
    print()
    print("  Sweep:")
    print(f"    {p.get('sweep_start_v', 0):.0f} V  ->  {p.get('sweep_max_v', 30):.0f} V  ->  {p.get('sweep_start_v', 0):.0f} V")
    print(f"    Step: {p.get('sweep_step_v', '?')} V  |  "
          f"Dwell: {p.get('step_dwell_time_s', '?')} s  |  "
          f"DMM interval: {p.get('dmm_read_interval_s', '?')} s")
    print()

    # ── Setup instructions ────────────────────────────────────────────────────
    print_setup_instructions(instr, settings, p)

    # ── Mode selection ────────────────────────────────────────────────────────
    if args.mode:
        mode = args.mode
        print(f"  Mode: {mode}  (from --mode flag)")
        print()
        response = input("  All connections made? Press ENTER to start (or 'q' to quit): ").strip().lower()
        if response in ('q', 'quit', 'exit'):
            print("  Cancelled.")
            return 0
    else:
        mode = interactive_mode_selector()
        if mode is None:
            return 0
        print(f"  Running: {mode}")

    # ── Output directory selection ────────────────────────────────────────────
    output_dir = args.output
    if output_dir is None:
        # Prompt user to select output directory (if not provided via --output flag)
        cfg_output_path = _CFG.get("output_dir", {})
        cfg_output_dir = (
            cfg_output_path.get("path", "input_range_ovp_results")
            if isinstance(cfg_output_path, dict)
            else str(cfg_output_path)
        )
        output_dir = prompt_output_directory(cfg_output_dir)

    # ── Create test instance ──────────────────────────────────────────────────
    test = InputRangeOVPTest(output_dir=output_dir)

    # ── Run selected mode ─────────────────────────────────────────────────────
    if mode == 'fixed':
        print("\n  Running Fixed Vin tests only.")
        if not test._connect_instruments():
            return 1
        try:
            test._prompt_probe_setup()
            fixed_results = test.run_fixed_vin_tests()
            empty_sweep = SweepResult(
                vin_range="N/A", vout_v=0.0,
                expected_vout_v=p.get("sweep_expected_vout_v", 0.0),
                status="NOT_RUN"
            )
            verdict = test._generate_reports(fixed_results, empty_sweep)
            return 0 if verdict == "PASS" else 1
        finally:
            test._disconnect_instruments()

    elif mode == 'sweep':
        print("\n  Running Sweep test only.")
        if not test._connect_instruments():
            return 1
        try:
            test._prompt_probe_setup()
            sweep_result = test.run_sweep_test()
            print("\n  Generating plots...")
            test._plot_sweep(sweep_result)
            print("\n  Writing reports...")
            test._generate_reports([], sweep_result)
            return 0 if sweep_result.status == "PASS" else 1
        finally:
            test._disconnect_instruments()

    else:  # full
        success = test.run()
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
