#!/usr/bin/env python3
# This line tells the operating system to run this file using Python 3; it is required for direct execution on Linux/macOS and is harmless on Windows
"""
VISA Instrument Auto-Detection Module

Automatically detects and identifies all connected VISA instruments including:
- Oscilloscopes (Tektronix, Keysight)
- Electronic Loads (Keithley 2380)
- Power Supplies (Keithley)
- Digital Multimeters (Keithley DMM6500)

Usage:
    from visa_auto_detect import detect_all_instruments

    instruments = detect_all_instruments()
    scope = instruments['oscilloscope']
    load = instruments['electronic_load']
"""

# Load the 'logging' library, which allows the program to record informational and error messages to the console or a log file during test execution
import logging
# Load type-hint helpers (Dict, Optional, List, Tuple) from the 'typing' library; these labels make the code self-documenting and help catch programming errors early
from typing import Dict, Optional, List, Tuple
# Load the 'dataclass' decorator from Python's built-in dataclasses library; this allows data-holding classes to be written concisely without writing repetitive setup code
from dataclasses import dataclass
# Load the 'Enum' base class, which is used to define a fixed set of named instrument-type labels (e.g., OSCILLOSCOPE, DMM) that cannot be accidentally misspelled elsewhere in the code
from enum import Enum

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a fixed list of instrument-type labels; using an Enum prevents typos and makes comparisons reliable throughout the codebase
class InstrumentType(Enum):
    # Each entry below is a named constant; the string value on the right is what appears in output messages and dictionary keys
    """Instrument type enumeration"""
    # Label used when the detected instrument is an oscilloscope (e.g., Tektronix MSO, Keysight DSOX)
    OSCILLOSCOPE = "oscilloscope"
    # Label used when the detected instrument is a programmable electronic load (e.g., Keithley 2380)
    ELECTRONIC_LOAD = "electronic_load"
    # Label used when the detected instrument is a DC power supply (e.g., Keithley 2230)
    POWER_SUPPLY = "power_supply"
    # Label used when the detected instrument is a digital multimeter (e.g., Keithley DMM6500)
    DMM = "dmm"
    # Label used when the instrument is connected but its type cannot be determined from its identification string
    UNKNOWN = "unknown"

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Apply the @dataclass decorator, which automatically generates the standard __init__, __repr__, and __eq__ methods so this class can store instrument details without extra boilerplate code
@dataclass
# Define a container class that holds all identifying information about one detected instrument; one instance of this class is created for each instrument found on the bus
class InstrumentInfo:
    # Each attribute below is a field that will be populated when an instrument is identified on the VISA bus
    """Information about a detected instrument"""
    # The VISA address string used to open a communication channel to this instrument (e.g., "USB0::0x0957::0x1780::MY65220169::INSTR")
    address: str
    # The category of instrument, stored as one of the InstrumentType labels defined above
    instrument_type: InstrumentType
    # The company that made the instrument (e.g., "TEKTRONIX", "KEYSIGHT"), parsed from the instrument's identification response
    manufacturer: str
    # The specific product model name or number (e.g., "MSO24", "2380"), parsed from the identification response
    model: str
    # The unique serial number of this individual instrument unit, parsed from the identification response
    serial: str
    # The version of internal software currently running on the instrument, parsed from the identification response
    firmware: str
    # The complete, raw identification string exactly as the instrument returned it; stored for traceability and debugging
    full_idn: str

    # Define how this object should look when printed as text; returns a readable summary line combining manufacturer, model, type, and address
    def __str__(self):
        # Build and return a formatted one-line summary such as "TEKTRONIX MSO24 (oscilloscope) at USB0::0x0699::0x0522::C012345::INSTR"
        return f"{self.manufacturer} {self.model} ({self.instrument_type.value}) at {self.address}"

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define the main detection class; all logic for scanning the VISA bus and identifying instruments is contained here
class VISAAutoDetector:
    # Docstring summarising the purpose of this class for anyone reading the source code
    """Automatic VISA instrument detection and identification"""

    # Define the setup method that runs automatically whenever a new VISAAutoDetector object is created
    def __init__(self):
        # Docstring explaining what this setup step does
        """Initialize auto-detector"""
        # Create a logger object named after this class; all messages logged through this object will be labelled with the class name, making it easy to trace where a log message came from
        self._logger = logging.getLogger(f"{self.__class__.__name__}")
        # Create an empty list that will be filled with InstrumentInfo objects as instruments are discovered during a scan; starts empty so each scan begins fresh
        self._detected_instruments: List[InstrumentInfo] = []

    # Define the public method that performs a full scan of all VISA resources and returns a dictionary of found instruments
    def detect_all_instruments(self) -> Dict[str, InstrumentInfo]:
        """
        Detect all connected VISA instruments

        Returns:
            Dictionary mapping instrument type to InstrumentInfo
            Keys: 'oscilloscope', 'electronic_load', 'power_supply', 'dmm'
        """
        # Create an empty dictionary that will hold one entry per instrument type found (e.g., 'oscilloscope': <InstrumentInfo>)
        instruments = {}

        # Attempt to import the PyVISA library; if it is not installed the scan cannot proceed
        try:
            # Load the pyvisa library, which provides all communication functions for VISA-connected instruments; this import is done here (not at the top of the file) so the rest of the module still works even without pyvisa installed
            import pyvisa
        # If PyVISA is not installed, Python raises an ImportError; this block catches that specific error gracefully
        except ImportError:
            # Record a clear error message in the log explaining how the engineer can fix the missing dependency
            self._logger.error("PyVISA not installed. Run: pip install pyvisa pyvisa-py")
            # Return the empty instruments dictionary immediately because no scanning can be done without the library
            return instruments

        # Attempt to open the VISA resource manager and scan all connected addresses; any hardware or driver error is caught below
        try:
            # Create resource manager
            # Open a VISA resource manager, which is the gateway object that can list and open connections to all VISA instruments currently visible to the PC
            rm = pyvisa.ResourceManager()
            # Ask the resource manager for a list of all VISA address strings currently detectable on the PC (USB, GPIB, LAN, etc.)
            resources = rm.list_resources()

            # Check whether the resource manager returned any addresses at all; if not, there is nothing to scan
            if not resources:
                # Record a warning in the log file so the absence of instruments is traceable
                self._logger.warning("No VISA resources found!")
                # Print a visible warning directly to the console so the engineer knows immediately that nothing was found
                print("\nWARNING: No VISA instruments detected!")
                # Print the first suggested troubleshooting action for the engineer
                print("  - Check instrument connections")
                # Print the second suggested troubleshooting action
                print("  - Verify VISA drivers are installed")
                # Print the third suggested troubleshooting action
                print("  - Ensure instruments are powered on")
                # Return the still-empty instruments dictionary because there is nothing to identify
                return instruments

            # Print a progress message showing how many VISA addresses will be probed
            print(f"\nScanning {len(resources)} VISA resource(s)...")
            # Print a horizontal divider line to separate the scan progress output from earlier console text
            print("-" * 70)

            # Scan each resource
            # Loop through every detected VISA address one at a time and try to identify what instrument is at that address
            for resource in resources:
                # Wrap each individual instrument query in its own try/except so that a problem with one instrument does not stop the scan of all remaining instruments
                try:
                    # Call the helper method that opens the address, sends an identification command, and returns a populated InstrumentInfo object (or None if it failed)
                    inst_info = self._identify_instrument(rm, resource)
                    # Only proceed if the instrument was successfully identified (inst_info will be None if identification failed)
                    if inst_info:
                        # Add the newly identified instrument to the master list of all instruments detected in this scan session
                        self._detected_instruments.append(inst_info)

                        # Add to results dictionary
                        # Extract the instrument type as a plain string key (e.g., "oscilloscope") so it can be used as a dictionary key
                        type_key = inst_info.instrument_type.value

                        # Store first found instrument of each type
                        # Only add this instrument to the results dictionary if no instrument of this type has been found yet; this ensures the dictionary always holds exactly one entry per instrument type
                        if type_key not in instruments:
                            # Store this instrument as the primary representative of its type in the results dictionary
                            instruments[type_key] = inst_info
                            # Print a green-tick-style confirmation line so the engineer can see which instrument was successfully found and logged
                            print(f"  ✓ {inst_info}")
                        else:
                            # Multiple instruments of same type found
                            # Log an informational note that a second instrument of the same type was found but is being ignored in favour of the first one
                            self._logger.info(f"Additional {type_key} found (using first): {inst_info}")
                            # Print a notice to the console so the engineer is aware that a duplicate instrument type was detected
                            print(f"  ℹ {inst_info} (duplicate, using first)")

                # If communication with this particular address failed for any reason, catch the error and move on to the next address
                except Exception as e:
                    # Log the failure at DEBUG level (not a critical error; some addresses may belong to non-instrument devices)
                    self._logger.debug(f"Failed to query {resource}: {e}")
                    # Print a cross-style failure line to the console so the engineer can see which address could not be identified
                    print(f"  ✗ {resource}: Unable to identify")

            # Print a closing horizontal divider line after the per-instrument scan output
            print("-" * 70)

            # Report summary
            # Print the heading for the final summary block that lists all successfully identified instruments
            print(f"\nDetected instruments:")
            # Check whether at least one instrument was identified before printing the summary table
            if instruments:
                # Iterate over each instrument type and its corresponding information object to print a summary row
                for inst_type, info in instruments.items():
                    # Print one summary row per instrument type, showing the type label, manufacturer, and model in aligned columns
                    print(f"  {inst_type:18s} : {info.manufacturer} {info.model}")
            else:
                # Print a single message indicating that the scan completed but no instruments could be positively identified
                print("  None - no instruments could be identified")

        # If anything in the entire scanning block fails unexpectedly (e.g., a VISA driver crash), catch the error here so the program does not crash
        except Exception as e:
            # Record the unexpected error in the log file for later diagnosis
            self._logger.error(f"VISA detection error: {e}")
            # Print a human-readable error message to the console so the engineer is immediately informed
            print(f"\nERROR during VISA detection: {e}")

        # Return the completed results dictionary; it may be empty if no instruments were found or all queries failed
        return instruments

    # Define the private helper method responsible for opening one VISA address and asking the instrument to identify itself
    def _identify_instrument(self, rm, address: str) -> Optional[InstrumentInfo]:
        """
        Identify a single instrument by querying *IDN?

        Args:
            rm: PyVISA resource manager
            address: VISA address to query

        Returns:
            InstrumentInfo or None if identification failed
        """
        # Attempt to open the instrument and query its identity; if anything fails, return None rather than crashing
        try:
            # Open resource with short timeout
            # Ask the VISA resource manager to open a communication channel to the instrument at the given address
            inst = rm.open_resource(address)
            # Set a 3-second time limit for any command sent to this instrument; if the instrument does not respond within 3 seconds, the query will fail and be handled by the except block
            inst.timeout = 3000  # 3 second timeout

            # Query identification
            # Send the standard IEEE 488.2 identification command "*IDN?" to the instrument and strip any trailing whitespace or newline characters from the response
            idn = inst.query("*IDN?").strip()
            # Close the communication channel to this instrument now that the identification string has been retrieved, freeing up the VISA resource
            inst.close()

            # Parse IDN response
            # Split the identification string at every comma; the standard format is "Manufacturer,Model,Serial,Firmware"
            parts = idn.split(',')
            # Extract the manufacturer name from the first comma-separated field, or use "Unknown" if the string did not contain that field
            manufacturer = parts[0].strip() if len(parts) > 0 else "Unknown"
            # Extract the model name or number from the second comma-separated field, or use "Unknown" if not present
            model = parts[1].strip() if len(parts) > 1 else "Unknown"
            # Extract the serial number from the third comma-separated field, or use "Unknown" if not present
            serial = parts[2].strip() if len(parts) > 2 else "Unknown"
            # Extract the firmware version from the fourth comma-separated field, or use "Unknown" if not present
            firmware = parts[3].strip() if len(parts) > 3 else "Unknown"

            # Identify instrument type
            # Pass the full identification string, manufacturer name, and model name to the classification method to determine what category of instrument this is
            inst_type = self._classify_instrument(idn, manufacturer, model)

            # Build and return a fully populated InstrumentInfo object containing all the information gathered about this instrument
            return InstrumentInfo(
                # Store the VISA address that was used to reach this instrument
                address=address,
                # Store the instrument category determined by the classification method
                instrument_type=inst_type,
                # Store the manufacturer name parsed from the identification string
                manufacturer=manufacturer,
                # Store the model name or number parsed from the identification string
                model=model,
                # Store the serial number parsed from the identification string
                serial=serial,
                # Store the firmware version parsed from the identification string
                firmware=firmware,
                # Store the complete raw identification string for traceability
                full_idn=idn
            )

        # If the instrument could not be opened, did not respond in time, or returned an unreadable response, catch the error here
        except Exception as e:
            # Log the failure at DEBUG level for diagnostic purposes; this is not a critical error because some VISA addresses may not be instruments
            self._logger.debug(f"Failed to identify {address}: {e}")
            # Return None to signal to the caller that this address could not be identified
            return None

    # Define the private helper method that reads an identification string and decides what type of instrument it belongs to
    def _classify_instrument(self, idn: str, manufacturer: str, model: str) -> InstrumentType:
        """
        Classify instrument type based on IDN string

        Args:
            idn: Full *IDN? response
            manufacturer: Manufacturer name
            model: Model number

        Returns:
            InstrumentType
        """
        # Convert the full identification string to upper case so that comparisons are not case-sensitive (instruments from different brands may return mixed-case strings)
        idn_upper = idn.upper()
        # Convert the model string to upper case for case-insensitive comparison
        model_upper = model.upper()
        # Convert the manufacturer string to upper case for case-insensitive comparison
        mfg_upper = manufacturer.upper()

        # Oscilloscope detection
        # Check whether the identification string contains any of the known model-prefix codes used by major oscilloscope brands; if it does, classify this instrument as an oscilloscope
        if any(scope_id in idn_upper for scope_id in [
            'MSO', 'DPO', 'TDS', 'MDO',  # Tektronix
            'DSOX', 'DSO', 'MSO', 'MSOX', 'INFINIIUM', 'INFINIUM',  # Keysight
            'HDO', 'WRO', 'WP', 'MXO',  # LeCroy/Teledyne
            'RIGOL', 'SDS', 'DS'  # Rigol
        ]):
            # Return the OSCILLOSCOPE type label because the identification string matched a known oscilloscope prefix
            return InstrumentType.OSCILLOSCOPE

        # Electronic load detection
        # Check whether this is specifically a Keithley 2380 electronic load by verifying both the model number and the manufacturer name
        if '2380' in model_upper and 'KEITHLEY' in mfg_upper:
            # Return the ELECTRONIC_LOAD type label because the model and manufacturer match the Keithley 2380 series
            return InstrumentType.ELECTRONIC_LOAD

        # Check whether the identification string explicitly contains the words "LOAD" or "ELECTRONIC LOAD" as a fallback for non-Keithley loads
        if any(load_id in idn_upper for load_id in ['LOAD', 'ELECTRONIC LOAD']):
            # Return the ELECTRONIC_LOAD type label based on the generic keyword match
            return InstrumentType.ELECTRONIC_LOAD

        # Power supply detection
        # Check whether the model number matches any of the known power supply model numbers from Keithley, Keysight, or Rigol
        if any(psu_id in model_upper for psu_id in [
            '2200', '2220', '2230', '2231', '2260', '2280', '2281',  # Keithley PSU
            'E3600', 'E3610', 'E3620', 'E3630', 'E3640', 'E3649',  # Keysight PSU
            'DP800', 'DP700', 'DP1000'  # Rigol PSU
        ]):
            # Return the POWER_SUPPLY type label because the model number matched a known power supply series
            return InstrumentType.POWER_SUPPLY

        # Check whether the identification string contains generic power supply keyword phrases as a fallback for unlisted models
        if any(psu_id in idn_upper for psu_id in [
            'POWER SUPPLY', 'PROGRAMMABLE POWER', 'DC POWER'
        ]):
            # Return the POWER_SUPPLY type label based on the generic keyword match
            return InstrumentType.POWER_SUPPLY

        # DMM detection
        # Check whether the model number is specifically a Keithley DMM6500 or DMM7510 digital multimeter
        if 'DMM6500' in model_upper or 'DMM7510' in model_upper:
            # Return the DMM type label because the model number matched a known Keithley multimeter
            return InstrumentType.DMM

        # Check whether the identification string contains the generic abbreviation "DMM" or the full word "MULTIMETER" as a fallback
        if 'DMM' in idn_upper or 'MULTIMETER' in idn_upper:
            # Return the DMM type label based on the generic keyword match
            return InstrumentType.DMM

        # Default to unknown
        # If none of the above checks matched, the instrument is connected but its type cannot be determined; return UNKNOWN so the caller can decide how to handle it
        return InstrumentType.UNKNOWN

    # Define the public method that returns the complete list of every instrument found during the most recent scan, including duplicates
    def list_all_detected(self) -> List[InstrumentInfo]:
        """
        Get list of all detected instruments

        Returns:
            List of InstrumentInfo objects
        """
        # Return the internal list of all detected instruments; the caller can inspect this list to see duplicates or instruments whose type was UNKNOWN
        return self._detected_instruments

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a module-level convenience function so that other scripts can detect all instruments with a single function call without needing to create a VISAAutoDetector object directly
def detect_all_instruments(verbose: bool = False) -> Dict[str, InstrumentInfo]:
    """
    Convenience function to detect all instruments

    Args:
        verbose: Enable verbose logging

    Returns:
        Dictionary mapping instrument type to InstrumentInfo
    """
    # If the caller requested verbose mode, configure the logging system to show all debug-level messages on the console, making it easier to diagnose detection problems
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Create a new VISAAutoDetector object; this sets up its internal logger and empty instrument list
    detector = VISAAutoDetector()
    # Run the full instrument scan and return the resulting dictionary of found instruments to the caller
    return detector.detect_all_instruments()

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define a specialised convenience function that runs the full detection scan but only returns the addresses of the two instruments needed specifically for the Load Transient test (oscilloscope and electronic load)
def detect_load_transient_instruments() -> Tuple[Optional[str], Optional[str]]:
    """
    Detect instruments specifically needed for Load Transient test

    Returns:
        Tuple of (oscilloscope_address, electronic_load_address)
        Returns (None, None) if instruments not found
    """
    # Run the full instrument detection scan and store the results dictionary
    instruments = detect_all_instruments()

    # Initialise the oscilloscope address variable to None; it will be overwritten if an oscilloscope is found
    scope_addr = None
    # Initialise the electronic load address variable to None; it will be overwritten if a load is found
    load_addr = None

    # Check whether the scan found an oscilloscope; if so, extract its VISA address
    if 'oscilloscope' in instruments:
        # Store the oscilloscope's VISA address so it can be returned to the caller
        scope_addr = instruments['oscilloscope'].address

    # Check whether the scan found an electronic load; if so, extract its VISA address
    if 'electronic_load' in instruments:
        # Store the electronic load's VISA address so it can be returned to the caller
        load_addr = instruments['electronic_load'].address

    # Report missing instruments
    # If no oscilloscope was found, print a warning and list the supported oscilloscope models so the engineer knows what to check
    if not scope_addr:
        # Print a prominent warning banner indicating the oscilloscope is missing
        print("\n⚠ WARNING: Oscilloscope not detected!")
        # Print the header for the list of supported oscilloscope families
        print("   Supported oscilloscopes:")
        # Print the first supported oscilloscope family
        print("     - Tektronix MSO/DPO/TDS series")
        # Print the second supported oscilloscope family
        print("     - Keysight DSOX/InfiniiVision series")

    # If no electronic load was found, print a warning and list the supported load models so the engineer knows what to check
    if not load_addr:
        # Print a prominent warning banner indicating the electronic load is missing
        print("\n⚠ WARNING: Electronic load not detected!")
        # Print the header for the list of supported electronic load models
        print("   Supported electronic loads:")
        # Print the supported electronic load series
        print("     - Keithley 2380 series")

    # Return both addresses as a pair; each will be None if the corresponding instrument was not found
    return scope_addr, load_addr

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# Define the main function that runs a standalone detection test and prints a full report; this is used when the script is run directly from the command line
def main():
    # Docstring explaining the purpose of this standalone entry point
    """Test auto-detection"""
    # Print the top border of the report header banner
    print("=" * 70)
    # Print the title of the standalone detection test
    print(" VISA INSTRUMENT AUTO-DETECTION TEST")
    # Print the bottom border of the report header banner
    print("=" * 70)

    # Run the full instrument detection scan with verbose logging enabled so all debug messages are visible when running this script directly
    instruments = detect_all_instruments(verbose=True)

    # Print a blank line followed by the top border of the summary section
    print("\n" + "=" * 70)
    # Print the heading of the summary section
    print(" DETECTION SUMMARY")
    # Print the bottom border of the summary section heading
    print("=" * 70)

    # Check whether any instruments were found before deciding what to print in the summary
    if instruments:
        # Print a count of how many distinct instrument types were found
        print(f"\nFound {len(instruments)} instrument type(s):")
        # Loop through each instrument type and its InstrumentInfo object to print a detailed block
        for inst_type, info in instruments.items():
            # Print a blank line followed by the instrument type label in upper case as a sub-heading
            print(f"\n  {inst_type.upper()}:")
            # Print the VISA address of this instrument
            print(f"    Address:      {info.address}")
            # Print the manufacturer name of this instrument
            print(f"    Manufacturer: {info.manufacturer}")
            # Print the model name or number of this instrument
            print(f"    Model:        {info.model}")
            # Print the serial number of this instrument
            print(f"    Serial:       {info.serial}")
            # Print the firmware version currently running on this instrument
            print(f"    Firmware:     {info.firmware}")
    else:
        # Print a message indicating that no instruments were found at all
        print("\n  No instruments detected!")
        # Print a blank line followed by the troubleshooting header
        print("\n  Troubleshooting:")
        # Print the first troubleshooting step: check that instruments are switched on
        print("    1. Verify instruments are powered on")
        # Print the second troubleshooting step: check the physical cable connections
        print("    2. Check USB/GPIB connections")
        # Print the third troubleshooting step: ensure the VISA driver software is installed
        print("    3. Install NI-VISA or similar VISA driver")
        # Print the fourth troubleshooting step: install the Python PyVISA package
        print("    4. Run: pip install pyvisa pyvisa-py")

    # Print the closing border of the summary section
    print("\n" + "=" * 70)

    # Return exit code 0 (success) if at least one instrument was found, or exit code 1 (failure) if the dictionary is empty
    return 0 if instruments else 1

# [Blank line for visual separation between sections]

# [Blank line for visual separation between sections]

# This block runs only when the file is executed directly (e.g., python visa_auto_detect.py); it does not run when the file is imported as a library by another script
if __name__ == "__main__":
    # Load the 'sys' library, which gives access to the system exit function; imported here because it is only needed when running as a standalone script
    import sys
    # Call the main() function and pass its return value (0 or 1) to sys.exit() so the operating system can tell whether the detection test succeeded or failed
    sys.exit(main())
