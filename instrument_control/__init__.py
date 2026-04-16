# This line tells the operating system to run this file using Python 3 when executed directly from the command line
#!/usr/bin/env python3
# This is the opening line of the module-level docstring — it provides the library's display name
"""
# This line is part of the docstring that gives a brief, professional name for this library
Professional Instrument Control Library

# This blank line inside the docstring separates the title from the detailed description
# A comprehensive, enterprise-grade Python library for controlling laboratory
# and test equipment with precision and reliability.
A comprehensive, enterprise-grade Python library for controlling laboratory
and test equipment with precision and reliability.

# This line credits the team responsible for authoring this library
Author: Professional Instrument Control Team
# This line records the current version number of this library for tracking updates
Version: 1.0.1
# This line declares the open-source license under which this library is distributed
License: MIT
"""

# [Blank line for visual separation between sections]

# This line sets the version number of the library so other code or tools can check which release is installed
__version__ = "1.0.1"
# This line records the name of the team or individual who created and maintains this library
__author__ = "Professional Instrument Control Team"
# This line stores a contact email address for support or enquiries related to this library
__email__ = "support@example.com"
# This line declares the software license that governs how others may use or distribute this library
__license__ = "MIT"
# This line stores a short human-readable sentence summarising what this library does
__description__ = "Professional-grade instrument control library for laboratory automation"

# [Blank line for visual separation between sections]

