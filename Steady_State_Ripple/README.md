# Steady-State Rail Verification and Ripple Test — Technician Guide

## Overview

This test verifies that all power rails on the DUT sit at correct steady-state DC voltage levels under nominal input conditions (5 V / 2 A), and that AC ripple on each rail does not exceed its specified limit.

**Objective:** Verify all power rails reach and maintain correct steady-state DC voltage levels under nominal input conditions, with no excessive ripple, drift, or dependency faults.

**Pass criterion:** Each selected rail must satisfy both conditions:
1. DC RMS voltage falls within its expected range (from `steady_state_ripple_config.json`)
2. AC ripple (Vpp) is below the specified limit — or the rail has no ripple specification and the ripple step is skipped

---

## Equipment Required

| Instrument | Role |
|---|---|
| Keithley Power Supply (e.g. 2230-30-3) | Pre-configured at 5 V / 2 A before the test starts. **Not controlled by this script.** |
| Keysight Oscilloscope (DSOX6004A) | CH1 used for all measurements — one rail at a time |
| Oscilloscope probe (1:1) | Set slide switch to **×1** before starting |
| GND spring tip (coaxial) | Replaces the alligator-clip ground for ripple measurements — **short ground path is critical** |
| USB cable | Connects oscilloscope to PC |

> The PSU is **not controlled by this script**. The DUT must already be powered and stable before you run the test.

---

## File Structure

```
Steady_State_Ripple/
├── steady_state_ripple_config.json     ← EDIT THIS to change settings
├── steady_state_ripple_test.py         ← Test logic (do not edit for routine use)
└── run_steady_state_ripple_test.py     ← Run this to start the test
```

**The only file you need to edit is `steady_state_ripple_config.json`.**

---

## Rail Specifications

| Rail | Test Point | Expected Range | Ripple Limit |
|---|---|---|---|
| 5V\_Input | PSU / TP | 4.75 – 5.25 V | — (no spec) |
| 3V6 | TP2 | 3.42 – 3.78 V | < 50 mVpp |
| 3V3 | TP10 | 3.14 – 3.47 V | < 50 mVpp |
| 2V5 | TP9 | 2.38 – 2.63 V | < 30 mVpp |
| 1V8 | TP6 | 1.71 – 1.89 V | < 30 mVpp |
| 1V35 | TP7 | 1.28 – 1.42 V | < 20 mVpp |
| 1V\_PS | TP5 | 0.95 – 1.05 V | < 20 mVpp |
| 1V\_PL | TP8 | 0.95 – 1.05 V | < 20 mVpp |

---

## Step 1 — Set Up the Config File

Open `steady_state_ripple_config.json` in any text editor (Notepad, VS Code, etc.).

### 1a. Set instrument addresses

```json
"instrument_addresses": {
    "psu":   "USB0::0x05E6::0x2230::805224014816710016::INSTR",
    "scope": "USB0::0x0957::0x1780::MY65220169::INSTR"
}
```

Find addresses using NI-MAX or:

```
python -c "import pyvisa; print(pyvisa.ResourceManager().list_resources())"
```

Replace the strings with the addresses shown for your scope (and PSU — kept for reference).

### 1b. Verify PSU settings (reference only)

```json
"psu_settings": {
    "channel":         1,
    "vin_v":           5.0,       ← Expected supply voltage (V)
    "current_limit_a": 2.0,       ← Expected current limit (A)
    "ovp_level_v":     6.0        ← Expected OVP level (V)
}
```

These values are displayed during setup instructions. The script does **not** connect to or control the PSU.

### 1c. Scope measurement settings

```json
"scope_settings": {
    "probe_attenuation":         1.0,    ← 1:1 probe — slide switch to ×1
    "bandwidth_limit_20mhz":     true,   ← 20 MHz BW limit enabled on CH1
    "dc_timebase_s_per_div":     0.01,   ← 10 ms/div for DC acquisition
    "ripple_timebase_s_per_div": 0.1,    ← 100 ms/div for ripple acquisition
    "ripple_v_scale_v_per_div":  0.05,   ← 50 mV/div for ripple
    "ripple_coupling":           "AC",   ← AC coupling for ripple phase
    "ripple_settle_periods":     3       ← Wait 3 × (10 × 100 ms) = 3 s after run
}
```

