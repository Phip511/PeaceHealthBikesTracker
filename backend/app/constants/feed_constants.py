"""File: feed_constants.py

Purpose:
    Defines default configuration values for GBFS feed collection.

System context:
    This file is part of the PeaceHealth Rides Availability and Navigation
    Dashboard backend. The ride feed collector imports these values so that
    feed URLs and timeout defaults are not hard-coded inside the service logic.

Creation date:
    May 29, 2026

Initial author:
    Drew Moulton

Modification history:
    May 29, 2026 - Drew Moulton - Created the constants module for the ride
    feed collector defaults.
"""


# Default GBFS auto-discovery endpoint used when no environment override or
# constructor argument provides a feed index URL.
DEFAULT_GBFS_AUTO_DISCOVERY_URL = "https://peacehealthrides.com/opendata/gbfs.json"

# Default network timeout, in seconds, for live GBFS HTTP requests. The value is
# intentionally short so a failed live feed does not block fallback behavior.
DEFAULT_FEED_TIMEOUT_SECONDS = 5.0