# These two comment lines explain that modules are loaded only when they are actually requested,
# rather than all at once when the package is first imported, to keep startup fast
# Import main instrument control classes for convenient access
# Note: Lazy imports to avoid loading all modules when only one is needed
# This defines a special Python function that is called automatically whenever someone
# tries to access an attribute of this package that has not been loaded yet —
# it acts as a gatekeeper that loads the right module on demand
def __getattr__(name):
    # This is the docstring for the lazy-import function — it explains the purpose in one sentence
    """Lazy import of instrument modules to avoid loading everything at once."""
    # This checks whether the name being requested is one of the Keithley power supply classes
    if name in ["KeithleyPowerSupply", "KeithleyPowerSupplyError"]:
        # This line loads the Keithley power supply module and imports both of its main classes
        from .keithley_power_supply import KeithleyPowerSupply, KeithleyPowerSupplyError
        # This returns the correct class depending on which name was asked for
        return KeithleyPowerSupply if name == "KeithleyPowerSupply" else KeithleyPowerSupplyError

    # [Blank line for visual separation between sections]
    # This checks whether the name being requested belongs to the Keithley DMM6500 multimeter group
    elif name in ["KeithleyDMM6500", "KeithleyDMM6500Error", "MeasurementFunction"]:
        # This line loads the Keithley DMM module and imports all three of its public classes
        from .keithley_dmm import KeithleyDMM6500, KeithleyDMM6500Error, MeasurementFunction
        # This returns the main DMM6500 class if that is what was requested
        if name == "KeithleyDMM6500":
            # This sends back the main instrument driver class for the Keithley DMM6500
            return KeithleyDMM6500
        # This handles the case where the error class specifically was requested
        elif name == "KeithleyDMM6500Error":
            # This sends back the custom error/exception class for the DMM6500
            return KeithleyDMM6500Error
        # This handles the remaining case — the MeasurementFunction class
        else:
            # This sends back the class that defines available measurement modes for the DMM
            return MeasurementFunction

    # [Blank line for visual separation between sections]
    # This checks whether the name being requested belongs to the Keithley 2380 electronic load
    elif name in ["Keithley2380", "Keithley2380Error"]:
        # This line loads the Keithley electronic load module and imports both of its classes
        from .keithley_load import Keithley2380, Keithley2380Error
        # This returns the correct class — either the driver or the error class — based on what was asked
        return Keithley2380 if name == "Keithley2380" else Keithley2380Error

    # [Blank line for visual separation between sections]
    # This checks whether the name being requested belongs to the Keysight oscilloscope group
    elif name in ["KeysightDSOX6004A", "KeysightDSOX6004AError"]:
        # This line loads the Keysight oscilloscope module and imports both of its classes
        from .keysight_oscilloscope import KeysightDSOX6004A, KeysightDSOX6004AError
        # This returns the correct class — either the driver or the error class — based on what was asked
        return KeysightDSOX6004A if name == "KeysightDSOX6004A" else KeysightDSOX6004AError

    # [Blank line for visual separation between sections]
    # This checks whether the name being requested is one of the instrument-scanning utility functions
    elif name in ["scan_and_identify_instruments", "list_available_instruments", "classify_instrument_type"]:
        # This line loads the SCPI wrapper module and imports the three instrument-scanning functions
        from .scpi_wrapper import scan_and_identify_instruments, list_available_instruments, classify_instrument_type
        # This returns the function that scans all connected VISA instruments and identifies each one
        if name == "scan_and_identify_instruments":
            # This sends back the scan-and-identify function to whoever requested it
            return scan_and_identify_instruments
        # This returns the simpler function that just lists VISA addresses without identifying them
        elif name == "list_available_instruments":
            # This sends back the list-instruments function to whoever requested it
            return list_available_instruments
        # This handles the last remaining case — the instrument-type classification function
        else:
            # This sends back the function that determines what type of instrument a given model is
            return classify_instrument_type

    # [Blank line for visual separation between sections]
    # This line raises an error if none of the known names matched — standard Python behaviour for missing attributes
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# [Blank line for visual separation between sections]
# This defines the public list of names that are exported when someone writes "from instrument_control import *"
__all__ = [
    # This group of entries exports the library metadata strings so external tools can read them
    # Version information
    "__version__",
    # This exports the author name string
    "__author__",
    # This exports the support email string
    "__email__",
    # This exports the license name string
    "__license__",
    # This exports the short description string
    "__description__",

    # [Blank line for visual separation between sections]
    # This group of entries exports the two Keithley power supply classes
    # Keithley Power Supply classes
    "KeithleyPowerSupply",
    # This exports the custom exception class for Keithley power supply errors
    "KeithleyPowerSupplyError",

    # [Blank line for visual separation between sections]
    # This group of entries exports the two Keithley electronic load classes
    # Keithley Electronic Load classes
    "Keithley2380",
    # This exports the custom exception class for Keithley 2380 electronic load errors
    "Keithley2380Error",

    # [Blank line for visual separation between sections]
    # This group of entries exports the three Keithley multimeter-related classes
    # Keithley Multimeter classes
    "KeithleyDMM6500",
    # This exports the custom exception class for Keithley DMM6500 errors
    "KeithleyDMM6500Error",
    # This exports the class that lists and represents the measurement modes available on the DMM
    "MeasurementFunction",

    # [Blank line for visual separation between sections]
    # This group of entries exports the two Keysight oscilloscope classes
    # Keysight Oscilloscope classes
    "KeysightDSOX6004A",
    # This exports the custom exception class for Keysight DSOX6004A oscilloscope errors
    "KeysightDSOX6004AError",

    # [Blank line for visual separation between sections]
    # This group of entries exports the three instrument-discovery utility functions
    # Auto-detection utilities
    "scan_and_identify_instruments",
    # This exports the simpler utility that returns a plain list of VISA addresses
    "list_available_instruments",
    # This exports the function that categorises a detected instrument by its model string
    "classify_instrument_type",
]

