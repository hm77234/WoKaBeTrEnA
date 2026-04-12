from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from conftest import BASE_URL, TEST_STUDENT, DB_NAME
#
import time




def test_app_functionality_restorbackup(logged_in_client_session, logged_in_driver, backup_filename):
    logged_in_driver
    wait = WebDriverWait(logged_in_driver, 25)

    logged_in_driver.get(BASE_URL + "/admin/restore-db")
    time.sleep(3) #sometimes restore is not present
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

   