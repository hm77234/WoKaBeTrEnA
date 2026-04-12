# tests/test_functional.py

from bs4 import BeautifulSoup

from conftest import ADMIN_USER, ADMIN_PW, TEST_STUDENT, TEST_STUDENT_PW, TEST_GRUPPE, TEST_GRUPPEN_BESCHREIBUNG, TESTFILE_TYP_1, TESTFILE_TYP_2, TESTFILE_PATH


def test_first_login_and_password_change(api_client):
    
    # GET-Anfrage an die Login-Seite
    # Das setzt auch das notwendige Session-Cookie im api_client
    response = api_client.get("/login")
    assert response.status_code == 200
    # CSRF-Token aus dem HTML extrahieren
    soup = BeautifulSoup(response.text, "html.parser")
    # Sucht nach <input name="csrf_token" value="...">
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None  # Sicherstellen, dass wir eins gefunden haben
    # POST-Anfrage mit den Daten UND dem Token
    login_data = {
        "username": ADMIN_USER,
        "password": ADMIN_PW,
        "csrf_token": csrf_token
    }
    headers = {"Referer": f"{api_client.base_url}/login"}
    post_resp = api_client.post("/login", data=login_data, headers=headers, follow_redirects=True)
    assert post_resp.status_code == 200
    assert "Bitte Passwort bei erstem Login ändern!" in post_resp.text
    # POST-Anfrage mit neuem Passwort
    soup2 = BeautifulSoup(response.text, "html.parser")
    csrf_token2 = soup2.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None  # 
    login_data2 = {
        "username": ADMIN_USER
    }
    login_data2["csrf_token"] = csrf_token2
    login_data2["old_password"] = ADMIN_PW
    login_data2["new_password"] = ADMIN_PW
    login_data2["confirm_password"] = ADMIN_PW
    post_resp = api_client.post("/change-password", data=login_data2, headers=headers, follow_redirects=True)

    # Prüfen, ob der Login erfolgreich war und das Passwort geändert wurde
    assert post_resp.status_code == 200
    assert "Passwort geändert! Bitte neu einloggen" in post_resp.text  # Oder ein anderer Text deiner App
    
def test_login_failed(api_client):
    """Prüft Login mit falschen Credentials."""
    response = api_client.get("/login")
    assert response.status_code == 200
    # CSRF-Token aus dem HTML extrahieren
    soup = BeautifulSoup(response.text, "html.parser")
    # Sucht nach <input name="csrf_token" value="...">
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None  # Sicherstellen, dass wir eins gefunden haben
    login_data = {
        "username": ADMIN_USER,
        "password": "BLA",
        "csrf_token": csrf_token
    }
    headers = {"Referer": f"{api_client.base_url}/login"}
    post_resp = api_client.post("/login", data=login_data, headers=headers, follow_redirects=True)
    assert post_resp.status_code == 200
    assert "Falsche Anmeldeinformationen!" in post_resp.text
    
def test_noword_admin_handling(logged_in_client):
    """ prüft das No Word Verhalten"""
    response = logged_in_client.get("/test/deutsch-englisch")
    assert response.status_code == 200
    assert "Keine Vokabeln gefunden Deutsch → Englisch!" in response.text
    
    
def test_app_functionality_upload_csv_typ_1(logged_in_client):
    """Upload von Files"""
    resp = logged_in_client.get("/")
    assert resp.status_code == 200
    assert "Lerne effizient neue Sprachen" in resp.text
    resp = logged_in_client.get("/admin", follow_redirects=True)
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, "html.parser")
    # Sucht nach <input name="csrf_token" value="...">
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None 
    option = soup.find("option", string="Deutsch → Spanisch")
    if option:
        lp_value = option["value"]
        #print(f"Gefundener Value: {lp_value}")

    assert lp_value is not None

    # 1. Pfad zur Beispieldatei (relativ zu deinem Test-Skript)
    file_path = TESTFILE_PATH + TESTFILE_TYP_1
    
    # 2. Datei im Binärmodus öffnen
    with open(file_path, "rb") as f:
        # 'file' muss dem 'name'-Attribut im HTML <input type="file" name="..."> entsprechen
        files = {"csvfile": (TESTFILE_TYP_1, f, "text/csv")}
        
        # 3. Formularfelder 
        data = {
            "csrf_token": csrf_token, # Achte auf den Namen (meist csrf_token, nicht csr_token)
            "language_pair": lp_value,
            "upload_csv": "Importieren"
        }
        headers = {"Referer": f"{logged_in_client.base_url}/admin/upload"}
        # 4. Der Request (httpx setzt multipart/form-data automatisch)
        file_upl_resp = logged_in_client.post(
            "/admin/upload", 
            data=data, 
            files=files, 
            headers=headers,
            follow_redirects=True
        )

    assert file_upl_resp.status_code == 200
    assert "3 assignments! 0 doublicates found!" in file_upl_resp.text
    
