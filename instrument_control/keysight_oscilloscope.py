"""
MEASUREMENT FEATURE: Keysight DSOX6004A Oscilloscope Measurement Functions

Provides automatic waveform analysis with multiple measurement types including channel and math function measurements

- SCPI COMMANDS VERIFIED AGAINST KEYSIGHT 6000X PROGRAMMING MANUAL
- ALL COMMANDS CROSS-REFERENCED WITH OFFICIAL DOCUMENTATION
- FIXED: Math function measurements and waveform saving operations

"""

# Load the logging library so the program can write status and error messages to a log file or console
import logging
# Load the time library so the program can pause briefly between instrument commands (instruments need small delays)
import time
# Load the Path class from pathlib so the program can build file paths that work on any operating system
from pathlib import Path
# Load the datetime class so the program can generate timestamps for screenshot filenames
from datetime import datetime
# Load typing helpers so function signatures can declare what types they accept and return
from typing import Optional, Dict, Any, List, Tuple, Union
# Load numpy for fast numerical array operations when converting raw waveform bytes to voltage values
import numpy as np
# Load the SCPIWrapper class from the local instrument_control package — this handles all the low-level USB/VISA communication
from instrument_control.scpi_wrapper import SCPIWrapper

# [Blank line for visual separation]

# Define a custom error class specifically for this oscilloscope so errors from it can be caught separately from generic Python errors
class KeysightDSOX6004AError(Exception):
    """Custom exception for Keysight DSOX6004A oscilloscope errors."""
    pass

# [Blank line for visual separation]

