#!/usr/bin/env python3
"""
PWR-STD-04 Configuration File

Professional configuration management for PWR-STD-04 automation suite.
Customize these settings for your specific lab setup and requirements.

Author: Senior Test Automation Engineer
Version: 1.0.0 - Production Grade
Date: 2024-12-03
"""

from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class LabConfiguration:
    """Laboratory-specific configuration parameters"""
    
    # ============================================================================
    # INSTRUMENT ADDRESSES - UPDATE FOR YOUR LAB SETUP
    # ============================================================================
    
    # Keithley DMM6500/7510 Digital Multimeter
    DMM_ADDRESS: str = "GPIB::22::INSTR"  # Update with your DMM VISA address
    
    # Keithley Power Supply (2230/2231/2280 series)
    PSU_ADDRESS: str = "GPIB::5::INSTR"   # Update with your PSU VISA address
    
    # Optional Oscilloscope (for ripple analysis)
    SCOPE_ADDRESS: str = "USB0::0x0699::0x0522::C012345::INSTR"  # Tektronix MSO24
    
    # ============================================================================
    # TEST CONFIGURATION PARAMETERS
    # ============================================================================
    
    # Power Supply Settings
    PSU_VOLTAGE: float = 5.0              # Input voltage (V)
    PSU_CURRENT_LIMIT: float = 3.0        # Current limit (A)
    
    # Test Timing
    STABILIZATION_TIME: int = 60          # Stabilization time after power-on (seconds)
    MEASUREMENT_SAMPLES: int = 10         # Number of measurements per rail
    MEASUREMENT_INTERVAL: float = 0.5     # Time between measurements (seconds)
    
    # Safety Limits
    SAFETY_CURRENT_LIMIT: float = 5.0     # Emergency shutdown current threshold (A)
    MAX_VOLTAGE_DEVIATION: float = 10.0   # Maximum allowed voltage deviation (%)
    
    # ============================================================================
    # MEASUREMENT SETTINGS
    # ============================================================================
    
    # DMM Configuration
    DMM_NPLC: float = 1.0                 # Power line cycles (higher = more accurate, slower)
    DMM_AUTO_ZERO: bool = True            # Enable auto-zero for maximum accuracy
    DMM_VOLTAGE_RANGE: float = 10.0       # Voltage range (V)
    
    # Statistical Analysis
    ENABLE_STATISTICS: bool = True        # Calculate std dev, min/max for each rail
    OUTLIER_DETECTION: bool = True        # Remove outliers from measurements
    OUTLIER_THRESHOLD: float = 3.0        # Standard deviations for outlier detection
    
    # ============================================================================
    # ADVANCED FEATURES
    # ============================================================================
    
    # Ripple Analysis (requires oscilloscope)
    ENABLE_RIPPLE_ANALYSIS: bool = False  # Enable AC ripple measurements
    RIPPLE_BANDWIDTH: float = 20e6        # Measurement bandwidth (Hz)
    RIPPLE_COUPLING: str = "AC"           # AC or DC coupling
    
    # Temperature Monitoring
    ENABLE_TEMPERATURE_MONITORING: bool = False  # Monitor board temperature
    TEMPERATURE_SENSOR_ADDRESS: str = ""  # Temperature sensor VISA address
    MAX_TEMPERATURE: float = 85.0         # Maximum safe temperature (°C)
    
    # ============================================================================
    # OUTPUT AND DOCUMENTATION
    # ============================================================================
    
    # File Paths
    OUTPUT_DIRECTORY: str = "./pwr_std_04_results"
    LOG_LEVEL: str = "INFO"               # DEBUG, INFO, WARNING, ERROR
    
    # Documentation Generation
    GENERATE_WORD_REPORT: bool = True     # Generate professional Word document
    GENERATE_PDF_REPORT: bool = False     # Generate PDF report (requires LibreOffice)
    GENERATE_CHARTS: bool = True          # Include measurement charts in reports
    
    # Report Customization
    COMPANY_NAME: str = "Your Company Name"
    ENGINEER_NAME: str = "Test Engineer"
    PROJECT_NAME: str = "CPU Board Validation"
    BOARD_REVISION: str = "Rev 1.0"
    
    # ============================================================================
    # RAIL-SPECIFIC OVERRIDES (Advanced Users)
    # ============================================================================
    
    # Custom rail specifications (overrides defaults if needed)
    CUSTOM_RAIL_SPECS: Dict[str, Any] = {
        # Example: Override 3V3 rail tolerance
        # '3V3': {
        #     'min_voltage': 3.100,  # Tighter tolerance
        #     'max_voltage': 3.500,
        #     'max_current_ma': 2000  # Higher current capability
        # }
    }
    
    # Measurement overrides per rail
    RAIL_MEASUREMENT_OVERRIDES: Dict[str, Any] = {
        # Example: Take more samples for critical rails
        # '1V35': {
        #     'measurement_samples': 20,
        #     'measurement_interval': 0.2
        # }
    }


