# Input Range and OVP Test — Technician Guide

## Overview

This test characterises the power input behaviour of the DUT (Device Under Test) across its full input voltage range. It verifies:

- The DUT output voltage is correct at specific input voltages (**Fixed Vin tests**)
- The DUT output remains stable as input voltage ramps up and back down (**Sweep test**)
- OVP (Over-Voltage Protection) limits are correctly configured on the PSU

---

## Equipment Required

| Instrument | Role |
|---|---|
| Keithley Power Supply (e.g. 2230-30-3) | Provides Vin to DUT input |
| Keithley DMM6500 | Measures Vout at DUT output |
| USB cables (x2) | Connects instruments to PC |

Both instruments must be connected to the PC via USB before running the test.

---

## File Structure

```
Input_Range_OVP/
├── input_range_ovp_config.json   ← EDIT THIS to change settings
├── input_range_ovp_test.py       ← Test logic (do not edit for routine use)
└── run_input_range_ovp_test.py   ← Run this to start the test
```

**The only file you need to edit is `input_range_ovp_config.json`.**

---

## Step 1 — Set Up the Config File

Open `input_range_ovp_config.json` in any text editor (Notepad, VS Code, etc.).

### 1a. Set instrument addresses

Find your VISA addresses using NI-MAX or `python -m visa list`. Update these two lines:

```json
"instrument_addresses": {
    "psu": "USB0::0x05E6::0x2230::805224014806770001::INSTR",
    "dmm": "USB0::0x05E6::0x6500::04561287::INSTR"
}
```

Replace the address strings with the addresses shown for your PSU and DMM.

### 1b. Set the PSU channel

The Keithley 2230-30-3 has three channels (CH1, CH2, CH3). Set whichever channel is wired to DUT input:

```json
"instrument_settings": {
    "psu_channel": 1
}
```

### 1c. Set the output directory (optional)

By default results are saved in a folder called `input_range_ovp_results` next to the script. To save elsewhere (e.g. a shared network drive), change:

```json
"output_dir": {
    "path": "D:/TestResults/MyBoard/input_range_ovp"
}
```

Use forward slashes `/` in the path, even on Windows.

### 1d. Set test parameters

```json
"test_parameters": {
    "psu_current_limit_a": 1.0,       ← Maximum current PSU will deliver (A)
    "psu_ovp_level_v": 32.0,          ← PSU over-voltage protection trip level (V)

    "fixed_vin_settle_time_s": 1.0,   ← Seconds to wait after applying each fixed Vin before reading DMM

    "sweep_start_v": 0.0,             ← Sweep starts at this voltage (V)
    "sweep_max_v": 30.0,              ← Sweep peaks at this voltage (V)
    "sweep_step_v": 2.0,              ← Voltage increment per step (V)
    "step_dwell_time_s": 1.0,         ← How long to hold each step before moving (s)
    "dmm_read_interval_s": 0.2,       ← How often DMM takes a reading during each step (s)
    "step_settle_time_s": 0.3,        ← Short wait after changing voltage, before reading (s)

    "sweep_vin_min_operating_v": 4.5, ← Below this Vin, Vout is not checked (pre-regulation region)
    "sweep_expected_vout_v": 3.6,     ← Expected DUT output voltage in operating range (V)
    "sweep_vout_tolerance_v": 0.1,    ← Acceptable deviation from expected Vout (V)

    "dmm_nplc": 0.2                   ← DMM measurement speed (0.2 = fast, 1.0 = accurate)
}
```

### 1e. Set fixed Vin test points

Each entry applies a fixed input voltage and checks that Vout is within tolerance:

```json
"fixed_vin_tests": [
    {"vin_v": 4.5,  "expected_vout_v": 3.6, "vout_tolerance_v": 0.1},
    {"vin_v": 5.0,  "expected_vout_v": 3.6, "vout_tolerance_v": 0.1},
    {"vin_v": 30.0, "expected_vout_v": 3.6, "vout_tolerance_v": 0.1}
]
```

- `vin_v` — input voltage the PSU will be set to (V)
- `expected_vout_v` — what the DMM should measure at DUT output (V)
- `vout_tolerance_v` — how close the reading must be to pass (V). A reading of 3.6 ± 0.1 V is PASS.

To add a test point, copy an existing entry and change the values. To remove one, delete the entire `{ }` block including its comma.

---

## Step 2 — Physical Setup

1. Connect PSU output leads to **DUT VIN** (positive) and **GND** (negative).
2. Keep the PSU output **OFF** — the script will turn it on.
3. Connect DMM probes to **DUT VOUT** (HI lead) and **GND** (LO lead). The script will prompt you before it starts measuring.
4. Connect both instruments to the PC via USB.
5. Power on both instruments.

