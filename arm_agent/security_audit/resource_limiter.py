from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ResourceLimiter:
    single_file_quota: int = 3
    batch_file_quota: int = 10
    min_interval_seconds: float = 1.0
    _last_call: float = field(default=0.0, init=False)
    _used: int = field(default=0, init=False)

    def acquire(self, batch_size: int = 1) -> dict:
        quota = self.batch_file_quota if batch_size > 1 else self.single_file_quota
        if self._used >= quota:
            return {"status": "rate_limited", "quota": quota, "used": self._used, "retry_after_seconds": self.min_interval_seconds}
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_call = time.monotonic()
        self._used += 1
        return {"status": "acquired", "quota": quota, "used": self._used}

    def reset(self) -> None:
        self._used = 0
        self._last_call = 0.0
