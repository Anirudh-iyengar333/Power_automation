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


# ─────────────────────────────────────────────────────────────────────────────
# Interactive rail selector  (multi-select with TAB / SPACE toggle)
# ─────────────────────────────────────────────────────────────────────────────

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
    import msvcrt

    _enable_ansi()

    selected = [True] * len(all_rails)   # start with everything checked
    cursor   = 0

    def render():
        lines = []
        lines.append("")
        lines.append("  RAIL SELECTION")
        lines.append("  " + "=" * 70)
        lines.append("  UP/DOWN: Navigate   SPACE/TAB: Toggle   A: All   N: None   ENTER: Run   Q: Quit")
        lines.append("")
        for i, rail in enumerate(all_rails):
            check  = "[X]" if selected[i] else "[ ]"
            arrow  = ">>" if i == cursor else "  "
            ripple = (f"ripple < {rail.ripple_max_mvpp:.0f} mVpp"
                      if rail.ripple_max_mvpp is not None else "no ripple spec")
            lines.append(
                f"  {arrow} {check}  {rail.name:<10}  {rail.test_point:<12}  "
                f"{rail.min_v:.2f} – {rail.max_v:.2f} V    {ripple}"
            )
        lines.append("")
        n = sum(selected)
        lines.append(f"  Selected: {n} rail{'s' if n != 1 else ''}")
        return lines

    display_lines = render()
    for line in display_lines:
        print(line)
    sys.stdout.flush()

    while True:
        key = msvcrt.getch()

        if key == b'\r':                            # ENTER — confirm
            print()
            picks = [r for r, s in zip(all_rails, selected) if s]
            return picks if picks else None

        elif key in (b' ', b'\t'):                  # SPACE / TAB — toggle current row
            selected[cursor] = not selected[cursor]

        elif key in (b'a', b'A'):                   # A — select all
            selected = [True] * len(all_rails)

        elif key in (b'n', b'N'):                   # N — deselect all
            selected = [False] * len(all_rails)

        elif key in (b'\xe0', b'\x00'):             # Arrow key prefix
            key2 = msvcrt.getch()
            if key2 == b'H':                        # UP
                cursor = (cursor - 1) % len(all_rails)
            elif key2 == b'P':                      # DOWN
                cursor = (cursor + 1) % len(all_rails)

        elif key in (b'q', b'Q', b'\x1b'):          # Q / ESC — cancel
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


# ─────────────────────────────────────────────────────────────────────────────
# Output directory prompt
# ─────────────────────────────────────────────────────────────────────────────

def prompt_output_directory(cfg_output_dir: str = None) -> str:
    default_path = cfg_output_dir or "steady_state_ripple_results"

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
            print(f"  Using: {default_path}")
            print()
            return default_path
        elif choice == "2":
            custom_path = input("  Enter output directory path: ").strip()
            if not custom_path:
                print("  ERROR: Path cannot be empty. Try again.")
                continue
            print(f"  Using: {custom_path}")
            print()
            return custom_path
        else:
            print("  Invalid choice. Please enter 1 or 2.")


# ─────────────────────────────────────────────────────────────────────────────
# Setup instructions
# ─────────────────────────────────────────────────────────────────────────────

