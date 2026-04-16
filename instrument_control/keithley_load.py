# This block is the module-level docstring that describes the purpose, capabilities,
# supported hardware models, and operating modes of this entire file.
"""
ELECTRONIC LOAD CONTROL: Keithley 2380 Series Electronic Load SCPI Wrapper

Provides comprehensive control and measurement capabilities for Keithley 2380 series
programmable DC electronic loads with support for all operation modes and advanced features.

- SCPI COMMANDS VERIFIED AGAINST KEITHLEY 2380 PROGRAMMING MANUAL
- ALL COMMANDS CROSS-REFERENCED WITH OFFICIAL DOCUMENTATION
- COMPREHENSIVE ERROR HANDLING AND LOGGING

Supported Models:
- 2380-500 (500W)
- 2380-120 (120W)

Operation Modes:
- Constant Current (CC)
- Constant Voltage (CV)
- Constant Resistance (CR)
- Constant Power (CP)

"""

# Load the Python standard library for recording log messages (status, warnings, errors)
import logging
# Load the Python standard library for adding pauses between instrument commands
import time
# Load the Path class from the standard library for working with file and folder paths
from pathlib import Path
# Load the datetime class to generate timestamps for filenames and log messages
from datetime import datetime
# Load type-hint helpers so the code can describe what data types functions expect and return
from typing import Optional, Dict, Any, List, Tuple, Union
# Load the NumPy library for fast numerical array operations (used when processing measurement data)
import numpy as np
# Load the shared SCPI communication wrapper that handles the low-level instrument messaging
from instrument_control.scpi_wrapper import SCPIWrapper

# Define a custom error type specifically for problems with the Keithley 2380 electronic load
class Keithley2380Error(Exception):
    # Docstring describing what this custom error class represents
    """Custom exception for Keithley 2380 electronic load errors."""
    # No extra code needed — the class inherits all behaviour from Python's built-in Exception
    pass

# [Blank line for visual separation between sections]

