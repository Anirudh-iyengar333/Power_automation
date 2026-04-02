# PWR-STD-06: Transient Response Test Automation

**Automatic Instrument Detection - No Manual Configuration Required**

Professional automated testing for power rail transient response using load steps to verify output voltage stability, regulator control loop bandwidth, and absence of oscillation.

## Overview

The PWR-STD-06 test validates power distribution network (PDN) performance by applying controlled load steps and measuring transient response characteristics. This test suite provides comprehensive analysis of voltage regulator dynamic behavior under real-world load conditions.

### Key Measurements

- **Voltage Droop**: Peak negative excursion from nominal during load step
- **Recovery Time**: Time to return within 10% of steady-state
- **Overshoot**: Peak positive excursion during recovery phase
- **Ringing Detection**: RMS-to-peak ratio analysis for oscillation

## Features

### Zero-Configuration Auto-Detection

Simply plug in your instruments and run the test - no VISA addresses needed.

- Automatically detects Tektronix and Keysight oscilloscopes
- Automatically detects Keithley 2380 electronic loads
- Automatically detects power supplies and digital multimeters
- Minimal user intervention required - confirm rail connections only

## Architecture

```
PWR_STD_06/
├── pwrstd06_transient_response_test.py    # Main test automation class
├── pwrstd06_config.py                     # Configuration management
├── run_pwrstd06_test.py                   # Interactive test runner
├── visa_auto_detect.py                    # VISA instrument auto-detection
└── instrument_control/                    # Professional instrument wrappers
    ├── keithley_load.py                   # Keithley 2380 Electronic Load
    ├── keysight_oscilloscope.py           # Keysight DSOX6004A/HD304MSO
    ├── tektronix_oscilloscope.py          # Tektronix MSO24
    └── scpi_wrapper.py                    # Enhanced SCPI communication
```

## Supported Instruments

### Power Supply

- **Keithley 2230/2231A Series**: Powers the rails under test

### Electronic Load

- **Keithley 2380 (120W/500W)**: Creates controlled load steps with 100ns rise time

### Oscilloscopes

- **Tektronix MSO24**: 2-Series MSO, 200MHz, 4 channels
- **Keysight DSOX6004A**: InfiniiVision 6000 X-Series, 1GHz, 4 channels
- **Keysight HD304MSO**: InfiniiVision HD3 Series, 200MHz-1GHz, 14-bit resolution

### Digital Multimeter (Optional)

- **Keithley DMM6500**: Additional precision measurements

All instruments utilize production-grade SCPI wrappers with robust error handling and timeout management.

## Test Procedure

### Hardware Setup

1. **Keithley Power Supply**: Configure channel to provide stable power to rail under test
2. **Keithley 2380 Load**: Connect to rail test point, configured for fast current steps
3. **Oscilloscope**: 3-channel monitoring of load current, rail voltage, and PGood signal
4. **DMM6500 (Optional)**: Additional precision voltage monitoring

### Automated Test Sequence

**Phase 1: Setup**
- Connect to all instruments via VISA
- Configure power supply for stable rail power
- Configure oscilloscope (3-channel setup with appropriate triggering)
- Configure electronic load (CC mode with fast slew rate)
- Optional: Configure DMM6500 for additional measurements

**Phase 2: Measurement (per rail)**
- Power supply provides stable voltage to rail
- Load applies positive load step (100mA to half rated current)
- Capture transient waveform on oscilloscope
- Load applies negative load step (half rated to 100mA)
- Capture transient waveform on oscilloscope
- Analyze measurements against limits

**Phase 3: Analysis**
- Calculate droop, recovery time, overshoot from scope measurements
- Detect ringing using RMS analysis
- Generate pass/fail results against specifications
- Capture screenshots and waveform data

## Rail Configurations

### Standard Rails

| Rail | Test Point | Max Current | Expected V | Max Droop | Recovery | Max Overshoot |
|------|------------|-------------|------------|-----------|----------|---------------|
| 3V6 | TP? | 1600mA | 3.6V | 75mV | 150us | 30mV |
| 3V3 | TP10 | 3000mA | 3.3V | 75mV | 150us | 30mV |
| 2V5 | TP9 | 1500mA | 2.5V | 50mV | 150us | 30mV |
| 1V8 | TP6 | 3000mA | 1.8V | 50mV | 150us | 30mV |

