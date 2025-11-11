"""Helpers for interacting with the QRZ Logbook API."""
from __future__ import annotations

import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional
from urllib.parse import parse_qs

__all__ = [
    "QRZClient",
    "QRZLookupError",
    "QRZAuthenticationError",
    "QRZNotFoundError",
]

LOGGER = logging.getLogger(__name__)
QRZ_API_URL = "https://logbook.qrz.com/api"
_USER_AGENT_TEMPLATE = "HamRadioMapper/{version}"
_DEFAULT_VERSION = "1.0"
_ADIF_FIELD_RE = re.compile(r"<([^:>]+):(\d+)(?::[^>]*)?>", re.IGNORECASE)


class QRZLookupError(RuntimeError):
    """Base error for QRZ lookups."""


class QRZAuthenticationError(QRZLookupError):
    """Raised when the QRZ API reports insufficient privileges."""


class QRZNotFoundError(QRZLookupError):
    """Raised when the QRZ API does not return a matching record."""


@dataclass(frozen=True)
class HTTPResponse:
    """Minimal representation of an HTTP response."""

    status_code: int
    text: str


@dataclass(frozen=True)
class QRZRecord:
    """Represents a single record returned by the QRZ logbook."""

    fields: Dict[str, str]

    def get(self, field: str, default: Optional[str] = None) -> Optional[str]:
        """Return a field from the record using case-insensitive lookups."""

        return self.fields.get(field.lower(), default)


class QRZClient:
    """Client for retrieving information from the QRZ Logbook API."""

    def __init__(
        self,
        api_key: str,
        *,
        user_agent: Optional[str] = None,
        http_post: Optional[Callable[[str, Dict[str, str], Dict[str, str], float], HTTPResponse]] = None,
        version: str = _DEFAULT_VERSION,
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("An API key is required to use the QRZ client.")

        self._api_key = api_key
        self._user_agent = user_agent or _USER_AGENT_TEMPLATE.format(version=version)
        self._http_post = http_post or _default_http_post
        self._timeout = timeout

    def lookup_callsign(self, callsign: str) -> QRZRecord:
        """Fetch the first log entry for the given callsign."""

        LOGGER.debug("Looking up callsign '%s' via QRZ", callsign)
        data = {
            "KEY": self._api_key,
            "ACTION": "FETCH",
            "OPTION": f"CALL:{callsign}",
            "TYPE": "ADIF",
            "MAX": "1",
        }
        response = self._http_post(
            QRZ_API_URL,
            data=data,
            headers={"User-Agent": self._user_agent},
            timeout=self._timeout,
        )
        LOGGER.debug("QRZ response status: %s", response.status_code)
        if response.status_code >= 400:
            raise QRZLookupError(f"QRZ request failed with status {response.status_code}.")

        payload = _parse_response_body(response.text)
        result = payload.get("RESULT", "")
        LOGGER.debug("QRZ result: %s", result)

        if result == "AUTH":
            raise QRZAuthenticationError("QRZ API authentication failed for the provided key.")
        if result != "OK":
            reason = payload.get("REASON", "Unknown error")
            raise QRZLookupError(f"QRZ lookup failed: {reason}")

        adif_data = payload.get("ADIF")
        LOGGER.debug("QRZ returned ADIF length: %s", len(adif_data) if adif_data else 0)
        if not adif_data:
            raise QRZNotFoundError(f"No QRZ record found for callsign '{callsign}'.")

        records = list(_parse_adif_records(adif_data))
        if not records:
            raise QRZNotFoundError(f"No QRZ record found for callsign '{callsign}'.")

        return records[0]

    def lookup_callsign_country(self, callsign: str) -> str:
        """Return the operating country for a callsign using the QRZ API."""

        record = self.lookup_callsign(callsign)
        country = record.get("country")
        if not country:
            raise QRZLookupError(
                f"The QRZ record for callsign '{callsign}' did not include a country field."
            )
        return country


def _parse_response_body(body: str) -> Dict[str, str]:
    """Parse the QRZ response body into a dictionary."""

    parsed = parse_qs(body, keep_blank_values=True, strict_parsing=False)
    return {key: values[0] for key, values in parsed.items()}


def _parse_adif_records(adif: str) -> Iterable[QRZRecord]:
    """Yield records parsed from an ADIF payload."""

    lower_adif = adif.lower()
    cursor = 0
    length = len(adif)

    while cursor < length:
        eor_index = lower_adif.find("<eor>", cursor)
        if eor_index == -1:
            segment = adif[cursor:]
            cursor = length
        else:
            segment = adif[cursor:eor_index]
            cursor = eor_index + 5

        fields = _parse_adif_segment(segment)
        if fields:
            yield QRZRecord(fields)


def _parse_adif_segment(segment: str) -> Dict[str, str]:
    """Parse a single ADIF segment into a mapping of field names to values."""

    fields: Dict[str, str] = {}
    for match in _ADIF_FIELD_RE.finditer(segment):
        field_name = match.group(1).lower()
        field_length = int(match.group(2))
        value_start = match.end()
        value_end = value_start + field_length
        if value_end > len(segment):
            LOGGER.debug("Skipping malformed ADIF field '%s'", field_name)
            continue
        fields[field_name] = segment[value_start:value_end]
    return fields


def _default_http_post(
    url: str,
    *,
    data: Dict[str, str],
    headers: Dict[str, str],
    timeout: float,
) -> HTTPResponse:
    """Send a POST request using urllib and return an :class:`HTTPResponse`."""

    encoded_data = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(url, data=encoded_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            status_code = response.getcode()
    except urllib.error.HTTPError as exc:  # pragma: no cover - exercised only on network errors
        body = exc.read().decode("utf-8", errors="replace")
        status_code = exc.code
    return HTTPResponse(status_code=status_code, text=body)
