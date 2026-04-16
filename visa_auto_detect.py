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
    load  = instruments['electronic_load']
"""

import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum


class InstrumentType(Enum):
    """Instrument type enumeration"""
    OSCILLOSCOPE    = "oscilloscope"
    ELECTRONIC_LOAD = "electronic_load"
    POWER_SUPPLY    = "power_supply"
    DMM             = "dmm"
    UNKNOWN         = "unknown"


@dataclass
class InstrumentInfo:
    """Information about a detected instrument"""
    address:         str
    instrument_type: InstrumentType
    manufacturer:    str
    model:           str
    serial:          str
    firmware:        str
    full_idn:        str

    def __str__(self):
        return f"{self.manufacturer} {self.model} ({self.instrument_type.value}) at {self.address}"


class VISAAutoDetector:
    """Automatic VISA instrument detection and identification"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._detected_instruments: List[InstrumentInfo] = []

    def detect_all_instruments(self) -> Dict[str, InstrumentInfo]:
        """
        Scan the VISA bus and identify all connected instruments.

        Returns:
            Dict mapping instrument type string to InstrumentInfo.
            Keys: 'oscilloscope', 'electronic_load', 'power_supply', 'dmm'
        """
        instruments: Dict[str, InstrumentInfo] = {}

        try:
            import pyvisa
        except ImportError:
            self._logger.error("PyVISA not installed. Run: pip install pyvisa pyvisa-py")
            return instruments

        try:
            rm        = pyvisa.ResourceManager()
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

            for resource in resources:
                try:
                    inst_info = self._identify_instrument(rm, resource)
                    if inst_info:
                        self._detected_instruments.append(inst_info)
                        type_key = inst_info.instrument_type.value
                        if type_key not in instruments:
                            instruments[type_key] = inst_info
                            print(f"  \u2713 {inst_info}")
                        else:
                            self._logger.info(f"Additional {type_key} found (using first): {inst_info}")
                            print(f"  \u2139 {inst_info} (duplicate, using first)")
                except Exception as e:
                    self._logger.debug(f"Failed to query {resource}: {e}")
                    print(f"  \u2717 {resource}: Unable to identify")

            print("-" * 70)
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
        """Open one VISA address and query *IDN? to identify the instrument."""
        try:
            inst         = rm.open_resource(address)
            inst.timeout = 3000
            idn          = inst.query("*IDN?").strip()
            inst.close()

            parts        = idn.split(',')
            manufacturer = parts[0].strip() if len(parts) > 0 else "Unknown"
            model        = parts[1].strip() if len(parts) > 1 else "Unknown"
            serial       = parts[2].strip() if len(parts) > 2 else "Unknown"
            firmware     = parts[3].strip() if len(parts) > 3 else "Unknown"
            inst_type    = self._classify_instrument(idn, manufacturer, model)

            return InstrumentInfo(
                address=address,
                instrument_type=inst_type,
                manufacturer=manufacturer,
                model=model,
                serial=serial,
                firmware=firmware,
                full_idn=idn,
            )
        except Exception as e:
            self._logger.debug(f"Failed to identify {address}: {e}")
            return None

    def _classify_instrument(self, idn: str, manufacturer: str, model: str) -> InstrumentType:
        """Classify instrument type from *IDN? response."""
        idn_upper = idn.upper()
        model_upper = model.upper()
        mfg_upper = manufacturer.upper()

        # Oscilloscope
        if any(s in idn_upper for s in [
            'MSO', 'DPO', 'TDS', 'MDO',                        # Tektronix
            'DSOX', 'DSO', 'MSOX', 'INFINIIUM', 'INFINIUM',    # Keysight
            'HDO', 'WRO', 'WP', 'MXO',                         # LeCroy/Teledyne
            'SDS',                                               # Siglent
        ]):
            return InstrumentType.OSCILLOSCOPE

        # Electronic load
        if '2380' in model_upper and 'KEITHLEY' in mfg_upper:
            return InstrumentType.ELECTRONIC_LOAD
        if any(s in idn_upper for s in ['ELECTRONIC LOAD']):
            return InstrumentType.ELECTRONIC_LOAD

        # Power supply
        if any(s in model_upper for s in [
            '2200', '2220', '2230', '2231', '2260', '2280', '2281',  # Keithley
            'E3600', 'E3610', 'E3620', 'E3630', 'E3640', 'E3649',    # Keysight
            'DP800', 'DP700', 'DP1000',                               # Rigol
        ]):
            return InstrumentType.POWER_SUPPLY
        if any(s in idn_upper for s in ['POWER SUPPLY', 'PROGRAMMABLE POWER', 'DC POWER']):
            return InstrumentType.POWER_SUPPLY

        # DMM
        if 'DMM6500' in model_upper or 'DMM7510' in model_upper:
            return InstrumentType.DMM
        if 'DMM' in idn_upper or 'MULTIMETER' in idn_upper:
            return InstrumentType.DMM

        return InstrumentType.UNKNOWN

    def list_all_detected(self) -> List[InstrumentInfo]:
        """Return every instrument found during the last scan (including duplicates)."""
        return self._detected_instruments


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience functions
# ─────────────────────────────────────────────────────────────────────────────