---

## Step 3 — Run the Test

Open a terminal in the `Input_Range_OVP` folder and run:

```
python run_input_range_ovp_test.py
```

### What appears on screen

After the banner and config summary, the **interactive mode selector** appears:

```
  ----------------------------------------------------------------------
  Ensure the DUT is ready and leads are connected to the PSU output.
  ----------------------------------------------------------------------

  TEST MODE SELECTION
  ==============================================================
  UP/DOWN: Navigate | TAB: Select | ENTER: Run | Q: Quit

  >> (X)  Full Test           Fixed Vin tests  +  Sweep  (complete characterisation)
     ( )  Fixed Vin Only      Apply configured voltages, read Vout, skip sweep
     ( )  Sweep Only          Vin ramp 0 -> Vmax -> 0 with continuous DMM capture

  Mode: Full Test
```

**Controls:**

| Key | Action |
|---|---|
| UP / DOWN arrow | Move the `>>` cursor between options |
| TAB or SPACE | Select the highlighted option (fills the radio button) |
| ENTER | Confirm selection and start the test |
| Q or ESC | Cancel and exit |

Navigate to your desired mode, press TAB to select it (the `(X)` moves), then press ENTER to start.

### Probe setup prompt

The script will then prompt you to connect the DMM probes:

```
  ============================================================
  PROBE SETUP — ACTION REQUIRED
  ============================================================

  Connect DMM probes to the DUT OUTPUT:
    + (HI) lead  ->  VOUT positive terminal
    - (LO) lead  ->  GND / VOUT return

  PSU leads should already be on DUT INPUT (VIN).

  Press ENTER when probes are connected and ready...
```

Connect the DMM probes, then press **ENTER**.

---

## Step 4 — Test Execution (Automatic)

Once you press ENTER the test runs completely automatically. You will see live progress.

### Phase 1 — Fixed Vin Tests

The PSU steps to each configured voltage, waits for the output to settle, reads the DMM, and logs a PASS or FAIL:

```
  -- Phase 1: Fixed Vin Tests ----------------------------------------
  VIN (V)      VOUT (V)       EXPECTED (V)     STATUS
  -------------------------------------------------------
  4.5          3.6021         3.6              PASS
  5.0          3.6018         3.6              PASS
  30.0         3.5997         3.6              PASS
  -------------------------------------------------------
```

**PASS** — DMM reading is within `vout_tolerance_v` of `expected_vout_v`.  
**FAIL** — DMM reading is outside the tolerance band.  
**ERROR** — Instrument communication failed at this step.

After each test point, the PSU returns to 0 V and the output is disabled before moving on.

### Phase 2 — Vin Sweep

The PSU ramps from 0 V up to the configured maximum, then back down to 0 V in steps. The DMM takes readings continuously throughout. Live progress is shown:

```
  -- Phase 2: Vin Sweep ----------------------------------------------
  0 V  ->  30 V  ->  0 V
  Step: 2.0 V  |  Dwell: 1.0 s  |  DMM interval: 0.20 s
  Total steps: 31

  [ 16/31] Vin set=30.0V  Vin meas=29.98V  Vout=3.6014V
```

After the sweep is complete:
- **PASS** — every DMM reading taken while Vin ≥ `sweep_vin_min_operating_v` was within `sweep_vout_tolerance_v` of `sweep_expected_vout_v`.
- **FAIL** — at least one reading was outside tolerance.

### Generating outputs

```
  Generating plots...
  Saved: plots/psu_sweep_20250402_143012.png
  Saved: plots/dmm_sweep_20250402_143012.png

  Writing reports...
  Saved: reports/input_range_ovp_results_20250402_143012.csv
  Saved: reports/input_range_ovp_results_20250402_143012.json
  Saved: reports/input_range_ovp_summary_20250402_143012.txt

  ==================================================
  OVERALL RESULT : PASS
  ==================================================
  Run folder     : input_range_ovp_results/run_20250402_143012
```

---

## Step 5 — Review the Results

All outputs are saved inside a **timestamped run folder**:

```
input_range_ovp_results/
└── run_20250402_143012/
    ├── input_range_ovp_test.log
    ├── reports/
    │   ├── input_range_ovp_results_20250402_143012.csv
    │   ├── input_range_ovp_results_20250402_143012.json
    │   └── input_range_ovp_summary_20250402_143012.txt
    └── plots/
        ├── psu_sweep_20250402_143012.png
        └── dmm_sweep_20250402_143012.png
```

Each test run gets its own folder. Old results are never overwritten.

### `reports/input_range_ovp_summary_TIMESTAMP.txt` — Human-readable summary

The main document for sign-off and archiving. Opens in any text editor.

