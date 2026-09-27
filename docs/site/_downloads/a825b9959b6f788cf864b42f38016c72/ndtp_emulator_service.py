"""Keep the optional NDTP emulator configured after container restarts."""

import asyncio
import logging

import httpx


LOG = logging.getLogger(__name__)


def _unit_settings(units: list[dict]) -> set[tuple[int, int, bool]]:
    return {
        (unit["unitId"], unit["intervalMs"], bool(unit.get("autoGenerate")))
        for unit in units
    }


async def maintain_emulator(url: str, config: dict) -> None:
    endpoint = f"{url.rstrip('/')}/api/config"
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                response = await client.get(endpoint)
                response.raise_for_status()
                current = response.json()
                current_units = _unit_settings(current.get("units") or []) if isinstance(current, dict) else set()
                desired_units = _unit_settings(config["units"])
                if (
                    not isinstance(current, dict)
                    or current.get("targetHost") != config["targetHost"]
                    or current.get("targetPort") != config["targetPort"]
                    or current_units != desired_units
                ):
                    configured = await client.post(endpoint, json=config)
                    configured.raise_for_status()
                    LOG.info("Configured NDTP emulator with %s units", len(desired_units))
                await asyncio.sleep(15)
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
                LOG.warning("NDTP emulator is not ready: %s", error)
                await asyncio.sleep(3)