# ============================================================================
# PREDEFINED CONFIGURATIONS FOR COMMON SETUPS
# ============================================================================

# High-Precision Configuration (slower but more accurate)
HIGH_PRECISION_CONFIG = LabConfiguration(
    MEASUREMENT_SAMPLES=20,
    MEASUREMENT_INTERVAL=1.0,
    DMM_NPLC=10.0,  # 10 power line cycles for maximum accuracy
    STABILIZATION_TIME=120,
    ENABLE_STATISTICS=True,
    OUTLIER_DETECTION=True
)

# Fast Testing Configuration (quicker measurements)
FAST_TEST_CONFIG = LabConfiguration(
    MEASUREMENT_SAMPLES=5,
    MEASUREMENT_INTERVAL=0.2,
    DMM_NPLC=0.1,   # Fast measurements
    STABILIZATION_TIME=30,
    ENABLE_STATISTICS=False
)

# Production Testing Configuration (balanced speed and accuracy)
PRODUCTION_CONFIG = LabConfiguration(
    MEASUREMENT_SAMPLES=10,
    MEASUREMENT_INTERVAL=0.5,
    DMM_NPLC=1.0,
    STABILIZATION_TIME=60,
    ENABLE_STATISTICS=True,
    GENERATE_WORD_REPORT=True,
    ENABLE_RIPPLE_ANALYSIS=False  # Disable for faster testing
)

# Engineering Debug Configuration (maximum information)
DEBUG_CONFIG = LabConfiguration(
    MEASUREMENT_SAMPLES=50,
    MEASUREMENT_INTERVAL=0.1,
    DMM_NPLC=5.0,
    STABILIZATION_TIME=180,
    ENABLE_STATISTICS=True,
    ENABLE_RIPPLE_ANALYSIS=True,
    ENABLE_TEMPERATURE_MONITORING=True,
    LOG_LEVEL="DEBUG"
)


def get_lab_config(config_name: str = "default") -> LabConfiguration:
    """
    Get laboratory configuration by name
    
    Args:
        config_name: Configuration name ("default", "high_precision", "fast", "production", "debug")
        
    Returns:
        LabConfiguration object
    """
    configs = {
        "default": LabConfiguration(),
        "high_precision": HIGH_PRECISION_CONFIG,
        "fast": FAST_TEST_CONFIG,
        "production": PRODUCTION_CONFIG,
        "debug": DEBUG_CONFIG
    }
    
    if config_name not in configs:
        raise ValueError(f"Unknown configuration: {config_name}. Available: {list(configs.keys())}")
    
    return configs[config_name]


def validate_configuration(config: LabConfiguration) -> bool:
    """
    Validate configuration parameters for safety and feasibility
    
    Args:
        config: Configuration to validate
        
    Returns:
        bool: True if configuration is valid
    """
    errors = []
    
    # Safety checks
    if config.PSU_CURRENT_LIMIT > 10.0:
        errors.append("PSU current limit too high (>10A) - safety risk")
    
    if config.PSU_VOLTAGE > 15.0 or config.PSU_VOLTAGE < 3.0:
        errors.append("PSU voltage out of safe range (3V-15V)")
    
    if config.SAFETY_CURRENT_LIMIT > 20.0:
        errors.append("Safety current limit too high (>20A)")
    
    # Measurement parameter checks
    if config.MEASUREMENT_SAMPLES < 1:
        errors.append("Measurement samples must be >= 1")
    
    if config.MEASUREMENT_INTERVAL < 0.1:
        errors.append("Measurement interval too fast (<0.1s)")
    
    if config.DMM_NPLC < 0.01 or config.DMM_NPLC > 100:
        errors.append("DMM NPLC out of range (0.01-100)")
    
    # Print errors if any
    if errors:
        print("Configuration Validation Errors:")
        for error in errors:
            print(f"  ERROR: {error}")
        return False
    
    print("Configuration validation passed")
    return True


if __name__ == "__main__":
    """Test configuration validation"""
    
    print("PWR-STD-04 Configuration Validation")
    print("=" * 50)
    
    # Test all predefined configurations
    for name in ["default", "high_precision", "fast", "production", "debug"]:
        print(f"\nValidating '{name}' configuration:")
        config = get_lab_config(name)
        validate_configuration(config)
    
    print(f"\nConfiguration files ready for use!")
    print(f"Update instrument addresses in LabConfiguration class for your lab setup.")
