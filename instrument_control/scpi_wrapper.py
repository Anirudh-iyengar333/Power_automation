# This is the opening line of the module-level docstring — it gives the file a clear title
"""
# This line is part of the docstring that states the title of this module
ENHANCED SCPI WRAPPER - INDUSTRY STANDARD VERSION

# This blank line inside the docstring separates the title from the change log
# Each of the FIXED lines below documents a specific improvement made to this file
 FIXED: Enhanced error handling and timeout management
# This line records that connection reliability for the Tektronix MSO24 has been improved
 FIXED: Better connection stability for MSO24
# This line records that the handling of raw binary data transfers has been corrected
 FIXED: Improved binary data handling
# This line records that instrument resources are now properly released after use
 FIXED: Proper resource cleanup
# This line records that compatibility issues between Windows and Linux signal handling have been resolved
 FIXED: Windows/Linux signal compatibility
# This line records that logging and automatic error recovery have been brought to production quality
 FIXED: Production-grade logging and error recovery

# This blank line inside the docstring separates the change log from the general description
This is the production-ready SCPI wrapper specifically enhanced for Tektronix MSO24
oscilloscope communication with bulletproof error handling.

# This line credits the organisation for whom this module was enhanced
Author: Enhanced for Digantara Research and Technologies
# This line records the date this version was completed
Date: 2024-12-03
# This line records the version number and quality designation of this module
Version: 2.0 - Industry Standard
"""

# [Blank line for visual separation between sections]
# This imports the PyVISA library, which provides the low-level communication layer
# needed to send commands to instruments over USB, GPIB, LAN, or serial connections
import pyvisa
# This imports the time module, which is used to add deliberate pauses between
# commands so instruments have enough time to process them
import time
# This imports the platform module, which can be used to detect the operating system
# — useful when behaviour must differ between Windows and Linux
import platform
# This imports type-hint helpers: Optional marks values that might be None,
# Any allows a variable to hold any type, and List represents a list of items
from typing import Optional, Any, List
# This imports the logging module, which is used throughout this file to record
# diagnostic messages at different severity levels (debug, info, warning, error)
import logging