### 1d. Add, remove, or modify rails

Each entry in the `"rails"` array defines one rail:

```json
{
    "name":            "3V6",
    "test_point":      "TP2",
    "nominal_v":       3.6,       ← Used to centre the DC waveform on screen
    "min_v":           3.42,      ← Lower limit for DC RMS FS measurement
    "max_v":           3.78,      ← Upper limit
    "dc_v_scale":      0.5,       ← Scope V/div for DC measurement (V)
    "ripple_max_mvpp": 50.0       ← Ripple limit (mVpp). Set to null → ripple skipped
}
```

Setting `"ripple_max_mvpp": null` skips the ripple measurement entirely for that rail (used for the 5V\_Input rail).

### 1e. Set output directory

```json
"output_dir": {
    "path": "steady_state_ripple_results"
}
```

Use forward slashes `/` in the path, even on Windows. A relative path is resolved from the folder where you run the script.

---

## Step 2 — Physical Setup

### PSU

1. Connect PSU CH1 **+** terminal (red) to **DUT VIN**.
2. Connect PSU CH1 **−** terminal (black) to **DUT GND**.
3. Set PSU to **5 V / 2 A, OVP 6 V**, output **ON**.
4. Confirm all DUT rails are stable before starting the script.

> The PSU does **not** need to be connected to the PC for this test.

### Oscilloscope probe

Set the probe slide switch to **×1** (1:1 attenuation) **before** connecting it to the scope.

CH1 is the only channel used. CH2–4 are disabled by the script.

The script reconfigures the probe coupling automatically:
- DC voltage phase → **DC coupling**
- Ripple phase → **AC coupling**

### GND spring (ripple measurements only)

For the ripple phase of each rail, the script will prompt you to fit a **coaxial GND spring** onto the probe barrel and remove the alligator-clip ground lead.

| Why it matters |
|---|
| A long alligator-clip ground lead acts as an inductor. On a 50 mVpp ripple measurement it can add 10–30 mV of apparent noise, causing false FAILs. |
| A GND spring keeps the ground loop area to < 1 cm² — the only reliable method for sub-50 mV ripple work. |

---

## Step 3 — Run the Test

Open a terminal in the `Steady_State_Ripple` folder and run:

```
python run_steady_state_ripple_test.py
```

### What appears on screen

After the banner and config summary the **interactive rail selector** appears:

```
  RAIL SELECTION
  ══════════════════════════════════════════════════════════════════════
  UP/DOWN: Navigate   SPACE/TAB: Toggle   A: All   N: None   ENTER: Run   Q: Quit

  >> [X]  5V_Input    PSU / TP      4.75 – 5.25 V    no ripple spec
     [X]  3V6         TP2           3.42 – 3.78 V    ripple < 50 mVpp
     [X]  3V3         TP10          3.14 – 3.47 V    ripple < 50 mVpp
     [X]  2V5         TP9           2.38 – 2.63 V    ripple < 30 mVpp
     [X]  1V8         TP6           1.71 – 1.89 V    ripple < 30 mVpp
     [X]  1V35        TP7           1.28 – 1.42 V    ripple < 20 mVpp
     [X]  1V_PS       TP5           0.95 – 1.05 V    ripple < 20 mVpp
     [X]  1V_PL       TP8           0.95 – 1.05 V    ripple < 20 mVpp

  Selected: 8 rails
```

| Key | Action |
|---|---|
| `↑` / `↓` | Move cursor |
| `SPACE` or `TAB` | Toggle selected rail on/off |
| `A` | Select all rails |
| `N` | Deselect all rails |
| `ENTER` | Confirm selection and proceed |
| `Q` or `ESC` | Cancel |

After confirming, the script prints setup instructions and prompts:

```
  All setup complete? Press ENTER to start (or 'q' to quit):
```

Press **ENTER** to begin.

---

## Step 4 — Test Execution (Rail by Rail)

For each selected rail the script runs two phases.

### Phase 1 — DC Voltage

