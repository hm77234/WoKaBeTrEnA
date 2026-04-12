from conftest import TEST_STUDENT

def test_app_functionality_check_word_save_by_selenium_test(logged_in_client):   
    """test if word is safed by selenium test"""
    resp = logged_in_client.get("/wordgroups/words/deutsch-spanisch", follow_redirects=True)
    assert resp.status_code == 200
    assert "saved by selenium" in resp.text
    assert "_EDIT" in resp.text