# [Blank line for visual separation between sections]
# This comment introduces the LIBRARY_INFO dictionary that bundles all key metadata in one place
# Library information
# This creates a dictionary that collects all important facts about this library
# so they can be retrieved as a single structured object
LIBRARY_INFO = {
    # This entry stores the full display name of the library
    "name": "Professional Instrument Control Library",
    # This entry links to the __version__ variable so the version is only defined in one place
    "version": __version__,
    # This entry links to the __author__ variable to keep the author name consistent
    "author": __author__,
    # This entry links to the __license__ variable to keep the license declaration consistent
    "license": __license__,
    # This entry links to the __description__ variable to keep the summary text consistent
    "description": __description__,
    # This entry is a nested dictionary that groups supported instruments by category
    "supported_instruments": {
        # This key groups all supported power supply model families
        "power_supplies": [
            # This entry lists the Keithley 2230 series as a supported power supply family
            "Keithley 2230 Series",
            # This entry lists the Keithley 2231A series as a supported power supply family
            "Keithley 2231A Series",
            # This entry lists the Keithley 2280S series as a supported power supply family
            "Keithley 2280S Series",
            # This entry lists the Keithley 2260B and 2268 series as supported power supply families
            "Keithley 2260B/2268 Series"
        ],
        # This key groups all supported digital multimeter model families
        "multimeters": [
            # This entry lists the Keithley DMM6500 as a supported multimeter
            "Keithley DMM6500",
            # This entry lists the Keithley DMM7510 as a supported multimeter
            "Keithley DMM7510"
        ],
        # This key groups all supported oscilloscope model families
        "oscilloscopes": [
            # This entry lists the Keysight DSOX6004A as the supported oscilloscope model
            "Keysight DSOX6000 Series (DSOX6004A)"
        ]
    }
}

# [Blank line for visual separation between sections]
# [Blank line for visual separation between sections]
# This defines a function that returns a safe copy of the library information dictionary
def get_library_info() -> dict:
    # This is the docstring for get_library_info — it explains the purpose and what is returned
    """
    Get comprehensive library information.

    Returns:
        Dictionary containing library metadata and capabilities
    """
    # This returns a copy of LIBRARY_INFO so that the caller cannot accidentally modify the original
    return LIBRARY_INFO.copy()

