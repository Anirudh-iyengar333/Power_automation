# This line tells the operating system to run this file using Python 3, making it directly executable on Unix/Linux/Mac systems
#!/usr/bin/env python3
# This is the module-level documentation string that describes the entire file's purpose, capabilities, and usage examples for developers and engineers
"""
Keithley DMM6500/DMM7510 Digital Multimeter Professional Control Library

Enterprise-grade Python interface for Keithley DMM6500 and DMM7510 precision
digital multimeters. Implements complete SCPI command set with IEEE 488.2
compliance for laboratory and production test automation.

Module: instrument_control.keithley_dmm
Author: Professional Instrument Control Team
Version: 2.0.0
License: MIT
Python: >=3.7
Dependencies: pyvisa>=1.11.0, pyvisa-py (optional backend)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUPPORTED INSTRUMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    - Keithley DMM6500  - 6.5-digit benchtop multimeter (1µV resolution)
    - Keithley DMM7510  - 7.5-digit graphical sampling multimeter
    - DMM7512          - 7.5-digit with extended memory

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEASUREMENT CAPABILITIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Voltage:        DC (1µV-1000V), AC (100µV-750V RMS)
    Current:        DC/AC (1nA-10A with 10nA resolution)
    Resistance:     2W/4W (1mΩ-100MΩ, 4W for <1Ω precision)
    Capacitance:    1pF-10µF
    Temperature:    RTD (PT100, PT385), Thermocouples (Type K,J,T,E,R,S,B,N)
    Frequency:      3Hz-300kHz
    Period:         3.33µs-0.333s
    Diode Test:     Forward voltage measurement
    Continuity:     Low-resistance check with beeper

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADVANCED FEATURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    - Triggered measurements (BUS, EXTERNAL, TIMER, MANUAL triggers)
    - Reading buffers (7M samples, circular/one-shot modes)
    - Built-in statistics (mean, stddev, min/max, peak-to-peak)
    - Math functions (mx+b scaling, percent, reciprocal, averaging)
    - Limit testing (pass/fail with programmable thresholds)
    - Display control (custom text, screen selection)
    - Configuration save/recall (5 non-volatile memory locations)
    - Context manager support (automatic connection management)
    - Comprehensive error handling with instrument error queue

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUICK START
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Basic Measurement:
    >>> from instrument_control.keithley_dmm import KeithleyDMM6500
    >>>
    >>> dmm = KeithleyDMM6500('USB0::0x05E6::0x6500::04561287::INSTR')
    >>> dmm.connect()
    >>> voltage = dmm.measure_dc_voltage(measurement_range=10.0, nplc=1.0)
    >>> print(f"Voltage: {voltage:.6f}V")
    >>> dmm.disconnect()

Context Manager (Recommended):
    >>> with KeithleyDMM6500('TCPIP::192.168.1.100::INSTR') as dmm:
    >>>     voltage = dmm.measure_dc_voltage()
    >>>     resistance = dmm.measure_resistance_4w()
    >>>     # Auto-disconnect on exit

Triggered Data Acquisition:
    >>> dmm.configure_trigger(TriggerSource.TIMER, count=100, timer_interval=0.01)
    >>> dmm.configure_buffer("defbuffer1", buffer_size=100, fill_mode="ONCE")
    >>> dmm.initiate_measurement()
    >>> time.sleep(2.0)  # Wait for 100 samples at 10ms interval
    >>> data = dmm.fetch_buffer_data("defbuffer1")
    >>> stats = dmm.get_buffer_statistics("defbuffer1")

Limit Testing:
    >>> dmm.configure_limit_test(lower_limit=4.95, upper_limit=5.05)
    >>> voltage = dmm.measure_dc_voltage()
    >>> result = dmm.get_limit_test_result()  # "PASS" or "FAIL"
    >>> if result == "FAIL":
    >>>     dmm.beep(2000, 0.5)  # Audible alert

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROFESSIONAL PRACTICES IMPLEMENTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    - Type hints throughout (PEP 484 compliance)
    - Comprehensive docstrings (Google style)
    - Proper exception handling with custom exceptions
    - Resource cleanup with context managers
    - Defensive parameter validation
    - IEEE 488.2 and SCPI standards compliance
    - Production-tested command sequences
    - Optimized for DMM6500 hardware characteristics
    - No external dependencies beyond PyVISA

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    - For 4-wire measurements: Use dedicated 4W terminals or configure scanning
    - NPLC settings: Higher values = better noise rejection but slower speed
    - NPLC settings: Higher values = better noise rejection but slower speed
    - Auto-zero: ON for maximum accuracy, OFF for maximum speed
    - Line frequency: Set to 50Hz (Europe/Asia) or 60Hz (Americas) for NPLC sync
    - Buffer memory: Up to 7 million readings (limited by available RAM)

See Also:
    DMM6500 Reference Manual: https://www.tek.com/keithley-dmm6500
    SCPI Standard: https://www.ivifoundation.org/scpi/
"""

# Load the Python standard library module for recording log messages (information, warnings, errors) throughout the script
import logging
# Load the Python standard library module that provides functions for pausing the program for a set number of seconds
import time
# Load specific type-hint helpers from Python's typing module so that function signatures can clearly declare what data types they accept and return
from typing import Optional, Dict, Any, List, Tuple, Union
# Load the Enum base class from Python's standard library, which allows groups of named constants (like measurement types) to be defined cleanly
from enum import Enum

# Attempt to import the PyVISA library, which provides the communication layer for talking to test instruments over USB, GPIB, Ethernet, and other interfaces
try:
    # Import the main PyVISA package used to discover and communicate with connected instruments
    import pyvisa
    # Import the specific VISA communication error class so connection and read/write failures can be caught and handled separately
    from pyvisa.errors import VisaIOError
