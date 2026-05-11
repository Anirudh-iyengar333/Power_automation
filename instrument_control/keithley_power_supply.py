# This line tells the operating system to run this file using Python 3, making it directly executable on Unix-like systems
#!/usr/bin/env python3
# This is the module-level documentation string (docstring) that describes the purpose and key design decisions of this file
"""
Keithley Power Supply Control Library - CONSOLIDATED FINAL
- No lock
- Robust I/O recovery
- Buffer drain and explicit write/read
- Consistent terminations and timeouts
"""

# [Blank line for visual separation between sections]

# Load the 'logging' library, which is used to record informational messages, warnings, and errors to the console or a log file during test runs
import logging
# Load the 'time' library, which is used to introduce deliberate pauses (sleep delays) between instrument commands so the hardware has time to respond
import time
# Load the 're' library (regular expressions), which is used to extract numeric values from raw text strings returned by the instrument
import re
# Load specific type-hint helpers from the 'typing' library: Optional (value may be None), Dict (a key-value dictionary), Any (any data type), Tuple (a fixed-size ordered pair)
from typing import Optional, Dict, Any, Tuple
# Load the 'dataclass' decorator from the 'dataclasses' library, which automatically creates simple data-container classes without needing to write boilerplate constructor code
from dataclasses import dataclass
# Load the 'Enum' base class from the 'enum' library, which is used to define a fixed set of named constant values (e.g., ON/OFF/UNKNOWN states)
from enum import Enum
# Load the 'pyvisa' library, which is the Python interface for communicating with test instruments over USB, GPIB, LAN, or serial using the VISA standard
import pyvisa
# Load the specific 'VisaIOError' exception class from pyvisa, which represents communication errors that can occur when talking to an instrument (e.g., timeout, device not found)
from pyvisa.errors import VisaIOError

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a custom error class for this library; any failure specific to the Keithley power supply will raise this type of error so callers can identify it easily
class KeithleyPowerSupplyError(Exception):
    # This line marks the class body as intentionally empty; all error-raising behaviour is inherited from Python's built-in Exception class
    pass

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a set of named constants to represent the possible on/off states of a power supply output channel, making the code self-documenting and preventing typo-related bugs
class OutputState(Enum):
    # Constant representing the state where a channel's output is switched on and supplying power
    ENABLED = "ENABLED"
    # Constant representing the state where a channel's output is switched off and not supplying power
    DISABLED = "DISABLED"
    # Constant representing the state where the output status could not be determined (e.g., after a communication error)
    UNKNOWN = "UNKNOWN"

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a set of named constants to represent the possible protection states of a channel, covering normal operation and two types of protection faults
class ProtectionState(Enum):
    # Constant representing normal operation with no protection faults active
    NORMAL = "NORMAL"
    # Constant representing an Over-Voltage Protection trip, meaning the output voltage exceeded the configured safety threshold
    OVP_TRIPPED = "OVP_TRIPPED"
    # Constant representing an Over-Current Protection trip, meaning the output current exceeded the configured safety threshold
    OCP_TRIPPED = "OCP_TRIPPED"
    # Constant representing an unknown protection state, used when the status cannot be read from the instrument
    UNKNOWN = "UNKNOWN"

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Apply the @dataclass decorator to the class below, which automatically generates the __init__ constructor and other utility methods based on the fields defined inside it
@dataclass
# Define a simple data container that holds the full configuration settings for one power supply channel (used when sending settings to or reading them from the instrument)
class ChannelConfiguration:
    # The channel number (e.g., 1, 2, or 3) that this configuration applies to
    channel: int
    # The target output voltage in volts that the channel should be set to
    voltage: float
    # The maximum current in amps that the channel is allowed to deliver before current limiting kicks in
    current_limit: float
    # The Over-Voltage Protection threshold in volts; if the output exceeds this value, the channel will trip and shut off
    ovp_level: float
    # A True/False flag indicating whether the output should be switched on after applying this configuration
    output_enabled: bool

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Apply the @dataclass decorator to the class below so Python automatically builds the constructor and comparison methods from the typed fields
@dataclass
# Define a simple data container that holds a snapshot of live measured values from one power supply channel (used to report actual readings back to the test script)
class ChannelMeasurement:
    # The channel number (e.g., 1, 2, or 3) from which these measurements were taken
    channel: int
    # The actual voltage in volts measured at the output terminals of this channel
    voltage: float
    # The actual current in amps measured flowing out of this channel
    current: float
    # The calculated output power in watts for this channel (voltage multiplied by current)
    power: float
    # The current on/off state of this channel's output, expressed as one of the OutputState constants
    output_state: OutputState
    # The current protection status of this channel, expressed as one of the ProtectionState constants
    protection_state: ProtectionState

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define the main class that encapsulates all communication logic for the Keithley bench power supply; every operation (connect, configure, measure, disconnect) lives here
class KeithleyPowerSupply:
    # Define the constructor method, which runs automatically when a new power supply object is created; it accepts the USB/VISA address and an optional communication timeout
    def __init__(self, visa_address: str, timeout_ms: int = 10000):
        # Store the VISA address string (e.g., "USB0::0x05E6::0x2230::XXXXXXXX::INSTR") so it can be used later when opening the connection
        self._visa_address = visa_address
        # Store the communication timeout in milliseconds; if the instrument does not reply within this time, an error will be raised
        self._timeout_ms = timeout_ms
        # Initialise the connection status flag to False; it will be set to True only after a successful connection is established
        self._is_connected = False
        # Initialise the VISA resource manager reference to None; this object manages the list of available instruments and will be created during connect()
        self._resource_manager: Optional[pyvisa.ResourceManager] = None
        # Initialise the instrument handle to None; this object represents the actual open connection to the power supply and will be assigned during connect()
        self._instrument: Any = None  # pyvisa Resource object (use Any to avoid type errors)
        # [Blank line for visual separation between sections]
        # Create a dedicated logger for this specific instance of the class, using both the class name and a unique object ID so log messages from multiple instances can be distinguished
        self._logger = logging.getLogger(f'{self.__class__.__name__}.{id(self)}')
        # [Blank line for visual separation between sections]
        # Set the default maximum number of output channels supported by the instrument; this may be overwritten after the model is identified during connection
        self.max_channels = 3
        # Set the default maximum output voltage in volts; this may be overwritten after the model is identified during connection
        self.max_voltage = 30.0
        # Set the default maximum output current in amps; this may be overwritten after the model is identified during connection
        self.max_current = 3.0
        # Set the model name to a placeholder string; this will be replaced with the actual model name once the instrument responds to identification queries
        self.model = "Unknown"
        # [Blank line for visual separation between sections]
        # Define how long in seconds to wait after sending a voltage command, giving the hardware time to settle to the new voltage before the next command is sent
        self._voltage_settling_time = 0.5
        # Define how long in seconds to wait after sending a current-limit command, giving the hardware time to apply the new setting before the next command is sent
        self._current_settling_time = 0.5
        # Define how long in seconds to wait after turning an output on, giving the hardware time to fully enable and stabilise before measurements are taken
        self._output_enable_time = 0.7
        # Define how long in seconds to wait after sending a reset command, giving the instrument enough time to complete its internal reset procedure
        self._reset_time = 3.0
        # [Blank line for visual separation between sections]
        # Define the allowable voltage range as a (minimum, maximum) pair in volts; any requested voltage outside this range will be rejected before being sent to the instrument
        self._valid_voltage_range = (0.0, 30.0)
        # Define the allowable current-limit range as a (minimum, maximum) pair in amps; the minimum is set above zero to prevent accidentally setting zero current limit
        self._valid_current_range = (0.001, 3.0)
        # Define the allowable Over-Voltage Protection range as a (minimum, maximum) pair in volts; the minimum is 1V to ensure OVP is always set above any reasonable output voltage
        self._valid_ovp_range = (1.0, 35.0)

    # Apply the @property decorator, which allows the method below to be called like a simple attribute (e.g., psu.is_connected) rather than a method call (psu.is_connected())
    @property
    # Define a read-only property that reports whether the power supply is currently connected and ready to accept commands; it checks both the internal flag and the instrument handle
    def is_connected(self) -> bool:
        # Return True only if both the connection flag is True AND the instrument handle exists; this guards against partial or failed connection states
        return self._is_connected and self._instrument is not None

    # Apply the @property decorator so the VISA address can be read like a plain attribute from outside the class without being accidentally overwritten
    @property
    # Define a read-only property that returns the VISA address string for this power supply instance, useful for logging and diagnostics
    def visa_address(self) -> str:
        # Return the stored VISA address string that was provided when this object was created
        return self._visa_address

    # Define the method that establishes the USB/VISA communication link with the physical power supply; it returns True if the connection succeeds and False if it fails
    def connect(self) -> bool:
        # Begin a try block so that if anything goes wrong during connection (cable unplugged, wrong address, instrument off), the error is caught and handled gracefully
        try:
            # Log that the connection attempt is starting, so the test log shows when this step began
            self._logger.info("Attempting to connect to Keithley power supply...")
            # Create the VISA resource manager, which scans the system for connected instruments and prepares the communication layer
            self._resource_manager = pyvisa.ResourceManager()
            # Log that the resource manager was created successfully, confirming the VISA driver is working
            self._logger.info("VISA resource manager created successfully")
            # [Blank line for visual separation between sections]
            # Open a communication session to the specific instrument at the stored VISA address; this creates the actual connection handle
            self._instrument = self._resource_manager.open_resource(self._visa_address)
            # Log that the connection to the address was opened, providing a confirmation point in the test log
            self._logger.info(f"Opened connection to {self._visa_address}")
            # [Blank line for visual separation between sections]
            # Set the communication timeout on the open instrument session so it matches the value specified when this object was created
            self._instrument.timeout = self._timeout_ms
            # Tell the instrument driver to expect a newline character at the end of every response it reads from the instrument
            self._instrument.read_termination = '\n'
            # Tell the instrument driver to append a newline character to the end of every command it sends to the instrument
            self._instrument.write_termination = '\n'
            # [Blank line for visual separation between sections]
            # Send the standard SCPI identification query to the instrument and read back its response, which contains the manufacturer, model, serial number, and firmware version
            identification = self._instrument.query("*IDN?")
            # Log the full identification string returned by the instrument so it is recorded in the test log for traceability
            self._logger.info(f"Instrument identification: {identification.strip()}")
            # [Blank line for visual separation between sections]
            # Call the internal helper method that parses the identification string and sets the correct voltage/current limits and channel count for the detected model
            self._configure_model_parameters(identification)
            # [Blank line for visual separation between sections]
            # Send the *CLS (Clear Status) command to the instrument to reset all error registers and clear any leftover status from a previous session
            self._instrument.write("*CLS")
            # Wait for the instrument to complete its reset procedure before sending any further commands
            time.sleep(self._reset_time)
            # Send the *OPC? (Operation Complete) query and wait for the instrument to confirm that all pending operations have finished
            self._instrument.query("*OPC?")
            # [Blank line for visual separation between sections]
            # Mark the connection as successful by setting the internal flag to True
            self._is_connected = True
            # Log a success message including the detected model name, so the test log confirms which physical instrument was connected
            self._logger.info(f"Successfully connected to Keithley {self.model}")
            # Return True to the caller to indicate that the connection was established without errors
            return True
        # [Blank line for visual separation between sections]
        # Catch any exception that occurred during the connection attempt so the program does not crash and can clean up resources properly
        except Exception as e:
            # Log the error message so the test log records why the connection failed
            self._logger.error(f"Connection failed: {e}")
            # Begin a nested try block to safely attempt cleanup even if the main connection failed partway through
            try:
                # If the instrument handle was partially created before the failure, close it to release the USB port
                if self._instrument:
                    self._instrument.close()
                # If the resource manager was created before the failure, close it to release VISA resources
                if self._resource_manager:
                    self._resource_manager.close()
            # If the cleanup itself raises an error (e.g., the handle was never valid), silently ignore it and continue
            except Exception:
                pass
            # Reset the instrument handle to None so subsequent checks correctly see the instrument as not connected
            self._instrument = None
            # Reset the resource manager to None so it can be recreated cleanly on the next connection attempt
            self._resource_manager = None
            # Reset the connection status flag to False to correctly reflect the failed connection state
            self._is_connected = False
            # Return False to the caller to indicate that the connection attempt failed
            return False

    # Define the internal helper method that reads the instrument's identification string and configures the correct model-specific limits and channel count
    def _configure_model_parameters(self, identification: str):
        # Split the identification string on commas to separate the individual fields (manufacturer, model, serial, firmware)
        parts = identification.strip().split(',')
        # Extract the first field as the manufacturer name, or use an empty string if the identification string had no fields
        manufacturer = parts[0] if len(parts) > 0 else ""
        # Extract the second field as the model name, or use an empty string if the identification string had fewer than two fields
        model = parts[1] if len(parts) > 1 else ""
        # [Blank line for visual separation between sections]
        # Check that the manufacturer name contains either "KEITHLEY" or "TEKTRONIX" (case-insensitive); if it does not, log a warning because an unexpected instrument may have been connected
        if "KEITHLEY" not in manufacturer.upper() and "TEKTRONIX" not in manufacturer.upper():
            self._logger.warning(f"Unexpected manufacturer: {manufacturer}")
        # [Blank line for visual separation between sections]
        # Check if the model string contains "2230", indicating this is a Keithley 2230-30-3 triple-output power supply
        if "2230" in model:
            # Set the channel count to 3 for the 2230-30-3 model
            self.max_channels = 3
            # Set the maximum output voltage to 30 V per channel for the 2230-30-3 model
            self.max_voltage = 30.0
            # Set the maximum output current to 3 A per channel for the 2230-30-3 model
            self.max_current = 3.0
            # Record the full model name string for logging and display purposes
            self.model = "2230-30-3"
        # Check if the model string contains "2231", indicating this is a Keithley 2231A-30-3 triple-output power supply
        elif "2231" in model:
            # Set the channel count to 3 for the 2231A-30-3 model
            self.max_channels = 3
            # Set the maximum output voltage to 30 V per channel for the 2231A-30-3 model
            self.max_voltage = 30.0
            # Set the maximum output current to 3 A per channel for the 2231A-30-3 model
            self.max_current = 3.0
            # Record the full model name string for logging and display purposes
            self.model = "2231A-30-3"
        # Check if the model string contains "2280S", indicating this is a Keithley 2280S high-voltage single-channel power supply
        elif "2280S" in model:
            # Set the channel count to 1 because the 2280S is a single-output instrument
            self.max_channels = 1
            # Set the maximum output voltage to 72 V for the 2280S model
            self.max_voltage = 72.0
            # Set the maximum output current to 120 A for the 2280S model
            self.max_current = 120.0
            # Record the full model name string for logging and display purposes
            self.model = "2280S"
        # Handle any unrecognised model string by applying safe default values and logging a warning
        else:
            # Use a default channel count of 3 as a conservative assumption for an unknown model
            self.max_channels = 3
            # Use a default maximum voltage of 30 V as a conservative assumption for an unknown model
            self.max_voltage = 30.0
            # Use a default maximum current of 3 A as a conservative assumption for an unknown model
            self.max_current = 3.0
            # Store the raw model string (with whitespace trimmed) as the model name so it appears in logs
            self.model = model.strip()
            # Log a warning so the engineer knows the model was not recognised and defaults were applied
            self._logger.warning(f"Unknown model {model}, using defaults")
        # [Blank line for visual separation between sections]
        # Update the valid voltage range tuple to reflect the actual maximum voltage of the identified model
        self._valid_voltage_range = (0.0, self.max_voltage)
        # Update the valid current range tuple to reflect the actual maximum current of the identified model
        self._valid_current_range = (0.001, self.max_current)
        # Update the valid OVP range tuple so the upper limit is 5 V above the instrument's maximum voltage, providing a safety margin
        self._valid_ovp_range = (1.0, self.max_voltage + 5.0)
        # [Blank line for visual separation between sections]
        # Log a summary of the model configuration that was applied, including channel count and the per-channel voltage and current limits
        self._logger.info(f"Configured model {self.model}: {self.max_channels} channels, {self.max_voltage}V/{self.max_current}A max")

    # Define the method that safely closes the connection to the power supply; it always tries to turn off all outputs first before releasing the USB session
    def disconnect(self):
        # Begin a try block to ensure that even if something fails during shutdown, the program attempts to clean up as much as possible
        try:
            # Only proceed with the graceful shutdown sequence if the instrument was actually connected and the handle exists
            if self._is_connected and self._instrument:
                # Begin a nested try block to attempt turning off all outputs; if this fails, it should not prevent the rest of the disconnect from completing
                try:
                    # Call the method that sends the OFF command to every output channel, so no channel is left energised after the test ends
                    self.disable_all_outputs()
                    # Wait half a second after disabling outputs to allow the channels to fully de-energise before closing the connection
                    time.sleep(0.5)
                # If disabling outputs raises an error (e.g., instrument stopped responding), log a warning but continue with disconnection
                except Exception as e:
                    self._logger.warning(f"Could not disable outputs during disconnect: {e}")
                # Close the VISA session to the instrument, releasing the USB port so other processes can use it
                self._instrument.close()
                # Log that the instrument connection was successfully closed
                self._logger.info("Instrument connection closed")
            # Check if the resource manager was created and still needs to be closed
            if self._resource_manager:
                # Close the VISA resource manager, releasing the underlying VISA driver resources
                self._resource_manager.close()
                # Log that the resource manager was successfully closed
                self._logger.info("VISA resource manager closed")
        # Catch any unexpected error that occurred during the disconnect sequence and log it so it appears in the test record
        except Exception as e:
            self._logger.error(f"Error during disconnection: {e}")
        # The 'finally' block always runs regardless of whether an error occurred, ensuring the internal state is always cleaned up
        finally:
            # Reset the instrument handle to None so the object correctly reports as disconnected
            self._instrument = None
            # Reset the resource manager reference to None so it can be recreated on the next connection attempt
            self._resource_manager = None
            # Set the connection flag to False so any subsequent check correctly shows the instrument as disconnected
            self._is_connected = False
            # Log that the full disconnection sequence has completed
            self._logger.info("Disconnection completed")

    # Define the method that retrieves and returns a dictionary of identifying information about the connected instrument (manufacturer, model, serial number, firmware, and limits)
    def get_instrument_info(self) -> Optional[Dict[str, Any]]:
        # Check if the instrument is connected before attempting to query it; if not, log an error and return immediately
        if not self.is_connected:
            self._logger.error("Cannot get info: not connected")
            return None
        # Begin a try block to handle any communication error that might occur while querying the instrument
        try:
            # Send the SCPI identification query to the instrument and store the response after removing leading and trailing whitespace
            idn = self._instrument.query("*IDN?").strip()
            # Split the identification string on commas to separate the individual fields into a list
            parts = idn.split(',')
            # Build and return a dictionary containing each piece of instrument information, using safe defaults if any field is missing
            return {
                # The name of the manufacturer (e.g., "KEITHLEY INSTRUMENTS"), taken from the first field of the identification string
                'manufacturer': parts[0] if len(parts) > 0 else 'Unknown',
                # The model designation (e.g., "2230-30-3"), taken from the second field
                'model': parts[1] if len(parts) > 1 else 'Unknown',
                # The unique serial number of this specific unit, taken from the third field, used for traceability in test records
                'serial_number': parts[2] if len(parts) > 2 else 'Unknown',
                # The firmware version currently installed on the instrument, taken from the fourth field
                'firmware_version': parts[3] if len(parts) > 3 else 'Unknown',
                # The number of independent output channels available on this instrument
                'max_channels': self.max_channels,
                # The maximum output voltage in volts that this instrument can produce on any channel
                'max_voltage': self.max_voltage,
                # The maximum output current in amps that this instrument can deliver on any channel
                'max_current': self.max_current,
                # The VISA address string used to connect to this instrument (useful for reference in test reports)
                'visa_address': self._visa_address,
                # The full raw identification string as returned by the instrument
                'identification': idn
            }
        # Catch any communication error, log it, and return None to indicate that the information could not be retrieved
        except Exception as e:
            self._logger.error(f"Failed to get instrument info: {e}")
            return None

    # Define the method that fully configures one output channel by setting its target voltage, current limit, over-voltage protection level, and optionally switching the output on
    def configure_channel(self, channel: int, voltage: float, current_limit: float, ovp_level: float, enable_output: bool = False) -> bool:
        # Check that the instrument is connected before sending any commands; if not, log an error and exit early
        if not self.is_connected:
            self._logger.error("Cannot configure channel: not connected")
            return False
        # Validate that the requested channel number is within the range of channels available on this instrument
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel {channel}")
            return False
        # Validate that the requested voltage falls within the allowed voltage range for this instrument model
        if not (self._valid_voltage_range[0] <= voltage <= self._valid_voltage_range[1]):
            self._logger.error(f"Voltage {voltage}V out of range {self._valid_voltage_range}")
            return False
        # Validate that the requested current limit falls within the allowed current range for this instrument model
        if not (self._valid_current_range[0] <= current_limit <= self._valid_current_range[1]):
            self._logger.error(f"Current limit {current_limit}A out of range {self._valid_current_range}")
            return False
        # Check that the OVP level is strictly greater than the output voltage, which is required by the instrument; if not, automatically increase it to 1 V above the set voltage
        if ovp_level <= voltage:
            self._logger.warning(f"OVP {ovp_level}V must be > voltage {voltage}V; adjusting to {voltage+1.0}V")
            ovp_level = voltage + 1.0
        # Begin a try block to handle any communication error that occurs while sending configuration commands
        try:
            # Send the command to select the target channel on the instrument so subsequent commands apply to it
            self._instrument.write(f":INSTrument:SELect CH{channel}")
            # Wait 200 milliseconds for the channel selection to take effect before sending the next command
            time.sleep(0.2)
            # Send the command to set the target output voltage on the selected channel
            self._instrument.write(f":SOURce:VOLTage {voltage}")
            # Wait for the voltage setting to stabilise before sending the current limit command
            time.sleep(self._voltage_settling_time)
            # Send the command to set the current limit on the selected channel, which protects the device under test from over-current damage
            self._instrument.write(f":SOURce:CURRent {current_limit}")
            # Wait for the current limit setting to stabilise before sending the OVP command
            time.sleep(self._current_settling_time)
            # Send the command to set the Over-Voltage Protection threshold on the selected channel
            self._instrument.write(f":SOURce:VOLTage:PROTection {ovp_level}")
            # Wait 300 milliseconds for the OVP setting to be applied before proceeding
            time.sleep(0.3)
            # If the caller requested that the output be switched on immediately after configuration, send the enable command
            if enable_output:
                self._instrument.write(":OUTPut ON")
                # Wait for the output to fully enable and reach a stable state before allowing the test to continue
                time.sleep(self._output_enable_time)
            # Query the instrument to read back the voltage it actually stored, to confirm the setting was applied correctly
            actual_voltage = float(self._instrument.query(":SOURce:VOLTage?"))
            # Query the instrument to read back the current limit it actually stored, to confirm the setting was applied correctly
            actual_current = float(self._instrument.query(":SOURce:CURRent?"))
            # Log the confirmed settings at INFO level for the test record, showing both the applied values and whether the output is on
            self._logger.info(f"CH{channel} configured: {actual_voltage:.6f}V, {actual_current:.6f}A limit, Output: {'Enabled' if enable_output else 'Disabled'}")
            # Return True to the caller to indicate the channel was configured successfully
            return True
        # Catch any communication error that occurred during configuration, log it with the channel number, and return False
        except Exception as e:
            self._logger.error(f"Failed to configure channel {channel}: {e}")
            return False

    # Define the method that switches on the output of a specific channel, making it deliver power to the device under test
    def enable_channel_output(self, channel: int) -> bool:
        # Check that the instrument is connected before sending any commands; if not, log an error and return False
        if not self.is_connected:
            self._logger.error("Cannot enable output: not connected")
            return False
        # Validate that the channel number is within the valid range for this instrument
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel {channel}")
            return False
        # Begin a try block to handle any communication error that might occur while enabling the output
        try:
            # Log that the output enable command is about to be sent, providing a timestamped entry in the test log
            self._logger.info(f"Enabling output on CH{channel}")
            # Send the command to select the target channel on the instrument
            self._instrument.write(f":INSTrument:SELect CH{channel}")
            # Wait 200 milliseconds for the channel selection to take effect
            time.sleep(0.2)
            # Send the command to turn the output on for the selected channel
            self._instrument.write(":OUTPut ON")
            # Wait for the output to fully enable and stabilise before checking its state
            time.sleep(self._output_enable_time)
            # Query the instrument for the current output state and convert it to upper-case for consistent comparison
            state = self._instrument.query(":OUTPut?").strip().upper()
            # Check whether the instrument confirmed the output is on (it may respond with "1" or "ON")
            if state in ("1", "ON"):
                # Log that the channel output was successfully enabled
                self._logger.info(f"CH{channel} output enabled")
                # Return True to the caller to confirm the enable command succeeded
                return True
            # If the instrument reported a state other than "1" or "ON", the enable command did not take effect; log this as an error
            self._logger.error(f"CH{channel} output enable failed; state='{state}'")
            # Return False to indicate that the output was not successfully enabled
            return False
        # Catch any communication error, log it with the channel number, and return False
        except Exception as e:
            self._logger.error(f"Enable output failed on CH{channel}: {e}")
            return False

    # Define the method that switches off the output of a specific channel, stopping it from delivering power to the device under test
    def disable_channel_output(self, channel: int) -> bool:
        # Check that the instrument is connected before sending any commands; if not, log an error and return False
        if not self.is_connected:
            self._logger.error("Cannot disable output: not connected")
            return False
        # Validate that the channel number is within the valid range for this instrument
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel {channel}")
            return False
        # Begin a try block to handle any communication error that might occur while disabling the output
        try:
            # Log that the output disable command is about to be sent
            self._logger.info(f"Disabling output on CH{channel}")
            # Send the command to select the target channel on the instrument
            self._instrument.write(f":INSTrument:SELect CH{channel}")
            # Wait 200 milliseconds for the channel selection to take effect
            time.sleep(0.2)
            # Send the command to turn the output off for the selected channel
            self._instrument.write(":OUTPut OFF")
            # Wait 500 milliseconds for the output to fully de-energise before checking its state
            time.sleep(0.5)
            # Query the instrument for the current output state and convert it to upper-case for consistent comparison
            state = self._instrument.query(":OUTPut?").strip().upper()
            # Check whether the instrument confirmed the output is off (it may respond with "0" or "OFF")
            if state in ("0", "OFF"):
                # Log that the channel output was successfully disabled
                self._logger.info(f"CH{channel} output disabled")
                # Return True to the caller to confirm the disable command succeeded
                return True
            # If the instrument reported a state other than "0" or "OFF", the disable command did not take effect; log this as an error
            self._logger.error(f"CH{channel} output disable failed; state='{state}'")
            # Return False to indicate that the output was not successfully disabled
            return False
        # Catch any communication error, log it with the channel number, and return False
        except Exception as e:
            self._logger.error(f"Disable output failed on CH{channel}: {e}")
            return False

    # Define the method that iterates over every channel and turns each one off; this is used as a safe shutdown step at the end of a test or during disconnect
    def disable_all_outputs(self) -> bool:
        # Check that the instrument is connected before sending any commands; if not, log an error and return False
        if not self.is_connected:
            self._logger.error("Cannot disable outputs: not connected")
            return False
        # Create a flag to track whether all channels were disabled successfully; it will be set to False if any channel fails
        ok = True
        # Iterate over each channel number from 1 up to and including the maximum channel number for this instrument
        for ch in range(1, self.max_channels + 1):
            # Attempt to disable the current channel; if it fails, set the overall success flag to False
            if not self.disable_channel_output(ch):
                ok = False
            # Wait 200 milliseconds between channel disable commands to avoid overwhelming the instrument with rapid commands
            time.sleep(0.2)
        # Check whether all channels were disabled successfully and log the appropriate outcome
        if ok:
            self._logger.info("All outputs disabled")
        else:
            self._logger.warning("Some outputs may still be ON")
        # Return the overall success flag: True if every channel was disabled, False if one or more channels failed
        return ok

    # Define the method that changes the output voltage on a specific channel without touching the current limit, OVP, or any other setting
    def set_voltage(self, channel: int, voltage: float) -> bool:
        """
        Set voltage on a specific channel without changing other parameters.

        Args:
            channel: Channel number (1-max_channels)
            voltage: Voltage to set in volts

        Returns:
            True if successful, False otherwise
        """
        # Check that the instrument is connected before sending any commands; if not, log an error and return False
        if not self.is_connected:
            self._logger.error("Cannot set voltage: not connected")
            return False
        # [Blank line for visual separation between sections]
        # Validate that the requested channel number is within the range of available channels for this instrument
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel {channel}")
            return False
        # [Blank line for visual separation between sections]
        # Validate that the requested voltage is within the safe operating range for this instrument model
        if not (self._valid_voltage_range[0] <= voltage <= self._valid_voltage_range[1]):
            self._logger.error(f"Voltage {voltage}V out of range {self._valid_voltage_range}")
            return False
        # [Blank line for visual separation between sections]
        # Begin a try block to catch any communication error that occurs while sending the voltage command
        try:
            # Use APPLY command which directly sets voltage on specific channel
            # This is more reliable than SELECT + SOURCE pattern for multi-channel
            # Format: APPLY CH{channel},{voltage}
            # [Blank line for visual separation between sections]
            # Send the APPLY command, which sets the voltage on the named channel directly without needing a separate channel-select command
            self._instrument.write(f":APPLY CH{channel},{voltage}")
            time.sleep(0.1)  # Delay for command to complete
            # [Blank line for visual separation between sections]
            # Log the successful voltage update at DEBUG level (visible only when verbose logging is enabled) so the test trace shows the value that was applied
            self._logger.debug(f"CH{channel} voltage set to {voltage:.4f}V using APPLY")
            # Return True to confirm the voltage command was sent without error
            return True
        # Catch any communication error that occurs during the command, log it, and return False
        except Exception as e:
            self._logger.error(f"Failed to set voltage on channel {channel}: {e}")
            return False

    # Define the method that queries the instrument and returns the actual live voltage currently being output by a specific channel
    def measure_voltage(self, channel: int) -> Optional[float]:
        """
        Measure voltage on a specific channel.

        Args:
            channel: Channel number (1-max_channels)

        Returns:
            Measured voltage in volts, or None if measurement fails
        """
        # Check that the instrument is connected before sending any commands; if not, log an error and return None
        if not self.is_connected:
            self._logger.error("Cannot measure voltage: not connected")
            return None
        # [Blank line for visual separation between sections]
        # Validate that the requested channel number is within the range of available channels for this instrument
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel {channel}")
            return None
        # [Blank line for visual separation between sections]
        # Begin a try block to catch any communication or parsing error that occurs during measurement
        try:
            # Send the channel-select command to point the instrument at the correct channel before querying it
            self._instrument.write(f":INSTrument:SELect CH{channel}")
            # Wait 100 milliseconds for the channel selection to take effect before querying
            time.sleep(0.1)
            # Send the voltage measurement query and store the raw text response after removing whitespace
            voltage_str = self._instrument.query(":MEASure:VOLTage?").strip()
            # [Blank line for visual separation between sections]
            # Parse numeric value from response
            # Use a regular expression to find all numbers (including decimals, signs, and scientific notation) in the raw response string
            matches = re.findall(r'[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?', voltage_str)
            # Check if at least one number was found in the response
            if matches:
                # Convert the first matched number to a floating-point value representing the measured voltage
                voltage = float(matches[0])
                # Log the measured voltage at DEBUG level for detailed tracing
                self._logger.debug(f"CH{channel} measured voltage: {voltage}V")
                # Return the measured voltage value to the caller
                return voltage
            else:
                # If no number was found in the response, log a warning including the raw string for diagnostic purposes
                self._logger.warning(f"Could not parse voltage from '{voltage_str}'")
                # Return 0.0 as a safe fallback value instead of None, so callers receive a numeric result
                return 0.0
        # Catch any communication or parsing error, log it, and return None to indicate measurement failure
        except Exception as e:
            self._logger.error(f"Failed to measure voltage on channel {channel}: {e}")
            return None

    # Define the method that queries the instrument and returns the actual live current currently being drawn from a specific channel
    def measure_current(self, channel: int) -> Optional[float]:
        """
        Measure current on a specific channel.

        Args:
            channel: Channel number (1-max_channels)

        Returns:
            Measured current in amps, or None if measurement fails
        """
        # Check that the instrument is connected before sending any commands; if not, log an error and return None
        if not self.is_connected:
            self._logger.error("Cannot measure current: not connected")
            return None
        # [Blank line for visual separation between sections]
        # Validate that the requested channel number is within the range of available channels for this instrument
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel {channel}")
            return None
        # [Blank line for visual separation between sections]
        # Begin a try block to catch any communication or parsing error that occurs during measurement
        try:
            # Send the channel-select command so subsequent measurement queries apply to the correct channel
            self._instrument.write(f":INSTrument:SELect CH{channel}")
            time.sleep(0.3)  # Increased from 0.1s to 0.3s for proper channel switching
            # Send the current measurement query and store the raw text response after removing whitespace
            current_str = self._instrument.query(":MEASure:CURRent?").strip()
            # [Blank line for visual separation between sections]
            # Parse numeric value from response
            # Use a regular expression to find all numbers (including decimals, signs, and scientific notation) in the raw response string
            matches = re.findall(r'[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?', current_str)
            # Check if at least one number was found in the response
            if matches:
                # Convert the first matched number to a floating-point value representing the measured current
                current = float(matches[0])
                # [Blank line for visual separation between sections]
                # Check if output is OFF and sanitize current reading
                # Begin a nested try block to check the output state, so that even if this check fails, the current value is still returned
                try:
                    # Query the instrument for the current output state so we can decide whether the current reading is physically meaningful
                    state_str = self._instrument.query(":OUTPut?").strip()
                    # If the output is off, any current reading above 1 mA is a hardware noise artefact and should be zeroed out
                    if state_str in ['0', 'OFF', 'off']:
                        if abs(current) > 0.001:
                            self._logger.debug(f"Output OFF but current={current}A, forcing to 0")
                            # Override the spurious current reading with zero because the output is physically off
                            current = 0.0
                # If querying the output state fails, silently continue and return whatever current value was already parsed
                except Exception:
                    pass
                # [Blank line for visual separation between sections]
                # Log the final measured current value at DEBUG level
                self._logger.debug(f"CH{channel} measured current: {current}A")
                # Return the measured current value to the caller
                return current
            else:
                # If no number was found in the response, log a warning including the raw string for diagnostic purposes
                self._logger.warning(f"Could not parse current from '{current_str}'")
                # Return 0.0 as a safe fallback so callers receive a numeric result
                return 0.0
        # Catch any communication or parsing error, log it, and return None to indicate measurement failure
        except Exception as e:
            self._logger.error(f"Failed to measure current on channel {channel}: {e}")
            return None

    # Define the method that measures both voltage and current from a single channel in one operation and returns them together as a pair; this is the recommended measurement method for test scripts
    def measure_channel_output(self, channel: int) -> Optional[Tuple[float, float]]:
        """
        ABSOLUTE FINAL: Improved parsing and buffer management
        Returns (voltage, current) tuple or None if measurement fails
        """
        # Check that the instrument is connected before sending any commands; if not, log an error and return None
        if not self.is_connected:
            self._logger.error("Cannot measure: not connected")
            return None
        # [Blank line for visual separation between sections]
        # Validate that the requested channel number is within the range of available channels for this instrument
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel {channel}")
            return None
        # [Blank line for visual separation between sections]
        # Capture original timeout before operations so we can always restore it
        # Save the current instrument timeout value so it can be restored at the end, even if an error occurs
        original_timeout = self._instrument.timeout
        # Begin the main try block that covers all measurement steps; the finally block below will always restore the timeout
        try:
            # Log that the measurement sequence is starting for the specified channel
            self._logger.info(f"Measuring channel {channel}...")
            # [Blank line for visual separation between sections]
            # Set longer timeout for potentially slow measurements
            # Temporarily increase the communication timeout to 15 seconds in case the instrument is slow to respond during measurement
            self._instrument.timeout = 15000  # 15 seconds
            # [Blank line for visual separation between sections]
            # Clear the device/read buffer to remove any stale data without blocking
            # Begin a nested try block for the buffer clear operation, since not all instrument backends support this command
            try:
                # Send a clear command to flush any leftover data from the instrument's response buffer, preventing stale data from corrupting the measurement
                self._instrument.clear()
            # If the buffer clear command is not supported by this instrument or backend, log a debug note and continue; do not abort the measurement
            except Exception as clear_err:
                # Not all backends/resources support clear(); log at debug and continue
                self._logger.debug(f"Buffer clear not supported or failed: {clear_err}")
            # [Blank line for visual separation between sections]
            # Select channel
            # Send the command to select the target channel so all subsequent queries return data from the correct channel
            self._instrument.write(f":INSTrument:SELect CH{channel}")
            time.sleep(0.3)  # Increased to 0.3s for reliable channel switching
            # [Blank line for visual separation between sections]
            # Measure voltage
            # Send the voltage measurement query and store the raw text response after removing leading/trailing whitespace
            voltage_str = self._instrument.query(":MEASure:VOLTage?").strip()
            # Log the raw voltage response string so it is visible in the detailed test log for debugging unexpected values
            self._logger.info(f"Raw voltage response: '{voltage_str}'")
            time.sleep(0.2)  # Increased to 0.2s between measurements
            # [Blank line for visual separation between sections]
            # Measure current
            # Send the current measurement query and store the raw text response after removing leading/trailing whitespace
            current_str = self._instrument.query(":MEASure:CURRent?").strip()
            # Log the raw current response string for debugging purposes
            self._logger.info(f"Raw current response: '{current_str}'")
            # [Blank line for visual separation between sections]
            # Better number parsing
            # Define a local helper function that extracts the first valid number from a raw instrument response string
            def extract_first_float(s: str) -> float:
                # Use a regular expression to find all numbers, including those in scientific notation, within the response string
                matches = re.findall(r'[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?', s)
                # If one or more numbers were found, return the first one as a float
                if matches:
                    return float(matches[0])
                # If no number was found, log a warning and return 0.0 as a safe default
                self._logger.warning(f"Could not parse number from '{s}', returning 0.0")
                return 0.0
            # [Blank line for visual separation between sections]
            # Apply the helper function to the raw voltage response to get a numeric voltage value
            voltage = extract_first_float(voltage_str)
            # Apply the helper function to the raw current response to get a numeric current value
            current = extract_first_float(current_str)
            # [Blank line for visual separation between sections]
            # Check output state and sanitize current if OFF
            # Begin a nested try block to query the output state; if this fails, the voltage and current values already obtained are still returned
            try:
                # Query the instrument for the current output state to determine whether the channel is physically supplying power
                state_str = self._instrument.query(":OUTPut?").strip()
                # Log the raw output state string for detailed tracing
                self._logger.debug(f"Output state: '{state_str}'")
                # If the output is reported as off, any current above 1 mA is instrument noise and should be replaced with zero
                if state_str in ['0', 'OFF', 'off']:
                    if abs(current) > 0.001:
                        self._logger.warning(f"Output OFF but current={current}A, forcing to 0")
                        # Replace the spurious non-zero current reading with zero, because the output is physically off
                        current = 0.0
            # If querying the output state raises an error, log it at DEBUG level and continue with the values already obtained
            except Exception as state_err:
                self._logger.debug(f"Could not check output state: {state_err}")
            # [Blank line for visual separation between sections]
            # Validate readings
            # Check whether the measured voltage is outside the physically realistic range and log a warning if so
            if voltage < 0 or voltage > (self.max_voltage + 5):
                self._logger.warning(f"Unrealistic voltage: {voltage}V")
            # Check whether the measured current is outside the physically realistic range and log a warning if so
            if current < 0 or current > (self.max_current + 2):
                self._logger.warning(f"Unrealistic current: {current}A")
            # [Blank line for visual separation between sections]
            # Log the final validated measurement values as a single summary line at INFO level
            self._logger.info(f"Channel {channel} final: {voltage:.4f}V, {current:.4f}A")
            # Return the voltage and current as a tuple (pair of values) to the caller
            return (voltage, current)
        # [Blank line for visual separation between sections]
        # Catch any error that occurred during measurement, log it along with the full stack trace for debugging, and return None
        except Exception as e:
            self._logger.error(f"Measurement failed on channel {channel}: {e}")
            # Import the traceback module here (inside the except block) so the full call stack is available for the error log
            import traceback
            # Log the complete stack trace so an engineer can identify exactly which line caused the failure
            self._logger.error(traceback.format_exc())
            # Return None to indicate that the measurement could not be completed
            return None
        # The 'finally' block always runs — whether the measurement succeeded or failed — ensuring the timeout is restored
        finally:
            # Always restore the original timeout
            # Begin a try block in case restoring the timeout itself raises an error (e.g., if the instrument connection dropped)
            try:
                # Restore the communication timeout to the value it had before this method increased it
                self._instrument.timeout = original_timeout
            # If restoring the timeout fails, log a debug note but do not raise an additional error
            except Exception as restore_err:
                self._logger.debug(f"Failed to restore timeout: {restore_err}")

    # Define the method that attempts to clear an Over-Voltage or Over-Current protection fault on a specific channel or all channels; this is needed when a protection trip has latched the output off
    def clear_protection(self, channel: int = None) -> bool:
        """
        Attempt to clear protection trip state (OVP/OCP) for a specific channel or all channels.

         IMPORTANT: The Keithley 2230 has a LATCHED OVP protection that typically requires
        a PHYSICAL POWER CYCLE to fully clear. This method attempts software reset, but if
        the front panel still shows "Over Voltage", you MUST:

        1. Turn OFF the power supply using the front panel power button
        2. Wait 5 seconds
        3. Turn ON the power supply again
        4. The OVP indicator should clear

        This method will log an instruction message if software reset doesn't work.

        Args:
            channel: Channel number (1-max_channels), or None to clear all channels

        Returns:
            True if software commands sent successfully (does NOT guarantee OVP cleared)

        Example:
            >>> psu.clear_protection(2)  # Attempt to clear CH2 OVP
            >>> # If front panel still shows OVP, physically power cycle the PSU
        """
        # Check that the instrument is connected before sending any commands; if not, log an error and return False
        if not self.is_connected:
            self._logger.error("Cannot clear protection: not connected")
            return False
        # [Blank line for visual separation between sections]
        # Begin a try block to handle any communication error that occurs during the protection-clear sequence
        try:
            # Check whether a specific channel number was provided, or whether the caller wants to clear all channels
            if channel is not None:
                # Clear specific channel
                # Validate that the specific channel number is within the valid range for this instrument
                if not (1 <= channel <= self.max_channels):
                    self._logger.error(f"Invalid channel {channel}")
                    return False
                # [Blank line for visual separation between sections]
                # Log that the protection-clear sequence is starting for the specified channel
                self._logger.info(f"Clearing protection state on CH{channel}")
                # [Blank line for visual separation between sections]
                # Step 1: Select the channel that tripped OVP
                # Send the channel-select command so all subsequent commands operate on the channel that tripped
                self._instrument.write(f":INSTrument:SELect CH{channel}")
                # Wait 200 milliseconds for the channel selection to take effect
                time.sleep(0.2)
                # [Blank line for visual separation between sections]
                # Step 2: Turn output OFF to clear the OVP latch (per Keithley manual)
                # This is the KEY step - OUTPUT:STATe OFF clears the protection
                # Log that the output is being turned off as the key step in clearing the OVP latch
                self._logger.info(f"CH{channel}: Turning output OFF to clear OVP latch")
                # Send the command to turn the output off on the selected channel; this is the step required by the Keithley manual to reset the OVP latch
                self._instrument.write("OUTPUT:STATe OFF")
                # Wait 500 milliseconds for the output to fully de-energise and the latch to reset
                time.sleep(0.5)
                # [Blank line for visual separation between sections]
                # Step 3: Clear system errors
                # Send the command to clear any system-level error codes stored in the instrument's error queue
                self._instrument.write("SYSTem:ERRor:CLEar")
                # Wait 300 milliseconds for the error-clear command to be processed
                time.sleep(0.3)
                # [Blank line for visual separation between sections]
                # Step 4: Clear standard event status
                # Send the *CLS command to reset all status registers and clear the error queue at the SCPI level
                self._instrument.write("*CLS")
                # Wait 300 milliseconds for the status-clear command to complete
                time.sleep(0.3)
                # [Blank line for visual separation between sections]
                # Step 5: Wait for operation complete
                # Send the *WAI command to instruct the instrument to finish all pending operations before accepting the next command
                self._instrument.write("*WAI")
                # Wait 300 milliseconds for the WAI command to be processed
                time.sleep(0.3)
                # [Blank line for visual separation between sections]
                # Step 6: Turn output back ON (this completes the reset cycle)
                # Log that the output is being turned back on to complete the software reset cycle
                self._logger.info(f"CH{channel}: Turning output ON to complete reset")
                # Send the command to turn the output back on, which completes the off-on-off protection reset cycle
                self._instrument.write("OUTPUT:STATe ON")
                # Wait 500 milliseconds for the output to turn on before immediately turning it off again
                time.sleep(0.5)
                # [Blank line for visual separation between sections]
                # Step 7: Immediately turn OFF again (leave in safe state)
                # Turn the output off again so the channel is left in a safe, de-energised state after the reset
                self._instrument.write("OUTPUT:STATe OFF")
                # Wait 300 milliseconds for the output to fully turn off
                time.sleep(0.3)
                # [Blank line for visual separation between sections]
                # Step 8: Final operation complete check
                # Send the *OPC? query and wait for the instrument to confirm all operations are done before returning
                self._instrument.query("*OPC?")
                # [Blank line for visual separation between sections]
                # Log completion and instructions
                # Log a prominent banner warning to alert the engineer that a software reset was performed and that a physical power cycle may still be required
                self._logger.warning(f"═══════════════════════════════════════════════════════════")
                # Log the first line of the reset summary, identifying which channel was reset
                self._logger.warning(f"CH{channel} SOFTWARE RESET COMPLETE")
                # Log the advisory header that explains what to do if the front panel still shows OVP
                self._logger.warning(f"  IF FRONT PANEL STILL SHOWS 'OVER VOLTAGE':")
                # Log step 1 of the manual power-cycle procedure
                self._logger.warning(f"    1. Turn OFF the PSU (front panel power button)")
                # Log step 2 of the manual power-cycle procedure
                self._logger.warning(f"    2. Wait 5 seconds")
                # Log step 3 of the manual power-cycle procedure
                self._logger.warning(f"    3. Turn ON the PSU")
                # Log step 4 describing the expected outcome after a physical power cycle
                self._logger.warning(f"    4. OVP indicator should clear")
                # Log the closing banner line to visually separate the advisory from subsequent log entries
                self._logger.warning(f"═══════════════════════════════════════════════════════════")
                # [Blank line for visual separation between sections]
                # Return True to indicate that the software reset commands were sent successfully (not that the OVP is guaranteed cleared)
                return True
            else:
                # Clear all channels
                # Log that the protection-clear sequence is about to run across all available channels
                self._logger.info("Clearing protection state on all channels")
                # [Blank line for visual separation between sections]
                # Process each channel individually with full reset sequence
                # Iterate over every channel number from 1 to the maximum so each one receives the reset sequence
                for ch in range(1, self.max_channels + 1):
                    # Select channel
                    # Send the channel-select command for the current loop iteration
                    self._instrument.write(f":INSTrument:SELect CH{ch}")
                    # Wait 200 milliseconds for the channel selection to take effect
                    time.sleep(0.2)
                    # [Blank line for visual separation between sections]
                    # Turn output OFF to clear OVP (per manual)
                    # Send the output-off command, which is the key step for clearing a latched OVP fault
                    self._instrument.write("OUTPUT:STATe OFF")
                    # Wait 500 milliseconds for the output to de-energise
                    time.sleep(0.5)
                    # [Blank line for visual separation between sections]
                    # Cycle output ON then OFF to complete reset
                    # Turn the output on briefly to complete the off-on-off reset cycle required by the instrument
                    self._instrument.write("OUTPUT:STATe ON")
                    # Wait 500 milliseconds for the output to turn on
                    time.sleep(0.5)
                    # Turn the output back off to leave the channel in a safe state after the reset
                    self._instrument.write("OUTPUT:STATe OFF")
                    # Wait 300 milliseconds for the output to turn off before moving to the next channel
                    time.sleep(0.3)
                # [Blank line for visual separation between sections]
                # Clear all system errors
                # After cycling all channels, send the system error clear command to flush the instrument's error queue
                self._instrument.write("SYSTem:ERRor:CLEar")
                # Wait 300 milliseconds for the error clear to complete
                time.sleep(0.3)
                # [Blank line for visual separation between sections]
                # Global clear
                # Send the *CLS command to reset all status registers at the SCPI level for the whole instrument
                self._instrument.write("*CLS")
                # Wait 300 milliseconds for the clear to complete
                time.sleep(0.3)
                # Send the *WAI command to instruct the instrument to complete all pending operations before proceeding
                self._instrument.write("*WAI")
                # Wait 300 milliseconds for the WAI command to complete
                time.sleep(0.3)
                # Send the *OPC? query and wait for the instrument's confirmation that everything is done
                self._instrument.query("*OPC?")
                # [Blank line for visual separation between sections]
                # Log that all channels have been processed and the protection-clear sequence is complete
                self._logger.info("All channels protection cleared and reset")
                # Return True to indicate that the reset commands for all channels were sent successfully
                return True
        # [Blank line for visual separation between sections]
        # Catch any communication error that occurred during the protection-clear sequence, log it, and return False
        except Exception as e:
            self._logger.error(f"Failed to clear protection: {e}")
            return False
