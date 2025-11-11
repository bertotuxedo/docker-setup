import pytest

from hamradio.country_resolver import Contact, determine_operating_country


class DummyLookup:
    def __init__(self, country: str = "Argentina") -> None:
        self.country = country
        self.calls = []

    def lookup_callsign_country(self, callsign: str) -> str:
        self.calls.append(callsign)
        return self.country


def test_domestic_contact_returns_reported_country():
    contact = Contact(callsign="K1ABC", reported_country="United States", reported_country_code="US")
    lookup = DummyLookup()

    result = determine_operating_country(contact, lookup)

    assert result == "United States"
    assert lookup.calls == []


def test_dx_contact_triggers_qrz_lookup():
    contact = Contact(callsign="LU8AE", reported_country=None, reported_country_code="AR")
    lookup = DummyLookup(country="Argentina")

    result = determine_operating_country(contact, lookup)

    assert result == "Argentina"
    assert lookup.calls == ["LU8AE"]


def test_missing_callsign_raises_error():
    contact = Contact(callsign="", reported_country=None, reported_country_code="AR")
    lookup = DummyLookup()

    with pytest.raises(ValueError):
        determine_operating_country(contact, lookup)
