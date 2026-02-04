#!/usr/bin/env python3
"""
PWRSTD06 Test Configuration File

Centralized configuration for transient response test parameters.
Modify these values to match your specific test setup and requirements.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import json
from pathlib import Path


@dataclass
class InstrumentConfig:
    """Instrument connection configuration"""
    # Oscilloscope configuration
    oscilloscope_address: str = "USB0::0x0957::0x1780::MY65220169::INSTR"  # Update with your scope
    oscilloscope_type: str = "keysight_dsox6004a"  # "keysight_dsox6004a", "keysight_hd304mso", "tektronix_mso24"
    
    # Power supply configuration (YOUR KEITHLEY POWER SUPPLY)
    power_supply_address: str = "USB0::0x05E6::0x2230::805224014806770001::INSTR"  # Update with your PSU
    
    # Electronic load configuration (YOUR KEITHLEY 2380 LOAD)  
    electronic_load_address: str = "USB0::0x05E6::0x2380::802436052807770001::INSTR"  # Update with your load
    
    # Optional DMM configuration (YOUR KEITHLEY DMM6500)
    dmm_address: str = "USB0::0x05E6::0x6500::04561287::INSTR"  # Update or set to None if not used
    
    # Timeout settings (milliseconds)
    oscilloscope_timeout_ms: int = 60000  # 60 seconds
    electronic_load_timeout_ms: int = 30000  # 30 seconds
    power_supply_timeout_ms: int = 10000  # 10 seconds
    dmm_timeout_ms: int = 30000  # 30 seconds


@dataclass 
class TestParameters:
    """Test execution parameters"""
    # Load step timing
    step_time_ns: int = 100  # Load step rise/fall time (nanoseconds)
    
    # Oscilloscope settings
    scope_time_base_ms: float = 1.0  # Time base: 1ms/div or 5ms/div
    scope_voltage_scale_mv: float = 50.0  # Voltage scale: 50mV/div for transient capture
    trigger_pre_capture_percent: float = 10.0  # Pre-trigger capture percentage
    
    # Test execution
    settle_time_s: float = 1.0  # Time to allow settling between measurements
    step_delay_s: float = 2.0  # Delay between positive and negative steps
    
    # Analysis parameters
    ringing_detection_threshold: float = 0.4  # RMS-to-peak ratio threshold for ringing detection


@dataclass
class RailLimits:
    """Power rail test limits and specifications"""
    name: str
    test_point: str
    max_current_ma: int
    expected_voltage_v: float
    max_droop_mv: float
    max_recovery_time_us: float
    max_overshoot_mv: float
    low_current_ma: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'test_point': self.test_point,
            'max_current_ma': self.max_current_ma,
            'expected_voltage_v': self.expected_voltage_v,
            'max_droop_mv': self.max_droop_mv,
            'max_recovery_time_us': self.max_recovery_time_us,
            'max_overshoot_mv': self.max_overshoot_mv,
            'low_current_ma': self.low_current_ma
        }


class PWRSTD06Config:
    """Complete PWRSTD06 test configuration"""
    
    def __init__(self):
        self.instruments = InstrumentConfig()
        self.test_params = TestParameters() 
        self.rail_limits = self._get_standard_rail_limits()
        
    def _get_standard_rail_limits(self) -> List[RailLimits]:
        """
        Define standard rail limits per PWRSTD06 specification

        Load Step Procedure: Set load to 100mA, increase to half of rated current in 100ns

        Rail Load Steps (from spec):
        - 3V6:    100mA → 800mA  (max 1600mA)
        - 3V3:    100mA → 1500mA (max 3000mA)
        - 2V5:    100mA → 750mA  (max 1500mA)
        - 1V8:    100mA → 1500mA (max 3000mA)
        - 1V35:   100mA → 1500mA (max 3000mA)
        - 1V_PS:  100mA → 1500mA (max 3000mA)
        - 1V_PL:  100mA → 1500mA (max 3000mA)
        - 1V1_E0: 100mA → 500mA  (max 1000mA)
        - 2V5_E0: 100mA → 500mA  (max 1000mA)
        - 1V8_E0: 100mA → 500mA  (max 1000mA)
        """
        return [
            # Main power rails (3V6/3V3: max droop < 50-75mV, recovery < 150µs, overshoot < 30mV)
            RailLimits(
                name="3V6",
                test_point="TP2",
                max_current_ma=1600,  # Half = 800mA load step
                expected_voltage_v=3.6,
                max_droop_mv=75.0,
                max_recovery_time_us=150.0,
                max_overshoot_mv=30.0
            ),
            RailLimits(
                name="3V3",
                test_point="TP10",
                max_current_ma=3000,  # Half = 1500mA load step
                expected_voltage_v=3.3,
                max_droop_mv=75.0,
                max_recovery_time_us=150.0,
                max_overshoot_mv=30.0
            ),

            # 2V5/1V8 rails (max droop < 50mV, recovery < 150µs, overshoot < 30mV)
            RailLimits(
                name="2V5",
                test_point="TP9",
                max_current_ma=1500,  # Half = 750mA load step
                expected_voltage_v=2.5,
                max_droop_mv=50.0,
                max_recovery_time_us=150.0,
                max_overshoot_mv=30.0
            ),
            RailLimits(
                name="1V8",
                test_point="TP6",
                max_current_ma=3000,  # Half = 1500mA load step
                expected_voltage_v=1.8,
                max_droop_mv=50.0,
                max_recovery_time_us=150.0,
                max_overshoot_mv=30.0
            ),

            # Core rails (max droop < 50-60mV, recovery < 100µs, overshoot < 20mV)
            RailLimits(
                name="1V35",
                test_point="TP7",
                max_current_ma=3000,  # Half = 1500mA load step
                expected_voltage_v=1.35,
                max_droop_mv=60.0,
                max_recovery_time_us=100.0,
                max_overshoot_mv=20.0
            ),
            RailLimits(
                name="1V_PS",
                test_point="TP5",
                max_current_ma=3000,  # Half = 1500mA load step
                expected_voltage_v=1.0,
                max_droop_mv=60.0,
                max_recovery_time_us=100.0,
                max_overshoot_mv=20.0
            ),
            RailLimits(
                name="1V_PL",
                test_point="TP8",
                max_current_ma=3000,  # Half = 1500mA load step
                expected_voltage_v=1.0,
                max_droop_mv=60.0,
                max_recovery_time_us=100.0,
                max_overshoot_mv=20.0
            ),

            # Ethernet subsystem rails (E0)
            RailLimits(
                name="1V1_E0",
                test_point="TP13",
                max_current_ma=1000,  # Half = 500mA load step
                expected_voltage_v=1.1,
                max_droop_mv=50.0,
                max_recovery_time_us=150.0,
                max_overshoot_mv=20.0
            ),
            RailLimits(
                name="2V5_E0",
                test_point="TP14",
                max_current_ma=1000,  # Half = 500mA load step
                expected_voltage_v=2.5,
                max_droop_mv=50.0,
                max_recovery_time_us=150.0,
                max_overshoot_mv=30.0
            ),
            RailLimits(
                name="1V8_E0",
                test_point="TP15",
                max_current_ma=1000,  # Half = 500mA load step
                expected_voltage_v=1.8,
                max_droop_mv=50.0,
                max_recovery_time_us=150.0,
                max_overshoot_mv=30.0
            ),
        ]
    
    def get_rail_by_name(self, rail_name: str) -> RailLimits:
        """Get rail configuration by name"""
        for rail in self.rail_limits:
            if rail.name == rail_name:
                return rail
        raise ValueError(f"Rail '{rail_name}' not found in configuration")
    
    def get_available_rail_names(self) -> List[str]:
        """Get list of all configured rail names"""
        return [rail.name for rail in self.rail_limits]
    
    def save_config(self, filepath: str) -> None:
        """Save configuration to JSON file"""
        config_data = {
            'instruments': {
                'oscilloscope_address': self.instruments.oscilloscope_address,
                'oscilloscope_type': self.instruments.oscilloscope_type,
                'power_supply_address': self.instruments.power_supply_address,
                'electronic_load_address': self.instruments.electronic_load_address,
                'dmm_address': self.instruments.dmm_address,
                'oscilloscope_timeout_ms': self.instruments.oscilloscope_timeout_ms,
                'electronic_load_timeout_ms': self.instruments.electronic_load_timeout_ms,
                'power_supply_timeout_ms': self.instruments.power_supply_timeout_ms,
                'dmm_timeout_ms': self.instruments.dmm_timeout_ms
            },
            'test_parameters': {
                'step_time_ns': self.test_params.step_time_ns,
                'scope_time_base_ms': self.test_params.scope_time_base_ms,
                'scope_voltage_scale_mv': self.test_params.scope_voltage_scale_mv,
                'trigger_pre_capture_percent': self.test_params.trigger_pre_capture_percent,
                'settle_time_s': self.test_params.settle_time_s,
                'step_delay_s': self.test_params.step_delay_s,
                'ringing_detection_threshold': self.test_params.ringing_detection_threshold
            },
            'rail_limits': [rail.to_dict() for rail in self.rail_limits]
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def load_config(self, filepath: str) -> None:
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            config_data = json.load(f)
        
        # Update instrument config
        if 'instruments' in config_data:
            instr = config_data['instruments']
            self.instruments.oscilloscope_address = instr.get('oscilloscope_address', self.instruments.oscilloscope_address)
            self.instruments.oscilloscope_type = instr.get('oscilloscope_type', self.instruments.oscilloscope_type)
            self.instruments.power_supply_address = instr.get('power_supply_address', self.instruments.power_supply_address)
            self.instruments.electronic_load_address = instr.get('electronic_load_address', self.instruments.electronic_load_address)
            self.instruments.dmm_address = instr.get('dmm_address', self.instruments.dmm_address)
            self.instruments.oscilloscope_timeout_ms = instr.get('oscilloscope_timeout_ms', self.instruments.oscilloscope_timeout_ms)
            self.instruments.electronic_load_timeout_ms = instr.get('electronic_load_timeout_ms', self.instruments.electronic_load_timeout_ms)
            self.instruments.power_supply_timeout_ms = instr.get('power_supply_timeout_ms', self.instruments.power_supply_timeout_ms)
            self.instruments.dmm_timeout_ms = instr.get('dmm_timeout_ms', self.instruments.dmm_timeout_ms)
        
        # Update test parameters
        if 'test_parameters' in config_data:
            params = config_data['test_parameters']
            self.test_params.step_time_ns = params.get('step_time_ns', self.test_params.step_time_ns)
            self.test_params.scope_time_base_ms = params.get('scope_time_base_ms', self.test_params.scope_time_base_ms)
            self.test_params.scope_voltage_scale_mv = params.get('scope_voltage_scale_mv', self.test_params.scope_voltage_scale_mv)
            self.test_params.trigger_pre_capture_percent = params.get('trigger_pre_capture_percent', self.test_params.trigger_pre_capture_percent)
            self.test_params.settle_time_s = params.get('settle_time_s', self.test_params.settle_time_s)
            self.test_params.step_delay_s = params.get('step_delay_s', self.test_params.step_delay_s)
            self.test_params.ringing_detection_threshold = params.get('ringing_detection_threshold', self.test_params.ringing_detection_threshold)
        
        # Update rail limits
        if 'rail_limits' in config_data:
            rail_data = config_data['rail_limits']
            self.rail_limits = []
            for rail_dict in rail_data:
                rail = RailLimits(
                    name=rail_dict['name'],
                    test_point=rail_dict['test_point'],
                    max_current_ma=rail_dict['max_current_ma'],
                    expected_voltage_v=rail_dict['expected_voltage_v'],
                    max_droop_mv=rail_dict['max_droop_mv'],
                    max_recovery_time_us=rail_dict['max_recovery_time_us'],
                    max_overshoot_mv=rail_dict['max_overshoot_mv'],
                    low_current_ma=rail_dict.get('low_current_ma', 100)
                )
                self.rail_limits.append(rail)


# Quick test configurations for different setups
class QuickConfigs:
    """Pre-defined configurations for common test setups"""
    
    @staticmethod
    def tektronix_mso24_keithley_setup() -> PWRSTD06Config:
        """Configuration for Tektronix MSO24 + Keithley Power Supply + Keithley 2380 Load"""
        config = PWRSTD06Config()
        config.instruments.oscilloscope_address = "USB0::0x0699::0x0522::C012345::INSTR"
        config.instruments.oscilloscope_type = "tektronix_mso24"
        config.instruments.power_supply_address = "USB0::0x05E6::0x2230::1234567::INSTR"  # Your Keithley PSU
        config.instruments.electronic_load_address = "USB0::0x05E6::0x2380::9103456::INSTR"  # Your Keithley 2380
        config.instruments.dmm_address = "USB0::0x05E6::0x6500::04561287::INSTR"  # Your Keithley DMM6500
        return config
    
    @staticmethod
    def keysight_dsox6004a_keithley_setup() -> PWRSTD06Config:
        """Configuration for Keysight DSOX6004A + Keithley Power Supply + Keithley 2380 Load"""
        config = PWRSTD06Config()
        config.instruments.oscilloscope_address = "USB0::0x0957::0x179B::MY12345678::INSTR"
        config.instruments.oscilloscope_type = "keysight_dsox6004a"
        config.instruments.power_supply_address = "USB0::0x05E6::0x2230::1234567::INSTR"  # Your Keithley PSU
        config.instruments.electronic_load_address = "USB0::0x05E6::0x2380::9103456::INSTR"  # Your Keithley 2380
        config.instruments.dmm_address = "USB0::0x05E6::0x6500::04561287::INSTR"  # Your Keithley DMM6500
        return config
    
    @staticmethod
    def keysight_hd304mso_keithley_setup() -> PWRSTD06Config:
        """Configuration for Keysight HD304MSO + Keithley Power Supply + Keithley 2380 Load"""
        config = PWRSTD06Config()
        config.instruments.oscilloscope_address = "USB0::0x0957::0x1780::MY65220169::INSTR"
        config.instruments.oscilloscope_type = "keysight_hd304mso"
        config.instruments.power_supply_address = "USB0::0x05E6::0x2230::805224014806770001::INSTR"  # Your Keithley PSU
        config.instruments.electronic_load_address = "USB0::0x05E6::0x2380::9103456::INSTR"  # Your Keithley 2380
        config.instruments.dmm_address = "USB0::0x05E6::0x6500::04561287::INSTR"  # Your Keithley DMM6500
        return config
    
    @staticmethod
    def fast_test_subset() -> List[str]:
        """Quick test subset for development/debug"""
        return ["3V3", "1V8", "1V35"]
    
    @staticmethod
    def core_rails_only() -> List[str]:
        """Test only core rails (most critical)"""
        return ["1V35", "1V_PS", "1V_PL"]
    
    @staticmethod
    def ethernet_rails_only() -> List[str]:
        """Test only Ethernet subsystem rails"""
        return ["1V1_E0", "2V5_E0", "1V8_E0"]


def main():
    """Example usage and configuration generation"""
    print("PWRSTD06 Configuration Generator")
    print("=" * 40)
    
    # Create default configuration
    config = PWRSTD06Config()
    
    # Show available rails
    print(f"Available Rails ({len(config.rail_limits)}):")
    for rail in config.rail_limits:
        print(f"  {rail.name:<10}: {rail.test_point:<6} "
              f"{rail.expected_voltage_v:>4.2f}V @ {rail.max_current_ma:>4}mA max")
    
    print(f"\nQuick Test Subsets:")
    print(f"  Fast test: {QuickConfigs.fast_test_subset()}")
    print(f"  Core rails: {QuickConfigs.core_rails_only()}")
    print(f"  Ethernet: {QuickConfigs.ethernet_rails_only()}")
    
    # Save default configuration
    config_path = "pwrstd06_config.json"
    config.save_config(config_path)
    print(f"\n✓ Default configuration saved to: {config_path}")
    
    # Example of loading and modifying configuration
    print("\nExample: Customizing configuration...")
    
    # Modify for your specific setup
    config.instruments.oscilloscope_address = "USB0::0x0699::0x0522::C054321::INSTR"  # Your scope
    config.instruments.electronic_load_address = "USB0::0x05E6::0x2380::9106543::INSTR"  # Your load
    config.test_params.scope_time_base_ms = 5.0  # Use 5ms/div instead of 1ms/div
    
    # Save customized configuration
    custom_config_path = "pwrstd06_config_custom.json"
    config.save_config(custom_config_path)
    print(f"✓ Custom configuration saved to: {custom_config_path}")
    
    print(f"\nTo use custom config in test:")
    print(f"  config = PWRSTD06Config()")
    print(f"  config.load_config('{custom_config_path}')")


if __name__ == "__main__":
    main()
