"""Logic for deriving the operating country of a contact."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

DOMESTIC_COUNTRY_CODES = {"US", "CA", "MX"}


class CallsignLookup(Protocol):
    """Protocol describing the methods required to look up a callsign."""

    def lookup_callsign_country(self, callsign: str) -> str:
        """Return the operating country for a callsign."""


@dataclass(frozen=True)
class Contact:
    """Basic representation of a radio contact."""

    callsign: str
    reported_country: str | None = None
    reported_country_code: str | None = None


def determine_operating_country(contact: Contact, lookup: CallsignLookup) -> str:
    """Determine the operating country for a contact.

    If the contact originated from the United States, Canada, or Mexico and the contact
    payload already contains a country name, that value is returned immediately. For all
    other countries the function defers to the provided QRZ lookup implementation.
    """

    country_code = (contact.reported_country_code or "").upper()
    if country_code in DOMESTIC_COUNTRY_CODES and contact.reported_country:
        return contact.reported_country

    if not contact.callsign:
        raise ValueError("A callsign is required to resolve the operating country.")

    country = lookup.lookup_callsign_country(contact.callsign)
    return country


__all__: Iterable[str] = [
    "Contact",
    "DOMESTIC_COUNTRY_CODES",
    "determine_operating_country",
]
