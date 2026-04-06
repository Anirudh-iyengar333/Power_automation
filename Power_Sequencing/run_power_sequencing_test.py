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
# Interactive mode selector
# ─────────────────────────────────────────────────────────────────────────────

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
    import msvcrt

    _enable_ansi()

    options = [
        {
            'key':   'full',
            'label': 'Full Test',
            'desc':  'Config 1 + Config 2  (complete power sequencing — 2 power cycles)',
        },
        {
            'key':   'config1',
            'label': 'Config 1 Only',
            'desc':  '1V0PL, 1V8, 1V0PS, 1V35  →  lower rails, 1 power cycle',
        },
        {
            'key':   'config2',
            'label': 'Config 2 Only',
            'desc':  '2V5, 1V8, 3V3, 1V35  →  higher rails, 1 power cycle',
        },
        {
            'key':   'capture',
            'label': 'Capture Only',
            'desc':  'Power-cycle + full screenshots, skip cursor analysis',
        },
        {
            'key':   'reanalyze',
            'label': 'Re-analyse',
            'desc':  'Scope already triggered — skip power cycle, re-run analysis only',
        },
    ]

    selected = 0   # index of currently selected option (radio button)
    cursor   = 0   # index of highlighted row

    def render():
        lines = []
        lines.append("")
        lines.append("  TEST MODE SELECTION")
        lines.append("  " + "=" * 66)
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


# ─────────────────────────────────────────────────────────────────────────────
# Output directory prompt
# ─────────────────────────────────────────────────────────────────────────────

def prompt_output_directory(cfg_output_dir: str = None) -> str:
    default_path = cfg_output_dir or "power_sequencing_results"

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
# Detailed setup instructions (mode-aware)
# ─────────────────────────────────────────────────────────────────────────────