```
  ── Rail 2 / 7 ─────────────────────────────────── 3V6 ══
  RAIL: 3V6  (TP2)
  Nominal: 3.600 V    Expected: 3.42 – 3.78 V

  STEP 1 of 2 — DC Voltage
  Connect probe tip (DC mode, 1:1) to  TP2  (3V6 rail).
  Attach ground clip to nearest board GND.
  Press ENTER when probe is connected...
```

1. Connect the probe tip to the stated test point.
2. Clip the ground lead to the nearest GND via/pad.
3. Press **ENTER**.

The script then:
- Configures CH1: **DC coupling · 20 MHz BW · auto-trigger**
- Sets V/div to the value from config (`dc_v_scale`)
- Sets vertical offset so the signal sits at screen centre
- Runs the scope for ~1.5 s, stops it, then measures **DC RMS FS** (`:MEASure:VRMS? DISPlay,DC,CHANnel1`)
- Saves a screenshot: `<RAIL>_dc_voltage.png`

```
  Measured DC RMS:  3.6412 V   [PASS]
  Saved: 3V6_dc_voltage.png
```

### Phase 2 — Ripple

```
  STEP 2 of 2 — Ripple  (limit: < 50 mVpp)

  For accurate ripple measurement — SHORT GROUND PATH IS ESSENTIAL:
    1. Remove the alligator-clip ground lead from the probe.
    2. Fit a GND SPRING (coaxial spring tip) onto the probe barrel.
    3. Connect the GND spring to a board ground point closest to the 3V6 rail.
    4. Place the probe tip directly across the LAST OUTPUT CAPACITOR of the 3V6 rail.
       (Long ground leads add inductance — they inflate ripple readings.)
  Press ENTER when GND spring and probe tip are positioned...
```

1. Fit the GND spring (remove the alligator-clip ground first).
2. Seat the spring on the nearest GND pad to the rail's last output capacitor.
3. Touch the probe tip across the capacitor.
4. Press **ENTER**.

The script then:
- Reconfigures CH1: **AC coupling · 20 MHz BW · 50 mV/div · 100 ms/div**
- Runs the scope, waits **3 s** for the waveform to settle
- Stops the scope
- Measures **Vpp** (`:MEASure:VPP? CHANnel1`)
- Saves a screenshot: `<RAIL>_ripple.png`

```
  Measured Ripple:  44.2 mVpp   [PASS]
  Saved: 3V6_ripple.png
```

### Rails with no ripple specification

For the **5V\_Input** rail (and any rail with `"ripple_max_mvpp": null`), Phase 2 is skipped:

```
  STEP 2 of 2 — Ripple:  No ripple spec for 5V_Input — skipped.
```

---

## Step 5 — Review Results

After all selected rails are measured, the script prints a summary table:

```
  ══════════════════════════════════════════════════════════════════════════════════
  RESULTS SUMMARY
  ══════════════════════════════════════════════════════════════════════════════════
  Rail        TP            Nominal    Measured DC       Range         DC    Ripple mVpp     Limit  Ripple
  ──────────────────────────────────────────────────────────────────────────────────────
  5V_Input    PSU / TP      5.000V    5.0921 V      4.75–5.25V     OK           —           N/A     N/A
  3V6         TP2           3.600V    3.6412 V      3.42–3.78V     OK        44.2         <50      PASS
  3V3         TP10          3.300V    3.3801 V      3.14–3.47V     OK        45.1         <50      PASS
  2V5         TP9           2.500V    2.5021 V      2.38–2.63V     OK        18.3         <30      PASS
  1V8         TP6           1.800V    1.7934 V      1.71–1.89V     OK        25.4         <30      PASS
  1V35        TP7           1.350V    1.3511 V      1.28–1.42V     OK        18.1         <20      PASS
  1V_PS       TP5           1.000V    1.0134 V      0.95–1.05V     OK        17.2         <20      PASS
  1V_PL       TP8           1.000V    1.0023 V      0.95–1.05V     OK        15.3         <20      PASS

  OVERALL: PASS — all rails within specification
  ══════════════════════════════════════════════════════════════════════════════════
```

All outputs are saved in a **timestamped run folder**:

```
steady_state_ripple_results/
└── run_20260407_143012/
    ├── steady_state_ripple_test.log
    ├── screenshots/
    │   ├── 5V_Input_dc_voltage.png
    │   ├── 3V6_dc_voltage.png
    │   ├── 3V6_ripple.png
    │   ├── 3V3_dc_voltage.png
    │   ├── 3V3_ripple.png
    │   ├── 2V5_dc_voltage.png
    │   ├── 2V5_ripple.png
    │   └── ...
    └── reports/
        ├── steady_state_ripple_results_20260407_143012.csv
        ├── steady_state_ripple_results_20260407_143012.json
        └── steady_state_ripple_summary_20260407_143012.txt
```

Each test run creates its own folder. Old results are never overwritten.

### `reports/steady_state_ripple_summary_TIMESTAMP.txt`

Human-readable table — primary document for sign-off.

### `reports/steady_state_ripple_results_TIMESTAMP.csv`

One row per rail. Open in Excel or Google Sheets. Columns: `rail_name`, `test_point`, `nominal_v`, `expected_range`, `measured_dc_v`, `dc_status`, `ripple_max_mvpp`, `measured_ripple_mvpp`, `ripple_status`.

### `reports/steady_state_ripple_results_TIMESTAMP.json`

Full structured data including overall pass/fail. Useful for programmatic post-processing or importing into test management systems.

### `screenshots/<RAIL>_dc_voltage.png`

Scope display for the DC voltage phase — CH1 DC coupled, signal centred on screen. The measurement value is visible in the scope's on-screen readout.

### `screenshots/<RAIL>_ripple.png`

Scope display for the ripple phase — CH1 AC coupled, 50 mV/div, 100 ms/div, scope in STOP mode after acquiring a settled waveform. Vpp readout visible on screen.

---

## Command-Line Options

| Option | Effect |
|---|---|
| *(no options)* | Interactive rail selector + output directory prompt |
| `--rails all` | Test all rails without the interactive selector |
| `--rails 3V6 2V5 1V8` | Test only the named rails (space-separated) |
| `--output PATH` | Override the output directory from config |
| `--verbose` | Print detailed instrument-level debug messages |

Examples:

```
python run_steady_state_ripple_test.py
python run_steady_state_ripple_test.py --rails all
python run_steady_state_ripple_test.py --rails 3V6 3V3 2V5
python run_steady_state_ripple_test.py --rails all --output D:/Results/Board_SN001
python run_steady_state_ripple_test.py --rails 1V8 1V35 --verbose
```

---

## Pass / Fail Logic

### Per-rail — DC voltage

| Condition | Status |
|---|---|
| `min_v ≤ measured_dc_v ≤ max_v` | **PASS** |
| Outside range | **FAIL** |
| Scope measurement returned no value | **ERROR** |

### Per-rail — Ripple

| Condition | Status |
|---|---|
| `measured_ripple_mvpp ≤ ripple_max_mvpp` | **PASS** |
| Exceeds limit | **FAIL** |
| Scope measurement returned no value | **ERROR** |
| Rail has `ripple_max_mvpp: null` in config | **N/A** (skipped) |

### Overall result

**PASS** only if every tested rail returns PASS on DC and PASS or N/A on Ripple. Any single FAIL or ERROR fails the overall result.

---

## Common Problems

### "ERROR: Config file not found"

`steady_state_ripple_config.json` is missing. It must be in the **same folder** as `steady_state_ripple_test.py`.

---

### "ERROR: Failed to connect to scope"

- Check the USB cable is connected to both the scope and the PC.
- Check the VISA address in the config matches NI-MAX.
- Check the scope is powered on.
- Run `python -c "import pyvisa; print(pyvisa.ResourceManager().list_resources())"` to list detected addresses.

---

### DC measurement is wrong / out of range

- Verify the probe tip is on the correct test point.
- Check the probe slide switch is set to **×1** (not ×10).
- Verify the DUT is fully powered up before starting the test.
- Check that the ground clip has a good connection to a nearby GND pad.

---

### Ripple reads much higher than expected

The most common cause is a **long ground lead**. At 50 mVpp sensitivity, a 10 cm ground wire can add 20–50 mV of apparent noise.