```
=================================================================
  INPUT RANGE AND OVP TEST — RESULTS SUMMARY
=================================================================
  Date / Time    : 2025-04-02 14:30:12
  PSU Address    : USB0::0x05E6::0x2230::...
  DMM Address    : USB0::0x05E6::0x6500::...
  PSU Channel    : CH1
  Current Limit  : 1.00 A
  OVP Level      : 32.0 V
=================================================================

  Results
  ------------------------------------------------------------
  PHASE      VIN (V)        VOUT (V)       EXPECTED (V)     STATUS
  ------------------------------------------------------------
  FIXED      4.5            3.6021         3.6              PASS
  FIXED      5.0            3.6018         3.6              PASS
  FIXED      30.0           3.5997         3.6              PASS
  SWEEP      0 - 30V        3.6008         3.6              PASS
  ------------------------------------------------------------

  Sweep Configuration
  ...

=================================================================
  OVERALL RESULT : PASS
=================================================================
```

### `reports/input_range_ovp_results_TIMESTAMP.csv` — Spreadsheet

Open in Microsoft Excel or Google Sheets. Contains one row per test point and one row for the sweep. Useful for comparing results across multiple runs or boards.

| Phase | Vin_V | Vout_V | Expected_V | Tolerance_V | Status |
|---|---|---|---|---|---|
| FIXED | 4.5 | 3.6021 | 3.6 | 0.1 | PASS |
| FIXED | 5.0 | 3.6018 | 3.6 | 0.1 | PASS |
| FIXED | 30.0 | 3.5997 | 3.6 | 0.1 | PASS |
| SWEEP | 0 - 30V | 3.6008 | 3.6 | 0.1 | PASS |

### `reports/input_range_ovp_results_TIMESTAMP.json` — Machine-readable

Contains complete test metadata (start time, end time, duration, instrument addresses) plus all results. Used by automated reporting systems or scripts that process multiple test runs. You do not need to open this manually.

### `plots/psu_sweep_TIMESTAMP.png` — PSU voltage and current graph

Two side-by-side graphs showing:
- **Left** — PSU voltage setpoint (dashed) vs measured voltage (solid) over time. These should track closely.
- **Right** — PSU current draw over time. Shows how much current the DUT drew as Vin changed.

### `plots/dmm_sweep_TIMESTAMP.png` — DUT output voltage graph

Shows the DMM-measured Vout over real time throughout the sweep. The output should be flat (regulated) once Vin exceeds the minimum operating voltage, and should drop to zero when Vin is too low to maintain regulation.

### `input_range_ovp_test.log` — Detailed log

A timestamped log of every action and error during the run. Used for debugging if something went wrong (instrument connection failures, unexpected readings, etc.). Not needed for normal review.

---

## Command-Line Options

| Option | Effect |
|---|---|
| *(no options)* | Show the interactive mode selector |
| `--mode full` | Skip selector, run full test (fixed Vin + sweep) |
| `--mode fixed` | Skip selector, run fixed Vin tests only |
| `--mode sweep` | Skip selector, run sweep only |
| `--output PATH` | Override the output directory from config |
| `--verbose` | Print detailed instrument-level debug messages |

Examples:

```
python run_input_range_ovp_test.py
python run_input_range_ovp_test.py --mode full
python run_input_range_ovp_test.py --mode fixed
python run_input_range_ovp_test.py --mode sweep
python run_input_range_ovp_test.py --output D:/Results/Board_SN001
python run_input_range_ovp_test.py --verbose
```

---

## Pass / Fail Logic

### Fixed Vin tests

Each fixed point passes if:

```
|measured_vout - expected_vout| <= vout_tolerance_v
```

Example: expected = 3.6 V, tolerance = 0.1 V → any reading between 3.5 V and 3.7 V is PASS.

### Sweep test

The sweep passes if **every single DMM sample** taken while `Vin >= sweep_vin_min_operating_v` is within `sweep_vout_tolerance_v` of `sweep_expected_vout_v`. One out-of-tolerance sample fails the sweep.

### Overall result

PASS only if all fixed Vin tests are PASS **and** the sweep is PASS. Any single FAIL or ERROR fails the overall result.

---

## Common Problems

### "ERROR: Config file not found"

`input_range_ovp_config.json` is missing or in the wrong folder. Make sure it is in the same folder as `input_range_ovp_test.py`.

### "ERROR: Config file has invalid JSON"

There is a syntax error in the JSON (missing comma, extra bracket, etc.). Open the file and look for the line number in the error message. Common mistakes:

- Missing comma between two entries
- Trailing comma after the last item in a list
- Mismatched `{` / `}` or `[` / `]`

Use a JSON validator (e.g. jsonlint.com) to find the exact error.

### "ERROR: Failed to connect to PSU / DMM"

