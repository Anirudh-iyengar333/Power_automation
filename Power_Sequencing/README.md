# Power Sequencing Test — Technician Guide

## Overview

This test verifies that all power rails on the DUT ramp in the correct order and reach their nominal voltages within defined timing windows after the 5 V input supply is applied.

**Objective:** Verify all power rails ramp in the correct order and reach nominal voltages within expected timing windows.

**Pass criterion:** Each rail must reach 90% of its nominal voltage within the time limit defined in `power_sequencing_config.json`.

---

## Equipment Required

| Instrument | Role |
|---|---|
| Keithley Power Supply (e.g. 2230-30-3) | Provides 5 V to DUT input; toggled ON/OFF to trigger the power-up sequence |
| Keysight Oscilloscope (DSOX6004A) | Captures all four rails simultaneously in single-shot mode |
| USB cables (x2) | Connects instruments to PC |
| DMM (manual) | Confirms 3V6 nominal voltage during Config 1 |

---

## File Structure

```
Power_Sequencing/
├── power_sequencing_config.json    ← EDIT THIS to change settings
├── power_sequencing_test.py        ← Test logic (do not edit for routine use)
└── run_power_sequencing_test.py    ← Run this to start the test
```

**The only file you need to edit is `power_sequencing_config.json`.**

---

## Step 1 — Set Up the Config File

Open `power_sequencing_config.json` in any text editor (Notepad, VS Code, etc.).

### 1a. Set instrument addresses

```json
"instrument_addresses": {
    "psu":   "USB0::0x05E6::0x2230::805224014816710016::INSTR",
    "scope": "USB0::0x0957::0x179B::MY12345678::INSTR"
}
```

Find addresses using NI-MAX or `python -m visa list`. Replace the strings with the addresses shown for your PSU and scope.

### 1b. Set PSU settings

```json
"psu_settings": {
    "channel":             1,        ← PSU channel wired to DUT VIN
    "vin_v":               5.0,      ← Supply voltage applied to DUT input (V)
    "current_limit_a":     2.0,      ← Maximum current the PSU will deliver (A)
    "ovp_level_v":         6.0,      ← PSU over-voltage protection level (V)
    "pre_poweroff_wait_s": 2.0,      ← Time DUT stays off before re-arming (s)
    "post_poweron_wait_s": 0.5       ← Short settle after PSU turns ON (s)
}
```

### 1c. Set scope timing

```json
"scope_settings": {
    "timebase_s_per_div":  1e-3,     ← 1 ms/div — adjust if rails are slower
    "pretrigger_pct":      20,       ← 20% of total window captured before trigger
    "trigger_slope":       "POS",    ← Rising edge trigger
    "sweep_mode":          "NORMal", ← Wait for actual trigger (single-shot)
    "trigger_wait_s":      15.0      ← Script waits this long for scope to trigger (s)
}
```

### 1d. Set timing limits per rail

```json
"rail_timing_limits": {
    "1V0PL": {"max_time_ms": 5.0},   ← Rail must reach 90% within 5 ms of T=0
    "1V0PS": {"max_time_ms": 5.0},
    "1V8":   {"max_time_ms": 10.0},
    "1V35":  {"max_time_ms": 15.0},
    "2V5":   {"max_time_ms": 20.0},
    "3V3":   {"max_time_ms": 25.0}
}
```

T = 0 is defined as the moment the trigger channel (Ch1) crosses 20% of its nominal voltage — i.e., when the 5 V input begins to rise and the first rail starts ramping.

### 1e. Set output directory (optional)

```json
"output_dir": {
    "path": "power_sequencing_results"
}
```

Use forward slashes `/` in the path, even on Windows.

---

## Step 2 — Physical Setup

### PSU

1. Connect PSU CH1 **+** terminal (red) to **DUT VIN** (5 V input).
2. Connect PSU CH1 **−** terminal (black) to **DUT GND**.
3. Leave the PSU output **OFF** — the script will toggle it.
4. Connect PSU to PC via USB.

### Scope — Config 1 (first capture)

| Scope Channel | Rail | Test Point | Notes |
|---|---|---|---|
| CH1 | 1V0PL | TP8 | **Trigger source** |
| CH2 | 1V8 | TP6 | |
| CH3 | 1V0PS | TP5 | |
| CH4 | 1V35 | TP7 | |

The script automatically configures the trigger: **rising edge on CH1 at 20% of 1 V = 0.20 V**.

### Scope — Config 2 (second capture, after first screenshot)

