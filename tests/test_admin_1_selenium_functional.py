from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from conftest import BASE_URL, TEST_STUDENT, DB_NAME
from bs4 import BeautifulSoup

def test_app_functionality_delete_user(logged_in_client, logged_in_driver):   
    """Add User"""
    resp = logged_in_client.get("/")
    assert resp.status_code == 200
    assert "Admin Dashboard" in resp.text
    resp = logged_in_client.get("/admin/users", follow_redirects=True)
    # soup = BeautifulSoup(resp.text, "html.parser")
    # # Sucht nach <input name="csrf_token" value="...">
    # csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    # assert csrf_token is not None   
    assert TEST_STUDENT in resp.text
    
    logged_in_driver.get(BASE_URL + "/admin/users")
    wait = WebDriverWait(logged_in_driver, 15)

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

    # delete_link = wait.until(
    #     EC.presence_of_element_located((
    #         By.XPATH,
    #         "//tr[td[normalize-space()='teststudent']]//a[contains(@href, '/admin/delete/teststudent')]"
    #     ))
    # )

    logged_in_driver.find_element(
        By.CSS_SELECTOR, 'a[href="/admin/delete/' + TEST_STUDENT +'"]'
    ).click()

    alert = wait.until(EC.alert_is_present())
    assert alert.text == "Löschen?"
    alert.accept()
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    assert "teststudent" not in logged_in_driver.page_source
    


def test_app_functionality_restorbackup(logged_in_client_session, logged_in_driver, backup_filename):
    logged_in_driver
    wait = WebDriverWait(logged_in_driver, 10)

    logged_in_driver.get(BASE_URL + "/admin/restore-db")

    select_elem = wait.until(
        EC.presence_of_element_located((By.NAME, "backup_file"))
    )
    select_box = Select(select_elem)

    # Sicherstellen, dass der Wert im Select vorkommt
    options = [o.get_attribute("value") for o in select_box.options]
    assert DB_NAME + backup_filename in options, f"{backup_filename} nicht in {options}"

    select_box.select_by_value(DB_NAME + backup_filename)

    selected_value = select_box.first_selected_option.get_attribute("value")
    assert selected_value == DB_NAME + backup_filename

    submit_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
    )
    submit_btn.click()

    alert = wait.until(EC.alert_is_present())
    assert "WIRKLICH" in alert.text
    alert.accept()

    wait.until(EC.url_contains("/admin/restore-db")) 
    assert f"DB wiederhergestellt aus: {DB_NAME}{backup_filename}" in logged_in_driver.page_source

   