def print_setup_instructions(instr: dict, psu_cfg: dict, scp_cfg: dict, selected_rails: list):
    psu_addr = instr.get("psu", "?")
    scp_addr = instr.get("scope", "?")
    ch       = psu_cfg.get("channel", 1)
    vin      = psu_cfg.get("vin_v", 5.0)
    i_lim    = psu_cfg.get("current_limit_a", "?")
    ovp      = psu_cfg.get("ovp_level_v", "?")
    tb_dc_ms = scp_cfg.get("dc_timebase_s_per_div", 0.01) * 1000
    tb_rp_ms = scp_cfg.get("ripple_timebase_s_per_div", 0.1) * 1000
    rp_mv    = scp_cfg.get("ripple_v_scale_v_per_div", 0.05) * 1000

    has_ripple = any(r.ripple_max_mvpp is not None for r in selected_rails)

    print()
    print("=" * 70)
    print("  SETUP INSTRUCTIONS — Complete these steps before starting")
    print("=" * 70)

    print()
    print("  STEP 1 — DUT State")
    print("  " + "-" * 60)
    print("  The DUT must be POWERED ON and fully stable at nominal conditions.")
    print("  All power rails should be up. This test does NOT power-cycle the DUT.")

    print()
    print("  STEP 2 — PSU Verification  (Keithley Power Supply)")
    print("  " + "-" * 60)
    print(f"  Confirm PSU CH{ch} is outputting  {vin} V / {i_lim} A  (OVP: {ovp} V)")
    print(f"  + lead (red)   →  DUT VIN positive")
    print(f"  − lead (black) →  DUT GND / return")
    print(f"  VISA address   :  {psu_addr}  (for reference only — script does not control PSU)")

    print()
    print("  STEP 3 — Oscilloscope Probe  (CH1 only)")
    print("  " + "-" * 60)
    print("  Use CH1 for ALL measurements — the script tests one rail at a time.")
    print("  Before starting, set the probe slide switch to:  1×  (1:1 attenuation)")
    print("  Coupling and BW are configured automatically by the script.")
    print()
    print(f"  DC Voltage phase:   DC coupling  ·  20 MHz BW  ·  {tb_dc_ms:.0f} ms/div")
    print(f"  Ripple phase:       AC coupling  ·  20 MHz BW  ·  {rp_mv:.0f} mV/div  ·  {tb_rp_ms:.0f} ms/div")
    print()
    print("  The script will prompt you to move the probe for each rail.")

    if has_ripple:
        print()
        print("  STEP 4 — GND Spring  (required for ripple measurements)")
        print("  " + "-" * 60)
        print("  Have a COAXIAL GND SPRING tip ready.  It fits over the probe barrel")
        print("  and replaces the long alligator-clip ground lead.")
        print("  Long ground leads add inductance — they inflate ripple readings.")
        print("  The script will ask you to fit the spring before the ripple phase")
        print("  of each rail and position the tip across the last output capacitor.")
    else:
        print()
        print("  STEP 4 — GND Spring:  Not required for the selected rails.")

    print()
    print("  STEP 5 — PC Connections via VISA")
    print("  " + "-" * 60)
    print(f"  Scope VISA address : {scp_addr}")
    print()
    print("  If the address looks wrong, edit steady_state_ripple_config.json")
    print("  and restart the script.")
    print()
    print("  To list detected instruments:")
    print("    python -c \"import pyvisa; print(pyvisa.ResourceManager().list_resources())\"")

    print()
    print("  STEP 6 — Power ON Instruments")
    print("  " + "-" * 60)
    print("  Power on the Keysight Oscilloscope.")
    print("  Do NOT press RUN on the scope manually — the script arms it for each")
    print("  measurement phase automatically.")

    print()
    print("  STEP 7 — Safety Reminders")
    print("  " + "-" * 60)
    print(f"  DUT input: {vin} V / {i_lim} A")
    print("  Remove the probe tip from one test point before moving to the next.")
    print("  Do NOT short probe tip to adjacent pads.")
    print("  Keep probe lead clear of rotating components.")
    print()
    print("=" * 70)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────