def print_setup_instructions(instr: dict, psu_cfg: dict, scp_cfg: dict, mode: str):
    psu_addr   = instr.get("psu", "?")
    scp_addr   = instr.get("scope", "?")
    ch         = psu_cfg.get("channel", 1)
    vin        = psu_cfg.get("vin_v", 5.0)
    i_lim      = psu_cfg.get("current_limit_a", "?")
    ovp        = psu_cfg.get("ovp_level_v", "?")
    tb_ms      = scp_cfg.get("timebase_s_per_div", 1e-3) * 1e3
    pre_trig   = scp_cfg.get("pretrigger_pct", 20)

    need_psu      = mode != "reanalyze"
    need_config1  = mode in ("full", "config1", "capture")
    need_config2  = mode in ("full", "config2", "capture")
    need_dmm      = mode in ("full", "config1")

    print()
    print("=" * 70)
    print("  SETUP INSTRUCTIONS — Complete these steps before starting")
    print("=" * 70)

    print()
    print("  STEP 1 — DUT State")
    print("  " + "-" * 60)
    if mode == "reanalyze":
        print("  The DUT should already be powered from a previous capture.")
        print("  The scope must be in STOP state with a valid waveform acquired.")
        print("  Do NOT power-cycle the DUT — the script will skip the trigger step.")
    else:
        print("  Ensure the DUT board is POWERED OFF before making connections.")
        print("  The script will apply power automatically at the correct moment.")

    print()
    print("  STEP 2 — PSU Wiring  (Keithley Power Supply)")
    print("  " + "-" * 60)
    if need_psu:
        print(f"  Channel : CH{ch}")
        print(f"  + terminal  (red lead)    →  DUT VIN positive input")
        print(f"  − terminal  (black lead)  →  DUT GND / return")
        print()
        print(f"  Settings applied by script:")
        print(f"    Output voltage   : {vin} V")
        print(f"    Current limit    : {i_lim} A")
        print(f"    OVP level        : {ovp} V")
        print()
        print(f"  Verify on PSU front panel:")
        print(f"    CH{ch} output is OFF (output button NOT lit)")
        print(f"    No over-voltage or fault indicators showing")
        print(f"  VISA address : {psu_addr}")
    else:
        print("  PSU not used in Re-analyse mode — skip this step.")

    print()
    print("  STEP 3 — Oscilloscope Probe Connections")
    print("  " + "-" * 60)

    if need_config1:
        print()
        print("  CONFIG 1  (connect these probes now):")
        print("  ┌─────────────────────────────────────────────────────┐")
        print("  │  Scope CH  │  Rail   │  Test Point  │  Note         │")
        print("  ├─────────────────────────────────────────────────────┤")
        print("  │  CH1       │  1V0PL  │  TP8         │  ← TRIGGER   │")
        print("  │  CH2       │  1V8    │  TP6         │               │")
        print("  │  CH3       │  1V0PS  │  TP5         │               │")
        print("  │  CH4       │  1V35   │  TP7         │               │")
        print("  └─────────────────────────────────────────────────────┘")
        print()
        print("  Probe settings (all channels) — set BEFORE connecting:")
        print("    Attenuation : 10×  ← slide switch on probe body to ×10")
        print("    Coupling    : DC   (configured automatically by script)")
        print("    BW limit    : 20 MHz  (configured automatically by script)")
        print("    Ground clip : nearest GND via / plane on DUT board")
        print()
        print(f"  Trigger (set automatically by script):")
        print(f"    Source : CH1  (1V0PL, TP8)")
        print(f"    Edge   : Rising")
        print(f"    Level  : 0.20 V  (20% of 1.0 V nominal)")
        print(f"    Mode   : Single-shot  |  {pre_trig}% pre-trigger")
        print(f"    Time base : {tb_ms:.0f} ms/div  "
              f"({int(pre_trig * tb_ms / 10)} ms pre-trigger  "
              f"{int((100 - pre_trig) * tb_ms / 10)} ms post-trigger)")

    if need_config2 and mode != "full":
        print()
        print("  CONFIG 2  (connect these probes now):")
        print("  ┌─────────────────────────────────────────────────────┐")
        print("  │  Scope CH  │  Rail   │  Test Point  │  Note         │")
        print("  ├─────────────────────────────────────────────────────┤")
        print("  │  CH1       │  2V5    │  TP9         │  ← TRIGGER   │")
        print("  │  CH2       │  1V8    │  TP6         │               │")
        print("  │  CH3       │  3V3    │  TP10        │               │")
        print("  │  CH4       │  1V35   │  TP7         │               │")
        print("  └─────────────────────────────────────────────────────┘")
        print()
        print("  Probe settings (all channels) — set BEFORE connecting:")
        print("    Attenuation : 10×  ← slide switch on probe body to ×10")
        print("    Coupling    : DC   (configured automatically by script)")
        print("    BW limit    : 20 MHz  (configured automatically by script)")
        print("    Ground clip : nearest GND via / plane on DUT board")
        print()
        print(f"  Trigger (set automatically by script):")
        print(f"    Source : CH1  (2V5, TP9)")
        print(f"    Edge   : Rising")
        print(f"    Level  : 0.50 V  (20% of 2.5 V nominal)")
        print(f"    Mode   : Single-shot  |  {pre_trig}% pre-trigger")
        print(f"    Time base : {tb_ms:.0f} ms/div  "
              f"({int(pre_trig * tb_ms / 10)} ms pre-trigger  "
              f"{int((100 - pre_trig) * tb_ms / 10)} ms post-trigger)")

    if mode == "full":
        print()
        print("  CONFIG 1 first — after Config 1 capture is complete, the script")
        print("  will prompt you to move the probes to CONFIG 2 before the second")
        print("  power cycle. Config 2 probe positions:")
        print("    CH1 → 2V5 (TP9)    CH2 → 1V8 (TP6)")
        print("    CH3 → 3V3 (TP10)   CH4 → 1V35 (TP7)")

    if mode == "reanalyze":
        print()
        print("  Connect probes for whichever config is currently under test.")
        print("  The script will ask which config is connected before analysing.")

    print()
    print("  STEP 4 — DMM Measurement  (3V6 confirmation)")
    print("  " + "-" * 60)
    if need_dmm:
        print("  Connect DMM probes to the 3V6 output rail on the DUT.")
        print("  The script will ask you to read and enter this value manually")
        print("  after Config 1 is captured. Expected: 3.50 V – 3.70 V.")
        print("  The DMM does NOT need to be connected to the PC.")
    else:
        print("  DMM check not included in this mode — skip this step.")

    print()
    print("  STEP 5 — PC Connections via VISA")
    print("  " + "-" * 60)
    print(f"  PSU VISA address   : {psu_addr}")
    print(f"  Scope VISA address : {scp_addr}")
    print()
    print("  If either address looks wrong, edit power_sequencing_config.json")
    print("  and restart the script.")
    print()
    print("  To list detected instruments:")
    print("    python -c \"import pyvisa; print(pyvisa.ResourceManager().list_resources())\"")

    print()
    print("  STEP 6 — Power ON Instruments")
    print("  " + "-" * 60)
    print("  Power on the Keithley PSU and the Keysight Oscilloscope.")
    if need_psu:
        print("  Leave the DUT powered off — the PSU output will be controlled")
        print("  by the script. The script will toggle it at the correct moment.")
    print("  Do NOT press RUN or SINGLE on the scope manually —")
    print("  the script configures and arms the scope automatically.")

    print()
    print("  STEP 7 — Safety Reminders")
    print("  " + "-" * 60)
    print(f"  Voltages up to {vin} V will be applied to the DUT input.")
    print("  Do NOT touch the board, leads, or probe tips once the test starts.")
    print("  Verify probe ground clips are securely attached before starting.")
    print("  Keep leads clear of fans or moving parts.")

    print()
    print("=" * 70)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Banner
