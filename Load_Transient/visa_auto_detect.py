#!/usr/bin/env python3
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

import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum


class InstrumentType(Enum):
    """Instrument type enumeration"""
    OSCILLOSCOPE = "oscilloscope"
    ELECTRONIC_LOAD = "electronic_load"
    POWER_SUPPLY = "power_supply"
    DMM = "dmm"
    UNKNOWN = "unknown"


@dataclass
class InstrumentInfo:
    """Information about a detected instrument"""
    address: str
    instrument_type: InstrumentType
    manufacturer: str
    model: str
    serial: str
    firmware: str
    full_idn: str

    def __str__(self):
        return f"{self.manufacturer} {self.model} ({self.instrument_type.value}) at {self.address}"


class VISAAutoDetector:
    """Automatic VISA instrument detection and identification"""

    def __init__(self):
        """Initialize auto-detector"""
        self._logger = logging.getLogger(f"{self.__class__.__name__}")
        self._detected_instruments: List[InstrumentInfo] = []

    def detect_all_instruments(self) -> Dict[str, InstrumentInfo]:
        """
        Detect all connected VISA instruments

        Returns:
            Dictionary mapping instrument type to InstrumentInfo
            Keys: 'oscilloscope', 'electronic_load', 'power_supply', 'dmm'
        """
        instruments = {}

        try:
            import pyvisa
        except ImportError:
            self._logger.error("PyVISA not installed. Run: pip install pyvisa pyvisa-py")
            return instruments

        try:
            # Create resource manager
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()

            if not resources:
                self._logger.warning("No VISA resources found!")
                print("\nWARNING: No VISA instruments detected!")
                print("  - Check instrument connections")
                print("  - Verify VISA drivers are installed")
                print("  - Ensure instruments are powered on")
                return instruments

            print(f"\nScanning {len(resources)} VISA resource(s)...")
            print("-" * 70)

            # Scan each resource
            for resource in resources:
                try:
                    inst_info = self._identify_instrument(rm, resource)
                    if inst_info:
                        self._detected_instruments.append(inst_info)

                        # Add to results dictionary
                        type_key = inst_info.instrument_type.value

                        # Store first found instrument of each type
                        if type_key not in instruments:
                            instruments[type_key] = inst_info
                            print(f"  ✓ {inst_info}")
                        else:
                            # Multiple instruments of same type found
                            self._logger.info(f"Additional {type_key} found (using first): {inst_info}")
                            print(f"  ℹ {inst_info} (duplicate, using first)")

                except Exception as e:
                    self._logger.debug(f"Failed to query {resource}: {e}")
                    print(f"  ✗ {resource}: Unable to identify")

            print("-" * 70)

            # Report summary
            print(f"\nDetected instruments:")
            if instruments:
                for inst_type, info in instruments.items():
                    print(f"  {inst_type:18s} : {info.manufacturer} {info.model}")
            else:
                print("  None - no instruments could be identified")

        except Exception as e:
            self._logger.error(f"VISA detection error: {e}")
            print(f"\nERROR during VISA detection: {e}")

        return instruments

    def _identify_instrument(self, rm, address: str) -> Optional[InstrumentInfo]:
        """
        Identify a single instrument by querying *IDN?

        Args:
            rm: PyVISA resource manager
            address: VISA address to query

        Returns:
            InstrumentInfo or None if identification failed
        """
        try:
            # Open resource with short timeout
            inst = rm.open_resource(address)
            inst.timeout = 3000  # 3 second timeout

            # Query identification
            idn = inst.query("*IDN?").strip()
            inst.close()

            # Parse IDN response
            parts = idn.split(',')
            manufacturer = parts[0].strip() if len(parts) > 0 else "Unknown"
            model = parts[1].strip() if len(parts) > 1 else "Unknown"
            serial = parts[2].strip() if len(parts) > 2 else "Unknown"
            firmware = parts[3].strip() if len(parts) > 3 else "Unknown"

            # Identify instrument type
            inst_type = self._classify_instrument(idn, manufacturer, model)

            return InstrumentInfo(
                address=address,
                instrument_type=inst_type,
                manufacturer=manufacturer,
                model=model,
                serial=serial,
                firmware=firmware,
                full_idn=idn
            )

        except Exception as e:
            self._logger.debug(f"Failed to identify {address}: {e}")
            return None

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
        idn_upper = idn.upper()
        model_upper = model.upper()
        mfg_upper = manufacturer.upper()

        # Oscilloscope detection
        if any(scope_id in idn_upper for scope_id in [
            'MSO', 'DPO', 'TDS', 'MDO',  # Tektronix
            'DSOX', 'DSO', 'MSO', 'MSOX', 'INFINIIUM', 'INFINIUM',  # Keysight
            'HDO', 'WRO', 'WP', 'MXO',  # LeCroy/Teledyne
            'RIGOL', 'SDS', 'DS'  # Rigol
        ]):
            return InstrumentType.OSCILLOSCOPE

        # Electronic load detection
        if '2380' in model_upper and 'KEITHLEY' in mfg_upper:
            return InstrumentType.ELECTRONIC_LOAD

        if any(load_id in idn_upper for load_id in ['LOAD', 'ELECTRONIC LOAD']):
            return InstrumentType.ELECTRONIC_LOAD

        # Power supply detection
        if any(psu_id in model_upper for psu_id in [
            '2200', '2220', '2230', '2231', '2260', '2280', '2281',  # Keithley PSU
            'E3600', 'E3610', 'E3620', 'E3630', 'E3640', 'E3649',  # Keysight PSU
            'DP800', 'DP700', 'DP1000'  # Rigol PSU
        ]):
            return InstrumentType.POWER_SUPPLY

        if any(psu_id in idn_upper for psu_id in [
            'POWER SUPPLY', 'PROGRAMMABLE POWER', 'DC POWER'
        ]):
            return InstrumentType.POWER_SUPPLY

        # DMM detection
        if 'DMM6500' in model_upper or 'DMM7510' in model_upper:
            return InstrumentType.DMM

        if 'DMM' in idn_upper or 'MULTIMETER' in idn_upper:
            return InstrumentType.DMM

        # Default to unknown
        return InstrumentType.UNKNOWN

    def list_all_detected(self) -> List[InstrumentInfo]:
        """
        Get list of all detected instruments

        Returns:
            List of InstrumentInfo objects
        """
        return self._detected_instruments


