"""
Shadow CLI - Integration Package
External data import: health, reading, browser activity.
"""

from .health import (
    import_health_csv,
    import_health_export,
    import_health_json,
    get_health_summary,
    record_health_manual,
)
from .reading import (
    import_reading_csv,
    import_reading_json,
    get_reading_summary,
    record_reading_manual,
)
from .browser_bridge import (
    import_browser_data,
    get_browser_summary,
    record_browser_manual,
)

__all__ = [
    "import_health_json",
    "import_health_csv",
    "import_health_export",
    "record_health_manual",
    "get_health_summary",
    "import_reading_json",
    "import_reading_csv",
    "record_reading_manual",
    "get_reading_summary",
    "import_browser_data",
    "record_browser_manual",
    "get_browser_summary",
]
