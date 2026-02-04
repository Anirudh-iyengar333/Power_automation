# PWRSTD06: Transient Response Test Automation

**⚡ AUTOMATIC INSTRUMENT DETECTION - NO MANUAL CONFIGURATION REQUIRED**

Professional automated testing for power rail transient response using load steps to verify output voltage stability, regulator control loop bandwidth, and absence of oscillation.

## ✨ New in Version 2.0: Zero-Configuration Auto-Detection

Simply plug in your instruments and run the test - **no VISA addresses needed!**
- Automatically detects Tektronix/Keysight oscilloscopes
- Automatically detects Keithley 2380 electronic loads
- Automatically detects power supplies and DMMs
- Minimal user intervention - just confirm rail connections

## 📋 Overview

The PWRSTD06 test validates power distribution network (PDN) performance by applying controlled load steps and measuring:
- **Voltage droop** during load transients
- **Recovery time** to steady-state
- **Overshoot** magnitude
- **Ringing** presence/absence

## 🏗️ Architecture

```
pwrstd06_transient_response_test.py    # Main test automation class
├── pwrstd06_config.py                 # Configuration management
├── run_pwrstd06_test.py               # Simple test runner
└── instrument_control/                # Professional instrument wrappers
    ├── keithley_load.py              # Keithley 2380 Electronic Load
    ├── keysight_oscilloscope.py      # Keysight DSOX6004A/HD304MSO  
    ├── tektronix_oscilloscope.py     # Tektronix MSO24
    └── scpi_wrapper.py               # Enhanced SCPI communication
```

## 🔧 Supported Instruments

### Your Actual Instrument Setup:
- **Keithley Power Supply** (2230/2231A Series) - Powers the rails under test
- **Keithley 2380 Electronic Load** (120W/500W) - Creates controlled load steps  
- **Keithley DMM6500** (Optional) - Additional precision measurements
- **Oscilloscope Options:**
  - **Tektronix MSO24** (2-Series MSO)
  - **Keysight DSOX6004A** (InfiniiVision 6000 X-Series)  
  - **Keysight HD304MSO** (InfiniiVision HD3 Series)

All instruments use your professional SCPI wrappers with robust error handling and timeout management.

## ⚡ Test Procedure

### Hardware Setup:
1. **Keithley Power Supply**: Configure channel to provide stable power to rail under test
2. **Keithley 2380 Load**: Connect to rail test point, configured for fast current steps (100ns)
3. **Oscilloscope**: 3-channel monitoring of load current, rail voltage, and PGood signal
4. **DMM6500** (Optional): Additional precision voltage monitoring if needed
### Automated Test Sequence:
1. **Setup Phase**
   - Connect to all instruments via VISA
   - Configure Keithley Power Supply for stable rail power
   - Configure oscilloscope (3-channel setup)
   - Configure Keithley 2380 electronic load (CC mode with fast slew rate)
   - Optional: Configure DMM6500 for additional measurements

2. **Measurement Phase** (per rail)
   - Power supply provides stable voltage to rail
   - Load applies positive load step (100mA → half rated current)
   - Capture transient waveform on oscilloscope
   - Load applies negative load step (half rated → 100mA) 
   - Capture transient waveform on oscilloscope
   - Analyze measurements vs. limits

3. **Analysis Phase**
   - Calculate droop, recovery time, overshoot from scope measurements
   - Detect ringing using RMS analysis
   - Generate pass/fail results against specifications
   - Capture screenshots and waveform data

## 📊 Standard Rail Configurations

| Rail | Test Point | Max Current | Expected V | Max Droop | Recovery | Max Overshoot |
|------|------------|-------------|------------|-----------|----------|---------------|
| 3V6  | TP? | 1600mA | 3.6V | 75mV | 150µs | 30mV |
| 3V3  | TP10 | 3000mA | 3.3V | 75mV | 150µs | 30mV |
| 2V5  | TP9 | 1500mA | 2.5V | 50mV | 150µs | 30mV |
| 1V8  | TP6 | 3000mA | 1.8V | 50mV | 150µs | 30mV |
| **Core Rails** ||||| **Tighter Limits** |
| 1V35 | TP7 | 3000mA | 1.35V | **60mV** | **100µs** | **20mV** |
| 1V_PS | TP5 | 3000mA | 1.0V | **60mV** | **100µs** | **20mV** |
| 1V_PL | TP8 | 3000mA | 1.0V | **60mV** | **100µs** | **20mV** |
| **Ethernet Rails** |||||| |
| 1V1_E0 | TP13 | 1000mA | 1.1V | 50mV | 150µs | 20mV |
| 2V5_E0 | TP14 | 1000mA | 2.5V | 50mV | 150µs | 30mV |
| 1V8_E0 | TP15 | 1000mA | 1.8V | 50mV | 150µs | 30mV |

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install pyvisa pyvisa-py numpy
# Install VISA drivers: NI-VISA (Windows) or libusb + pyvisa-py (Linux)
```

### 2. Connect Your Instruments
1. Connect oscilloscope (Tektronix or Keysight) via USB/GPIB
2. Connect Keithley 2380 electronic load via USB/GPIB
3. Power on all instruments
**That's it - no configuration files to edit!**

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

### 4. Programmatic Usage with Auto-Detection
```python
from pwrstd06_transient_response_test import PWRSTD06TransientTest