- Check USB cable is plugged in to both instrument and PC
- Check the VISA address in the config matches what NI-MAX shows
- Check the instrument is powered on
- Try unplugging and re-plugging the USB cable

### Test shows FAIL on sweep

- Check the DUT is fully powered and not in a fault state
- Increase `sweep_vout_tolerance_v` if the DUT has natural output ripple
- Reduce `dmm_nplc` to 0.1 for faster readings (less averaging noise)
- If the failure is only at the top of the sweep range, the DUT may not support that high an input voltage

### Plots not generated

matplotlib is not installed. Install it with:

```
pip install matplotlib
```

The test will still run and produce CSV/JSON/TXT reports without matplotlib.

---

## Modifying the Test

**To change voltages, tolerances, or instrument addresses:** edit `input_range_ovp_config.json` only.

**To add more fixed test points:** add more entries to the `fixed_vin_tests` array in the JSON:

```json
{"vin_v": 12.0, "expected_vout_v": 3.6, "vout_tolerance_v": 0.1}
```

**To run a faster sweep:** reduce `sweep_step_v` and `step_dwell_time_s`:

```json
"sweep_step_v": 1.0,
"step_dwell_time_s": 0.5,
"dmm_read_interval_s": 0.1
```

**To run a slower, more detailed sweep** (more data points):

```json
"sweep_step_v": 1.0,
"step_dwell_time_s": 2.0,
"dmm_read_interval_s": 0.1
```

**Never edit `input_range_ovp_test.py` or `run_input_range_ovp_test.py`** for routine configuration changes. All parameters are controlled by the JSON file.

---

## How the Code Works (Internal Reference)

This section is for engineers who need to understand or maintain the code.

### File roles

| File | Role |
|---|---|
| `input_range_ovp_config.json` | Single source of truth for all test parameters. Loaded at startup. |
| `input_range_ovp_test.py` | Contains all test logic. Reads the JSON directly at module load (`_CFG`). Never imported by the user. |
| `run_input_range_ovp_test.py` | Thin runner. Parses CLI arguments, prints the banner, imports and runs `InputRangeOVPTest`. |

### Startup sequence

1. `run_input_range_ovp_test.py` is executed.
2. It imports `input_range_ovp_test`, which immediately calls `_load_config()`.
3. `_load_config()` reads `input_range_ovp_config.json` into the module-level dict `_CFG`. If the file is missing or malformed, the program exits with a clear error.
4. `_build_fixed_vin_tests(_CFG)` builds the list of `FixedVinPoint` objects and stores them as `InputRangeOVPTest.FIXED_VIN_TESTS` (a class attribute). The runner uses this to display the config summary without constructing the test object.
5. The runner prints the banner and config summary, then waits for confirmation.
6. `InputRangeOVPTest(output_dir=...)` is constructed. The constructor reads all values from `_CFG` and creates the run folder structure.

### Run folder creation

The constructor creates:

```
<output_dir>/run_YYYYMMDD_HHMMSS/
    input_range_ovp_test.log    ← created by FileHandler
    reports/                    ← created empty, populated later
    plots/                      ← created empty, populated later
```

If the requested output path is not writable (permissions error), it falls back to a folder next to the script.

### Phase 1 — Fixed Vin (`run_fixed_vin_tests`)

For each `FixedVinPoint` in `FIXED_VIN_TESTS`:
1. Set PSU to `vin_v`.
2. Wait `fixed_vin_settle_time_s`.
3. Read DMM once (`measure_dc_voltage_fast`).
4. Compare to `expected_vout_v ± vout_tolerance_v`.
5. Record `FixedVinResult` with status PASS / FAIL / ERROR.

After all points: PSU returns to 0 V and output is disabled.

### Phase 2 — Sweep (`run_sweep_test`)

`_build_sweep_setpoints()` generates the full list: `[0, 2, 4, ..., 30, 28, ..., 0]`.

For each setpoint:
1. Set PSU voltage.
2. Wait `step_settle_time_s` for output to stabilise.
3. Read PSU measured voltage and current once.
4. Enter dwell loop: repeatedly read DMM every `dmm_read_interval_s` for `step_dwell_time_s` seconds. Each reading is stored as a `SweepSample`.

After the sweep: pass/fail evaluated on operating-range samples only (`psu_setpoint_v >= sweep_vin_min_operating_v`).

### Report generation (`_generate_reports`)

Called once after both phases complete. Writes three files to `reports/`:

- **CSV** — one row per fixed point, one row for the sweep summary. Importable into Excel.
- **JSON** — full metadata + all results as structured data.
- **TXT** — formatted table + sweep config + overall verdict. The primary document for sign-off.

Returns the verdict string (`"PASS"` or `"FAIL"`).