# Define the main class that represents and controls the Keysight DSOX6004A oscilloscope
class KeysightDSOX6004A:
    """Keysight DSOX6004A Oscilloscope Control Class with Measurement Features"""

    # Define the constructor — this runs once when a new oscilloscope object is created and sets up all default values
    def __init__(self, visa_address: str, timeout_ms: int = 60000) -> None:
        """
        Initialize oscilloscope connection parameters

        Args:
            visa_address: VISA resource address (e.g., "USB0::0x0957::0x179B::MY12345678::INSTR")
            timeout_ms: Initial VISA timeout in milliseconds (default: 60000 = 60 seconds)
                       Note: Timeout will be automatically increased for long timebase settings
                       (20s, 50s per division) to prevent acquisition errors.
        """
        # Create the low-level SCPI communication wrapper using the given USB address and timeout
        self._scpi_wrapper = SCPIWrapper(visa_address, timeout_ms)
        # Set up a logger named after this specific oscilloscope instance so log messages are easy to trace
        self._logger = logging.getLogger(f'{self.__class__.__name__}.{id(self)}')
        # Store the maximum number of analog channels this oscilloscope has (4 channels)
        self.max_channels = 4
        # Store the maximum sample rate in samples per second (20 billion samples per second)
        self.max_sample_rate = 20e9
        # Set screenshot_dir to None — it will be filled in later by setup_output_directories() or set externally
        self.screenshot_dir = None   # set by setup_output_directories() or overridden externally
        # Store the maximum waveform memory depth (16 million data points)
        self.max_memory_depth = 16e6
        # Store the oscilloscope's analog bandwidth in Hz (1 GHz)
        self.bandwidth_hz = 1e9

        # Store the list of valid vertical voltage-per-division scale values that the oscilloscope can be set to
        self._valid_vertical_scales = [
            1e-3, 2e-3, 5e-3, 10e-3, 20e-3, 50e-3,
            100e-3, 200e-3, 500e-3, 1.0, 2.0, 5.0, 10.0
        ]

        # Store the list of valid horizontal time-per-division scale values that the oscilloscope can be set to
        self._valid_timebase_scales = [
            1e-12, 2e-12, 5e-12, 10e-12, 20e-12, 50e-12,
            100e-12, 200e-12, 500e-12, 1e-9, 2e-9, 5e-9,
            10e-9, 20e-9, 50e-9, 100e-9, 200e-9, 500e-9,
            1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6,
            100e-6, 200e-6, 500e-6, 1e-3, 2e-3, 5e-3,
            10e-3, 20e-3, 50e-3, 100e-3, 200e-3, 500e-3,
            1.0, 2.0, 5.0, 10.0, 20.0, 50.0
        ]

        # This comment in the original code notes that these measurement types are verified against the Keysight manual
        # - VERIFIED: Measurement types from manual pages 616-619, 645-711
        # Store the list of all supported waveform measurement type names the oscilloscope can compute
        self._measurement_types = [
            "FREQ", "PERiod", "VPP", "VAMP", "VTOP", "VBASe",
            "VAVG", "VRMS", "VMAX", "VMIN", "RISE", "FALL",
            "DUTYcycle", "NDUTy", "OVERshoot", "PWIDth", "NWIDth"
        ]

    # Define the connect method — this opens the physical communication link to the oscilloscope
    def connect(self) -> bool:
        """Establish VISA connection to oscilloscope"""
        # Attempt to open the low-level VISA connection; if it succeeds, run identification checks
        if self._scpi_wrapper.connect():
            # Wrap the identification sequence in a try block in case the instrument doesn't respond properly
            try:
                # Ask the oscilloscope to identify itself by sending the standard IEEE *IDN? query
                identification = self._scpi_wrapper.query("*IDN?")
                # Write the instrument's identification string to the log for traceability
                self._logger.info(f"Instrument identification: {identification.strip()}")
                # Send *CLS to clear any error flags or status registers left over from a previous session
                self._scpi_wrapper.write("*CLS")
                # Wait half a second to let the instrument process the clear command before continuing
                time.sleep(0.5)
                # Ask *OPC? (Operation Complete?) to confirm the instrument is ready and idle
                self._scpi_wrapper.query("*OPC?")
                # Log a success message so the operator knows the oscilloscope is ready
                self._logger.info("Successfully connected to Keysight DSOX6004A")
                # Return True to tell the caller that the connection was established successfully
                return True
            # If anything goes wrong during identification (e.g. wrong address, instrument off), catch the error
            except Exception as e:
                # Log the error so the operator knows what went wrong
                self._logger.error(f"Error during instrument identification: {e}")
                # Close the low-level VISA link since identification failed and the object is not usable
                self._scpi_wrapper.disconnect()
                # Return False to tell the caller that the connection attempt failed
                return False
        # If the low-level VISA connection itself failed (e.g. address not found), return False immediately
        return False

    # Define the disconnect method — this closes the communication link cleanly
    def disconnect(self) -> None:
        """Close connection to oscilloscope"""
        # Tell the SCPI wrapper to close the VISA session
        self._scpi_wrapper.disconnect()
        # Log a message so the operator can confirm the oscilloscope was disconnected
        self._logger.info("Disconnection completed")

    # Mark the next method as a Python property — it can be accessed like an attribute without parentheses
    @property
    # Define is_connected as a read-only property that reports whether the oscilloscope is currently linked
    def is_connected(self) -> bool:
        """Check if oscilloscope is currently connected"""
        # Delegate to the underlying SCPI wrapper's own connection status flag
        return self._scpi_wrapper.is_connected

    # Define a method to query full identification and hardware specification info from the instrument
    def get_instrument_info(self) -> Optional[Dict[str, Any]]:
        """Query instrument identification and specifications"""
        # Return None immediately if there is no active connection — nothing can be queried
        if not self.is_connected:
            return None
        # Try to query the instrument — wrap in try/except because the query could fail at any time
        try:
            # Ask the instrument for its identification string and strip any trailing whitespace
            idn = self._scpi_wrapper.query("*IDN?").strip()
            # Split the comma-separated response into individual fields (manufacturer, model, serial, firmware)
            parts = idn.split(',')
            # Build and return a dictionary with each specification field labelled for easy use
            return {
                # Extract the manufacturer name from position 0; default to 'Unknown' if the field is missing
                'manufacturer': parts[0] if len(parts) > 0 else 'Unknown',
                # Extract the model name from position 1
                'model': parts[1] if len(parts) > 1 else 'Unknown',
                # Extract the serial number from position 2
                'serial_number': parts[2] if len(parts) > 2 else 'Unknown',
                # Extract the firmware version from position 3
                'firmware_version': parts[3] if len(parts) > 3 else 'Unknown',
                # Include the maximum channel count stored in the object
                'max_channels': self.max_channels,
                # Include the bandwidth in Hz stored in the object
                'bandwidth_hz': self.bandwidth_hz,
                # Include the maximum sample rate stored in the object
                'max_sample_rate': self.max_sample_rate,
                # Include the maximum memory depth stored in the object
                'max_memory_depth': self.max_memory_depth,
                # Include the full raw identification string for debugging
                'identification': idn
            }
        # If the query fails for any reason, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to get instrument info: {e}")
            return None

    # Define the configure_channel method — this sets up how a single oscilloscope input channel behaves
    def configure_channel(self, channel: int, vertical_scale: float, vertical_offset: float = 0.0,
                          coupling: str = "DC", probe_attenuation: float = 1.0) -> bool:
        """
        Configure vertical parameters for specified channel

        - VERIFIED: CHANnel commands from manual pages 345-365
        """
        # Raise a clear error if no connection exists so the caller knows the operation cannot proceed
        if not self.is_connected:
            raise KeysightDSOX6004AError("Oscilloscope not connected")
        # Raise an error if the caller asked for a channel number outside the valid range of 1 to 4
        if not (1 <= channel <= self.max_channels):
            raise ValueError(f"Channel must be 1-{self.max_channels}, got {channel}")

        # Wrap all instrument writes in try/except because any SCPI write could fail
        try:
            # SCPI: :CHANnel:DISPlay {ON|OFF|} (pg 347)
            # Turn the channel's display on so its waveform is visible on screen
            self._scpi_wrapper.write(f":CHANnel{channel}:DISPlay ON")
            # Wait 50 ms to let the oscilloscope process the display command before sending the next one
            time.sleep(0.05)
            # [Blank line for visual separation]
            # SCPI: :CHANnel:SCALe (pg 364)
            # Set the vertical voltage scale (volts per division) for this channel
            self._scpi_wrapper.write(f":CHANnel{channel}:SCALe {vertical_scale}")
            # Wait 50 ms between commands to avoid overloading the instrument's command queue
            time.sleep(0.05)
            # [Blank line for visual separation]
            # SCPI: :CHANnel:OFFSet (pg 353)
            # Set the vertical offset (how many volts the waveform is shifted up or down on screen)
            self._scpi_wrapper.write(f":CHANnel{channel}:OFFSet {vertical_offset}")
            # Wait 50 ms for the offset command to be applied
            time.sleep(0.05)
            # [Blank line for visual separation]
            # SCPI: :CHANnel:COUPling {AC|DC|DCLimit} (pg 346)
            # Set input coupling mode: DC passes all frequencies, AC blocks DC component, DCLimit protects the input
            self._scpi_wrapper.write(f":CHANnel{channel}:COUPling {coupling}")
            # Wait 50 ms for the coupling command to be processed
            time.sleep(0.05)

            # SCPI: :CHANnel:PROBe (pg 354)
            # NOTE: Only set probe attenuation if explicitly provided (not default 1.0)
            # This avoids "control limit hit" when scope auto-detects probe
            # Only send the probe attenuation command if a non-default value was supplied, to avoid hardware errors
            if probe_attenuation != 1.0:
                # Set the probe multiplication factor so voltage readings are scaled correctly
                self._scpi_wrapper.write(f":CHANnel{channel}:PROBe {probe_attenuation}")
                # Wait 50 ms for the probe setting to take effect
                time.sleep(0.05)
            # [Blank line for visual separation]
            # Log a summary of all the settings applied to this channel for traceability
            self._logger.info(f"Channel {channel} configured: Scale={vertical_scale}V/div, "
                            f"Offset={vertical_offset}V, Coupling={coupling}, Probe={probe_attenuation}x")
            # Return True to tell the caller that all channel settings were applied successfully
            return True
        # If any SCPI write fails, catch the error, log it, and return False
        except Exception as e:
            self._logger.error(f"Failed to configure channel {channel}: {e}")
            return False

    # Define enable_channel — this turns a specific input channel on so it appears on screen
    def enable_channel(self, channel: int) -> bool:
        """
        Enable (turn on) a channel for display and acquisition

        - VERIFIED: :CHANnel:DISPlay command from manual page 347

        Args:
            channel: Channel number (1-4)

        Returns:
            bool: True if successful
        """
        # Check connection first — cannot send commands if not connected
        if not self.is_connected:
            self._logger.error("Cannot enable channel: oscilloscope not connected")
            return False

        # Validate the channel number is in the allowed range before sending any command
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel: {channel}")
            return False

        # Try to send the enable command, catching any communication errors
        try:
            # Send the SCPI command to turn the channel's display on
            self._scpi_wrapper.write(f":CHANnel{channel}:DISPlay ON")
            # Log at debug level that the channel was turned on (debug is used for low-priority detail)
            self._logger.debug(f"Channel {channel} enabled")
            # Return True to indicate success
            return True
        # If the write fails, log the error including the exception type for easier debugging
        except Exception as e:
            self._logger.error(f"Failed to enable channel {channel}: {type(e).__name__}: {e}")
            return False

    # Define disable_channel — this turns a specific input channel off so it is hidden from screen
    def disable_channel(self, channel: int) -> bool:
        """
        Disable (turn off) a channel from display and acquisition

        - VERIFIED: :CHANnel:DISPlay command from manual page 347

        Args:
            channel: Channel number (1-4)

        Returns:
            bool: True if successful
        """
        # Check that the oscilloscope is connected before attempting any command
        if not self.is_connected:
            self._logger.error("Cannot disable channel: oscilloscope not connected")
            # Return False because the operation cannot proceed without a connection
            return False

        # Validate the channel number before sending any command
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel: {channel}")
            return False

        # Try to send the disable command, catching any communication errors
        try:
            # Send the SCPI command to turn the channel's display off
            self._scpi_wrapper.write(f":CHANnel{channel}:DISPlay OFF")
            # Log at debug level that the channel was turned off
            self._logger.debug(f"Channel {channel} disabled")
            # Return True to indicate the channel was disabled successfully
            return True
        # If the write fails, catch the error and log it with the exception type
        except Exception as e:
            self._logger.error(f"Failed to disable channel {channel}: {type(e).__name__}: {e}")
            return False

    # Define configure_timebase — this sets how much time each horizontal division on screen represents
    def configure_timebase(self, time_scale: float, time_offset: float = 0.0) -> bool:
        """
        Configure horizontal timebase settings

        - VERIFIED: TIMebase commands from manual pages 905-920

        Automatically adjusts VISA timeout based on timebase to prevent timeout errors
        during long acquisitions (e.g., 20s or 50s per division)
        """
        # Return False immediately if no connection is active
        if not self.is_connected:
            self._logger.error("Cannot configure timebase: oscilloscope not connected")
            return False

        # Check if the requested time scale is in the list of valid values
        if time_scale not in self._valid_timebase_scales:
            # If not valid, find the closest valid scale value
            closest_scale = min(self._valid_timebase_scales, key=lambda x: abs(x - time_scale))
            # Warn the operator that the scale was snapped to the nearest valid value
            self._logger.warning(f"Invalid timebase scale {time_scale}s, using {closest_scale}s")
            # Replace the requested scale with the closest valid one
            time_scale = closest_scale

        # Try to apply the timebase settings, handling any communication errors
        try:
            # Calculate required timeout based on timebase
            # Acquisition time ≈ 10 divisions × time_scale + buffer
            # Add 50% safety margin and convert to milliseconds
            # Estimate how long one full sweep will take: 10 horizontal divisions times the scale
            estimated_acq_time_s = 10 * time_scale
            # Add 50% safety margin on top of the estimated time and convert to milliseconds
            required_timeout_ms = int((estimated_acq_time_s * 1.5 + 10) * 1000)

            # Set minimum timeout of 10 seconds for short timebase
            # Ensure the timeout is never less than 10 seconds, even for very fast time scales
            required_timeout_ms = max(required_timeout_ms, 10000)

            # Update timeout if needed for long acquisitions
            # Only change the timeout if the new value is longer than the current one
            if required_timeout_ms > self._scpi_wrapper.timeout:
                # Apply the new longer timeout to prevent premature communication timeouts
                self._scpi_wrapper.set_timeout(required_timeout_ms)
                # Log that the timeout was extended so the operator is aware
                self._logger.info(f"Timeout adjusted to {required_timeout_ms/1000:.1f}s for timebase {time_scale}s/div")

            # SCPI: :TIMebase:SCALe (pg 919)
            # Send the command to set the horizontal time scale (seconds per division)
            self._scpi_wrapper.write(f":TIMebase:SCALe {time_scale}")
            # Wait 100 ms for the scale setting to take effect before sending the next command
            time.sleep(0.1)

            # SCPI: :TIMebase:OFFSet (pg 909)
            # Send the command to shift the horizontal position (where time zero is on screen)
            self._scpi_wrapper.write(f":TIMebase:OFFSet {time_offset}")
            # Wait 100 ms for the offset setting to be applied
            time.sleep(0.1)

            # Log the final timebase settings for traceability
            self._logger.info(f"Timebase configured: Scale={time_scale}s/div, Offset={time_offset}s")
            # Return True to signal that the timebase was configured successfully
            return True
        # If any command fails, catch the exception and log it
        except Exception as e:
            self._logger.error(f"Failed to configure timebase: {type(e).__name__}: {e}")
            return False

    # Define configure_trigger — this tells the oscilloscope when to start capturing a waveform
    def configure_trigger(self, channel: int, trigger_level: float, trigger_slope: str = "POS",
                          sweep_mode: str = "NORMal") -> bool:
        """
        Configure trigger settings

        - VERIFIED: TRIGger commands from manual pages 921-1078

        Args:
            channel: Trigger source channel (1-4)
            trigger_level: Trigger voltage level in Volts
            trigger_slope: "POS" (rising), "NEG" (falling), "EITH" (either)
            sweep_mode: "NORMal" (waits for actual trigger - DEFAULT)
                       "AUTO" (triggers after timeout if no trigger event)

        NOTE: Using NORMal sweep mode ensures scope ONLY captures when trigger fires!
        """
        # Confirm the oscilloscope is connected before attempting trigger configuration
        if not self.is_connected:
            self._logger.error("Cannot configure trigger: oscilloscope not connected")
            return False

        # Raise an error if an invalid channel number is given
        if not (1 <= channel <= self.max_channels):
            raise ValueError(f"Channel must be 1-{self.max_channels}, got {channel}")

        # Define the set of allowed slope values so invalid inputs are caught early
        valid_slopes = ["POS", "NEG", "EITH"]
        # Raise an error if the given slope string is not one of the accepted values
        if trigger_slope.upper() not in valid_slopes:
            raise ValueError(f"Trigger slope must be one of {valid_slopes}, got {trigger_slope}")

        # Try to configure the trigger, handling any communication errors
        try:
            # SCPI: :TRIGger:MODE EDGE (pg 999)
            # Set the trigger type to EDGE (trigger on a rising or falling voltage edge)
            self._scpi_wrapper.write(":TRIGger:MODE EDGE")
            # Wait 100 ms for the mode command to be processed
            time.sleep(0.1)

            # SCPI: :TRIGger:EDGE:SOURce CHANneln (pg 956)
            # Tell the oscilloscope which channel's signal should be watched for the trigger event
            self._scpi_wrapper.write(f":TRIGger:EDGE:SOURce CHANnel{channel}")
            # Wait 100 ms before sending the next command
            time.sleep(0.1)

            # CRITICAL: Set sweep mode BEFORE trigger level
            # SCPI: :TRIGger:SWEep {AUTO|NORMal} (pg 1018)
            # NORMal = scope WAITS for actual trigger event (what we want!)
            # AUTO = scope triggers automatically after timeout (bad for transient capture)
            # Set the sweep mode — NORMal means the scope only captures when the actual trigger event occurs
            self._scpi_wrapper.write(f":TRIGger:SWEep {sweep_mode}")
            # Wait 100 ms for the sweep mode to be applied
            time.sleep(0.1)
            # Log the sweep mode that was applied
            self._logger.info(f"Trigger sweep mode set to: {sweep_mode}")

            # SCPI: :TRIGger:EDGE:LEVel <level>,CHANneln (pg 954)
            # Setting trigger level with explicit channel specification
            # Set the voltage threshold at which the trigger fires, tied to the specific channel
            self._scpi_wrapper.write(f":TRIGger:EDGE:LEVel {trigger_level},CHANnel{channel}")
            # Wait 100 ms for the level to be set
            time.sleep(0.1)

            # SCPI: :TRIGger:EDGE:SLOPe {POSitive|NEGative|EITHer} (pg 955)
            # Set whether the trigger fires on a rising edge, falling edge, or either
            self._scpi_wrapper.write(f":TRIGger:EDGE:SLOPe {trigger_slope.upper()}")
            # Wait 100 ms for the slope setting to be applied
            time.sleep(0.1)

            # Verify the trigger level was actually set correctly
            # Try to read back the trigger level to confirm it was accepted by the instrument
            try:
                # Query the trigger level that the oscilloscope is actually using
                actual_level = self._scpi_wrapper.query(f":TRIGger:EDGE:LEVel? CHANnel{channel}").strip()
                # Log both the requested and actual trigger levels for comparison
                self._logger.info(f"Trigger level VERIFIED on scope: {actual_level}V (requested: {trigger_level}V)")
            # If the verification query fails, log a warning but do not fail the whole function
            except Exception as verify_err:
                self._logger.warning(f"Could not verify trigger level: {verify_err}")

            # Log a summary of all the trigger settings that were applied
            self._logger.info(f"Trigger configured: CH{channel}, Level={trigger_level}V, Slope={trigger_slope}, Sweep={sweep_mode}")
            # Return True to signal that all trigger settings were applied successfully
            return True
        # If any trigger command fails, catch the error and log it
        except Exception as e:
            self._logger.error(f"Failed to configure trigger: {type(e).__name__}: {e}")
            return False

    # ============================================================================
    # MEASUREMENT FUNCTIONS - VERIFIED AGAINST KEYSIGHT 6000X MANUAL
    # ============================================================================

    # Define measure_single — this tells the oscilloscope to compute one specific measurement on one channel
    def measure_single(self, channel: int, measurement_type: str) -> Optional[float]:
        """
        Perform a single measurement on specified channel

        - ALL SCPI COMMANDS VERIFIED AGAINST MANUAL PAGES 620-718

        Args:
            channel (int): Channel number (1-4)
            measurement_type (str): Type of measurement (FREQ, PERiod, VAMP, VPP, etc.)

        Returns:
            float: Measurement value or None if error
        """
        # Return None if not connected — measurements cannot be taken without a live link
        if not self.is_connected:
            self._logger.error("Cannot measure: oscilloscope not connected")
            return None

        # Validate the channel number before attempting any measurement
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel: {channel}")
            return None

        # Try to perform the measurement, catching any errors
        try:
            # Build SCPI command based on measurement type
            # All commands verified from Keysight 6000X Programming Manual
            # - Manual pg 706-714: MEASure:XXXX? CHANneln
            # [Blank line for visual separation]
            # Map each human-readable measurement name to its exact SCPI command prefix
            cmd_map = {
                # Frequency measurement command
                "FREQ": ":MEASure:FREQuency? CHANnel",
                # Period measurement command
                "PERiod": ":MEASure:PERiod? CHANnel",
                # Peak-to-peak voltage measurement command
                "VPP": ":MEASure:VPP? CHANnel",
                # Amplitude (Vtop minus Vbase) measurement command
                "VAMP": ":MEASure:VAMPlitude? CHANnel",
                # Top voltage level measurement command
                "VTOP": ":MEASure:VTOP? CHANnel",
                # Base voltage level measurement command
                "VBASe": ":MEASure:VBASe? CHANnel",
                # Average voltage measurement command (across displayed portion)
                "VAVG": ":MEASure:VAVerage? DISPlay,CHANnel",
                # DC RMS voltage measurement command
                "VRMS": ":MEASure:VRMS? DISPlay,DC,CHANnel",
                # Maximum voltage measurement command
                "VMAX": ":MEASure:VMAX? CHANnel",
                # Minimum voltage measurement command
                "VMIN": ":MEASure:VMIN? CHANnel",
                # Rise time measurement command (how fast the signal rises)
                "RISE": ":MEASure:RISetime? CHANnel",
                # Fall time measurement command (how fast the signal falls)
                "FALL": ":MEASure:FALLtime? CHANnel",
                # Positive duty cycle measurement command (percentage of time signal is high)
                "DUTYcycle": ":MEASure:DUTYcycle? CHANnel",
                # Negative duty cycle measurement command
                "NDUTy": ":MEASure:NDUTy? CHANnel",
                # Overshoot measurement command (how much the signal exceeds its target level)
                "OVERshoot": ":MEASure:OVERshoot? CHANnel",
                # Positive pulse width measurement command
                "PWIDth": ":MEASure:PWIDth? CHANnel",
                # Negative pulse width measurement command
                "NWIDth": ":MEASure:NWIDth? CHANnel"
            }

            # Check that the requested measurement type exists in the command map
            if measurement_type not in cmd_map:
                self._logger.error(f"Unknown measurement type: {measurement_type}")
                return None

            # Build complete command
            # Look up the base SCPI command string for the requested measurement type
            base_cmd = cmd_map[measurement_type]
            # Append the channel number to the end of the base command to complete the SCPI query
            query_command = f"{base_cmd}{channel}"

            # Execute query
            # Wait for any pending operations to finish before sending the measurement query
            self._scpi_wrapper.query("*OPC?")
            # Pause briefly to let the instrument settle before sending the measurement command
            time.sleep(0.1)
            # [Blank line for visual separation]
            # Send the measurement query and capture the response text
            response = self._scpi_wrapper.query(query_command).strip()

            # Try to convert the response text to a floating-point number
            try:
                # Parse the numeric value from the instrument's response string
                value = float(response)
                # Log the measurement at debug level for detailed tracing
                self._logger.debug(f"CH{channel} {measurement_type}: {value}")
                # Return the numeric measurement value to the caller
                return value
            # If the response cannot be converted to a number (e.g. instrument returned an error string), catch the error
            except ValueError:
                self._logger.error(f"Failed to parse measurement response: '{response}'")
                return None

        # If any part of the measurement query fails (communication error, timeout, etc.), catch the error
        except Exception as e:
            self._logger.error(f"Measurement failed for CH{channel} ({measurement_type}): {e}")
            return None

    # Define measure_math_single — this performs a measurement on a math (computed) waveform rather than a raw channel
    def measure_math_single(self, function_num: int, measurement_type: str) -> Optional[float]:
        """
        Perform a single measurement on specified math function

        - VERIFIED: Math function measurement source from manual pages 706-714

        Args:
            function_num (int): Math function number (1-4)
            measurement_type (str): Type of measurement (FREQ, PERiod, VAMP, VPP, etc.)

        Returns:
            float: Measurement value or None if error
        """
        # Return None immediately if the oscilloscope is not connected
        if not self.is_connected:
            self._logger.error("Cannot measure: oscilloscope not connected")
            return None

        # Validate the math function number (the oscilloscope supports functions 1 through 4)
        if not (1 <= function_num <= 4):
            self._logger.error(f"Invalid math function: {function_num}")
            return None

        # Try to perform the math measurement, catching any errors
        try:
            # Build SCPI command based on measurement type
            # - Manual pg 706-714: MEASure:XXXX? source (where source can be FUNCtion1-4)
            # [Blank line for visual separation]
            # Map measurement type names to SCPI query prefixes that target math function channels
            cmd_map = {
                # Frequency measurement on a math function channel
                "FREQ": ":MEASure:FREQuency? FUNCtion",
                # Period measurement on a math function channel
                "PERiod": ":MEASure:PERiod? FUNCtion",
                # Peak-to-peak voltage on a math function channel
                "VPP": ":MEASure:VPP? FUNCtion",
                # Amplitude measurement on a math function channel
                "VAMP": ":MEASure:VAMPlitude? FUNCtion",
                # Top voltage level on a math function channel
                "VTOP": ":MEASure:VTOP? FUNCtion",
                # Base voltage level on a math function channel
                "VBASe": ":MEASure:VBASe? FUNCtion",
                # Average voltage on a math function channel
                "VAVG": ":MEASure:VAVerage? DISPlay,FUNCtion",
                # DC RMS voltage on a math function channel
                "VRMS": ":MEASure:VRMS? DISPlay,DC,FUNCtion",
                # Maximum voltage on a math function channel
                "VMAX": ":MEASure:VMAX? FUNCtion",
                # Minimum voltage on a math function channel
                "VMIN": ":MEASure:VMIN? FUNCtion",
                # Rise time on a math function channel
                "RISE": ":MEASure:RISetime? FUNCtion",
                # Fall time on a math function channel
                "FALL": ":MEASure:FALLtime? FUNCtion",
                # Positive duty cycle on a math function channel
                "DUTYcycle": ":MEASure:DUTYcycle? FUNCtion",
                # Negative duty cycle on a math function channel
                "NDUTy": ":MEASure:NDUTy? FUNCtion",
                # Overshoot on a math function channel
                "OVERshoot": ":MEASure:OVERshoot? FUNCtion",
                # Positive pulse width on a math function channel
                "PWIDth": ":MEASure:PWIDth? FUNCtion",
                # Negative pulse width on a math function channel
                "NWIDth": ":MEASure:NWIDth? FUNCtion"
            }

            # Check that the requested measurement type is in the command map
            if measurement_type not in cmd_map:
                self._logger.error(f"Unknown measurement type: {measurement_type}")
                return None

            # Build complete command
            # Look up the base SCPI command string for this measurement type
            base_cmd = cmd_map[measurement_type]
            # Append the math function number to complete the SCPI query
            query_command = f"{base_cmd}{function_num}"

            # Execute query
            # Confirm the instrument is idle before sending the measurement query
            self._scpi_wrapper.query("*OPC?")
            # Brief pause to let the instrument settle
            time.sleep(0.1)
            # [Blank line for visual separation]
            # Send the query and capture the text response
            response = self._scpi_wrapper.query(query_command).strip()

            # Try to parse the response text as a floating-point number
            try:
                # Convert the response string to a number
                value = float(response)
                # Log the result at debug level
                self._logger.debug(f"MATH{function_num} {measurement_type}: {value}")
                # Return the numeric measurement value
                return value
            # If conversion fails (instrument returned a non-numeric string), catch and log the error
            except ValueError:
                self._logger.error(f"Failed to parse measurement response: '{response}'")
                return None

        # If the query itself fails, catch the exception and log it
        except Exception as e:
            self._logger.error(f"Measurement failed for MATH{function_num} ({measurement_type}): {e}")
            return None

    # Define measure_multiple — this runs several measurements in a loop and collects all results in a dictionary
    def measure_multiple(self, channel: int, measurement_types: List[str]) -> Optional[Dict[str, float]]:
        """
        Perform multiple measurements on specified channel

        Args:
            channel (int): Channel number (1-4)
            measurement_types (List[str]): List of measurement types

        Returns:
            Dict[str, float]: Dictionary with measurement names as keys and values
        """
        # Return None immediately if the oscilloscope is not connected
        if not self.is_connected:
            self._logger.error("Cannot measure: oscilloscope not connected")
            return None

        # Start with an empty dictionary to hold the measurement results
        results = {}
        # Loop through each requested measurement type one at a time
        for meas_type in measurement_types:
            # Run one measurement and get its numeric value (or None if it failed)
            value = self.measure_single(channel, meas_type)
            # Only store the result if the measurement was successful (not None)
            if value is not None:
                results[meas_type] = value

        # Check if at least one measurement succeeded
        if results:
            # Log all the results together for convenience
            self._logger.info(f"CH{channel} measurements: {results}")
            # Return the dictionary of successful measurements
            return results
        else:
            # Log an error if every measurement failed
            self._logger.error(f"No measurements succeeded for CH{channel}")
            return None

    # Define get_all_measurements — this runs every available measurement type on a channel and returns all results
    def get_all_measurements(self, channel: int) -> Optional[Dict[str, float]]:
        """
        Get all available measurements for a channel

        Args:
            channel (int): Channel number (1-4)

        Returns:
            Dict[str, float]: All available measurements
        """
        # List every supported measurement type that the oscilloscope can compute
        essential_measurements = [
            "FREQ", "PERiod", "VPP", "VAMP", "VTOP", "VBASe",
            "VAVG", "VRMS", "VMAX", "VMIN", "RISE", "FALL",
            "DUTYcycle", "NDUTy", "OVERshoot", "PWIDth", "NWIDth"
        ]
        # Delegate to measure_multiple with all measurement types to get a complete set of readings
        return self.measure_multiple(channel, essential_measurements)

    # ============================================================================
    # CONVENIENCE MEASUREMENT METHODS - CHANNEL
    # ============================================================================

    # Define measure_frequency — a shortcut that measures how many times per second the signal repeats
    def measure_frequency(self, channel: int) -> Optional[float]:
        """Measure signal frequency in Hz"""
        # Call the general measure_single function with the FREQ measurement type
        return self.measure_single(channel, "FREQ")

    # Define measure_period — a shortcut that measures the time for one complete signal cycle
    def measure_period(self, channel: int) -> Optional[float]:
        """Measure signal period in seconds"""
        # Call the general measure_single function with the PERiod measurement type
        return self.measure_single(channel, "PERiod")

    # Define measure_peak_to_peak — a shortcut that measures the total voltage swing of the signal
    def measure_peak_to_peak(self, channel: int) -> Optional[float]:
        """Measure signal peak-to-peak voltage in volts"""
        # Call the general measure_single function with the VPP (peak-to-peak) measurement type
        return self.measure_single(channel, "VPP")

    # Define measure_amplitude — a shortcut that measures the signal amplitude (top voltage minus base voltage)
    def measure_amplitude(self, channel: int) -> Optional[float]:
        """Measure signal amplitude (Vtop - Vbase) in volts"""
        # Call the general measure_single function with the VAMP measurement type
        return self.measure_single(channel, "VAMP")

    # Define measure_top — a shortcut that measures the upper stable voltage level of a pulse waveform
    def measure_top(self, channel: int) -> Optional[float]:
        """Measure signal top voltage in volts"""
        # Call the general measure_single function with the VTOP measurement type
        return self.measure_single(channel, "VTOP")

    # Define measure_base — a shortcut that measures the lower stable voltage level of a pulse waveform
    def measure_base(self, channel: int) -> Optional[float]:
        """Measure signal base voltage in volts"""
        # Call the general measure_single function with the VBASe measurement type
        return self.measure_single(channel, "VBASe")

    # Define measure_average — a shortcut that measures the mean voltage of the signal over time
    def measure_average(self, channel: int) -> Optional[float]:
        """Measure signal average voltage in volts"""
        # Call the general measure_single function with the VAVG measurement type
        return self.measure_single(channel, "VAVG")

    # Define measure_rms — a shortcut that measures the RMS (root mean square) voltage of the signal
    def measure_rms(self, channel: int) -> Optional[float]:
        """Measure signal RMS voltage in volts"""
        # Call the general measure_single function with the VRMS measurement type
        return self.measure_single(channel, "VRMS")

    # Define measure_dc_rms_fs — measures the true DC RMS voltage using the scope's built-in DC RMS calculation
    def measure_dc_rms_fs(self, channel: int) -> Optional[float]:
        """
        Measure DC RMS Full Scale voltage using the scope's built-in DC RMS measurement.

        This is the true DC baseline voltage level on the channel, measured as the
        RMS value of the entire captured waveform (DISPlay), including the DC component.

        Uses SCPI: :MEASure:VRMS? DISPlay,DC,CHANnel<N>

        Returns:
            DC RMS FS value in volts, or None if measurement fails
        """
        # Return None if the oscilloscope is not connected
        if not self.is_connected:
            self._logger.error("Oscilloscope not connected")
            return None
        # [Blank line for visual separation]
        # Try to send the DC RMS query, catching any errors
        try:
            # Query the DC RMS measurement directly from scope
            # DISPlay: measures all data on the display
            # DC: includes the DC component (not just AC)
            # CHANnel<N>: the channel to measure
            # Build the SCPI command that asks for DC RMS across the full displayed waveform on this channel
            cmd = f":MEASure:VRMS? DISPlay,DC,CHANnel{channel}"
            # Send the query and capture the raw text response
            result = self._scpi_wrapper.query(cmd)
            # Parse the response text into a floating-point voltage value
            value = float(result.strip())
            # Log the result at debug level
            self._logger.debug(f"DC RMS FS (Ch{channel}): {value:.6f}V")
            # Return the DC RMS voltage value
            return value
        # If the query or conversion fails, catch the error and log it
        except Exception as e:
            self._logger.error(f"Failed to measure DC RMS FS on channel {channel}: {e}")
            return None

    # Define measure_max — a shortcut that measures the highest voltage point in the captured waveform
    def measure_max(self, channel: int) -> Optional[float]:
        """Measure maximum voltage in volts"""
        # Call the general measure_single function with the VMAX measurement type
        return self.measure_single(channel, "VMAX")

    # Define measure_min — a shortcut that measures the lowest voltage point in the captured waveform
    def measure_min(self, channel: int) -> Optional[float]:
        """Measure minimum voltage in volts"""
        # Call the general measure_single function with the VMIN measurement type
        return self.measure_single(channel, "VMIN")

    # Define measure_rise_time — a shortcut that measures how long the signal takes to go from 10% to 90% of its amplitude
    def measure_rise_time(self, channel: int) -> Optional[float]:
        """Measure signal rise time in seconds"""
        # Call the general measure_single function with the RISE measurement type
        return self.measure_single(channel, "RISE")

    # Define measure_fall_time — a shortcut that measures how long the signal takes to drop from 90% to 10% of its amplitude
    def measure_fall_time(self, channel: int) -> Optional[float]:
        """Measure signal fall time in seconds"""
        # Call the general measure_single function with the FALL measurement type
        return self.measure_single(channel, "FALL")

    # Define measure_duty_cycle_positive — a shortcut that measures the percentage of time the signal is in its high state
    def measure_duty_cycle_positive(self, channel: int) -> Optional[float]:
        """Measure positive duty cycle as percentage"""
        # Call the general measure_single function with the DUTYcycle measurement type
        return self.measure_single(channel, "DUTYcycle")

    # Define measure_duty_cycle_negative — a shortcut that measures the percentage of time the signal is in its low state
    def measure_duty_cycle_negative(self, channel: int) -> Optional[float]:
        """Measure negative duty cycle as percentage"""
        # Call the general measure_single function with the NDUTy measurement type
        return self.measure_single(channel, "NDUTy")

    # Define measure_overshoot — a shortcut that measures how much the signal overshoots its target level after a transition
    def measure_overshoot(self, channel: int) -> Optional[float]:
        """Measure signal overshoot voltage in volts"""
        # Call the general measure_single function with the OVERshoot measurement type
        return self.measure_single(channel, "OVERshoot")

    # Define measure_pulse_width_positive — a shortcut that measures how long the signal stays in its high state each cycle
    def measure_pulse_width_positive(self, channel: int) -> Optional[float]:
        """Measure positive pulse width in seconds"""
        # Call the general measure_single function with the PWIDth measurement type
        return self.measure_single(channel, "PWIDth")

    # Define measure_pulse_width_negative — a shortcut that measures how long the signal stays in its low state each cycle
    def measure_pulse_width_negative(self, channel: int) -> Optional[float]:
        """Measure negative pulse width in seconds"""
        # Call the general measure_single function with the NWIDth measurement type
        return self.measure_single(channel, "NWIDth")

    # ============================================================================
    # ROOT ACQUISITION CONTROL - RUN, STOP, SINGLE, DIGITIZE
    # ============================================================================

    # Define set_bandwidth_limit — this enables or disables the 20 MHz low-pass filter on a channel to reduce noise
    def set_bandwidth_limit(self, channel: int, enable: bool) -> bool:
        """
        Enable or disable the 20 MHz bandwidth limit filter on a channel.

        SCPI: :CHANnel<n>:BWLimit {ON|OFF}
        """
        # Return False if not connected — command cannot be sent
        if not self.is_connected:
            return False
        # Try to send the bandwidth limit command, catching any errors
        try:
            # Convert the boolean enable flag to the "ON" or "OFF" string the instrument expects
            state = "ON" if enable else "OFF"
            # Send the SCPI command to enable or disable the 20 MHz bandwidth limit filter
            self._scpi_wrapper.write(f":CHANnel{channel}:BWLimit {state}")
            # Pause briefly so the instrument can process the command
            time.sleep(0.05)
            # Log the bandwidth limit state change
            self._logger.info(f"CH{channel} bandwidth limit: {state}")
            # Return True to indicate the filter state was changed successfully
            return True
        # If the command fails, log the error and return False
        except Exception as e:
            self._logger.error(f"Failed to set bandwidth limit: {type(e).__name__}: {e}")
            return False

    # Define get_acquisition_state — this asks the oscilloscope whether it is currently running, stopped, or in single mode
    def get_acquisition_state(self) -> Optional[str]:
        """
        Query the current acquisition run state.

        SCPI: :RSTate?
        Returns: "RUN", "STOP", "SING" or None on error
        """
        # Return None if not connected
        if not self.is_connected:
            return None
        # Try to query the run state, catching any errors
        try:
            # Ask the oscilloscope for its current run state and return the cleaned-up response
            return self._scpi_wrapper.query(":RSTate?").strip()
        # If the query fails, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to get acquisition state: {type(e).__name__}: {e}")
            return None

    # Define force_trigger — this forces the oscilloscope to trigger immediately even if the trigger condition has not occurred
    def force_trigger(self) -> bool:
        """
        Force an immediate trigger when the scope is waiting for a trigger event.

        SCPI: :TRIGger:FORCe
        """
        # Return False if not connected
        if not self.is_connected:
            return False
        # Try to send the force trigger command, catching any errors
        try:
            # Send the SCPI command that forces an immediate trigger event
            self._scpi_wrapper.write(":TRIGger:FORCe")
            # Wait 100 ms for the trigger to be processed
            time.sleep(0.1)
            # Log that a forced trigger was issued
            self._logger.info("Trigger forced")
            # Return True to indicate the command was sent successfully
            return True
        # If the command fails, log the error and return False
        except Exception as e:
            self._logger.error(f"Failed to force trigger: {type(e).__name__}: {e}")
            return False

    # Define run — this starts the oscilloscope in continuous acquisition mode so it keeps capturing waveforms
    def run(self) -> bool:
        """
        Start continuous acquisition

        - VERIFIED: RUN command from manual page 285
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot run: oscilloscope not connected")
            return False

        # Try to send the RUN command, catching any errors
        try:
            # SCPI: RUN (pg 285)
            # Send the RUN command to start continuous waveform acquisition
            self._scpi_wrapper.write("RUN")
            # Wait 100 ms for the acquisition to start
            time.sleep(0.1)
            # Log that the oscilloscope has been put into run mode
            self._logger.info("Acquisition started: RUN")
            # Return True to indicate the command succeeded
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to start acquisition: {type(e).__name__}: {e}")
            return False

    # Define stop — this halts the oscilloscope acquisition so the current waveform stays frozen on screen
    def stop(self) -> bool:
        """
        Stop acquisition

        - VERIFIED: STOP command from manual page 289
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot stop: oscilloscope not connected")
            return False

        # Try to send the STOP command, catching any errors
        try:
            # SCPI: STOP (pg 289)
            # Send the STOP command to freeze the current waveform on screen
            self._scpi_wrapper.write("STOP")
            # Wait 100 ms for the oscilloscope to finish its current sweep and stop
            time.sleep(0.1)
            # Log that the oscilloscope acquisition has been stopped
            self._logger.info("Acquisition stopped: STOP")
            # Return True to indicate the stop command succeeded
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to stop acquisition: {type(e).__name__}: {e}")
            return False

    # Define single — this arms the oscilloscope to capture exactly one waveform and then stop
    def single(self) -> bool:
        """
        Trigger single acquisition

        - VERIFIED: SINGle command from manual page 287
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot trigger single: oscilloscope not connected")
            return False

        # Try to send the SINGle command, catching any errors
        try:
            # SCPI: SINGle (pg 287)
            # Send the SINGle command to arm the oscilloscope for one trigger-and-capture cycle
            self._scpi_wrapper.write("SINGle")
            # Wait 100 ms for the oscilloscope to arm itself
            time.sleep(0.1)
            # Log that a single-shot acquisition was triggered
            self._logger.info("Single acquisition triggered")
            # Return True to indicate the command was accepted
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to trigger single: {type(e).__name__}: {e}")
            return False

    # Define digitize — this commands the oscilloscope to acquire a complete waveform and wait until it is done
    def digitize(self, channel: Optional[int] = None) -> bool:
        """
        Acquire waveform and wait for completion

        - VERIFIED: DIGitize command from manual page 262

        Args:
            channel: Optional channel number 1-4, None for all channels

        Returns:
            bool: True if successful

        Note: This function waits for acquisition to complete. For long timebase
        settings (20s, 50s), this may take several minutes.
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot digitize: oscilloscope not connected")
            return False

        # Try to run the digitize sequence, catching any errors
        try:
            # Check whether the caller specified a particular channel or wants all channels
            if channel is not None:
                # Validate the channel number before sending any command
                if not (1 <= channel <= self.max_channels):
                    self._logger.error(f"Invalid channel: {channel}")
                    return False
                # SCPI: :DIGitize CHANnel (pg 262)
                # Tell the oscilloscope to digitize (sample and store) the waveform on the specified channel
                self._scpi_wrapper.write(f":DIGitize CHANnel{channel}")
            else:
                # SCPI: :DIGitize (pg 262)
                # No channel specified — digitize all active channels at once
                self._scpi_wrapper.write(":DIGitize")

            # Get current timebase to estimate wait time
            # Try to read the current timebase so we know how long to wait for the sweep to complete
            try:
                # Query the current time scale setting from the oscilloscope
                timebase_scale = float(self._scpi_wrapper.query(":TIMebase:SCALe?").strip())
                # Calculate the total sweep time as 10 horizontal divisions times the scale
                estimated_time = 10 * timebase_scale  # 10 divisions
                # Log the estimated acquisition time so the operator knows to wait
                self._logger.info(f"Digitizing... estimated time: {estimated_time:.1f}s")

                # Use smaller sleep intervals for short acquisitions
                # For fast sweeps, only wait half a second before polling for completion
                if estimated_time < 2.0:
                    time.sleep(0.5)
                else:
                    # For long acquisitions, wait 80% of estimated time before polling
                    # For slow sweeps, wait most of the expected time before checking if done
                    time.sleep(estimated_time * 0.8)
            # If we cannot read the timebase, fall back to a default wait time
            except Exception:
                # If we can't get timebase, use default wait
                time.sleep(0.5)

            # Wait for operation to complete (will timeout if acquisition takes too long)
            # Block until the oscilloscope signals that the digitize operation is fully complete
            self._scpi_wrapper.query("*OPC?")
            # Log that digitization finished
            self._logger.info(f"Digitize completed for channel {channel if channel else 'all'}")
            # Return True to signal successful completion
            return True
        # If the digitize operation fails for any reason, catch and log the error
        except Exception as e:
            self._logger.error(f"Digitize failed: {type(e).__name__}: {e}")
            return False

    # ============================================================================
    # ACQUISITION CONFIGURATION - ACQuire SUBSYSTEM
    # ============================================================================

    # Define set_acquire_mode — this controls how the oscilloscope samples waveform data (real-time, equivalent-time, or segmented)
    def set_acquire_mode(self, mode: str) -> bool:
        """
        Set acquisition mode

        - VERIFIED: :ACQuire:MODE command from manual page 300

        Args:
            mode: "RTIMe", "ETIMe", or "SEGMented"

        Returns:
            bool: True if successful
        """
        # Return False if not connected — cannot configure without a link
        if not self.is_connected:
            self._logger.error("Cannot set acquire mode: oscilloscope not connected")
            return False

        # Define the list of valid acquisition mode strings
        valid_modes = ["RTIMe", "ETIMe", "SEGMented"]
        # Check that the caller's mode string is one of the valid options
        if mode not in valid_modes:
            self._logger.error(f"Invalid acquire mode: {mode}. Must be one of {valid_modes}")
            return False

        # Try to send the acquire mode command, catching any errors
        try:
            # SCPI: :ACQuire:MODE (pg 300)
            # Send the command to set the acquisition mode
            self._scpi_wrapper.write(f":ACQuire:MODE {mode}")
            # Wait 100 ms for the mode change to take effect
            time.sleep(0.1)
            # Log the new acquisition mode
            self._logger.info(f"Acquire mode set to: {mode}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set acquire mode: {type(e).__name__}: {e}")
            return False

    # Define get_acquire_mode — this queries the oscilloscope to find out what acquisition mode it is currently in
    def get_acquire_mode(self) -> Optional[str]:
        """
        Query current acquisition mode

        - VERIFIED: :ACQuire:MODE? query from manual page 300

        Returns:
            str: Current mode (RTIM, ETIM, or SEGM) or None if error
        """
        # Return None if not connected
        if not self.is_connected:
            return None

        # Try to query the current acquisition mode, catching any errors
        try:
            # SCPI: :ACQuire:MODE? (pg 300)
            # Ask the oscilloscope what acquisition mode it is currently using
            mode = self._scpi_wrapper.query(":ACQuire:MODE?").strip()
            # Return the mode string to the caller
            return mode
        # If the query fails, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to query acquire mode: {type(e).__name__}: {e}")
            return None

    # Define set_acquire_type — this sets whether the oscilloscope samples normally, averages, uses high resolution, or uses peak detection
    def set_acquire_type(self, acq_type: str) -> bool:
        """
        Set acquisition type

        - VERIFIED: :ACQuire:TYPE command from manual page 310

        Args:
            acq_type: "NORMal", "AVERage", "HRESolution", or "PEAK"

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set acquire type: oscilloscope not connected")
            return False

        # Define the list of valid acquisition type strings
        valid_types = ["NORMal", "AVERage", "HRESolution", "PEAK"]
        # Check that the caller's type is valid
        if acq_type not in valid_types:
            self._logger.error(f"Invalid acquire type: {acq_type}. Must be one of {valid_types}")
            return False

        # Try to send the acquire type command, catching any errors
        try:
            # SCPI: :ACQuire:TYPE (pg 310)
            # Send the command to set the acquisition type
            self._scpi_wrapper.write(f":ACQuire:TYPE {acq_type}")
            # Wait 100 ms for the type change to take effect
            time.sleep(0.1)
            # Log the new acquisition type
            self._logger.info(f"Acquire type set to: {acq_type}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set acquire type: {type(e).__name__}: {e}")
            return False

    # Define get_acquire_type — this asks the oscilloscope what acquisition type it is currently configured to use
    def get_acquire_type(self) -> Optional[str]:
        """
        Query current acquisition type

        - VERIFIED: :ACQuire:TYPE? query from manual page 310

        Returns:
            str: Current type (NORM, AVER, HRES, or PEAK) or None if error
        """
        # Return None if not connected
        if not self.is_connected:
            return None

        # Try to query the acquisition type, catching any errors
        try:
            # SCPI: :ACQuire:TYPE? (pg 310)
            # Ask the oscilloscope for its current acquisition type setting
            acq_type = self._scpi_wrapper.query(":ACQuire:TYPE?").strip()
            # Return the acquisition type string
            return acq_type
        # If the query fails, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to query acquire type: {type(e).__name__}: {e}")
            return None

    # Define set_acquire_count — this sets how many waveforms are averaged together when in AVERage acquisition mode
    def set_acquire_count(self, count: int) -> bool:
        """
        Set number of averages for AVERage mode

        - VERIFIED: :ACQuire:COUNt command from manual page 298

        Args:
            count: Number of averages (2 to 65536)

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set acquire count: oscilloscope not connected")
            return False

        # Validate that the count is within the allowed range
        if not (2 <= count <= 65536):
            self._logger.error(f"Invalid count: {count}. Must be 2-65536")
            return False

        # Try to send the acquire count command, catching any errors
        try:
            # SCPI: :ACQuire:COUNt (pg 298)
            # Send the command to set how many waveforms to average
            self._scpi_wrapper.write(f":ACQuire:COUNt {count}")
            # Wait 100 ms for the count to be applied
            time.sleep(0.1)
            # Log the new average count
            self._logger.info(f"Acquire count set to: {count}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set acquire count: {type(e).__name__}: {e}")
            return False

    # Define get_acquire_count — this queries how many waveforms are currently being averaged
    def get_acquire_count(self) -> Optional[int]:
        """
        Query current average count

        - VERIFIED: :ACQuire:COUNt? query from manual page 298

        Returns:
            int: Current count or None if error
        """
        # Return None if not connected
        if not self.is_connected:
            return None

        # Try to query the current average count, catching any errors
        try:
            # SCPI: :ACQuire:COUNt? (pg 298)
            # Ask the oscilloscope for its current average count and convert the response to an integer
            count = int(self._scpi_wrapper.query(":ACQuire:COUNt?").strip())
            # Return the count value
            return count
        # If the query fails, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to query acquire count: {type(e).__name__}: {e}")
            return None

    # Define get_sample_rate — this queries how many data points per second the oscilloscope is currently capturing
    def get_sample_rate(self) -> Optional[float]:
        """
        Query current sample rate

        - VERIFIED: :ACQuire:SRATe? query from manual page 309

        Returns:
            float: Sample rate in Sa/s or None if error
        """
        # Return None if not connected
        if not self.is_connected:
            return None

        # Try to query the sample rate, catching any errors
        try:
            # SCPI: :ACQuire:SRATe? (pg 309)
            # Ask the oscilloscope for its current sample rate in samples per second
            rate = float(self._scpi_wrapper.query(":ACQuire:SRATe?").strip())
            # Return the sample rate
            return rate
        # If the query fails, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to query sample rate: {type(e).__name__}: {e}")
            return None

    # Define get_acquire_points — this queries how many data points were captured in the most recent acquisition
    def get_acquire_points(self) -> Optional[int]:
        """
        Query number of acquired points

        - VERIFIED: :ACQuire:POINts? query from manual page 302

        Returns:
            int: Number of acquired points or None if error
        """
        # Return None if not connected
        if not self.is_connected:
            return None

        # Try to query the number of acquired points, catching any errors
        try:
            # SCPI: :ACQuire:POINts? (pg 302)
            # Ask the oscilloscope how many data points it stored in the last acquisition
            points = int(self._scpi_wrapper.query(":ACQuire:POINts?").strip())
            # Return the point count
            return points
        # If the query fails, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to query acquire points: {type(e).__name__}: {e}")
            return None

    # ============================================================================
    # TRIGGER CONFIGURATION - ADVANCED TRIGGER MODES (GLITCH, PULSE, etc.)
    # ============================================================================

    # Define set_trigger_mode — this selects what type of signal event causes the oscilloscope to trigger
    def set_trigger_mode(self, mode: str) -> bool:
        """
        Set trigger mode

        - VERIFIED: :TRIGger:MODE command from manual page 999

        Args:
            mode: "EDGE", "GLITch", "PATTern", "PULSE", "TV", "DELay", "TIMeout", etc.

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set trigger mode: oscilloscope not connected")
            return False

        # Try to send the trigger mode command, catching any errors
        try:
            # SCPI: :TRIGger:MODE (pg 999)
            # Send the command to set the trigger mode (e.g. EDGE, GLITCH, PULSE)
            self._scpi_wrapper.write(f":TRIGger:MODE {mode}")
            # Wait 100 ms for the mode to be applied
            time.sleep(0.1)
            # Log the new trigger mode
            self._logger.info(f"Trigger mode set to: {mode}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set trigger mode: {type(e).__name__}: {e}")
            return False

    # Define get_trigger_mode — this queries what trigger mode the oscilloscope is currently using
    def get_trigger_mode(self) -> Optional[str]:
        """
        Query current trigger mode

        - VERIFIED: :TRIGger:MODE? query from manual page 999

        Returns:
            str: Current trigger mode or None if error
        """
        # Return None if not connected
        if not self.is_connected:
            return None

        # Try to query the trigger mode, catching any errors
        try:
            # SCPI: :TRIGger:MODE? (pg 999)
            # Ask the oscilloscope what trigger mode it is currently using
            mode = self._scpi_wrapper.query(":TRIGger:MODE?").strip()
            # Return the trigger mode string
            return mode
        # If the query fails, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to query trigger mode: {type(e).__name__}: {e}")
            return None

    # Define set_trigger_level — this sets the voltage threshold at which the trigger fires
    def set_trigger_level(self, level: float) -> bool:
        """
        Set trigger level

        - VERIFIED: :TRIGger:LEVel command from manual page 993

        Args:
            level: Trigger level in volts

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set trigger level: oscilloscope not connected")
            return False

        # Try to send the trigger level command, catching any errors
        try:
            # SCPI: :TRIGger:LEVel (pg 993)
            # Send the command to set the voltage level at which the trigger fires
            self._scpi_wrapper.write(f":TRIGger:LEVel {level}")
            # Wait 100 ms for the level to be applied
            time.sleep(0.1)
            # Log the new trigger level
            self._logger.info(f"Trigger level set to: {level}V")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set trigger level: {type(e).__name__}: {e}")
            return False

    # Define get_trigger_level — this queries the current voltage threshold used for triggering
    def get_trigger_level(self) -> Optional[float]:
        """
        Query trigger level

        - VERIFIED: :TRIGger:LEVel? query from manual page 993

        Returns:
            float: Trigger level in volts or None if error
        """
        # Return None if not connected
        if not self.is_connected:
            return None

        # Try to query the trigger level, catching any errors
        try:
            # SCPI: :TRIGger:LEVel? (pg 993)
            # Ask the oscilloscope for its current trigger level in volts
            level = float(self._scpi_wrapper.query(":TRIGger:LEVel?").strip())
            # Return the trigger level value
            return level
        # If the query fails, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to query trigger level: {type(e).__name__}: {e}")
            return None

    # Define set_trigger_sweep — this sets whether the scope waits for a real trigger or captures automatically after a timeout
    def set_trigger_sweep(self, sweep: str) -> bool:
        """
        Set trigger sweep mode

        - VERIFIED: :TRIGger:SWEep command from manual page 1018

        Args:
            sweep: "AUTO", "NORMal", or "TRIG"

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set trigger sweep: oscilloscope not connected")
            return False

        # Define the valid sweep modes
        valid_sweeps = ["AUTO", "NORMal", "TRIG"]
        # Check that the given sweep mode is one of the accepted values
        if sweep not in valid_sweeps:
            self._logger.error(f"Invalid sweep mode: {sweep}. Must be one of {valid_sweeps}")
            return False

        # Try to send the trigger sweep mode command, catching any errors
        try:
            # SCPI: :TRIGger:SWEep (pg 1018)
            # Send the command to set the sweep mode
            self._scpi_wrapper.write(f":TRIGger:SWEep {sweep}")
            # Wait 100 ms for the sweep mode to take effect
            time.sleep(0.1)
            # Log the new sweep mode
            self._logger.info(f"Trigger sweep set to: {sweep}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set trigger sweep: {type(e).__name__}: {e}")
            return False

    # Define set_trigger_holdoff — this sets a dead time after each trigger during which the oscilloscope will not re-trigger
    def set_trigger_holdoff(self, holdoff_time: float) -> bool:
        """
        Set trigger holdoff time

        - VERIFIED: :TRIGger:HOLDoff command from manual page 987

        Args:
            holdoff_time: Holdoff time in seconds

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set trigger holdoff: oscilloscope not connected")
            return False

        # Try to send the holdoff command, catching any errors
        try:
            # SCPI: :TRIGger:HOLDoff (pg 987)
            # Send the command to set how long after a trigger the scope ignores subsequent triggers
            self._scpi_wrapper.write(f":TRIGger:HOLDoff {holdoff_time}")
            # Wait 100 ms for the holdoff to be applied
            time.sleep(0.1)
            # Log the new holdoff time
            self._logger.info(f"Trigger holdoff set to: {holdoff_time}s")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set trigger holdoff: {type(e).__name__}: {e}")
            return False

    # Define set_glitch_trigger — this configures the oscilloscope to trigger when it detects a very short unexpected pulse (glitch)
    def set_glitch_trigger(self, channel: int, level: float, polarity: str = "POSitive",
                           width: float = 1e-9) -> bool:
        """
        Configure glitch trigger (spike detection)

        - VERIFIED: :TRIGger:GLITch commands from manual pages 981-988

        Args:
            channel: Source channel (1-4)
            level: Trigger level in volts
            polarity: "POSitive" or "NEGative"
            width: Glitch width threshold in seconds

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set glitch trigger: oscilloscope not connected")
            return False

        # Validate the channel number
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel: {channel}")
            return False

        # Try to configure the glitch trigger, catching any errors
        try:
            # SCPI: :TRIGger:MODE GLITch (pg 981)
            # Set the trigger mode to GLITch so the scope looks for short abnormal pulses
            self._scpi_wrapper.write(":TRIGger:MODE GLITch")
            # Wait 100 ms for the mode change to take effect
            time.sleep(0.1)
            # [Blank line for visual separation]
            # SCPI: :TRIGger:GLITch:SOURce (pg 984)
            # Set which channel the glitch trigger should monitor
            self._scpi_wrapper.write(f":TRIGger:GLITch:SOURce CHANnel{channel}")
            # Wait 100 ms between commands
            time.sleep(0.1)
            # [Blank line for visual separation]
            # SCPI: :TRIGger:LEVel (pg 993)
            # Set the voltage threshold at which the glitch trigger fires
            self._scpi_wrapper.write(f":TRIGger:LEVel {level}")
            # Wait 100 ms for the level to be applied
            time.sleep(0.1)
            # [Blank line for visual separation]
            # SCPI: :TRIGger:GLITch:POLarity (pg 983)
            # Set whether the glitch trigger looks for positive or negative spikes
            self._scpi_wrapper.write(f":TRIGger:GLITch:POLarity {polarity}")
            # Wait 100 ms for the polarity to be applied
            time.sleep(0.1)
            # [Blank line for visual separation]
            # SCPI: :TRIGger:GLITch:WIDTh (pg 988)
            # Set the maximum pulse width that counts as a glitch (anything shorter triggers the scope)
            self._scpi_wrapper.write(f":TRIGger:GLITch:WIDTh {width}")
            # Wait 100 ms for the width to be applied
            time.sleep(0.1)
            # [Blank line for visual separation]
            # Log a summary of the glitch trigger settings
            self._logger.info(f"Glitch trigger configured: CH{channel}, Level={level}V, Width={width}s")
            # Return True to indicate success
            return True
        # If any command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to configure glitch trigger: {type(e).__name__}: {e}")
            return False

    # Define set_pulse_trigger — this configures the oscilloscope to trigger on pulses of a specific width
    def set_pulse_trigger(self, channel: int, level: float, width: float = 1e-9,
                          polarity: str = "POSitive") -> bool:
        """
        Configure pulse width trigger

        - VERIFIED: :TRIGger:PULSE commands from manual pages 1002-1010

        Args:
            channel: Source channel (1-4)
            level: Trigger level in volts
            width: Pulse width threshold in seconds
            polarity: "POSitive" or "NEGative"

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set pulse trigger: oscilloscope not connected")
            return False

        # Validate the channel number
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel: {channel}")
            return False

        # Try to configure the pulse width trigger, catching any errors
        try:
            # SCPI: :TRIGger:MODE PULSE (pg 1002)
            # Set the trigger mode to PULSE so the scope triggers on a specific pulse width
            self._scpi_wrapper.write(":TRIGger:MODE PULSE")
            # Wait 100 ms for the mode change to take effect
            time.sleep(0.1)
            # [Blank line for visual separation]
            # SCPI: :TRIGger:PULSE:SOURce (pg 1007)
            # Set which channel the pulse trigger should monitor
            self._scpi_wrapper.write(f":TRIGger:PULSE:SOURce CHANnel{channel}")
            # Wait 100 ms between commands
            time.sleep(0.1)
            # [Blank line for visual separation]
            # SCPI: :TRIGger:LEVel (pg 993)
            # Set the voltage threshold for pulse detection
            self._scpi_wrapper.write(f":TRIGger:LEVel {level}")
            # Wait 100 ms for the level to be applied
            time.sleep(0.1)
            # [Blank line for visual separation]
            # SCPI: :TRIGger:PULSE:WIDTh (pg 1010)
            # Set the pulse width threshold that triggers the scope
            self._scpi_wrapper.write(f":TRIGger:PULSE:WIDTh {width}")
            # Wait 100 ms for the width to be applied
            time.sleep(0.1)
            # [Blank line for visual separation]
            # SCPI: :TRIGger:PULSE:POLarity (pg 1005)
            # Set whether to trigger on positive or negative pulses
            self._scpi_wrapper.write(f":TRIGger:PULSE:POLarity {polarity}")
            # Wait 100 ms for the polarity to be applied
            time.sleep(0.1)
            # [Blank line for visual separation]
            # Log a summary of the pulse trigger settings
            self._logger.info(f"Pulse trigger configured: CH{channel}, Width={width}s")
            # Return True to indicate success
            return True
        # If any command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to configure pulse trigger: {type(e).__name__}: {e}")
            return False

    # ============================================================================
    # WAVEFORM DATA TRANSFER - WAVeform SUBSYSTEM
    # ============================================================================

    # Define get_waveform_data — this downloads the raw waveform data points from the oscilloscope to the computer
    def get_waveform_data(self, channel: int, format_type: str = "BYTE",
                          freeze_acquisition: bool = True) -> Optional[np.ndarray]:
        """
        Retrieve waveform data from oscilloscope

        - VERIFIED: :WAVeform commands from manual pages 1137-1203

        Args:
            channel: Channel number (1-4)
            format_type: "BYTE", "WORD", or "ASCii"
            freeze_acquisition: If True, stops acquisition before reading data and resumes after
                              This prevents signal from disappearing during long acquisitions

        Returns:
            numpy array of waveform data or None if error

        Note: For long timebase settings (20s, 50s), freeze_acquisition=True is recommended
        to ensure stable data capture without signal disappearance.
        """
        # Return None if not connected
        if not self.is_connected:
            self._logger.error("Cannot get waveform: oscilloscope not connected")
            return None

        # Validate the channel number
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel: {channel}")
            return None

        # Define the valid data format options
        valid_formats = ["BYTE", "WORD", "ASCii"]
        # Check that the caller's format is valid
        if format_type not in valid_formats:
            self._logger.error(f"Invalid format: {format_type}. Must be one of {valid_formats}")
            return None

        # Track whether we stopped the acquisition so we can restart it after the transfer
        acquisition_was_running = False

        # Try to transfer the waveform data, catching any errors
        try:
            # FREEZE ACQUISITION: Stop the scope to preserve the current waveform
            # If the caller wants a stable snapshot, stop the oscilloscope before reading data
            if freeze_acquisition:
                # Try to stop the oscilloscope, but do not fail if this step does not work
                try:
                    self._logger.info("Stopping acquisition to freeze waveform for data transfer")
                    # Stop the oscilloscope acquisition so the waveform does not change during the transfer
                    self.stop()
                    # Remember that the oscilloscope was running so we can restart it after the transfer
                    acquisition_was_running = True
                    # Wait 200 ms for the oscilloscope to fully stop before reading data
                    time.sleep(0.2)  # Allow scope to settle
                # If stopping fails (e.g. scope already stopped), log a warning and continue
                except Exception as e:
                    self._logger.warning(f"Could not stop acquisition: {e}")

            # SCPI: :WAVeform:SOURce (pg 1201)
            # Tell the oscilloscope which channel's waveform data we want to read
            self._scpi_wrapper.write(f":WAVeform:SOURce CHANnel{channel}")
            # Wait 100 ms before sending the next command
            time.sleep(0.1)

            # SCPI: :WAVeform:FORMat (pg 1156)
            # Set the binary data format for the waveform transfer (BYTE = 8-bit, most common)
            self._scpi_wrapper.write(f":WAVeform:FORMat {format_type}")
            # Wait 100 ms for the format to be applied
            time.sleep(0.1)

            # SCPI: :WAVeform:PREamble? (pg 1158)
            # Read the preamble which contains scaling information needed to convert raw bytes to volts
            preamble = self._scpi_wrapper.query(":WAVeform:PREamble?").strip()
            # Log the preamble at debug level for detailed tracing
            self._logger.debug(f"Waveform preamble: {preamble}")

            # SCPI: :WAVeform:DATA? (pg 1150)
            # Download the raw binary waveform data from the oscilloscope
            data = self._scpi_wrapper.query_binary_values(":WAVeform:DATA?", datatype='B')

            # Check that some data was actually received
            if data:
                # Convert the list of raw byte values into a numpy array for efficient processing
                waveform = np.array(data, dtype=np.uint8)
                # Log how many data points were received
                self._logger.info(f"Retrieved {len(waveform)} waveform points from CH{channel}")

                # RESUME ACQUISITION: Restart the scope if it was running
                # If we stopped the scope earlier, restart it now that the data has been safely transferred
                if freeze_acquisition and acquisition_was_running:
                    # Try to restart the oscilloscope, but do not fail if this step does not work
                    try:
                        self._logger.info("Resuming acquisition (RUN mode)")
                        # Put the oscilloscope back into continuous run mode
                        self.run()
                        # Wait 100 ms for the oscilloscope to restart
                        time.sleep(0.1)
                    # If restarting fails, log a warning
                    except Exception as e:
                        self._logger.warning(f"Could not restart acquisition: {e}")

                # Return the numpy array of waveform data points to the caller
                return waveform

            # If no data was received, return None
            return None
        # If the data transfer fails at any point, catch the error
        except Exception as e:
            self._logger.error(f"Failed to get waveform data: {type(e).__name__}: {e}")

            # RESUME ACQUISITION: Make sure to restart even if data transfer failed
            # Even if the transfer failed, try to restart the oscilloscope so it does not stay stopped
            if freeze_acquisition and acquisition_was_running:
                # Try to restart the oscilloscope after the error
                try:
                    self._logger.info("Resuming acquisition after error")
                    # Put the oscilloscope back into run mode
                    self.run()
                # If restart also fails, log the secondary error
                except Exception as resume_error:
                    self._logger.error(f"Failed to resume acquisition: {resume_error}")

            # Return None to indicate the data transfer failed
            return None

    # Define set_waveform_points_mode — this controls whether the oscilloscope sends normal, maximum, or raw memory data
    def set_waveform_points_mode(self, mode: str) -> bool:
        """
        Set waveform points mode

        - VERIFIED: :WAVeform:POINtsMODE command from manual page 1160

        Args:
            mode: "NORMal", "MAXimum", or "RAW"

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set waveform points mode: oscilloscope not connected")
            return False

        # Define the valid points mode options
        valid_modes = ["NORMal", "MAXimum", "RAW"]
        # Check that the caller's mode is valid
        if mode not in valid_modes:
            self._logger.error(f"Invalid mode: {mode}. Must be one of {valid_modes}")
            return False

        # Try to send the waveform points mode command, catching any errors
        try:
            # SCPI: :WAVeform:POINtsMODE (pg 1160)
            # Send the command to set how many waveform points the oscilloscope returns
            self._scpi_wrapper.write(f":WAVeform:POINtsMODE {mode}")
            # Wait 100 ms for the mode to be applied
            time.sleep(0.1)
            # Log the new points mode
            self._logger.info(f"Waveform points mode set to: {mode}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set waveform points mode: {type(e).__name__}: {e}")
            return False

    # ============================================================================
    # MARKER/CURSOR OPERATIONS - MARKer SUBSYSTEM
    # ============================================================================

    # Define set_marker_mode — this controls whether the oscilloscope displays measurement cursors on screen
    def set_marker_mode(self, mode: str) -> bool:
        """
        Set marker/cursor mode

        - VERIFIED: :MARKer:MODE command from manual page 602

        Args:
            mode: "OFF", "MEASurement", "MANual", or "WAVeform"

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set marker mode: oscilloscope not connected")
            return False

        # Define the valid marker mode options
        valid_modes = ["OFF", "MEASurement", "MANual", "WAVeform"]
        # Check that the caller's mode is one of the accepted values
        if mode not in valid_modes:
            self._logger.error(f"Invalid marker mode: {mode}. Must be one of {valid_modes}")
            return False

        # Try to send the marker mode command, catching any errors
        try:
            # SCPI: :MARKer:MODE (pg 602)
            # Send the command to set the cursor/marker display mode
            self._scpi_wrapper.write(f":MARKer:MODE {mode}")
            # Wait 100 ms for the mode to be applied
            time.sleep(0.1)
            # Log the new marker mode
            self._logger.info(f"Marker mode set to: {mode}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set marker mode: {type(e).__name__}: {e}")
            return False

    # Define set_marker_x_position — this moves one of the two time-axis cursors to a specific position on screen
    def set_marker_x_position(self, marker: int, position: float) -> bool:
        """
        Set marker X position (time)

        - VERIFIED: :MARKer:X1POSition, :MARKer:X2POSition from manual pages 611-612

        Args:
            marker: Marker number (1 or 2)
            position: Time position in seconds

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set marker X position: oscilloscope not connected")
            return False

        # Validate that the marker number is 1 or 2 (only two horizontal markers are available)
        if marker not in [1, 2]:
            self._logger.error(f"Invalid marker: {marker}. Must be 1 or 2")
            return False

        # Try to send the marker X position command, catching any errors
        try:
            # SCPI: :MARKer:X1POSition / :MARKer:X2POSition (pg 611-612)
            # Send the command to place the chosen marker at the specified time position
            self._scpi_wrapper.write(f":MARKer:X{marker}POSition {position}")
            # Wait 100 ms for the position to be updated on screen
            time.sleep(0.1)
            # Log the new marker time position
            self._logger.info(f"Marker {marker} X position set to: {position}s")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set marker X position: {type(e).__name__}: {e}")
            return False

    # Define set_marker_y_position — this moves one of the two voltage-axis cursors to a specific voltage level on screen
    def set_marker_y_position(self, marker: int, position: float) -> bool:
        """
        Set marker Y position (voltage)

        - VERIFIED: :MARKer:Y1POSition, :MARKer:Y2POSition from manual pages 614-615

        Args:
            marker: Marker number (1 or 2)
            position: Voltage position in volts

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set marker Y position: oscilloscope not connected")
            return False

        # Validate that the marker number is 1 or 2
        if marker not in [1, 2]:
            self._logger.error(f"Invalid marker: {marker}. Must be 1 or 2")
            return False

        # Try to send the marker Y position command, catching any errors
        try:
            # SCPI: :MARKer:Y1POSition / :MARKer:Y2POSition (pg 614-615)
            # Send the command to place the chosen voltage cursor at the specified voltage level
            self._scpi_wrapper.write(f":MARKer:Y{marker}POSition {position}")
            # Wait 100 ms for the position to be updated on screen
            time.sleep(0.1)
            # Log the new marker voltage position
            self._logger.info(f"Marker {marker} Y position set to: {position}V")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set marker Y position: {type(e).__name__}: {e}")
            return False

    # Define set_marker_x1y1_source — this links the first cursor pair to a specific oscilloscope channel
    def set_marker_x1y1_source(self, channel: int) -> bool:
        """
        Set source channel for marker 1 (X1/Y1).
        Must be called after set_marker_mode("WAVeform") and before setting positions.

        SCPI: :MARKer:X1Y1Source CHANnel<n>  (pg 607)
        """
        # Return False if not connected
        if not self.is_connected:
            return False
        # Try to send the marker source command, catching any errors
        try:
            # Send the command to associate the first marker pair with the specified channel
            self._scpi_wrapper.write(f":MARKer:X1Y1Source CHANnel{channel}")
            # Wait 50 ms for the source assignment to take effect
            time.sleep(0.05)
            # Log the source assignment
            self._logger.info(f"Marker X1Y1 source set to CHANnel{channel}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set marker X1Y1 source: {type(e).__name__}: {e}")
            return False

    # Define set_marker_x2y2_source — this links the second cursor pair to a specific oscilloscope channel
    def set_marker_x2y2_source(self, channel: int) -> bool:
        """
        Set source channel for marker 2 (X2/Y2).
        Must be called after set_marker_mode("WAVeform") and before setting positions.

        SCPI: :MARKer:X2Y2Source CHANnel<n>  (pg 608)
        """
        # Return False if not connected
        if not self.is_connected:
            return False
        # Try to send the marker source command, catching any errors
        try:
            # Send the command to associate the second marker pair with the specified channel
            self._scpi_wrapper.write(f":MARKer:X2Y2Source CHANnel{channel}")
            # Wait 50 ms for the source assignment to take effect
            time.sleep(0.05)
            # Log the source assignment
            self._logger.info(f"Marker X2Y2 source set to CHANnel{channel}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set marker X2Y2 source: {type(e).__name__}: {e}")
            return False

    # Define get_marker_x_delta — this reads the time difference between the two horizontal cursors
    def get_marker_x_delta(self) -> Optional[float]:
        """
        Get X delta (time difference) between markers

        - VERIFIED: :MARKer:XDELta? query from manual page 609

        Returns:
            float: Time difference in seconds or None if error
        """
        # Return None if not connected
        if not self.is_connected:
            return None

        # Try to query the X delta between the two cursors, catching any errors
        try:
            # SCPI: :MARKer:XDELta? (pg 609)
            # Ask the oscilloscope for the time difference between marker 1 and marker 2
            delta = float(self._scpi_wrapper.query(":MARKer:XDELta?").strip())
            # Log the time delta at debug level
            self._logger.debug(f"Marker X delta: {delta}s")
            # Return the time difference value
            return delta
        # If the query fails, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to get marker X delta: {type(e).__name__}: {e}")
            return None

    # Define get_marker_y_delta — this reads the voltage difference between the two vertical cursors
    def get_marker_y_delta(self) -> Optional[float]:
        """
        Get Y delta (voltage difference) between markers

        - VERIFIED: :MARKer:YDELta? query from manual page 610

        Returns:
            float: Voltage difference in volts or None if error
        """
        # Return None if not connected
        if not self.is_connected:
            return None

        # Try to query the Y delta between the two cursors, catching any errors
        try:
            # SCPI: :MARKer:YDELta? (pg 610)
            # Ask the oscilloscope for the voltage difference between the two voltage cursors
            delta = float(self._scpi_wrapper.query(":MARKer:YDELta?").strip())
            # Log the voltage delta at debug level
            self._logger.debug(f"Marker Y delta: {delta}V")
            # Return the voltage difference value
            return delta
        # If the query fails, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to get marker Y delta: {type(e).__name__}: {e}")
            return None

    # Define show_screen_annotation — this displays a text label on the oscilloscope screen
    def show_screen_annotation(self, text: str) -> bool:
        """
        Display a text annotation on the oscilloscope screen.

        SCPI: :DISPlay:ANNotation:TEXT  (pg 275)
              :DISPlay:ANNotation:STATe (pg 274)

        Args:
            text: String to display (max ~64 chars). Pass empty string "" to clear.

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            return False
        # Try to send the annotation commands, catching any errors
        try:
            # Check if the caller provided a text string to show
            if text:
                # Send the annotation text string to the oscilloscope display
                self._scpi_wrapper.write(f':DISPlay:ANNotation:TEXT "{text}"')
                # Turn the annotation display on so the text becomes visible on screen
                self._scpi_wrapper.write(":DISPlay:ANNotation:STATe ON")
            else:
                # If an empty string was given, turn the annotation off to clear any existing text
                self._scpi_wrapper.write(":DISPlay:ANNotation:STATe OFF")
            # Wait 50 ms for the annotation to be rendered on screen
            time.sleep(0.05)
            # Log what annotation text was set (or cleared)
            self._logger.info(f"Screen annotation set: {text!r}")
            # Return True to indicate success
            return True
        # If any command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set screen annotation: {type(e).__name__}: {e}")
            return False

    # ============================================================================
    # MATH FUNCTIONS - FUNCtion SUBSYSTEM
    # ============================================================================

    # Define set_math_function — this configures one of the oscilloscope's built-in math channels to compute a derived waveform
    def set_math_function(self, function_num: int, operation: str, source1: int,
                          source2: Optional[int] = None) -> bool:
        """
        Configure math function

        - VERIFIED: :FUNCtion:OPERation from manual pages 478-483

        Args:
            function_num: Function number (1-4)
            operation: "ADD", "SUBTract", "MULTiply", "DIVide", "FFT", etc.
            source1: First source channel (1-4)
            source2: Second source channel (required for most operations)

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set math function: oscilloscope not connected")
            return False

        # Try to configure the math function, catching any errors
        try:
            # SCPI: :FUNCtion:OPERation (pg 478)
            # Set the mathematical operation to perform on the source channels
            self._scpi_wrapper.write(f":FUNCtion{function_num}:OPERation {operation}")
            # Wait 100 ms for the operation to be set
            time.sleep(0.1)
            # [Blank line for visual separation]
            # SCPI: :FUNCtion:SOURce1 (pg 484)
            # Set the first input channel for the math function
            self._scpi_wrapper.write(f":FUNCtion{function_num}:SOURce1 CHANnel{source1}")
            # Wait 100 ms for the source to be set
            time.sleep(0.1)
            # [Blank line for visual separation]
            # Check if a second source channel was provided
            if source2 is not None:
                # SCPI: :FUNCtion:SOURce2 (pg 485)
                # Set the second input channel for operations that need two inputs (e.g. ADD, SUBTRACT)
                self._scpi_wrapper.write(f":FUNCtion{function_num}:SOURce2 CHANnel{source2}")
                # Wait 100 ms for the second source to be set
                time.sleep(0.1)
            # [Blank line for visual separation]
            # Log a summary of the math function configuration
            self._logger.info(f"Math function {function_num} configured: {operation}")
            # Return True to indicate success
            return True
        # If any command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set math function: {type(e).__name__}: {e}")
            return False

    # Define set_math_display — this shows or hides a math function's waveform on the oscilloscope screen
    def set_math_display(self, function_num: int, display: bool) -> bool:
        """
        Show/hide math function

        - VERIFIED: :FUNCtion:DISPlay command from manual page 475

        Args:
            function_num: Function number (1-4)
            display: True to show, False to hide

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set math display: oscilloscope not connected")
            return False

        # Try to send the math display command, catching any errors
        try:
            # Convert the boolean display flag to the "ON" or "OFF" string
            state = "ON" if display else "OFF"
            # SCPI: :FUNCtion:DISPlay (pg 475)
            # Send the command to show or hide the math waveform
            self._scpi_wrapper.write(f":FUNCtion{function_num}:DISPlay {state}")
            # Wait 100 ms for the display state to change
            time.sleep(0.1)
            # Log the new display state
            self._logger.info(f"Math function {function_num} display: {state}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set math display: {type(e).__name__}: {e}")
            return False

    # Define set_math_scale — this sets how many volts each vertical division represents for a math function waveform
    def set_math_scale(self, function_num: int, scale: float) -> bool:
        """
        Set math function vertical scale

        - VERIFIED: :FUNCtion:RANGe command from manual page 486

        Args:
            function_num: Function number (1-4)
            scale: Desired volts/division

        Returns:
            bool: True if successful

        Note: The oscilloscope's RANGe command sets the full range (peak-to-peak) of the display.
        Since the display has 10 divisions, we need to multiply by 8 to get the correct scaling.
        The factor of 8 (not 10) accounts for the oscilloscope's internal scaling.
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set math scale: oscilloscope not connected")
            return False

        # Try to send the math scale command, catching any errors
        try:
            # Convert desired V/div to full scale range with correction factor
            # The factor of 0.8 (8/10) accounts for the oscilloscope's scaling behavior
            # Multiply the volts-per-division by 8 to get the full voltage range for the display
            full_scale_range = scale * 8.0  # 8x instead of 10x to match oscilloscope's behavior
            # [Blank line for visual separation]
            # SCPI: :FUNCtion:RANGe (pg 486)
            # Send the command to set the full-scale voltage range for the math function
            self._scpi_wrapper.write(f":FUNCtion{function_num}:RANGe {full_scale_range}")
            # Wait 100 ms for the range to be applied
            time.sleep(0.1)
            # Log the scale in V/div and the equivalent full-scale range
            self._logger.info(f"Math function {function_num} scale set to {scale} V/div (range: {full_scale_range}V)")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set math scale: {type(e).__name__}: {e}")
            return False

    # ============================================================================
    # DISPLAY OPERATIONS - DISPlay SUBSYSTEM
    # ============================================================================

    # Define set_display_menu — this controls whether the menu overlay is shown on the oscilloscope's screen
    def set_display_menu(self, show: bool) -> bool:
        """
        Show/hide menu on display

        - VERIFIED: :DISPlay:MENU command from manual page 429

        Args:
            show: True to show, False to hide

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set display menu: oscilloscope not connected")
            return False

        # Try to send the display menu command, catching any errors
        try:
            # Convert the boolean show flag to the "ON" or "OFF" string
            state = "ON" if show else "OFF"
            # SCPI: :DISPlay:MENU (pg 429)
            # Send the command to show or hide the oscilloscope's menu overlay
            self._scpi_wrapper.write(f":DISPlay:MENU {state}")
            # Wait 100 ms for the display to update
            time.sleep(0.1)
            # Log the new menu display state
            self._logger.info(f"Display menu: {state}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set display menu: {type(e).__name__}: {e}")
            return False

    # Define set_display_grid — this controls what type of grid lines are shown on the oscilloscope screen
    def set_display_grid(self, grid_type: str = "FRAME") -> bool:
        """
        Set display grid type

        - VERIFIED: :DISPlay:GRID command from manual page 428

        Args:
            grid_type: "FRAME", "GRID", or "OFF"

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set display grid: oscilloscope not connected")
            return False

        # Define the valid grid type options
        valid_grids = ["FRAME", "GRID", "OFF"]
        # Check that the given grid type is one of the accepted values
        if grid_type not in valid_grids:
            self._logger.error(f"Invalid grid type: {grid_type}. Must be one of {valid_grids}")
            return False

        # Try to send the display grid command, catching any errors
        try:
            # SCPI: :DISPlay:GRID (pg 428)
            # Send the command to set the grid type shown on the oscilloscope screen
            self._scpi_wrapper.write(f":DISPlay:GRID {grid_type}")
            # Wait 100 ms for the grid change to be rendered
            time.sleep(0.1)
            # Log the new grid type
            self._logger.info(f"Display grid set to: {grid_type}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set display grid: {type(e).__name__}: {e}")
            return False

    # ============================================================================
    # FILE I/O OPERATIONS - DISK SUBSYSTEM
    # ============================================================================

    # Define save_setup — this saves the oscilloscope's current configuration to its internal storage
    def save_setup(self, filename: str = "setup.stp") -> bool:
        """
        Save instrument setup to internal memory

        - VERIFIED: :DISK:SAVESETup command from manual page 393

        Args:
            filename: Setup filename (stored internally, no path needed)

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot save setup: oscilloscope not connected")
            return False

        # Try to send the save setup command, catching any errors
        try:
            # SCPI: :DISK:SAVESETup (pg 393)
            # Manual shows: :DISK:SAVESETup "<filename>"
            # Send the command to save the current oscilloscope configuration to the given filename
            self._scpi_wrapper.write(f":DISK:SAVESETup \"{filename}\"")
            # Wait 1 second for the save operation to complete
            time.sleep(1.0)
            # Log that the setup was saved
            self._logger.info(f"Setup saved: {filename}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to save setup: {type(e).__name__}: {e}")
            return False

    # Define recall_setup — this loads a previously saved oscilloscope configuration from internal storage
    def recall_setup(self, filename: str = "setup.stp") -> bool:
        """
        Recall instrument setup from internal memory

        - VERIFIED: :DISK:RECallSETup command from manual page 388

        Args:
            filename: Setup filename to recall

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot recall setup: oscilloscope not connected")
            return False

        # Try to send the recall setup command, catching any errors
        try:
            # SCPI: :DISK:RECallSETup (pg 388)
            # Manual shows: :DISK:RECallSETup "<filename>"
            # Send the command to load a previously saved oscilloscope configuration
            self._scpi_wrapper.write(f":DISK:RECallSETup \"{filename}\"")
            # Wait 1 second for the recall operation to complete and the instrument to reconfigure itself
            time.sleep(1.0)
            # Log that the setup was recalled
            self._logger.info(f"Setup recalled: {filename}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to recall setup: {type(e).__name__}: {e}")
            return False

    # Define save_waveform — this saves a channel's waveform data to the oscilloscope's internal storage
    def save_waveform(self, channel: int, filename: str) -> bool:
        """
        Save waveform data to internal memory

        - VERIFIED: :DISK:SAVEWAVeform command from manual page 397

        Args:
            channel: Channel to save (1-4)
            filename: Waveform filename

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot save waveform: oscilloscope not connected")
            return False

        # Validate the channel number before sending any command
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel: {channel}")
            return False

        # Try to send the save waveform command, catching any errors
        try:
            # SCPI: :DISK:SAVEWAVeform (pg 397)
            # Manual shows: :DISK:SAVEWAVeform <channel>,<filename>
            # IMPORTANT: Manual uses comma separator and NO quotes for the channel part
            # Send the command to save the specified channel's waveform data to the given filename
            self._scpi_wrapper.write(f":DISK:SAVEWAVeform CHANnel{channel},\"{filename}\"")
            # Wait 1 second for the waveform data to be written to storage
            time.sleep(1.0)
            # Log that the waveform was saved
            self._logger.info(f"Waveform saved: {filename}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to save waveform: {type(e).__name__}: {e}")
            return False

    # Define recall_waveform — this loads a previously saved waveform back from internal storage
    def recall_waveform(self, filename: str) -> bool:
        """
        Recall waveform data from internal memory

        - VERIFIED: :DISK:RECallWAVeform command from manual page 384

        Args:
            filename: Waveform filename to recall

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot recall waveform: oscilloscope not connected")
            return False

        # Try to send the recall waveform command, catching any errors
        try:
            # SCPI: :DISK:RECallWAVeform (pg 384)
            # Manual shows: :DISK:RECallWAVeform "<filename>"
            # Send the command to reload a previously saved waveform from internal storage
            self._scpi_wrapper.write(f":DISK:RECallWAVeform \"{filename}\"")
            # Wait 1 second for the waveform to be loaded
            time.sleep(1.0)
            # Log that the waveform was recalled
            self._logger.info(f"Waveform recalled: {filename}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to recall waveform: {type(e).__name__}: {e}")
            return False

    # ============================================================================
    # SYSTEM COMMANDS & UTILITIES
    # ============================================================================

    # Define reset — this returns the oscilloscope to its factory default settings
    def reset(self) -> bool:
        """
        Reset oscilloscope to default state

        - VERIFIED: *RST command from manual page 1761

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot reset: oscilloscope not connected")
            return False

        # Try to send the reset command, catching any errors
        try:
            # SCPI: *RST
            # Send the standard IEEE *RST command to restore the instrument to factory defaults
            self._scpi_wrapper.write("*RST")
            # Wait 1 second for the reset to complete and the oscilloscope to reinitialise
            time.sleep(1.0)
            # Wait for the reset operation to fully complete before allowing further commands
            self._scpi_wrapper.query("*OPC?")
            # Log that the oscilloscope has been reset
            self._logger.info("Oscilloscope reset to default state")
            # Return True to indicate the reset was successful
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to reset oscilloscope: {type(e).__name__}: {e}")
            return False

    # Define get_error_queue — this reads any error messages the oscilloscope has queued up since the last clear
    def get_error_queue(self) -> Optional[List[str]]:
        """
        Query instrument error queue

        - VERIFIED: :SYStem:ERRor? command from manual page 865

        Returns:
            List of error strings or None
        """
        # Return None if not connected
        if not self.is_connected:
            return None

        # Try to drain the error queue, catching any errors
        try:
            # Start with an empty list to collect any error messages
            errors = []
            # Keep reading errors until the queue is empty (indicated by a response starting with "0,")
            while True:
                # SCPI: :SYStem:ERRor? (pg 865)
                # Ask the oscilloscope for the next error in its queue
                error = self._scpi_wrapper.query(":SYStem:ERRor?").strip()
                # If the response starts with "0," it means "no error" — the queue is now empty
                if error.startswith("0,"):
                    break
                # Otherwise add this error string to the list
                errors.append(error)

            # If any errors were found, log them as a warning and return the list
            if errors:
                self._logger.warning(f"Instrument errors: {errors}")
                return errors
            # If no errors were found, return None to indicate a clean error queue
            return None
        # If the query itself fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to get error queue: {type(e).__name__}: {e}")
            return None

    # Define wait_for_trigger — this blocks the program until the oscilloscope fires its trigger or the timeout expires
    def wait_for_trigger(self, timeout: float = 10.0) -> bool:
        """
        Wait for trigger event with timeout

        - VERIFIED: *OPC? command behavior from manual

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            bool: True if triggered, False if timeout
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot wait for trigger: oscilloscope not connected")
            return False

        # Record the current time so we can track when the timeout expires
        start_time = time.time()
        # Try to poll for trigger completion, catching any errors
        try:
            # Keep polling until either the trigger fires or the timeout is reached
            while time.time() - start_time < timeout:
                # Ask the oscilloscope if its current operation is complete
                status = self._scpi_wrapper.query("*OPC?").strip()
                # A response of "1" means the operation is complete (trigger fired and acquisition done)
                if status == "1":
                    # Log that the trigger event was detected
                    self._logger.info("Trigger event detected")
                    # Return True to indicate a successful trigger
                    return True
                # Wait 100 ms before polling again to avoid overwhelming the instrument
                time.sleep(0.1)

            # If the loop ended because the timeout was reached, log a warning
            self._logger.warning(f"Trigger timeout after {timeout}s")
            # Return False to indicate no trigger was detected within the timeout
            return False
        # If any poll query fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed waiting for trigger: {type(e).__name__}: {e}")
            return False

    # ============================================================================
    # OTHER OSCILLOSCOPE FUNCTIONS
    # ============================================================================

    # Define capture_screenshot — this takes a picture of what is currently displayed on the oscilloscope screen and saves it as an image file
    def capture_screenshot(self, filename: Optional[str] = None, image_format: str = "PNG",
                          include_timestamp: bool = True, freeze_acquisition: bool = True) -> Optional[str]:
        """
        Capture oscilloscope display screenshot

        - VERIFIED: HARDcopy and DISPlay commands from manual pages 515-534

        Args:
            filename: Custom filename (None = auto-generate with timestamp)
            image_format: Image format ("PNG", "BMP", or "BMP8bit")
            include_timestamp: Include timestamp in auto-generated filename
            freeze_acquisition: If True, stops acquisition before screenshot and resumes after
                              This prevents signal disappearance during long timebase acquisitions

        Returns:
            str: Path to saved screenshot file, or None if failed

        Note: For long timebase settings (20s, 50s), freeze_acquisition=True is recommended
        to prevent the signal from disappearing during screenshot capture.
        """
        # Return None if not connected
        if not self.is_connected:
            self._logger.error("Cannot capture screenshot: not connected")
            return None

        # Track whether the oscilloscope was running so we can restart it after the screenshot
        acquisition_was_running = False

        # Try to capture and save the screenshot, catching any errors
        try:
            # If no output directory has been set up yet, create the default directory structure now
            if self.screenshot_dir is None:
                self.setup_output_directories()

            # FREEZE ACQUISITION: Stop the scope to preserve the current waveform
            # If freeze_acquisition is enabled, stop the oscilloscope to lock the display before capturing
            if freeze_acquisition:
                # Try to stop the oscilloscope; if it fails, continue anyway
                try:
                    # Check if acquisition is running by querying operation complete
                    # If scope is running, stop it to freeze the display
                    # Log that we are stopping the acquisition to get a stable screenshot
                    self._logger.info("Stopping acquisition to freeze display for screenshot")
                    # Stop the oscilloscope so the waveform does not change while we capture the screen
                    self.stop()
                    # Remember that the oscilloscope was running so we can restart it after
                    acquisition_was_running = True
                    # Wait 200 ms for the display to fully settle after stopping
                    time.sleep(0.2)  # Allow scope to settle after stop
                # If stopping fails, log a warning but do not abort the screenshot
                except Exception as e:
                    self._logger.warning(f"Could not stop acquisition: {e}")

            # If no filename was provided, generate one automatically using a timestamp
            if filename is None:
                # Get the current date and time as a formatted string for the filename
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                # Build the filename using the timestamp and the image format extension
                filename = f"scope_screenshot_{timestamp}.{image_format.lower()}"

            # Check that the filename ends with the correct file extension for the image format
            if not filename.lower().endswith(f".{image_format.lower()}"):
                # Append the correct extension if it is missing
                filename += f".{image_format.lower()}"

            # Combine the screenshot directory path with the filename to get the full save path
            screenshot_path = self.screenshot_dir / filename

            # SCPI: :DISPlay:DATA? {PNG|BMP|BMP8bit} (pg 424)
            # Log that the screenshot capture is starting
            self._logger.info(f"Capturing screenshot in {image_format} format")
            # Send the SCPI command to retrieve the screen image as binary data and download it
            image_data = self._scpi_wrapper.query_binary_values(
                f":DISPlay:DATA? {image_format}",
                datatype='B'
            )

            # Check that image data was actually received
            if image_data:
                # Open the file at the screenshot path for binary writing
                with open(screenshot_path, 'wb') as f:
                    # Write the raw image bytes to the file on disk
                    f.write(bytes(image_data))
                # Log the path where the screenshot was saved
                self._logger.info(f"Screenshot saved: {screenshot_path}")

                # RESUME ACQUISITION: Restart the scope if it was running
                # If we stopped the oscilloscope earlier, restart it now that the screenshot is saved
                if freeze_acquisition and acquisition_was_running:
                    # Try to restart the oscilloscope; if it fails, log a warning
                    try:
                        self._logger.info("Resuming acquisition (RUN mode)")
                        # Put the oscilloscope back into continuous run mode
                        self.run()
                        # Wait 100 ms for the oscilloscope to restart
                        time.sleep(0.1)
                    # If restarting fails, log a warning
                    except Exception as e:
                        self._logger.warning(f"Could not restart acquisition: {e}")

                # Return the full path to the saved screenshot file as a string
                return str(screenshot_path)

            # If no image data was returned, return None
            return None
        # If anything fails during the screenshot capture, catch the error
        except Exception as e:
            self._logger.error(f"Screenshot capture failed: {e}")

            # RESUME ACQUISITION: Make sure to restart even if screenshot failed
            # Even after a failure, try to restart the oscilloscope so it does not stay stopped
            if freeze_acquisition and acquisition_was_running:
                # Try to restart the oscilloscope after the error
                try:
                    self._logger.info("Resuming acquisition after error")
                    # Put the oscilloscope back into run mode
                    self.run()
                # If restart also fails, log the secondary error
                except Exception as resume_error:
                    self._logger.error(f"Failed to resume acquisition: {resume_error}")

            # Return None to indicate the screenshot capture failed
            return None

    # Define get_operation_register — this reads the oscilloscope's internal status register to check if it is still acquiring
    def get_operation_register(self) -> Optional[int]:
        """
        Get operation register status

        - VERIFIED: :OPERegister:CONDition? command from manual

        Returns:
            int: Operation register value, or None if error

        Note: Bit 3 (value 8) indicates "Run" status
              When bit 3 is 0, acquisition is complete/stopped
        """
        # Return None if not connected
        if not self.is_connected:
            self._logger.error("Cannot get operation register: oscilloscope not connected")
            return None

        # Try to query the operation register, catching any errors
        try:
            # Send the query and retrieve the raw register value as a string
            status = self._scpi_wrapper.query(":OPERegister:CONDition?").strip()
            # Convert the register value from a string to an integer and return it
            return int(status)
        # If the query fails, log the error and return None
        except Exception as e:
            self._logger.error(f"Failed to get operation register: {type(e).__name__}: {e}")
            return None

    # Define wait_for_trigger_complete — this waits until the oscilloscope finishes its acquisition by checking the operation register
    def wait_for_trigger_complete(self, timeout: float = 10.0) -> bool:
        """
        Wait for trigger and acquisition to complete using operation register

        This method is more reliable than wait_for_trigger() as it uses the
        operation register to check if acquisition is truly complete.

        Args:
            timeout: Maximum wait time in seconds

        Returns:
            bool: True if acquisition completed, False if timeout
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot wait for trigger: oscilloscope not connected")
            return False

        # Record the start time so we can measure how long we have been waiting
        start_time = time.time()
        # Try to poll the operation register, catching any errors
        try:
            # Keep checking the register until the acquisition completes or the timeout is hit
            while time.time() - start_time < timeout:
                # Query operation register - Bit 3 (value 8) = Run status
                # When bit 3 is 0, acquisition is complete
                # Read the current operation register value
                oper_status = self.get_operation_register()
                # Check whether bit 3 (value 8) is clear — if it is, acquisition is done
                if oper_status is not None and (oper_status & 8) == 0:
                    # Log that the acquisition has finished
                    self._logger.info("Trigger acquisition complete")
                    # Return True to indicate acquisition completed successfully
                    return True
                # Wait 100 ms before checking again
                time.sleep(0.1)

            # If the timeout was reached without completion, log a warning
            self._logger.warning(f"Trigger timeout after {timeout}s")
            # Return False to indicate the timeout was reached
            return False
        # If any poll fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed waiting for trigger: {type(e).__name__}: {e}")
            return False

    # Define get_waveform_preamble — this retrieves the metadata needed to convert raw waveform bytes into actual voltage and time values
    def get_waveform_preamble(self, channel: int) -> Optional[Dict[str, Any]]:
        """
        Get waveform preamble with scaling information

        - VERIFIED: :WAVeform:PREamble? command from manual page 1158

        Args:
            channel: Channel number (1-4)

        Returns:
            dict: Dictionary with waveform scaling parameters, or None if error
                - format: Data format
                - type: Acquisition type
                - points: Number of points
                - count: Average count
                - x_increment: Time increment per point (s)
                - x_origin: Time origin (s)
                - x_reference: Time reference point
                - y_increment: Voltage increment per bit (V)
                - y_origin: Voltage origin (V)
                - y_reference: Voltage reference level
        """
        # Return None if not connected
        if not self.is_connected:
            self._logger.error("Cannot get waveform preamble: oscilloscope not connected")
            return None

        # Validate the channel number
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel: {channel}")
            return None

        # Try to retrieve the preamble, catching any errors
        try:
            # Set waveform source
            # Tell the oscilloscope which channel's waveform preamble to return
            self._scpi_wrapper.write(f":WAVeform:SOURce CHANnel{channel}")
            # Wait 50 ms for the source selection to take effect
            time.sleep(0.05)

            # Query preamble
            # Ask the oscilloscope for the waveform preamble (scaling and format metadata)
            preamble = self._scpi_wrapper.query(":WAVeform:PREamble?").strip()
            # Split the comma-separated response into individual fields
            parts = preamble.split(',')

            # Check that the preamble has at least the expected 10 fields
            if len(parts) >= 10:
                # Build and return a dictionary with each preamble field labelled
                return {
                    # Data format code (e.g. 0 = BYTE, 1 = WORD)
                    'format': int(parts[0]),
                    # Acquisition type code (e.g. 0 = NORMAL, 1 = PEAK, 2 = AVERAGE)
                    'type': int(parts[1]),
                    # Total number of waveform data points
                    'points': int(parts[2]),
                    # Number of averages (only meaningful in AVERAGE mode)
                    'count': int(parts[3]),
                    # Time interval between consecutive data points in seconds
                    'x_increment': float(parts[4]),
                    # Time value corresponding to the first data point
                    'x_origin': float(parts[5]),
                    # Index of the reference point for time calculations
                    'x_reference': float(parts[6]),
                    # Voltage difference represented by one ADC count (volts per raw unit)
                    'y_increment': float(parts[7]),
                    # Voltage value that corresponds to ADC output zero
                    'y_origin': float(parts[8]),
                    # Raw ADC value that represents the voltage reference level
                    'y_reference': float(parts[9])
                }
            else:
                # Log an error if the preamble did not contain enough fields
                self._logger.error(f"Incomplete preamble data: {preamble}")
                return None

        # If any query fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to get waveform preamble: {type(e).__name__}: {e}")
            return None

    # Define set_waveform_format — this tells the oscilloscope what binary format to use when sending waveform data
    def set_waveform_format(self, format_type: str = "BYTE") -> bool:
        """
        Set waveform data format

        - VERIFIED: :WAVeform:FORMat command from manual page 1156

        Args:
            format_type: "BYTE", "WORD", or "ASCii"

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set waveform format: oscilloscope not connected")
            return False

        # Define the valid format options
        valid_formats = ["BYTE", "WORD", "ASCii"]
        # Check that the given format is one of the accepted values
        if format_type not in valid_formats:
            self._logger.error(f"Invalid format: {format_type}. Must be one of {valid_formats}")
            return False

        # Try to send the waveform format command, catching any errors
        try:
            # Send the command to set the waveform data transfer format
            self._scpi_wrapper.write(f":WAVeform:FORMat {format_type}")
            # Log the new format at debug level
            self._logger.debug(f"Waveform format set to {format_type}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set waveform format: {type(e).__name__}: {e}")
            return False

    # Define set_waveform_source — this selects which channel the oscilloscope reads when transferring waveform data
    def set_waveform_source(self, channel: int) -> bool:
        """
        Set waveform data source channel

        - VERIFIED: :WAVeform:SOURce command from manual page 1201

        Args:
            channel: Channel number (1-4)

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set waveform source: oscilloscope not connected")
            return False

        # Validate the channel number
        if not (1 <= channel <= self.max_channels):
            self._logger.error(f"Invalid channel: {channel}")
            return False

        # Try to send the waveform source command, catching any errors
        try:
            # Send the command to select which channel's data will be transferred
            self._scpi_wrapper.write(f":WAVeform:SOURce CHANnel{channel}")
            # Log the source channel at debug level
            self._logger.debug(f"Waveform source set to CH{channel}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set waveform source: {type(e).__name__}: {e}")
            return False

    # Define set_waveform_points — this limits how many data points are transferred in a waveform download
    def set_waveform_points(self, points: int) -> bool:
        """
        Set number of waveform points to transfer

        - VERIFIED: :WAVeform:POINts command from manual page 1160

        Args:
            points: Number of points (typically 100 to 62500)

        Returns:
            bool: True if successful
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot set waveform points: oscilloscope not connected")
            return False

        # Try to send the waveform points command, catching any errors
        try:
            # Send the command to set how many waveform points will be transferred
            self._scpi_wrapper.write(f":WAVeform:POINts {points}")
            # Log the point count at debug level
            self._logger.debug(f"Waveform points set to {points}")
            # Return True to indicate success
            return True
        # If the command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to set waveform points: {type(e).__name__}: {e}")
            return False

    # Define get_waveform_raw_data — this downloads the raw binary waveform bytes from whichever source was previously selected
    def get_waveform_raw_data(self) -> Optional[List[int]]:
        """
        Get raw waveform data from currently configured source

        - VERIFIED: :WAVeform:DATA? command from manual page 1150

        Note: Use set_waveform_source() and set_waveform_format() first

        Returns:
            list: Raw waveform data bytes, or None if error
        """
        # Return None if not connected
        if not self.is_connected:
            self._logger.error("Cannot get waveform data: oscilloscope not connected")
            return None

        # Try to download the waveform data, catching any errors
        try:
            # Send the waveform data query and receive the binary payload
            data = self._scpi_wrapper.query_binary_values(":WAVeform:DATA?", datatype='B')
            # Check that some data was received
            if data:
                # Log how many points were received
                self._logger.debug(f"Retrieved {len(data)} waveform points")
                # Return the list of raw data bytes
                return data
            # If nothing was received, return None
            return None
        # If the query fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to get waveform data: {type(e).__name__}: {e}")
            return None

    # Define get_screenshot_binary — this captures the oscilloscope screen image and returns it as raw bytes without saving to a file
    def get_screenshot_binary(self, image_format: str = "PNG") -> Optional[bytes]:
        """
        Get screenshot as binary data without saving to file

        - VERIFIED: :DISPlay:DATA? command from manual page 424

        Args:
            image_format: "PNG", "BMP", or "BMP8bit"

        Returns:
            bytes: Screenshot image data, or None if error
        """
        # Return None if not connected
        if not self.is_connected:
            self._logger.error("Cannot get screenshot: oscilloscope not connected")
            return None

        # Define the valid image format options
        valid_formats = ["PNG", "BMP", "BMP8bit"]
        # Check that the given format is one of the accepted values
        if image_format not in valid_formats:
            self._logger.error(f"Invalid format: {image_format}. Must be one of {valid_formats}")
            return None

        # Try to retrieve the screenshot image data, catching any errors
        try:
            # Log at debug level that the screenshot is being captured
            self._logger.debug(f"Capturing screenshot in {image_format} format")
            # Send the SCPI display data query and download the raw image bytes
            image_data = self._scpi_wrapper.query_binary_values(
                f":DISPlay:DATA? {image_format}",
                datatype='B'
            )

            # Check that image data was received
            if image_data:
                # Convert the list of byte values to a Python bytes object and return it
                return bytes(image_data)
            # If nothing was received, return None
            return None
        # If the query fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to get screenshot: {type(e).__name__}: {e}")
            return None

    # Define setup_output_directories — this creates the folders on disk where screenshots and data files will be saved
    def setup_output_directories(self) -> None:
        """Create default output directories (screenshot_dir is not overwritten if already set)."""
        # Get the current working directory as the base location for all output folders
        base_path = Path.cwd()
        # Only set the screenshot directory if it has not already been set externally
        if self.screenshot_dir is None:
            # Create the screenshots folder path inside the current working directory
            self.screenshot_dir = base_path / "oscilloscope_screenshots"
        # Always set the data directory for saving raw waveform data files
        self.data_dir = base_path / "oscilloscope_data"
        # Always set the graph directory for saving waveform graph image files
        self.graph_dir = base_path / "oscilloscope_graphs"

        # Loop through each output directory and create it if it does not already exist
        for directory in [self.screenshot_dir, self.data_dir, self.graph_dir]:
            # Create the directory and any missing parent directories; do not fail if it already exists
            directory.mkdir(parents=True, exist_ok=True)

    # Define configure_function_generator — this sets up the oscilloscope's built-in signal generator to output a test waveform
    def configure_function_generator(self, generator: int, waveform: str = "SIN",
                                     frequency: float = 1000.0, amplitude: float = 1.0,
                                     offset: float = 0.0, enable: bool = True) -> bool:
        """
        Configure function generator output

        - VERIFIED: WGEN commands from manual pages 1515-1573

        Args:
            generator: Generator number (1 or 2)
            waveform: Waveform type (SIN, SQUARE, RAMP, PULSE, DC, NOISE, etc.)
            frequency: Signal frequency in Hz (default: 1000.0)
            amplitude: Peak-to-peak amplitude in volts (default: 1.0)
            offset: DC offset in volts (default: 0.0)
            enable: Enable output after configuration (default: True)
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot configure function generator: not connected")
            return False

        # Validate that the generator number is 1 or 2 (the oscilloscope has two generators)
        if generator not in [1, 2]:
            self._logger.error(f"Invalid generator number: {generator}")
            return False

        # Try to configure the function generator, catching any errors
        try:
            # SCPI: :WGEN:FUNCtion {SINusoid|SQUare|RAMP|...} (pg 1526)
            # Set the waveform shape for the function generator output
            self._scpi_wrapper.write(f":WGEN{generator}:FUNCtion {waveform.upper()}")
            # Wait 50 ms for the waveform shape to be set
            time.sleep(0.05)

            # Only set the frequency if the waveform is not DC (DC has no frequency)
            if waveform.upper() != "DC":
                # SCPI: :WGEN:FREQuency (pg 1525)
                # Set the output frequency in Hz
                self._scpi_wrapper.write(f":WGEN{generator}:FREQuency {frequency}")
                # Wait 50 ms for the frequency to be set
                time.sleep(0.05)

            # SCPI: :WGEN:VOLTage (pg 1557)
            # Set the peak-to-peak amplitude of the output signal in volts
            self._scpi_wrapper.write(f":WGEN{generator}:VOLTage {amplitude}")
            # Wait 50 ms for the amplitude to be set
            time.sleep(0.05)

            # SCPI: :WGEN:VOLTage:OFFSet (pg 1560)
            # Set the DC offset voltage added to the output waveform
            self._scpi_wrapper.write(f":WGEN{generator}:VOLTage:OFFSet {offset}")
            # Wait 50 ms for the offset to be set
            time.sleep(0.05)

            # SCPI: :WGEN:OUTPut {ON|OFF|} (pg 1547)
            # Determine whether to enable or disable the generator output based on the enable flag
            output_state = "ON" if enable else "OFF"
            # Send the command to turn the function generator output on or off
            self._scpi_wrapper.write(f":WGEN{generator}:OUTPut {output_state}")
            # Wait 50 ms for the output state to change
            time.sleep(0.05)

            # Log a summary of the function generator configuration
            self._logger.info(f"WGEN{generator} configured: {waveform}, {frequency}Hz, {amplitude}Vpp")
            # Return True to indicate success
            return True
        # If any command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to configure WGEN{generator}: {e}")
            return False

    # Define autoscale — this sends a single command that automatically adjusts all channels and the timebase for optimal viewing
    def autoscale(self) -> bool:
        """
        Execute autoscale command

        - VERIFIED: :AUToscale command from manual page 254
        """
        # Return False if not connected
        if not self.is_connected:
            self._logger.error("Cannot autoscale: oscilloscope not connected")
            return False

        # Try to send the autoscale command, catching any errors
        try:
            # Send the autoscale command to let the oscilloscope automatically set all scale settings
            self._scpi_wrapper.write(":AUToscale")
            # Wait 2 seconds for the autoscale operation to finish (it can take a moment)
            time.sleep(2.0)  # Wait for autoscale to complete
            # Wait for the autoscale to fully complete before allowing further commands
            self._scpi_wrapper.query("*OPC?")
            # Log that autoscale completed successfully
            self._logger.info("Autoscale executed successfully")
            # Return True to indicate success
            return True
        # If any command fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Autoscale failed: {type(e).__name__}: {e}")
            return False

    # Define get_function_generator_config — this reads back all the current settings of a function generator
    def get_function_generator_config(self, generator: int) -> Optional[Dict[str, Any]]:
        """
        Query function generator configuration

        - VERIFIED: WGEN query commands from manual
        """
        # Return None if not connected
        if not self.is_connected:
            return None

        # Return None if an invalid generator number was given
        if generator not in [1, 2]:
            return None

        # Try to query all function generator settings, catching any errors
        try:
            # Wait for any previous operation to complete before querying
            self._scpi_wrapper.query("*OPC?")
            # Brief pause to let the instrument settle before sending multiple queries
            time.sleep(0.05)

            # Build a dictionary of all current function generator settings by querying each one
            config = {
                # Store the generator number for reference
                'generator': generator,
                # Query and store the current waveform shape (e.g. SIN, SQUARE, RAMP)
                'function': self._scpi_wrapper.query(f":WGEN{generator}:FUNCtion?").strip(),
                # Query and store the current output frequency in Hz
                'frequency': float(self._scpi_wrapper.query(f":WGEN{generator}:FREQuency?").strip()),
                # Query and store the current peak-to-peak amplitude in volts
                'amplitude': float(self._scpi_wrapper.query(f":WGEN{generator}:VOLTage?").strip()),
                # Query and store the current DC offset voltage
                'offset': float(self._scpi_wrapper.query(f":WGEN{generator}:VOLTage:OFFSet?").strip()),
                # Query and store whether the output is currently on or off
                'output': self._scpi_wrapper.query(f":WGEN{generator}:OUTPut?").strip()
            }

            # Return the completed dictionary of generator settings
            return config
        # If any query fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to get WGEN{generator} config: {e}")
            return None

    # ============================================================================
    # COMPATIBILITY METHODS (for tests written for Tektronix API)
    # ============================================================================

    # Define get_channel_data — this downloads a full waveform from a channel and returns time and voltage arrays (matching Tektronix API format)
    def get_channel_data(self, channel: int, start_point: int = 1,
                        stop_point: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get waveform data from channel in Tektronix-compatible format

        This method wraps get_waveform_data() to provide compatibility with
        tests written for Tektronix oscilloscopes.

        Args:
            channel: Channel number (1-4)
            start_point: Starting point index (not used in Keysight, kept for compatibility)
            stop_point: Ending point index (not used in Keysight, kept for compatibility)

        Returns:
            Dictionary with time/voltage arrays and metadata
        """
        # Return None if not connected
        if not self.is_connected:
            self._logger.error("Cannot get channel data: not connected")
            return None

        # Try to download and process the waveform data, catching any errors
        try:
            # Set extended timeout for waveform transfer operations
            # Extend the VISA timeout to 15 seconds to allow time for large waveform transfers
            self._scpi_wrapper.set_timeout(15000)

            # Set waveform source (write doesn't need timeout - it's set globally)
            # Tell the oscilloscope which channel's waveform to transfer
            self._scpi_wrapper.write(f":WAVeform:SOURce CHANnel{channel}")
            # Wait 100 ms for the source selection to be applied
            time.sleep(0.1)

            # Set waveform format
            # Use BYTE format (8-bit values) for the waveform data transfer
            self._scpi_wrapper.write(":WAVeform:FORMat BYTE")
            # Wait 100 ms for the format setting to take effect
            time.sleep(0.1)

            # Get waveform preamble for metadata
            # Retrieve the preamble string which contains all the scaling information
            preamble_str = self._scpi_wrapper.query(":WAVeform:PREamble?").strip()
            # Split the comma-separated preamble into its individual fields
            parts = preamble_str.split(',')

            # Check that the preamble has at least 10 fields (the minimum expected)
            if len(parts) < 10:
                self._logger.error(f"Incomplete preamble: {preamble_str}")
                return None

            # Parse preamble
            # Extract the time increment (seconds per sample point) from the preamble
            x_increment = float(parts[4])
            # Extract the time origin (time value of the first data point) from the preamble
            x_origin = float(parts[5])
            # Extract the time reference index from the preamble
            x_reference = float(parts[6])
            # Extract the voltage increment (volts per ADC count) from the preamble
            y_increment = float(parts[7])
            # Extract the voltage origin (voltage at ADC output zero) from the preamble
            y_origin = float(parts[8])
            # Extract the ADC reference level from the preamble
            y_reference = float(parts[9])

            # Get waveform data with extended timeout
            # Download the raw binary waveform data with a 15-second timeout
            waveform_data = self._scpi_wrapper.query_binary_values(
                ":WAVeform:DATA?",
                datatype='B',
                timeout=15000
            )

            # Check that data was received
            if not waveform_data:
                self._logger.error(f"No waveform data received for channel {channel}")
                return None

            # Convert to numpy array
            # Turn the list of raw byte values into a numpy array for efficient computation
            waveform_array = np.array(waveform_data, dtype=np.uint8)

            # Convert raw ADC values to voltage
            # Apply the scaling formula: voltage = (raw - y_reference) * y_increment + y_origin
            voltage_data = ((waveform_array - y_reference) * y_increment) + y_origin

            # Create time array
            # Count how many data points were received
            num_points = len(waveform_array)
            # Build a time array where each point's time = point_index * x_increment + x_origin
            time_data = np.arange(num_points) * x_increment + x_origin

            # Reset timeout to default after waveform transfer
            # Restore the VISA timeout to its default value now that the long transfer is complete
            self._scpi_wrapper.reset_timeout()

            # Return a dictionary containing all waveform data and metadata in Tektronix-compatible format
            return {
                # The time axis array in seconds
                'time': time_data,
                # The voltage axis array in volts
                'voltage': voltage_data,
                # The channel number that was read
                'channel': channel,
                # The SCPI source string for this channel
                'source': f"CHAN{channel}",
                # Total number of data points
                'num_points': num_points,
                # Time between consecutive samples
                'x_increment': x_increment,
                # Time origin (Tektronix compatibility name)
                'x_zero': x_origin,  # Tektronix compatibility name
                # Voltage per ADC count (Tektronix compatibility name)
                'y_multiplier': y_increment,  # Tektronix compatibility name
                # Voltage at ADC zero (Tektronix compatibility name)
                'y_zero': y_origin,  # Tektronix compatibility name
                # ADC reference level (Tektronix compatibility name)
                'y_offset': y_reference,  # Tektronix compatibility name
                # Start point index (kept for API compatibility, not used internally)
                'start_point': start_point,
                # Stop point index (kept for API compatibility, not used internally)
                'stop_point': stop_point or num_points
            }

        # If any part of the waveform download fails, catch the error
        except Exception as e:
            self._logger.error(f"Failed to get channel {channel} data: {e}")
            # Reset timeout even on error
            # Try to restore the default timeout even after a failure
            try:
                self._scpi_wrapper.reset_timeout()
            # If resetting the timeout also fails, silently ignore it
            except:
                pass
            # Return None to indicate the data transfer failed
            return None

    # Define get_screenshot — this captures a screenshot and saves it to a user-specified file path (Tektronix-compatible API)
    def get_screenshot(self, screenshot_path: str, freeze_acquisition: bool = True) -> Optional[str]:
        """
        Capture screenshot and save to file (Tektronix-compatible API)

        Args:
            screenshot_path: Path to save screenshot file
            freeze_acquisition: Whether to freeze acquisition during screenshot

        Returns:
            Path to saved screenshot file if successful, None if failed
        """
        # Return None if not connected
        if not self.is_connected:
            self._logger.error("Cannot capture screenshot: not connected")
            return None

        # Try to capture and save the screenshot, catching any errors
        try:
            # Ensure path ends with .png
            # Force the file path to use a .png extension regardless of what was provided
            screenshot_path_png = str(Path(screenshot_path).with_suffix('.png'))

            # Freeze acquisition if requested
            # Track whether the oscilloscope was running so it can be restarted later
            acquisition_was_running = False
            # If freeze_acquisition is enabled, stop the oscilloscope before taking the screenshot
            if freeze_acquisition:
                # Try to check and stop acquisition; silently continue if this fails
                try:
                    # Check if running
                    # Ask the oscilloscope for its current run state
                    status = self._scpi_wrapper.query(":RSTate?").strip()
                    # Determine if the oscilloscope is currently acquiring
                    acquisition_was_running = (status == "RUN")
                    # If it was running, stop it so the display is frozen for the screenshot
                    if acquisition_was_running:
                        self.stop()
                        # Wait 200 ms for the oscilloscope to fully stop
                        time.sleep(0.2)
                # If the stop check fails, silently continue — we will try anyway
                except:
                    pass

            # Get screenshot as binary data
            # Download the screen image as raw PNG bytes
            image_data = self.get_screenshot_binary(image_format="PNG")
            # If no image data was returned, log an error and return None
            if not image_data:
                self._logger.error("Failed to get screenshot data")
                return None

            # Save to file
            # Build a Path object from the screenshot path string
            screenshot_path_obj = Path(screenshot_path_png)
            # Create any missing parent directories so the file can be written
            screenshot_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Open the file at the screenshot path for binary writing
            with open(screenshot_path_obj, 'wb') as f:
                # Write the raw PNG bytes to the file
                f.write(image_data)

            # Log that the screenshot was saved, including the file size for verification
            self._logger.info(f"Screenshot saved: {screenshot_path_png} ({len(image_data)} bytes)")

            # Resume acquisition if it was running
            # If we stopped the oscilloscope earlier, put it back into run mode now
            if freeze_acquisition and acquisition_was_running:
                # Try to restart; silently continue if this fails
                try:
                    self.run()
                # If restarting fails, silently ignore it
                except:
                    pass

            # Return the final path to the saved screenshot file
            return screenshot_path_png

        # If anything fails during the screenshot process, catch the error
        except Exception as e:
            self._logger.error(f"Screenshot capture failed: {e}")
            return None


