# tests/test_app.py
def test_index_redirect(api_client):
    """Testet, ob die Index-Seite auf Login umleitet (302)."""
    resp = api_client.get('/')
    assert resp.status_code == 302
    # Optional: Prüfen, ob er zum Login schickt
    assert "login" in resp.headers.get("Location", "").lower()