| Scope Channel | Rail | Test Point | Notes |
|---|---|---|---|
| CH1 | 2V5 | TP9 | **Trigger source** |
| CH2 | 1V8 | TP6 | |
| CH3 | 3V3 | TP10 | |
| CH4 | 1V35 | TP7 | |

The script automatically reconfigures the trigger: **rising edge on CH1 at 20% of 2.5 V = 0.50 V**.

### DMM

During Config 1, after the capture completes, the script will ask you to read the DMM on the 3V6 output and enter the value. The DMM does not connect to the PC — it is a manual confirmation step.

---

## Step 3 — Run the Test

Open a terminal in the `Power_Sequencing` folder and run:

```
python run_power_sequencing_test.py
```

### What appears on screen

After the banner and config summary, the script prints setup instructions and waits for confirmation:

```
  All connections made? Press ENTER to start (or 'q' to quit):
```

Press **ENTER** to begin.

---

## Step 4 — Test Execution (Automatic + Manual Prompts)

### Config 1 — Probe setup prompt

```
  SCOPE SETUP — CONFIG 1   (ACTION REQUIRED)
  CH1  →  1V0PL  (TP8)    [trigger channel]
  CH2  →  1V8    (TP6)
  CH3  →  1V0PS  (TP5)
  CH4  →  1V35   (TP7)

  Press ENTER when all probes are connected and ready...
```

Connect the probes for Config 1, then press **ENTER**.

### Config 1 — Automatic power-cycle and capture

The script:
1. Configures the scope (channels, timebase, trigger).
2. Turns the PSU output **OFF** (DUT powers down).
3. Arms the scope for a **single-shot** acquisition.
4. Turns the PSU output **ON** → DUT rails begin ramping → scope triggers on CH1.
5. Waits for scope to confirm acquisition complete.

```
  Turning PSU CH1 output OFF (DUT power down)...
  Arming scope for single-shot acquisition...
  Turning PSU CH1 output ON (5 V) — watching for trigger...
  Scope triggered — acquisition complete.
```

### Config 1 — 90% timing measurements

For each rail, the script:
- Downloads the waveform from that channel.
- Finds the first time after T=0 that the waveform crosses 90% of nominal.
- Places **cursor 1 at T=0** and **cursor 2 at the 90% crossing time**.
- Saves a screenshot showing the cursors.

Live table printed to screen:

```
  -- Config 1 : Rail Ramp Timing Measurements ------------------
  Rail       TP     90% (V)    Time (ms)      Limit (ms)    Status
  ----------------------------------------------------------------
  1V0PL      TP8    0.900      0.900          5.0           PASS
  1V8        TP6    1.620      1.920          10.0          PASS
  1V0PS      TP5    0.900      0.910          5.0           PASS
  1V35       TP7    1.215      3.160          15.0          PASS
  ----------------------------------------------------------------
```

After the table, a full four-channel screenshot is saved.

### DMM 3V6 confirmation

```
  DMM check: confirm 3V6 rail is in range 3.50 V – 3.70 V
  Enter DMM reading (V) and press ENTER: 3.612
  3V6 DMM: 3.6120 V  →  PASS
```

### Config 2 — Probe reconfiguration prompt

```
  SCOPE SETUP — CONFIG 2   (ACTION REQUIRED)
  Reconnect oscilloscope probes:
    CH1  →  2V5   (TP9)    [trigger channel]
    CH2  →  1V8   (TP6)
    CH3  →  3V3   (TP10)
    CH4  →  1V35  (TP7)

  Press ENTER when all probes are reconnected and ready...
```

Move the probes, then press **ENTER**.

### Config 2 — Capture and measurements

Identical sequence to Config 1. The trigger reconfigures automatically to CH1 at 0.50 V (20% of 2.5 V). Results are added to the same report.

```
  -- Config 2 : Rail Ramp Timing Measurements ------------------
  Rail       TP     90% (V)    Time (ms)      Limit (ms)    Status
  ----------------------------------------------------------------
  2V5        TP9    2.250      4.780          20.0          PASS
  1V8        TP6    1.620      1.920          10.0          PASS
  3V3        TP10   2.970      6.240          25.0          PASS
  1V35       TP7    1.215      3.160          15.0          PASS
  ----------------------------------------------------------------
```

---

## Step 5 — Review the Results

All outputs are saved in a **timestamped run folder**:

```
power_sequencing_results/
└── run_20260402_143012/
    ├── power_sequencing_test.log
    ├── screenshots/
    │   ├── config1_1V0PL_cursor.png   ← cursor at 90% crossing for 1V0PL
    │   ├── config1_1V8_cursor.png
    │   ├── config1_1V0PS_cursor.png
    │   ├── config1_1V35_cursor.png
    │   ├── config1_full.png           ← all 4 channels, no cursors
    │   ├── config2_2V5_cursor.png
    │   ├── config2_1V8_cursor.png
    │   ├── config2_3V3_cursor.png
    │   ├── config2_1V35_cursor.png
    │   └── config2_full.png
    └── reports/
        ├── power_sequencing_results_20260402_143012.csv
        ├── power_sequencing_results_20260402_143012.json
        └── power_sequencing_summary_20260402_143012.txt
```

Each test run gets its own folder. Old results are never overwritten.

### `reports/power_sequencing_summary_TIMESTAMP.txt` — Human-readable summary

Primary document for sign-off and archiving.

```
======================================================================
  POWER SEQUENCING TEST — RESULTS SUMMARY
======================================================================
  Date / Time    : 2026-04-02 14:30:12
  PSU Address    : USB0::...
  Scope Address  : USB0::...
  PSU Channel    : CH1  (5.0 V)
  Timebase       : 1 ms/div  |  Pre-trigger: 20%
  3V6 DMM check  : 3.612 V
======================================================================

  Rail Ramp Timing Measurements
  (T = 0 when 5 V input begins rising, i.e. scope trigger event)

  ---------------------------------------------------------------
  Rail       TP     90% V      Measured (ms)    Limit (ms)    Status
  ---------------------------------------------------------------
  1V0PL      TP8    0.900      0.900            5.0           PASS
  1V8        TP6    1.620      1.920            10.0          PASS
  1V0PS      TP5    0.900      0.910            5.0           PASS
  1V35       TP7    1.215      3.160            15.0          PASS
  2V5        TP9    2.250      4.780            20.0          PASS
  1V8        TP6    1.620      1.920            10.0          PASS
  3V3        TP10   2.970      6.240            25.0          PASS
  1V35       TP7    1.215      3.160            15.0          PASS
  ---------------------------------------------------------------

======================================================================
  OVERALL RESULT : PASS
======================================================================
```

### `reports/power_sequencing_results_TIMESTAMP.csv` — Spreadsheet

One row per rail per config. Open in Excel or Google Sheets to compare results across runs or boards.

| Config | Rail | Test_Point | Nominal_V | Threshold_90pct_V | Measured_Time_ms | Max_Time_ms | Status |
|---|---|---|---|---|---|---|---|
| Config 1 | 1V0PL | TP8 | 1.0 | 0.9 | 0.900 | 5.0 | PASS |
| Config 1 | 1V8 | TP6 | 1.8 | 1.62 | 1.920 | 10.0 | PASS |
| Config 2 | 2V5 | TP9 | 2.5 | 2.25 | 4.780 | 20.0 | PASS |
| Config 2 | 3V3 | TP10 | 3.3 | 2.97 | 6.240 | 25.0 | PASS |

### `screenshots/config1_<RAIL>_cursor.png` — Cursor measurements

Each screenshot shows the 4-channel waveform with:
- **Cursor X1** at T=0 (trigger point, when 5 V input began rising)
- **Cursor X2** at the 90% threshold crossing time for that rail

The time delta between the cursors is the reported 90% timing value.

### `screenshots/config1_full.png` / `config2_full.png` — Full waveform captures

Four-channel overview without cursors. Useful for reviewing the complete power-up sequence at a glance.

---

## Command-Line Options

| Option | Effect |
|---|---|
| *(no options)* | Interactive mode selector + output directory prompt |
| `--mode full` | Full test: Config 1 + Config 2 (2 power cycles, all 6 rails) |
| `--mode config1` | Config 1 only: 1V0PL, 1V8, 1V0PS, 1V35 (1 power cycle) |
| `--mode config2` | Config 2 only: 2V5, 1V8, 3V3, 1V35 (1 power cycle) |
| `--mode capture` | Power-cycle + full screenshots only, skip cursor analysis |
| `--mode reanalyze` | Skip power cycle; analyse current scope waveform |
| `--output PATH` | Override the output directory from config |
| `--verbose` | Print detailed instrument-level debug messages |

Examples:

```
python run_power_sequencing_test.py
python run_power_sequencing_test.py --mode full
python run_power_sequencing_test.py --mode config1 --output D:/Results/Board_SN001
python run_power_sequencing_test.py --mode reanalyze --verbose
```

---

## Pass / Fail Logic

### Per-rail result

A rail **PASSES** if:

```
measured_time_ms <= max_time_ms   (from rail_timing_limits in config)
```

where `measured_time_ms` is the time from T=0 (trigger) to the first sample at or above 90% of the rail's nominal voltage.