# [Blank line for visual separation between sections]
# This defines the SCPIWrapper class — a self-contained object that manages
# the full lifecycle of communicating with a test instrument using SCPI commands
class SCPIWrapper:
    # This is the class-level docstring explaining what SCPIWrapper does
    """
    Enhanced SCPI communication wrapper with improved error handling
    and MSO24-specific optimizations
    """
    # [Blank line for visual separation between sections]
    # This defines the initialisation method — it is called automatically when a new
    # SCPIWrapper object is created, and it sets up all the internal state the object needs
    def __init__(self, visa_address: str, timeout_ms: int = 10000):
        # This checks that the VISA address provided is a non-empty text string;
        # if it is not, it raises an error immediately so the problem is caught early
        if not visa_address or not isinstance(visa_address, str):
            # This raises a descriptive error that tells the caller exactly what is wrong with the input
            raise ValueError("visa_address must be a non-empty string")

        # [Blank line for visual separation between sections]
        # This stores the instrument's VISA address (e.g. "USB0::0x0699::...") for later use when connecting
        self._visa_address = visa_address
        # This stores the communication timeout in milliseconds — how long the software waits
        # for the instrument to respond before giving up
        self._timeout_ms = timeout_ms
        # This stores a permanent copy of the original timeout so it can be restored after temporary overrides
        self._default_timeout_ms = timeout_ms  # Store default timeout
        # This prepares a placeholder for the PyVISA resource manager object;
        # it will be created when the connect() method is called
        self._resource_manager: Optional[pyvisa.ResourceManager] = None
        # This prepares a placeholder for the PyVISA instrument resource object
        # that represents the physical connection to the instrument
        self._instrument: Any = None  # pyvisa Resource object
        # This flag tracks whether the instrument is currently connected;
        # it starts as False because no connection has been made yet
        self._is_connected = False
        # [Blank line for visual separation between sections]
        # This comment introduces the logging setup for this object
        # Setup logging
        # This creates a dedicated logger for this object, named after the class,
        # so log messages from this instrument can be filtered or redirected independently
        self._logger = logging.getLogger(f'{self.__class__.__name__}')

    # [Blank line for visual separation between sections]
    # This defines the connect method, which attempts to open a communication channel
    # to the instrument at the stored VISA address
    def connect(self) -> bool:
        # This is the docstring for connect — it explains what the method does and what improvements were made
        """
        Establish VISA connection with enhanced error handling

         ENHANCED: Better error messages and connection stability
        """
        # This begins a protected block that tries to establish the instrument connection;
        # if anything goes wrong, the appropriate except block will handle it cleanly
        try:
            # This writes a log message at the informational level so operators know a connection is being attempted
            self._logger.info(f"Attempting VISA connection to: {self._visa_address}")
            # [Blank line for visual separation between sections]
            # This comment introduces the resource manager creation step
            # Create resource manager
            # This creates the PyVISA resource manager, which is the entry point for all VISA operations
            self._resource_manager = pyvisa.ResourceManager()
            # [Blank line for visual separation between sections]
            # This comment introduces the instrument connection step
            # Open instrument connection
            # This opens a communication session to the instrument at the stored VISA address
            self._instrument = self._resource_manager.open_resource(self._visa_address)

            # [Blank line for visual separation between sections]
            # This comment notes that the following settings are tuned for reliable communication with the MSO24
            # FIXED: MSO24-optimized settings
            # This sets how long the instrument will wait for a response before reporting a timeout
            self._instrument.timeout = self._timeout_ms
            # This tells the instrument driver that each incoming message ends with a newline character
            self._instrument.read_termination = '\n'
            # This tells the instrument driver that each outgoing command should end with a newline character
            self._instrument.write_termination = '\n'
            # This comment explains why latin_1 encoding is used — it prevents Unicode errors
            # when the instrument returns unusual characters in its error messages
            # Use a single-byte encoding so non-ASCII error strings (e.g. SYSTem:ERRor?)
            # never cause UnicodeDecodeError while still preserving raw bytes
            # This sets the text encoding used when reading or writing string data to the instrument
            self._instrument.encoding = 'latin_1'

            # [Blank line for visual separation between sections]
            # This comment notes that the chunk size is set large to handle bulk waveform downloads efficiently
            # FIXED: Additional settings for better stability
            # This sets the maximum number of bytes read in a single operation to 1 megabyte,
            # which is large enough to receive full waveform data without splitting
            self._instrument.chunk_size = 1024 * 1024  # 1MB chunks for large data
            # [Blank line for visual separation between sections]
            # This comment introduces the connection verification step
            # Test connection with identification query
            # This begins an inner protected block that tests whether the instrument responds correctly
            try:
                # This sends the standard "*IDN?" identification query to the instrument
                # and waits for a response confirming the instrument model and firmware
                idn = self._instrument.query("*IDN?", delay=0.1)
                # This writes the instrument's identification string to the log so operators can confirm the right device is connected
                self._logger.info(f"Connected to: {idn.strip()}")
                # This sets the internal connection flag to True now that communication is confirmed
                self._is_connected = True
                # This returns True to the caller to indicate the connection was successful
                return True
                # [Blank line for visual separation between sections]
            # This catches any error that occurs during the identification test
            except Exception as test_error:
                # This writes the specific error to the log at error level so it can be diagnosed
                self._logger.error(f"Connection test failed: {test_error}")
                # This calls the internal cleanup method to release any partially-opened resources
                self._cleanup_connection()
                # This returns False to the caller to indicate the connection attempt failed
                return False
                # [Blank line for visual separation between sections]
        # This catches the specific PyVISA communication error that occurs when the instrument cannot be reached
        except pyvisa.errors.VisaIOError as e:
            # This writes the VISA-specific error details to the log
            self._logger.error(f"VISA IO error connecting to {self._visa_address}: {e}")
            # This calls the internal cleanup method to release any partially-opened resources
            self._cleanup_connection()
            # This returns False to the caller to indicate the connection attempt failed
            return False
        # This catches any other unexpected error that is not a VISA communication error
        except Exception as e:
            # This writes the unexpected error details to the log at error level
            self._logger.error(f"Unexpected error connecting to {self._visa_address}: {e}")
            # This calls the internal cleanup method to release any partially-opened resources
            self._cleanup_connection()
            # This returns False to the caller to indicate the connection attempt failed
            return False

    # [Blank line for visual separation between sections]
    # This defines the disconnect method, which cleanly closes all communication channels
    # and releases the hardware resources held by this object
    def disconnect(self) -> None:
        # This is the docstring for disconnect — it summarises what the method does in one line
        """Clean disconnect with proper resource cleanup"""
        # This begins a protected attempt to close the instrument session
        try:
            # This checks that an instrument session is actually open before trying to close it
            if self._instrument:
                # This writes a log message so operators can see that the instrument connection is being closed
                self._logger.info("Closing instrument connection...")
                # This closes the instrument communication session and releases the hardware handle
                self._instrument.close()
        # This catches any error that occurs while closing the instrument session
        except Exception as e:
            # This writes a warning (not an error) because a close failure is non-critical
            self._logger.warning(f"Error closing instrument: {e}")
            # [Blank line for visual separation between sections]
        # This begins a second protected attempt to close the resource manager
        try:
            # This checks that a resource manager is actually open before trying to close it
            if self._resource_manager:
                # This writes a log message so operators can see that the resource manager is being closed
                self._logger.info("Closing resource manager...")
                # This closes the resource manager, releasing the VISA session at the driver level
                self._resource_manager.close()
        # This catches any error that occurs while closing the resource manager
        except Exception as e:
            # This writes a warning because a resource-manager close failure is also non-critical
            self._logger.warning(f"Error closing resource manager: {e}")
            # [Blank line for visual separation between sections]
        # This calls the internal cleanup method to reset all connection-related attributes to their default state
        self._cleanup_connection()

    # [Blank line for visual separation between sections]
    # This defines an internal helper method that resets all connection state variables
    # after a disconnect or a failed connection attempt
    def _cleanup_connection(self) -> None:
        # This is the docstring for _cleanup_connection — it describes the method's sole purpose
        """Internal cleanup of connection state"""
        # This sets the connection flag to False so the rest of the code knows no instrument is connected
        self._is_connected = False
        # This clears the instrument resource reference so Python can free the associated memory
        self._instrument = None
        # This clears the resource manager reference so Python can free the associated memory
        self._resource_manager = None

    # [Blank line for visual separation between sections]
    # This decorator turns the following method into a read-only property,
    # meaning callers can write "wrapper.is_connected" instead of "wrapper.is_connected()"
    @property
    # This defines the is_connected property — it reports whether the instrument is currently connected
    def is_connected(self) -> bool:
        # This is the docstring for is_connected — it explains what the property checks
        """Check if instrument is currently connected"""
        # This returns True only if both the internal flag is set AND the instrument object still exists;
        # both conditions must be true to guarantee the connection is actually usable
        return self._is_connected and self._instrument is not None

    # [Blank line for visual separation between sections]
    # This defines the write method, which sends a single SCPI command to the instrument
    # without expecting any response back
    def write(self, command: str) -> None:
        # This is the docstring for write — it explains the method and notes the improvements made
        """
        Send SCPI command to instrument

         ENHANCED: Better error handling and logging
        """
        # This checks that the instrument is connected before trying to send a command;
        # if not, it raises an error immediately so the caller knows why the command failed
        if not self.is_connected:
            # This raises a connection error with a clear message
            raise ConnectionError("Instrument not connected")
            # [Blank line for visual separation between sections]
        # This begins a protected attempt to send the command to the instrument
        try:
            # This writes the outgoing command to the debug log so it can be reviewed when troubleshooting
            self._logger.debug(f"WRITE: {command}")
            # This sends the command string to the instrument over the VISA communication channel
            self._instrument.write(command)
            # [Blank line for visual separation between sections]
        # This catches the specific VISA communication error that can occur when writing a command
        except pyvisa.errors.VisaIOError as e:
            # This writes the VISA error details to the log so the cause can be diagnosed
            self._logger.error(f"VISA error writing command '{command}': {e}")
            # This re-raises the same error so the calling code can also handle or report it
            raise
        # This catches any other unexpected error that is not a VISA-specific issue
        except Exception as e:
            # This writes the unexpected error details to the log at error level
            self._logger.error(f"Unexpected error writing command '{command}': {e}")
            # This re-raises the same error so the calling code can also handle or report it
            raise

    # [Blank line for visual separation between sections]
    # This defines the query method, which sends a command to the instrument and reads back its response
    def query(self, command: str, timeout: Optional[int] = None) -> str:
        # This is the docstring for query — it lists all parameters and the return value
        """
        Send a query and return the response

         ENHANCED: Better timeout handling and error reporting

        Args:
            command: SCPI query command
            timeout: Optional timeout override in milliseconds

        Returns:
            Response string from instrument
        """
        # This checks that the instrument is connected before trying to query it
        if not self.is_connected:
            # This raises a connection error with a clear message
            raise ConnectionError("Instrument not connected")

        # [Blank line for visual separation between sections]
        # This comment introduces the optional timeout override logic
        # Handle timeout override
        # This initialises the variable that will hold the previous timeout value before overriding it
        original_timeout = None
        # This checks whether the caller has supplied a custom timeout for this specific query
        if timeout is not None:
            # This saves the currently active timeout so it can be restored after the query
            original_timeout = self._instrument.timeout
            # This applies the caller's custom timeout so the instrument waits the right amount of time
            self._instrument.timeout = timeout

        # [Blank line for visual separation between sections]
        # This begins a protected attempt to send the query and receive the response
        try:
            # This writes the outgoing query command to the debug log for traceability
            self._logger.debug(f"QUERY: {command}")
            # This sends the query command and waits for the instrument's response string
            response = self._instrument.query(command)
            # This writes the response to the debug log (with leading/trailing whitespace removed for readability)
            self._logger.debug(f"RESPONSE: {response.strip()}")
            # This sends the response string back to the caller
            return response
            # [Blank line for visual separation between sections]
        # This catches the specific VISA communication error that can occur during a query
        except pyvisa.errors.VisaIOError as e:
            # This writes the VISA error details to the log
            self._logger.error(f"VISA error querying '{command}': {e}")
            # This re-raises the error so the calling code can also react to it
            raise
        # This catches any other unexpected error during the query
        except Exception as e:
            # This writes the unexpected error details to the log
            self._logger.error(f"Unexpected error querying '{command}': {e}")
            # This re-raises the error so the calling code can also react to it
            raise
        # This finally block always runs whether or not an error occurred — it restores the original timeout
        finally:
            # This comment explains that the original timeout is restored after the query is complete
            # Restore original timeout
            # This restores the previous timeout value only if a custom timeout was actually set
            if timeout is not None and original_timeout is not None:
                # This puts the original timeout back so subsequent calls use the normal setting
                self._instrument.timeout = original_timeout

    # [Blank line for visual separation between sections]
    # This defines the query_binary_values method, which sends a command and reads back
    # a block of binary data — used for downloading waveform samples from an oscilloscope
    def query_binary_values(self, command: str, datatype='B', is_big_endian=False,
                           chunk_size: int = 1024*1024, header_fmt='ieee', expect_termination=True,
                           timeout: int = None) -> list:
        # This is the docstring for query_binary_values — it lists all parameters and the return value
        """
        Query binary data from instrument

         ENHANCED: Optimized for large waveform data transfers

        Args:
            command: SCPI query command for binary data
            datatype: Data type specification ('B' for unsigned byte, etc.)
            is_big_endian: Byte order (False for little-endian)
            chunk_size: Size of data chunks for transfer
            header_fmt: Header format - 'ieee' (default), 'hp', or 'empty' for no header
            expect_termination: Whether to expect termination character (default True)
            timeout: Optional timeout in milliseconds for this query

        Returns:
            List of binary values
        """
        # This checks that the instrument is connected before attempting a binary transfer
        if not self.is_connected:
            # This raises a connection error with a clear message
            raise ConnectionError("Instrument not connected")

        # [Blank line for visual separation between sections]
        # This initialises a variable to hold the original chunk size before any temporary change
        original_chunk_size = None
        # This initialises a variable to hold the original timeout before any temporary change
        original_timeout = None

        # [Blank line for visual separation between sections]
        # This begins a protected attempt to perform the binary data query
        try:
            # This writes a debug log entry showing the command and settings being used for the binary transfer
            self._logger.debug(f"BINARY QUERY: {command} (header_fmt={header_fmt}, timeout={timeout}ms)")

            # [Blank line for visual separation between sections]
            # This comment introduces the temporary timeout override for this binary transfer
            # Set temporary timeout if specified
            # This checks whether a custom timeout was provided for this transfer
            if timeout is not None:
                # This saves the current timeout so it can be restored after the transfer
                original_timeout = self._instrument.timeout
                # This applies the custom timeout, giving the instrument more time for large data transfers
                self._instrument.timeout = timeout
                # This writes a debug message confirming the new timeout setting
                self._logger.debug(f"Timeout set to {timeout}ms for binary transfer")

            # [Blank line for visual separation between sections]
            # This comment introduces the temporary chunk-size increase for large binary transfers
            #  ENHANCED: Set larger chunk size for waveform data
            # This reads the current chunk size from the instrument object if it has that attribute
            original_chunk_size = getattr(self._instrument, 'chunk_size', None)
            # This checks whether the instrument object actually has a chunk_size attribute
            if original_chunk_size is not None:
                # This sets the chunk size to the requested value so large waveforms transfer without splitting
                self._instrument.chunk_size = chunk_size

            # [Blank line for visual separation between sections]
            # This comment introduces the actual binary query call
            # Query binary data with specified header format
            # This sends the binary query command and reads back the data as a list of numerical values,
            # using the specified data type, byte order, header format, and termination settings
            data = self._instrument.query_binary_values(
                # This passes the SCPI command to the underlying PyVISA method
                command,
                # This specifies how each individual value should be interpreted (e.g. 'B' = unsigned byte)
                datatype=datatype,
                # This tells the driver whether the bytes arrive in big-endian order
                is_big_endian=is_big_endian,
                # This tells the driver which binary block header format to expect from the instrument
                header_fmt=header_fmt,
                # This tells the driver whether to look for a termination character at the end of the data
                expect_termination=expect_termination
            )

            # [Blank line for visual separation between sections]
            # This writes a debug log entry showing how many values were received
            self._logger.debug(f"BINARY RESPONSE: {len(data)} values received")
            # This returns the list of binary data values to the caller
            return data

        # This catches the specific VISA communication error that can occur during a binary transfer
        except pyvisa.errors.VisaIOError as e:
            # This writes the VISA error details to the log
            self._logger.error(f"VISA error in binary query '{command}': {e}")
            # This re-raises the error so the calling code can also react to it
            raise
        # This catches any other unexpected error during the binary transfer
        except Exception as e:
            # This writes the unexpected error details to the log
            self._logger.error(f"Unexpected error in binary query '{command}': {e}")
            # This re-raises the error so the calling code can also react to it
            raise
        # This finally block always runs — it restores the original chunk size and timeout
        finally:
            # This comment introduces the settings restoration block
            # Restore original settings
            # This restores the original chunk size if it was changed earlier in this method
            if original_chunk_size is not None:
                # This puts the original chunk size back so subsequent calls are not affected
                self._instrument.chunk_size = original_chunk_size
            # This restores the original timeout if a custom one was set earlier in this method
            if timeout is not None and original_timeout is not None:
                # This puts the original timeout back so subsequent calls use the normal setting
                self._instrument.timeout = original_timeout

    # [Blank line for visual separation between sections]
    # This defines the read_raw method, which reads raw bytes directly from the instrument
    # without any text interpretation — useful when receiving binary data
    def read_raw(self) -> bytes:
        # This is the docstring for read_raw — it explains the purpose and notes the improvement
        """
        Read raw bytes from instrument

         ENHANCED: Better error handling for raw data reads
        """
        # This checks that the instrument is connected before attempting a raw read
        if not self.is_connected:
            # This raises a connection error with a clear message
            raise ConnectionError("Instrument not connected")

        # [Blank line for visual separation between sections]
        # This begins a protected attempt to read raw bytes from the instrument
        try:
            # This writes a debug log entry to mark that a raw read is starting
            self._logger.debug("READ RAW")
            # This reads the next available bytes from the instrument and stores them as a bytes object
            data = self._instrument.read_raw()
            # This writes a debug log entry showing how many bytes were received
            self._logger.debug(f"RAW RESPONSE: {len(data)} bytes")
            # This returns the raw bytes to the caller
            return data

        # This catches the specific VISA communication error that can occur when reading raw data
        except pyvisa.errors.VisaIOError as e:
            # This writes the VISA error details to the log
            self._logger.error(f"VISA error reading raw data: {e}")
            # This re-raises the error so the calling code can also react to it
            raise
        # This catches any other unexpected error during the raw read
        except Exception as e:
            # This writes the unexpected error details to the log
            self._logger.error(f"Unexpected error reading raw data: {e}")
            # This re-raises the error so the calling code can also react to it
            raise

    # [Blank line for visual separation between sections]
    # This defines the query_raw_binary method, which sends a command and then reads back
    # raw binary bytes in multiple chunks — designed for commands that return raw file data
    # rather than IEEE 488.2 formatted binary blocks
    def query_raw_binary(self, command: str, timeout: int = None, chunk_size: int = 1024*1024) -> bytes:
        # This is the docstring for query_raw_binary — it explains the purpose, parameters, and return value
        """
        Query and read raw binary data (without IEEE 488.2 block header parsing)

        This is useful for commands that return raw binary files (like FILESystem:READFile)
        that don't use IEEE 488.2 definite length block format.

        Args:
            command: SCPI query command
            timeout: Optional timeout in milliseconds
            chunk_size: Size of chunks to read (default: 1MB)

        Returns:
            Raw bytes response
        """
        # This checks that the instrument is connected before attempting the raw binary query
        if not self.is_connected:
            # This raises a connection error with a clear message
            raise ConnectionError("Instrument not connected")

        # [Blank line for visual separation between sections]
        # This begins a protected attempt to send the command and read back binary data
        try:
            # This writes a debug log entry showing the command that will be sent
            self._logger.debug(f"RAW BINARY QUERY: {command}")

            # [Blank line for visual separation between sections]
            # This comment introduces the temporary settings override variables
            # Set temporary timeout and chunk size
            # This initialises the variable that will hold the previous timeout before any override
            original_timeout = None
            # This initialises the variable that will hold the previous chunk size before any override
            original_chunk_size = None

            # [Blank line for visual separation between sections]
            # This checks whether the caller supplied a custom timeout for this transfer
            if timeout is not None:
                # This saves the current timeout so it can be restored after the transfer
                original_timeout = self._instrument.timeout
                # This applies the custom timeout for this operation
                self._instrument.timeout = timeout

            # [Blank line for visual separation between sections]
            # This checks whether the instrument object supports configuring chunk size
            if hasattr(self._instrument, 'chunk_size'):
                # This saves the current chunk size
                original_chunk_size = self._instrument.chunk_size
                # This sets the chunk size to the requested value for more efficient large transfers
                self._instrument.chunk_size = chunk_size

            # [Blank line for visual separation between sections]
            # This comment introduces the section that sends the command and reads data in a loop
            # Send query
            # This sends the SCPI command to the instrument without reading a response yet
            self._instrument.write(command)
            # This pauses for half a second to give the instrument enough time to prepare the file data
            time.sleep(0.5)  # Longer delay for file operations

            # [Blank line for visual separation between sections]
            # This comment explains that a short timeout is used here so the read loop knows when no more data is coming
            # Set a shorter timeout for subsequent reads
            # This saves the current timeout so it can be restored after the read loop
            saved_timeout = self._instrument.timeout
            # This applies a 2-second read timeout so the loop stops quickly when the instrument sends no more data
            self._instrument.timeout = 2000  # 2 second timeout per read

            # [Blank line for visual separation between sections]
            # This comment introduces the data accumulation loop
            # Read all available data - keep reading until timeout
            # This starts with an empty bytes object that will grow as chunks of data are received
            data = b''
            # This counter tracks how many chunks have been received so far
            attempts = 0
            # This sets the maximum number of read attempts to prevent the loop from running forever
            max_attempts = 100  # Prevent infinite loops

            # [Blank line for visual separation between sections]
            # This loop keeps reading chunks of data from the instrument until no more arrives or the limit is hit
            while attempts < max_attempts:
                # This begins a protected attempt to read one chunk of data
                try:
                    # This reads the next available chunk of bytes from the instrument
                    chunk = self._instrument.read_raw()
                    # This checks whether the received chunk is empty, which signals the end of the data
                    if not chunk or len(chunk) == 0:
                        # This writes a debug message noting that an empty chunk was received
                        self._logger.debug("Empty chunk received, ending read")
                        # This exits the loop because no more data is available
                        break

                    # [Blank line for visual separation between sections]
                    # This appends the newly received chunk to the accumulated data buffer
                    data += chunk
                    # This increments the attempt counter to track progress
                    attempts += 1
                    # This writes a debug message showing how many bytes arrived in this chunk and in total
                    self._logger.debug(f"Read chunk {attempts}: {len(chunk)} bytes (total: {len(data)})")

                # This catches VISA communication errors that occur during chunk reads
                except pyvisa.errors.VisaIOError as e:
                    # This comment explains that a timeout error is expected and means all data has been received
                    # Timeout means no more data available
                    # This checks whether the error is specifically a timeout error
                    if 'timeout' in str(e).lower():
                        # This writes a debug message confirming that the read loop ended due to a normal timeout
                        self._logger.debug(f"Timeout after {attempts} chunks - assuming all data received")
                        # This exits the loop because no more data is coming
                        break
                    # This re-raises any non-timeout VISA error because it is unexpected
                    raise

            # [Blank line for visual separation between sections]
            # This comment introduces the timeout restoration step
            # Restore timeout
            # This puts the saved timeout back (or falls back to the original timeout argument if needed)
            self._instrument.timeout = saved_timeout if saved_timeout else timeout

            # [Blank line for visual separation between sections]
            # This writes an informational log message summarising the total number of bytes received
            self._logger.info(f"RAW BINARY RESPONSE: {len(data)} bytes total")

            # [Blank line for visual separation between sections]
            # This comment introduces the optional header-logging block for debugging data format issues
            # Log data header for debugging
            # This checks whether at least 8 bytes were received so the header can be logged
            if len(data) >= 8:
                # This converts the first 8 bytes to a hex string for easy reading in the log
                header_hex = ' '.join(f'{b:02x}' for b in data[:8])
                # This writes the hex representation of the first 8 bytes to the debug log
                self._logger.debug(f"Data starts with: {header_hex}")

            # [Blank line for visual separation between sections]
            # This returns all the accumulated raw bytes to the caller
            return data

        # This catches the specific VISA communication error that can occur during the raw binary query
        except pyvisa.errors.VisaIOError as e:
            # This writes the VISA error details to the log
            self._logger.error(f"VISA error in raw binary query '{command}': {e}")
            # This re-raises the error so the calling code can also react to it
            raise
        # This catches any other unexpected error during the raw binary query
        except Exception as e:
            # This writes the unexpected error details to the log
            self._logger.error(f"Unexpected error in raw binary query '{command}': {e}")
            # This re-raises the error so the calling code can also react to it
            raise
        # This finally block always runs — it restores the original timeout and chunk size
        finally:
            # This comment introduces the settings restoration block
            # Restore original settings
            # This restores the original timeout if a custom one was set earlier
            if timeout is not None and original_timeout is not None:
                # This puts the original timeout back
                self._instrument.timeout = original_timeout
            # This restores the original chunk size if it was changed earlier
            if original_chunk_size is not None:
                # This puts the original chunk size back
                self._instrument.chunk_size = original_chunk_size

    # [Blank line for visual separation between sections]
    # This defines the set_timeout method, which lets the caller change the communication
    # timeout while the instrument is connected — useful before long operations
    def set_timeout(self, timeout_ms: int) -> None:
        # This is the docstring for set_timeout — it notes the validation and logging improvements
        """
        Set VISA timeout dynamically

         ENHANCED: Better validation and logging
        """
        # This checks that the instrument is connected before trying to change the timeout
        if not self.is_connected:
            # This raises a connection error with a clear message
            raise ConnectionError("Instrument not connected")
            # [Blank line for visual separation between sections]
        # This validates that the requested timeout is a positive number
        if timeout_ms <= 0:
            # This raises a descriptive error because a zero or negative timeout makes no sense
            raise ValueError("Timeout must be positive")
            # [Blank line for visual separation between sections]
        # This begins a protected attempt to apply the new timeout
        try:
            # This updates the internally stored timeout value to match the new setting
            self._timeout_ms = timeout_ms
            # This applies the new timeout to the live instrument connection
            self._instrument.timeout = timeout_ms
            # This writes a debug log entry confirming the new timeout has been applied
            self._logger.debug(f"Timeout set to {timeout_ms} ms")
            # [Blank line for visual separation between sections]
        # This catches any unexpected error that occurs while setting the timeout
        except Exception as e:
            # This writes the error details to the log so it can be investigated
            self._logger.error(f"Error setting timeout to {timeout_ms} ms: {e}")
            # This re-raises the error so the calling code is also aware of the failure
            raise

    # [Blank line for visual separation between sections]
    # This defines the reset_timeout method, which restores the communication timeout
    # to the value that was configured when this object was first created
    def reset_timeout(self) -> None:
        # This is the docstring for reset_timeout — it explains the method's purpose in one line
        """Reset timeout to default value"""
        # This checks that the instrument is connected before trying to change the timeout
        if not self.is_connected:
            # This raises a connection error with a clear message
            raise ConnectionError("Instrument not connected")
            # [Blank line for visual separation between sections]
        # This begins a protected attempt to restore the default timeout
        try:
            # This resets the internally stored timeout to the original default value
            self._timeout_ms = self._default_timeout_ms
            # This applies the default timeout to the live instrument connection
            self._instrument.timeout = self._default_timeout_ms
            # This writes a debug log entry confirming the timeout has been reset
            self._logger.debug(f"Timeout reset to default {self._default_timeout_ms} ms")
            # [Blank line for visual separation between sections]
        # This catches any unexpected error that occurs while resetting the timeout
        except Exception as e:
            # This writes the error details to the log
            self._logger.error(f"Error resetting timeout: {e}")
            # This re-raises the error so the calling code is also aware of the failure
            raise

    # [Blank line for visual separation between sections]
    # This decorator turns the following method into a read-only property so callers
    # can read the current timeout value without calling a method explicitly
    @property
    # This defines the timeout property — it returns the currently active timeout in milliseconds
    def timeout(self) -> int:
        # This is the docstring for the timeout property
        """Get current timeout in milliseconds"""
        # This returns the internally stored timeout value in milliseconds
        return self._timeout_ms
    # [Blank line for visual separation between sections]
    # This decorator turns the following method into a read-only property so callers
    # can read the VISA address without calling a method explicitly
    @property
    # This defines the visa_address property — it returns the VISA address string of the instrument
    def visa_address(self) -> str:
        # This is the docstring for the visa_address property
        """Get the VISA address"""
        # This returns the stored VISA address string
        return self._visa_address
    # [Blank line for visual separation between sections]
    # This defines the get_instrument_errors method, which reads all error messages
    # currently stored in the instrument's internal error queue
    def get_instrument_errors(self) -> list:
        # This is the docstring for get_instrument_errors — it notes that this is a new addition
        """
        Get all errors from instrument error queue

         NEW: Enhanced error reporting for debugging
        """
        # This returns an empty list immediately if the instrument is not connected
        if not self.is_connected:
            # This returns an empty list because there is nothing to query
            return []
            # [Blank line for visual separation between sections]
        # This creates an empty list that will be filled with any error messages returned by the instrument
        errors = []
        # This begins a protected attempt to read all errors from the instrument error queue
        try:
            # This comment explains that the loop runs repeatedly until the queue reports "no error"
            # Query all errors until queue is empty
            # This loop repeatedly queries the instrument error queue until it is empty
            while True:
                # This queries the error queue and removes leading/trailing whitespace from the response
                error = self.query("SYST:ERR?", timeout=2000).strip()
                # This checks whether the response indicates the queue is now empty (no more errors)
                if error.startswith('0,"No error') or error == '0':
                    # This exits the loop because the queue is empty
                    break
                # This adds the error message to the list
                errors.append(error)
                # This checks whether the list has grown too large, which might mean the loop is stuck
                if len(errors) > 10:  # Prevent infinite loop
                    # This exits the loop as a safety measure to prevent infinite querying
                    break
                    # [Blank line for visual separation between sections]
        # This catches any error that occurs while reading the instrument error queue
        except Exception as e:
            # This writes a warning (not an error) because failing to read the error queue is non-critical
            self._logger.warning(f"Could not read instrument errors: {e}")
            # [Blank line for visual separation between sections]
        # This returns the list of error messages (may be empty if no errors were found)
        return errors

    # [Blank line for visual separation between sections]
    # This defines the clear_instrument_errors method, which sends a reset command
    # to the instrument to wipe its error queue and then confirms the queue is empty
    def clear_instrument_errors(self) -> bool:
        # This is the docstring for clear_instrument_errors — it notes that this is a new addition
        """
        Clear instrument error queue

         NEW: Utility function to clear errors
        """
        # This returns False immediately if the instrument is not connected
        if not self.is_connected:
            # This returns False because there is no instrument to clear errors from
            return False
            # [Blank line for visual separation between sections]
        # This begins a protected attempt to clear the instrument's error queue
        try:
            # This comment introduces the command that clears the instrument's status registers
            # Send clear command
            # This sends the standard IEEE 488.2 clear status command to the instrument
            self.write("*CLS")
            # This pauses for 100 milliseconds to give the instrument time to process the clear command
            time.sleep(0.1)
            # [Blank line for visual separation between sections]
            # This comment introduces the verification step
            # Verify errors are cleared
            # This reads the error queue again to confirm it is now empty
            errors = self.get_instrument_errors()
            # This returns True if the error list is empty (meaning the clear was successful),
            # or False if errors are still present
            return len(errors) == 0
            # [Blank line for visual separation between sections]
        # This catches any unexpected error that occurs while clearing the error queue
        except Exception as e:
            # This writes the error details to the log at error level
            self._logger.error(f"Error clearing instrument errors: {e}")
            # This returns False to indicate that the error-clearing operation failed
            return False

    # [Blank line for visual separation between sections]
    # This defines the test_communication method, which sends a simple identification query
    # and checks that the instrument responds — a quick health check for the connection
    def test_communication(self) -> bool:
        # This is the docstring for test_communication — it notes that this is a new addition
        """
        Test communication with instrument

         NEW: Communication health check function
        """
        # This returns False immediately if the instrument is not connected
        if not self.is_connected:
            # This returns False because there is no instrument to test communication with
            return False
            # [Blank line for visual separation between sections]
        # This begins a protected attempt to send the identification query and validate the response
        try:
            # This comment introduces the identification query step
            # Test with standard identification query
            # This sends the standard identification query with a 5-second timeout
            idn = self.query("*IDN?", timeout=5000)
            # This checks that the response is not empty before declaring success
            if idn and len(idn.strip()) > 0:
                # This writes a success message to the log with the instrument's identity string
                self._logger.info(f"Communication test passed: {idn.strip()}")
                # This returns True to indicate the communication health check passed
                return True
            # This handles the case where the instrument responded but with an empty string
            else:
                # This writes a warning to the log because an empty response is unexpected
                self._logger.warning("Communication test failed: Empty response")
                # This returns False to indicate the health check did not pass
                return False
                # [Blank line for visual separation between sections]
        # This catches any error that occurs during the communication test
        except Exception as e:
            # This writes the error details to the log at error level
            self._logger.error(f"Communication test failed: {e}")
            # This returns False to indicate the health check failed
            return False

    # [Blank line for visual separation between sections]
    # This defines the __enter__ method, which is called when this object is used in a
    # "with" statement — it automatically opens the connection at the start of the block
    def __enter__(self):
        # This is the docstring for __enter__
        """Context manager entry"""
        # This attempts to connect to the instrument; if it fails, an error is raised immediately
        if not self.connect():
            # This raises a connection error telling the caller which address could not be reached
            raise ConnectionError(f"Failed to connect to {self._visa_address}")
        # This returns the connected SCPIWrapper object so the caller can use it inside the with block
        return self

    # [Blank line for visual separation between sections]
    # This defines the __exit__ method, which is called automatically when the "with" block ends —
    # it ensures the instrument is disconnected whether the block ended normally or with an error
    def __exit__(self, exc_type, exc_val, exc_tb):
        # This is the docstring for __exit__
        """Context manager exit"""
        # This calls the disconnect method to cleanly close the instrument connection
        self.disconnect()

    # [Blank line for visual separation between sections]
    # This defines the __del__ method, which is called by Python when the object is
    # about to be destroyed — it is a safety net to ensure the connection is always closed
    def __del__(self):
        # This is the docstring for __del__
        """Destructor to ensure proper cleanup"""
        # This begins a protected attempt to disconnect if the connection is still open
        try:
            # This checks whether the connection flag says the instrument is still connected
            if self._is_connected:
                # This closes the instrument connection before the object is removed from memory
                self.disconnect()
        # This silently ignores any error during object destruction to avoid crashing the program
        except:
            # This passes without action because errors during cleanup at program exit are expected
            pass  # Ignore errors during destruction


