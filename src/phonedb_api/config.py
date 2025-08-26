import dataclasses
from typing import Optional


@dataclasses.dataclass
class SessionConfig:
    max_retries: int = 3
    delay_ms: float = 3000  # ms
    kwargs: Optional[dict] = None
