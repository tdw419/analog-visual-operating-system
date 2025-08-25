from typing import Dict, Any
import hashlib
import json
from event_bus import EventBus

class DataModel:
    def __init__(self, event_bus: EventBus):
        self._state: Dict[str, Any] = {}
        self._cache: Dict[str, Any] = {}
        self._event_bus = event_bus

    def _calculate_hash(self, data: Any) -> str:
        """Calculates a hash for any JSON-serializable data."""
        serialized_data = json.dumps(data, sort_keys=True).encode('utf-8')
        return hashlib.sha256(serialized_data).hexdigest()

    def get(self, key: str) -> Any:
        return self._state.get(key)

    async def set(self, key: str, value: Any, use_cache: bool = False) -> None:
        if use_cache:
            data_hash = self._calculate_hash(value)
            if self._cache.get(key) == data_hash:
                # Data is the same as cached, no update needed
                return
            self._cache[key] = data_hash

        self._state[key] = value
        await self._event_bus.publish(f"data_changed:{key}", value)
        await self._event_bus.publish("data_changed", {key: value})

    def get_all(self) -> Dict[str, Any]:
        return self._state.copy()