# Auto-detect instruments (no addresses needed!)
test = PWRSTD06TransientTest()

# Run test on all rails
success = test.run_test_sequence()

# Or test specific rails
success = test.run_test_sequence(rails=["3V3", "1V8", "1V35"])
```

## 📁 Output Files

The test generates comprehensive results in timestamped directories:

```
transient_test_results_20241203_143022/
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

## 🔌 Hardware Setup

### Power Supply Connections (Keithley 2230/2231A):
- Configure appropriate channel for rail under test
- Set voltage to rail nominal value (e.g., 3.3V for 3V3 rail)
- Set current limit above maximum test current with margin
- Enable output to power the rail

### Electronic Load Connections (Keithley 2380):
- **Positive**: Connect to rail test point (e.g., TP10 for 3V3)
- **Negative**: Connect to board ground
- **Sense** (if available): Direct connection to rail for accurate regulation
- Configure for constant current mode with fast slew rate (100ns steps)

### Oscilloscope Connections:
- **Ch1**: Load current monitor (Keithley 2380 analog output or 0.1Ω sense resistor)
- **Ch2**: Rail voltage (1:1 probe, **AC-coupled** for transient capture)
- **Ch3**: PGood signal (digital, DC-coupled)

### DMM6500 Connections (Optional):
- Connect for additional precision voltage monitoring if needed
- Can provide reference measurements for validation

### Critical Settings:
- **Timebase**: 1ms/div or 5ms/div
- **Voltage Scale**: 50mV/div (Ch2)
- **Trigger**: Rising edge on Ch1 (load current)
- **Coupling**: AC on Ch2, DC on Ch1/Ch3

## ⚙️ Configuration Options

### Quick Configurations:
```python
# Tektronix MSO24 + Keithley Power Supply + Keithley 2380 Load + DMM6500
config = QuickConfigs.tektronix_mso24_keithley_setup()

# Keysight DSOX6004A + Keithley Power Supply + Keithley 2380 Load + DMM6500
config = QuickConfigs.keysight_dsox6004a_keithley_setup()

# Keysight HD304MSO + Keithley Power Supply + Keithley 2380 Load + DMM6500  
config = QuickConfigs.keysight_hd304mso_keithley_setup()
```

### Test Subsets:
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

### Custom Limits:
```python
# Modify individual rail limits
rail = config.get_rail_by_name("1V35")
rail.max_droop_mv = 40.0        # Tighter droop limit
rail.max_recovery_time_us = 80.0 # Faster recovery requirement
```

## 📈 Analysis Features

### Automatic Measurements:
- **Voltage Droop**: Peak negative excursion from nominal
- **Recovery Time**: Time to return within 10% of steady-state  
- **Overshoot**: Peak positive excursion during recovery
- **Ringing Detection**: RMS-to-peak ratio analysis

### Pass/Fail Criteria:
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

## 🔍 Troubleshooting

### Common Issues:

**1. Instrument Connection Failures**
```bash
# Check VISA resources
python -c "import pyvisa; print(pyvisa.ResourceManager().list_resources())"

# Verify addresses in config
# Update timeout if instruments are slow to respond
config.instruments.oscilloscope_timeout_ms = 60000
```

**2. Trigger Issues**
```python
# Verify trigger level matches load current step
# Check Ch1 connection (load current monitor)
# Increase trigger timeout for slow load steps
```

**3. Measurement Accuracy**
```python
# Ensure proper probe calibration
# Verify AC-coupling on voltage channel (Ch2)
# Check timebase matches transient duration
config.test_params.scope_time_base_ms = 5.0  # Use 5ms/div for slower transients
```

**4. Load Step Issues**  
```python
# Verify current slew rate capability
# Check voltage protection limits
# Ensure load can sink required current
```

## 🛡️ Safety Considerations

### Before Testing:
- ✅ Verify power supply output limits
- ✅ Confirm test point current ratings  
- ✅ Check probe ground connections
- ✅ Validate load current does not exceed rail capacity
- ✅ Ensure proper thermal management for high-power tests

### During Testing:
- ⚠️ Monitor for excessive heating
- ⚠️ Watch for protection circuit activation
- ⚠️ Verify stable oscilloscope triggering
- ⚠️ Check for cross-rail interference

## 📚 Reference Documents

- **PWRSTD06 Specification**: Transient response test requirements
- **Keithley 2380 Manual**: Electronic load programming guide
- **Oscilloscope Programming Manuals**: SCPI command references
- **IEEE 488.2**: Standard digital interface specification

## 🤝 Professional Standards

This automation follows professional test development practices:
- ✅ **Type hints** throughout codebase
- ✅ **Comprehensive error handling** with custom exceptions  
- ✅ **Professional logging** with multiple levels
- ✅ **Resource management** with automatic cleanup
- ✅ **Modular design** with clear separation of concerns
- ✅ **Production-grade SCPI wrappers** with timeout management
- ✅ **Comprehensive documentation** with examples
- ✅ **Configurable test parameters** via external files

---

**Author**: Professional Instrument Control Team  
**Version**: 1.0.0  
**License**: MIT  
**Python**: >=3.7  
**Dependencies**: pyvisa, numpy, instrument_control