def detect_all_instruments(verbose: bool = False) -> Dict[str, InstrumentInfo]:
    """Run a full VISA bus scan and return a dict of found instruments."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    return VISAAutoDetector().detect_all_instruments()


def detect_load_transient_instruments() -> Tuple[Optional[str], Optional[str]]:
    """
    Detect instruments needed for the Load Transient test.

    Returns:
        (oscilloscope_address, electronic_load_address)
        Either value is None if that instrument was not found.
    """
    instruments = detect_all_instruments()
    scope_addr  = instruments.get('oscilloscope',    None)
    load_addr   = instruments.get('electronic_load', None)

    if scope_addr:
        scope_addr = scope_addr.address
    else:
        print("\n\u26a0 WARNING: Oscilloscope not detected!")
        print("   Supported: Tektronix MSO/DPO/TDS, Keysight DSOX/InfiniiVision")

    if load_addr:
        load_addr = load_addr.address
    else:
        print("\n\u26a0 WARNING: Electronic load not detected!")
        print("   Supported: Keithley 2380 series")

    return scope_addr, load_addr


def detect_input_range_ovp_instruments() -> Tuple[Optional[str], Optional[str]]:
    """
    Detect instruments needed for the Input Range / OVP test.

    Returns:
        (psu_address, dmm_address)
        Either value is None if that instrument was not found.
    """
    instruments = detect_all_instruments()
    psu_info    = instruments.get('power_supply', None)
    dmm_info    = instruments.get('dmm',          None)

    psu_addr = psu_info.address if psu_info else None
    dmm_addr = dmm_info.address if dmm_info else None

    if not psu_addr:
        print("\n\u26a0 WARNING: Power supply not detected!")
        print("   Supported: Keithley 2230 / 2280 series")

    if not dmm_addr:
        print("\n\u26a0 WARNING: DMM not detected!")
        print("   Supported: Keithley DMM6500 / DMM7510")

    return psu_addr, dmm_addr


def detect_power_sequencing_instruments() -> Tuple[Optional[str], Optional[str]]:
    """
    Detect instruments needed for the Power Sequencing test.

    Returns:
        (psu_address, scope_address)
        Either value is None if that instrument was not found.
    """
    instruments = detect_all_instruments()
    psu_info    = instruments.get('power_supply',  None)
    scope_info  = instruments.get('oscilloscope',  None)

    psu_addr   = psu_info.address   if psu_info   else None
    scope_addr = scope_info.address if scope_info else None

    if not psu_addr:
        print("\n\u26a0 WARNING: Power supply not detected!")
        print("   Supported: Keithley 2230 / 2280 series")

    if not scope_addr:
        print("\n\u26a0 WARNING: Oscilloscope not detected!")
        print("   Supported: Tektronix MSO/DPO/TDS, Keysight DSOX/InfiniiVision")

    return psu_addr, scope_addr


def detect_steady_state_ripple_instruments() -> Tuple[Optional[str]]:
    """
    Detect instruments needed for the Steady-State Ripple test.

    Returns:
        (scope_address,)
        Value is None if the oscilloscope was not found.
    """
    instruments = detect_all_instruments()
    scope_info  = instruments.get('oscilloscope', None)
    scope_addr  = scope_info.address if scope_info else None

    if not scope_addr:
        print("\n\u26a0 WARNING: Oscilloscope not detected!")
        print("   Supported: Tektronix MSO/DPO/TDS, Keysight DSOX/InfiniiVision")

    return (scope_addr,)


# ─────────────────────────────────────────────────────────────────────────────
# Standalone entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Run a standalone detection scan and print a full report."""
    print("=" * 70)
    print(" VISA INSTRUMENT AUTO-DETECTION")
    print("=" * 70)

    instruments = detect_all_instruments(verbose=True)

    print("\n" + "=" * 70)
    print(" DETECTION SUMMARY")
    print("=" * 70)

    if instruments:
        print(f"\nFound {len(instruments)} instrument type(s):\n")
        for inst_type, info in instruments.items():
            print(f"  {inst_type.upper()}:")
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