A rail returns **ERROR** if the waveform analysis could not extract a crossing time (e.g., the rail never reached threshold within the captured window, or communication with the scope failed).

### Overall result

**PASS** only if every rail in both configurations returns PASS. Any single FAIL or ERROR fails the overall result.

---

## Common Problems

### "ERROR: Config file not found"

`power_sequencing_config.json` is missing or in the wrong folder. It must be in the same folder as `power_sequencing_test.py`.

### "ERROR: Failed to connect to PSU / scope"

- Check USB/GPIB cables are connected to both instrument and PC.
- Check the VISA address in the config matches what NI-MAX shows.
- Check the instrument is powered on.
- Try `python -c "import pyvisa; print(pyvisa.ResourceManager().list_resources())"` to list detected addresses.

### "ERROR: Scope did not trigger within 15 s"

- Verify Ch1 probe is correctly connected to the trigger test point.
- Check the trigger level: 20% of 1V0 = 0.20 V for Config 1, 20% of 2V5 = 0.50 V for Config 2. Adjust `trigger_wait_s` in the config if the DUT is slow to power up.
- Confirm the PSU is actually supplying voltage by checking the front panel.

### Rail shows FAIL (too slow)

- Increase `max_time_ms` for that rail if the limit is too tight for this board revision.
- Verify the probe is on the correct test point.
- Check for excessive load on the rail slowing the ramp.

### Rail shows ERROR (waveform not captured)

- The rail may not have reached 90% within the 8 ms post-trigger window. Try increasing `timebase_s_per_div` to `2e-3` (2 ms/div) for a wider window.
- Verify the probe contact is solid.

### Scope screenshots are blank

- The scope may have been in the wrong acquisition state. Ensure single-shot mode is selected before each capture (the script sets this automatically — verify no manual mode change on the scope front panel during the test).

---

## Modifying the Test

**To change timing limits:** edit only the `rail_timing_limits` section in `power_sequencing_config.json`.

**To change the timebase** (wider window for slower boards):

```json
"scope_settings": {
    "timebase_s_per_div": 2e-3
}
```

**To change the vertical scale for a specific rail:**

```json
"scope_config_1": {
    "channels": {
        "1": {"v_scale": 0.5, "v_offset": 0.5}
    }
}
```

**Never edit `power_sequencing_test.py` or `run_power_sequencing_test.py`** for routine configuration changes.

---

## How the Code Works (Internal Reference)

### File roles

| File | Role |
|---|---|
| `power_sequencing_config.json` | Single source of truth for all parameters. Loaded once at startup. |
| `power_sequencing_test.py` | Contains all test and analysis logic. Reads JSON via `_CFG`. |
| `run_power_sequencing_test.py` | Thin runner. Prints banner, reads config summary, imports and runs `PowerSequencingTest`. |

### 90% crossing time algorithm

After single-shot capture, for each channel:

1. **Preamble query** (`get_waveform_preamble`) returns `x_increment`, `x_origin`, `x_reference`, `y_increment`, `y_origin`, `y_reference`.
2. **Raw data download** (`get_waveform_data`) returns an array of raw byte values.
3. **Physical conversion:**
   ```
   time[i]    = x_increment * (i - x_reference) + x_origin
   voltage[i] = y_increment * (raw[i] - y_reference) + y_origin
   ```
4. **Threshold search:** scan samples where `time[i] >= 0` (after trigger). Return the first `time[i]` where `voltage[i] >= 0.9 * nominal_v`.
5. **Units conversion:** result in seconds × 1000 = milliseconds.

### Cursor placement

After computing `t_90_s` for a channel:

```
scope.set_marker_mode("WAVeform")
scope.set_marker_x1y1_source(channel)   # marker 1 tracks this channel
scope.set_marker_x2y2_source(channel)   # marker 2 tracks this channel
scope.set_marker_x_position(1, 0.0)     # X1 at T=0 (trigger)
scope.set_marker_x_position(2, t_90_s)  # X2 at 90% crossing time
```

The scope display shows Y1 at the waveform voltage at T=0 (≈0 V) and Y2 at the 90% voltage, confirming the threshold. ΔX readout = measured timing.

### Pre-trigger offset calculation

With 20% pre-trigger and 1 ms/div (10 ms total window):

```
total_window_s   = 10 × timebase_s  = 10 ms
pre_trigger_s    = 20% × 10 ms     = 2 ms   (captured before trigger)
timebase_offset  = (10 ms / 2) − 2 ms = 3 ms  (trigger appears 2 ms from left edge)
```

Sent to scope as `:TIMebase:OFFSet 3e-3`.