### Core Rails (Tighter Limits)

| Rail | Test Point | Max Current | Expected V | Max Droop | Recovery | Max Overshoot |
|------|------------|-------------|------------|-----------|----------|---------------|
| 1V35 | TP7 | 3000mA | 1.35V | 60mV | 100us | 20mV |
| 1V_PS | TP5 | 3000mA | 1.0V | 60mV | 100us | 20mV |
| 1V_PL | TP8 | 3000mA | 1.0V | 60mV | 100us | 20mV |

### Ethernet Rails

| Rail | Test Point | Max Current | Expected V | Max Droop | Recovery | Max Overshoot |
|------|------------|-------------|------------|-----------|----------|---------------|
| 1V1_E0 | TP13 | 1000mA | 1.1V | 50mV | 150us | 20mV |
| 2V5_E0 | TP14 | 1000mA | 2.5V | 50mV | 150us | 30mV |
| 1V8_E0 | TP15 | 1000mA | 1.8V | 50mV | 150us | 30mV |

## Quick Start

### 1. Install Dependencies

```bash
pip install pyvisa pyvisa-py numpy
```

For Windows, install NI-VISA drivers. For Linux, use pyvisa-py with libusb.

### 2. Connect Instruments

1. Connect oscilloscope (Tektronix or Keysight) via USB/GPIB
2. Connect Keithley 2380 electronic load via USB/GPIB
3. Power on all instruments

No configuration files to edit - the system auto-detects instruments.

### 3. Run Test with Auto-Detection

```bash
# Auto-detect all instruments and test all rails
python run_pwrstd06_test.py

# List detected instruments
python run_pwrstd06_test.py --list

# Test specific rails only
python run_pwrstd06_test.py --rails 3V6,3V3,1V8

# Override auto-detection if needed (optional)
python run_pwrstd06_test.py --scope USB0::... --load USB0::...
```

### 4. Programmatic Usage

```python
from pwrstd06_transient_response_test import PWRSTD06TransientTest

# Auto-detect instruments (no addresses needed)
test = PWRSTD06TransientTest()

# Run test on all rails
success = test.run_test_sequence()

# Or test specific rails
success = test.run_test_sequence(rails=["3V3", "1V8", "1V35"])
```

## Output Files

Test results are generated in timestamped directories:

```
transient_test_results_YYYYMMDD_HHMMSS/
├── screenshots/                    # Oscilloscope captures
│   ├── 3V3_POSITIVE_step_*.png
│   ├── 3V3_NEGATIVE_step_*.png
│   └── ...
├── waveform_data/                 # Raw waveform data
│   └── (binary waveform files)
└── reports/                       # Analysis reports
    ├── pwrstd06_transient_measurements.csv    # All measurements
    ├── pwrstd06_transient_complete.json       # Complete test data
    └── pwrstd06_transient_summary.txt         # Human-readable summary
```

## Hardware Setup Details

### Power Supply Connections (Keithley 2230/2231A)

- Configure appropriate channel for rail under test
- Set voltage to rail nominal value (e.g., 3.3V for 3V3 rail)
- Set current limit above maximum test current with margin
- Enable output to power the rail

### Electronic Load Connections (Keithley 2380)

- **Positive**: Connect to rail test point (e.g., TP10 for 3V3)
- **Negative**: Connect to board ground
- **Sense** (if available): Direct connection to rail for accurate regulation
- Configure for constant current mode with fast slew rate (100ns steps)

### Oscilloscope Connections

- **Ch1**: Load current monitor (Keithley 2380 analog output or 0.1 ohm sense resistor)
- **Ch2**: Rail voltage (1:1 probe, AC-coupled for transient capture)
- **Ch3**: PGood signal (digital, DC-coupled)

### DMM6500 Connections (Optional)

- Connect for additional precision voltage monitoring
- Provides reference measurements for validation

### Critical Oscilloscope Settings

| Parameter | Setting |
|-----------|---------|
| Timebase | 1ms/div or 5ms/div |
| Ch2 Voltage Scale | 50mV/div |
| Trigger Source | Ch1 (load current) |
| Trigger Edge | Rising |
| Ch1 Coupling | DC |
| Ch2 Coupling | AC |
| Ch3 Coupling | DC |

