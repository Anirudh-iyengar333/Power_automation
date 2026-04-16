"""
Compatibility shim — re-exports everything from the shared visa_auto_detect
module at the project root.  Do not add logic here.
"""
import sys
from pathlib import Path

# Ensure project root is on the path so the real module can be found
_ROOT = str(Path(__file__).parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from visa_auto_detect import (   # noqa: F401, F403  (re-export)
    InstrumentType,
    InstrumentInfo,
    VISAAutoDetector,
    detect_all_instruments,
    detect_load_transient_instruments,
    detect_input_range_ovp_instruments,
    detect_power_sequencing_instruments,
    detect_steady_state_ripple_instruments,
)
