import pytest

from app.domain.exceptions import UnsafeURL
from app.domain.services.ssrf import assert_safe_url, is_unsafe_address


def test_is_unsafe_address():
    assert is_unsafe_address("127.0.0.1")
    assert is_unsafe_address("10.0.0.1")
    assert is_unsafe_address("192.168.1.1")
    assert is_unsafe_address("169.254.169.254")
    assert is_unsafe_address("::1")
    assert not is_unsafe_address("8.8.8.8")
    assert not is_unsafe_address("93.184.216.34")


async def test_literal_private_ip_blocked():
    with pytest.raises(UnsafeURL):
        await assert_safe_url("http://127.0.0.1/")


async def test_literal_metadata_ip_blocked():
    with pytest.raises(UnsafeURL):
        await assert_safe_url("http://169.254.169.254/latest/meta-data/")


async def test_literal_public_ip_allowed():
    assert await assert_safe_url("http://8.8.8.8/") == "http://8.8.8.8/"


async def test_unsupported_scheme_blocked():
    with pytest.raises(UnsafeURL):
        await assert_safe_url("ftp://example.com/")


async def test_hostname_resolving_to_private_blocked():
    async def resolver(host):
        return ["10.0.0.5"]

    with pytest.raises(UnsafeURL):
        await assert_safe_url("http://internal.example/", resolver=resolver)


async def test_hostname_resolving_to_public_allowed():
    async def resolver(host):
        return ["93.184.216.34"]

    assert await assert_safe_url("http://example.com/", resolver=resolver) == "http://example.com/"


async def test_allowed_hosts_bypass_resolution():
    async def resolver(host):
        return ["10.0.0.5"]

    assert (
        await assert_safe_url("http://api/", allowed_hosts=frozenset({"api"}), resolver=resolver)
        == "http://api/"
    )


async def test_allow_private_bypasses_check():
    async def resolver(host):
        return ["10.0.0.5"]

    assert (
        await assert_safe_url("http://internal/", allow_private=True, resolver=resolver)
        == "http://internal/"
    )