# ─────────────────────────────────────────────────────────────────────────────

def print_banner():
    print()
    print("=" * 70)
    print("  POWER SEQUENCING TEST")
    print("  Verifies all power rails ramp in correct order within timing windows")
    print("=" * 70)
    print()
    print("  Instruments : Keithley Power Supply  +  Keysight Oscilloscope")
    print()
    print("  Modes available:")
    print("    Full Test    — Config 1 + Config 2  (2 power cycles, all 6 rails)")
    print("    Config 1     — 1V0PL, 1V8, 1V0PS, 1V35  (1 power cycle)")
    print("    Config 2     — 2V5, 1V8, 3V3, 1V35  (1 power cycle)")
    print("    Capture Only — Power-cycle + screenshots only, no cursor analysis")
    print("    Re-analyse   — Skip power cycle, analyse current scope waveform")
    print()
    print("  Edit  power_sequencing_config.json  to change instrument addresses,")
    print("  timing limits, vertical scales, and output directory.")
    print()
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    _enable_ansi()

    parser = argparse.ArgumentParser(
        description="Power Sequencing Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
    parser.add_argument(
        '--mode',
        choices=['full', 'config1', 'config2', 'capture', 'reanalyze'],
        default=None,
        help='Test mode (default: interactive selector)'
    )
    parser.add_argument(
        '--output', type=str, default=None,
        help='Base directory for results (default: path from power_sequencing_config.json)'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Enable verbose instrument-level logging'
    )

    args = parser.parse_args()
    _setup_logging(args.verbose)

    print_banner()

    try:
        from power_sequencing_test import PowerSequencingTest, _CFG
    except ImportError as e:
        print(f"\n  ERROR: Could not import test module: {e}")
        print("  Make sure power_sequencing_test.py is in the same directory.")
        return 1

    # ── Config summary ────────────────────────────────────────────────────────
    instr   = _CFG.get("instrument_addresses", {})
    psu_cfg = _CFG.get("psu_settings", {})
    scp_cfg = _CFG.get("scope_settings", {})
    limits  = _CFG.get("rail_timing_limits", {})

    print("  Configuration summary:")
    print(f"    PSU address   : {instr.get('psu')}")
    print(f"    Scope address : {instr.get('scope')}")
    print(f"    PSU channel   : CH{psu_cfg.get('channel', 1)}  →  {psu_cfg.get('vin_v', 5.0)} V")
    print(f"    Timebase      : {scp_cfg.get('timebase_s_per_div', 1e-3) * 1e3:.0f} ms/div  |  "
          f"Pre-trigger: {scp_cfg.get('pretrigger_pct', 20)}%")
    print()
    print("  Scope Config 1 channels:")
    for ch in PowerSequencingTest.CONFIG1_CHANNELS:
        lim     = limits.get(ch.name, {}).get("max_time_ms", None)
        lim_str = f"{lim:.1f} ms" if lim else "—"
        print(f"    CH{ch.channel}: {ch.name:<8} ({ch.test_point})  "
              f"90% @ {ch.threshold_90pct_v:.3f} V  limit {lim_str}")
    print()
    print("  Scope Config 2 channels:")
    for ch in PowerSequencingTest.CONFIG2_CHANNELS:
        lim     = limits.get(ch.name, {}).get("max_time_ms", None)
        lim_str = f"{lim:.1f} ms" if lim else "—"
        print(f"    CH{ch.channel}: {ch.name:<8} ({ch.test_point})  "
              f"90% @ {ch.threshold_90pct_v:.3f} V  limit {lim_str}")
    print()

    # ── Mode selection ────────────────────────────────────────────────────────
    if args.mode:
        mode = args.mode
        print(f"  Mode: {mode}  (from --mode flag)")
        print()
    else:
        mode = interactive_mode_selector()
        if mode is None:
            return 0
        print(f"  Running: {mode}")

    # ── Setup instructions (mode-aware) ───────────────────────────────────────
    print_setup_instructions(instr, psu_cfg, scp_cfg, mode)

    # ── Output directory selection ────────────────────────────────────────────
    output_dir = args.output
    if output_dir is None:
        cfg_out = _CFG.get("output_dir", {})
        cfg_dir = (
            cfg_out.get("path", "power_sequencing_results")
            if isinstance(cfg_out, dict)
            else str(cfg_out)
        )
        output_dir = prompt_output_directory(cfg_dir)

    # ── Start confirmation ────────────────────────────────────────────────────
    response = input("  All connections made? Press ENTER to start (or 'q' to quit): ").strip().lower()
    if response in ('q', 'quit', 'exit'):
        print("  Cancelled.")
        return 0

    # ── Create test instance and run ──────────────────────────────────────────
    test    = PowerSequencingTest(output_dir=output_dir)
    success = test.run(mode=mode)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