## Configuration Options

### Quick Configurations

```python
# Tektronix MSO24 + Keithley Power Supply + Keithley 2380 Load + DMM6500
config = QuickConfigs.tektronix_mso24_keithley_setup()

# Keysight DSOX6004A + Keithley Power Supply + Keithley 2380 Load + DMM6500
config = QuickConfigs.keysight_dsox6004a_keithley_setup()

# Keysight HD304MSO + Keithley Power Supply + Keithley 2380 Load + DMM6500
config = QuickConfigs.keysight_hd304mso_keithley_setup()
```

### Test Subsets

```python
# Fast development testing
selected_rails = QuickConfigs.fast_test_subset()        # ["3V3", "1V8", "1V35"]

# Critical rails only
selected_rails = QuickConfigs.core_rails_only()         # ["1V35", "1V_PS", "1V_PL"]

# Ethernet subsystem
selected_rails = QuickConfigs.ethernet_rails_only()     # ["1V1_E0", "2V5_E0", "1V8_E0"]

# All rails
selected_rails = None
```

### Custom Limits

```python
# Modify individual rail limits
rail = config.get_rail_by_name("1V35")
rail.max_droop_mv = 40.0         # Tighter droop limit
rail.max_recovery_time_us = 80.0 # Faster recovery requirement
```

## Analysis Features

### Automatic Measurements

- **Voltage Droop**: Peak negative excursion from nominal
- **Recovery Time**: Time to return within 10% of steady-state
- **Overshoot**: Peak positive excursion during recovery
- **Ringing Detection**: RMS-to-peak ratio analysis

### Pass/Fail Criteria

```python
@dataclass
class TransientMeasurement:
    def meets_limits(self, rail_config: RailConfiguration) -> TestResult:
        return TestResult.PASS if (
            self.droop_voltage_mv <= rail_config.max_droop_mv and
            self.recovery_time_us <= rail_config.max_recovery_time_us and
            self.overshoot_voltage_mv <= rail_config.max_overshoot_mv and
            not self.has_ringing
        ) else TestResult.FAIL
```

## Troubleshooting

### Instrument Connection Failures

```bash
# Check VISA resources
python -c "import pyvisa; print(pyvisa.ResourceManager().list_resources())"
```

If instruments are not listed:
- Verify USB/GPIB connections
- Check instrument power status
- Reinstall NI-VISA drivers
- Adjust timeout in configuration:
  ```python
  config.instruments.oscilloscope_timeout_ms = 60000
  ```

### Trigger Issues

- Verify trigger level matches load current step
- Check Ch1 connection (load current monitor)
- Increase trigger timeout for slow load steps

### Measurement Accuracy

- Ensure proper probe calibration
- Verify AC-coupling on voltage channel (Ch2)
- Check timebase matches transient duration:
  ```python
  config.test_params.scope_time_base_ms = 5.0  # Use 5ms/div for slower transients
  ```

### Load Step Issues

- Verify current slew rate capability
- Check voltage protection limits
- Ensure load can sink required current

## Safety Considerations

### Before Testing

- Verify power supply output limits
- Confirm test point current ratings
- Check probe ground connections
- Validate load current does not exceed rail capacity
- Ensure proper thermal management for high-power tests

### During Testing

- Monitor for excessive heating
- Watch for protection circuit activation
- Verify stable oscilloscope triggering
- Check for cross-rail interference

## Reference Documents

- **PWR-STD-06 Specification**: Transient response test requirements
- **Keithley 2380 Manual**: Electronic load programming guide
- **Oscilloscope Programming Manuals**: SCPI command references
- **IEEE 488.2**: Standard digital interface specification

## Development Standards

This automation follows professional test development practices:

- Type hints throughout codebase
- Comprehensive error handling with custom exceptions
- Professional logging with multiple levels
- Resource management with automatic cleanup
- Modular design with clear separation of concerns
- Production-grade SCPI wrappers with timeout management
- Comprehensive documentation with examples
- Configurable test parameters via external files

---

**Author**: Test Engineering Team
**Version**: 1.0.0
**License**: MIT
**Python**: 3.7 or higher
**Dependencies**: pyvisa, numpy, instrument_control