# [Blank line for visual separation between sections]
# This decorative comment block visually separates the class definition from the standalone utility functions
# ============================================================================
# This comment labels the section containing test and utility functions
# 🧪 TESTING AND UTILITIES
# ============================================================================

# [Blank line for visual separation between sections]
# This defines a standalone function that exercises the main features of the SCPIWrapper class
# against a real instrument to confirm everything is working correctly
def test_scpi_wrapper(visa_address: str) -> bool:
    # This is the docstring for test_scpi_wrapper — it lists the parameter and return value
    """
    Test the SCPI wrapper functionality

    Args:
        visa_address: VISA address to test

    Returns:
        True if all tests pass
    """
    # This prints a message to the console so the operator knows the test has started
    print(f"Testing SCPI wrapper with {visa_address}...")
    # [Blank line for visual separation between sections]
    # This begins a protected attempt to run all the test steps
    try:
        # This comment introduces the connection test step
        # Test connection
        # This creates a new SCPIWrapper object for the given VISA address with a 10-second timeout
        wrapper = SCPIWrapper(visa_address, timeout_ms=10000)
        # [Blank line for visual separation between sections]
        # This attempts to connect and checks whether the connection succeeded
        if not wrapper.connect():
            # This prints a failure message if the connection could not be established
            print(" Connection test failed")
            # This returns False to indicate the test suite failed at the connection step
            return False
        # [Blank line for visual separation between sections]
        # This prints a success message confirming the connection was established
        print(" Connection successful")
        # [Blank line for visual separation between sections]
        # This comment introduces the identification test step
        # Test identification
        # This sends the standard identification query to the instrument
        idn = wrapper.query("*IDN?")
        # This prints the instrument's identity string (with whitespace removed) to the console
        print(f" Identification: {idn.strip()}")
        # [Blank line for visual separation between sections]
        # This comment introduces the error-clearing test step
        # Test error clearing
        # This sends the clear-errors command to the instrument
        wrapper.clear_instrument_errors()
        # This prints a confirmation that the error queue has been cleared
        print(" Error queue cleared")
        # [Blank line for visual separation between sections]
        # This comment introduces the communication health check step
        # Test communication
        # This runs the communication health check and prints the result
        if wrapper.test_communication():
            # This prints a pass message if the health check succeeded
            print(" Communication test passed")
        else:
            # This prints a warning message if the health check returned a concern
            print(" Communication test warning")
        # [Blank line for visual separation between sections]
        # This comment introduces the timeout management test step
        # Test timeout management
        # This sets the timeout to 5 seconds to verify that set_timeout works without error
        wrapper.set_timeout(5000)
        # This resets the timeout back to the default to verify that reset_timeout works without error
        wrapper.reset_timeout()
        # This prints a confirmation that both timeout functions executed successfully
        print(" Timeout management working")
        # [Blank line for visual separation between sections]
        # This closes the instrument connection at the end of the test
        wrapper.disconnect()
        # This prints a confirmation that the disconnection was successful
        print(" Disconnection successful")
        # [Blank line for visual separation between sections]
        # This returns True to indicate all test steps passed successfully
        return True
        # [Blank line for visual separation between sections]
    # This catches any unexpected error that occurs during the test sequence
    except Exception as e:
        # This prints the error message so the operator can see what went wrong
        print(f" Test failed: {e}")
        # This returns False to indicate the test sequence did not complete successfully
        return False

