from collections.abc import Callable
from typing import Any


class KafkaHealthProbe:
    def __init__(self, probe: Callable[[], dict[str, Any]]) -> None:
        self._probe = probe

    def probe(self) -> dict[str, Any]:
        return self._probe()
