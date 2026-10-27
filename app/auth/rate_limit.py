import math
import time
from collections import deque
from threading import Lock

from fastapi import HTTPException, Request

from app.auth.config import AuthSettings


class LoginLimiter:
    """Per-process sliding window; no trust in client-supplied proxy headers."""

    def __init__(self, max_clients: int = 10000):
        self._attempts: dict[str, deque[float]] = {}
        self._lock = Lock()
        self._max_clients = max_clients

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()

    def check(self, request: Request, settings: AuthSettings) -> None:
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        cutoff = now - settings.login_window_seconds
        with self._lock:
            for key, attempts in list(self._attempts.items()):
                while attempts and attempts[0] <= cutoff:
                    attempts.popleft()
                if not attempts:
                    del self._attempts[key]
            attempts = self._attempts.get(client)
            if attempts is None:
                if len(self._attempts) >= self._max_clients:
                    self._reject(settings.login_window_seconds)
                attempts = self._attempts[client] = deque()
            if len(attempts) >= settings.login_max_attempts:
                self._reject(max(1, math.ceil(attempts[0] + settings.login_window_seconds - now)))
            attempts.append(now)

    @staticmethod
    def _reject(retry_after: int) -> None:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
            headers={"Retry-After": str(retry_after)},
        )


login_limiter = LoginLimiter()
