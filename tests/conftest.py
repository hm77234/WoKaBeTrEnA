import pytest
import subprocess
import os
import httpx
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# Konfiguration
DB_NAME = "vocab.db"
DB_PATH = "volume/" + DB_NAME
DB_FLAG = "volume/db_initialized.flag"
BASE_URL = "https://localhost:8443"
CONTAINER_NAME = "wokabetrena"  # Name deines Podman-Containers
ADMIN_AUTH = ("admin", "admin123")
ADMIN_USER = "admin"
ADMIN_PW = "admin123"
STUDENT_USER = "student"
STUDENT_PW = "student123"
TEST_STUDENT = "teststudent"
TEST_STUDENT_PW = "teststudent12"
TEST_GRUPPE = "Testgruppe"
TEST_GRUPPEN_BESCHREIBUNG = "Testgruppe Beschreibung"
TESTFILE_PATH = "./examples/"
TESTFILE_TYP_1 = "deutsch_spanische_example.csv"
TESTFILE_TYP_2 = "deutsch_spanisch_verbs_declination.csv"



def perform_login(api_client, username, password):
    """Hilfsfunktion, die CSRF-Handling und Login übernimmt."""
    # 1. Token holen
    resp = api_client.get("/login")
    soup = BeautifulSoup(resp.text, "html.parser")
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    
    # 2. Login-Daten zusammenbauen
    login_data = {
        "username": ADMIN_USER,
        "password": ADMIN_PW,
        "csrf_token": csrf_token
    }
    headers = {"Referer": f"{api_client.base_url}/login"}
    
    # 3. Post ausführen
    return api_client.post("/login", data=login_data, headers=headers, follow_redirects=True)

def perform_browser_login(driver, username, password):
    driver.get(f"{BASE_URL}/login")

    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
    )


@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--start-maximized")
    # optional für CI:
    # options.add_argument("--headless=new")

    drv = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    drv.implicitly_wait(5)
    yield drv
    drv.quit()

@pytest.fixture(autouse=True,scope="session")
def reset_environment():
    """Löscht die DB und startet Podman neu vor jedem Test."""
    # 1. SQLite DB löschen (entspricht DROP DATABASE bei SQLite)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    if os.path.exists(DB_FLAG):
        os.remove(DB_FLAG)
    
    subprocess.run(["./runPodman.sh"], check=True)
    time.sleep(5)

@pytest.fixture(scope="function")
def api_client():
    # follow_redirects=False ist wichtig, um den 302 Status zu sehen!
    with httpx.Client(
        base_url=BASE_URL, 
        verify=False, 
        timeout=15.0, 
        follow_redirects=False
    ) as client:
        yield client
        
@pytest.fixture(scope="function")
def student_client():
    # follow_redirects=False ist wichtig, um den 302 Status zu sehen!
    with httpx.Client(
        base_url=BASE_URL, 
        verify=False, 
        timeout=15.0, 
        follow_redirects=False
    ) as client:
        yield client
        
@pytest.fixture(scope="session")
def session_client():
    # follow_redirects=False wichtig
    with httpx.Client(base_url=BASE_URL, verify=False, timeout=15.0, follow_redirects=False) as client:
        yield client


@pytest.fixture
def logged_in_client(api_client):
    """Gibt einen Client zurück, der bereits eingeloggt ist."""
    perform_login(api_client, ADMIN_USER, ADMIN_PW)
    # Hier evtl. noch die Passwortänderung durchführen, falls nötig
    return api_client

@pytest.fixture
def logged_in_student_client(student_client):
    """Gibt einen Client zurück, der bereits eingeloggt ist."""
    perform_login(student_client, STUDENT_USER, STUDENT_PW)
    # Hier evtl. noch die Passwortänderung durchführen, falls nötig
    return student_client

@pytest.fixture
def logged_in_driver(driver):
    perform_browser_login(driver, ADMIN_USER, ADMIN_PW)
    return driver


@pytest.fixture(scope="session")
def logged_in_client_session(session_client):
    perform_login(session_client, ADMIN_USER, ADMIN_PW)
    return session_client

@pytest.fixture(scope="session")
def backup_filename(logged_in_client_session):
    resp = logged_in_client_session.get("/admin/backup-db")
    soup = BeautifulSoup(resp.text, "html.parser")
    backup_input = soup.find("input", {"name": "backupfilename"})
    assert backup_input is not None
    return backup_input["value"]