def detect_all_instruments(verbose: bool = False) -> Dict[str, InstrumentInfo]:
    """
    Convenience function to detect all instruments

    Args:
        verbose: Enable verbose logging

    Returns:
        Dictionary mapping instrument type to InstrumentInfo
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    detector = VISAAutoDetector()
    return detector.detect_all_instruments()


def detect_load_transient_instruments() -> Tuple[Optional[str], Optional[str]]:
    """
    Detect instruments specifically needed for Load Transient test

    Returns:
        Tuple of (oscilloscope_address, electronic_load_address)
        Returns (None, None) if instruments not found
    """
    instruments = detect_all_instruments()

    scope_addr = None
    load_addr = None

    if 'oscilloscope' in instruments:
        scope_addr = instruments['oscilloscope'].address

    if 'electronic_load' in instruments:
        load_addr = instruments['electronic_load'].address

    # Report missing instruments
    if not scope_addr:
        print("\n⚠ WARNING: Oscilloscope not detected!")
        print("   Supported oscilloscopes:")
        print("     - Tektronix MSO/DPO/TDS series")
        print("     - Keysight DSOX/InfiniiVision series")

    if not load_addr:
        print("\n⚠ WARNING: Electronic load not detected!")
        print("   Supported electronic loads:")
        print("     - Keithley 2380 series")

    return scope_addr, load_addr


def main():
    """Test auto-detection"""
    print("=" * 70)
    print(" VISA INSTRUMENT AUTO-DETECTION TEST")
    print("=" * 70)

    instruments = detect_all_instruments(verbose=True)

    print("\n" + "=" * 70)
    print(" DETECTION SUMMARY")
    print("=" * 70)

    if instruments:
        print(f"\nFound {len(instruments)} instrument type(s):")
        for inst_type, info in instruments.items():
            print(f"\n  {inst_type.upper()}:")
            print(f"    Address:      {info.address}")
            print(f"    Manufacturer: {info.manufacturer}")
            print(f"    Model:        {info.model}")
            print(f"    Serial:       {info.serial}")
            print(f"    Firmware:     {info.firmware}")
    else:
        print("\n  No instruments detected!")
        print("\n  Troubleshooting:")
        print("    1. Verify instruments are powered on")
        print("    2. Check USB/GPIB connections")
        print("    3. Install NI-VISA or similar VISA driver")
        print("    4. Run: pip install pyvisa pyvisa-py")

    print("\n" + "=" * 70)

    return 0 if instruments else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