# [Blank line for visual separation between sections]
# [Blank line for visual separation between sections]
# This defines a function that checks whether all required and optional Python packages are installed
def check_dependencies() -> dict:
    # This is the docstring for check_dependencies — it explains the purpose and what is returned
    """
    Check availability of required dependencies.

    Returns:
        Dictionary with dependency status information
    """
    # This creates an empty dictionary that will be filled with the status of each package
    dependencies = {}

    # [Blank line for visual separation between sections]
    # This comment labels the block that specifically tests for the PyVISA instrument communication library
    # Check PyVISA
    # This begins a protected attempt to import PyVISA — if it is missing, the except block will catch the error
    try:
        # This imports the PyVISA library, which is needed to talk to instruments over USB/GPIB/LAN
        import pyvisa
        # This records in the dictionary that PyVISA is available, along with its installed version number
        dependencies['pyvisa'] = {
            # This sub-entry confirms that PyVISA was found and loaded successfully
            'available': True,
            # This sub-entry stores the installed version string of PyVISA
            'version': pyvisa.__version__,
            # This sub-entry starts with an empty list that will be filled with the detected VISA backends
            'backends': []
        }

        # [Blank line for visual separation between sections]
        # This comment labels the inner block that probes for available VISA driver backends
        # Check available VISA backends
        # This inner try block attempts to open the default system VISA backend
        try:
            # This creates a PyVISA resource manager using the default installed VISA driver
            rm = pyvisa.ResourceManager()
            # This records that the default VISA backend is available on this machine
            dependencies['pyvisa']['backends'].append('Default')
            # This closes the resource manager after checking, freeing system resources
            rm.close()
        # This silently ignores any error if the default backend is not installed
        except:
            # This passes without action if the default VISA backend cannot be opened
            pass

        # [Blank line for visual separation between sections]
        # This inner try block attempts to open the pure-Python fallback VISA backend (PyVISA-py)
        try:
            # This creates a resource manager using the PyVISA-py software-only backend
            rm = pyvisa.ResourceManager('@py')
            # This records that the PyVISA-py backend is available on this machine
            dependencies['pyvisa']['backends'].append('PyVISA-py')
            # This closes the resource manager after checking, freeing system resources
            rm.close()
        # This silently ignores any error if the PyVISA-py backend is not installed
        except:
            # This passes without action if the PyVISA-py backend cannot be opened
            pass

    # [Blank line for visual separation between sections]
    # This catches the specific error that occurs when PyVISA is not installed at all
    except ImportError:
        # This records in the dictionary that PyVISA is missing and cannot be used
        dependencies['pyvisa'] = {
            # This sub-entry explicitly marks PyVISA as unavailable
            'available': False,
            # This sub-entry stores a human-readable explanation of why PyVISA is missing
            'error': 'PyVISA not installed'
        }

    # [Blank line for visual separation between sections]
    # This comment labels the block that tests for the NumPy numerical computing library
    # Check NumPy
    # This begins a protected attempt to import NumPy — if it is missing, the except block will catch the error
    try:
        # This imports NumPy, which is needed for processing arrays of measurement data
        import numpy
        # This records in the dictionary that NumPy is available, along with its installed version number
        dependencies['numpy'] = {
            # This sub-entry confirms that NumPy was found and loaded successfully
            'available': True,
            # This sub-entry stores the installed version string of NumPy
            'version': numpy.__version__
        }
    # This catches the specific error that occurs when NumPy is not installed at all
    except ImportError:
        # This records in the dictionary that NumPy is missing and cannot be used
        dependencies['numpy'] = {
            # This sub-entry explicitly marks NumPy as unavailable
            'available': False,
            # This sub-entry stores a human-readable explanation of why NumPy is missing
            'error': 'NumPy not installed'
        }

    # [Blank line for visual separation between sections]
    # This comment labels the block that tests for optional libraries which are useful but not strictly required
    # Check optional dependencies
    # This creates a list of optional package names to probe one by one
    optional_deps = ['scipy', 'matplotlib', 'pandas', 'gradio']
    # This loops through each optional package name in the list
    for dep in optional_deps:
        # This begins a protected attempt to import each optional package
        try:
            # This dynamically imports the package by name and stores a reference to the loaded module
            module = __import__(dep)
            # This records in the dictionary that the optional package is available
            dependencies[dep] = {
                # This sub-entry confirms the optional package was found and loaded
                'available': True,
                # This sub-entry stores the version string, falling back to 'unknown' if none is defined
                'version': getattr(module, '__version__', 'unknown'),
                # This sub-entry flags this entry as optional so callers know it is not strictly required
                'optional': True
            }
        # This catches the specific error that occurs when the optional package is not installed
        except ImportError:
            # This records in the dictionary that the optional package is missing
            dependencies[dep] = {
                # This sub-entry explicitly marks the optional package as unavailable
                'available': False,
                # This sub-entry stores a human-readable explanation that the package is not installed
                'error': f'{dep} not installed',
                # This sub-entry flags this entry as optional so callers know missing it is not critical
                'optional': True
            }

    # [Blank line for visual separation between sections]
    # This returns the completed dependency status dictionary to whoever called this function
    return dependencies

