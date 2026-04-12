from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from conftest import BASE_URL, TEST_STUDENT, DB_NAME
from bs4 import BeautifulSoup
import time



from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from conftest import BASE_URL


def test_app_functionality_edit_cancel_word(logged_in_client, logged_in_driver):
    page_url = "/wordgroups/words/deutsch-spanisch"

    resp = logged_in_client.get(page_url, follow_redirects=True)
    assert resp.status_code == 200
    assert "<table" in resp.text

    logged_in_driver.get(BASE_URL + page_url)
    wait = WebDriverWait(logged_in_driver, 15)

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    first_row = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr")))

    orig_mutter = first_row.find_element(By.CSS_SELECTOR, ".mutter-cell").text.strip()
    orig_foreign = first_row.find_element(By.CSS_SELECTOR, ".foreign-cell").text.strip()
    orig_info = first_row.find_element(By.CSS_SELECTOR, ".info-cell").text.strip()

    # Cancel prüfen
    first_row.find_element(By.CSS_SELECTOR, ".edit-btn").click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr .mutter-cell input")))

    first_row.find_element(By.CSS_SELECTOR, ".mutter-cell input").clear()
    first_row.find_element(By.CSS_SELECTOR, ".mutter-cell input").send_keys(orig_mutter + "_X")
    first_row.find_element(By.CSS_SELECTOR, ".foreign-cell input").clear()
    first_row.find_element(By.CSS_SELECTOR, ".foreign-cell input").send_keys(orig_foreign + "_Y")
    first_row.find_element(By.CSS_SELECTOR, ".info-cell input").clear()
    first_row.find_element(By.CSS_SELECTOR, ".info-cell input").send_keys("changed by selenium")

    first_row.find_element(By.CSS_SELECTOR, ".cancel-btn").click()

    wait.until(lambda d: d.find_element(By.CSS_SELECTOR, "tbody tr .mutter-cell").text.strip() == orig_mutter)

    first_row = d_first_row = logged_in_driver.find_element(By.CSS_SELECTOR, "tbody tr")
    assert d_first_row.find_element(By.CSS_SELECTOR, ".mutter-cell").text.strip() == orig_mutter
    assert d_first_row.find_element(By.CSS_SELECTOR, ".foreign-cell").text.strip() == orig_foreign
    assert d_first_row.find_element(By.CSS_SELECTOR, ".info-cell").text.strip() == orig_info
    assert d_first_row.find_element(By.CSS_SELECTOR, ".edit-btn")
    assert d_first_row.find_element(By.CSS_SELECTOR, ".btn-group-assign")

    # Save prüfen
    d_first_row.find_element(By.CSS_SELECTOR, ".edit-btn").click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr .mutter-cell input")))

    new_mutter = orig_mutter + "_EDIT"
    new_foreign = orig_foreign + "_EDIT"
    new_info = "saved by selenium"

    mutter_input = logged_in_driver.find_element(By.CSS_SELECTOR, "tbody tr .mutter-cell input")
    foreign_input = logged_in_driver.find_element(By.CSS_SELECTOR, "tbody tr .foreign-cell input")
    info_input = logged_in_driver.find_element(By.CSS_SELECTOR, "tbody tr .info-cell input")

    mutter_input.clear()
    mutter_input.send_keys(new_mutter)
    foreign_input.clear()
    foreign_input.send_keys(new_foreign)
    info_input.clear()
    info_input.send_keys(new_info)

    logged_in_driver.find_element(By.CSS_SELECTOR, "tbody tr .save-btn").click()

    wait.until(lambda d: d.find_element(By.CSS_SELECTOR, "tbody tr .mutter-cell").text.strip() == new_mutter)

    row_after_save = logged_in_driver.find_element(By.CSS_SELECTOR, "tbody tr")
    assert row_after_save.find_element(By.CSS_SELECTOR, ".mutter-cell").text.strip() == new_mutter
    assert row_after_save.find_element(By.CSS_SELECTOR, ".foreign-cell").text.strip() == new_foreign
    assert row_after_save.find_element(By.CSS_SELECTOR, ".info-cell").text.strip() == new_info
    assert row_after_save.find_element(By.CSS_SELECTOR, ".edit-btn")
    assert row_after_save.find_element(By.CSS_SELECTOR, ".btn-group-assign")

    # Persistenz prüfen: Seite neu laden
    logged_in_driver.refresh()
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    row_after_reload = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr")))

    assert row_after_reload.find_element(By.CSS_SELECTOR, ".mutter-cell").text.strip() == new_mutter
    assert row_after_reload.find_element(By.CSS_SELECTOR, ".foreign-cell").text.strip() == new_foreign
    assert row_after_reload.find_element(By.CSS_SELECTOR, ".info-cell").text.strip() == new_info

    # # Optional zusätzlich über Flask-Testclient prüfen
    # resp_after_save = logged_in_client.get(page_url, follow_redirects=True)
    # assert resp_after_save.status_code == 200
    # assert new_mutter in resp_after_save.text
    # assert new_foreign in resp_after_save.text
    # assert new_info in resp_after_save.text



def test_app_functionality_delete_user(logged_in_client, logged_in_driver):   
    """Add User"""
    resp = logged_in_client.get("/")
    assert resp.status_code == 200
    assert "Lerne effizient neue Sprachen" in resp.text
    resp = logged_in_client.get("/admin/users", follow_redirects=True)
    assert resp.status_code == 200
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
    




   