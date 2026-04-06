from bs4 import BeautifulSoup

from conftest import STUDENT_USER, STUDENT_PW, TESTFILE_PATH, TESTFILE_TYP_2, TESTFILE_TYP_1


def get_answer(question_word : str) -> str:  # pragma: no cover
    answer_word = ""
    with open(TESTFILE_PATH + TESTFILE_TYP_1, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    with open(TESTFILE_PATH + TESTFILE_TYP_2, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows2 = list(reader)

    
    
    for item in rows:
        # pragma: no cover
        if len(item) >= 2 and question_word == item[0]:
            # pragma: no cover
            answer_word = item[1]
            # pragma: no cover
            break
        # pragma: no cover
        elif len(item) >= 2 and question_word == item[1]:
            # pragma: no cover
            answer_word = item[0]
            # pragma: no cover
            break

    # Falls nicht in rows1, suche in rows2
    # pragma: no cover
    if not answer_word:
        # pragma: no cover
        for item in rows2:
            # pragma: no cover
            if len(item) >= 2 and question_word == item[0]:
                # pragma: no cover
                answer_word = item[1]
                # pragma: no cover
                break
            # pragma: no cover
            elif len(item) >= 2 and question_word == item[1]:
                # pragma: no cover
                answer_word = item[0]
                # pragma: no cover
                break
    return answer_word

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
        "username": STUDENT_USER,
        "password": STUDENT_PW,
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
        "username": STUDENT_USER
    }
    login_data2["csrf_token"] = csrf_token2
    login_data2["old_password"] = STUDENT_PW
    login_data2["new_password"] = STUDENT_PW
    login_data2["confirm_password"] = STUDENT_PW
    post_resp = api_client.post("/change-password", data=login_data2, headers=headers, follow_redirects=True)

    # Prüfen, ob der Login erfolgreich war und das Passwort geändert wurde
    assert post_resp.status_code == 200
    assert "Passwort geändert! Bitte neu einloggen" in post_resp.text  # Oder ein anderer Text deiner App
import csv
 
def test_vocable_test_correct_typ2(logged_in_student_client):
    """Upload von Files"""
   
    resp = logged_in_student_client.get("/")
    assert resp.status_code == 200
    assert "Vokabeltrainer" in resp.text

    resp = logged_in_student_client.get("/test/deutsch-spanisch")
    assert resp.status_code == 200
    assert "Test: Deutsch → Spanisch" in resp.text
    
    soup = BeautifulSoup(resp.text, "html.parser")
    div = soup.find("div", style=True)  # oder genauer nach style / Position

    text = div.get_text(strip=True)
    question_word = text.split("→")[0].strip()
    # pragma: no cover
    answer_word = get_answer(question_word) # pragma: no cover
    
    assert answer_word != ""
    assert question_word != ""
   
    word_id = soup.find("input", {"name": "word_id"})["value"]
    assert word_id is not None  # Sicherstellen, dass wir eins gefunden haben
    knowledgebase = soup.find("input", {"name": "knowledgebase"})["value"]
    assert knowledgebase is not None  # Sicherstellen, dass wir eins gefunden haben
    direction_radio = soup.find("input", {"name": "direction", "checked": True})
    if direction_radio:
        direction = direction_radio["value"]
    else: # pragma: no cover
        direction = "A→B" # pragma: no cover
    random_direction = (
        soup.find("input", {"name": "random_direction", "checked": True}) is not None
    )
   
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None  # Sicherstellen, dass wir eins gefunden haben
    assert all((csrf_token, word_id, knowledgebase, answer_word, question_word))
    answer_form_data = {
        "csrf_token": csrf_token,
        "word_id": word_id,
        "knowledgebase": knowledgebase,  
        "group": "all",     
        "answer": answer_word,
        "direction": direction,             
    }

    if random_direction:
        answer_form_data["random_direction"] = "1"
    headers = {"Referer": f"{logged_in_student_client.base_url}/test/deutsch-spanisch"}
    resp = logged_in_student_client.post(
        "/test/deutsch-spanisch",      # oder die tatsächliche action‑URL
        data=answer_form_data,
        follow_redirects=True,
        headers=headers
    )

    assert resp.status_code == 200
    assert "Richtig!" in resp.text
    
def test_vocable_test_incorrect_typ1(logged_in_student_client):
    """Upload von Files"""
   
    resp = logged_in_student_client.get("/")
    assert resp.status_code == 200
    assert "Vokabeltrainer" in resp.text

    resp = logged_in_student_client.get("/test/deutsch-spanisch")
    assert resp.status_code == 200
    assert "Test: Deutsch → Spanisch" in resp.text
    
    soup = BeautifulSoup(resp.text, "html.parser")
    div = soup.find("div", style=True)  # oder genauer nach style / Position

    text = div.get_text(strip=True)
    question_word = text.split("→")[0].strip()
    answer_word = "yxcfsafafg"
    
    assert answer_word != ""
    assert question_word != ""
   
    word_id = soup.find("input", {"name": "word_id"})["value"]
    assert word_id is not None  # Sicherstellen, dass wir eins gefunden haben
    knowledgebase = soup.find("input", {"name": "knowledgebase"})["value"]
    assert knowledgebase is not None  # Sicherstellen, dass wir eins gefunden haben
    direction_radio = soup.find("input", {"name": "direction", "checked": True})
    if direction_radio:
        direction = direction_radio["value"]
    else: # pragma: no cover
        direction = "A→B" # pragma: no cover
    random_direction = (
        soup.find("input", {"name": "random_direction", "checked": True}) is not None
    )
   
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None  # Sicherstellen, dass wir eins gefunden haben
    assert all((csrf_token, word_id, knowledgebase, answer_word, question_word))
    answer_form_data = {
        "csrf_token": csrf_token,
        "word_id": word_id,
        "knowledgebase": knowledgebase,  
        "group": "all",     
        "answer": answer_word,
        "direction": direction,             
    }

    if random_direction:
        answer_form_data["random_direction"] = "1"
    headers = {"Referer": f"{logged_in_student_client.base_url}/test/deutsch-spanisch"}
    resp = logged_in_student_client.post(
        "/test/deutsch-spanisch",      # oder die tatsächliche action‑URL
        data=answer_form_data,
        follow_redirects=True,
        headers=headers
    )

    assert resp.status_code == 200
    assert "Falsch!" in resp.text   