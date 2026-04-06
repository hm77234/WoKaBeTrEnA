from conftest import TEST_STUDENT

def test_app_functionality_add_user(logged_in_client):   
    """test user after restored from database"""

    post_resp = logged_in_client.get("/admin/users")
    assert post_resp.status_code == 200
    assert TEST_STUDENT in post_resp.text