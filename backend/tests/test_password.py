from app.security import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    stored = hash_password("abc123", iterations=1000)
    assert stored.startswith("pbkdf2_sha256$1000$")
    assert verify_password("abc123", stored)
    assert not verify_password("outra", stored)


def test_same_password_gets_different_salts():
    assert hash_password("abc123", iterations=1000) != hash_password("abc123", iterations=1000)


def test_malformed_hash_is_rejected_not_crashed():
    assert not verify_password("abc123", "isto-nao-e-um-hash")
    assert not verify_password("abc123", "md5$1$00$00")