# If PyVISA is not installed, catch the import failure and raise a clear, informative error instead of a cryptic crash
except ImportError as e:
    # Stop the program immediately and tell the user exactly how to fix the missing dependency
    raise ImportError(
        "PyVISA library is required. Install with: pip install pyvisa"
    ) from e

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a named group of constants representing all the types of measurements the Keithley DMM6500 multimeter can perform; each name maps to the exact command text the instrument expects
class MeasurementFunction(Enum):
    """
    Enumeration of supported measurement functions per SCPI standard.

    Each enum value corresponds to the SCPI subsystem command for that
    measurement type. These are used with :SENSe:FUNCtion command.
    """
    # Constant representing steady (non-alternating) voltage measurement mode
    DC_VOLTAGE = "VOLTage:DC"          # DC voltage measurement
    # Constant representing alternating voltage measurement mode, which reports the effective (RMS) value
    AC_VOLTAGE = "VOLTage:AC"          # AC voltage measurement (RMS)
    # Constant representing steady (non-alternating) current measurement mode
    DC_CURRENT = "CURRent:DC"          # DC current measurement
    # Constant representing alternating current measurement mode, which reports the effective (RMS) value
    AC_CURRENT = "CURRent:AC"          # AC current measurement (RMS)
    # Constant representing standard two-wire resistance measurement (suitable for resistances above 1 ohm)
    RESISTANCE_2W = "RESistance"       # 2-wire resistance measurement
    # Constant representing four-wire resistance measurement (eliminates lead resistance for very low-value components)
    RESISTANCE_4W = "FRESistance"      # 4-wire resistance measurement
    # Constant representing capacitance (charge-storage ability) measurement mode
    CAPACITANCE = "CAPacitance"        # Capacitance measurement
    # Constant representing frequency (cycles per second) measurement mode for AC signals
    FREQUENCY = "FREQuency"            # Frequency measurement
    # Constant representing period (time for one complete cycle) measurement mode for AC signals
    PERIOD = "PERiod"                  # Period measurement
    # Constant representing temperature measurement mode, compatible with RTD probes and thermocouple sensors
    TEMPERATURE = "TEMPerature"        # Temperature measurement (RTD/Thermocouple)
    # Constant representing diode forward-voltage test mode
    DIODE = "DIODe"                    # Diode test
    # Constant representing continuity check mode, which sounds a beep when resistance is very low
    CONTINUITY = "CONTinuity"          # Continuity test

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a named group of constants representing all the ways the multimeter can be told to start taking a measurement
class TriggerSource(Enum):
    """
    Trigger source options for measurement triggering.

    Controls what event initiates a measurement sequence.
    """
    # Constant meaning the instrument should start measuring right away without waiting for any external event
    IMMEDIATE = "IMMediate"            # Trigger immediately (continuous)
    # Constant meaning the instrument should start measuring at regular time intervals set by an internal clock
    TIMER = "TIMer"                    # Internal timer trigger
    # Constant meaning the instrument waits for a human to press the TRIGGER button on its front panel
    MANUAL = "MANual"                  # Front panel TRIGGER button
    # Constant meaning the instrument waits for a software command sent over the computer interface
    BUS = "BUS"                        # Software/SCPI trigger (*TRG)
    # Constant meaning the instrument waits for a voltage pulse on the external trigger input connector
    EXTERNAL = "EXTernal"              # External trigger input
    # Constant meaning the instrument synchronises its measurements to the mains electricity supply frequency
    LINE = "LINE"                      # AC line sync trigger

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a named group of constants representing the different screens that can be shown on the instrument's front-panel display
class DisplayState(Enum):
    """Display screen state options."""
    # Constant representing the main home screen of the instrument
    HOME = "HOME"                      # Home screen
    # Constant representing the live measurement readings screen
    READING = "READing"                # Show readings
    # Constant representing the histogram (bar chart distribution) screen
    HISTOGRAM = "HISTogram"            # Histogram display
    # Constant representing the statistics summary screen (mean, min, max, etc.)
    STATISTICS = "STATistics"          # Statistics display
    # Constant representing the swipe-style graph screen
    GRAPH_SWIPE = "GRAPh:SWIPe"       # Swipe graph
    # Constant representing the trend chart (time-based graph) screen
    GRAPH_TREND = "GRAPh:TRENd"       # Trend chart
    # Constant representing the custom user-defined text screen
    USER = "USER"                      # User-defined screen

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a named group of constants for the mathematical post-processing operations the instrument can apply to each measurement before displaying or storing it
class MathOperation(Enum):
    """Math operations for measurement processing."""
    # Constant meaning no mathematical operation is applied — the raw measurement is used as-is
    NONE = "NONE"                      # No math operation
    # Constant representing linear scaling: the result equals (m × reading) + b, useful for sensor calibration
    MXB = "MXB"                        # y = mx + b scaling
    # Constant representing percent-deviation calculation relative to a reference value
    PERCENT = "PERCent"                # Percent deviation
    # Constant representing the reciprocal (1 divided by the reading) operation
    RECIPROCAL = "RECiprocal"          # 1/x
    # Constant representing a relative offset (subtracts a stored reference from the current reading)
    OFFSET = "OFFSet"                  # Offset compensation
    # Constant representing a moving average filter applied over successive readings
    AVERAGE = "AVERage"                # Moving average
    # Constant representing the limit-test mode, which flags whether a measurement is within acceptable bounds
    LIMIT = "LIMit"                    # Limit testing

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a named group of constants for the three possible auto-zero settings, which control whether the instrument corrects for its own internal offset before each measurement
class AutoZeroMode(Enum):
    """Auto-zero configuration modes."""
    # Constant meaning auto-zero correction is completely disabled (fastest, but potentially less accurate)
    OFF = "OFF"                        # Auto-zero disabled
    # Constant meaning the instrument performs an internal zero correction before every single measurement (slowest, most accurate)
    ON = "ON"                          # Auto-zero before each measurement
    # Constant meaning the instrument performs a zero correction one time, then disables it for subsequent readings
    ONCE = "ONCE"                      # Auto-zero once then disable

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a custom error class specific to this instrument so that problems with the Keithley DMM6500 can be caught and identified separately from general Python errors
class KeithleyDMM6500Error(Exception):
    """Custom exception for Keithley DMM6500 multimeter errors."""
    # This class body uses "pass" because it inherits all error behaviour from the built-in Exception class and needs no additional logic
    pass

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define the main control class that wraps all communication and measurement capabilities for the Keithley DMM6500 digital multimeter into a single, organised interface
class KeithleyDMM6500:
    """
    Control interface for Keithley DMM6500 digital multimeter.

    This class provides methods for high-precision measurements, statistical
    analysis, and comprehensive instrument configuration. All methods follow
    IEEE 488.2 and SCPI standards for maximum compatibility.

    Attributes:
        visa_address (str): VISA resource identifier string
        timeout_ms (int): Communication timeout in milliseconds
        max_voltage_range (float): Maximum DC voltage measurement range
        min_resolution (float): Minimum measurement resolution achievable
    """

    # Define the setup function that runs automatically when a new KeithleyDMM6500 object is created; it stores the connection address and prepares all internal variables
    def __init__(self, visa_address: str, timeout_ms: int = 30000) -> None:
        """
        Initialize DMM control instance with extended timeout for precision measurements.

        Args:
            visa_address: VISA resource string (e.g., 'USB0::0x05E6::0x6500::04561287::INSTR')
            timeout_ms: Communication timeout in milliseconds (extended default for precision)

        Raises:
            ValueError: If visa_address is empty or invalid format
        """
        # Check that the address provided is not empty and is actually a text string; if not, stop immediately with a clear error message
        if not visa_address or not isinstance(visa_address, str):
            raise ValueError("visa_address must be a non-empty string")

        # Store configuration parameters
        # Save the instrument's USB/GPIB/network address so it can be used when opening the connection later
        self._visa_address = visa_address
        # Save the communication timeout (in milliseconds) so it can be applied after the connection is opened
        self._timeout_ms = timeout_ms

        # Initialize VISA communication objects
        # Set the VISA resource manager variable to empty for now; it will be populated when connect() is called
        self._resource_manager: Optional[pyvisa.ResourceManager] = None
        # Set the instrument handle variable to empty for now; it will be populated when connect() is called
        self._instrument: Any = None  # pyvisa Resource object (use Any to avoid type errors)
        # Set the connection status flag to False because no connection has been established yet
        self._is_connected = False

        # Initialize logging for this instance
        # Create a dedicated log channel for this specific multimeter object so its messages can be traced individually
        self._logger = logging.getLogger(f'{self.__class__.__name__}.{id(self)}')

        # Define instrument specifications (DMM6500)
        # Store the highest DC voltage the instrument can safely measure (1000 volts)
        self.max_voltage_range = 1000.0  # Maximum DC voltage range (V)
        # Store the highest DC current the instrument can safely measure (10 amps)
        self.max_current_range = 10.0    # Maximum DC current range (A)
        # Store the highest resistance the instrument can measure (100 megaohms)
        self.max_resistance_range = 100e6  # Maximum resistance range (Ohm)
        # Store the smallest increment the instrument can resolve (1 nanovolt at best accuracy)
        self.min_resolution = 1e-9       # Minimum resolution for highest accuracy

        # Define valid measurement ranges for different functions
        # List all the fixed voltage measurement ranges available on this instrument (in volts)
        self._voltage_ranges = [0.1, 1.0, 10.0, 100.0, 1000.0]
        # List all the fixed current measurement ranges available on this instrument (in amps)
        self._current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 100e-3, 1.0, 3.0, 10.0]
        # List all the fixed resistance measurement ranges available on this instrument (in ohms)
        self._resistance_ranges = [100.0, 1e3, 10e3, 100e3, 1e6, 10e6, 100e6]

        # Define valid NPLC (Number of Power Line Cycles) values
        # List all the permitted NPLC (integration time) values the instrument accepts; higher values are slower but more accurate
        self._valid_nplc_values = [0.01, 0.02, 0.06, 0.2, 1.0, 2.0, 10.0]

    # Define the function that opens a communication session with the physical multimeter and prepares it for use
    def connect(self) -> bool:
        """
        Establish communication with the multimeter.

        This method creates the VISA resource manager, opens the instrument
        connection, and performs comprehensive initialization sequence optimized
        for DMM6500 characteristics.

        Returns:
            True if connection successful, False otherwise

        Raises:
            KeithleyDMM6500Error: If critical connection error occurs
        """
        # Begin a protected block of code; if anything goes wrong during connection, errors will be caught below
        try:
            # Create VISA resource manager instance
            # Start the VISA resource manager, which scans available communication buses for connected instruments
            self._resource_manager = pyvisa.ResourceManager()
            # Write a log message confirming the resource manager was created successfully
            self._logger.info("VISA resource manager created successfully")

            # Open connection to specified instrument with optimized settings
            # Open a communication channel to the instrument at the stored address
            self._instrument = self._resource_manager.open_resource(self._visa_address)
            # Write a log message showing which address was successfully opened
            self._logger.info(f"Opened connection to {self._visa_address}")

            # Configure communication parameters optimized for DMM6500
            # Apply the saved timeout value so the instrument does not wait indefinitely for a response
            self._instrument.timeout = self._timeout_ms
            # Tell PyVISA that the instrument signals the end of each response with a line-feed character
            self._instrument.read_termination = '\n'  # Line feed termination
            # Tell PyVISA to add a line-feed character at the end of every command sent to the instrument
            self._instrument.write_termination = '\n'  # Line feed termination
            # Set the internal data chunk size to 20 kilobytes for reliable high-volume transfers
            self._instrument.chunk_size = 20480  # Optimized buffer size for stability

            # Clear any existing errors immediately after connection
            # Send the IEEE 488.2 "clear status" command to wipe any leftover error flags from a previous session
            self._instrument.write("*CLS")
            # Pause for 0.2 seconds to give the instrument time to fully process the clear command
            time.sleep(0.2)  # Allow error clearing to complete

            # Verify instrument communication with identification query
            # Ask the instrument to identify itself; the response confirms communication is working
            identification = self._instrument.query("*IDN?")
            # Write a log message showing the instrument's full identification string
            self._logger.info(f"Instrument identification: {identification.strip()}")

            # Validate instrument model compatibility
            # Check whether the manufacturer name in the response confirms this is a Keithley instrument
            if "KEITHLEY" not in identification.upper():
                # Log a warning if the manufacturer is not Keithley, as an unexpected device may be connected
                self._logger.warning(f"Unexpected manufacturer in IDN response: {identification}")

            # Check whether the model string confirms this is a DMM-series multimeter
            if "DMM" not in identification.upper() and "6500" not in identification:
                # Log a warning if the model number is not recognised as a supported DMM type
                self._logger.warning(f"Unexpected model in IDN response: {identification}")

            # Perform optimized initialization sequence for DMM6500
            # Log the start of the instrument initialisation sequence
            self._logger.info("Performing DMM6500-optimized initialization sequence")

            # Clear all error registers
            # Send the clear-status command a second time to ensure all error registers are fully reset
            self._instrument.write("*CLS")
            # Pause for 0.1 seconds to allow the clear command to complete before sending the next command
            time.sleep(0.1)

            # Use *RST for instrument reset (:SYSTem:PRESet causes -113 on some models)
            # Attempt the full instrument reset; wrap it in its own error handler because some firmware versions do not support it cleanly
            try:
                # Send the IEEE 488.2 reset command to restore the instrument to its factory default state
                self._instrument.write("*RST")
                # Pause for 1 full second to allow the instrument to complete its internal reset procedure
                time.sleep(1.0)  # Allow reset to complete
                # Log a debug message confirming the reset command was sent
                self._logger.debug("Instrument reset with *RST")
            # If the reset command fails for any reason, log a warning but continue — the instrument may still be usable
            except Exception as e:
                # Log a warning that the reset failed but note that the program will continue without resetting
                self._logger.warning(f"*RST failed, continuing without reset: {e}")

            # Removed :FORMat:ASCii:PRECision to avoid unsupported header (-113) on some models
            # Removed :ABORt command as it causes -113 on this DMM model

            # Final error clearing
            # Send one last clear-status command after the reset to ensure the instrument starts with a clean error state
            self._instrument.write("*CLS")

            # Verify instrument is responsive after initialization
            # Query the operation-complete flag; the instrument returns "1" when all previous commands have finished
            self._instrument.query("*OPC?")  # Operation complete query

            # Mark connection as established
            # Set the connection flag to True now that communication is confirmed and the instrument is ready
            self._is_connected = True
            # Write a log message confirming a successful connection to the Keithley DMM6500
            self._logger.info("Successfully connected to Keithley DMM6500")

            # Return True to inform the caller that the connection succeeded
            return True

        # If a VISA-specific communication error occurred (e.g. device not found, wrong address), handle it here
        except VisaIOError as e:
            # Log the specific VISA error that prevented the connection
            self._logger.error(f"VISA communication error during connection: {e}")
            # Release any partially allocated resources to avoid memory or port leaks
            self._cleanup_connection()
            # Return False to inform the caller that the connection failed
            return False

        # If any other unexpected error occurred, handle it here
        except Exception as e:
            # Log the unexpected error that occurred during connection
            self._logger.error(f"Unexpected error during connection: {e}")
            # Release any partially allocated resources to avoid memory or port leaks
            self._cleanup_connection()
            # Raise a custom KeithleyDMM6500Error so the caller knows the connection failed and why
            raise KeithleyDMM6500Error(f"Connection failed: {e}") from e

    # Define the function that safely closes the connection to the multimeter and releases all associated computer resources
    def disconnect(self) -> None:
        """
        Safely disconnect from multimeter and release resources.

        This method puts the instrument in a safe state, closes connections,
        and performs proper cleanup to prevent resource leaks.
        """
        # Begin a protected block; any error during disconnection will be caught and logged rather than crashing the program
        try:
            # Check whether an instrument handle exists before trying to close it
            if self._instrument is not None:
                # Put instrument in safe state before disconnection
                # Removed :ABORt command as it causes -113 on this DMM model
                # Send the clear-status command to leave the instrument in a clean state before closing the session
                self._instrument.write("*CLS")   # Clear status registers

                # Close instrument connection
                # Close the communication channel to the physical instrument
                self._instrument.close()
                # Log confirmation that the instrument connection was closed
                self._logger.info("Instrument connection closed")

            # Check whether the resource manager was opened before trying to close it
            if self._resource_manager is not None:
                # Close resource manager
                # Shut down the VISA resource manager and free the associated operating system resources
                self._resource_manager.close()
                # Log confirmation that the resource manager was closed
                self._logger.info("VISA resource manager closed")

        # If any error occurs during the close-down sequence, catch it so the program can still continue
        except Exception as e:
            # Log the error that occurred while trying to disconnect
            self._logger.error(f"Error during disconnection: {e}")

        # This block always runs regardless of whether an error occurred, ensuring cleanup always happens
        finally:
            # Reset connection state and object references
            # Call the internal cleanup helper to reset all connection-related variables to their initial empty state
            self._cleanup_connection()
            # Log a message confirming that the disconnection process has fully completed
            self._logger.info("Disconnection completed")

    # Define the main high-precision DC voltage measurement function that configures the instrument and returns a single reading
    def measure_dc_voltage(self,
                          measurement_range: Optional[float] = None,
                          resolution: Optional[float] = None,
                          nplc: Optional[float] = None,
                          auto_zero: bool = True) -> Optional[float]:
        """
        Perform high-precision DC voltage measurement.

        This method configures the multimeter for optimal DC voltage measurement
        accuracy and performs the measurement with comprehensive error handling.

        Args:
            measurement_range: Measurement range in volts (None for auto-range)
            resolution: Measurement resolution in volts (None for default)
            nplc: Number of Power Line Cycles for integration (None for default)
            auto_zero: Enable automatic zero correction for highest accuracy

        Returns:
            DC voltage measurement in volts, or None if measurement failed

        Raises:
            KeithleyDMM6500Error: If instrument not connected or invalid parameters
        """
        # Check whether the instrument is connected before attempting any measurement; raise an error if not
        if not self._is_connected:
            raise KeithleyDMM6500Error("Multimeter not connected")

        # Begin a protected measurement block; any error will be caught and handled below
        try:
            # Log that DC voltage measurement configuration is starting
            self._logger.info("Configuring for high-precision DC voltage measurement")

            # Clear any existing errors
            # Clear the instrument's error and status registers before configuring for a fresh measurement
            self._instrument.write("*CLS")
            # Pause briefly to allow the clear command to take effect before sending further commands
            time.sleep(0.1)

            # Removed :ABORt command as it causes -113 on this DMM model

            # Configure measurement function for DC voltage
            # Tell the instrument to switch into DC voltage measurement mode
            self._instrument.write(':SENSe:FUNCtion "VOLTage:DC"')
            # Pause briefly to allow the function-select command to take effect
            time.sleep(0.1)

            # Configure measurement range
            # Check whether a specific measurement range was requested by the caller
            if measurement_range is not None:
                # Validate and select appropriate range
                # Check whether the requested range is one of the instrument's supported fixed ranges
                if measurement_range not in self._voltage_ranges:
                    # Find the smallest valid range that is still large enough to measure the requested voltage without overflow
                    valid_range = min([r for r in self._voltage_ranges if r >= measurement_range],
                                    default=self._voltage_ranges[-1])
                    # Log a warning that the requested range was not valid and explain which range will be used instead
                    self._logger.warning(f"Invalid range {measurement_range}V, using {valid_range}V")
                    # Replace the requested range with the nearest valid range
                    measurement_range = valid_range

                # Send the command to set the instrument's voltage range to the (validated) requested value
                self._instrument.write(f":SENSe:VOLTage:DC:RANGe {measurement_range}")
                # Log a debug message confirming the range that was set
                self._logger.debug(f"Set measurement range to {measurement_range}V")
            # If no range was specified, configure the instrument to choose the best range automatically
            else:
                # Enable auto-ranging for maximum flexibility
                # Tell the instrument to automatically select the most appropriate voltage range
                self._instrument.write(":SENSe:VOLTage:DC:RANGe:AUTO ON")
                # Log a debug message confirming that auto-ranging was enabled
                self._logger.debug("Enabled auto-ranging")

            # Pause to allow the range setting to take effect before applying the next configuration
            time.sleep(0.1)

            # Configure measurement resolution if specified
            # Check whether a specific resolution was provided by the caller
            if resolution is not None:
                # Ensure resolution is within instrument capabilities
                # Check whether the requested resolution is finer than what the instrument can physically achieve
                if resolution < self.min_resolution:
                    # Log a warning and cap the resolution at the instrument's physical minimum
                    self._logger.warning(f"Resolution {resolution} below minimum, using {self.min_resolution}")
                    # Replace the too-fine resolution with the instrument's minimum achievable resolution
                    resolution = self.min_resolution

                #self._instrument.write(f":SENSe:VOLTage:DC:RESolution {resolution}")
                # Log a debug message noting the requested resolution (actual command is commented out as unsupported)
                self._logger.debug(f"Set resolution to {resolution}V")

            # Configure integration time (NPLC) if specified
            # Check whether a specific integration time (NPLC) was provided by the caller
            if nplc is not None:
                # Validate NPLC value
                # Check whether the requested NPLC value is one of the instrument's supported options
                if nplc not in self._valid_nplc_values:
                    # Create a local copy of the nplc value for safe comparison
                    nplc_val = nplc if nplc is not None else 1.0
                    # Find the closest valid NPLC value to what the caller requested
                    valid_nplc = min(self._valid_nplc_values, key=lambda x: abs(x - nplc_val))
                    # Log a warning that the NPLC was adjusted to the nearest supported value
                    self._logger.warning(f"Invalid NPLC {nplc}, using {valid_nplc}")
                    # Replace the invalid NPLC with the nearest valid one
                    nplc = valid_nplc

                # Send the command to set the integration time on the instrument
                self._instrument.write(f":SENSe:VOLTage:DC:NPLC {nplc}")
                # Log a debug message confirming the NPLC value that was set
                self._logger.debug(f"Set NPLC to {nplc}")
            # If no NPLC was specified, apply the default value of 1 (one power line cycle)
            else:
                # Use default NPLC for good balance of speed and accuracy
                # Set NPLC to 1 as a sensible default that balances measurement speed and noise rejection
                self._instrument.write(":SENSe:VOLTage:DC:NPLC 1")
                # Log a debug message confirming the default NPLC was applied
                self._logger.debug("Set NPLC to 1 (default)")

            # Removed auto-zero headers to avoid -113; do not change auto-zero state here

            # Allow all settings to take effect
            # Pause for 0.2 seconds to let all configuration commands finish before triggering the measurement
            time.sleep(0.2)

            # Log that the actual reading is about to be requested from the instrument
            self._logger.debug("Performing fresh DC voltage reading")
            # Send the READ? query, which triggers a fresh measurement and returns the result as a text string
            measurement_str = self._instrument.query(":READ?")
            # Convert the text response from the instrument into a Python floating-point number
            voltage = float(measurement_str.strip())

            # Log the successful measurement result with high precision for traceability
            self._logger.info(f"DC voltage measurement successful: {voltage:.9f} V")

            # Return the measured voltage value to the caller
            return voltage

        # If a VISA communication error occurred during measurement (e.g. timeout, device disconnected), handle it here
        except VisaIOError as e:
            # Check specifically whether the error was a timeout so a more targeted message can be logged
            if "timeout" in str(e).lower():
                # Log advice to the user: either increase the timeout or reduce NPLC to speed up the measurement
                self._logger.error("Measurement timeout - consider increasing timeout or reducing NPLC")
            # If it was a different VISA error, log the raw error detail
            else:
                self._logger.error(f"VISA communication error: {e}")
            # Return None to indicate the measurement failed
            return None

        # If the response from the instrument could not be converted to a number, or a function parameter was wrong, handle it here
        except (ValueError, AttributeError) as e:
            # Log the parameter or parsing error
            self._logger.error(f"Parameter or parsing error: {e}")
            # Return None to indicate the measurement failed
            return None

        # Catch any other unexpected error that was not handled above
        except Exception as e:
            # Log the unexpected error with enough detail to help diagnose the problem
            self._logger.error(f"Unexpected error during DC voltage measurement: {e}")
            # Return None to indicate the measurement failed
            return None

    # Define a lightweight DC voltage measurement function that sends the minimum number of commands, trading configurability for speed
    def measure_dc_voltage_fast(self) -> Optional[float]:
        """
        Perform fast DC voltage measurement with minimal configuration overhead.

        This method uses the simplest SCPI command for situations where speed
        is more important than maximum precision or configurability.

        Returns:
            DC voltage measurement in volts, or None if measurement failed
        """
        # Check whether the instrument is connected; if not, log an error and return None immediately
        if not self._is_connected:
            self._logger.error("Cannot measure voltage: multimeter not connected")
            return None

        # Begin a protected measurement block; any error will be caught below
        try:
            # Log that a fast measurement is about to be taken
            self._logger.debug("Performing fast DC voltage measurement")

            # Clear any errors first
            # Send the clear-status command to remove any lingering error flags before the measurement
            self._instrument.write("*CLS")
            # Pause for 0.05 seconds (shorter than normal to keep the fast measurement quick)
            time.sleep(0.05)

            # Removed :ABORt command as it causes -113 on this DMM model

            # Switch the instrument into DC voltage measurement mode
            self._instrument.write(':SENSe:FUNCtion "VOLTage:DC"')
            # Pause briefly to allow the mode-switch command to take effect
            time.sleep(0.05)

            # Fresh measurement
            # Send the READ? query to trigger a new measurement and retrieve the result
            measurement_str = self._instrument.query(":READ?")
            # Convert the text response to a Python floating-point number
            voltage = float(measurement_str.strip())

            # Log the fast measurement result with moderate precision
            self._logger.debug(f"Fast DC voltage measurement: {voltage:.6f} V")

            # Return the measured voltage to the caller
            return voltage

        # Catch any error that occurred during the fast measurement
        except Exception as e:
            # Log the error that caused the fast measurement to fail
            self._logger.error(f"Fast measurement failed: {e}")
            # Return None to signal that the measurement was unsuccessful
            return None

    # Define a function that reads and returns any error messages currently stored in the instrument's internal error queue
    def check_instrument_errors(self) -> List[str]:
        """
        Check and retrieve any accumulated instrument errors.

        Returns:
            List of error messages, empty list if no errors
        """
        # Create an empty list that will be populated with any error messages found
        errors = []

        # If the instrument is not connected, return immediately with a descriptive message instead of crashing
        if not self._is_connected:
            return ["Multimeter not connected"]

        # Begin a protected block for querying the instrument's error queue
        try:
            # Read up to 20 errors to prevent infinite loops
            # Loop up to 20 times to drain the error queue, using an index variable that is intentionally not referenced
            for _ in range(20):
                # Ask the instrument for the next error in its queue and remove the surrounding whitespace from the response
                error_response = self._instrument.query(":SYSTem:ERRor:NEXT?").strip()

                # Check if no more errors (standard SCPI response)
                # If the response says "No error" or starts with "0," the queue is empty — stop reading
                if "No error" in error_response or error_response.startswith("0,"):
                    break

                # Add the error message text to the list of found errors
                errors.append(error_response)

        # If querying the error queue itself causes an error, add a description of that failure to the list
        except Exception as e:
            errors.append(f"Error reading instrument errors: {str(e)}")

        # Return the complete list of error messages (may be empty if no errors were found)
        return errors

    # Define a function that takes multiple DC voltage readings in sequence and returns statistical summary data about them
    def perform_measurement_statistics(self,
                                     measurement_count: int = 10,
                                     measurement_interval: float = 0.1) -> Optional[Dict[str, float]]:
        """
        Perform multiple measurements and calculate statistical parameters.

        Args:
            measurement_count: Number of measurements to perform
            measurement_interval: Delay between measurements in seconds

        Returns:
            Dictionary containing statistical results, or None if failed
        """
        # If the instrument is not connected, log an error and return None immediately
        if not self._is_connected:
            self._logger.error("Cannot perform statistics: multimeter not connected")
            return None

        # Require at least 2 measurements to compute meaningful statistics such as standard deviation
        if measurement_count < 2:
            raise ValueError("measurement_count must be at least 2 for statistics")

        # Begin a protected block for the statistics collection and calculation
        try:
            # Log that the statistics measurement campaign is starting, including how many readings will be taken
            self._logger.info(f"Performing {measurement_count} measurements for statistics")

            # Create an empty list that will hold all the successfully obtained voltage readings
            measurements = []

            # Collect measurements
            # Loop through the required number of measurements, collecting one reading per iteration
            for i in range(measurement_count):
                # Take a single fast DC voltage reading and store the result
                voltage = self.measure_dc_voltage_fast()
                # Only add the reading to the list if it was successful (not None)
                if voltage is not None:
                    measurements.append(voltage)
                    # Log each successful reading with its position in the sequence for traceability
                    self._logger.debug(f"Measurement {i+1}/{measurement_count}: {voltage:.6f}V")

                    # Wait between measurements if not the last one
                    # Pause between readings unless this is the very last one, to avoid a pointless final delay
                    if i < measurement_count - 1:
                        time.sleep(measurement_interval)
                # If the reading failed, log a warning but continue collecting the remaining readings
                else:
                    self._logger.warning(f"Measurement {i+1} failed")

            # Verify that at least 2 successful readings were collected before attempting statistics
            if len(measurements) < 2:
                # Log an error and return None if there are not enough valid readings for statistics
                self._logger.error("Insufficient valid measurements for statistics")
                return None

            # Calculate statistics
            # Import Python's built-in statistics module for calculating mean and standard deviation
            import statistics

            # Calculate the average (mean) of all the collected voltage readings
            mean_value = statistics.mean(measurements)
            # Calculate the standard deviation (spread) of the readings; return 0 if only one reading exists
            std_deviation = statistics.stdev(measurements) if len(measurements) > 1 else 0.0
            # Find the smallest reading in the collected set
            min_value = min(measurements)
            # Find the largest reading in the collected set
            max_value = max(measurements)
            # Calculate the range (difference between the largest and smallest readings)
            range_value = max_value - min_value

            # Calculate coefficient of variation (percentage)
            # Calculate the coefficient of variation: standard deviation as a percentage of the mean (shows relative spread)
            cv_percent = (std_deviation / mean_value * 100.0) if mean_value != 0 else float('inf')

            # Build a dictionary containing all the calculated statistics, ready to return to the caller
            results = {
                # Store how many valid readings were actually collected
                'count': len(measurements),
                # Store the average voltage
                'mean': mean_value,
                # Store the standard deviation (measure of reading stability)
                'standard_deviation': std_deviation,
                # Store the lowest recorded voltage
                'minimum': min_value,
                # Store the highest recorded voltage
                'maximum': max_value,
                # Store the total spread from minimum to maximum
                'range': range_value,
                # Store the coefficient of variation expressed as a percentage
                'coefficient_of_variation_percent': cv_percent
            }

            # Log a summary of the statistics results for traceability in the test log
            self._logger.info(f"Statistics complete: Mean={mean_value:.6f}V, "
                            f"StdDev={std_deviation:.6f}V, CV={cv_percent:.3f}%")

            # Return the dictionary of statistical results to the caller
            return results

        # Catch any unexpected error that occurred during the statistics collection or calculation
        except Exception as e:
            # Log the error that prevented the statistics from completing
            self._logger.error(f"Failed to perform measurement statistics: {e}")
            # Return None to signal that statistics collection failed
            return None

    # Define a function that queries the instrument for all available identification and status information and returns it as a dictionary
    def get_instrument_info(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve comprehensive instrument information and status.

        Returns:
            Dictionary containing instrument details, or None if query failed
        """
        # If the instrument is not connected, return None immediately rather than attempting a query
        if not self._is_connected:
            return None

        # Begin a protected block for the instrument information query
        try:
            # Query instrument identification
            # Ask the instrument for its identification string, which includes manufacturer, model, serial number, and firmware
            idn_response = self._instrument.query("*IDN?").strip()
            # Split the identification string into its individual comma-separated fields
            idn_parts = idn_response.split(',')

            # Extract identification components
            # Extract the manufacturer name from the first field, or use "Unknown" if unavailable
            manufacturer = idn_parts[0] if len(idn_parts) > 0 else "Unknown"
            # Extract the model number from the second field, or use "Unknown" if unavailable
            model = idn_parts[1] if len(idn_parts) > 1 else "Unknown"
            # Extract the serial number from the third field, or use "Unknown" if unavailable
            serial_number = idn_parts[2] if len(idn_parts) > 2 else "Unknown"
            # Extract the firmware version from the fourth field, or use "Unknown" if unavailable
            firmware_version = idn_parts[3] if len(idn_parts) > 3 else "Unknown"

            # Check for current errors
            # Call the error-checking function to retrieve any current instrument errors
            current_errors = self.check_instrument_errors()
            # Format the error information as a single string; use "None" if the error list is empty
            error_status = "None" if not current_errors else "; ".join(current_errors)

            # Compile comprehensive instrument information
            # Build a dictionary containing all relevant instrument details for reporting or logging
            info = {
                # Include the instrument manufacturer name
                'manufacturer': manufacturer,
                # Include the instrument model number
                'model': model,
                # Include the unique serial number of this specific unit
                'serial_number': serial_number,
                # Include the firmware version currently running on the instrument
                'firmware_version': firmware_version,
                # Include the VISA address used to connect to this instrument
                'visa_address': self._visa_address,
                # Include a text label indicating whether the instrument is currently connected
                'connection_status': 'Connected' if self._is_connected else 'Disconnected',
                # Include the communication timeout setting in milliseconds
                'timeout_ms': self._timeout_ms,
                # Include the maximum DC voltage range in volts
                'max_voltage_range': self.max_voltage_range,
                # Include the maximum DC current range in amps
                'max_current_range': self.max_current_range,
                # Include the maximum resistance range in ohms
                'max_resistance_range': self.max_resistance_range,
                # Include the minimum achievable measurement resolution
                'min_resolution': self.min_resolution,
                # Include any current error messages, or "None" if the instrument is error-free
                'current_errors': error_status
            }

            # Return the complete information dictionary to the caller
            return info

        # Catch any error that occurred while querying the instrument for its information
        except Exception as e:
            # Log the error so the problem can be investigated
            self._logger.error(f"Failed to retrieve instrument information: {e}")
            # Return None to signal that the information query failed
            return None

    # Define a general-purpose measurement function that works for any supported measurement type by accepting a MeasurementFunction enum value
    def measure(self,
                function: MeasurementFunction,
                measurement_range: Optional[float] = None,
                resolution: Optional[float] = None,
                nplc: Optional[float] = None,
                auto_zero: Optional[bool] = None) -> Optional[float]:
        """
        Generic measurement method for any supported SCPI function.

        Args:
            function: Measurement function enum value
            measurement_range: Optional range to set; None enables auto-range
            resolution: Optional resolution; ignored if unsupported by function
            nplc: Optional integration time in power line cycles
            auto_zero: Optional auto-zero; only applied for functions that support it

        Returns:
            Measured value as float, or None on failure
        """
        # If the instrument is not connected, log an error and return None immediately
        if not self._is_connected:
            self._logger.error("Cannot measure: multimeter not connected")
            return None

        # Begin a protected measurement block; any error will be caught and handled below
        try:
            # Clear to start clean
            # Send the clear-status command to remove any lingering error flags before configuration
            self._instrument.write("*CLS")
            # Pause briefly to allow the clear command to complete
            time.sleep(0.1)
            # Removed :ABORt command as it causes -113 on this DMM model

            # Select function
            # Extract the SCPI command text (e.g., "VOLTage:DC") from the enum value
            func_token = function.value
            # Send the command to switch the instrument into the requested measurement mode
            self._instrument.write(f':SENSe:FUNCtion "{func_token}"')
            # Pause briefly to allow the function-select command to take effect
            time.sleep(0.1)

            # Determine SCPI path prefix for this function
            # Remove the colon and convert to proper format for commands
            # e.g., "VOLTage:DC" -> "VOLTage:DC", "RESistance" -> "RESistance", "FRESistance" -> "FRESistance"
            # Store the function token as the SCPI path prefix used to build subsequent configuration commands
            prefix = func_token  # e.g., VOLTage:DC

            # Determine which parameters are supported for this function
            # Based on DMM6500 SCPI command testing:
            # - AC functions don't support NPLC or RESolution
            # - Frequency doesn't support RANGe, NPLC, or RESolution
            # - All resistance functions don't support RESolution
            # Convert the function name to uppercase for consistent string comparisons
            func_upper = func_token.upper()
            # Determine whether the range command is supported: frequency and period measurements do not use a range setting
            supports_range = "FREQ" not in func_upper and "PERIOD" not in func_upper
            # Determine whether the NPLC setting is supported: AC functions, frequency, and period do not use NPLC
            supports_nplc = ":AC" not in func_upper and "FREQ" not in func_upper and "PERIOD" not in func_upper
            # Resolution commands are not supported on any tested DMM6500 function, so this is always False
            supports_resolution = False  # Resolution command not supported on any function tested

            # Configure range (or auto) - only if supported
            # Only attempt to set a measurement range if this measurement function supports it
            if supports_range:
                # Check whether a specific range was requested by the caller
                if measurement_range is not None:
                    # Snap range based on function type where we know the valid sets
                    # Try to validate the requested range against the known list for this function type
                    try:
                        # Convert the function token to uppercase for string matching
                        token_upper = func_token.upper()
                        # Check whether this is a voltage or current measurement function
                        if any(x in token_upper for x in ["VOLT", "CURR"]):
                            # Select the voltage or current range list depending on which function was chosen
                            valid_ranges = self._voltage_ranges if "VOLT" in token_upper else self._current_ranges
                            # If the requested range is not in the valid list, find the next valid range up
                            if measurement_range not in valid_ranges:
                                valid_range = min([r for r in valid_ranges if r >= measurement_range],
                                                  default=valid_ranges[-1])
                                # Log a warning that the requested range was adjusted
                                self._logger.warning(f"Invalid range {measurement_range}, using {valid_range}")
                                # Replace the invalid range with the nearest valid one
                                measurement_range = valid_range
                        # Check whether this is a resistance measurement function
                        elif "RES" in token_upper:
                            # Use the resistance-specific range list for validation
                            valid_ranges = self._resistance_ranges
                            # If the requested range is not in the valid list, find the next valid range up
                            if measurement_range not in valid_ranges:
                                valid_range = min([r for r in valid_ranges if r >= measurement_range],
                                                  default=valid_ranges[-1])
                                # Log a warning that the requested range was adjusted
                                self._logger.warning(f"Invalid range {measurement_range}, using {valid_range}")
                                # Replace the invalid range with the nearest valid one
                                measurement_range = valid_range
                    # If any part of the range validation fails, silently continue — the range will be set as provided
                    except Exception:
                        # If any validation fails, proceed to set the provided range directly
                        pass

                    # Attempt to send the range-setting command to the instrument
                    try:
                        # Send the command to set the measurement range to the (validated) value
                        self._instrument.write(f":SENSe:{prefix}:RANGe {measurement_range}")
                        # Pause briefly to allow the range command to take effect
                        time.sleep(0.05)
                    # If the range command fails (not supported for this function), log it and move on
                    except Exception as e:
                        self._logger.debug(f"Range command failed for {func_token}: {e}")
                # If no specific range was requested, try to enable auto-ranging instead
                else:
                    # Try to enable auto-range if available
                    # Attempt to enable automatic range selection for this measurement function
                    try:
                        # Send the auto-range enable command
                        self._instrument.write(f":SENSe:{prefix}:RANGe:AUTO ON")
                        # Pause briefly to allow the command to take effect
                        time.sleep(0.05)
                    # If auto-range is not supported for this function, log it and continue
                    except Exception as e:
                        self._logger.debug(f"Auto-range failed for {func_token}: {e}")
            # If range configuration is not supported for this function, log a debug note and skip it
            else:
                self._logger.debug(f"Range not supported for {func_token}")

            # Pause briefly before applying the next configuration step
            time.sleep(0.05)

            # Configure resolution if supported (currently not supported on any DMM6500 function)
            # Only attempt to set resolution if both the function supports it and a value was provided
            if supports_resolution and resolution is not None:
                # Attempt to send the resolution-setting command
                try:
                    # If the requested resolution is below the instrument's physical minimum, clamp it
                    if resolution < self.min_resolution:
                        # Log a warning that the resolution was too fine and explain what value will be used instead
                        self._logger.warning(f"Resolution {resolution} below minimum, using {self.min_resolution}")
                        # Replace the too-fine resolution with the instrument's minimum
                        resolution = self.min_resolution
                    # Send the command to set the measurement resolution
                    self._instrument.write(f":SENSe:{prefix}:RESolution {resolution}")
                    # Pause briefly to allow the resolution command to take effect
                    time.sleep(0.05)
                # If the resolution command fails, log it and continue
                except Exception as e:
                    self._logger.debug(f"Resolution command failed for {func_token}: {e}")
            # If a resolution was requested but is not supported for this function, log a debug note
            elif resolution is not None:
                self._logger.debug(f"Resolution not supported for {func_token}")

            # Configure NPLC if supported (not supported for AC functions, frequency, period)
            # Only attempt to set the NPLC if both the function supports it and a value was provided
            if supports_nplc and nplc is not None:
                # Attempt to send the NPLC command
                try:
                    # Check whether the requested NPLC is one of the instrument's supported values
                    if nplc not in self._valid_nplc_values:
                        # Create a local copy of the nplc value for safe comparison
                        nplc_val = nplc if nplc is not None else 1.0
                        # Find the closest valid NPLC value to what the caller requested
                        valid_nplc = min(self._valid_nplc_values, key=lambda x: abs(x - nplc_val))
                        # Log a warning that the NPLC was adjusted
                        self._logger.warning(f"Invalid NPLC {nplc}, using {valid_nplc}")
                        # Replace the invalid NPLC with the nearest valid one
                        nplc = valid_nplc
                    # Send the command to set the integration time on the instrument
                    self._instrument.write(f":SENSe:{prefix}:NPLC {nplc}")
                    # Pause briefly to allow the NPLC command to take effect
                    time.sleep(0.05)
                # If the NPLC command fails, log it and continue
                except Exception as e:
                    self._logger.debug(f"NPLC command failed for {func_token}: {e}")
            # If an NPLC was requested but is not supported for this function, log a debug note
            elif nplc is not None:
                self._logger.debug(f"NPLC not supported for {func_token}")

            # Do not send auto-zero headers here to avoid -113 on some models

            # Brief delay to apply settings
            # Pause for 0.2 seconds to allow all configuration commands to fully take effect before triggering a measurement
            time.sleep(0.2)

            # Removed :TRACe:CLEar to avoid -113 on models lacking TRACE buffer

            # Perform measurement
            # Send the READ? query to trigger a fresh measurement and retrieve the result as a text string
            value_str = self._instrument.query(":READ?")
            # Convert the text response from the instrument into a Python floating-point number
            value = float(value_str.strip())

            # Log the successful measurement result including the function type and value
            self._logger.info(f"Measurement {func_token} successful: {value:.9f}")
            # Return the measured value to the caller
            return value

        # If a VISA communication error occurred during measurement (e.g. timeout), handle it here
        except VisaIOError as e:
            # Check specifically whether the error was a timeout so a more informative message can be logged
            if "timeout" in str(e).lower():
                # Log advice to the user: reduce NPLC or increase the timeout setting
                self._logger.error("Measurement timeout - consider increasing timeout or reducing NPLC")
            # If it was a different VISA error, log the raw error detail
            else:
                self._logger.error(f"VISA communication error: {e}")
            # Return None to signal the measurement failed
            return None
        # Catch any other unexpected error that was not handled by the VISA error handler
        except Exception as e:
            # Log the unexpected error along with the measurement function type for context
            self._logger.error(f"Unexpected error during measurement {function.value}: {e}")
            # Return None to signal the measurement failed
            return None

    # Convenience wrappers mirroring common DMM functions
    # Define a shortcut method for AC voltage measurement that calls the general measure() function with the correct mode constant
    def measure_ac_voltage(self,
                           measurement_range: Optional[float] = None,
                           resolution: Optional[float] = None,
                           nplc: Optional[float] = None) -> Optional[float]:
        # Delegate to the general measure() function with the AC voltage mode selected, passing all provided settings
        return self.measure(MeasurementFunction.AC_VOLTAGE, measurement_range, resolution, nplc)

    # Define a shortcut method for DC current measurement that calls the general measure() function with the correct mode constant
    def measure_dc_current(self,
                           measurement_range: Optional[float] = None,
                           resolution: Optional[float] = None,
                           nplc: Optional[float] = None,
                           auto_zero: Optional[bool] = None) -> Optional[float]:
        # Delegate to the general measure() function with the DC current mode selected, passing all provided settings
        return self.measure(MeasurementFunction.DC_CURRENT, measurement_range, resolution, nplc, auto_zero)

    # Define a shortcut method for AC current measurement that calls the general measure() function with the correct mode constant
    def measure_ac_current(self,
                           measurement_range: Optional[float] = None,
                           resolution: Optional[float] = None,
                           nplc: Optional[float] = None) -> Optional[float]:
        # Delegate to the general measure() function with the AC current mode selected, passing all provided settings
        return self.measure(MeasurementFunction.AC_CURRENT, measurement_range, resolution, nplc)

    # Define a shortcut method for two-wire resistance measurement that calls the general measure() function with the correct mode constant
    def measure_resistance_2w(self,
                              measurement_range: Optional[float] = None,
                              resolution: Optional[float] = None,
                              nplc: Optional[float] = None) -> Optional[float]:
        # Delegate to the general measure() function with the 2-wire resistance mode selected, passing all provided settings
        return self.measure(MeasurementFunction.RESISTANCE_2W, measurement_range, resolution, nplc)

    # Define a shortcut method for four-wire resistance measurement that calls the general measure() function with the correct mode constant
    def measure_resistance_4w(self,
                              measurement_range: Optional[float] = None,
                              resolution: Optional[float] = None,
                              nplc: Optional[float] = None) -> Optional[float]:
        # Delegate to the general measure() function with the 4-wire resistance mode selected, passing all provided settings
        return self.measure(MeasurementFunction.RESISTANCE_4W, measurement_range, resolution, nplc)

    # Define a shortcut method for capacitance measurement that calls the general measure() function with the correct mode constant
    def measure_capacitance(self,
                            measurement_range: Optional[float] = None,
                            resolution: Optional[float] = None,
                            nplc: Optional[float] = None) -> Optional[float]:
        # Delegate to the general measure() function with the capacitance mode selected, passing all provided settings
        return self.measure(MeasurementFunction.CAPACITANCE, measurement_range, resolution, nplc)

    # Define a shortcut method for frequency measurement that calls the general measure() function with the correct mode constant
    def measure_frequency(self,
                          measurement_range: Optional[float] = None,
                          resolution: Optional[float] = None,
                          nplc: Optional[float] = None) -> Optional[float]:
        # Delegate to the general measure() function with the frequency mode selected, passing all provided settings
        return self.measure(MeasurementFunction.FREQUENCY, measurement_range, resolution, nplc)

    # Define a shortcut method for signal period measurement that calls the general measure() function with the correct mode constant
    def measure_period(self,
                       measurement_range: Optional[float] = None,
                       resolution: Optional[float] = None) -> Optional[float]:
        """
        Measure signal period.

        Args:
            measurement_range: Expected voltage range of signal
            resolution: Desired measurement resolution

        Returns:
            Period in seconds, or None on failure
        """
        # Delegate to the general measure() function with the period mode selected, passing only the range and resolution
        return self.measure(MeasurementFunction.PERIOD, measurement_range, resolution)

    # Define a shortcut method for temperature measurement that calls the general measure() function with the correct mode constant
    def measure_temperature(self,
                           sensor_type: str = "RTD",
                           measurement_range: Optional[float] = None) -> Optional[float]:
        """
        Measure temperature using RTD or thermocouple sensors.

        Args:
            sensor_type: Sensor type - "RTD", "TC", "THER"
            measurement_range: Temperature range (°C)

        Returns:
            Temperature in degrees Celsius, or None on failure

        Note:
            Sensor types: RTD (PT100, PT385), Thermocouple (K, J, T, E, R, S, B, N)
        """
        # Delegate to the general measure() function with the temperature mode selected, passing only the range
        return self.measure(MeasurementFunction.TEMPERATURE, measurement_range)

    # Define a shortcut method for diode testing that calls the general measure() function with the correct mode constant
    def measure_diode(self,
                      measurement_range: Optional[float] = None) -> Optional[float]:
        """
        Perform diode test measurement.

        Applies forward bias current and measures voltage drop.
        Typical silicon diode: 0.5-0.7V

        Args:
            measurement_range: Voltage range (typically 10V)

        Returns:
            Forward voltage drop in volts, or None on failure
        """
        # Delegate to the general measure() function with the diode test mode selected
        return self.measure(MeasurementFunction.DIODE, measurement_range)

    # Define a shortcut method for continuity testing that calls the general measure() function with the correct mode constant
    def measure_continuity(self) -> Optional[float]:
        """
        Perform continuity test.

        Measures resistance with audible tone for low resistance.
        Threshold typically ~10Ω.

        Returns:
            Resistance in ohms, or None on failure
        """
        # Delegate to the general measure() function with the continuity mode selected
        return self.measure(MeasurementFunction.CONTINUITY)

    # ========================================================================
    # TRIGGER SUBSYSTEM - Advanced measurement triggering control
    # ========================================================================

    # Define the function that configures how and when the instrument starts taking measurements (the trigger system)
    def configure_trigger(self,
                         source: TriggerSource = TriggerSource.IMMEDIATE,
                         count: int = 1,
                         delay: float = 0.0,
                         timer_interval: Optional[float] = None) -> bool:
        """
        Configure measurement trigger system.

        Professional implementation of IEEE 488.2 trigger subsystem for
        precise control of measurement timing and sequencing.

        Args:
            source: Trigger source (IMMEDIATE, BUS, EXTERNAL, etc.)
            count: Number of measurements per trigger (1-1e6, INF)
            delay: Delay after trigger before measurement (0-10000s)
            timer_interval: Timer period if source is TIMER (1e-6 to 1e6s)

        Returns:
            True if configuration successful

        Raises:
            KeithleyDMM6500Error: If invalid parameters or communication error

        Example:
            >>> dmm.configure_trigger(TriggerSource.BUS, count=10, delay=0.001)
            >>> dmm.initiate_measurement()
            >>> dmm.send_software_trigger()  # Trigger via *TRG
        """
        # If the instrument is not connected, raise an error immediately rather than trying to configure a disconnected device
        if not self._is_connected:
            raise KeithleyDMM6500Error("Multimeter not connected")

        # Begin a protected block for the trigger configuration sequence
        try:
            # Log the trigger configuration details for traceability in the test log
            self._logger.info(f"Configuring trigger: source={source.value}, count={count}, delay={delay}")

            # Removed :ABORt command as it causes -113 on this DMM model

            # Set trigger source
            # Send the command to select which type of event will start a measurement sequence
            self._instrument.write(f":TRIGger:SOURce {source.value}")

            # Set trigger count
            # Verify the count is at least 1 before sending it to the instrument
            if count < 1:
                raise ValueError("Trigger count must be >= 1")
            # Send the command to set how many measurements the instrument will take each time it is triggered
            self._instrument.write(f":TRIGger:COUNt {count}")

            # Set trigger delay
            # Verify the delay is not negative before sending it to the instrument
            if delay < 0:
                raise ValueError("Trigger delay must be >= 0")
            # Send the command to set how long the instrument waits after a trigger event before starting the measurement
            self._instrument.write(f":TRIGger:DELay {delay}")

            # Configure timer interval if using timer trigger
            # If the trigger source is an internal timer, also configure the time interval between trigger events
            if source == TriggerSource.TIMER:
                # Require the caller to provide a timer interval when using TIMER trigger source
                if timer_interval is None:
                    raise ValueError("timer_interval required when source is TIMER")
                # Validate that the timer interval is within the instrument's supported range
                if timer_interval < 1e-6 or timer_interval > 1e6:
                    raise ValueError("Timer interval must be between 1µs and 1000s")
                # Send the command to set the internal timer interval in seconds
                self._instrument.write(f":TRIGger:TIMer {timer_interval}")

            # Verify settings took effect
            # Query the operation-complete flag to confirm all trigger settings were applied successfully
            self._instrument.query("*OPC?")

            # Log that the trigger configuration completed without errors
            self._logger.info("Trigger configuration successful")
            # Return True to inform the caller the configuration succeeded
            return True

        # Catch any error that occurred during trigger configuration and re-raise it as a custom error
        except Exception as e:
            # Log the specific error that caused the trigger configuration to fail
            self._logger.error(f"Trigger configuration failed: {e}")
            # Re-raise the error as a KeithleyDMM6500Error so the caller knows it came from this instrument
            raise KeithleyDMM6500Error(f"Trigger configuration error: {e}") from e

    # Define the function that arms the instrument to wait for a trigger event before taking measurements
    def initiate_measurement(self) -> bool:
        """
        Initiate measurement system to wait for trigger.

        After calling this, the instrument waits for the configured trigger
        source before taking measurements. Use with configure_trigger().

        Returns:
            True if initiation successful

        Note:
            Use :INITiate when you need precise control over measurement timing.
            For simple single measurements, use :READ? which combines INIT+FETCH.
        """
        # If the instrument is not connected, raise an error immediately
        if not self._is_connected:
            raise KeithleyDMM6500Error("Multimeter not connected")

        # Begin a protected block for the initiate command
        try:
            # Send the initiate command to arm the instrument and put it in the "waiting for trigger" state
            self._instrument.write(":INITiate")
            # Log that the instrument has been armed and is waiting for the configured trigger event
            self._logger.debug("Measurement initiated, waiting for trigger")
            # Return True to confirm the initiate command was sent successfully
            return True
        # Catch any error that prevented the initiate command from being sent
        except Exception as e:
            # Log the error that caused the initiation to fail
            self._logger.error(f"Failed to initiate measurement: {e}")
            # Return False to signal the initiation was unsuccessful
            return False

    # Define the function that sends a software trigger command over the communication bus to start a measurement
    def send_software_trigger(self) -> bool:
        """
        Send software trigger (Bus trigger).

        Use when trigger source is set to BUS. Equivalent to *TRG command.

        Returns:
            True if trigger sent successfully
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # Begin a protected block for sending the trigger command
        try:
            # Send the IEEE 488.2 trigger command (*TRG) over the communication bus to start a measurement
            self._instrument.write("*TRG")
            # Log that the software trigger was sent successfully
            self._logger.debug("Software trigger sent")
            # Return True to confirm the trigger command was sent
            return True
        # Catch any error that prevented the trigger command from being sent
        except Exception as e:
            # Log the error that caused the trigger command to fail
            self._logger.error(f"Failed to send software trigger: {e}")
            # Return False to signal the trigger was not sent
            return False

    # Define the function that retrieves the most recently completed measurement from the instrument's memory without triggering a new one
    def fetch_measurement(self) -> Optional[float]:
        """
        Fetch the latest measurement without initiating new measurement.

        Use after initiate_measurement() completes. This retrieves readings
        from the instrument's reading buffer without taking new measurements.

        Returns:
            Measurement value, or None on failure

        Note:
            :FETCh? returns the most recent reading. Use :READ? to trigger
            and fetch in one command, or :INITiate then :FETCh? for precise
            timing control.
        """
        # If the instrument is not connected, return None immediately
        if not self._is_connected:
            return None

        # Begin a protected block for the fetch command
        try:
            # Send the FETCh? query to retrieve the most recently completed measurement from the instrument's buffer
            result = self._instrument.query(":FETCh?")
            # Convert the text response to a Python floating-point number
            value = float(result.strip())
            # Log the fetched value for debugging
            self._logger.debug(f"Fetched measurement: {value}")
            # Return the fetched measurement value to the caller
            return value
        # Catch any error that occurred during the fetch
        except Exception as e:
            # Log the error that caused the fetch to fail
            self._logger.error(f"Failed to fetch measurement: {e}")
            # Return None to signal the fetch failed
            return None

    # Define a stub function for aborting measurements; the actual abort command is not supported on this DMM model
    def abort_measurement(self) -> bool:
        """
        Abort any running measurement operations.

        Note: :ABORt command causes -113 error on this DMM model and has been removed.
        This method now does nothing but returns True for compatibility.

        Returns:
            True (always, for compatibility)
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # ABORt command removed as it causes -113 on this DMM model
        # Log a debug note that this function was called but no command was sent because it is not supported
        self._logger.debug("Abort called but :ABORt not supported on this model")
        # Return True so any calling code that checks this return value does not consider it an error
        return True

    # ========================================================================
    # BUFFER/TRACE SUBSYSTEM - Data logging and retrieval
    # ========================================================================

    # Define the function that sets up the instrument's internal reading buffer for storing multiple measurements over time
    def configure_buffer(self,
                        buffer_name: str = "defbuffer1",
                        buffer_size: int = 100000,
                        fill_mode: str = "CONTINUOUS") -> bool:
        """
        Configure reading buffer for data logging.

        The DMM6500 has two default buffers (defbuffer1, defbuffer2) and
        supports user-defined buffers for sophisticated data acquisition.

        Args:
            buffer_name: Buffer identifier (defbuffer1, defbuffer2, or custom)
            buffer_size: Number of readings to store (1 to 7e6)
            fill_mode: "CONTINUOUS" (circular) or "ONCE" (stop when full)

        Returns:
            True if configuration successful

        Raises:
            KeithleyDMM6500Error: If invalid parameters

        Example:
            >>> dmm.configure_buffer("defbuffer1", 1000, "CONTINUOUS")
            >>> dmm.clear_buffer("defbuffer1")
            >>> # Take measurements...
            >>> data = dmm.fetch_buffer_data("defbuffer1")
        """
        # If the instrument is not connected, raise an error immediately
        if not self._is_connected:
            raise KeithleyDMM6500Error("Multimeter not connected")

        # Begin a protected block for the buffer configuration sequence
        try:
            # Log the buffer configuration details for traceability
            self._logger.info(f"Configuring buffer {buffer_name}: size={buffer_size}, fill={fill_mode}")

            # Validate buffer size
            # Ensure the requested buffer size is within the supported range (1 to 7 million readings)
            if buffer_size < 1 or buffer_size > 7000000:
                raise ValueError("Buffer size must be between 1 and 7000000")

            # Validate fill mode
            # Ensure the fill mode is one of the two accepted values
            if fill_mode not in ["CONTINUOUS", "ONCE"]:
                raise ValueError("Fill mode must be 'CONTINUOUS' or 'ONCE'")

            # Clear any existing buffer data (wrapped in try-except as not all models support TRACe)
            # Try to clear any old data from the buffer before reconfiguring it
            try:
                # Send the command to erase all existing readings from the named buffer
                self._instrument.write(f":TRACe:CLEar \"{buffer_name}\"")
                # Pause briefly to allow the clear operation to complete
                time.sleep(0.1)
            # If the clear command is not supported on this model, log a debug note and continue
            except Exception as e:
                self._logger.debug(f"TRACe:CLEar not supported, skipping: {e}")

            # Set buffer capacity (wrapped as not all models support TRACe)
            # Try to set the number of readings the buffer can hold
            try:
                # Send the command to allocate space for the specified number of readings in the named buffer
                self._instrument.write(f":TRACe:POINts {buffer_size}, \"{buffer_name}\"")
            # If the buffer size command is not supported, raise a descriptive error
            except Exception as e:
                self._logger.warning(f"TRACe:POINts not supported: {e}")
                raise KeithleyDMM6500Error("Buffer configuration not supported on this DMM model") from e

            # Set fill mode (wrapped as not all models support TRACe)
            # Try to set how the buffer behaves when it fills up (overwrite continuously or stop)
            try:
                # Send the command to set the buffer fill mode on the named buffer
                self._instrument.write(f":TRACe:FILL:MODE {fill_mode}, \"{buffer_name}\"")
            # If the fill mode command is not supported, raise a descriptive error
            except Exception as e:
                self._logger.warning(f"TRACe:FILL:MODE not supported: {e}")
                raise KeithleyDMM6500Error("Buffer configuration not supported on this DMM model") from e

            # Verify configuration
            # Query the operation-complete flag to confirm all buffer settings were applied
            self._instrument.query("*OPC?")

            # Log confirmation that the buffer was configured successfully
            self._logger.info("Buffer configuration successful")
            # Return True to tell the caller the buffer is ready for use
            return True

        # Catch any error that occurred during buffer configuration and re-raise as a custom error
        except Exception as e:
            # Log the error that caused the buffer configuration to fail
            self._logger.error(f"Buffer configuration failed: {e}")
            # Re-raise as a KeithleyDMM6500Error so the caller can identify the source
            raise KeithleyDMM6500Error(f"Buffer configuration error: {e}") from e

    # Define the function that erases all stored readings from the named buffer on the instrument
    def clear_buffer(self, buffer_name: str = "defbuffer1") -> bool:
        """
        Clear all data from specified buffer.

        Args:
            buffer_name: Buffer to clear (default: "defbuffer1")

        Returns:
            True if clear successful
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # Begin a protected block for the buffer clear operation
        try:
            # Attempt the inner buffer clear, which may not be supported on all models
            try:
                # Send the command to erase all readings stored in the named buffer
                self._instrument.write(f":TRACe:CLEar \"{buffer_name}\"")
                # Log that the buffer was cleared successfully
                self._logger.debug(f"Buffer {buffer_name} cleared")
                # Return True to confirm the clear was successful
                return True
            # If the clear command is not supported on this model, log a debug note and return True anyway
            except Exception as e:
                # Some models don't support TRACe commands
                # Log that the TRACe:CLEar command is not supported on this model but treat it as a non-fatal issue
                self._logger.debug(f"TRACe:CLEar not supported on this model: {e}")
                return True  # Return success as buffer may not need clearing
        # Catch any other unexpected error
        except Exception as e:
            # Log the error that caused the clear attempt to fail
            self._logger.error(f"Failed to clear buffer {buffer_name}: {e}")
            # Return False to signal the clear was unsuccessful
            return False

    # Define the function that retrieves statistical summary data (mean, min, max, etc.) from the instrument's internal buffer analysis
    def get_buffer_statistics(self, buffer_name: str = "defbuffer1") -> Optional[Dict[str, float]]:
        """
        Retrieve statistical analysis of buffered data.

        Uses instrument's built-in statistics calculation for maximum accuracy
        and efficiency. Much faster than transferring all data for client-side
        calculation.

        Args:
            buffer_name: Buffer to analyze (default: "defbuffer1")

        Returns:
            Dictionary with mean, stddev, min, max, count, or None on failure

        Example:
            >>> stats = dmm.get_buffer_statistics("defbuffer1")
            >>> print(f"Mean: {stats['mean']:.6f}V, StdDev: {stats['stddev']:.6f}V")
        """
        # If the instrument is not connected, return None immediately
        if not self._is_connected:
            return None

        # Begin a protected block for the buffer statistics queries
        try:
            # Query buffer statistics using SCPI calculate commands
            # Wrap in try-except as TRACe commands may not be supported on all models
            # Try the buffer statistics queries — these may not be available on all firmware versions
            try:
                # Ask the instrument how many readings are currently stored in the named buffer
                count = int(self._instrument.query(f":TRACe:ACTual? \"{buffer_name}\"").strip())

                # If the buffer is empty, there are no statistics to calculate
                if count == 0:
                    # Log a warning that the buffer is empty and return None
                    self._logger.warning(f"Buffer {buffer_name} is empty")
                    return None

                # Get statistics from instrument
                # Ask the instrument for the average (mean) value of all readings in the buffer
                mean = float(self._instrument.query(f":TRACe:STATistics:AVERage? \"{buffer_name}\"").strip())
                # Ask the instrument for the standard deviation of the readings in the buffer
                stddev = float(self._instrument.query(f":TRACe:STATistics:STDDev? \"{buffer_name}\"").strip())
                # Ask the instrument for the minimum reading stored in the buffer
                minimum = float(self._instrument.query(f":TRACe:STATistics:MINimum? \"{buffer_name}\"").strip())
                # Ask the instrument for the maximum reading stored in the buffer
                maximum = float(self._instrument.query(f":TRACe:STATistics:MAXimum? \"{buffer_name}\"").strip())
                # Ask the instrument for the peak-to-peak value (difference between max and min) in the buffer
                pk_pk = float(self._instrument.query(f":TRACe:STATistics:PK2Pk? \"{buffer_name}\"").strip())

                # Build a dictionary containing all the statistical results retrieved from the instrument
                stats = {
                    # Number of readings stored in the buffer
                    'count': count,
                    # Average value of all readings
                    'mean': mean,
                    # Standard deviation (spread) of the readings
                    'stddev': stddev,
                    # Smallest reading in the buffer
                    'minimum': minimum,
                    # Largest reading in the buffer
                    'maximum': maximum,
                    # Difference between the largest and smallest readings
                    'peak_to_peak': pk_pk
                }

                # Log a summary of the buffer statistics for traceability
                self._logger.info(f"Buffer stats: {count} pts, mean={mean:.6f}, stddev={stddev:.6f}")
                # Return the statistics dictionary to the caller
                return stats
            # If the statistics commands are not supported on this model, log a warning and return None
            except Exception as e:
                self._logger.warning(f"TRACe:STATistics commands not supported on this model: {e}")
                # Advise the caller to retrieve raw buffer data and calculate statistics on the computer instead
                self._logger.info("Buffer statistics not available - use fetch_buffer_data() and calculate manually")
                return None

        # Catch any other unexpected error that occurred during the statistics query
        except Exception as e:
            # Log the error that prevented the statistics from being retrieved
            self._logger.error(f"Failed to get buffer statistics: {e}")
            # Return None to signal the statistics query failed
            return None

    # Define the function that downloads stored measurement readings from the instrument's internal buffer to the computer
    def fetch_buffer_data(self,
                         buffer_name: str = "defbuffer1",
                         start_index: int = 1,
                         end_index: Optional[int] = None) -> Optional[List[float]]:
        """
        Retrieve measurement data from buffer.

        Fetches readings with timestamps and metadata. For large datasets,
        consider using start/end indices to retrieve data in chunks.

        Args:
            buffer_name: Buffer to read from
            start_index: Starting index (1-based, default 1)
            end_index: Ending index (None = all available)

        Returns:
            List of measurement values, or None on failure

        Note:
            For high-speed acquisition with 100k+ samples, consider using
            binary transfer format or chunked retrieval to avoid timeouts.
        """
        # If the instrument is not connected, return None immediately
        if not self._is_connected:
            return None

        # Begin a protected block for the buffer data retrieval
        try:
            # Get actual buffer count if end_index not specified
            # Wrap in try-except as TRACe commands may not be supported on all models
            # Try the buffer data retrieval — this may not be available on all firmware versions
            try:
                # If no end index was specified, ask the instrument how many readings are available and use that as the end
                if end_index is None:
                    # Query the number of readings currently stored in the named buffer
                    count_str = self._instrument.query(f":TRACe:ACTual? \"{buffer_name}\"")
                    # Convert the response to an integer to use as the end index
                    end_index = int(count_str.strip())

                # Validate that the end index is at least as large as the start index
                if end_index < start_index:
                    # Log an error explaining that the end index cannot be before the start index
                    self._logger.error("end_index must be >= start_index")
                    return None

                # Fetch data from buffer
                # Build the SCPI query command requesting readings from start_index to end_index in the named buffer
                query_cmd = f":TRACe:DATA? {start_index}, {end_index}, \"{buffer_name}\", READ"
                # Send the query and receive the comma-separated list of readings as a single text string
                data_str = self._instrument.query(query_cmd)

                # Parse comma-separated values
                # Split the text string by commas and convert each value to a float, skipping any empty fields
                values = [float(x.strip()) for x in data_str.split(',') if x.strip()]

                # Log how many readings were successfully retrieved from the buffer
                self._logger.info(f"Retrieved {len(values)} readings from {buffer_name}")
                # Return the list of measurement values to the caller
                return values
            # If the buffer data retrieval commands are not supported on this model, log a warning and return None
            except Exception as e:
                self._logger.warning(f"TRACe commands not supported on this model: {e}")
                # Advise the caller that buffer data retrieval is not available on this instrument
                self._logger.info("Buffer data retrieval not available on this model")
                return None

        # Catch any other unexpected error that occurred during buffer data retrieval
        except Exception as e:
            # Log the error that prevented the buffer data from being downloaded
            self._logger.error(f"Failed to fetch buffer data: {e}")
            # Return None to signal the retrieval failed
            return None

    # ========================================================================
    # DISPLAY CONTROL - Front panel display management
    # ========================================================================

    # Define the function that switches the front-panel screen of the instrument to a different display mode
    def set_display_state(self, state: DisplayState) -> bool:
        """
        Set front panel display screen.

        Args:
            state: Display state from DisplayState enum

        Returns:
            True if display change successful

        Example:
            >>> dmm.set_display_state(DisplayState.READING)  # Show live readings
            >>> dmm.set_display_state(DisplayState.STATISTICS)  # Show stats
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # Begin a protected block for the display command
        try:
            # Send the command to switch the instrument's front-panel display to the requested screen
            self._instrument.write(f":DISPlay:SCReen {state.value}")
            # Log which screen was activated
            self._logger.debug(f"Display set to {state.value}")
            # Return True to confirm the display command was sent successfully
            return True
        # Catch any error that prevented the display from being changed
        except Exception as e:
            # Log the error that caused the display command to fail
            self._logger.error(f"Failed to set display state: {e}")
            # Return False to signal the command was unsuccessful
            return False

    # Define the function that shows a custom text message on the instrument's front-panel display
    def display_text(self, text: str, row: int = 1) -> bool:
        """
        Display custom text on front panel (user screen).

        Args:
            text: Text to display (max ~40 characters)
            row: Row number (1-5 depending on model)

        Returns:
            True if text displayed successfully

        Example:
            >>> dmm.display_text("PSU VOLTAGE TEST", row=1)
            >>> dmm.display_text("PASS: 5.023V", row=2)
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # Begin a protected block for the display text command
        try:
            # Switch to user screen first
            # Switch the instrument's display to the user-defined text screen before writing the message
            self._instrument.write(":DISPlay:SCReen USER")
            # Pause briefly to allow the screen transition to complete
            time.sleep(0.05)

            # Display text on specified row
            # Send the command to write the provided text onto the specified row of the user display
            self._instrument.write(f":DISPlay:USER:TEXT \"{text}\",{row}")
            # Log which text was displayed and on which row
            self._logger.debug(f"Displayed text on row {row}: {text}")
            # Return True to confirm the text was displayed successfully
            return True
        # Catch any error that prevented the text from being displayed
        except Exception as e:
            # Log the error that caused the display text command to fail
            self._logger.error(f"Failed to display text: {e}")
            # Return False to signal the command was unsuccessful
            return False

    # Define the function that erases any custom text currently shown on the instrument's front-panel user display
    def clear_display_text(self) -> bool:
        """
        Clear all text from user display screen.

        Returns:
            True if clear successful
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # Begin a protected block for the display clear command
        try:
            # Send the command to erase all text from the instrument's front-panel display
            self._instrument.write(":DISPlay:CLEar")
            # Log that the display was cleared
            self._logger.debug("Display cleared")
            # Return True to confirm the display was cleared successfully
            return True
        # Catch any error that prevented the display from being cleared
        except Exception as e:
            # Log the error that caused the clear command to fail
            self._logger.error(f"Failed to clear display: {e}")
            # Return False to signal the command was unsuccessful
            return False

    # Define the function that triggers the instrument's built-in speaker to produce a tone at a specified frequency and duration
    def beep(self, frequency: float = 2000.0, duration: float = 0.5) -> bool:
        """
        Sound beeper for audible indication.

        Args:
            frequency: Tone frequency in Hz (65-4000Hz)
            duration: Beep duration in seconds (0.001-7.9s)

        Returns:
            True if beep command successful

        Example:
            >>> dmm.beep(1000, 0.2)  # Short confirmation beep
            >>> dmm.beep(4000, 1.0)  # High-pitched alert
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # Begin a protected block for the beep command
        try:
            # Validate parameters
            # Clamp the frequency to the instrument's valid range: 65 Hz minimum, 4000 Hz maximum
            frequency = max(65, min(4000, frequency))
            # Clamp the duration to the instrument's valid range: 0.001 seconds minimum, 7.9 seconds maximum
            duration = max(0.001, min(7.9, duration))

            # Send the command to sound the instrument's beeper at the specified frequency and duration
            self._instrument.write(f":SYSTem:BEEPer {frequency}, {duration}")
            # Log the beep parameters for debugging
            self._logger.debug(f"Beep: {frequency}Hz for {duration}s")
            # Return True to confirm the beep command was sent
            return True
        # Catch any error that prevented the beep from being triggered
        except Exception as e:
            # Log the error that caused the beep command to fail
            self._logger.error(f"Failed to beep: {e}")
            # Return False to signal the command was unsuccessful
            return False

    # ========================================================================
    # MATH AND LIMIT TESTING - Measurement post-processing
    # ========================================================================

    # Define the function that would configure linear scaling (mx+b) on the instrument; currently unsupported on this DMM model
    def configure_math_mxb(self,
                           m_factor: float = 1.0,
                           b_offset: float = 0.0,
                           enable: bool = True) -> bool:
        """
        Configure mx+b scaling for measurements.

        Apply linear scaling to readings: result = m * reading + b
        Useful for sensor calibration, unit conversion, etc.

        Args:
            m_factor: Multiplicative scale factor (m)
            b_offset: Additive offset (b)
            enable: Enable math function

        Returns:
            True if configuration successful

        Example:
            >>> # Convert voltage to temperature: T = 100*V + 0
            >>> dmm.configure_math_mxb(m_factor=100, b_offset=0)
            >>> temp = dmm.measure_dc_voltage()  # Returns scaled value
        """
        # If the instrument is not connected, raise an error immediately
        if not self._is_connected:
            raise KeithleyDMM6500Error("Multimeter not connected")

        # CALCulate commands cause -113 on this DMM model - feature not available
        # Log a warning that the mathematical scaling feature is not available on this instrument
        self._logger.warning(":CALCulate commands not supported on this model")
        # Raise an error to clearly inform the caller that this feature cannot be used on this DMM model
        raise KeithleyDMM6500Error("Math MXB function not supported on this DMM model")

    # Define the function that would configure upper and lower pass/fail limits for measurements; currently unsupported on this DMM model
    def configure_limit_test(self,
                            lower_limit: float,
                            upper_limit: float,
                            enable: bool = True) -> bool:
        """
        Configure limit testing for pass/fail analysis.

        Note: :CALCulate commands cause -113 error on this DMM model.
        This feature is not available on your DMM.

        Args:
            lower_limit: Lower limit value
            upper_limit: Upper limit value
            enable: Enable limit testing

        Returns:
            False (feature not supported)

        Example:
            >>> dmm.configure_limit_test(4.95, 5.05)  # Will raise error
        """
        # If the instrument is not connected, raise an error immediately
        if not self._is_connected:
            raise KeithleyDMM6500Error("Multimeter not connected")

        # CALCulate commands cause -113 on this DMM model - feature not available
        # Log a warning that limit testing is not available on this instrument
        self._logger.warning(":CALCulate commands not supported on this model")
        # Raise an error to clearly inform the caller that limit testing cannot be used on this DMM model
        raise KeithleyDMM6500Error("Limit test function not supported on this DMM model")

    # Define the function that would retrieve the pass/fail result of the last limit test; currently unsupported on this DMM model
    def get_limit_test_result(self) -> Optional[str]:
        """
        Get limit test result for last measurement.

        Note: :CALCulate commands cause -113 error on this DMM model.
        This feature is not available on your DMM.

        Returns:
            None (feature not supported)
        """
        # If the instrument is not connected, return None immediately
        if not self._is_connected:
            return None

        # CALCulate commands cause -113 on this DMM model - feature not available
        # Log a warning that the limit test result query is not available on this instrument
        self._logger.warning(":CALCulate:DATA? not supported on this model")
        # Return None to indicate the feature is not available on this DMM model
        return None

    # Define the function that would disable all active math operations on the instrument; returns True immediately as math is not supported on this model
    def disable_math(self) -> bool:
        """
        Disable all math operations.

        Note: :CALCulate commands cause -113 error on this DMM model.
        This feature is not available on your DMM.

        Returns:
            True (always, as math operations are not supported)
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # CALCulate commands cause -113 on this DMM model - feature not available
        # Log a debug note that the math disable command is not supported but return success anyway
        self._logger.debug(":CALCulate:STATe not supported on this model")
        # Return True because math operations are already unavailable, so disabling is effectively a no-operation
        return True  # Return success as math operations are not available anyway

    # ========================================================================
    # SYSTEM COMMANDS - Configuration and status
    # ========================================================================

    # Define the function that sends the IEEE 488.2 reset command to restore the instrument to its factory default state
    def reset_instrument(self) -> bool:
        """
        Perform complete instrument reset (*RST).

        Resets all settings to factory defaults. More thorough than
        system preset but slower. Clears buffers, aborts measurements,
        and restores default configuration.

        Returns:
            True if reset successful

        Warning:
            This will erase all user settings and buffer data.
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # Begin a protected block for the reset sequence
        try:
            # Log a warning that a full factory reset is about to be performed, which erases all user settings
            self._logger.warning("Performing instrument reset (*RST)")
            # Send the IEEE 488.2 reset command to restore the instrument to its factory default configuration
            self._instrument.write("*RST")
            # Pause for 2 full seconds to allow the instrument to fully complete its internal reset process
            time.sleep(2.0)  # Allow reset to complete

            # Clear status registers
            # Send the clear-status command after the reset to remove any flags set during the reset process
            self._instrument.write("*CLS")
            # Pause briefly to allow the clear command to complete
            time.sleep(0.2)

            # Verify instrument responsive
            # Query the operation-complete flag to confirm the instrument is ready to receive commands again
            self._instrument.query("*OPC?")

            # Log confirmation that the reset completed successfully
            self._logger.info("Instrument reset completed")
            # Return True to inform the caller the reset was successful
            return True

        # Catch any error that occurred during the reset sequence
        except Exception as e:
            # Log the error that prevented the reset from completing
            self._logger.error(f"Failed to reset instrument: {e}")
            # Return False to signal the reset was unsuccessful
            return False

    # Define the function that performs a fast system preset to restore the instrument to default settings
    def system_preset(self) -> bool:
        """
        Perform fast system preset.

        Note: :SYSTem:PRESet causes -113 error on some models, so this
        uses *RST instead for compatibility.

        Returns:
            True if preset successful
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # Begin a protected block for the preset sequence
        try:
            # Log that a system preset is being performed using the reset command
            self._logger.info("Performing system preset with *RST")
            # Use *RST instead of :SYSTem:PRESet (causes -113 on some models)
            # Send the reset command as a substitute for the preset command (which is not compatible with all models)
            self._instrument.write("*RST")
            # Pause for 1 second to allow the reset to complete before sending further commands
            time.sleep(1.0)  # Allow reset to complete

            # Send the clear-status command to remove any flags set during the reset
            self._instrument.write("*CLS")
            # Log confirmation that the system preset completed successfully
            self._logger.info("System preset completed")
            # Return True to inform the caller the preset was successful
            return True

        # Catch any error that occurred during the preset sequence
        except Exception as e:
            # Log the error that prevented the preset from completing
            self._logger.error(f"Failed to perform system preset: {e}")
            # Return False to signal the preset was unsuccessful
            return False

    # Define the function that retrieves the instrument's internal clock date and time
    def get_system_date_time(self) -> Optional[str]:
        """
        Retrieve instrument date and time.

        Returns:
            ISO format timestamp string, or None on failure

        Example:
            >>> timestamp = dmm.get_system_date_time()
            >>> print(f"Instrument time: {timestamp}")
        """
        # If the instrument is not connected, return None immediately
        if not self._is_connected:
            return None

        # Begin a protected block for the date and time queries
        try:
            # Query date and time separately
            # Ask the instrument for its current date and remove surrounding whitespace from the response
            date_str = self._instrument.query(":SYSTem:DATE?").strip()
            # Ask the instrument for its current time and remove surrounding whitespace from the response
            time_str = self._instrument.query(":SYSTem:TIME?").strip()

            # Combine the date and time strings into a single timestamp string
            timestamp = f"{date_str} {time_str}"
            # Return the combined timestamp to the caller
            return timestamp

        # Catch any error that occurred while querying the instrument's date and time
        except Exception as e:
            # Log the error that prevented the date and time from being retrieved
            self._logger.error(f"Failed to get system date/time: {e}")
            # Return None to signal the query failed
            return None

    # Define the function that sets the instrument's power-line frequency setting, which affects noise rejection for AC-synchronised measurements
    def set_line_frequency(self, frequency: int = 60) -> bool:
        """
        Set power line frequency for noise rejection.

        Args:
            frequency: Line frequency in Hz (50 or 60)

        Returns:
            True if frequency set successfully

        Note:
            Set to match local power line frequency (50Hz Europe, 60Hz Americas)
            for optimal noise rejection at 1 NPLC and higher integration times.
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # Begin a protected block for the line frequency command
        try:
            # Validate that only 50 or 60 Hz are accepted, as these are the only standard mains frequencies
            if frequency not in [50, 60]:
                raise ValueError("Line frequency must be 50 or 60 Hz")

            # Send the command to set the instrument's line frequency reference to the specified value
            self._instrument.write(f":SYSTem:LFRequency {frequency}")
            # Log confirmation that the line frequency was set
            self._logger.info(f"Line frequency set to {frequency}Hz")
            # Return True to confirm the command was sent successfully
            return True

        # Catch any error that occurred while setting the line frequency
        except Exception as e:
            # Log the error that prevented the line frequency from being set
            self._logger.error(f"Failed to set line frequency: {e}")
            # Return False to signal the command was unsuccessful
            return False

    # Define the function that saves the current instrument configuration to one of five non-volatile memory slots
    def save_setup(self, location: int = 1) -> bool:
        """
        Save current instrument configuration to non-volatile memory.

        Args:
            location: Save location number (1-5)

        Returns:
            True if save successful

        Example:
            >>> dmm.save_setup(1)  # Save to location 1
            >>> # Later...
            >>> dmm.recall_setup(1)  # Restore configuration
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # Begin a protected block for the save command
        try:
            # Validate that the location number is within the supported range of 1 to 5
            if location < 1 or location > 5:
                raise ValueError("Save location must be 1-5")

            # Send the command to save the current instrument configuration to the specified memory slot
            self._instrument.write(f":SYSTem:SETUP:SAVE {location}")
            # Log confirmation that the configuration was saved and to which location
            self._logger.info(f"Configuration saved to location {location}")
            # Return True to confirm the save was successful
            return True

        # Catch any error that occurred while saving the configuration
        except Exception as e:
            # Log the error that prevented the configuration from being saved
            self._logger.error(f"Failed to save setup: {e}")
            # Return False to signal the save was unsuccessful
            return False

    # Define the function that restores a previously saved instrument configuration from one of the five non-volatile memory slots
    def recall_setup(self, location: int = 1) -> bool:
        """
        Recall instrument configuration from non-volatile memory.

        Args:
            location: Recall location number (1-5)

        Returns:
            True if recall successful
        """
        # If the instrument is not connected, return False immediately
        if not self._is_connected:
            return False

        # Begin a protected block for the recall command
        try:
            # Validate that the location number is within the supported range of 1 to 5
            if location < 1 or location > 5:
                raise ValueError("Recall location must be 1-5")

            # Send the command to load the saved configuration from the specified memory slot
            self._instrument.write(f":SYSTem:SETUP:RECall {location}")
            # Pause for 0.5 seconds to allow the instrument to finish loading the recalled configuration
            time.sleep(0.5)  # Allow recall to complete
            # Log confirmation that the configuration was recalled from the specified location
            self._logger.info(f"Configuration recalled from location {location}")
            # Return True to confirm the recall was successful
            return True

        # Catch any error that occurred while recalling the configuration
        except Exception as e:
            # Log the error that prevented the configuration from being recalled
            self._logger.error(f"Failed to recall setup: {e}")
            # Return False to signal the recall was unsuccessful
            return False

    # ========================================================================
    # CONTEXT MANAGER SUPPORT - Pythonic resource management
    # ========================================================================

    # Define the special method that runs automatically when this object is used in a "with" statement, connecting to the instrument
    def __enter__(self) -> 'KeithleyDMM6500':
        """
        Context manager entry - automatically connect.

        Example:
            >>> with KeithleyDMM6500(visa_address) as dmm:
            >>>     voltage = dmm.measure_dc_voltage()
            >>>     # Automatically disconnects on exit
        """
        # Check whether the instrument is already connected before trying to connect again
        if not self._is_connected:
            # Attempt to connect and raise an error if the connection fails, so the "with" block does not proceed
            if not self.connect():
                raise KeithleyDMM6500Error("Failed to connect to instrument")
        # Return the current object (self) so the "with ... as dmm:" syntax provides the caller with this instance
        return self

    # Define the special method that runs automatically when the "with" block ends, disconnecting from the instrument
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - automatically disconnect."""
        # Call the disconnect method to safely close the connection and release all resources when the "with" block exits
        self.disconnect()

    # Define the internal helper method that resets all connection-related variables back to their uninitialised state
    def _cleanup_connection(self) -> None:
        """Clean up connection state and references."""
        # Set the connection status flag to False to indicate no active connection
        self._is_connected = False
        # Set the instrument handle to None to release the reference to the closed instrument object
        self._instrument = None
        # Set the resource manager reference to None to release the reference to the closed resource manager
        self._resource_manager = None

    # Apply the @property decorator, which allows is_connected to be read like a variable (dmm.is_connected) rather than called as a function (dmm.is_connected())
    @property
    # Define a read-only property that exposes the private connection status flag to external code
    def is_connected(self) -> bool:
        """Check if multimeter is currently connected."""
        # Return the internal connection status flag; True means connected, False means not connected
        return self._is_connected

    # Apply the @property decorator so visa_address can be accessed like a variable rather than called as a function
    @property
    # Define a read-only property that exposes the instrument's VISA address string to external code
    def visa_address(self) -> str:
        """Get the VISA address for this instrument."""
        # Return the stored VISA address string that identifies this instrument on the communication bus
        return self._visa_address

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define the standalone demonstration function that shows how to use the KeithleyDMM6500 class with example measurements and output
def main() -> None:
    """Example usage demonstration."""
    # Configuration parameters
    # Store the VISA address of the multimeter to be used in this demonstration
    multimeter_address = "USB0::0x05E6::0x6500::04561287::INSTR"

    # Create multimeter instance
    # Create a new KeithleyDMM6500 control object using the stored VISA address
    dmm = KeithleyDMM6500(multimeter_address)

    # Begin a protected block for the demonstration; any multimeter errors will be caught at the end
    try:
        # Connect to instrument
        # Attempt to open a communication session with the physical multimeter
        if not dmm.connect():
            # If the connection fails, print a message and exit the function immediately
            print("Failed to connect to multimeter")
            return

        # Print a confirmation message to the console when the connection succeeds
        print("Connected to multimeter successfully")

        # Perform high-precision measurement
        # Request a high-precision DC voltage reading using a 10V range, 1-microvolt resolution, 1-NPLC integration, and auto-zero correction
        voltage = dmm.measure_dc_voltage(
            measurement_range=10.0,  # 10V range
            resolution=1e-6,         # 1µV resolution
            nplc=1.0,               # 1 power line cycle
            auto_zero=True          # Enable auto-zero correction
        )

        # Check whether the measurement returned a valid value before printing it
        if voltage is not None:
            # Print the measured voltage with 9 decimal places for maximum precision visibility
            print(f"High-precision DC voltage: {voltage:.9f} V")
        # If the measurement returned None, print a failure notice
        else:
            print("High-precision measurement failed")

        # Perform statistical analysis
        # Request a statistical summary of 10 repeated voltage measurements
        stats = dmm.perform_measurement_statistics(measurement_count=10)
        # Check whether the statistics were calculated successfully before printing them
        if stats:
            # Print the number of measurements included in the statistical summary
            print(f"Statistical analysis (n={stats['count']}):")
            # Print the mean (average) voltage value
            print(f"  Mean: {stats['mean']:.6f} V")
            # Print the standard deviation (spread) of the readings
            print(f"  Std Dev: {stats['standard_deviation']:.6f} V")
            # Print the coefficient of variation as a percentage (relative spread)
            print(f"  CV: {stats['coefficient_of_variation_percent']:.3f}%")

        # Display instrument information
        # Request the full instrument identification and status information
        info = dmm.get_instrument_info()
        # Check whether the information was retrieved successfully before printing it
        if info:
            # Print the manufacturer and model number of the connected instrument
            print(f"Instrument: {info['manufacturer']} {info['model']}")
            # Print the unique serial number of the connected instrument
            print(f"Serial: {info['serial_number']}")
            # Print the firmware version currently running on the instrument
            print(f"Firmware: {info['firmware_version']}")
            # Print any current error messages, or "None" if there are no errors
            print(f"Errors: {info['current_errors']}")

    # Catch any KeithleyDMM6500-specific errors that occurred during the demonstration
    except KeithleyDMM6500Error as e:
        # Print the multimeter-specific error message to the console
        print(f"Multimeter error: {e}")

    # Catch any other unexpected errors that were not specifically related to the multimeter
    except Exception as e:
        # Print the unexpected error message to the console
        print(f"Unexpected error: {e}")

    # This block always runs regardless of whether an error occurred, ensuring the connection is always closed
    finally:
        # Always disconnect to clean up resources
        # Call disconnect to safely close the communication session and free all resources
        dmm.disconnect()
        # Print a confirmation message that the instrument has been disconnected
        print("Disconnected from multimeter")

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Check whether this script is being run directly (not imported as a module); if so, call the main() demonstration function
if __name__ == "__main__":
    # Call the main demonstration function to execute the example measurement workflow
    main()