# [Blank line for visual separation between sections]
# [Blank line for visual separation between sections]
# This defines a function that returns a detailed comparison of the supported oscilloscope models
def get_oscilloscope_comparison() -> dict:
    # This is the docstring for get_oscilloscope_comparison — it explains the purpose and what is returned
    """
    Get comparison between supported oscilloscope models.

    Returns:
        Dictionary comparing oscilloscope specifications and capabilities
    """
    # This returns a dictionary containing the technical specifications for the Keysight DSOX6004A
    return {
        # This key identifies the Keysight DSOX6004A entry within the comparison dictionary
        "keysight_dsox6004a": {
            # This sub-entry names the company that manufactures this oscilloscope
            "manufacturer": "Keysight Technologies",
            # This sub-entry records the model number of this oscilloscope
            "model": "DSOX6004A",
            # This sub-entry records the product series this oscilloscope belongs to
            "series": "InfiniiVision 6000 X-Series",
            # This sub-entry records the maximum signal frequency this oscilloscope can accurately capture
            "bandwidth": "1 GHz",
            # This sub-entry records the number of analogue input channels this oscilloscope provides
            "channels": 4,
            # This sub-entry records how many data samples per second this oscilloscope can capture at maximum speed
            "sample_rate": "20 GS/s",
            # This sub-entry records how many data points the oscilloscope can store in one acquisition
            "memory_depth": "16 Mpts",
            # This sub-entry records the bit-depth of the analogue-to-digital converter in this oscilloscope
            "resolution": "8-bit",
            # This sub-entry records how many built-in signal generators this oscilloscope contains
            "function_generators": 2,
            # This sub-entry records the number of digital logic channels (this model has none)
            "digital_channels": 0,
            # This sub-entry lists the standout features of this oscilloscope in plain English
            "key_features": [
                # This feature highlights the wide frequency range this oscilloscope can handle
                "High bandwidth (1 GHz)",
                # This feature highlights the two built-in signal generators
                "Dual function generators",
                # This feature highlights the flexible triggering options available
                "Advanced trigger modes",
                # This feature highlights the on-screen mathematical processing of signals
                "Math functions",
                # This feature highlights the very fast data capture rate
                "High sample rate"
            ]
        }
    }

# [Blank line for visual separation between sections]
# [Blank line for visual separation between sections]
# This defines a function that returns recommended use cases for each supported oscilloscope model
def get_recommended_usage() -> dict:
    # This is the docstring for get_recommended_usage — it explains the purpose and what is returned
    """
    Get recommended usage scenarios for each oscilloscope.

    Returns:
        Dictionary with recommended applications for each model
    """
    # This returns a dictionary where each oscilloscope model maps to a list of ideal application areas
    return {
        # This key identifies the list of recommended applications for the Keysight DSOX6004A
        "keysight_dsox6004a": [
            # This describes one recommended use case — analysing very high-frequency signals
            "High-frequency signal analysis (up to 1 GHz)",
            # This describes another recommended use case — radio frequency and microwave signal work
            "RF and microwave applications",
            # This describes another use case — checking that fast digital signals meet their timing specs
            "High-speed digital signal validation",
            # This describes another use case — applications that need the built-in signal generators
            "Advanced signal generation requirements",
            # This describes the final use case — any application that requires maximum capture bandwidth
            "Applications requiring maximum bandwidth"
        ]
    }

# [Blank line for visual separation between sections]
# [Blank line for visual separation between sections]
# This comment introduces the factory function that creates the correct oscilloscope object based on a model name
# Convenience function for quick instrument selection
# This defines a factory function that creates and returns the right oscilloscope driver object
# based on a plain-English model string, hiding the import details from the caller
def create_oscilloscope(model: str, visa_address: str, **kwargs):
    # This is the docstring for create_oscilloscope — it lists all inputs, outputs, and possible errors
    """
    Factory function to create oscilloscope instances.

    Args:
        model: Oscilloscope model ("keysight_dsox6004a", "keysight_hd304mso", or "tektronix_mso24")
        visa_address: VISA address for the instrument
        **kwargs: Additional arguments passed to the constructor

    Returns:
        Oscilloscope instance

    Raises:
        ValueError: If model is not supported
    """
    # This converts the model string to lowercase and replaces dashes and spaces with underscores
    # so that user input like "DSOX-6004A" or "dsox 6004a" all match the same condition below
    model = model.lower().replace("-", "_").replace(" ", "_")

    # [Blank line for visual separation between sections]
    # This checks whether the normalised model string matches the Keysight DSOX6004A
    if model in ["keysight_dsox6004a", "dsox6004a"]:
        # This imports the Keysight DSOX6004A driver class from the oscilloscope sub-module
        from .keysight_oscilloscope import KeysightDSOX6004A
        # This creates a new Keysight DSOX6004A instrument object using the provided VISA address
        # and any extra keyword arguments, then returns it to the caller
        return KeysightDSOX6004A(visa_address, **kwargs)
    # This handles the case where the model string does not match any supported oscilloscope
    else:
        # This raises a descriptive error telling the caller which model they asked for
        # and listing the only currently supported model so they can correct their input
        raise ValueError(f"Unsupported oscilloscope model: {model}. "
                        f"Supported models: keysight_dsox6004a")

