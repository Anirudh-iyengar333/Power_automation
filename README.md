# Digantara Power Rail Test Automation Framework

A modular test automation framework for power rail verification on embedded systems. Each test suite controls laboratory instruments over VISA/SCPI, executes a standardised test sequence, captures oscilloscope screenshots, and saves structured results.

---

## Project Structure

```
Digantara_Automation/
├── instrument_control/       # Shared instrument drivers (oscilloscopes, PSUs, loads, DMMs)
│
├── <TestSuite>/              # One folder per test type, e.g.:
│   ├── <suite>_config.json   #   Edit this to configure rails, limits, and instrument addresses
│   ├── <suite>_test.py       #   Core test logic
│   ├── run_<suite>_test.py   #   Interactive runner — start here
│   └── README.md             #   Suite-specific documentation
│
├── run_YYYYMMDD_HHMMSS/      # Auto-created output directory per run
│   ├── screenshots/          #   Oscilloscope captures
│   ├── reports/              #   JSON / CSV / TXT results
│   └── *.log                 #   Execution log
│
└── README.md                 # This file
```

### Current Test Suites

| Folder | What it tests |
|--------|---------------|
| `Steady_State_Ripple/` | DC voltage accuracy and AC ripple on each rail under steady load |
| `Load_Transient/` | Voltage droop, overshoot, and recovery time under dynamic load steps |
| `Power_Sequencing/` | Power-on/off rail sequencing order and timing |
| `Input_Range_OVP/` | Input voltage range compliance and over-voltage protection (OVP) trip points |

Each suite follows the same pattern: edit the config file, run the runner script, review results.

---

## Requirements

| Dependency | Purpose |
|------------|---------|
| Python 3.7+ | Runtime |
| `pyvisa` | VISA instrument communication |
| `pyvisa-py` | Pure-Python VISA backend (optional if NI-VISA installed) |
| `numpy` | Waveform calculations |
| NI-VISA or Keysight IO Libraries | USB/GPIB driver layer (Windows) |

```bash
pip install pyvisa pyvisa-py numpy
```

Verify instrument detection:

```bash
python -c "import pyvisa; print(pyvisa.ResourceManager().list_resources())"
```

---

## Running a Test

1. **Edit the config file** in the relevant suite folder (e.g. `Load_Transient/load_transient_config.json`) — set instrument addresses, rail parameters, and test limits.
2. **Run the runner script**:
   ```bash
   python Load_Transient/run_load_transient_test.py
   ```
3. Follow the interactive prompts to select rails and confirm settings.
4. Results are saved automatically to a timestamped `run_*/` directory.

Each suite's own `README.md` documents its specific config options and output format.

---

## Instrument Control Library

The `instrument_control/` module provides reusable SCPI drivers for:

- **Keithley power supplies** (2230 / 2231 / 2280 series)
- **Keithley electronic loads** (2380 series)
- **Keithley DMM** (DMM6500)
- **Keysight oscilloscopes** (InfiniiVision / InfiniiVision X-Series)
- **Generic SCPI wrapper** for any VISA-compatible instrument

All drivers handle connection management, timeouts, and resource cleanup automatically.

---

## Output

Every run creates a timestamped directory:

```
run_20250101_120000/
├── screenshots/    # PNG captures from the oscilloscope
├── reports/        # JSON (full data), CSV (tabular), TXT (human-readable summary)
└── test.log        # Full execution log
```

---

## Safety

- Confirm power supply current limits match the DUT before running.
- Do not exceed test-point current ratings.
- Ensure probe grounds are secure before enabling outputs.
- All drivers disable outputs and loads on error or test completion.

---

**Maintained by**: Test Engineering Team — Digantara Research & Technologies