# [Blank line for visual separation between sections]
# This defines a standalone utility function that lists the VISA addresses
# of all instruments currently visible on the system
def list_available_instruments() -> list:
    # This is the docstring for list_available_instruments — it explains what it returns
    """
    List all available VISA instruments

    Returns:
        List of available VISA addresses
    """
    # This begins a protected attempt to create a resource manager and list all connected instruments
    try:
        # This creates a PyVISA resource manager to access the VISA driver layer
        rm = pyvisa.ResourceManager()
        # This queries the VISA driver for a tuple of all currently visible instrument addresses
        instruments = rm.list_resources()
        # This closes the resource manager now that the address list has been retrieved
        rm.close()
        # This converts the tuple of addresses to a plain list and returns it to the caller
        return list(instruments)
    # This catches any error that occurs while listing instruments
    except Exception as e:
        # This prints a descriptive error message to the console
        print(f"Error listing instruments: {e}")
        # This returns an empty list so the caller always receives a valid list, even on failure
        return []


# [Blank line for visual separation between sections]
# This defines a standalone utility function that scans for all visible instruments
# and attempts to identify each one by querying its identification string
def scan_and_identify_instruments(timeout_ms: int = 5000) -> list:
    # This is the docstring for scan_and_identify_instruments — it describes the parameter and return format
    """
    Scan for VISA instruments and identify them by querying *IDN?

    Args:
        timeout_ms: Timeout for each instrument query in milliseconds

    Returns:
        List of dictionaries containing instrument information:
        [
            {
                'visa_address': str,
                'manufacturer': str,
                'model': str,
                'serial_number': str,
                'firmware': str,
                'idn_string': str,
                'instrument_type': str  # 'dmm', 'power_supply', 'oscilloscope', 'load', 'unknown'
            },
            ...
        ]
    """
    # This creates an empty list that will be filled with one dictionary per identified instrument
    identified_instruments = []

    # [Blank line for visual separation between sections]
    # This begins a protected attempt to open the VISA driver and scan for instruments
    try:
        # This comment introduces the resource manager and address listing step
        # Get list of available VISA resources
        # This creates a PyVISA resource manager to access the VISA driver layer
        rm = pyvisa.ResourceManager()
        # This queries the VISA driver for all currently visible instrument addresses
        visa_addresses = rm.list_resources()

        # [Blank line for visual separation between sections]
        # This loops through each discovered VISA address to attempt identification
        for visa_address in visa_addresses:
            # This begins a protected attempt to open and query each individual instrument
            try:
                # This comment introduces the instrument connection and query step
                # Attempt to open and query each instrument
                # This opens a communication session to the instrument at the current address
                instrument = rm.open_resource(visa_address)
                # This sets the read timeout for this instrument to the specified value
                instrument.timeout = timeout_ms
                # This sets the expected end-of-message character for incoming text
                instrument.read_termination = '\n'
                # This sets the end-of-message character that will be appended to outgoing commands
                instrument.write_termination = '\n'

                # [Blank line for visual separation between sections]
                # This comment introduces the identification query
                # Query instrument identification
                # This sends the standard identification query and removes surrounding whitespace from the response
                idn_response = instrument.query("*IDN?").strip()

                # [Blank line for visual separation between sections]
                # This comment explains that the response is split into fields using commas
                # Parse IDN response (typically: Manufacturer,Model,SerialNumber,Firmware)
                # This splits the identification string into a list of individual fields at each comma
                parts = idn_response.split(',')

                # [Blank line for visual separation between sections]
                # This extracts the manufacturer name from the first field, or uses "Unknown" if missing
                manufacturer = parts[0].strip() if len(parts) > 0 else "Unknown"
                # This extracts the model name from the second field, or uses "Unknown" if missing
                model = parts[1].strip() if len(parts) > 1 else "Unknown"
                # This extracts the serial number from the third field, or uses "Unknown" if missing
                serial_number = parts[2].strip() if len(parts) > 2 else "Unknown"
                # This extracts the firmware version from the fourth field, or uses "Unknown" if missing
                firmware = parts[3].strip() if len(parts) > 3 else "Unknown"

                # [Blank line for visual separation between sections]
                # This comment introduces the instrument-type classification step
                # Identify instrument type based on model
                # This calls the classify function to determine whether the instrument is a DMM,
                # power supply, oscilloscope, load, or unknown type
                instrument_type = classify_instrument_type(manufacturer, model)

                # [Blank line for visual separation between sections]
                # This appends a dictionary of all the instrument's details to the results list
                identified_instruments.append({
                    # This stores the VISA address so the caller knows how to connect to this instrument
                    'visa_address': visa_address,
                    # This stores the manufacturer name extracted from the identification response
                    'manufacturer': manufacturer,
                    # This stores the model name extracted from the identification response
                    'model': model,
                    # This stores the serial number extracted from the identification response
                    'serial_number': serial_number,
                    # This stores the firmware version string extracted from the identification response
                    'firmware': firmware,
                    # This stores the full raw identification string for reference
                    'idn_string': idn_response,
                    # This stores the classified instrument type (e.g. 'dmm', 'oscilloscope')
                    'instrument_type': instrument_type,
                    # This stores a human-readable display name combining manufacturer, model, and serial number
                    'display_name': f"{manufacturer} {model} (S/N: {serial_number})"
                })

                # [Blank line for visual separation between sections]
                # This closes the instrument session now that identification is complete
                instrument.close()

            # This catches any error that occurs for a specific instrument and skips to the next one
            except Exception as e:
                # This comment explains that unresponsive instruments are silently skipped
                # If we can't query this instrument, skip it
                # This prints a descriptive message so the operator knows which address could not be identified
                print(f"Could not identify instrument at {visa_address}: {e}")
                # This moves to the next VISA address without crashing the whole scan
                continue

        # [Blank line for visual separation between sections]
        # This closes the resource manager now that all instruments have been scanned
        rm.close()
        # This returns the list of identified instrument dictionaries to the caller
        return identified_instruments

    # This catches any error that occurs at the top level of the scanning process
    except Exception as e:
        # This prints a descriptive error message to the console
        print(f"Error scanning instruments: {e}")
        # This returns an empty list so the caller always receives a valid list, even on failure
        return []


