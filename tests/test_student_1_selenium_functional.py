from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from conftest import BASE_URL


def test_app_functionality_declination_settings(logged_in_student_client, logged_in_student_driver):
    page_url = "/declination/settings"

    resp = logged_in_student_client.get(page_url, follow_redirects=True)
    assert resp.status_code == 200

    wait = WebDriverWait(logged_in_student_driver, 15)

    logged_in_student_driver.get(BASE_URL + page_url)

    select = Select(logged_in_student_driver.find_element(By.NAME, "pair"))
    assert select.first_selected_option.get_attribute("value") == "deutsch-spanisch"

    button = logged_in_student_driver.find_element(By.XPATH, "//button[normalize-space()='Speichern']")
    assert button.is_enabled()
    button.click()
    
    select2 = Select(logged_in_student_driver.find_element(By.NAME, "tense"))
    futuro_element = logged_in_student_driver.find_element(By.CSS_SELECTOR, 'option[value=Futuro]')
    select2.select_by_value("Futuro")
    assert futuro_element.is_selected()
    
    button2 = logged_in_student_driver.find_element(By.XPATH, "//button[normalize-space()='Speichern']")
    assert button2.is_enabled()
    button2.click()
    wait.until(EC.url_contains("testdeclination/deutsch-spanisch")) 
    assert "Futuro" in logged_in_student_driver.page_source

    
    
    