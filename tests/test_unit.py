# tests/test_unit.py
import pytest
from difflib import SequenceMatcher

@pytest.mark.unit
def test_similarity():
    def similarity(a, b):  # INLINE! Kein utils.py nötig
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    assert similarity("Hallo", "Hallo") == 1.0
    assert similarity("Hallo", "hello") > 0.5
    assert similarity("Hallo", "xyz") < 0.5

@pytest.mark.unit
def test_password_hashing():
    from werkzeug.security import generate_password_hash, check_password_hash
    user = type("User", (), {"username": "test"})()
    user.set_password = lambda pw: setattr(user, "password_hash", generate_password_hash(pw))
    user.check_password = lambda pw: check_password_hash(user.password_hash, pw)
    
    user.set_password("secret")
    assert user.check_password("secret") is True
    assert user.check_password("wrong") is False