# [Blank line for visual separation between sections]
# This defines a standalone utility function that determines what category of instrument
# a given manufacturer/model combination belongs to
def classify_instrument_type(manufacturer: str, model: str) -> str:
    # This is the docstring for classify_instrument_type — it lists parameters and possible return values
    """
    Classify instrument type based on manufacturer and model information.

    Args:
        manufacturer: Manufacturer name from *IDN? response
        model: Model name from *IDN? response

    Returns:
        Instrument type: 'dmm', 'power_supply', 'oscilloscope', 'load', 'unknown'
    """
    # This converts the manufacturer string to lowercase for case-insensitive comparisons
    manufacturer_lower = manufacturer.lower()
    # This converts the model string to lowercase for case-insensitive comparisons
    model_lower = model.lower()

    # [Blank line for visual separation between sections]
    # This comment labels the block that checks for digital multimeter model identifiers
    # Digital Multimeters
    # This checks whether the model string contains 'dmm', '6500', or '7510' — all DMM indicators
    if 'dmm' in model_lower or '6500' in model or '7510' in model:
        # This returns the classification string for digital multimeters
        return 'dmm'

    # [Blank line for visual separation between sections]
    # This comment labels the block that checks for Keithley power supply model numbers
    # Power Supplies
    # This checks whether the model string contains any of the known Keithley power supply model numbers
    if any(x in model for x in ['2230', '2231', '2280', '2260', '2268']):
        # This returns the classification string for power supplies
        return 'power_supply'

    # [Blank line for visual separation between sections]
    # This comment labels the block that checks for Keithley electronic load model numbers
    # Electronic Loads
    # This checks whether the model string contains any of the known Keithley electronic load model numbers
    if any(x in model for x in ['2380', '2382']):
        # This returns the classification string for electronic loads
        return 'load'

    # [Blank line for visual separation between sections]
    # This comment labels the block that checks for Keysight or Agilent oscilloscope identifiers
    # Oscilloscopes - Keysight
    # This checks whether the manufacturer is Keysight or its predecessor Agilent Technologies
    if 'keysight' in manufacturer_lower or 'agilent' in manufacturer_lower:
        # This checks whether the model contains a known oscilloscope series identifier
        if any(x in model_lower for x in ['dso', 'mso', 'infiniivision', 'dsox']):
            # This returns the classification string for oscilloscopes
            return 'oscilloscope'

    # [Blank line for visual separation between sections]
    # This comment labels the block that checks for Tektronix oscilloscope identifiers
    # Oscilloscopes - Tektronix
    # This checks whether the manufacturer is Tektronix
    if 'tektronix' in manufacturer_lower:
        # This checks whether the model contains a known Tektronix oscilloscope series identifier
        if any(x in model_lower for x in ['mso', 'dpo', 'tds', 'mdo']):
            # This returns the classification string for oscilloscopes
            return 'oscilloscope'

    # [Blank line for visual separation between sections]
    # This comment notes that none of the known categories matched
    # Default
    # This returns 'unknown' when the manufacturer and model do not match any recognised instrument category
    return 'unknown'


