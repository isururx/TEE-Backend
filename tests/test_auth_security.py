import app.core.security as security

def test_argon2_password_hash_round_trip():
    hashed = security.hash_password('StrongPass123')
    assert hashed.startswith('$argon2id$')
    assert security.verify_password('StrongPass123', hashed)
    assert not security.verify_password('WrongPass123', hashed)

def test_legacy_plaintext_password_is_verified_for_migration():
    assert security.verify_password('LegacyPass123', 'LegacyPass123')
    assert not security.verify_password('WrongPass123', 'LegacyPass123')

def test_access_token_contains_expected_identity(monkeypatch):
    monkeypatch.setattr(security, 'SECRET_KEY', 'test-secret-key-with-at-least-32-characters')
    token = security.create_access_token(user_id=42, role='manager')
    payload = security.decode_access_token(token)
    assert payload['sub'] == '42'
    assert payload['role'] == 'manager'
    assert payload['type'] == 'access'