def print_banner():
    print()
    print("=" * 70)
    print("  STEADY-STATE RAIL VERIFICATION AND RIPPLE TEST")
    print("  Verify DC levels and AC ripple on selected power rails")
    print("=" * 70)
    print()
    print("  Instruments : Keysight Oscilloscope  (CH1, one rail at a time)")
    print()
    print("  Per-rail procedure:")
    print("    Phase 1 — DC Voltage  : DC coupling · 20 MHz BW · measure DC RMS FS")
    print("    Phase 2 — Ripple      : AC coupling · 50 mV/div · 100 ms/div · measure Vpp")
    print("                            (GND spring placed across last output capacitor)")
    print()
    print("  Edit  steady_state_ripple_config.json  to change instrument addresses,")
    print("  rail voltage ranges, ripple limits, and output directory.")
    print()
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    _enable_ansi()

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
    parser.add_argument(
        '--rails', nargs='+', default=None,
        help='Rail names to test, or "all". Default: interactive selector.'
    )
    parser.add_argument(
        '--output', type=str, default=None,
        help='Base directory for results (default: path from config)'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable verbose instrument-level logging'
    )

    args = parser.parse_args()
    _setup_logging(args.verbose)

    print_banner()

    try:
        from steady_state_ripple_test import SteadyStateRippleTest, _CFG
    except ImportError as e:
        print(f"\n  ERROR: Could not import test module: {e}")
        print("  Make sure steady_state_ripple_test.py is in the same directory.")
        return 1

    all_rails = SteadyStateRippleTest.ALL_RAILS

    # ── Config summary ────────────────────────────────────────────────────────
    instr   = _CFG.get("instrument_addresses", {})
    psu_cfg = _CFG.get("psu_settings", {})
    scp_cfg = _CFG.get("scope_settings", {})

    print("  Configuration summary:")
    print(f"    Scope address    : {instr.get('scope')}")
    print(f"    PSU ref          : CH{psu_cfg.get('channel',1)}  {psu_cfg.get('vin_v',5.0)} V / "
          f"{psu_cfg.get('current_limit_a',2.0)} A  (pre-configured — not controlled by test)")
    print(f"    DC timebase      : {scp_cfg.get('dc_timebase_s_per_div',0.01)*1000:.0f} ms/div")
    print(f"    Ripple timebase  : {scp_cfg.get('ripple_timebase_s_per_div',0.1)*1000:.0f} ms/div  "
          f"at {scp_cfg.get('ripple_v_scale_v_per_div',0.05)*1000:.0f} mV/div  AC coupling")
    print()
    print(f"  Available rails ({len(all_rails)}):")
    for r in all_rails:
        ripple = f"< {r.ripple_max_mvpp:.0f} mVpp" if r.ripple_max_mvpp is not None else "no spec"
        print(f"    {r.name:<10}  {r.test_point:<12}  "
              f"{r.min_v:.2f} – {r.max_v:.2f} V    ripple: {ripple}")
    print()

    # ── Rail selection ────────────────────────────────────────────────────────
    if args.rails:
        if args.rails == ['all']:
            selected_rails = all_rails
            print(f"  Rails: all ({len(selected_rails)})  (from --rails flag)")
        else:
            name_map = {r.name: r for r in all_rails}
            selected_rails = []
            for name in args.rails:
                if name in name_map:
                    selected_rails.append(name_map[name])
                else:
                    print(f"  WARNING: Unknown rail '{name}' — skipped. "
                          f"Available: {[r.name for r in all_rails]}")
            if not selected_rails:
                print("  ERROR: No valid rails selected.")
                return 1
            print(f"  Rails: {[r.name for r in selected_rails]}  (from --rails flag)")
        print()
    else:
        selected_rails = interactive_rail_selector(all_rails)
        if selected_rails is None:
            return 0
        if not selected_rails:
            print("  No rails selected — nothing to test.")
            return 0
        print(f"  Running {len(selected_rails)} rail(s): "
              + "  ".join(r.name for r in selected_rails))

    # ── Setup instructions ────────────────────────────────────────────────────
    print_setup_instructions(instr, psu_cfg, scp_cfg, selected_rails)

    # ── Output directory selection ────────────────────────────────────────────
    output_dir = args.output
    if output_dir is None:
        cfg_out = _CFG.get("output_dir", {})
        cfg_dir = (
            cfg_out.get("path", "steady_state_ripple_results")
            if isinstance(cfg_out, dict)
            else str(cfg_out)
        )
        output_dir = prompt_output_directory(cfg_dir)

    # ── Start confirmation ────────────────────────────────────────────────────
    response = input("  All setup complete? Press ENTER to start (or 'q' to quit): ").strip().lower()
    if response in ('q', 'quit', 'exit'):
        print("  Cancelled.")
        return 0

    # ── Run ───────────────────────────────────────────────────────────────────
    test    = SteadyStateRippleTest(rails=selected_rails, output_dir=output_dir)
    success = test.run()

    # ── Save or discard prompt ────────────────────────────────────────────────
    print()
    while True:
        save_resp = input("  Save results? [Y/n]: ").strip().lower()
        if save_resp in ('', 'y', 'yes'):
            print(f"  Results saved: {test._run_dir}")
            print()
            break
        elif save_resp in ('n', 'no'):
            import shutil
            import subprocess
            # Close the log file handler so Windows releases the file lock
            for handler in list(test._logger.handlers):
                try:
                    handler.close()
                except Exception:
                    pass
                test._logger.removeHandler(handler)
            # Use Windows rmdir /s /q — handles OneDrive-locked dirs that
            # shutil.rmtree silently fails on
            try:
                subprocess.run(
                    ['cmd', '/c', 'rmdir', '/s', '/q', str(test._run_dir)],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass
            # Fallback: shutil in case subprocess didn't finish cleanly
            if test._run_dir.exists():
                shutil.rmtree(test._run_dir, ignore_errors=True)
            if test._run_dir.exists():
                print(f"  WARNING: Could not fully delete run folder (OneDrive may still be syncing).")
                print(f"  Delete manually: {test._run_dir}")
            else:
                print("  Results discarded — run folder deleted.")
            print()
            break

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
