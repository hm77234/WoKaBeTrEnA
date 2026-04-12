from conftest import TEST_STUDENT

def test_app_functionality_check_user_from_backup(logged_in_client):   
    """test user after restored from database"""

    post_resp = logged_in_client.get("/admin/users")
    assert post_resp.status_code == 200
    assert TEST_STUDENT in post_resp.text
    post_resp = logged_in_client.get("/admin/users")
    