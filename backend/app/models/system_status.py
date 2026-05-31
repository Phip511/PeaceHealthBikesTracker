from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FeedStatus:
    feed_name: str
    available: bool
    source_type: str
    last_updated: Optional[int]
    error_message: Optional[str] = None


@dataclass
class SystemStatus:
    status: str
    source: str
    source_label: str
    using_live_data: bool
    using_cached_data: bool
    using_sample_data: bool
    live_feed_available: bool
    cache_data_available: bool
    sample_data_available: bool
    last_successful_update: Optional[int]
    visible_message: str
    feeds: List[FeedStatus]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