def test_app_functionality_upload_csv_typ_2(logged_in_client):
    """Upload von Files"""
    resp = logged_in_client.get("/")
    assert resp.status_code == 200
    assert "Lerne effizient neue Sprachen" in resp.text
    resp = logged_in_client.get("/admin", follow_redirects=True)
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, "html.parser")
    # Sucht nach <input name="csrf_token" value="...">
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None 
    option = soup.find("option", string="Deutsch → Spanisch")
    if option:
        lp_value = option["value"]
        #print(f"Gefundener Value: {lp_value}")

    assert lp_value is not None

    # 1. Pfad zur Beispieldatei (relativ zu deinem Test-Skript)
    file_path = TESTFILE_PATH + TESTFILE_TYP_2
    
    # 2. Datei im Binärmodus öffnen
    with open(file_path, "rb") as f:
        # 'file' muss dem 'name'-Attribut im HTML <input type="file" name="..."> entsprechen
        files = {"csvfile": (TESTFILE_TYP_2, f, "text/csv")}
        
        # 3. Formularfelder 
        data = {
            "csrf_token": csrf_token, # Achte auf den Namen (meist csrf_token, nicht csr_token)
            "language_pair": lp_value,
            "upload_csv": "Importieren"
        }
        headers = {"Referer": f"{logged_in_client.base_url}/admin/upload"}
        # 4. Der Request (httpx setzt multipart/form-data automatisch)
        file_upl_resp = logged_in_client.post(
            "/admin/upload", 
            data=data, 
            files=files, 
            headers=headers,
            follow_redirects=True
        )

    assert file_upl_resp.status_code == 200
    assert "15 assignments! 0 doublicates found!" in file_upl_resp.text
    
#Delete USer is in selenium tests
def test_app_functionality_add_user(logged_in_client):   
    """Add User"""
    resp = logged_in_client.get("/")
    assert resp.status_code == 200
    assert "Lerne effizient neue Sprachen" in resp.text
    resp = logged_in_client.get("/admin/users", follow_redirects=True)
    soup = BeautifulSoup(resp.text, "html.parser")
    # Sucht nach <input name="csrf_token" value="...">
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None 
    option = soup.find("option", string="Student")
    if option:
        ugroup_value = option["value"]
        

    assert ugroup_value is not None
    new_user_data = {
        "username": TEST_STUDENT,
        "password": TEST_STUDENT_PW,
        "csrf_token": csrf_token
    }
    headers = {"Referer": f"{logged_in_client.base_url}/admin/users"}
    post_resp = logged_in_client.post("/admin/users", data=new_user_data, headers=headers, follow_redirects=True)
    assert post_resp.status_code == 200
    assert "teststudent (student) erstellt!" in post_resp.text

#Wordgroups  
def test_app_functionality_group_add(logged_in_client):  
    resp = logged_in_client.get("/wordgroups/create", follow_redirects=True)
    assert resp.status_code == 200
    assert "Wortgruppenname" in resp.text
    assert "Sprachpaar" in resp.text 
    soup = BeautifulSoup(resp.text, "html.parser")
    # Sucht nach <input name="csrf_token" value="...">
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None 
    option = soup.find("option", string="deutsch-spanisch")
    if option:
        lp_value = option["value"]
        #print(f"Gefundener Value: {lp_value}")

    assert lp_value is not None
    new_group_data = {
        "name": TEST_GRUPPE,
        "description": TEST_GRUPPEN_BESCHREIBUNG,
        "csrf_token": csrf_token,
        "language_pair_id": lp_value
    }
    headers = {"Referer": f"{logged_in_client.base_url}/wordgroups/create"}
    post_resp = logged_in_client.post("/wordgroups/create", data=new_group_data, headers=headers, follow_redirects=True)
    assert post_resp.status_code == 200
    assert "Gruppe erfolgreich angelegt" in post_resp.text
    assert TEST_GRUPPE in post_resp.text
    


def test_app_functionality_group_list(logged_in_client):   
    resp = logged_in_client.get("/wordgroups/wordgroups", follow_redirects=True)
    assert resp.status_code == 200
    assert "Wortgruppe" in resp.text
    assert "Allgemein" in resp.text
    assert TEST_GRUPPE in resp.text


def test_app_functionality_group_stats(logged_in_client):  
    resp = logged_in_client.get("/wordgroups/wordgroups_stats", follow_redirects=True)
    assert resp.status_code == 200
    assert "Wortgruppe" in resp.text
    assert "essen" in resp.text 
    assert "student" in resp.text 
    

#BACKUP   
def test_app_functionality_backup(logged_in_client_session, backup_filename):  
    resp = logged_in_client_session.get("/admin/backup-db", follow_redirects=True)
    assert resp.status_code == 200
    assert "Datenbank Backup" in resp.text
    soup = BeautifulSoup(resp.text, "html.parser")

    backup_filename_inpage = soup.find("input", {"name": "backupfilename"})["value"]
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None 
    assert backup_filename_inpage is not None 
    assert backup_filename_inpage != "safe"
    
    new_backup_data = {
        "backupfilename": backup_filename,
        "csrf_token": csrf_token

    }

    headers = {"Referer": f"{logged_in_client_session.base_url}/admin/backup-db"}
    post_resp = logged_in_client_session.post("/admin/backup-db", data=new_backup_data, headers=headers, follow_redirects=True )
    assert post_resp.status_code == 200
    assert "Backup erfolgreich erzeugt!" in post_resp.text


 


   
