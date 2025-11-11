import pytest

from hamradio.qrz_lookup import (
    HTTPResponse,
    QRZAuthenticationError,
    QRZClient,
    QRZLookupError,
    QRZNotFoundError,
)


def make_client(response_body: str, status_code: int = 200) -> QRZClient:
    def fake_post(url, *, data, headers, timeout):
        return HTTPResponse(status_code=status_code, text=response_body)

    return QRZClient("test-key", http_post=fake_post)


def test_lookup_returns_country():
    response_body = (
        "RESULT=OK&COUNT=1&ADIF="
        "<call:5>LU8AE<country:9>Argentina<state:2>BA<eor>"
    )
    client = make_client(response_body)

    country = client.lookup_callsign_country("LU8AE")

    assert country == "Argentina"


def test_lookup_handles_missing_country():
    response_body = "RESULT=OK&COUNT=1&ADIF=<call:5>LU8AE<eor>"
    client = make_client(response_body)

    with pytest.raises(QRZLookupError):
        client.lookup_callsign_country("LU8AE")


def test_lookup_handles_auth():
    response_body = "RESULT=AUTH&REASON=Not authorized"
    client = make_client(response_body)

    with pytest.raises(QRZAuthenticationError):
        client.lookup_callsign_country("LU8AE")


def test_lookup_handles_fail():
    response_body = "RESULT=FAIL&REASON=Bad request"
    client = make_client(response_body)

    with pytest.raises(QRZLookupError):
        client.lookup_callsign_country("LU8AE")


def test_lookup_handles_missing_records():
    response_body = "RESULT=OK&COUNT=0&ADIF="
    client = make_client(response_body)

    with pytest.raises(QRZNotFoundError):
        client.lookup_callsign_country("LU8AE")


def test_lookup_handles_http_error():
    client = make_client("RESULT=OK", status_code=500)

    with pytest.raises(QRZLookupError):
        client.lookup_callsign_country("LU8AE")