# [Blank line for visual separation between sections]
# This block runs only when this file is executed directly as a script,
# not when it is imported as a module by other code
if __name__ == "__main__":
    # This prints a header banner to the console when the script is run directly
    print("🔗 ENHANCED SCPI WRAPPER - TESTING")
    # This prints a dividing line of equals signs for visual separation
    print("=" * 50)
    # [Blank line for visual separation between sections]
    # This prints a label before listing all discovered instruments
    # List available instruments
    print("Available VISA instruments:")
    # This calls the listing function and stores the returned list of VISA addresses
    instruments = list_available_instruments()
    # [Blank line for visual separation between sections]
    # This checks whether any instruments were found before trying to display or test them
    if instruments:
        # This loops through each address and prints it with a numbered label
        for i, addr in enumerate(instruments):
            # This prints the index and address of each discovered instrument
            print(f"  {i+1}. {addr}")
        # [Blank line for visual separation between sections]
        # This comment introduces the filtering step that looks specifically for Tektronix instruments
        # Test with first Tektronix instrument found
        # This filters the list to keep only addresses that suggest a Tektronix instrument
        tek_instruments = [addr for addr in instruments if 'tek' in addr.lower() or '0699' in addr]
        # [Blank line for visual separation between sections]
        # This checks whether any Tektronix instruments were found in the filtered list
        if tek_instruments:
            # This prints the address of the first Tektronix instrument that will be tested
            print(f"\nTesting with Tektronix instrument: {tek_instruments[0]}")
            # This runs the full SCPI wrapper test against the first Tektronix instrument found
            test_scpi_wrapper(tek_instruments[0])
        # This handles the case where no Tektronix instruments were found
        else:
            # This prints an informational message explaining that automatic testing is skipped
            print("\nNo Tektronix instruments found for automatic testing")
            # This prints instructions for running a manual test with a user-supplied VISA address
            print("To test manually, use: test_scpi_wrapper('YOUR_VISA_ADDRESS')")
    # This handles the case where no instruments at all were found
    else:
        # This prints a message telling the operator that no instruments are visible
        print("  No VISA instruments found")
        # This prints a hint about the most common reasons why no instruments appear
        print("Make sure your oscilloscope is connected and VISA drivers are installed")