# Define the main control class that wraps all communication with the Keithley 2380 electronic load
class Keithley2380:
    # Docstring summarising what this class does overall
    """Keithley 2380 Series Electronic Load Control Class"""

    # Define the constructor method — this runs automatically when a new Keithley2380 object is created
    def __init__(self, visa_address: str, timeout_ms: int = 30000) -> None:
        # Docstring explaining the constructor's purpose and the parameters it accepts
        """
        Initialize electronic load connection parameters

        Args:
            visa_address: VISA resource address (e.g., "GPIB::5::INSTR" or "COM3")
            timeout_ms: VISA timeout in milliseconds (default: 30000 = 30 seconds)
        """
        # Create a low-level SCPI communication object using the provided address and timeout
        self._scpi_wrapper = SCPIWrapper(visa_address, timeout_ms)
        # Create a dedicated logger for this specific instrument instance, identified by class name and memory address
        self._logger = logging.getLogger(f'{self.__class__.__name__}.{id(self)}')
        # [Blank line for visual separation between sections]
        # Store the comment that these hardware limits will be filled in after connection
        # Device specifications - will be populated after connection
        # Store the default maximum current rating (amperes) for the 2380-120 model
        self.max_current = 120.0  # A - default for 2380-120
        # Store the default maximum input voltage rating (volts) for the electronic load
        self.max_voltage = 60.0   # V - typical maximum
        # Store the default maximum power rating (watts) for the 2380-120 model
        self.max_power = 120.0    # W - default for 2380-120
        # Store the default maximum resistance setting (ohms) supported by the load
        self.max_resistance = 10000.0  # Ω - typical maximum
        # [Blank line for visual separation between sections]
        # Store the comment noting that these mode names were verified from the instrument manual
        # - VERIFIED: Operation modes from manual page 101
        # Build a dictionary mapping short mode codes to the full SCPI command strings for each operating mode
        self._operation_modes = {
            "CC": "CURRent",     # Constant Current
            "CV": "VOLTage",     # Constant Voltage
            "CR": "RESistance",  # Constant Resistance
            "CP": "POWer"        # Constant Power
        }
        # [Blank line for visual separation between sections]
        # Store the comment noting that these transient mode names were verified from the instrument manual
        # - VERIFIED: Transient modes from manual page 108
        # Build a list of valid transient mode names that the load supports for dynamic load stepping
        self._transient_modes = [
            "CONTinuous",  # Continuous pulse stream
            "PULSe",       # Single pulse
            "TOGGle"       # Toggle between levels
        ]
        # [Blank line for visual separation between sections]
        # Store the comment noting that these trigger source names were verified from the instrument manual
        # - VERIFIED: Trigger sources from manual page 93
        # Build a list of all valid trigger sources that can initiate a measurement or transient event
        self._trigger_sources = [
            "BUS",      # GPIB/SCPI trigger
            "EXTernal", # External trigger input
            "HOLD",     # Hold mode
            "MANUal",   # Manual trigger (front panel)
            "TIMer"     # Internal timer
        ]

    # Define the method that opens the communication channel to the physical instrument
    def connect(self) -> bool:
        # Docstring explaining what this method does
        """Establish VISA connection to electronic load"""
        # Attempt to open the VISA connection; if successful, continue with setup
        if self._scpi_wrapper.connect():
            # Begin a block where connection errors are caught gracefully
            try:
                # Ask the instrument to identify itself so we know which model is connected
                identification = self._scpi_wrapper.query("*IDN?")
                # Write the instrument's identity string to the log for traceability
                self._logger.info(f"Instrument identification: {identification.strip()}")
                # [Blank line for visual separation between sections]
                # Store the comment explaining the purpose of parsing the model string
                # Parse model information to set specifications
                # If the identity string indicates a 500 W model, update the power and current limits accordingly
                if "2380-500" in identification:
                    # Set the maximum power limit for the 500 W variant
                    self.max_power = 500.0
                    # Set the maximum current limit for the 500 W variant
                    self.max_current = 120.0
                # If the identity string indicates a 120 W model, set the appropriate lower limits
                elif "2380-120" in identification:
                    # Set the maximum power limit for the 120 W variant
                    self.max_power = 120.0
                    # Set the maximum current limit for the 120 W variant
                    self.max_current = 60.0
                # [Blank line for visual separation between sections]
                # Send the *CLS command to clear any previous status registers and error flags on the instrument
                self._scpi_wrapper.write("*CLS")
                # Pause briefly to allow the instrument to finish clearing its status registers
                time.sleep(0.5)
                # Ask the instrument to confirm it has finished all pending operations before continuing
                self._scpi_wrapper.query("*OPC?")
                # Record a success message in the log confirming the connection is established
                self._logger.info("Successfully connected to Keithley 2380 Electronic Load")
                # Return True to indicate the connection was made successfully
                return True
            # If any error occurs during the identification process, catch it here
            except Exception as e:
                # Record the error details in the log so it can be investigated later
                self._logger.error(f"Error during instrument identification: {e}")
                # Close the connection because the setup did not complete successfully
                self._scpi_wrapper.disconnect()
                # Return False to signal that the connection failed
                return False
        # If the underlying VISA connection itself could not be opened, return False immediately
        return False

    # Define the method that cleanly closes the communication channel to the instrument
    def disconnect(self) -> None:
        # Docstring explaining what this method does
        """Close connection to electronic load"""
        # Tell the SCPI wrapper to close the VISA session
        self._scpi_wrapper.disconnect()
        # Record a message in the log confirming the disconnection completed
        self._logger.info("Disconnection completed")

    # Mark the following method as a read-only property so it can be accessed like an attribute (no parentheses needed)
    @property
    # Define a property that reports whether the instrument is currently connected
    def is_connected(self) -> bool:
        # Docstring explaining what this property returns
        """Check if electronic load is currently connected"""
        # Return the connection status from the underlying SCPI wrapper
        return self._scpi_wrapper.is_connected

    # Define the method that retrieves identification and hardware specification details from the instrument
    def get_instrument_info(self) -> Optional[Dict[str, Any]]:
        # Docstring explaining what this method does and what it returns
        """Query instrument identification and specifications"""
        # If the instrument is not connected, there is nothing to query — return nothing
        if not self.is_connected:
            return None
        # Attempt to query the instrument and parse the response
        try:
            # Send the *IDN? command and remove leading/trailing whitespace from the response
            idn = self._scpi_wrapper.query("*IDN?").strip()
            # Split the comma-separated identity string into individual fields
            parts = idn.split(',')
            # Build and return a dictionary with labelled instrument information and hardware limits
            return {
                'manufacturer': parts[0] if len(parts) > 0 else 'Unknown',
                'model': parts[1] if len(parts) > 1 else 'Unknown',
                'serial_number': parts[2] if len(parts) > 2 else 'Unknown',
                'firmware_version': parts[3] if len(parts) > 3 else 'Unknown',
                'max_current_a': self.max_current,
                'max_voltage_v': self.max_voltage,
                'max_power_w': self.max_power,
                'max_resistance_ohm': self.max_resistance,
                'identification': idn
            }
        # If anything goes wrong during the query or parsing, catch the error
        except Exception as e:
            # Record the error details in the log
            self._logger.error(f"Failed to get instrument info: {e}")
            # Return nothing to indicate the information could not be retrieved
            return None

    # ============================================================================
    # INPUT CONTROL - LOAD ON/OFF AND BASIC OPERATIONS
    # ============================================================================

    # Define the method that switches the electronic load input ON so it starts drawing current
    def enable_input(self) -> bool:
        # Docstring explaining what this function does, which SCPI command it uses, and what it returns
        """
        Enable electronic load input (turn load ON)

        - VERIFIED: [SOURce:]INPut[:STATe] command from manual page 99

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop — cannot enable a disconnected load
        if not self.is_connected:
            self._logger.error("Cannot enable input: electronic load not connected")
            return False

        # Attempt to send the enable command to the instrument
        try:
            # SCPI: [SOURce:]INPut[:STATe] ON (pg 99)
            # Send the command that turns the load input on (starts drawing current from the power supply)
            self._scpi_wrapper.write(":INPut:STATe ON")
            # Wait 100 ms to give the instrument time to activate its input circuit
            time.sleep(0.1)
            # Record a message in the log confirming the input was enabled
            self._logger.info("Electronic load input enabled")
            # Return True to indicate success
            return True
        # If the command fails for any reason, catch the error
        except Exception as e:
            # Record the error type and message in the log
            self._logger.error(f"Failed to enable input: {type(e).__name__}: {e}")
            # Return False to signal that the operation did not succeed
            return False

    # Define the method that switches the electronic load input OFF so it stops drawing current
    def disable_input(self) -> bool:
        # Docstring explaining what this function does, which SCPI command it uses, and what it returns
        """
        Disable electronic load input (turn load OFF)

        - VERIFIED: [SOURce:]INPut[:STATe] command from manual page 99

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot disable input: electronic load not connected")
            return False

        # Attempt to send the disable command to the instrument
        try:
            # SCPI: [SOURce:]INPut[:STATe] OFF (pg 99)
            # Send the command that turns the load input off (stops drawing current)
            self._scpi_wrapper.write(":INPut:STATe OFF")
            # Wait 100 ms for the instrument to deactivate its input circuit
            time.sleep(0.1)
            # Record a message in the log confirming the input was disabled
            self._logger.info("Electronic load input disabled")
            # Return True to indicate success
            return True
        # If the command fails for any reason, catch the error
        except Exception as e:
            # Record the error type and message in the log
            self._logger.error(f"Failed to disable input: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that reads back whether the load input is currently on or off
    def get_input_state(self) -> Optional[bool]:
        # Docstring explaining what this function does, which SCPI command it uses, and what it returns
        """
        Query electronic load input state

        - VERIFIED: [SOURce:]INPut[:STATe]? query from manual page 99

        Returns:
            bool: True if input enabled, False if disabled, None if error
        """
        # If the instrument is not connected, there is nothing to query
        if not self.is_connected:
            return None

        # Attempt to query the input state from the instrument
        try:
            # SCPI: [SOURce:]INPut[:STATe]? (pg 99)
            # Ask the instrument whether its input is currently on (1) or off (0)
            response = self._scpi_wrapper.query(":INPut:STATe?").strip()
            # Convert the numeric string response ("0" or "1") into a Python True/False value
            state = bool(int(response))
            # Write the current state to the debug log for diagnostic purposes
            self._logger.debug(f"Input state: {state}")
            # Return the boolean state value
            return state
        # If the query fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to query input state: {type(e).__name__}: {e}")
            # Return None to indicate the state could not be determined
            return None

    # Define the method that enables short-circuit mode on the load input (maximum current draw)
    def enable_input_short(self) -> bool:
        # Docstring explaining what this function does and what it returns
        """
        Enable input short circuit mode (maximum current sink)

        - VERIFIED: [SOURce:]INPut:SHORt[:STATe] command from manual page 99

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot enable input short: electronic load not connected")
            return False

        # Attempt to activate short-circuit mode
        try:
            # SCPI: [SOURce:]INPut:SHORt[:STATe] ON (pg 99)
            # Send the command to put the load into short-circuit mode (draws as much current as possible)
            self._scpi_wrapper.write(":INPut:SHORt:STATe ON")
            # Wait 100 ms for the load to enter short-circuit mode
            time.sleep(0.1)
            # Record a message in the log confirming the mode was activated
            self._logger.info("Input short circuit mode enabled")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to enable input short: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that turns off short-circuit mode and returns the load to normal operation
    def disable_input_short(self) -> bool:
        # Docstring explaining what this function does and what it returns
        """
        Disable input short circuit mode

        - VERIFIED: [SOURce:]INPut:SHORt[:STATe] command from manual page 99

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot disable input short: electronic load not connected")
            return False

        # Attempt to deactivate short-circuit mode
        try:
            # SCPI: [SOURce:]INPut:SHORt[:STATe] OFF (pg 99)
            # Send the command to exit short-circuit mode
            self._scpi_wrapper.write(":INPut:SHORt:STATe OFF")
            # Wait 100 ms for the load to leave short-circuit mode
            time.sleep(0.1)
            # Record a message confirming the mode was deactivated
            self._logger.info("Input short circuit mode disabled")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to disable input short: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that configures the automatic input timer (auto on/off after a delay)
    def set_input_timer(self, enable: bool, delay_seconds: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Configure input timer for automatic load control

        - VERIFIED: [SOURce:]INPut:TIMer commands from manual page 100

        Args:
            enable: Enable/disable timer
            delay_seconds: Timer delay in seconds (1-60000), only needed when enabling

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set input timer: electronic load not connected")
            return False

        # Attempt to configure the timer
        try:
            # SCPI: [SOURce:]INPut:TIMer[:STATe] (pg 100)
            # Build the ON or OFF string based on whether the timer is being enabled or disabled
            state = "ON" if enable else "OFF"
            # Send the command to turn the timer on or off
            self._scpi_wrapper.write(f":INPut:TIMer:STATe {state}")
            # Wait 100 ms for the instrument to apply the timer state change
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # If enabling the timer AND a delay value was provided, also set the delay duration
            if enable and delay_seconds is not None:
                # Check that the delay is within the valid range of 1 to 60000 seconds
                if not (1 <= delay_seconds <= 60000):
                    # Log an error describing the out-of-range value
                    self._logger.error(f"Invalid timer delay: {delay_seconds}s (must be 1-60000)")
                    # Return False because an invalid delay was specified
                    return False
                # [Blank line for visual separation between sections]
                # SCPI: [SOURce:]INPut:TIMer:DELay (pg 100)
                # Send the command to set the timer delay to the specified number of seconds
                self._scpi_wrapper.write(f":INPut:TIMer:DELay {delay_seconds}")
                # Wait 100 ms for the instrument to store the delay value
                time.sleep(0.1)
                # Record a success message showing the delay that was applied
                self._logger.info(f"Input timer enabled with {delay_seconds}s delay")
            # If only disabling, no delay is needed — log the disable action
            else:
                self._logger.info("Input timer disabled")
            # [Blank line for visual separation between sections]
            # Return True to indicate the timer was configured successfully
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set input timer: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # ============================================================================
    # OPERATION MODE CONTROL - CC, CV, CR, CP
    # ============================================================================

    # Define the method that sets the operating mode of the electronic load (CC, CV, CR, or CP)
    def set_function(self, function: str) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set electronic load operation mode

        - VERIFIED: [SOURce:]FUNCtion command from manual page 101

        Args:
            function: Operation mode - "CURRent", "VOLTage", "RESistance", "POWer"
                     or short forms "CC", "CV", "CR", "CP"

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set function: electronic load not connected")
            return False

        # Store the comment explaining why the short form conversion is needed
        # Convert short forms to full SCPI commands
        # If the user passed a short code like "CC", convert it to the full SCPI keyword "CURRent"
        if function.upper() in self._operation_modes:
            # Look up the full SCPI command string for this short code
            scpi_function = self._operation_modes[function.upper()]
        # If the user already passed a full SCPI keyword, use it directly
        elif function in ["CURRent", "VOLTage", "RESistance", "POWer"]:
            # Store the full keyword as-is for use in the command
            scpi_function = function
        # If the input is neither a valid short code nor a valid full keyword, log an error
        else:
            self._logger.error(f"Invalid function: {function}")
            # Return False because an unrecognised mode was requested
            return False

        # Attempt to send the mode-change command to the instrument
        try:
            # SCPI: [SOURce:]FUNCtion (pg 101)
            # Send the command to switch the load to the requested operating mode
            self._scpi_wrapper.write(f":FUNCtion {scpi_function}")
            # Wait 100 ms for the mode switch to take effect
            time.sleep(0.1)
            # Record a message confirming the mode that was set
            self._logger.info(f"Operation mode set to: {scpi_function}")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set function: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that reads back the current operating mode of the load
    def get_function(self) -> Optional[str]:
        # Docstring explaining what this function does and what it returns
        """
        Query current operation mode

        - VERIFIED: [SOURce:]FUNCtion? query from manual page 101

        Returns:
            str: Current operation mode or None if error
        """
        # If the instrument is not connected, there is nothing to query
        if not self.is_connected:
            return None

        # Attempt to query the current mode
        try:
            # SCPI: [SOURce:]FUNCtion? (pg 101)
            # Ask the instrument which operating mode is currently active
            response = self._scpi_wrapper.query(":FUNCtion?").strip()
            # Write the current mode to the debug log
            self._logger.debug(f"Current function: {response}")
            # Return the mode string to the caller
            return response
        # If the query fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to query function: {type(e).__name__}: {e}")
            # Return None to indicate the mode could not be determined
            return None

    # Define the method that sets whether the load runs from a fixed single level or a programmable list
    def set_function_mode(self, mode: str) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set function mode (Fixed or List)

        - VERIFIED: [SOURce:]FUNCtion:MODE command from manual page 101

        Args:
            mode: "FIXed" or "LIST"

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set function mode: electronic load not connected")
            return False

        # Validate that the requested mode is one of the two allowed values
        if mode.upper() not in ["FIXED", "LIST"]:
            # Log an error describing the invalid value
            self._logger.error(f"Invalid mode: {mode}. Must be FIXED or LIST")
            # Return False because the mode is not recognised
            return False

        # Attempt to send the mode command to the instrument
        try:
            # SCPI: [SOURce:]FUNCtion:MODE (pg 101)
            # Send the command to set the function mode (FIXED or LIST)
            self._scpi_wrapper.write(f":FUNCtion:MODE {mode.upper()}")
            # Wait 100 ms for the instrument to apply the mode change
            time.sleep(0.1)
            # Record a message confirming the mode that was set
            self._logger.info(f"Function mode set to: {mode.upper()}")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set function mode: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # ============================================================================
    # CONSTANT CURRENT (CC) MODE CONTROL
    # ============================================================================

    # Define the method that sets how many amperes the load will draw in constant-current mode
    def set_current_level(self, current: float) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set current level for constant current mode

        - VERIFIED: [SOURce:]CURRent[:LEVel][:IMMediate] command from manual page 103

        Args:
            current: Current level in amperes (0 to max_current)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set current: electronic load not connected")
            return False

        # Validate that the requested current is within the allowed range
        if not (0 <= current <= self.max_current):
            # Log an error describing the out-of-range value
            self._logger.error(f"Invalid current: {current}A (must be 0-{self.max_current})")
            # Return False because the value is out of range
            return False

        # Attempt to send the current-level command to the instrument
        try:
            # SCPI: [SOURce:]CURRent[:LEVel][:IMMediate] (pg 103)
            # Send the command to set the load current to the requested number of amperes
            self._scpi_wrapper.write(f":CURRent:LEVel {current}")
            # Wait 100 ms for the instrument to apply the new current setting
            time.sleep(0.1)
            # Record a message confirming the current level that was set
            self._logger.info(f"Current level set to: {current}A")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set current: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that reads back the current-level setting from the instrument
    def get_current_level(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Query current level setting

        - VERIFIED: [SOURce:]CURRent[:LEVel][:IMMediate]? query from manual page 103

        Returns:
            float: Current level in amperes or None if error
        """
        # If the instrument is not connected, there is nothing to query
        if not self.is_connected:
            return None

        # Attempt to query the current level
        try:
            # SCPI: [SOURce:]CURRent[:LEVel][:IMMediate]? (pg 103)
            # Ask the instrument what current level it is currently configured to draw
            response = self._scpi_wrapper.query(":CURRent:LEVel?").strip()
            # Convert the string response to a floating-point number
            current = float(response)
            # Write the value to the debug log
            self._logger.debug(f"Current level: {current}A")
            # Return the numeric current level to the caller
            return current
        # If the query fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to query current level: {type(e).__name__}: {e}")
            # Return None to indicate the value could not be read
            return None

    # Define the method that sets the measurement range for current (to maximise accuracy at a given level)
    def set_current_range(self, current_range: float) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set current range for optimal resolution

        - VERIFIED: [SOURce:]CURRent:RANGe command from manual page 103

        Args:
            current_range: Current range in amperes

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set current range: electronic load not connected")
            return False

        # Attempt to send the range command to the instrument
        try:
            # SCPI: [SOURce:]CURRent:RANGe (pg 103)
            # Send the command to set the current measurement range
            self._scpi_wrapper.write(f":CURRent:RANGe {current_range}")
            # Wait 100 ms for the instrument to switch to the new range
            time.sleep(0.1)
            # Record a message confirming the range that was set
            self._logger.info(f"Current range set to: {current_range}A")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set current range: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that controls how quickly the load ramps its current up or down (slew rate)
    def set_current_slew_rate(self, slew_rate: Optional[float] = None,
                            positive: Optional[float] = None,
                            negative: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set current slew rate for controlled current changes

        - VERIFIED: [SOURce:]CURRent:SLEW commands from manual page 104-105

        Args:
            slew_rate: Both positive and negative slew rate (A/μs or A/ms depending on mode)
            positive: Positive-going slew rate
            negative: Negative-going slew rate

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set current slew: electronic load not connected")
            return False

        # Attempt to configure the slew rate
        try:
            # If a combined slew rate was provided, set both positive and negative slew rates together
            if slew_rate is not None:
                # SCPI: [SOURce:]CURRent:SLEW[:BOTH] (pg 104)
                # Send the command to set the same slew rate in both directions
                self._scpi_wrapper.write(f":CURRent:SLEW {slew_rate}")
                # Wait 100 ms for the instrument to apply the slew rate
                time.sleep(0.1)
                # Record a message confirming the slew rate
                self._logger.info(f"Current slew rate set to: {slew_rate}")
            # [Blank line for visual separation between sections]
            # If a positive-only slew rate was provided, set just the rising-edge slew rate
            if positive is not None:
                # SCPI: [SOURce:]CURRent:SLEW:POSitive (pg 105)
                # Send the command to set the current slew rate for rising transitions
                self._scpi_wrapper.write(f":CURRent:SLEW:POSitive {positive}")
                # Wait 100 ms for the instrument to apply the positive slew rate
                time.sleep(0.1)
                # Record a message confirming the positive slew rate
                self._logger.info(f"Current positive slew rate set to: {positive}")
            # [Blank line for visual separation between sections]
            # If a negative-only slew rate was provided, set just the falling-edge slew rate
            if negative is not None:
                # SCPI: [SOURce:]CURRent:SLEW:NEGative (pg 105)
                # Send the command to set the current slew rate for falling transitions
                self._scpi_wrapper.write(f":CURRent:SLEW:NEGative {negative}")
                # Wait 100 ms for the instrument to apply the negative slew rate
                time.sleep(0.1)
                # Record a message confirming the negative slew rate
                self._logger.info(f"Current negative slew rate set to: {negative}")
            # [Blank line for visual separation between sections]
            # Return True to indicate all requested slew rate settings were applied
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set current slew: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that switches the slew rate unit between slow mode (A/ms) and quick mode (A/µs)
    def set_current_slow_rate_mode(self, slow_mode: bool) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set current slew rate speed mode

        - VERIFIED: [SOURce:]CURRent:SLOWrate:STATe command from manual page 106

        Args:
            slow_mode: True for slow mode (A/ms), False for quick mode (A/μs)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set slow rate mode: electronic load not connected")
            return False

        # Attempt to set the slew rate speed mode
        try:
            # Build the ON or OFF string depending on whether slow mode is requested
            state = "ON" if slow_mode else "OFF"
            # SCPI: [SOURce:]CURRent:SLOWrate[:STATe] (pg 106)
            # Send the command to set the slew rate speed mode
            self._scpi_wrapper.write(f":CURRent:SLOWrate:STATe {state}")
            # Wait 100 ms for the instrument to apply the mode change
            time.sleep(0.1)
            # Build a human-readable description of which mode was applied
            mode_str = "slow (A/ms)" if slow_mode else "quick (A/μs)"
            # Record a message describing the mode that was activated
            self._logger.info(f"Current slew rate mode set to: {mode_str}")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set slow rate mode: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that configures over-current protection to guard the device under test
    def set_current_protection(self, enable: bool, level: Optional[float] = None,
                             delay: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Configure current protection settings

        - VERIFIED: [SOURce:]CURRent:PROTection commands from manual page 107-108

        Args:
            enable: Enable/disable overcurrent protection
            level: Protection level in amperes (optional)
            delay: Protection delay in seconds (0-60, optional)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set current protection: electronic load not connected")
            return False

        # Attempt to configure the protection settings
        try:
            # SCPI: [SOURce:]CURRent:PROTection:STATe (pg 107)
            # Build the ON or OFF string based on whether protection is being enabled
            state = "ON" if enable else "OFF"
            # Send the command to enable or disable overcurrent protection
            self._scpi_wrapper.write(f":CURRent:PROTection:STATe {state}")
            # Wait 100 ms for the instrument to apply the protection state change
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # If a specific protection trip level was provided, set it on the instrument
            if level is not None:
                # SCPI: [SOURce:]CURRent:PROTection:LEVel (pg 107)
                # Send the command to set the current level at which protection will trip
                self._scpi_wrapper.write(f":CURRent:PROTection:LEVel {level}")
                # Wait 100 ms for the instrument to store the protection level
                time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # If a protection delay was provided, validate and set it
            if delay is not None:
                # Check that the delay is within the valid range of 0 to 60 seconds
                if not (0 <= delay <= 60):
                    # Log an error describing the out-of-range delay
                    self._logger.error(f"Invalid protection delay: {delay}s (must be 0-60)")
                    # Return False because the delay value is invalid
                    return False
                # SCPI: [SOURce:]CURRent:PROTection:DELay (pg 108)
                # Send the command to set how long the overcurrent condition must persist before tripping
                self._scpi_wrapper.write(f":CURRent:PROTection:DELay {delay}")
                # Wait 100 ms for the instrument to store the delay
                time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # Record a message summarising the protection configuration
            self._logger.info(f"Current protection configured: enabled={enable}")
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set current protection: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that sets the upper and lower voltage limits allowed while operating in CC mode
    def set_current_bounds(self, high: Optional[float] = None, low: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set voltage bounds for constant current mode

        - VERIFIED: [SOURce:]CURRent:HIGH/LOW commands from manual page 110

        Args:
            high: High voltage bound in volts
            low: Low voltage bound in volts

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set current bounds: electronic load not connected")
            return False

        # Attempt to set the voltage bounds
        try:
            # If an upper voltage bound was provided, send it to the instrument
            if high is not None:
                # SCPI: [SOURce:]CURRent:HIGH (pg 110)
                # Send the command to set the maximum input voltage allowed in CC mode
                self._scpi_wrapper.write(f":CURRent:HIGH {high}")
                # Wait 100 ms for the instrument to apply the upper bound
                time.sleep(0.1)
                # Record a message confirming the upper bound
                self._logger.info(f"Current mode high voltage bound set to: {high}V")
            # [Blank line for visual separation between sections]
            # If a lower voltage bound was provided, send it to the instrument
            if low is not None:
                # SCPI: [SOURce:]CURRent:LOW (pg 110)
                # Send the command to set the minimum input voltage allowed in CC mode
                self._scpi_wrapper.write(f":CURRent:LOW {low}")
                # Wait 100 ms for the instrument to apply the lower bound
                time.sleep(0.1)
                # Record a message confirming the lower bound
                self._logger.info(f"Current mode low voltage bound set to: {low}V")
            # [Blank line for visual separation between sections]
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set current bounds: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # ============================================================================
    # CONSTANT VOLTAGE (CV) MODE CONTROL
    # ============================================================================

    # Define the method that sets the target voltage the load will regulate to in constant-voltage mode
    def set_voltage_level(self, voltage: float) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set voltage level for constant voltage mode

        - VERIFIED: [SOURce:]VOLTage[:LEVel][:IMMediate] command from manual page 111

        Args:
            voltage: Voltage level in volts (0 to max_voltage)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set voltage: electronic load not connected")
            return False

        # Validate that the requested voltage is within the allowed range
        if not (0 <= voltage <= self.max_voltage):
            # Log an error describing the out-of-range value
            self._logger.error(f"Invalid voltage: {voltage}V (must be 0-{self.max_voltage})")
            # Return False because the value is out of range
            return False

        # Attempt to send the voltage-level command to the instrument
        try:
            # SCPI: [SOURce:]VOLTage[:LEVel][:IMMediate] (pg 111)
            # Send the command to set the load voltage to the requested number of volts
            self._scpi_wrapper.write(f":VOLTage:LEVel {voltage}")
            # Wait 100 ms for the instrument to apply the new voltage setting
            time.sleep(0.1)
            # Record a message confirming the voltage level that was set
            self._logger.info(f"Voltage level set to: {voltage}V")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set voltage: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that reads back the voltage-level setting from the instrument
    def get_voltage_level(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Query voltage level setting

        - VERIFIED: [SOURce:]VOLTage[:LEVel][:IMMediate]? query from manual page 111

        Returns:
            float: Voltage level in volts or None if error
        """
        # If the instrument is not connected, there is nothing to query
        if not self.is_connected:
            return None

        # Attempt to query the voltage level
        try:
            # SCPI: [SOURce:]VOLTage[:LEVel][:IMMediate]? (pg 111)
            # Ask the instrument what voltage level it is currently set to regulate
            response = self._scpi_wrapper.query(":VOLTage:LEVel?").strip()
            # Convert the string response to a floating-point number
            voltage = float(response)
            # Write the value to the debug log
            self._logger.debug(f"Voltage level: {voltage}V")
            # Return the numeric voltage level to the caller
            return voltage
        # If the query fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to query voltage level: {type(e).__name__}: {e}")
            # Return None to indicate the value could not be read
            return None

    # Define the method that sets the voltage measurement range and optionally enables auto-ranging
    def set_voltage_range(self, voltage_range: float, auto: Optional[bool] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set voltage range and auto-range mode

        - VERIFIED: [SOURce:]VOLTage:RANGe commands from manual page 112

        Args:
            voltage_range: Voltage range in volts
            auto: Enable/disable auto-range (optional)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set voltage range: electronic load not connected")
            return False

        # Attempt to set the voltage range
        try:
            # SCPI: [SOURce:]VOLTage:RANGe (pg 112)
            # Send the command to set the fixed voltage range
            self._scpi_wrapper.write(f":VOLTage:RANGe {voltage_range}")
            # Wait 100 ms for the instrument to switch to the new range
            time.sleep(0.1)
            # Record a message confirming the range
            self._logger.info(f"Voltage range set to: {voltage_range}V")
            # [Blank line for visual separation between sections]
            # If an auto-range setting was provided, apply it as well
            if auto is not None:
                # SCPI: [SOURce:]VOLTage:RANGe:AUTO[:STATe] (pg 112)
                # Build the ON or OFF string for auto-range
                state = "ON" if auto else "OFF"
                # Send the command to enable or disable automatic voltage ranging
                self._scpi_wrapper.write(f":VOLTage:RANGe:AUTO:STATe {state}")
                # Wait 100 ms for the instrument to apply the auto-range setting
                time.sleep(0.1)
                # Record a message confirming the auto-range state
                self._logger.info(f"Voltage auto-range: {state}")
            # [Blank line for visual separation between sections]
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set voltage range: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that sets the Von level (minimum voltage at which the load activates) and optional latch behaviour
    def set_voltage_on_level(self, von_level: float, latch: Optional[bool] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set Von (voltage on) level and latch mode

        - VERIFIED: [SOURce:]VOLTage:ON and LATCh commands from manual page 113

        Args:
            von_level: Von level in volts
            latch: Enable/disable latch mode (optional)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set Von level: electronic load not connected")
            return False

        # Attempt to set the Von level and optionally the latch mode
        try:
            # SCPI: [SOURce:]VOLTage[:LEVel]:ON (pg 113)
            # Send the command to set the minimum voltage at which the load turns on
            self._scpi_wrapper.write(f":VOLTage:ON {von_level}")
            # Wait 100 ms for the instrument to store the Von level
            time.sleep(0.1)
            # Record a message confirming the Von level
            self._logger.info(f"Von level set to: {von_level}V")
            # [Blank line for visual separation between sections]
            # If a latch mode setting was provided, apply it as well
            if latch is not None:
                # SCPI: [SOURce:]VOLTage:LATCh[:STATe] (pg 113)
                # Build the ON or OFF string for the latch mode
                state = "ON" if latch else "OFF"
                # Send the command to enable or disable the latch mode (which keeps the load off once Von is crossed)
                self._scpi_wrapper.write(f":VOLTage:LATCh:STATe {state}")
                # Wait 100 ms for the instrument to apply the latch mode
                time.sleep(0.1)
                # Record a message confirming the latch mode state
                self._logger.info(f"Voltage latch mode: {state}")
            # [Blank line for visual separation between sections]
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set Von level: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that sets the upper and lower current limits allowed while operating in CV mode
    def set_voltage_bounds(self, high: Optional[float] = None, low: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set current bounds for constant voltage mode

        - VERIFIED: [SOURce:]VOLTage:HIGH/LOW commands from manual page 116

        Args:
            high: High current bound in amperes
            low: Low current bound in amperes

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set voltage bounds: electronic load not connected")
            return False

        # Attempt to set the current bounds for CV mode
        try:
            # If an upper current bound was provided, send it to the instrument
            if high is not None:
                # SCPI: [SOURce:]VOLTage:HIGH (pg 116)
                # Send the command to set the maximum current draw allowed in CV mode
                self._scpi_wrapper.write(f":VOLTage:HIGH {high}")
                # Wait 100 ms for the instrument to apply the upper bound
                time.sleep(0.1)
                # Record a message confirming the upper bound
                self._logger.info(f"Voltage mode high current bound set to: {high}A")
            # [Blank line for visual separation between sections]
            # If a lower current bound was provided, send it to the instrument
            if low is not None:
                # SCPI: [SOURce:]VOLTage:LOW (pg 116)
                # Send the command to set the minimum current draw allowed in CV mode
                self._scpi_wrapper.write(f":VOLTage:LOW {low}")
                # Wait 100 ms for the instrument to apply the lower bound
                time.sleep(0.1)
                # Record a message confirming the lower bound
                self._logger.info(f"Voltage mode low current bound set to: {low}A")
            # [Blank line for visual separation between sections]
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set voltage bounds: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # ============================================================================
    # CONSTANT RESISTANCE (CR) MODE CONTROL
    # ============================================================================

    # Define the method that sets the target resistance the load will simulate in constant-resistance mode
    def set_resistance_level(self, resistance: float) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set resistance level for constant resistance mode

        - VERIFIED: [SOURce:]RESistance[:LEVel][:IMMediate] command from manual page 116

        Args:
            resistance: Resistance level in ohms

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set resistance: electronic load not connected")
            return False

        # Validate that the resistance value is a positive number
        if resistance <= 0:
            # Log an error describing the invalid value
            self._logger.error(f"Invalid resistance: {resistance}Ω (must be positive)")
            # Return False because a zero or negative resistance is not physically meaningful
            return False

        # Attempt to send the resistance-level command to the instrument
        try:
            # SCPI: [SOURce:]RESistance[:LEVel][:IMMediate] (pg 116)
            # Send the command to set the load resistance to the requested value in ohms
            self._scpi_wrapper.write(f":RESistance:LEVel {resistance}")
            # Wait 100 ms for the instrument to apply the new resistance setting
            time.sleep(0.1)
            # Record a message confirming the resistance level that was set
            self._logger.info(f"Resistance level set to: {resistance}Ω")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set resistance: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that reads back the resistance-level setting from the instrument
    def get_resistance_level(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Query resistance level setting

        - VERIFIED: [SOURce:]RESistance[:LEVel][:IMMediate]? query from manual page 116

        Returns:
            float: Resistance level in ohms or None if error
        """
        # If the instrument is not connected, there is nothing to query
        if not self.is_connected:
            return None

        # Attempt to query the resistance level
        try:
            # SCPI: [SOURce:]RESistance[:LEVel][:IMMediate]? (pg 116)
            # Ask the instrument what resistance level it is currently set to simulate
            response = self._scpi_wrapper.query(":RESistance:LEVel?").strip()
            # Convert the string response to a floating-point number
            resistance = float(response)
            # Write the value to the debug log
            self._logger.debug(f"Resistance level: {resistance}Ω")
            # Return the numeric resistance level to the caller
            return resistance
        # If the query fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to query resistance level: {type(e).__name__}: {e}")
            # Return None to indicate the value could not be read
            return None

    # Define the method that sets the measurement range for resistance (to maximise accuracy)
    def set_resistance_range(self, resistance_range: float) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set resistance range

        - VERIFIED: [SOURce:]RESistance:RANGe command from manual page 117

        Args:
            resistance_range: Resistance range in ohms

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set resistance range: electronic load not connected")
            return False

        # Attempt to send the range command to the instrument
        try:
            # SCPI: [SOURce:]RESistance:RANGe (pg 117)
            # Send the command to set the resistance measurement range
            self._scpi_wrapper.write(f":RESistance:RANGe {resistance_range}")
            # Wait 100 ms for the instrument to switch to the new range
            time.sleep(0.1)
            # Record a message confirming the range that was set
            self._logger.info(f"Resistance range set to: {resistance_range}Ω")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set resistance range: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that sets the upper and lower voltage limits allowed while operating in CR mode
    def set_resistance_bounds(self, high: Optional[float] = None, low: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set voltage bounds for constant resistance mode

        - VERIFIED: [SOURce:]RESistance:HIGH/LOW commands from manual page 119

        Args:
            high: High voltage bound in volts
            low: Low voltage bound in volts

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set resistance bounds: electronic load not connected")
            return False

        # Attempt to set the voltage bounds for CR mode
        try:
            # If an upper voltage bound was provided, send it to the instrument
            if high is not None:
                # SCPI: [SOURce:]RESistance:HIGH (pg 119)
                # Send the command to set the maximum input voltage allowed in CR mode
                self._scpi_wrapper.write(f":RESistance:HIGH {high}")
                # Wait 100 ms for the instrument to apply the upper bound
                time.sleep(0.1)
                # Record a message confirming the upper bound
                self._logger.info(f"Resistance mode high voltage bound set to: {high}V")
            # [Blank line for visual separation between sections]
            # If a lower voltage bound was provided, send it to the instrument
            if low is not None:
                # SCPI: [SOURce:]RESistance:LOW (pg 119)
                # Send the command to set the minimum input voltage allowed in CR mode
                self._scpi_wrapper.write(f":RESistance:LOW {low}")
                # Wait 100 ms for the instrument to apply the lower bound
                time.sleep(0.1)
                # Record a message confirming the lower bound
                self._logger.info(f"Resistance mode low voltage bound set to: {low}V")
            # [Blank line for visual separation between sections]
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set resistance bounds: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # ============================================================================
    # CONSTANT POWER (CP) MODE CONTROL
    # ============================================================================

    # Define the method that sets the target power the load will dissipate in constant-power mode
    def set_power_level(self, power: float) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set power level for constant power mode

        - VERIFIED: [SOURce:]POWer[:LEVel][:IMMediate] command from manual page 119

        Args:
            power: Power level in watts (0 to max_power)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set power: electronic load not connected")
            return False

        # Validate that the requested power is within the allowed range
        if not (0 <= power <= self.max_power):
            # Log an error describing the out-of-range value
            self._logger.error(f"Invalid power: {power}W (must be 0-{self.max_power})")
            # Return False because the value is out of range
            return False

        # Attempt to send the power-level command to the instrument
        try:
            # SCPI: [SOURce:]POWer[:LEVel][:IMMediate] (pg 119)
            # Send the command to set the load power to the requested number of watts
            self._scpi_wrapper.write(f":POWer:LEVel {power}")
            # Wait 100 ms for the instrument to apply the new power setting
            time.sleep(0.1)
            # Record a message confirming the power level that was set
            self._logger.info(f"Power level set to: {power}W")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set power: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that reads back the power-level setting from the instrument
    def get_power_level(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Query power level setting

        - VERIFIED: [SOURce:]POWer[:LEVel][:IMMediate]? query from manual page 119

        Returns:
            float: Power level in watts or None if error
        """
        # If the instrument is not connected, there is nothing to query
        if not self.is_connected:
            return None

        # Attempt to query the power level
        try:
            # SCPI: [SOURce:]POWer[:LEVel][:IMMediate]? (pg 119)
            # Ask the instrument what power level it is currently set to dissipate
            response = self._scpi_wrapper.query(":POWer:LEVel?").strip()
            # Convert the string response to a floating-point number
            power = float(response)
            # Write the value to the debug log
            self._logger.debug(f"Power level: {power}W")
            # Return the numeric power level to the caller
            return power
        # If the query fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to query power level: {type(e).__name__}: {e}")
            # Return None to indicate the value could not be read
            return None

    # Define the method that sets the measurement range for power dissipation
    def set_power_range(self, power_range: float) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set power range

        - VERIFIED: [SOURce:]POWer:RANGe command from manual page 120

        Args:
            power_range: Power range in watts

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set power range: electronic load not connected")
            return False

        # Attempt to send the range command to the instrument
        try:
            # SCPI: [SOURce:]POWer:RANGe (pg 120)
            # Send the command to set the power measurement range
            self._scpi_wrapper.write(f":POWer:RANGe {power_range}")
            # Wait 100 ms for the instrument to switch to the new range
            time.sleep(0.1)
            # Record a message confirming the range that was set
            self._logger.info(f"Power range set to: {power_range}W")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set power range: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that configures over-power protection to guard the device under test
    def set_power_protection(self, level: float, delay: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set power protection level and delay

        - VERIFIED: [SOURce:]POWer:PROTection commands from manual page 124

        Args:
            level: Power protection level in watts
            delay: Protection delay in seconds (optional)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set power protection: electronic load not connected")
            return False

        # Attempt to configure the power protection settings
        try:
            # SCPI: [SOURce:]POWer:PROTection[:LEVel] (pg 124)
            # Send the command to set the power level at which protection will trip
            self._scpi_wrapper.write(f":POWer:PROTection:LEVel {level}")
            # Wait 100 ms for the instrument to store the protection level
            time.sleep(0.1)
            # Record a message confirming the protection level
            self._logger.info(f"Power protection level set to: {level}W")
            # [Blank line for visual separation between sections]
            # If a protection delay was provided, set it as well
            if delay is not None:
                # Note: Manual shows POW:PROT:DEL but command not fully documented
                # Send the command to set how long the overpower condition must last before tripping
                self._scpi_wrapper.write(f":POWer:PROTection:DELay {delay}")
                # Wait 100 ms for the instrument to store the delay
                time.sleep(0.1)
                # Record a message confirming the delay
                self._logger.info(f"Power protection delay set to: {delay}s")
            # [Blank line for visual separation between sections]
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set power protection: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that sets the upper and lower voltage limits allowed while operating in CP mode
    def set_power_bounds(self, high: Optional[float] = None, low: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set voltage bounds for constant power mode

        - VERIFIED: [SOURce:]POWer:HIGH/LOW commands from manual page 123

        Args:
            high: High voltage bound in volts
            low: Low voltage bound in volts

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set power bounds: electronic load not connected")
            return False

        # Attempt to set the voltage bounds for CP mode
        try:
            # If an upper voltage bound was provided, send it to the instrument
            if high is not None:
                # SCPI: [SOURce:]POWer:HIGH (pg 123)
                # Send the command to set the maximum input voltage allowed in CP mode
                self._scpi_wrapper.write(f":POWer:HIGH {high}")
                # Wait 100 ms for the instrument to apply the upper bound
                time.sleep(0.1)
                # Record a message confirming the upper bound
                self._logger.info(f"Power mode high voltage bound set to: {high}V")
            # [Blank line for visual separation between sections]
            # If a lower voltage bound was provided, send it to the instrument
            if low is not None:
                # SCPI: [SOURce:]POWer:LOW (pg 123)
                # Send the command to set the minimum input voltage allowed in CP mode
                self._scpi_wrapper.write(f":POWer:LOW {low}")
                # Wait 100 ms for the instrument to apply the lower bound
                time.sleep(0.1)
                # Record a message confirming the lower bound
                self._logger.info(f"Power mode low voltage bound set to: {low}V")
            # [Blank line for visual separation between sections]
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set power bounds: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # ============================================================================
    # TRANSIENT OPERATION CONTROL
    # ============================================================================

    # Define the method that activates or deactivates the load's transient generator (dynamic load stepping)
    def enable_transient(self, enable: bool) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Enable or disable transient generator

        - VERIFIED: [SOURce:]TRANsient[:STATe] command from manual page 102

        Args:
            enable: True to enable transient generator

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set transient: electronic load not connected")
            return False

        # Attempt to enable or disable the transient generator
        try:
            # Build the ON or OFF string based on whether the transient generator is being enabled
            state = "ON" if enable else "OFF"
            # SCPI: [SOURce:]TRANsient[:STATe] (pg 102)
            # Send the command to turn the transient generator on or off
            self._scpi_wrapper.write(f":TRANsient:STATe {state}")
            # Wait 100 ms for the instrument to apply the change
            time.sleep(0.1)
            # Record a message confirming the transient generator state
            self._logger.info(f"Transient generator: {state}")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set transient: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that configures a current transient — the load will step between two current levels
    def set_current_transient(self, mode: str, a_level: float, b_level: float,
                            a_width: Optional[float] = None, b_width: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Configure current transient operation

        - VERIFIED: [SOURce:]CURRent:TRANsient commands from manual page 108-110

        Args:
            mode: "CONTinuous", "PULSe", or "TOGGle"
            a_level: Level A current in amperes
            b_level: Level B current in amperes
            a_width: Level A width in seconds (optional)
            b_width: Level B width in seconds (optional)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set current transient: electronic load not connected")
            return False

        # Validate that the requested transient mode is one of the supported types
        if mode not in self._transient_modes:
            # Log an error describing the invalid mode
            self._logger.error(f"Invalid transient mode: {mode}")
            # Return False because the mode is not recognised
            return False

        # Attempt to configure the current transient parameters
        try:
            # SCPI: [SOURce:]CURRent:TRANsient:MODE (pg 108)
            # Send the command to set the transient switching pattern (continuous, single pulse, or toggle)
            self._scpi_wrapper.write(f":CURRent:TRANsient:MODE {mode}")
            # Wait 100 ms for the instrument to apply the mode
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # SCPI: [SOURce:]CURRent:TRANsient:ALEVel (pg 109)
            # Send the command to set the Level A current value (the lower or first step)
            self._scpi_wrapper.write(f":CURRent:TRANsient:ALEVel {a_level}")
            # Wait 100 ms for the instrument to store Level A
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # SCPI: [SOURce:]CURRent:TRANsient:BLEVel (pg 109)
            # Send the command to set the Level B current value (the upper or second step)
            self._scpi_wrapper.write(f":CURRent:TRANsient:BLEVel {b_level}")
            # Wait 100 ms for the instrument to store Level B
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # If a Level A duration was provided, set how long the load stays at Level A
            if a_width is not None:
                # SCPI: [SOURce:]CURRent:TRANsient:AWIDth (pg 110)
                # Send the command to set the duration of Level A in seconds
                self._scpi_wrapper.write(f":CURRent:TRANsient:AWIDth {a_width}")
                # Wait 100 ms for the instrument to store the Level A width
                time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # If a Level B duration was provided, set how long the load stays at Level B
            if b_width is not None:
                # SCPI: [SOURce:]CURRent:TRANsient:BWIDth (pg 110)
                # Send the command to set the duration of Level B in seconds
                self._scpi_wrapper.write(f":CURRent:TRANsient:BWIDth {b_width}")
                # Wait 100 ms for the instrument to store the Level B width
                time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # Record a summary message describing the transient configuration
            self._logger.info(f"Current transient configured: {mode}, A={a_level}A, B={b_level}A")
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set current transient: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that configures a voltage transient — the load will step between two voltage levels
    def set_voltage_transient(self, mode: str, a_level: float, b_level: float,
                            a_width: Optional[float] = None, b_width: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Configure voltage transient operation

        - VERIFIED: [SOURce:]VOLTage:TRANsient commands from manual page 114-115

        Args:
            mode: "CONTinuous", "PULSe", or "TOGGle"
            a_level: Level A voltage in volts
            b_level: Level B voltage in volts
            a_width: Level A width in seconds (optional)
            b_width: Level B width in seconds (optional)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set voltage transient: electronic load not connected")
            return False

        # Validate that the requested transient mode is one of the supported types
        if mode not in self._transient_modes:
            # Log an error describing the invalid mode
            self._logger.error(f"Invalid transient mode: {mode}")
            # Return False because the mode is not recognised
            return False

        # Attempt to configure the voltage transient parameters
        try:
            # SCPI: [SOURce:]VOLTage:TRANsient:MODE (pg 114)
            # Send the command to set the voltage transient switching pattern
            self._scpi_wrapper.write(f":VOLTage:TRANsient:MODE {mode}")
            # Wait 100 ms for the instrument to apply the mode
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # SCPI: [SOURce:]VOLTage:TRANsient:ALEVel (pg 114)
            # Send the command to set the Level A voltage value
            self._scpi_wrapper.write(f":VOLTage:TRANsient:ALEVel {a_level}")
            # Wait 100 ms for the instrument to store Level A
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # SCPI: [SOURce:]VOLTage:TRANsient:BLEVel (pg 114)
            # Send the command to set the Level B voltage value
            self._scpi_wrapper.write(f":VOLTage:TRANsient:BLEVel {b_level}")
            # Wait 100 ms for the instrument to store Level B
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # If a Level A duration was provided, set how long the load stays at Level A
            if a_width is not None:
                # SCPI: [SOURce:]VOLTage:TRANsient:AWIDth (pg 115)
                # Send the command to set the duration of Level A in seconds
                self._scpi_wrapper.write(f":VOLTage:TRANsient:AWIDth {a_width}")
                # Wait 100 ms for the instrument to store the Level A width
                time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # If a Level B duration was provided, set how long the load stays at Level B
            if b_width is not None:
                # SCPI: [SOURce:]VOLTage:TRANsient:BWIDth (pg 115)
                # Send the command to set the duration of Level B in seconds
                self._scpi_wrapper.write(f":VOLTage:TRANsient:BWIDth {b_width}")
                # Wait 100 ms for the instrument to store the Level B width
                time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # Record a summary message describing the voltage transient configuration
            self._logger.info(f"Voltage transient configured: {mode}, A={a_level}V, B={b_level}V")
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set voltage transient: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that configures a resistance transient — the load steps between two resistance levels
    def set_resistance_transient(self, mode: str, a_level: float, b_level: float,
                               a_width: Optional[float] = None, b_width: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Configure resistance transient operation

        - VERIFIED: [SOURce:]RESistance:TRANsient commands from manual page 118-119

        Args:
            mode: "CONTinuous", "PULSe", or "TOGGle"
            a_level: Level A resistance in ohms
            b_level: Level B resistance in ohms
            a_width: Level A width in seconds (optional)
            b_width: Level B width in seconds (optional)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set resistance transient: electronic load not connected")
            return False

        # Validate that the requested transient mode is one of the supported types
        if mode not in self._transient_modes:
            # Log an error describing the invalid mode
            self._logger.error(f"Invalid transient mode: {mode}")
            # Return False because the mode is not recognised
            return False

        # Attempt to configure the resistance transient parameters
        try:
            # SCPI: [SOURce:]RESistance:TRANsient:MODE (pg 118)
            # Send the command to set the resistance transient switching pattern
            self._scpi_wrapper.write(f":RESistance:TRANsient:MODE {mode}")
            # Wait 100 ms for the instrument to apply the mode
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # SCPI: [SOURce:]RESistance:TRANsient:ALEVel (pg 118)
            # Send the command to set the Level A resistance value
            self._scpi_wrapper.write(f":RESistance:TRANsient:ALEVel {a_level}")
            # Wait 100 ms for the instrument to store Level A
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # SCPI: [SOURce:]RESistance:TRANsient:BLEVel (pg 118)
            # Send the command to set the Level B resistance value
            self._scpi_wrapper.write(f":RESistance:TRANsient:BLEVel {b_level}")
            # Wait 100 ms for the instrument to store Level B
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # If a Level A duration was provided, set how long the load stays at Level A
            if a_width is not None:
                # SCPI: [SOURce:]RESistance:TRANsient:AWIDth (pg 119)
                # Send the command to set the duration of Level A in seconds
                self._scpi_wrapper.write(f":RESistance:TRANsient:AWIDth {a_width}")
                # Wait 100 ms for the instrument to store the Level A width
                time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # If a Level B duration was provided, set how long the load stays at Level B
            if b_width is not None:
                # SCPI: [SOURce:]RESistance:TRANsient:BWIDth (pg 119)
                # Send the command to set the duration of Level B in seconds
                self._scpi_wrapper.write(f":RESistance:TRANsient:BWIDth {b_width}")
                # Wait 100 ms for the instrument to store the Level B width
                time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # Record a summary message describing the resistance transient configuration
            self._logger.info(f"Resistance transient configured: {mode}, A={a_level}Ω, B={b_level}Ω")
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set resistance transient: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that configures a power transient — the load steps between two power levels
    def set_power_transient(self, mode: str, a_level: float, b_level: float,
                          a_width: Optional[float] = None, b_width: Optional[float] = None) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Configure power transient operation

        - VERIFIED: [SOURce:]POWer:TRANsient commands from manual page 121-122

        Args:
            mode: "CONTinuous", "PULSe", or "TOGGle"
            a_level: Level A power in watts
            b_level: Level B power in watts
            a_width: Level A width in seconds (optional)
            b_width: Level B width in seconds (optional)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set power transient: electronic load not connected")
            return False

        # Validate that the requested transient mode is one of the supported types
        if mode not in self._transient_modes:
            # Log an error describing the invalid mode
            self._logger.error(f"Invalid transient mode: {mode}")
            # Return False because the mode is not recognised
            return False

        # Attempt to configure the power transient parameters
        try:
            # SCPI: [SOURce:]POWer:TRANsient:MODE (pg 121)
            # Send the command to set the power transient switching pattern
            self._scpi_wrapper.write(f":POWer:TRANsient:MODE {mode}")
            # Wait 100 ms for the instrument to apply the mode
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # SCPI: [SOURce:]POWer:TRANsient:ALEVel (pg 122)
            # Send the command to set the Level A power value
            self._scpi_wrapper.write(f":POWer:TRANsient:ALEVel {a_level}")
            # Wait 100 ms for the instrument to store Level A
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # SCPI: [SOURce:]POWer:TRANsient:BLEVel (pg 122)
            # Send the command to set the Level B power value
            self._scpi_wrapper.write(f":POWer:TRANsient:BLEVel {b_level}")
            # Wait 100 ms for the instrument to store Level B
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # If a Level A duration was provided, set how long the load stays at Level A
            if a_width is not None:
                # SCPI: [SOURce:]POWer:TRANsient:AWIDth (pg 122)
                # Send the command to set the duration of Level A in seconds
                self._scpi_wrapper.write(f":POWer:TRANsient:AWIDth {a_width}")
                # Wait 100 ms for the instrument to store the Level A width
                time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # If a Level B duration was provided, set how long the load stays at Level B
            if b_width is not None:
                # SCPI: [SOURce:]POWer:TRANsient:BWIDth (pg 122)
                # Send the command to set the duration of Level B in seconds
                self._scpi_wrapper.write(f":POWer:TRANsient:BWIDth {b_width}")
                # Wait 100 ms for the instrument to store the Level B width
                time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # Record a summary message describing the power transient configuration
            self._logger.info(f"Power transient configured: {mode}, A={a_level}W, B={b_level}W")
            # Return True to indicate success
            return True
        # If any command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set power transient: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # ============================================================================
    # MEASUREMENT FUNCTIONS - VERIFIED AGAINST KEITHLEY 2380 MANUAL
    # ============================================================================

    # Define the method that measures the actual voltage currently at the load's input terminals
    def measure_voltage(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Measure input voltage

        - VERIFIED: MEASure:VOLTage[:DC]? command from manual page 88

        Returns:
            float: Measured voltage in volts or None if error
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot measure voltage: electronic load not connected")
            return None

        # Attempt to measure the actual input voltage
        try:
            # SCPI: MEASure:VOLTage[:DC]? (pg 88)
            # Ask the instrument to measure and return the DC voltage at its input terminals
            response = self._scpi_wrapper.query(":MEASure:VOLTage:DC?").strip()
            # Convert the string response to a floating-point number
            voltage = float(response)
            # Write the measured value to the debug log
            self._logger.debug(f"Measured voltage: {voltage}V")
            # Return the measured voltage to the caller
            return voltage
        # If the measurement fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to measure voltage: {type(e).__name__}: {e}")
            # Return None to indicate the measurement failed
            return None

    # Define the method that measures the actual current currently flowing into the load
    def measure_current(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Measure input current

        - VERIFIED: MEASure:CURRent[:DC]? command from manual page 90

        Returns:
            float: Measured current in amperes or None if error
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot measure current: electronic load not connected")
            return None

        # Attempt to measure the actual input current
        try:
            # SCPI: MEASure:CURRent[:DC]? (pg 90)
            # Ask the instrument to measure and return the DC current flowing into the load
            response = self._scpi_wrapper.query(":MEASure:CURRent:DC?").strip()
            # Convert the string response to a floating-point number
            current = float(response)
            # Write the measured value to the debug log
            self._logger.debug(f"Measured current: {current}A")
            # Return the measured current to the caller
            return current
        # If the measurement fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to measure current: {type(e).__name__}: {e}")
            # Return None to indicate the measurement failed
            return None

    # Define the method that measures the actual power currently being dissipated by the load
    def measure_power(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Measure input power

        - VERIFIED: MEASure:POWer[:DC]? command from manual page 91

        Returns:
            float: Measured power in watts or None if error
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot measure power: electronic load not connected")
            return None

        # Attempt to measure the actual input power
        try:
            # SCPI: MEASure:POWer[:DC]? (pg 91)
            # Ask the instrument to measure and return the DC power being consumed
            response = self._scpi_wrapper.query(":MEASure:POWer:DC?").strip()
            # Convert the string response to a floating-point number
            power = float(response)
            # Write the measured value to the debug log
            self._logger.debug(f"Measured power: {power}W")
            # Return the measured power to the caller
            return power
        # If the measurement fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to measure power: {type(e).__name__}: {e}")
            # Return None to indicate the measurement failed
            return None

    # Define the method that measures the total charge drawn by the load (in ampere-hours) — used in battery testing
    def measure_capability(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Measure discharging capability

        - VERIFIED: MEASure:CAPability? command from manual page 91

        Returns:
            float: Measured discharging capability in ampere-hours or None if error
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot measure capability: electronic load not connected")
            return None

        # Attempt to measure the total charge drawn
        try:
            # SCPI: MEASure:CAPability? (pg 91)
            # Ask the instrument to return the total charge that has been drawn so far
            response = self._scpi_wrapper.query(":MEASure:CAPability?").strip()
            # Convert the string response to a floating-point number
            capability = float(response)
            # Write the measured value to the debug log
            self._logger.debug(f"Measured capability: {capability}Ah")
            # Return the charge value to the caller
            return capability
        # If the measurement fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to measure capability: {type(e).__name__}: {e}")
            # Return None to indicate the measurement failed
            return None

    # Define the method that measures the total time the load has been drawing current (used in battery testing)
    def measure_time(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Measure discharging time

        - VERIFIED: MEASure:TIME? command from manual page 91

        Returns:
            float: Measured discharging time in seconds or None if error
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot measure time: electronic load not connected")
            return None

        # Attempt to measure the total discharge time
        try:
            # SCPI: MEASure:TIME? (pg 91)
            # Ask the instrument to return the total time the load has been active
            response = self._scpi_wrapper.query(":MEASure:TIME?").strip()
            # Convert the string response to a floating-point number
            time_val = float(response)
            # Write the measured value to the debug log
            self._logger.debug(f"Measured time: {time_val}s")
            # Return the time value to the caller
            return time_val
        # If the measurement fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to measure time: {type(e).__name__}: {e}")
            # Return None to indicate the measurement failed
            return None

    # Define the method that reads both the peak-high and peak-low voltages at the load input
    def measure_voltage_max_min(self) -> Optional[Dict[str, float]]:
        # Docstring explaining what this function does and what it returns
        """
        Measure voltage maximum and minimum values

        - VERIFIED: MEASure:VOLTage:MAX/MIN? commands from manual page 89

        Returns:
            dict: {"max": max_voltage, "min": min_voltage} or None if error
        """
        # If the instrument is not connected, there is nothing to measure
        if not self.is_connected:
            return None

        # Attempt to measure both the maximum and minimum voltages
        try:
            # SCPI: MEASure:VOLTage:MAX? (pg 89)
            # Ask the instrument to return the highest voltage seen at the input
            max_response = self._scpi_wrapper.query(":MEASure:VOLTage:MAX?").strip()
            # Convert the maximum voltage string to a float
            max_voltage = float(max_response)
            # [Blank line for visual separation between sections]
            # SCPI: MEASure:VOLTage:MIN? (pg 89)
            # Ask the instrument to return the lowest voltage seen at the input
            min_response = self._scpi_wrapper.query(":MEASure:VOLTage:MIN?").strip()
            # Convert the minimum voltage string to a float
            min_voltage = float(min_response)
            # [Blank line for visual separation between sections]
            # Bundle both values into a labelled dictionary for easy use by the caller
            result = {"max": max_voltage, "min": min_voltage}
            # Write the result to the debug log
            self._logger.debug(f"Voltage max/min: {result}")
            # Return the dictionary containing both values
            return result
        # If any measurement fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to measure voltage max/min: {type(e).__name__}: {e}")
            # Return None to indicate the measurements failed
            return None

    # Define the method that reads both the peak-high and peak-low current values at the load input
    def measure_current_max_min(self) -> Optional[Dict[str, float]]:
        # Docstring explaining what this function does and what it returns
        """
        Measure current maximum and minimum values

        - VERIFIED: MEASure:CURRent:MAX/MIN? commands from manual page 90

        Returns:
            dict: {"max": max_current, "min": min_current} or None if error
        """
        # If the instrument is not connected, there is nothing to measure
        if not self.is_connected:
            return None

        # Attempt to measure both the maximum and minimum currents
        try:
            # SCPI: MEASure:CURRent:MAX? (pg 90)
            # Ask the instrument to return the highest current seen at the input
            max_response = self._scpi_wrapper.query(":MEASure:CURRent:MAX?").strip()
            # Convert the maximum current string to a float
            max_current = float(max_response)
            # [Blank line for visual separation between sections]
            # SCPI: MEASure:CURRent:MIN? (pg 90)
            # Ask the instrument to return the lowest current seen at the input
            min_response = self._scpi_wrapper.query(":MEASure:CURRent:MIN?").strip()
            # Convert the minimum current string to a float
            min_current = float(min_response)
            # [Blank line for visual separation between sections]
            # Bundle both values into a labelled dictionary for easy use by the caller
            result = {"max": max_current, "min": min_current}
            # Write the result to the debug log
            self._logger.debug(f"Current max/min: {result}")
            # Return the dictionary containing both values
            return result
        # If any measurement fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to measure current max/min: {type(e).__name__}: {e}")
            # Return None to indicate the measurements failed
            return None

    # Define the method that runs all available measurements in one call and returns a summary dictionary
    def measure_all(self) -> Optional[Dict[str, float]]:
        # Docstring explaining what this function does and what it returns
        """
        Perform comprehensive measurements

        Returns:
            dict: All measurement values or None if error
        """
        # If the instrument is not connected, there is nothing to measure
        if not self.is_connected:
            return None

        # Create an empty dictionary to collect all measurement results
        measurements = {}
        # [Blank line for visual separation between sections]
        # Store the comment explaining what the basic measurements block covers
        # Basic measurements
        # Measure the actual voltage at the load input
        voltage = self.measure_voltage()
        # If the voltage measurement succeeded, add it to the results dictionary
        if voltage is not None:
            # Store the measured voltage under the key 'voltage'
            measurements['voltage'] = voltage
        # [Blank line for visual separation between sections]
        # Measure the actual current flowing into the load
        current = self.measure_current()
        # If the current measurement succeeded, add it to the results dictionary
        if current is not None:
            # Store the measured current under the key 'current'
            measurements['current'] = current
        # [Blank line for visual separation between sections]
        # Measure the actual power being dissipated by the load
        power = self.measure_power()
        # If the power measurement succeeded, add it to the results dictionary
        if power is not None:
            # Store the measured power under the key 'power'
            measurements['power'] = power
        # [Blank line for visual separation between sections]
        # Measure the total charge drawn (relevant for battery testing)
        capability = self.measure_capability()
        # If the capability measurement succeeded, add it to the results dictionary
        if capability is not None:
            # Store the charge value under the key 'capability'
            measurements['capability'] = capability
        # [Blank line for visual separation between sections]
        # Measure the total time the load has been active
        time_val = self.measure_time()
        # If the time measurement succeeded, add it to the results dictionary
        if time_val is not None:
            # Store the time value under the key 'time'
            measurements['time'] = time_val
        # [Blank line for visual separation between sections]
        # Store the comment explaining the calculated resistance check
        # Calculate resistance if voltage and current available
        # If both voltage and current were measured and current is non-zero, compute resistance
        if voltage is not None and current is not None and current > 0:
            # Calculate resistance using Ohm's Law and add it to the results dictionary
            measurements['resistance'] = voltage / current
        # [Blank line for visual separation between sections]
        # Record all measurements to the log for traceability
        self._logger.info(f"All measurements: {measurements}")
        # Return the dictionary if it has any values, or None if all measurements failed
        return measurements if measurements else None

    # ============================================================================
    # FAST MEASUREMENTS - FETCH COMMANDS
    # ============================================================================

    # Define the method that retrieves a previously triggered voltage reading without starting a new measurement
    def fetch_voltage(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Fetch previously triggered voltage measurement (faster than measure)

        - VERIFIED: FETCh:VOLTage[:DC]? command from manual page 85

        Returns:
            float: Fetched voltage in volts or None if error
        """
        # If the instrument is not connected, there is nothing to fetch
        if not self.is_connected:
            return None

        # Attempt to fetch the most recent voltage reading
        try:
            # SCPI: FETCh:VOLTage[:DC]? (pg 85)
            # Ask the instrument to return the last completed voltage measurement (faster than a fresh measurement)
            response = self._scpi_wrapper.query(":FETCh:VOLTage:DC?").strip()
            # Convert the string response to a floating-point number
            voltage = float(response)
            # Write the fetched value to the debug log
            self._logger.debug(f"Fetched voltage: {voltage}V")
            # Return the fetched voltage to the caller
            return voltage
        # If the fetch fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to fetch voltage: {type(e).__name__}: {e}")
            # Return None to indicate the fetch failed
            return None

    # Define the method that retrieves a previously triggered current reading without starting a new measurement
    def fetch_current(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Fetch previously triggered current measurement (faster than measure)

        - VERIFIED: FETCh:CURRent[:DC]? command from manual page 86

        Returns:
            float: Fetched current in amperes or None if error
        """
        # If the instrument is not connected, there is nothing to fetch
        if not self.is_connected:
            return None

        # Attempt to fetch the most recent current reading
        try:
            # SCPI: FETCh:CURRent[:DC]? (pg 86)
            # Ask the instrument to return the last completed current measurement
            response = self._scpi_wrapper.query(":FETCh:CURRent:DC?").strip()
            # Convert the string response to a floating-point number
            current = float(response)
            # Write the fetched value to the debug log
            self._logger.debug(f"Fetched current: {current}A")
            # Return the fetched current to the caller
            return current
        # If the fetch fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to fetch current: {type(e).__name__}: {e}")
            # Return None to indicate the fetch failed
            return None

    # Define the method that retrieves a previously triggered power reading without starting a new measurement
    def fetch_power(self) -> Optional[float]:
        # Docstring explaining what this function does and what it returns
        """
        Fetch previously triggered power measurement (faster than measure)

        - VERIFIED: FETCh:POWer[:DC]? command from manual page 87

        Returns:
            float: Fetched power in watts or None if error
        """
        # If the instrument is not connected, there is nothing to fetch
        if not self.is_connected:
            return None

        # Attempt to fetch the most recent power reading
        try:
            # SCPI: FETCh:POWer[:DC]? (pg 87)
            # Ask the instrument to return the last completed power measurement
            response = self._scpi_wrapper.query(":FETCh:POWer:DC?").strip()
            # Convert the string response to a floating-point number
            power = float(response)
            # Write the fetched value to the debug log
            self._logger.debug(f"Fetched power: {power}W")
            # Return the fetched power to the caller
            return power
        # If the fetch fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to fetch power: {type(e).__name__}: {e}")
            # Return None to indicate the fetch failed
            return None

    # ============================================================================
    # TRIGGER SYSTEM CONTROL
    # ============================================================================

    # Define the method that selects which signal (bus, external, timer, etc.) will trigger measurements
    def set_trigger_source(self, source: str) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set trigger source

        - VERIFIED: TRIGger:SOURce command from manual page 93

        Args:
            source: "BUS", "EXTernal", "HOLD", "MANUal", or "TIMer"

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set trigger source: electronic load not connected")
            return False

        # Validate that the requested source is one of the supported trigger sources
        if source not in self._trigger_sources:
            # Log an error describing the invalid source
            self._logger.error(f"Invalid trigger source: {source}")
            # Return False because the source is not recognised
            return False

        # Attempt to set the trigger source on the instrument
        try:
            # SCPI: TRIGger:SOURce (pg 93)
            # Send the command to select the trigger source
            self._scpi_wrapper.write(f":TRIGger:SOURce {source}")
            # Wait 100 ms for the instrument to apply the change
            time.sleep(0.1)
            # Record a message confirming the trigger source that was set
            self._logger.info(f"Trigger source set to: {source}")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set trigger source: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that reads back the currently selected trigger source
    def get_trigger_source(self) -> Optional[str]:
        # Docstring explaining what this function does and what it returns
        """
        Query current trigger source

        - VERIFIED: TRIGger:SOURce? query from manual page 93

        Returns:
            str: Current trigger source or None if error
        """
        # If the instrument is not connected, there is nothing to query
        if not self.is_connected:
            return None

        # Attempt to query the current trigger source
        try:
            # SCPI: TRIGger:SOURce? (pg 93)
            # Ask the instrument which trigger source is currently selected
            response = self._scpi_wrapper.query(":TRIGger:SOURce?").strip()
            # Write the current trigger source to the debug log
            self._logger.debug(f"Trigger source: {response}")
            # Return the trigger source string to the caller
            return response
        # If the query fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to query trigger source: {type(e).__name__}: {e}")
            # Return None to indicate the source could not be determined
            return None

    # Define the method that sets how often the internal timer triggers measurements automatically
    def set_trigger_timer(self, period: float) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Set trigger timer period

        - VERIFIED: TRIGger:TIMer command from manual page 94

        Args:
            period: Timer period in seconds (0.01 to 9999.99)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot set trigger timer: electronic load not connected")
            return False

        # Validate that the period is within the allowed range
        if not (0.01 <= period <= 9999.99):
            # Log an error describing the out-of-range value
            self._logger.error(f"Invalid timer period: {period}s (must be 0.01-9999.99)")
            # Return False because the value is out of range
            return False

        # Attempt to set the trigger timer period
        try:
            # SCPI: TRIGger:TIMer (pg 94)
            # Send the command to set how often the internal timer fires a trigger
            self._scpi_wrapper.write(f":TRIGger:TIMer {period}")
            # Wait 100 ms for the instrument to apply the timer period
            time.sleep(0.1)
            # Record a message confirming the period that was set
            self._logger.info(f"Trigger timer period set to: {period}s")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to set trigger timer: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that sends an immediate software trigger to the instrument
    def force_trigger(self) -> bool:
        # Docstring explaining what this function does and what it returns
        """
        Force a trigger event

        - VERIFIED: FORCe:TRIGger command from manual page 92

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot force trigger: electronic load not connected")
            return False

        # Attempt to send a forced trigger to the instrument
        try:
            # SCPI: FORCe:TRIGger (pg 92)
            # Send the command that forces the instrument to trigger immediately, regardless of trigger source
            self._scpi_wrapper.write(":FORCe:TRIGger")
            # Wait 100 ms for the instrument to complete the triggered action
            time.sleep(0.1)
            # Record a message confirming the trigger was forced
            self._logger.info("Trigger forced")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to force trigger: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # ============================================================================
    # PROTECTION AND SAFETY FUNCTIONS
    # ============================================================================

    # Define the method that clears any latched protection faults so the load can operate again
    def clear_protection(self) -> bool:
        # Docstring explaining what this function does and what it returns
        """
        Clear protection latches

        - VERIFIED: [SOURce:]PROTection:CLEar command from manual page 102

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot clear protection: electronic load not connected")
            return False

        # Attempt to clear any latched protection faults
        try:
            # SCPI: [SOURce:]PROTection:CLEar (pg 102)
            # Send the command to reset any protection latch that was triggered
            self._scpi_wrapper.write(":PROTection:CLEar")
            # Wait 500 ms to allow the instrument enough time to clear the protection latch
            time.sleep(0.5)  # Allow time for protection to clear
            # Record a message confirming the protection latches were cleared
            self._logger.info("Protection latches cleared")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to clear protection: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # ============================================================================
    # SYSTEM COMMANDS & UTILITIES
    # ============================================================================

    # Define the method that resets the instrument to its factory default settings
    def reset(self) -> bool:
        # Docstring explaining what this function does and what it returns
        """
        Reset electronic load to default state

        - VERIFIED: *RST command from manual page 71

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot reset: electronic load not connected")
            return False

        # Attempt to reset the instrument to its factory default state
        try:
            # SCPI: *RST (pg 71)
            # Send the standard IEEE-488 reset command to restore all settings to factory defaults
            self._scpi_wrapper.write("*RST")
            # Wait 2 seconds to allow the instrument to complete the reset process
            time.sleep(2.0)  # Allow time for reset
            # Ask the instrument to confirm all reset operations are complete before proceeding
            self._scpi_wrapper.query("*OPC?")
            # Record a message confirming the reset completed
            self._logger.info("Electronic load reset to default state")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to reset: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that runs the instrument's internal self-test routine to check for hardware faults
    def self_test(self) -> Optional[int]:
        # Docstring explaining what this function does and what it returns
        """
        Execute self-test

        - VERIFIED: *TST? command from manual page 72

        Returns:
            int: Test result (0 = passed) or None if error
        """
        # If the instrument is not connected, there is nothing to test
        if not self.is_connected:
            return None

        # Attempt to run the instrument's self-test
        try:
            # SCPI: *TST? (pg 72)
            # Ask the instrument to run its internal diagnostic test and return the result
            response = self._scpi_wrapper.query("*TST?").strip()
            # Convert the result code string to an integer (0 means passed)
            result = int(response)
            # Record a message in the log showing whether the test passed or failed
            self._logger.info(f"Self-test result: {result} ({'PASSED' if result == 0 else 'FAILED'})")
            # Return the integer result code to the caller
            return result
        # If the test fails to run, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to execute self-test: {type(e).__name__}: {e}")
            # Return None to indicate the self-test could not be completed
            return None

    # Define the method that retrieves any error messages waiting in the instrument's error queue
    def get_error_queue(self) -> Optional[List[str]]:
        # Docstring explaining what this function does and what it returns
        """
        Query instrument error queue

        - VERIFIED: :SYStem:ERRor? command referenced in manual

        Returns:
            List of error strings or None
        """
        # If the instrument is not connected, there is nothing to query
        if not self.is_connected:
            return None

        # Attempt to read all errors from the instrument's error queue
        try:
            # Create an empty list to hold the error messages
            errors = []
            # Keep reading errors until the queue is empty
            while True:
                # Query error queue until empty (0,"No error" response)
                # Ask the instrument for the next error in its queue
                error = self._scpi_wrapper.query(":SYStem:ERRor?").strip()
                # If the response starts with "0," it means no more errors — stop the loop
                if error.startswith("0,"):
                    break
                # Otherwise, add the error string to the list
                errors.append(error)
                # Safety limit to prevent infinite loop
                # If somehow we receive more than 100 errors, stop to avoid being stuck forever
                if len(errors) > 100:
                    break

            # If any errors were found, log them as warnings
            if errors:
                self._logger.warning(f"Instrument errors: {errors}")
                # Return the list of error strings
                return errors
            # If no errors were found, return None
            return None
        # If the query fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to get error queue: {type(e).__name__}: {e}")
            # Return None to indicate the error queue could not be read
            return None

    # Define the method that saves the current instrument configuration to a numbered memory slot
    def save_setup(self, location: int) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Save current setup to non-volatile memory

        - VERIFIED: *SAV command from manual page 72

        Args:
            location: Memory location (0-100)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot save setup: electronic load not connected")
            return False

        # Validate that the memory location number is within the allowed range
        if not (0 <= location <= 100):
            # Log an error describing the invalid location
            self._logger.error(f"Invalid memory location: {location} (must be 0-100)")
            # Return False because the location is out of range
            return False

        # Attempt to save the current settings to the specified memory location
        try:
            # SCPI: *SAV (pg 72)
            # Send the command to store the current setup in the specified non-volatile memory slot
            self._scpi_wrapper.write(f"*SAV {location}")
            # Wait 500 ms for the instrument to write the settings to memory
            time.sleep(0.5)
            # Ask the instrument to confirm the save is complete
            self._scpi_wrapper.query("*OPC?")
            # Record a message confirming the memory location used
            self._logger.info(f"Setup saved to location: {location}")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to save setup: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that restores a previously saved instrument configuration from a numbered memory slot
    def recall_setup(self, location: int) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Recall setup from non-volatile memory

        - VERIFIED: *RCL command from manual page 71

        Args:
            location: Memory location (0-100)

        Returns:
            bool: True if successful
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot recall setup: electronic load not connected")
            return False

        # Validate that the memory location number is within the allowed range
        if not (0 <= location <= 100):
            # Log an error describing the invalid location
            self._logger.error(f"Invalid memory location: {location} (must be 0-100)")
            # Return False because the location is out of range
            return False

        # Attempt to restore the settings from the specified memory location
        try:
            # SCPI: *RCL (pg 71)
            # Send the command to load the settings previously saved in the specified memory slot
            self._scpi_wrapper.write(f"*RCL {location}")
            # Wait 500 ms for the instrument to restore the settings from memory
            time.sleep(0.5)
            # Ask the instrument to confirm the recall is complete
            self._scpi_wrapper.query("*OPC?")
            # Record a message confirming the memory location recalled from
            self._logger.info(f"Setup recalled from location: {location}")
            # Return True to indicate success
            return True
        # If the command fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to recall setup: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # Define the method that blocks execution until the instrument reports all pending operations are complete
    def wait_for_operation_complete(self, timeout: float = 30.0) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Wait for operation to complete

        - VERIFIED: *OPC? command from manual page 69

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            bool: True if operation completed, False if timeout
        """
        # If the instrument is not connected, log an error and stop
        if not self.is_connected:
            self._logger.error("Cannot wait for operation: electronic load not connected")
            return False

        # Record the time at which waiting begins so we can detect a timeout
        start_time = time.time()
        # Attempt to poll the instrument until it confirms completion or the timeout expires
        try:
            # Keep polling while the elapsed time is within the allowed timeout
            while time.time() - start_time < timeout:
                # SCPI: *OPC? (pg 69)
                # Ask the instrument whether all pending operations are complete; "1" means yes
                response = self._scpi_wrapper.query("*OPC?").strip()
                # If the instrument confirms completion, log it and return success
                if response == "1":
                    self._logger.info("Operation completed")
                    return True
                # Wait 100 ms before polling again to avoid flooding the instrument with queries
                time.sleep(0.1)

            # If we exit the loop, the timeout was reached without completion — log a warning
            self._logger.warning(f"Operation timeout after {timeout}s")
            # Return False to indicate the operation did not complete within the allowed time
            return False
        # If the polling fails, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed waiting for operation: {type(e).__name__}: {e}")
            # Return False to signal failure
            return False

    # ============================================================================
    # CONVENIENCE METHODS - HIGH-LEVEL OPERATIONS
    # ============================================================================

    # Define a helper method that configures the load for constant-current operation in a single call
    def quick_cc_setup(self, current: float, enable: bool = True) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Quick setup for constant current mode

        Args:
            current: Current level in amperes
            enable: Enable input after setup

        Returns:
            bool: True if successful
        """
        # Attempt to configure the load for constant-current mode
        try:
            # Store the comment explaining this step
            # Set to CC mode
            # Switch the load to constant-current operating mode
            if not self.set_function("CURRent"):
                # If switching modes failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Store the comment explaining this step
            # Set current level
            # Set the desired current draw level
            if not self.set_current_level(current):
                # If setting the current level failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Store the comment explaining this step
            # Enable input if requested
            # If the caller requested the load to be turned on after setup, enable the input
            if enable and not self.enable_input():
                # If enabling the input failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Record a message confirming the quick setup completed successfully
            self._logger.info(f"Quick CC setup complete: {current}A, enabled={enable}")
            # Return True to indicate all steps succeeded
            return True
        # If any step throws an exception, catch it
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Quick CC setup failed: {e}")
            # Return False to signal failure
            return False

    # Define a helper method that configures the load for constant-voltage operation in a single call
    def quick_cv_setup(self, voltage: float, enable: bool = True) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Quick setup for constant voltage mode

        Args:
            voltage: Voltage level in volts
            enable: Enable input after setup

        Returns:
            bool: True if successful
        """
        # Attempt to configure the load for constant-voltage mode
        try:
            # Store the comment explaining this step
            # Set to CV mode
            # Switch the load to constant-voltage operating mode
            if not self.set_function("VOLTage"):
                # If switching modes failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Store the comment explaining this step
            # Set voltage level
            # Set the desired regulated voltage level
            if not self.set_voltage_level(voltage):
                # If setting the voltage level failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Store the comment explaining this step
            # Enable input if requested
            # If the caller requested the load to be turned on after setup, enable the input
            if enable and not self.enable_input():
                # If enabling the input failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Record a message confirming the quick setup completed successfully
            self._logger.info(f"Quick CV setup complete: {voltage}V, enabled={enable}")
            # Return True to indicate all steps succeeded
            return True
        # If any step throws an exception, catch it
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Quick CV setup failed: {e}")
            # Return False to signal failure
            return False

    # Define a helper method that configures the load for constant-resistance operation in a single call
    def quick_cr_setup(self, resistance: float, enable: bool = True) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Quick setup for constant resistance mode

        Args:
            resistance: Resistance level in ohms
            enable: Enable input after setup

        Returns:
            bool: True if successful
        """
        # Attempt to configure the load for constant-resistance mode
        try:
            # Store the comment explaining this step
            # Set to CR mode
            # Switch the load to constant-resistance operating mode
            if not self.set_function("RESistance"):
                # If switching modes failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Store the comment explaining this step
            # Set resistance level
            # Set the desired simulated resistance value
            if not self.set_resistance_level(resistance):
                # If setting the resistance level failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Store the comment explaining this step
            # Enable input if requested
            # If the caller requested the load to be turned on after setup, enable the input
            if enable and not self.enable_input():
                # If enabling the input failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Record a message confirming the quick setup completed successfully
            self._logger.info(f"Quick CR setup complete: {resistance}Ω, enabled={enable}")
            # Return True to indicate all steps succeeded
            return True
        # If any step throws an exception, catch it
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Quick CR setup failed: {e}")
            # Return False to signal failure
            return False

    # Define a helper method that configures the load for constant-power operation in a single call
    def quick_cp_setup(self, power: float, enable: bool = True) -> bool:
        # Docstring explaining what this function does, its parameters, and what it returns
        """
        Quick setup for constant power mode

        Args:
            power: Power level in watts
            enable: Enable input after setup

        Returns:
            bool: True if successful
        """
        # Attempt to configure the load for constant-power mode
        try:
            # Store the comment explaining this step
            # Set to CP mode
            # Switch the load to constant-power operating mode
            if not self.set_function("POWer"):
                # If switching modes failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Store the comment explaining this step
            # Set power level
            # Set the desired power dissipation level
            if not self.set_power_level(power):
                # If setting the power level failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Store the comment explaining this step
            # Enable input if requested
            # If the caller requested the load to be turned on after setup, enable the input
            if enable and not self.enable_input():
                # If enabling the input failed, return False immediately
                return False
            # [Blank line for visual separation between sections]
            # Record a message confirming the quick setup completed successfully
            self._logger.info(f"Quick CP setup complete: {power}W, enabled={enable}")
            # Return True to indicate all steps succeeded
            return True
        # If any step throws an exception, catch it
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Quick CP setup failed: {e}")
            # Return False to signal failure
            return False

    # Define the method that performs a controlled safe shutdown of the electronic load
    def safe_shutdown(self) -> bool:
        # Docstring explaining what this function does and what it returns
        """
        Safely shutdown the electronic load

        Returns:
            bool: True if successful
        """
        # Attempt to execute each shutdown step in sequence
        try:
            # Store the comment explaining this step
            # Disable input first
            # Turn the load input off to stop drawing current from the power supply
            if not self.disable_input():
                # Log a warning if this step fails but continue with the rest of the shutdown
                self._logger.warning("Failed to disable input during shutdown")
            # [Blank line for visual separation between sections]
            # Store the comment explaining this step
            # Disable transient generator if active
            # Turn off the transient generator to stop any dynamic load-stepping that may be running
            if not self.enable_transient(False):
                # Log a warning if this step fails but continue
                self._logger.warning("Failed to disable transient during shutdown")
            # [Blank line for visual separation between sections]
            # Store the comment explaining this step
            # Clear any protection latches
            # Reset any latched fault conditions so the load can start cleanly next time
            if not self.clear_protection():
                # Log a warning if this step fails but continue
                self._logger.warning("Failed to clear protection during shutdown")
            # [Blank line for visual separation between sections]
            # Record a message confirming the safe shutdown completed
            self._logger.info("Electronic load safely shut down")
            # Return True to indicate success
            return True
        # If any step throws an unexpected exception, catch it
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Safe shutdown failed: {e}")
            # Return False to signal failure
            return False

    # Define the method that collects all current instrument settings and measurements into a single status report
    def get_status_summary(self) -> Optional[Dict[str, Any]]:
        # Docstring explaining what this function does and what it returns
        """
        Get comprehensive status summary

        Returns:
            dict: Complete status information or None if error
        """
        # If the instrument is not connected, there is nothing to report
        if not self.is_connected:
            return None

        # Attempt to collect all status information
        try:
            # Create an empty dictionary to hold all status fields
            status = {}
            # [Blank line for visual separation between sections]
            # Store the comment explaining this block
            # Basic information
            # Retrieve the instrument identification and hardware specification details
            info = self.get_instrument_info()
            # If the info was retrieved successfully, add it to the status report
            if info:
                status['instrument'] = info
            # [Blank line for visual separation between sections]
            # Store the comment explaining this block
            # Input state
            # Check whether the load input is currently on or off
            input_state = self.get_input_state()
            # If the state was read successfully, add it to the status report
            if input_state is not None:
                status['input_enabled'] = input_state
            # [Blank line for visual separation between sections]
            # Store the comment explaining this block
            # Current operation mode
            # Query which operating mode (CC, CV, CR, or CP) is currently active
            function = self.get_function()
            # If the mode was read successfully, add it to the status report
            if function:
                status['operation_mode'] = function
            # [Blank line for visual separation between sections]
            # Store the comment explaining this block
            # Current settings based on mode
            # Depending on the active mode, read the corresponding setpoint level
            if function == "CURR":
                # If the load is in constant-current mode, read the current setpoint
                level = self.get_current_level()
                # If the setpoint was read successfully, add it to the status report
                if level is not None:
                    status['current_level'] = level
            elif function == "VOLT":
                # If the load is in constant-voltage mode, read the voltage setpoint
                level = self.get_voltage_level()
                # If the setpoint was read successfully, add it to the status report
                if level is not None:
                    status['voltage_level'] = level
            elif function == "RES":
                # If the load is in constant-resistance mode, read the resistance setpoint
                level = self.get_resistance_level()
                # If the setpoint was read successfully, add it to the status report
                if level is not None:
                    status['resistance_level'] = level
            elif function == "POW":
                # If the load is in constant-power mode, read the power setpoint
                level = self.get_power_level()
                # If the setpoint was read successfully, add it to the status report
                if level is not None:
                    status['power_level'] = level
            # [Blank line for visual separation between sections]
            # Store the comment explaining this block
            # Current measurements
            # Perform all available measurements (voltage, current, power, etc.)
            measurements = self.measure_all()
            # If any measurements succeeded, add them to the status report
            if measurements:
                status['measurements'] = measurements
            # [Blank line for visual separation between sections]
            # Store the comment explaining this block
            # Trigger source
            # Read which trigger source is currently selected
            trigger_source = self.get_trigger_source()
            # If the trigger source was read successfully, add it to the status report
            if trigger_source:
                status['trigger_source'] = trigger_source
            # [Blank line for visual separation between sections]
            # Store the comment explaining this block
            # Error queue
            # Check the instrument's error queue for any pending faults
            errors = self.get_error_queue()
            # If any errors were found, add them to the status report
            if errors:
                # Store the list of error messages under the key 'errors'
                status['errors'] = errors
            # [Blank line for visual separation between sections]
            # Return the fully populated status dictionary
            return status
        # If anything goes wrong during the status collection, catch the error
        except Exception as e:
            # Record the error in the log
            self._logger.error(f"Failed to get status summary: {e}")
            # Return None to indicate the status could not be collected
            return None