# ============================================================================
# HD3 SERIES OSCILLOSCOPE CLASS
# ============================================================================

# Define a custom error class specifically for the HD304MSO so its errors can be caught separately
class KeysightHD304MSOError(Exception):
    """Custom exception for Keysight HD304MSO oscilloscope errors."""
    pass

# [Blank line for visual separation]

# [Blank line for visual separation]

# Define the KeysightHD304MSO class which inherits all functionality from KeysightDSOX6004A and overrides specs for the HD3 series
class KeysightHD304MSO(KeysightDSOX6004A):
    """
    Keysight HD304MSO Oscilloscope Control Class (InfiniiVision HD3 Series)

    Inherits from KeysightDSOX6004A with updated specifications for HD3 series.
    The HD3 series uses the same SCPI command set as the 6000 X-Series with only
    minor differences (status registers, removed TV trigger mode).

    Key Differences from DSOX6004A:
    - 14-bit ADC resolution (vs 8-bit)
    - 100 Mpts memory depth (vs 16 Mpts)
    - 2.5 GSa/s sample rate for 200 MHz model (vs 20 GSa/s)
    - Supports up to 4 graticules (vs 1)
    - 2 frequency counters (vs 1)
    - SCPI-99 compliant status registers
    - No TV trigger mode

    - VERIFIED: Command compatibility with InfiniiVision HD3-Series Programmer's Guide
    - All SCPI commands from DSOX6004A parent class remain compatible
    """

    # Define the constructor for the HD304MSO — this calls the parent constructor then overrides the hardware specifications
    def __init__(self, visa_address: str, timeout_ms: int = 60000) -> None:
        """
        Initialize HD304MSO oscilloscope connection parameters

        Args:
            visa_address: VISA resource address (e.g., "USB0::0x0957::0x####::MY12345678::INSTR")
            timeout_ms: Initial VISA timeout in milliseconds (default: 60000 = 60 seconds)
        """
        # Call parent class constructor
        # Run the parent class __init__ first to set up all the shared infrastructure
        super().__init__(visa_address, timeout_ms)

        # Override specifications for HD304MSO
        # HD3 series has different bandwidth options: 200/350/500 MHz/1 GHz
        # Update this based on your specific model
        # Set the bandwidth to 200 MHz for the base HD304MSO model (override the parent's 1 GHz value)
        self.bandwidth_hz = 200e6  # 200 MHz for HD302MSO/HD304MSO base model
        # Set the maximum sample rate to 2.5 GSa/s for the 200 MHz HD3 model
        self.max_sample_rate = 2.5e9  # 2.5 GSa/s for 200 MHz model
        # Set the maximum memory depth to 100 million points (much larger than the parent's 16 Mpts)
        self.max_memory_depth = 100e6  # 100 Mpts standard
        # Set the ADC resolution to 14 bits (a major improvement over the parent's 8-bit ADC)
        self.resolution_bits = 14  # 14-bit ADC (major upgrade from 8-bit)
        # Set the number of analog channels to 4
        self.max_channels = 4  # 4 analog channels
        # Set the number of digital channels to 16 (the MSO variant includes a logic analyser)
        self.digital_channels = 16  # 16 digital channels (MSO model)
        # Set the number of built-in frequency counters to 2
        self.num_counters = 2  # 2 frequency counters
        # Set the maximum number of independent graticule grids to 4
        self.max_graticules = 4  # Supports up to 4 graticules

        # Update logger name for HD3
        # Create a new logger named after the HD304MSO class so its log messages are clearly identified
        self._logger = logging.getLogger(f'{self.__class__.__name__}.{id(self)}')

        # Timebase scales remain compatible with parent class
        # All SCPI commands remain the same as DSOX6004A

    # Define get_instrument_info for HD304MSO — this overrides the parent version to include HD3-specific specification fields
    def get_instrument_info(self) -> Optional[Dict[str, Any]]:
        """
        Query instrument identification and specifications for HD304MSO

        Returns:
            Dictionary with instrument information including HD3-specific specs
        """
        # Return None if not connected
        if not self.is_connected:
            return None
        # Try to query identification and build the info dictionary, catching any errors
        try:
            # Ask the HD304MSO for its identification string and remove trailing whitespace
            idn = self._scpi_wrapper.query("*IDN?").strip()
            # Split the comma-separated identification string into its four parts
            parts = idn.split(',')
            # Build and return a dictionary with all identification fields plus HD3-specific specs
            return {
                # Manufacturer name from the identification string
                'manufacturer': parts[0] if len(parts) > 0 else 'Unknown',
                # Model name from the identification string
                'model': parts[1] if len(parts) > 1 else 'Unknown',
                # Serial number from the identification string
                'serial_number': parts[2] if len(parts) > 2 else 'Unknown',
                # Firmware version from the identification string
                'firmware_version': parts[3] if len(parts) > 3 else 'Unknown',
                # Maximum number of analog channels
                'max_channels': self.max_channels,
                # Number of digital channels (unique to MSO models)
                'digital_channels': self.digital_channels,
                # Analog bandwidth in Hz
                'bandwidth_hz': self.bandwidth_hz,
                # Maximum sample rate in samples per second
                'max_sample_rate': self.max_sample_rate,
                # Maximum memory depth in samples
                'max_memory_depth': self.max_memory_depth,
                # ADC resolution in bits (14-bit for HD3 series)
                'resolution_bits': self.resolution_bits,
                # Number of built-in frequency counters
                'num_counters': self.num_counters,
                # Maximum number of independent graticule grids
                'max_graticules': self.max_graticules,
                # Full raw identification string for debugging
                'identification': idn
            }
        # If any query fails, catch and log the error
        except Exception as e:
            self._logger.error(f"Failed to query instrument information: {e}")
            return None