# [Blank line for visual separation between sections]
# [Blank line for visual separation between sections]
# This comment introduces the BEST_PRACTICES dictionary that collects professional coding guidelines
# Professional instrument control best practices
# This creates a dictionary of recommended engineering guidelines organised into four categories
# so developers can refer to them programmatically or display them in documentation
BEST_PRACTICES = {
    # This key groups guidelines for managing instrument connections safely and reliably
    "connection_management": [
        # This guideline recommends using error-handling blocks for all instrument communication calls
        "Always use try-catch blocks for VISA operations",
        # This guideline recommends setting sensible time limits so the program does not hang indefinitely
        "Implement proper timeout management for long operations",
        # This guideline recommends always closing the instrument connection when finished
        "Use context managers or ensure proper disconnect() calls",
        # This guideline recommends confirming the instrument responds correctly after connecting
        "Verify instrument identification after connection"
    ],
    # This key groups guidelines for structuring measurement automation sequences
    "measurement_automation": [
        # This guideline recommends setting up all channel parameters before beginning a test run
        "Configure channels before starting measurements",
        # This guideline recommends configuring triggers so waveforms are captured cleanly and repeatably
        "Use appropriate trigger settings for stable acquisition",
        # This guideline recommends checking that each measurement value is valid before using it
        "Implement error checking for measurement validity",
        # This guideline recommends storing configuration settings so tests can be reproduced exactly
        "Save configuration state for reproducible results"
    ],
    # This key groups guidelines for handling and storing measurement data professionally
    "data_handling": [
        # This guideline recommends naming saved files with timestamps and meaningful identifiers
        "Use professional file naming conventions with timestamps",
        # This guideline recommends validating data values and handling corrupted readings gracefully
        "Implement proper data validation and error checking",
        # This guideline recommends including instrument settings and test conditions alongside measurement data
        "Provide comprehensive metadata with exported data",
        # This guideline recommends choosing the right file format (e.g. CSV for readability, binary for speed)
        "Use appropriate data formats (CSV, binary) for the application"
    ],
    # This key groups guidelines for safely running multiple operations at the same time
    "thread_safety": [
        # This guideline recommends using locking mechanisms to prevent two threads from sending commands simultaneously
        "Use locks for multi-threaded instrument access",
        # This guideline recommends catching exceptions inside background threads so they do not crash silently
        "Implement proper exception handling in threads",
        # This guideline warns that sending two SCPI commands to the same instrument at the same time can corrupt communication
        "Avoid simultaneous SCPI commands to the same instrument",
        # This guideline recommends using queue objects to safely pass data between threads
        "Use queues for data sharing between threads"
    ]
}

# [Blank line for visual separation between sections]
# [Blank line for visual separation between sections]
# This defines a function that returns a safe copy of the best practices dictionary
def get_best_practices() -> dict:
    # This is the docstring for get_best_practices — it explains the purpose and what is returned
    """
    Get professional instrument control best practices.

    Returns:
        Dictionary containing best practice guidelines
    """
    # This returns a copy of BEST_PRACTICES so that the caller cannot accidentally modify the original
    return BEST_PRACTICES.copy()