Checklist:
1. Use a **GND spring**, not the alligator-clip.
2. The spring must seat on the probe barrel, not hang loose.
3. The spring contact must touch **board ground right next to the capacitor** — not a ground via 2 cm away.
4. Verify the probe tip is across the **last** output capacitor of the rail (not the inductor input or mid-rail capacitor).

If readings are still elevated:
- Check that the scope is in **AC coupling** (the script sets this automatically; verify it on the scope display).
- Check for interference from adjacent switching regulators by probing a known-quiet point.

---

### Ripple phase screenshot shows a flat line (no waveform)

- The probe is not touching the capacitor, or the contact is intermittent.
- The scope AC coupling is blocking a very-low-frequency drift signal — confirm the timebase is 100 ms/div (set automatically).
- Verify the GND spring is making contact with the board.

---

### "No valid rails selected" when using `--rails`

Rail names are **case-sensitive**. Use the exact names from the config:
`5V_Input`, `3V6`, `3V3`, `2V5`, `1V8`, `1V35`, `1V_PS`, `1V_PL`.

---

## Modifying the Test

**To change a voltage range:** edit only `min_v` / `max_v` for that rail in `steady_state_ripple_config.json`.

**To change a ripple limit:** edit only `ripple_max_mvpp` for that rail.

**To add a new rail:**

```json
{
    "name":            "1V1_E0",
    "test_point":      "TP13",
    "nominal_v":       1.1,
    "min_v":           1.045,
    "max_v":           1.155,
    "dc_v_scale":      0.2,
    "ripple_max_mvpp": 20.0
}
```

Append it to the `"rails"` array. The rail will appear in the selector on the next run.

**To disable ripple for a rail** (voltage check only):

```json
"ripple_max_mvpp": null
```

**To change the ripple measurement window** (e.g. wider for lower-frequency switchers):

```json
"scope_settings": {
    "ripple_timebase_s_per_div": 0.2
}
```

**To change the ripple vertical scale** (e.g. rails with large expected ripple):

```json
"scope_settings": {
    "ripple_v_scale_v_per_div": 0.1
}
```

**Never edit `steady_state_ripple_test.py` or `run_steady_state_ripple_test.py`** for routine configuration changes.

---

## How the Code Works (Internal Reference)

### File roles

| File | Role |
|---|---|
| `steady_state_ripple_config.json` | Single source of truth for all parameters. Loaded once at startup. |
| `steady_state_ripple_test.py` | `SteadyStateRippleTest` class. Reads JSON via `_CFG`. Handles scope config, measurement, screenshots, and reports. |
| `run_steady_state_ripple_test.py` | Thin runner. Prints banner, reads config summary, shows interactive selector, imports and runs `SteadyStateRippleTest`. |

### DC RMS measurement

The scope is configured in free-run AUTO trigger mode:

```
:TRIGger:SWEep AUTO
```

After 1.5 s of acquisition the scope is stopped and the DC RMS full-screen value is read:

```
:MEASure:VRMS? DISPlay,DC,CHANnel1
```

This command returns the true RMS of the full displayed waveform including the DC component. For a stable DC rail (small ripple relative to the DC level), this equals the DC voltage to four significant figures.

### Ripple measurement

The scope is reconfigured with AC coupling, which blocks the DC component and centres the ripple waveform around 0 V:

```
:CHANnel1:COUPling AC
:CHANnel1:SCALe 0.05         ← 50 mV/div
:TIMebase:SCALe 0.1          ← 100 ms/div
```

After running for `ripple_settle_periods × 10 × ripple_timebase` = 3 s, the scope is stopped:

```
:STOP
```

Vpp is then measured from the acquired waveform:

```
:MEASure:VPP? CHANnel1
```

The returned value (in volts) is multiplied by 1000 to give mVpp and compared against `ripple_max_mvpp`.

### Output structure

```
SteadyStateRippleTest.__init__()
    → creates  run_YYYYMMDD_HHMMSS/screenshots/  and  .../reports/
    → opens    steady_state_ripple_test.log

SteadyStateRippleTest.run()
    → for each rail:
        _measure_dc_voltage(rail)   → Phase 1 — DC RMS FS + screenshot
        _measure_ripple(result, rail) → Phase 2 — Vpp + screenshot
    → _print_summary()
    → _save_reports()              → CSV + JSON + TXT
```
