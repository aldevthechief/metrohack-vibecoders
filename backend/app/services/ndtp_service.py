"""TCP receiver for the emulator's unencrypted NDTP 6.2 packets."""

import asyncio
import logging
import struct
from contextlib import suppress
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.telemetry import TelemetryPoint
from app.services.processing_service import ProcessingService


LOG = logging.getLogger(__name__)
MOSCOW = ZoneInfo("Europe/Moscow")
NPL_SIZE = 15
NPH_SIZE = 10
NAV_SIZE = 26


class NdtpProtocolError(ValueError):
    pass


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc


def _swapped(value: int) -> int:
    return ((value & 0xFF) << 8) | (value >> 8)


def decode_frame(header: bytes, payload: bytes) -> tuple[int, int, TelemetryPoint | None]:
    """Return (unit_id, NPH type, navigation); handshake has no navigation."""
    if len(header) != NPL_SIZE or len(payload) < NPH_SIZE:
        raise NdtpProtocolError("Incomplete NDTP frame")
    signature, data_size, flags, stored_crc, frame_type, unit_id, _ = struct.unpack(
        "<HHHHBIH", header
    )
    if signature != 0x7E7E or frame_type != 2 or flags != 0:
        raise NdtpProtocolError("Unsupported NDTP header")
    if data_size != len(payload):
        raise NdtpProtocolError("NDTP frame size mismatch")
    if stored_crc != _swapped(crc16_modbus(payload)):
        raise NdtpProtocolError("Invalid NDTP CRC")

    service_id, message_type, _, request_id = struct.unpack_from("<HHHI", payload)
    body = payload[NPH_SIZE:]
    if (service_id, message_type) == (0, 100):
        if len(body) != 18:
            raise NdtpProtocolError("Invalid NDTP handshake length")
        major, minor, _, peer_address, _, _ = struct.unpack("<HHHIII", body)
        if (major, minor) != (6, 2) or peer_address != unit_id:
            raise NdtpProtocolError("Invalid NDTP handshake")
        return unit_id, message_type, None

    if (service_id, message_type) != (1, 101):
        raise NdtpProtocolError("Unsupported NDTP message")
    if len(body) < 2 + NAV_SIZE or body[0:2] != b"\x00\x00":
        raise NdtpProtocolError("First realtime cell must be G6CellNav00")

    (timestamp, longitude, latitude, nav_flags, _, speed, _, heading,
     _, altitude, _, _) = struct.unpack_from("<IIIBBHHHHHBB", body, 2)
    event_time = datetime.fromtimestamp(timestamp, MOSCOW).replace(tzinfo=None)
    receive_time = datetime.now(MOSCOW).replace(tzinfo=None)
    lon = longitude / 10_000_000 * (1 if nav_flags & 0x40 else -1)
    lat = latitude / 10_000_000 * (1 if nav_flags & 0x20 else -1)
    valid = bool(nav_flags & 0x80) and -180 <= lon <= 180 and -90 <= lat <= 90
    valid = valid and lon != 0 and lat != 0

    telemetry = TelemetryPoint(
        packet_id=f"{unit_id}:{request_id}:{timestamp}",
        tr_id=str(unit_id),
        unit_id=str(unit_id),
        event_time=event_time,
        gps_time=event_time,
        receive_time=receive_time,
        speed=float(speed),
        heading=float(heading),
        altitude=float(altitude),
        location_valid=valid,
        longitude=lon if valid else None,
        latitude=lat if valid else None,
    )
    return unit_id, message_type, telemetry


class NdtpServer:
    def __init__(self, processing_service: ProcessingService, host: str, port: int) -> None:
        self._processing_service = processing_service
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None
        self._unit_map: dict[int, str] = {}
        self._clients: set[asyncio.StreamWriter] = set()
        self.connected_clients = 0
        self.received_packets = 0
        self.predictions_updated = 0
        self.rejected_frames = 0
        self.processing_errors = 0

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]
        LOG.info("NDTP TCP listening on %s:%s", self.host, self.port)

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        for writer in tuple(self._clients):
            writer.close()
        for writer in tuple(self._clients):
            with suppress(ConnectionError, OSError):
                await writer.wait_closed()

    def register_unit(self, unit_id: int, tr_id: str) -> None:
        self._unit_map[unit_id] = tr_id

    def status(self) -> dict:
        return {
            "listening": self._server is not None,
            "host": self.host,
            "port": self.port,
            "connected_clients": self.connected_clients,
            "received_packets": self.received_packets,
            "predictions_updated": self.predictions_updated,
            "rejected_frames": self.rejected_frames,
            "processing_errors": self.processing_errors,
            "unit_map": self._unit_map.copy(),
        }

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.connected_clients += 1
        self._clients.add(writer)
        bound_unit: int | None = None
        try:
            while True:
                header = await reader.readexactly(NPL_SIZE)
                data_size = struct.unpack_from("<H", header, 2)[0]
                if (header[:2] != b"~~" or header[8] != 2
                        or struct.unpack_from("<H", header, 4)[0] != 0
                        or data_size < NPH_SIZE):
                    raise NdtpProtocolError("Invalid NDTP frame header")
                payload = await reader.readexactly(data_size)
                unit_id, message_type, telemetry = decode_frame(header, payload)

                if bound_unit is None:
                    if message_type != 100:
                        raise NdtpProtocolError("NDTP handshake required")
                    bound_unit = unit_id
                    continue
                if unit_id != bound_unit or message_type != 101 or telemetry is None:
                    raise NdtpProtocolError("Unexpected NDTP frame after handshake")

                telemetry.tr_id = self._unit_map.get(unit_id, str(unit_id))
                self.received_packets += 1
                try:
                    incident = await self._processing_service.process_telemetry(telemetry)
                    if incident is not None:
                        self.predictions_updated += 1
                except Exception:
                    self.processing_errors += 1
                    LOG.exception("Could not process NDTP telemetry for unit %s", unit_id)
        except asyncio.IncompleteReadError:
            pass
        except NdtpProtocolError as error:
            self.rejected_frames += 1
            LOG.warning("Rejected NDTP client %s: %s", writer.get_extra_info("peername"), error)
        finally:
            self.connected_clients -= 1
            self._clients.discard(writer)
            writer.close()
            with suppress(ConnectionError, OSError):
                await writer.wait_closed()
