#!/usr/bin/env python3
# This line tells the operating system to run this file using Python 3; it is required for direct execution on Linux/macOS and is harmless on Windows
"""
Load Transient Test Configuration File

Centralized configuration for transient response test parameters.
Modify these values to match your specific test setup and requirements.
"""

# Load the 'dataclass' decorator from Python's built-in dataclasses library; this allows data-holding classes to be written concisely without writing separate __init__ setup code
from dataclasses import dataclass
# Load type-hint helpers (List, Dict, Any) from the 'typing' library; these labels make the code self-documenting and help catch programming errors early
from typing import List, Dict, Any
# Load the 'json' library, which provides functions for reading and writing configuration data in the standard JSON file format; this enables saving and loading test settings between sessions
import json
# Load the 'Path' class from the built-in 'pathlib' library; this provides a safe, platform-independent way to build and manipulate file paths on both Windows and Linux
from pathlib import Path





# Apply the @dataclass decorator so Python automatically generates the __init__ method; the engineer only needs to declare field names and their defaults
@dataclass
# Define a container class that holds all connection settings for the physical test instruments; one instance stores the addresses and timeout values for every instrument in the test bench
class InstrumentConfig:
    # Docstring summarising what information this class stores
    """Instrument connection configuration"""
    # Oscilloscope configuration
    # Store the USB VISA address string used to open a communication channel to the oscilloscope; replace the placeholder value with the address shown in the VISA instrument manager on the test PC
    oscilloscope_address: str = "USB0::0x0957::0x1780::MY65220169::INSTR"  # Update with your scope
    # Store a short name identifying which oscilloscope model is in use; this controls which driver functions are called during the test (supported values: "keysight_dsox6004a", "keysight_hd304mso", "tektronix_mso24")
    oscilloscope_type: str = "keysight_dsox6004a"  # "keysight_dsox6004a", "keysight_hd304mso", "tektronix_mso24"
    
    # Power supply configuration (YOUR KEITHLEY POWER SUPPLY)
    # Store the USB VISA address string used to open a communication channel to the Keithley DC power supply that powers the device under test; replace with the address shown in the VISA instrument manager
    power_supply_address: str = "USB0::0x05E6::0x2230::805224014806770001::INSTR"  # Update with your PSU
    
    # Electronic load configuration (YOUR KEITHLEY 2380 LOAD)
    # Store the USB VISA address string used to open a communication channel to the Keithley 2380 programmable electronic load; replace with the address shown in the VISA instrument manager
    electronic_load_address: str = "USB0::0x05E6::0x2380::802436052807770001::INSTR"  # Update with your load
    
    # Optional DMM configuration (YOUR KEITHLEY DMM6500)
    # Store the USB VISA address string for the optional Keithley DMM6500 digital multimeter; set this to None if no multimeter is being used in this test bench
    dmm_address: str = "USB0::0x05E6::0x6500::04561287::INSTR"  # Update or set to None if not used
    
    # Timeout settings (milliseconds)
    # Set the maximum time (in milliseconds) the program will wait for the oscilloscope to respond to a command before giving up; 60 seconds is long to allow for waveform captures and data transfers
    oscilloscope_timeout_ms: int = 60000  # 60 seconds
    # Set the maximum time (in milliseconds) the program will wait for the electronic load to respond to a command before giving up
    electronic_load_timeout_ms: int = 30000  # 30 seconds
    # Set the maximum time (in milliseconds) the program will wait for the power supply to respond to a command before giving up
    power_supply_timeout_ms: int = 10000  # 10 seconds
    # Set the maximum time (in milliseconds) the program will wait for the digital multimeter to respond to a command before giving up
    dmm_timeout_ms: int = 30000  # 30 seconds





# Apply the @dataclass decorator so Python automatically generates the __init__ method for this settings container
@dataclass
# Define a container class that holds all timing, oscilloscope scaling, and analysis settings used during test execution; adjust these values to change how the test is run
class TestParameters:
    # Docstring summarising what information this class stores
    """Test execution parameters"""
    # Load step timing
    # Set the time in nanoseconds over which the electronic load steps from the low current level to the high current level; 100 ns approximates a realistic fast transient event
    step_time_ns: int = 100  # Load step rise/fall time (nanoseconds)
    
    # Oscilloscope settings
    # Set the horizontal time scale of the oscilloscope display in milliseconds per division; this controls how wide a time window is captured around the transient event
    scope_time_base_ms: float = 1.0  # Time base: 1ms/div or 5ms/div
    # Set the vertical voltage scale of the oscilloscope display in millivolts per division; 50 mV per division is chosen to make small voltage transients clearly visible
    scope_voltage_scale_mv: float = 50.0  # Voltage scale: 50mV/div for transient capture
    # Set the percentage of the captured waveform time window that is recorded before the trigger event; 10% of the window before the step allows the stable baseline to be seen
    trigger_pre_capture_percent: float = 10.0  # Pre-trigger capture percentage
    
    # Test execution
    # Set the number of seconds the program waits after each action to allow the power rail voltage to stabilise before the next measurement is taken
    settle_time_s: float = 1.0  # Time to allow settling between measurements
    # Set the number of seconds the program pauses between the positive load step and the negative load step, giving the rail time to fully recover before the next transient is applied
    step_delay_s: float = 2.0  # Delay between positive and negative steps
    
    # Analysis parameters
    # Set the ratio threshold used to decide whether oscillations after a transient event should be flagged as ringing; if the peak-to-RMS ratio exceeds this value the result is marked as ringing
    ringing_detection_threshold: float = 0.4  # RMS-to-peak ratio threshold for ringing detection





