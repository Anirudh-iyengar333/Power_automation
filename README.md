# Digantara Power Rail Test Automation Framework

A comprehensive, production-grade test automation framework for power rail verification and transient response analysis. This framework provides automated testing capabilities for validating power distribution networks (PDN) on embedded systems, with support for multiple instrument manufacturers and configurable test parameters.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Test Suites](#test-suites)
  - [PWR-STD-04: Steady-State Rail Verification](#pwr-std-04-steady-state-rail-verification)
  - [PWR-STD-06: Transient Response Testing](#pwr-std-06-transient-response-testing)
- [Instrument Control Library](#instrument-control-library)
- [Supported Hardware](#supported-hardware)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output and Reporting](#output-and-reporting)
- [Safety Considerations](#safety-considerations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This test automation framework was developed to streamline power rail verification testing for embedded systems. It provides a unified interface for controlling laboratory instruments, executing standardized test sequences, and generating comprehensive test reports.

The framework addresses common challenges in power rail testing:

- **Instrument Abstraction**: Unified API across different oscilloscope and power supply manufacturers
- **Automated Test Execution**: Reduces manual intervention and human error
- **Standardized Reporting**: Consistent output formats for documentation and traceability
- **Configurable Test Parameters**: Flexible configuration for different board revisions and test requirements

## Features

### Core Capabilities

- **Automatic Instrument Detection**: VISA-based auto-discovery of connected instruments eliminates manual address configuration
- **Multi-Vendor Support**: Compatible with Tektronix, Keysight, and Keithley instrumentation
- **Interactive Rail Selection**: Console-based interface for selecting specific rails to test
- **Comprehensive Measurements**: Voltage accuracy, ripple analysis, transient response, and stability metrics
- **Professional Documentation**: Automated generation of test reports in JSON, CSV, and human-readable formats

### Technical Features

- Type hints throughout the codebase for improved maintainability
- Comprehensive error handling with custom exception classes
- Professional logging with configurable verbosity levels
- Resource management with automatic cleanup on test completion or failure
- Modular architecture with clear separation of concerns
- Production-grade SCPI wrappers with timeout management

## System Requirements

### Software Requirements

| Component | Minimum Version | Recommended |
|-----------|-----------------|-------------|
| Python | 3.7 | 3.9+ |
| pyvisa | 1.11.0 | Latest |
| pyvisa-py | 0.5.0 | Latest |
| numpy | 1.19.0 | Latest |

### Hardware Requirements

- Windows 10/11 with NI-VISA drivers installed
- USB or GPIB connectivity to laboratory instruments
- Sufficient USB ports for instrument connections (typically 3-4 ports)

### VISA Backend

The framework requires a VISA backend for instrument communication:

- **Windows**: NI-VISA (recommended) or Keysight IO Libraries Suite
- **Linux**: pyvisa-py with libusb (native Python implementation)

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Digantara_Automation
```

### Step 2: Create Virtual Environment (Recommended)

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS
```

### Step 3: Install Dependencies

```bash
pip install pyvisa pyvisa-py numpy
```

### Step 4: Install VISA Drivers

For Windows systems, install NI-VISA from the National Instruments website. This provides the necessary drivers for USB and GPIB instrument communication.

### Step 5: Verify Installation

```bash
python -c "import pyvisa; rm = pyvisa.ResourceManager(); print(rm.list_resources())"
```

This command should list all connected VISA instruments.

## Project Structure

```
Digantara_Automation/
├── instrument_control/              # Instrument driver library
│   ├── __init__.py                 # Module initialization with factory functions
│   ├── scpi_wrapper.py             # Enhanced SCPI communication wrapper
│   ├── keithley_power_supply.py    # Keithley PSU control (2230/2231/2280)
│   ├── keithley_load.py            # Keithley 2380 electronic load control
│   ├── keithley_dmm.py             # Keithley DMM6500 multimeter control
│   └── keysight_oscilloscope.py    # Keysight oscilloscope drivers
│
├── PWR_STD_04/                     # Steady-state rail verification tests
│   ├── pwr_std_04_automation.py    # Main test automation class
│   ├── pwr_std_04_config.py        # Configuration management
│   ├── pwr_std_04_documentation.py # Report generation (Word output)
│   ├── pwr_std_04_demo.py          # Example implementation
│   └── README.md                   # Test-specific documentation
│
├── PWR_STD_06/                     # Transient response tests
│   ├── pwrstd06_transient_response_test.py  # Main test class
│   ├── pwrstd06_config.py          # Configuration management
│   ├── run_pwrstd06_test.py        # Test runner with interactive selection
│   ├── visa_auto_detect.py         # VISA instrument auto-detection
│   └── README.md                   # Test-specific documentation
│
├── run_YYYYMMDD_HHMMSS/            # Test result directories (timestamped)
│   ├── reports/                    # Generated test reports
│   ├── screenshots/                # Oscilloscope captures
│   └── calculations/               # Detailed calculation data
│
└── README.md                       # This file
```

## Test Suites

### PWR-STD-04: Steady-State Rail Verification

The PWR-STD-04 test suite validates power rail performance under steady-state conditions. This test measures:

- **DC Voltage Accuracy**: Verification against nominal voltage specifications
- **Load Regulation**: Voltage stability across varying load conditions
- **Ripple and Noise**: AC component analysis on DC rails
- **Long-Term Stability**: Voltage drift over extended measurement periods

#### Key Parameters

| Parameter | Description | Typical Value |
|-----------|-------------|---------------|
| Stabilization Time | Time to wait before measurements | 60 seconds |
| Measurements per Rail | Number of samples per rail | 10 |
| Voltage Tolerance | Acceptable deviation from nominal | +/- 3% |

#### Running PWR-STD-04 Tests

```bash
cd PWR_STD_04
python pwr_std_04_automation.py
```

Refer to [PWR_STD_04/README.md](PWR_STD_04/README.md) for detailed documentation.

### PWR-STD-06: Transient Response Testing

The PWR-STD-06 test suite validates power rail performance under dynamic load conditions. This test applies controlled load steps and measures:

- **Voltage Droop**: Peak negative excursion during load step
- **Recovery Time**: Time to return within 10% of steady-state
- **Overshoot**: Peak positive excursion during recovery
- **Ringing Detection**: RMS-to-peak ratio analysis for oscillation

#### Rail Configurations

| Rail | Test Point | Voltage | Max Current | Droop Limit | Recovery Time | Overshoot Limit |
|------|------------|---------|-------------|-------------|---------------|-----------------|
| 3V6 | TP? | 3.6V | 1600mA | 75mV | 150us | 30mV |
| 3V3 | TP10 | 3.3V | 3000mA | 75mV | 150us | 30mV |
| 2V5 | TP9 | 2.5V | 1500mA | 50mV | 150us | 30mV |
| 1V8 | TP6 | 1.8V | 3000mA | 50mV | 150us | 30mV |
| 1V35 | TP7 | 1.35V | 3000mA | 60mV | 100us | 20mV |
| 1V_PS | TP5 | 1.0V | 3000mA | 60mV | 100us | 20mV |
| 1V_PL | TP8 | 1.0V | 3000mA | 60mV | 100us | 20mV |
| 1V1_E0 | TP13 | 1.1V | 1000mA | 50mV | 150us | 20mV |
| 2V5_E0 | TP14 | 2.5V | 1000mA | 50mV | 150us | 30mV |
| 1V8_E0 | TP15 | 1.8V | 1000mA | 50mV | 150us | 30mV |

#### Running PWR-STD-06 Tests

```bash
cd PWR_STD_06

# Auto-detect instruments and test all rails
python run_pwrstd06_test.py

# List detected instruments without running tests
python run_pwrstd06_test.py --list

# Test specific rails only
python run_pwrstd06_test.py --rails 3V3,1V8,1V35
```

Refer to [PWR_STD_06/README.md](PWR_STD_06/README.md) for detailed documentation.

## Instrument Control Library

The `instrument_control` module provides professional-grade drivers for laboratory instruments. All drivers implement consistent interfaces with:

- Automatic connection management
- Comprehensive error handling
- Configurable timeouts
- Query/command retry logic
- Resource cleanup on exit

### Available Drivers

| Module | Instruments Supported |
|--------|----------------------|
| `keithley_power_supply.py` | Keithley 2230, 2231A, 2280 Series |
| `keithley_load.py` | Keithley 2380 Electronic Load (120W/500W) |
| `keithley_dmm.py` | Keithley DMM6500 Digital Multimeter |
| `keysight_oscilloscope.py` | DSOX6004A, HD304MSO, InfiniiVision Series |
| `scpi_wrapper.py` | Generic SCPI wrapper for custom instruments |

### Usage Example

```python
from instrument_control import KeysightOscilloscope, KeithleyPowerSupply

# Initialize instruments
scope = KeysightOscilloscope("USB0::0x2A8D::0x1764::MY12345678::INSTR")
psu = KeithleyPowerSupply("USB0::0x05E6::0x2230::12345678::INSTR")

# Configure and measure
scope.configure_channel(1, scale_v_div=0.1, coupling="DC")
psu.set_voltage(channel=1, voltage=3.3)
psu.enable_output(channel=1)

# Read measurements
voltage = scope.measure_voltage(channel=1)
```

## Supported Hardware

### Power Supplies

| Model | Channels | Voltage Range | Current Range |
|-------|----------|---------------|---------------|
| Keithley 2230-30-1 | 3 | 0-30V | 0-1A |
| Keithley 2231A-30-3 | 3 | 0-30V | 0-3A |
| Keithley 2280S-32-6 | 1 | 0-32V | 0-6A |

### Electronic Loads

| Model | Power Rating | Current Range | Slew Rate |
|-------|--------------|---------------|-----------|
| Keithley 2380-120-60 | 120W | 0-60A | 2.5A/us |
| Keithley 2380-500-15 | 500W | 0-15A | 2.5A/us |

### Oscilloscopes

| Model | Bandwidth | Channels | Sample Rate | Memory |
|-------|-----------|----------|-------------|--------|
| Tektronix MSO24 | 200MHz | 4 | 2.5GS/s | 62.5Mpts |
| Keysight DSOX6004A | 1GHz | 4 | 20GS/s | 16Mpts |
| Keysight HD304MSO | 200MHz-1GHz | 4+16D | 2.5GS/s | 100Mpts |

### Digital Multimeters

| Model | DC Accuracy | Resolution |
|-------|-------------|------------|
| Keithley DMM6500 | 0.0025% | 6.5 digits |

## Configuration

### Test Configuration

Each test suite includes a configuration module that defines:

- Instrument VISA addresses
- Timeout settings
- Test parameters (timing, thresholds, limits)
- Rail specifications

Configuration is managed through Python dataclasses for type safety and IDE support.

### Example Configuration

```python
from dataclasses import dataclass

@dataclass
class TestConfiguration:
    # Instrument addresses
    oscilloscope_address: str = "USB0::0x2A8D::0x1764::MY12345678::INSTR"
    power_supply_address: str = "USB0::0x05E6::0x2230::12345678::INSTR"
    electronic_load_address: str = "USB0::0x05E6::0x2380::12345678::INSTR"

    # Timeout settings (milliseconds)
    instrument_timeout_ms: int = 30000

    # Test parameters
    stabilization_time_s: float = 60.0
    measurements_per_rail: int = 10
```

### Rail Configuration

Individual rails can be configured with specific test limits:

```python
@dataclass
class RailConfiguration:
    name: str
    test_point: str
    nominal_voltage_v: float
    max_current_ma: float
    max_droop_mv: float
    max_recovery_time_us: float
    max_overshoot_mv: float
```

## Usage

### Basic Test Execution

```python
from PWR_STD_06.pwrstd06_transient_response_test import PWRSTD06TransientTest

# Initialize with auto-detection
test = PWRSTD06TransientTest()

# Run all rails
success = test.run_test_sequence()

# Run specific rails
success = test.run_test_sequence(rails=["3V3", "1V8", "1V35"])
```

### Command Line Execution

```bash
# PWR-STD-06 transient testing
python PWR_STD_06/run_pwrstd06_test.py --rails 3V3,1V8

# PWR-STD-04 steady-state verification
python PWR_STD_04/pwr_std_04_automation.py
```

### Programmatic Configuration

```python
from PWR_STD_06.pwrstd06_config import QuickConfigs

# Use predefined configurations
config = QuickConfigs.tektronix_mso24_keithley_setup()

# Select rail subsets
rails = QuickConfigs.core_rails_only()  # ["1V35", "1V_PS", "1V_PL"]
rails = QuickConfigs.ethernet_rails_only()  # ["1V1_E0", "2V5_E0", "1V8_E0"]
rails = QuickConfigs.fast_test_subset()  # ["3V3", "1V8", "1V35"]
```

## Output and Reporting

### Directory Structure

Test results are organized in timestamped directories:

```
run_YYYYMMDD_HHMMSS/
├── reports/
│   ├── pwrstd06_results_TIMESTAMP.json    # Complete structured data
│   ├── pwrstd06_results_TIMESTAMP.csv     # Spreadsheet-compatible format
│   └── pwrstd06_summary_TIMESTAMP.txt     # Human-readable summary
├── screenshots/
│   ├── 3V3_POSITIVE_step_capture.png      # Oscilloscope captures
│   ├── 3V3_NEGATIVE_step_capture.png
│   └── ...
├── calculations/
│   └── README.txt                         # Calculation methodology
└── pwrstd06_test.log                      # Execution log
```

### Report Contents

**JSON Report** includes:
- Test metadata (timestamp, configuration, software version)
- Per-rail measurement results
- Pass/fail status for each test criterion
- Detailed calculation traces
- Screenshot file references

**CSV Report** provides:
- Tabular format for spreadsheet analysis
- One row per rail measurement
- Columns for all measured parameters

**Summary Report** contains:
- Executive summary with overall pass/fail
- Rail-by-rail results table
- Failed tests highlighted
- Test configuration summary

## Safety Considerations

### Pre-Test Verification

Before executing tests, verify the following:

1. Power supply output limits are configured correctly
2. Test point current ratings are not exceeded
3. Probe ground connections are secure
4. Electronic load current limits are appropriate
5. Thermal management is adequate for high-power tests

### During Testing

Monitor the following during test execution:

- Component and board temperature
- Protection circuit activation
- Oscilloscope trigger stability
- Cross-rail interference

### Emergency Procedures

All instrument drivers implement emergency shutdown procedures:

```python
# Emergency shutdown
test.emergency_stop()  # Disables all outputs and loads
```

## Troubleshooting

### Instrument Connection Issues

**Problem**: Instruments not detected

**Solution**:
1. Verify USB/GPIB connections
2. Check NI-VISA driver installation
3. Run VISA resource enumeration:
   ```bash
   python -c "import pyvisa; print(pyvisa.ResourceManager().list_resources())"
   ```
4. Verify instrument power and USB drivers

### Timeout Errors

**Problem**: Communication timeouts during measurements

**Solution**:
1. Increase timeout values in configuration
2. Check for USB hub issues (use direct connection)
3. Reduce instrument query rate
4. Verify instrument is not in local mode

### Trigger Issues

**Problem**: Oscilloscope not capturing transients

**Solution**:
1. Verify trigger source channel connection
2. Adjust trigger level to match load step amplitude
3. Check channel coupling settings (AC vs DC)
4. Increase trigger timeout

### Measurement Accuracy

**Problem**: Measurements outside expected range

**Solution**:
1. Calibrate oscilloscope probes
2. Verify AC coupling on voltage channel
3. Check timebase matches transient duration
4. Validate load current step amplitude

## Contributing

### Code Standards

- Follow PEP 8 style guidelines
- Include type hints for all function parameters and return values
- Document public functions with docstrings
- Implement proper error handling with custom exceptions
- Write unit tests for new functionality

### Pull Request Process

1. Create feature branch from main
2. Implement changes with appropriate tests
3. Update documentation as needed
4. Submit pull request with detailed description

## License

This project is licensed under the MIT License.

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2024 | Initial release with PWR-STD-04 and PWR-STD-06 test suites |

## Contact

For questions or support, please contact the Test Engineering team.

---

**Maintained by**: Test Engineering Team
**Framework Version**: 1.0.0
**Python Compatibility**: 3.7+
