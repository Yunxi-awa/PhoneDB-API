import dataclasses

from curl_cffi.requests.session import BaseSessionParams, Response


@dataclasses.dataclass
class SessionConfig:
    max_retries: int = 3
    delay_ms: float = 3000  # ms
    kwargs: dict = dataclasses.field(default_factory=dict)