# Apply the @dataclass decorator to this class so Python generates the __init__ method automatically from the declared fields
@dataclass
# Define a container class that holds the specification limits for one individual power rail; each rail on the board has its own instance of this class with its own pass/fail thresholds
class RailLimits:
    # Docstring summarising what information this class stores
    """Power rail test limits and specifications"""
    # The short label used to identify this power rail throughout the test (e.g., "3V3", "1V8"); appears in reports and on-screen messages
    name: str
    # The physical probe connection point on the circuit board where the oscilloscope probe should be placed to measure this rail (e.g., "TP2")
    test_point: str
    # The maximum current in milliamps that the electronic load is permitted to draw from this rail during the load step; the actual step goes to half of this value
    max_current_ma: int
    # The nominal output voltage in volts that this power rail is designed to supply; used as the baseline for calculating droop and overshoot
    expected_voltage_v: float
    # The maximum allowed voltage drop in millivolts below the nominal voltage when the load step is applied; exceeding this value means the regulator cannot hold the rail steady enough
    max_droop_mv: float
    # The maximum allowed time in microseconds for the rail voltage to recover back to within its specification band after the load step; exceeding this means the regulator is too slow
    max_recovery_time_us: float
    # The maximum allowed voltage spike in millivolts above the nominal voltage when the load is suddenly removed; exceeding this could damage sensitive devices powered from this rail
    max_overshoot_mv: float
    # The low (starting) current level in milliamps that the electronic load is set to before each load step is applied; defaults to 100 mA if not specified
    low_current_ma: int = 100
    
    # Define a method that converts all the fields of this RailLimits object into a plain Python dictionary; this is needed to save the configuration to a JSON file
    def to_dict(self) -> Dict[str, Any]:
        # Build and return a dictionary where each key is a field name and each value is the corresponding field value for this rail
        return {
            # Include the rail name label
            'name': self.name,
            # Include the physical test point identifier on the PCB
            'test_point': self.test_point,
            # Include the maximum current limit for the load step
            'max_current_ma': self.max_current_ma,
            # Include the nominal target voltage for this rail
            'expected_voltage_v': self.expected_voltage_v,
            # Include the maximum permitted voltage droop limit
            'max_droop_mv': self.max_droop_mv,
            # Include the maximum permitted recovery time limit
            'max_recovery_time_us': self.max_recovery_time_us,
            # Include the maximum permitted overshoot limit
            'max_overshoot_mv': self.max_overshoot_mv,
            # Include the low (baseline) current level used before each load step
            'low_current_ma': self.low_current_ma
        }





# Define the top-level configuration class that combines instrument settings, test execution parameters, and all rail specification limits into a single object that the test script imports
class LoadTransientConfig:
    # Docstring summarising what this class provides
    """Complete Load Transient test configuration"""
    
    # Define the setup method that runs automatically when a new LoadTransientConfig object is created; it populates all three configuration sections with their default values
    def __init__(self):
        # Create a new InstrumentConfig object using all its default values and store it as the instrument settings section of this configuration
        self.instruments = InstrumentConfig()
        # Create a new TestParameters object using all its default values and store it as the test execution settings section of this configuration
        self.test_params = TestParameters()
        # Call the internal helper method that builds the full list of rail specification objects and store the result as the rail limits section of this configuration
        self.rail_limits = self._get_standard_rail_limits()
        
    # Define the internal method that constructs the list of RailLimits objects, one per power rail, based on the Load Transient test specification document
    def _get_standard_rail_limits(self) -> List[RailLimits]:
        """
        Define standard rail limits per Load Transient specification

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
        # Build and return a list containing one RailLimits object for each power rail on the board; the values come directly from the Load Transient test specification
        return [
            # Main power rails (3V6/3V3: max droop < 50-75mV, recovery < 150µs, overshoot < 30mV)
            # Create the specification limits object for the 3.6 V main power rail
            RailLimits(
                # Short label for the 3.6 V rail used in all reports and console output
                name="3V6",
                # Physical probe contact point on the PCB for the 3.6 V rail
                test_point="TP2",
                # Maximum rated current for this rail; the load step will go to half this value (800 mA)
                max_current_ma=1600,  # Half = 800mA load step
                # Target nominal output voltage for the 3.6 V rail
                expected_voltage_v=3.6,
                # Maximum permitted voltage droop when the 800 mA load step is applied; must stay within 75 mV of nominal
                max_droop_mv=75.0,
                # Maximum allowed time for the rail to recover back within specification after the load step; must be within 150 microseconds
                max_recovery_time_us=150.0,
                # Maximum permitted voltage overshoot above nominal when the load is removed; must stay within 30 mV
                max_overshoot_mv=30.0
            ),
            # Create the specification limits object for the 3.3 V main power rail
            RailLimits(
                # Short label for the 3.3 V rail
                name="3V3",
                # Physical probe contact point on the PCB for the 3.3 V rail
                test_point="TP10",
                # Maximum rated current for this rail; the load step will go to half this value (1500 mA)
                max_current_ma=3000,  # Half = 1500mA load step
                # Target nominal output voltage for the 3.3 V rail
                expected_voltage_v=3.3,
                # Maximum permitted voltage droop; must stay within 75 mV of nominal
                max_droop_mv=75.0,
                # Maximum allowed recovery time; must be within 150 microseconds
                max_recovery_time_us=150.0,
                # Maximum permitted overshoot; must stay within 30 mV above nominal
                max_overshoot_mv=30.0
            ),

            # 2V5/1V8 rails (max droop < 50mV, recovery < 150µs, overshoot < 30mV)
            # Create the specification limits object for the 2.5 V power rail
            RailLimits(
                # Short label for the 2.5 V rail
                name="2V5",
                # Physical probe contact point on the PCB for the 2.5 V rail
                test_point="TP9",
                # Maximum rated current for this rail; the load step will go to half this value (750 mA)
                max_current_ma=1500,  # Half = 750mA load step
                # Target nominal output voltage for the 2.5 V rail
                expected_voltage_v=2.5,
                # Maximum permitted voltage droop; must stay within 50 mV of nominal
                max_droop_mv=50.0,
                # Maximum allowed recovery time; must be within 150 microseconds
                max_recovery_time_us=150.0,
                # Maximum permitted overshoot; must stay within 30 mV above nominal
                max_overshoot_mv=30.0
            ),
            # Create the specification limits object for the 1.8 V power rail
            RailLimits(
                # Short label for the 1.8 V rail
                name="1V8",
                # Physical probe contact point on the PCB for the 1.8 V rail
                test_point="TP6",
                # Maximum rated current for this rail; the load step will go to half this value (1500 mA)
                max_current_ma=3000,  # Half = 1500mA load step
                # Target nominal output voltage for the 1.8 V rail
                expected_voltage_v=1.8,
                # Maximum permitted voltage droop; must stay within 50 mV of nominal
                max_droop_mv=50.0,
                # Maximum allowed recovery time; must be within 150 microseconds
                max_recovery_time_us=150.0,
                # Maximum permitted overshoot; must stay within 30 mV above nominal
                max_overshoot_mv=30.0
            ),

            # Core rails (max droop < 50-60mV, recovery < 100µs, overshoot < 20mV)
            # Create the specification limits object for the 1.35 V core power rail
            RailLimits(
                # Short label for the 1.35 V core rail
                name="1V35",
                # Physical probe contact point on the PCB for the 1.35 V rail
                test_point="TP7",
                # Maximum rated current for this rail; the load step will go to half this value (1500 mA)
                max_current_ma=3000,  # Half = 1500mA load step
                # Target nominal output voltage for the 1.35 V core rail
                expected_voltage_v=1.35,
                # Maximum permitted voltage droop; must stay within 60 mV of nominal
                max_droop_mv=60.0,
                # Maximum allowed recovery time; tighter limit of 100 microseconds for core rails
                max_recovery_time_us=100.0,
                # Maximum permitted overshoot; tighter limit of 20 mV above nominal for core rails
                max_overshoot_mv=20.0
            ),
            # Create the specification limits object for the 1.0 V PS (Processing System) core rail
            RailLimits(
                # Short label for the 1.0 V PS rail
                name="1V_PS",
                # Physical probe contact point on the PCB for the 1.0 V PS rail
                test_point="TP5",
                # Maximum rated current for this rail; the load step will go to half this value (1500 mA)
                max_current_ma=3000,  # Half = 1500mA load step
                # Target nominal output voltage for the 1.0 V PS rail
                expected_voltage_v=1.0,
                # Maximum permitted voltage droop; must stay within 60 mV of nominal
                max_droop_mv=60.0,
                # Maximum allowed recovery time; tighter limit of 100 microseconds for core rails
                max_recovery_time_us=100.0,
                # Maximum permitted overshoot; tighter limit of 20 mV above nominal for core rails
                max_overshoot_mv=20.0
            ),
            # Create the specification limits object for the 1.0 V PL (Programmable Logic) core rail
            RailLimits(
                # Short label for the 1.0 V PL rail
                name="1V_PL",
                # Physical probe contact point on the PCB for the 1.0 V PL rail
                test_point="TP8",
                # Maximum rated current for this rail; the load step will go to half this value (1500 mA)
                max_current_ma=3000,  # Half = 1500mA load step
                # Target nominal output voltage for the 1.0 V PL rail
                expected_voltage_v=1.0,
                # Maximum permitted voltage droop; must stay within 60 mV of nominal
                max_droop_mv=60.0,
                # Maximum allowed recovery time; tighter limit of 100 microseconds for core rails
                max_recovery_time_us=100.0,
                # Maximum permitted overshoot; tighter limit of 20 mV above nominal for core rails
                max_overshoot_mv=20.0
            ),

            # Ethernet subsystem rails (E0)
            # Create the specification limits object for the 1.1 V Ethernet subsystem rail
            RailLimits(
                # Short label for the 1.1 V Ethernet rail
                name="1V1_E0",
                # Physical probe contact point on the PCB for the 1.1 V Ethernet rail
                test_point="TP13",
                # Maximum rated current for this rail; the load step will go to half this value (500 mA); lower than the main rails because the Ethernet subsystem draws less current
                max_current_ma=1000,  # Half = 500mA load step
                # Target nominal output voltage for the 1.1 V Ethernet rail
                expected_voltage_v=1.1,
                # Maximum permitted voltage droop; must stay within 50 mV of nominal
                max_droop_mv=50.0,
                # Maximum allowed recovery time; 150 microseconds for this Ethernet subsystem rail
                max_recovery_time_us=150.0,
                # Maximum permitted overshoot; must stay within 20 mV above nominal
                max_overshoot_mv=20.0
            ),
            # Create the specification limits object for the 2.5 V Ethernet subsystem rail
            RailLimits(
                # Short label for the 2.5 V Ethernet rail
                name="2V5_E0",
                # Physical probe contact point on the PCB for the 2.5 V Ethernet rail
                test_point="TP14",
                # Maximum rated current for this rail; the load step will go to half this value (500 mA)
                max_current_ma=1000,  # Half = 500mA load step
                # Target nominal output voltage for the 2.5 V Ethernet rail
                expected_voltage_v=2.5,
                # Maximum permitted voltage droop; must stay within 50 mV of nominal
                max_droop_mv=50.0,
                # Maximum allowed recovery time; 150 microseconds for this Ethernet subsystem rail
                max_recovery_time_us=150.0,
                # Maximum permitted overshoot; must stay within 30 mV above nominal
                max_overshoot_mv=30.0
            ),
            # Create the specification limits object for the 1.8 V Ethernet subsystem rail
            RailLimits(
                # Short label for the 1.8 V Ethernet rail
                name="1V8_E0",
                # Physical probe contact point on the PCB for the 1.8 V Ethernet rail
                test_point="TP15",
                # Maximum rated current for this rail; the load step will go to half this value (500 mA)
                max_current_ma=1000,  # Half = 500mA load step
                # Target nominal output voltage for the 1.8 V Ethernet rail
                expected_voltage_v=1.8,
                # Maximum permitted voltage droop; must stay within 50 mV of nominal
                max_droop_mv=50.0,
                # Maximum allowed recovery time; 150 microseconds for this Ethernet subsystem rail
                max_recovery_time_us=150.0,
                # Maximum permitted overshoot; must stay within 30 mV above nominal
                max_overshoot_mv=30.0
            ),
        ]
    
    # Define the public method that looks up a single rail's specification limits by its name label and returns the matching RailLimits object
    def get_rail_by_name(self, rail_name: str) -> RailLimits:
        # Docstring explaining what this method does
        """Get rail configuration by name"""
        # Iterate through the list of all configured rails looking for the one whose name matches the requested label
        for rail in self.rail_limits:
            # Compare the name of the current rail in the loop against the requested name; return this rail if they match
            if rail.name == rail_name:
                # Return the matching RailLimits object so the caller can read its voltage, current, and limit values
                return rail
        # If the loop completed without finding a match, raise a descriptive error so the caller knows exactly which rail name was invalid
        raise ValueError(f"Rail '{rail_name}' not found in configuration")
    
    # Define the public method that returns a simple list of all rail name labels currently configured; useful for building menus and validating user input
    def get_available_rail_names(self) -> List[str]:
        # Docstring explaining what this method does
        """Get list of all configured rail names"""
        # Build and return a list containing only the name labels extracted from each RailLimits object in the rail_limits list
        return [rail.name for rail in self.rail_limits]
    
    # Define the public method that writes the entire current configuration (instruments, test parameters, and rail limits) to a JSON file on disk so it can be reloaded in a future session
    def save_config(self, filepath: str) -> None:
        # Docstring explaining what this method does
        """Save configuration to JSON file"""
        # Build a nested dictionary containing all three sections of the configuration, ready for serialisation to JSON format
        config_data = {
            # The 'instruments' section holds all VISA addresses and timeout values for the test bench equipment
            'instruments': {
                # Save the oscilloscope VISA address
                'oscilloscope_address': self.instruments.oscilloscope_address,
                # Save the oscilloscope type/model identifier string
                'oscilloscope_type': self.instruments.oscilloscope_type,
                # Save the power supply VISA address
                'power_supply_address': self.instruments.power_supply_address,
                # Save the electronic load VISA address
                'electronic_load_address': self.instruments.electronic_load_address,
                # Save the digital multimeter VISA address
                'dmm_address': self.instruments.dmm_address,
                # Save the oscilloscope communication timeout in milliseconds
                'oscilloscope_timeout_ms': self.instruments.oscilloscope_timeout_ms,
                # Save the electronic load communication timeout in milliseconds
                'electronic_load_timeout_ms': self.instruments.electronic_load_timeout_ms,
                # Save the power supply communication timeout in milliseconds
                'power_supply_timeout_ms': self.instruments.power_supply_timeout_ms,
                # Save the digital multimeter communication timeout in milliseconds
                'dmm_timeout_ms': self.instruments.dmm_timeout_ms
            },
            # The 'test_parameters' section holds all timing and oscilloscope scaling settings
            'test_parameters': {
                # Save the load step rise/fall time in nanoseconds
                'step_time_ns': self.test_params.step_time_ns,
                # Save the oscilloscope horizontal time scale in milliseconds per division
                'scope_time_base_ms': self.test_params.scope_time_base_ms,
                # Save the oscilloscope vertical voltage scale in millivolts per division
                'scope_voltage_scale_mv': self.test_params.scope_voltage_scale_mv,
                # Save the pre-trigger capture percentage setting
                'trigger_pre_capture_percent': self.test_params.trigger_pre_capture_percent,
                # Save the settling wait time between measurements in seconds
                'settle_time_s': self.test_params.settle_time_s,
                # Save the delay between the positive and negative load steps in seconds
                'step_delay_s': self.test_params.step_delay_s,
                # Save the ringing detection threshold ratio value
                'ringing_detection_threshold': self.test_params.ringing_detection_threshold
            },
            # The 'rail_limits' section is a list of dictionaries, one per rail, built by calling to_dict() on each RailLimits object
            'rail_limits': [rail.to_dict() for rail in self.rail_limits]
        }
        
        # Open the file at the specified path for writing (creating it if it does not exist, overwriting it if it does); 'f' is the file handle
        with open(filepath, 'w') as f:
            # Write the config_data dictionary to the file in JSON format; indent=2 makes the file human-readable with two-space indentation
            json.dump(config_data, f, indent=2)
    
    # Define the public method that reads a previously saved JSON configuration file and updates all settings in this object to match the values stored in the file
    def load_config(self, filepath: str) -> None:
        # Docstring explaining what this method does
        """Load configuration from JSON file"""
        # Open the specified JSON configuration file for reading; 'f' is the file handle
        with open(filepath, 'r') as f:
            # Parse the JSON content from the file into a nested Python dictionary and store it in config_data
            config_data = json.load(f)
        
        # Update instrument config
        # Check whether the loaded data contains an 'instruments' section before trying to read it
        if 'instruments' in config_data:
            # Extract the instruments sub-dictionary and assign it to a local variable for convenient access
            instr = config_data['instruments']
            # Update the oscilloscope address with the value from the file, keeping the current value as the fallback if the key is missing
            self.instruments.oscilloscope_address = instr.get('oscilloscope_address', self.instruments.oscilloscope_address)
            # Update the oscilloscope type identifier with the value from the file, keeping the current value as the fallback
            self.instruments.oscilloscope_type = instr.get('oscilloscope_type', self.instruments.oscilloscope_type)
            # Update the power supply address with the value from the file, keeping the current value as the fallback
            self.instruments.power_supply_address = instr.get('power_supply_address', self.instruments.power_supply_address)
            # Update the electronic load address with the value from the file, keeping the current value as the fallback
            self.instruments.electronic_load_address = instr.get('electronic_load_address', self.instruments.electronic_load_address)
            # Update the digital multimeter address with the value from the file, keeping the current value as the fallback
            self.instruments.dmm_address = instr.get('dmm_address', self.instruments.dmm_address)
            # Update the oscilloscope timeout with the value from the file, keeping the current value as the fallback
            self.instruments.oscilloscope_timeout_ms = instr.get('oscilloscope_timeout_ms', self.instruments.oscilloscope_timeout_ms)
            # Update the electronic load timeout with the value from the file, keeping the current value as the fallback
            self.instruments.electronic_load_timeout_ms = instr.get('electronic_load_timeout_ms', self.instruments.electronic_load_timeout_ms)
            # Update the power supply timeout with the value from the file, keeping the current value as the fallback
            self.instruments.power_supply_timeout_ms = instr.get('power_supply_timeout_ms', self.instruments.power_supply_timeout_ms)
            # Update the digital multimeter timeout with the value from the file, keeping the current value as the fallback
            self.instruments.dmm_timeout_ms = instr.get('dmm_timeout_ms', self.instruments.dmm_timeout_ms)
        
        # Update test parameters
        # Check whether the loaded data contains a 'test_parameters' section before trying to read it
        if 'test_parameters' in config_data:
            # Extract the test_parameters sub-dictionary and assign it to a local variable for convenient access
            params = config_data['test_parameters']
            # Update the load step time with the value from the file, keeping the current value as the fallback
            self.test_params.step_time_ns = params.get('step_time_ns', self.test_params.step_time_ns)
            # Update the oscilloscope time base setting with the value from the file, keeping the current value as the fallback
            self.test_params.scope_time_base_ms = params.get('scope_time_base_ms', self.test_params.scope_time_base_ms)
            # Update the oscilloscope voltage scale setting with the value from the file, keeping the current value as the fallback
            self.test_params.scope_voltage_scale_mv = params.get('scope_voltage_scale_mv', self.test_params.scope_voltage_scale_mv)
            # Update the pre-trigger capture percentage with the value from the file, keeping the current value as the fallback
            self.test_params.trigger_pre_capture_percent = params.get('trigger_pre_capture_percent', self.test_params.trigger_pre_capture_percent)
            # Update the settling time with the value from the file, keeping the current value as the fallback
            self.test_params.settle_time_s = params.get('settle_time_s', self.test_params.settle_time_s)
            # Update the delay between load steps with the value from the file, keeping the current value as the fallback
            self.test_params.step_delay_s = params.get('step_delay_s', self.test_params.step_delay_s)
            # Update the ringing detection threshold with the value from the file, keeping the current value as the fallback
            self.test_params.ringing_detection_threshold = params.get('ringing_detection_threshold', self.test_params.ringing_detection_threshold)
        
        # Update rail limits
        # Check whether the loaded data contains a 'rail_limits' section before trying to read it
        if 'rail_limits' in config_data:
            # Extract the list of rail limit dictionaries from the loaded data
            rail_data = config_data['rail_limits']
            # Replace the current rail limits list with an empty list; it will be rebuilt from the loaded data
            self.rail_limits = []
            # Loop through each rail dictionary in the loaded data and create a new RailLimits object for it
            for rail_dict in rail_data:
                # Create a new RailLimits object using the values loaded from the JSON file for this rail
                rail = RailLimits(
                    # Set the rail name from the loaded dictionary
                    name=rail_dict['name'],
                    # Set the PCB test point identifier from the loaded dictionary
                    test_point=rail_dict['test_point'],
                    # Set the maximum current limit from the loaded dictionary
                    max_current_ma=rail_dict['max_current_ma'],
                    # Set the expected nominal voltage from the loaded dictionary
                    expected_voltage_v=rail_dict['expected_voltage_v'],
                    # Set the maximum droop limit from the loaded dictionary
                    max_droop_mv=rail_dict['max_droop_mv'],
                    # Set the maximum recovery time limit from the loaded dictionary
                    max_recovery_time_us=rail_dict['max_recovery_time_us'],
                    # Set the maximum overshoot limit from the loaded dictionary
                    max_overshoot_mv=rail_dict['max_overshoot_mv'],
                    # Set the low baseline current level; defaults to 100 mA if this key is not present in the file (backwards compatibility with older saved configs)
                    low_current_ma=rail_dict.get('low_current_ma', 100)
                )
                # Append the newly created RailLimits object to the rail limits list being rebuilt from file
                self.rail_limits.append(rail)



# Quick test configurations for different setups
# Define a utility class that provides ready-made configuration factory methods for the most common test bench hardware combinations; engineers can call these instead of manually editing addresses
class QuickConfigs:
    # Docstring summarising the purpose of this helper class
    """Pre-defined configurations for common test setups"""
    
    # Apply the @staticmethod decorator so this method can be called directly on the class (e.g., QuickConfigs.tektronix_mso24_keithley_setup()) without needing to create an instance first
    @staticmethod
    # Define the factory method that returns a ready-configured LoadTransientConfig for a test bench using a Tektronix MSO24 oscilloscope and Keithley instruments
    def tektronix_mso24_keithley_setup() -> LoadTransientConfig:
        # Docstring explaining which hardware combination this preset is for
        """Configuration for Tektronix MSO24 + Keithley Power Supply + Keithley 2380 Load"""
        # Create a new LoadTransientConfig object using the standard default settings as the starting point
        config = LoadTransientConfig()
        # Override the oscilloscope VISA address with the placeholder address for the Tektronix MSO24; replace with the actual address from the VISA instrument manager
        config.instruments.oscilloscope_address = "USB0::0x0699::0x0522::C012345::INSTR"
        # Set the oscilloscope type identifier so the correct driver functions are used for the Tektronix MSO24
        config.instruments.oscilloscope_type = "tektronix_mso24"
        # Override the power supply address with the placeholder address for the Keithley power supply; replace with the actual address
        config.instruments.power_supply_address = "USB0::0x05E6::0x2230::1234567::INSTR"  # Your Keithley PSU
        # Override the electronic load address with the placeholder address for the Keithley 2380; replace with the actual address
        config.instruments.electronic_load_address = "USB0::0x05E6::0x2380::9103456::INSTR"  # Your Keithley 2380
        # Override the multimeter address with the placeholder address for the Keithley DMM6500; replace with the actual address
        config.instruments.dmm_address = "USB0::0x05E6::0x6500::04561287::INSTR"  # Your Keithley DMM6500
        # Return the fully configured LoadTransientConfig object to the caller
        return config
    
    # Apply the @staticmethod decorator so this method can be called on the class without needing an instance
    @staticmethod
    # Define the factory method that returns a ready-configured LoadTransientConfig for a test bench using a Keysight DSOX6004A oscilloscope and Keithley instruments
    def keysight_dsox6004a_keithley_setup() -> LoadTransientConfig:
        # Docstring explaining which hardware combination this preset is for
        """Configuration for Keysight DSOX6004A + Keithley Power Supply + Keithley 2380 Load"""
        # Create a new LoadTransientConfig object using the standard default settings as the starting point
        config = LoadTransientConfig()
        # Override the oscilloscope VISA address with the placeholder address for the Keysight DSOX6004A; replace with the actual address
        config.instruments.oscilloscope_address = "USB0::0x0957::0x179B::MY12345678::INSTR"
        # Set the oscilloscope type identifier so the correct driver functions are used for the Keysight DSOX6004A
        config.instruments.oscilloscope_type = "keysight_dsox6004a"
        # Override the power supply address with the placeholder address for the Keithley power supply
        config.instruments.power_supply_address = "USB0::0x05E6::0x2230::1234567::INSTR"  # Your Keithley PSU
        # Override the electronic load address with the placeholder address for the Keithley 2380
        config.instruments.electronic_load_address = "USB0::0x05E6::0x2380::9103456::INSTR"  # Your Keithley 2380
        # Override the multimeter address with the placeholder address for the Keithley DMM6500
        config.instruments.dmm_address = "USB0::0x05E6::0x6500::04561287::INSTR"  # Your Keithley DMM6500
        # Return the fully configured LoadTransientConfig object to the caller
        return config
    
    # Apply the @staticmethod decorator so this method can be called on the class without needing an instance
    @staticmethod
    # Define the factory method that returns a ready-configured LoadTransientConfig for a test bench using a Keysight HD304MSO oscilloscope and Keithley instruments
    def keysight_hd304mso_keithley_setup() -> LoadTransientConfig:
        # Docstring explaining which hardware combination this preset is for
        """Configuration for Keysight HD304MSO + Keithley Power Supply + Keithley 2380 Load"""
        # Create a new LoadTransientConfig object using the standard default settings as the starting point
        config = LoadTransientConfig()
        # Override the oscilloscope VISA address with the placeholder address for the Keysight HD304MSO; replace with the actual address
        config.instruments.oscilloscope_address = "USB0::0x0957::0x1780::MY65220169::INSTR"
        # Set the oscilloscope type identifier so the correct driver functions are used for the Keysight HD304MSO
        config.instruments.oscilloscope_type = "keysight_hd304mso"
        # Override the power supply address with the placeholder address for the Keithley power supply
        config.instruments.power_supply_address = "USB0::0x05E6::0x2230::805224014806770001::INSTR"  # Your Keithley PSU
        # Override the electronic load address with the placeholder address for the Keithley 2380
        config.instruments.electronic_load_address = "USB0::0x05E6::0x2380::9103456::INSTR"  # Your Keithley 2380
        # Override the multimeter address with the placeholder address for the Keithley DMM6500
        config.instruments.dmm_address = "USB0::0x05E6::0x6500::04561287::INSTR"  # Your Keithley DMM6500
        # Return the fully configured LoadTransientConfig object to the caller
        return config
    
    # Apply the @staticmethod decorator so this method can be called on the class without needing an instance
    @staticmethod
    # Define a helper method that returns a short list of three commonly tested rails for rapid development or debug runs when the engineer does not want to test all ten rails
    def fast_test_subset() -> List[str]:
        # Docstring explaining the purpose of this quick subset
        """Quick test subset for development/debug"""
        # Return a list containing only the 3.3 V, 1.8 V, and 1.35 V rails; these cover the most important voltage domains for a quick sanity check
        return ["3V3", "1V8", "1V35"]
    
    # Apply the @staticmethod decorator so this method can be called on the class without needing an instance
    @staticmethod
    # Define a helper method that returns only the three core voltage rails, which supply the processor and FPGA fabric; these are the most critical rails to pass
    def core_rails_only() -> List[str]:
        # Docstring explaining which rails are considered "core"
        """Test only core rails (most critical)"""
        # Return a list containing the 1.35 V, 1.0 V PS, and 1.0 V PL rails that power the processor and programmable logic cores
        return ["1V35", "1V_PS", "1V_PL"]
    
    # Apply the @staticmethod decorator so this method can be called on the class without needing an instance
    @staticmethod
    # Define a helper method that returns only the three Ethernet subsystem rails, which supply the on-board Ethernet controller; useful when only the Ethernet section has been changed
    def ethernet_rails_only() -> List[str]:
        # Docstring explaining which rails belong to the Ethernet subsystem
        """Test only Ethernet subsystem rails"""
        # Return a list containing the three Ethernet subsystem rails: 1.1 V, 2.5 V, and 1.8 V
        return ["1V1_E0", "2V5_E0", "1V8_E0"]





# Define the standalone entry-point function that demonstrates how to use this configuration module and generates default JSON configuration files; runs when the script is executed directly
def main():
    # Docstring explaining the purpose of this standalone demo function
    """Example usage and configuration generation"""
    # Print the title of the configuration generator output
    print("Load Transient Configuration Generator")
    # Print a horizontal divider line below the title
    print("=" * 40)
    
    # Create default configuration
    # Create a new LoadTransientConfig object using all the built-in default values; this is the baseline configuration
    config = LoadTransientConfig()
    
    # Show available rails
    # Print the heading for the table listing all configured rails and their key parameters
    print(f"Available Rails ({len(config.rail_limits)}):")
    # Loop through each rail in the configuration and print one summary row per rail
    for rail in config.rail_limits:
        # Print one row showing the rail name, PCB test point, expected voltage, and maximum current in a neatly aligned format
        print(f"  {rail.name:<10}: {rail.test_point:<6} "
              f"{rail.expected_voltage_v:>4.2f}V @ {rail.max_current_ma:>4}mA max")
    
    # Print the heading for the quick test subset section
    print(f"\nQuick Test Subsets:")
    # Print the list of rails in the fast development/debug subset
    print(f"  Fast test: {QuickConfigs.fast_test_subset()}")
    # Print the list of rails in the core rails subset
    print(f"  Core rails: {QuickConfigs.core_rails_only()}")
    # Print the list of rails in the Ethernet subsystem subset
    print(f"  Ethernet: {QuickConfigs.ethernet_rails_only()}")
    
    # Save default configuration
    # Define the file path where the default configuration will be saved
    config_path = "load_transient_config.json"
    # Call the save method to write the current default configuration to the JSON file
    config.save_config(config_path)
    # Print a confirmation message showing the engineer where the file was saved
    print(f"\n✓ Default configuration saved to: {config_path}")
    
    # Example of loading and modifying configuration
    # Print a heading to mark the start of the customisation example
    print("\nExample: Customizing configuration...")
    
    # Modify for your specific setup
    # Override the oscilloscope address with a custom example address to show how the engineer would change it for their specific instrument
    config.instruments.oscilloscope_address = "USB0::0x0699::0x0522::C054321::INSTR"  # Your scope
    # Override the electronic load address with a custom example address
    config.instruments.electronic_load_address = "USB0::0x05E6::0x2380::9106543::INSTR"  # Your load
    # Change the time base to 5 ms per division as an example of adjusting a test parameter
    config.test_params.scope_time_base_ms = 5.0  # Use 5ms/div instead of 1ms/div
    
    # Save customized configuration
    # Define the file path where the customised configuration will be saved
    custom_config_path = "load_transient_config_custom.json"
    # Save the modified configuration to the custom JSON file
    config.save_config(custom_config_path)
    # Print a confirmation message showing the engineer where the customised file was saved
    print(f"✓ Custom configuration saved to: {custom_config_path}")
    
    # Print usage instructions showing how another script would load the custom configuration file
    print(f"\nTo use custom config in test:")
    # Print the first line of the example code snippet
    print(f"  config = LoadTransientConfig()")
    # Print the second line of the example code snippet showing how to call load_config
    print(f"  config.load_config('{custom_config_path}')")





# This block runs only when the file is executed directly (e.g., python load_transient_config.py); it does not run when the file is imported as a library by another script
if __name__ == "__main__":
    # Call the main() demo function to generate default and custom configuration files and print the rail summary
    main()
