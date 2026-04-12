from bs4 import BeautifulSoup
import re

from conftest import STUDENT_USER, STUDENT_PW, TESTFILE_PATH, TESTFILE_TYP_2, TESTFILE_TYP_1

import re

def parse_declination_field(decl_field): # pragma: no cover
    """
    Zerlegt z. B.:
        "Presente:s1=...,s2=...|Indefinido:s1=...|Futuro:s1=..."
    in ein dict:
        { "Presente": {"s1": "vengo", "s2": "vienes", ...},
          "Indefinido": {"s1": "vine", ...},
          "Futuro": {"s1": "vendré", ...} }
    """
    tenses = {}
    for part in decl_field.split("|"):
        part = part.strip()
        if not part:
            continue

        # z. B. "Presente:s1=vengo,s2=vienes,..."
        match = re.match(r"([^:]+):(.*)", part)
        if not match:
            continue

        time = match.group(1)  # Presente / Indefinido / Futuro
        forms_str = match.group(2)

        # "s1=vengo,s2=vienes,..."
        forms = {}
        for form in forms_str.split(","):
            form = form.strip()
            if "=" not in form:
                continue
            person, value = form.split("=", 1)
            forms[person] = value.strip()

        tenses[time] = forms
    return tenses

def get_answer_forms(base_word, time_line, person_codes): # pragma: no cover
    """
    base_word: z. B. "kommen"
    time_line: z. B. "Indefinido"
    person_codes: Liste wie ["m1", "s2"] (welche Personen gefragt sind)

    """
    with open(TESTFILE_PATH + TESTFILE_TYP_2, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        all_rows = list(reader)
    
    # Zeile finden
    row = None
    for rows in all_rows:
        if rows[0] == base_word or rows[1] == base_word:
            row = rows
            break
        if row:
            break
    if not row:
        raise ValueError(f"Kein Verb für {base_word} gefunden")

    # Deklination parsen
    tenses = parse_declination_field(row[5])
    if time_line not in tenses:
        raise ValueError(f"Zeitform {time_line} nicht in CSV enthalten")

    forms = tenses[time_line]
    result = {}
    for p in person_codes:
        result[p] = forms.get(p)
    return result




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
 
def test_vocable_test_correct_typ1(logged_in_student_client):
    """vocable test typ1 icorrect"""
   
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
    """vocable test typ 1 incorrect"""
   
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
    
def test_vocable_test_correct_typ2(logged_in_student_client):
    """vocable test typ2 correct"""
   
    resp = logged_in_student_client.get("/")
    assert resp.status_code == 200
    assert "Vokabeltrainer" in resp.text

    resp = logged_in_student_client.get("/testdeclination/deutsch-spanisch")
    assert resp.status_code == 200
    assert "Deklinationstraining" in resp.text
    
    soup = BeautifulSoup(resp.text, "html.parser")

    question_box = soup.find("div", class_="mb-3 p-3 bg-question question")
    strong_text = question_box.find("strong").get_text(" ", strip=True)

    # "nächstes Wort: kommen → venir"
    word_part = strong_text.replace("nächstes Wort:", "").strip()
    base_word = word_part.split("→")[0].strip()

    question_box = soup.find("div", class_="mb-3 p-3 bg-question question")
    full_text = question_box.get_text("\n", strip=True)

    # nächstes Wort: kommen → venir
    # Info: A1
    # Gefragt sind folgende Personen
    # * (m2):2 Person, Mehrzahl
    # * (s1):1 Person, Einzahl
    # Indefinido

    persons = re.findall(r"\(([^)]+)\)", full_text)

    lines = [line.strip() for line in full_text.split("\n") if line.strip()]

    # Zeit ist immer die letzte Zeile in diesem Block
    tense = lines[-1]

    answer_result = get_answer_forms(base_word, tense, persons)
    answer_string = ""
    for v in answer_result.values():
        answer_string += v + ", "
    answer_string = answer_string[:-2]

        
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None  # Sicherstellen, dass wir eins gefunden haben
    direction = soup.find("input", {"name": "direction"})["value"]
    assert direction is not None 
    personset = soup.find("input", {"name": "personset"})["value"]
    assert personset is not None 
    wordid = soup.find("input", {"name": "wordid"})["value"]
    assert wordid is not None 
    answer_form_data = {
        "csrf_token": csrf_token,
        "answer": answer_string,
        "testtense": tense,
        "direction": direction,
        "personset": personset,
        "wordid": wordid
    } 
    
    
    headers = {"Referer": f"{logged_in_student_client.base_url}/testdeclination/deutsch-spanisch"}
    resp = logged_in_student_client.post(
        "/testdeclination/deutsch-spanisch",      # oder die tatsächliche action‑URL
        data=answer_form_data,
        follow_redirects=True,
        headers=headers
    )

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, "html.parser")

    # finde den wrapper mit class="text-left"
    container = soup.find("div", class_="text-left")
    assert container is not None, "div.text-left fehlt"

    # suche alle <code> mit Richtig! innerhalb dieses Containers
    correct_codes = container.find_all("code", string=lambda s: s and "Richtig!" in s)

    # assert: genau 2 × "Richtig!"
    assert len(correct_codes) == 2, resp.text
    
def test_vocable_test_incorrect_1_typ2(logged_in_student_client):
    """vocable test typ2 correct"""
   
    resp = logged_in_student_client.get("/")
    assert resp.status_code == 200
    assert "Vokabeltrainer" in resp.text

    resp = logged_in_student_client.get("/testdeclination/deutsch-spanisch")
    assert resp.status_code == 200
    assert "Deklinationstraining" in resp.text
    
    soup = BeautifulSoup(resp.text, "html.parser")

    question_box = soup.find("div", class_="mb-3 p-3 bg-question question")
    strong_text = question_box.find("strong").get_text(" ", strip=True)

    # "nächstes Wort: kommen → venir"
    word_part = strong_text.replace("nächstes Wort:", "").strip()
    base_word = word_part.split("→")[0].strip()

    question_box = soup.find("div", class_="mb-3 p-3 bg-question question")
    full_text = question_box.get_text("\n", strip=True)

    # nächstes Wort: kommen → venir
    # Info: A1
    # Gefragt sind folgende Personen
    # * (m2):2 Person, Mehrzahl
    # * (s1):1 Person, Einzahl
    # Indefinido

    persons = re.findall(r"\(([^)]+)\)", full_text)

    lines = [line.strip() for line in full_text.split("\n") if line.strip()]

    # Zeit ist immer die letzte Zeile in diesem Block
    tense = lines[-1]

    answer_result = get_answer_forms(base_word, tense, persons)
    answer_key = list(answer_result.keys())[0]
    answer_result[answer_key] = "wrong"
    answer_string = ""
    for v in answer_result.values():
        answer_string += v + ", "

        
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None  # Sicherstellen, dass wir eins gefunden haben
    direction = soup.find("input", {"name": "direction"})["value"]
    assert direction is not None 
    personset = soup.find("input", {"name": "personset"})["value"]
    assert personset is not None 
    wordid = soup.find("input", {"name": "wordid"})["value"]
    assert wordid is not None 
    answer_form_data = {
        "csrf_token": csrf_token,
        "answer": answer_string,
        "testtense": tense,
        "direction": direction,
        "personset": personset,
        "wordid": wordid
    } 
    
    
    headers = {"Referer": f"{logged_in_student_client.base_url}/testdeclination/deutsch-spanisch"}
    resp = logged_in_student_client.post(
        "/testdeclination/deutsch-spanisch",      # oder die tatsächliche action‑URL
        data=answer_form_data,
        follow_redirects=True,
        headers=headers
    )

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, "html.parser")

    # finde den wrapper mit class="text-left"
    container = soup.find("div", class_="text-left")
    assert container is not None, "div.text-left fehlt"

    # suche alle <code> mit Richtig! innerhalb dieses Containers
    correct_codes = container.find_all("code", string=lambda s: s and "Richtig!" in s)

    # assert: genau 2 × "Richtig!"
    assert len(correct_codes) == 1, resp.text
    assert "Falsch" in resp.text
    
def test_vocable_test_incorrect_2_typ2(logged_in_student_client):
    """vocable test typ2 correct"""
   
    resp = logged_in_student_client.get("/")
    assert resp.status_code == 200
    assert "Vokabeltrainer" in resp.text

    resp = logged_in_student_client.get("/testdeclination/deutsch-spanisch")
    assert resp.status_code == 200
    assert "Deklinationstraining" in resp.text
    
    soup = BeautifulSoup(resp.text, "html.parser")

    
    question_box = soup.find("div", class_="mb-3 p-3 bg-question question")
    full_text = question_box.get_text("\n", strip=True)




    lines = [line.strip() for line in full_text.split("\n") if line.strip()]

    # Zeit ist immer die letzte Zeile in diesem Block
    tense = lines[-1]

   # A1
    answer_string = "wrong, wrong"


        
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None  # Sicherstellen, dass wir eins gefunden haben
    direction = soup.find("input", {"name": "direction"})["value"]
    assert direction is not None 
    personset = soup.find("input", {"name": "personset"})["value"]
    assert personset is not None 
    wordid = soup.find("input", {"name": "wordid"})["value"]
    assert wordid is not None 
    answer_form_data = {
        "csrf_token": csrf_token,
        "answer": answer_string,
        "testtense": tense,
        "direction": direction,
        "personset": personset,
        "wordid": wordid
    } 
    
    
    headers = {"Referer": f"{logged_in_student_client.base_url}/testdeclination/deutsch-spanisch"}
    resp = logged_in_student_client.post(
        "/testdeclination/deutsch-spanisch",      # oder die tatsächliche action‑URL
        data=answer_form_data,
        follow_redirects=True,
        headers=headers
    )

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, "html.parser")

    # finde den wrapper mit class="text-left"
    container = soup.find("div", class_="text-left")
    assert container is not None, "div.text-left fehlt"

    # suche alle <code> mit Richtig! innerhalb dieses Containers
    correct_codes = container.find_all("code", string=lambda s: s and "Richtig!" in s)

    # assert: genau 2 × "Richtig!"
    assert len(correct_codes) == 0, resp.text
    assert "Falsch" in resp.text
    
def test_vocable_test_student_stats(logged_in_student_client):
    """check stats page"""
   
    resp = logged_in_student_client.get("/stats")
    assert resp.status_code == 200
    assert "Meine Stats" in resp.text
    assert "A1-Verben" in resp.text 
    assert '<td align="center">8</td>' in resp.text
    
def test_vocable_test_declination_set_presente(logged_in_student_client):
    """setzt testdeclination  page auf presente , Vorbereitung für den Selenium Test """
   
    page_url = "/declination/settings/deutsch-spanisch"
    resp = logged_in_student_client.get(page_url)
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.text, "html.parser")
    csrf_token = soup.find("input", {"name": "csrf_token"})["value"]
    assert csrf_token is not None  # Sicherstellen, dass wir eins gefunden haben
    # POST-Anfrage mit den Daten UND dem Token
    data = {
        "group": "all",
        "tense": "presente",
        "csrf_token": csrf_token
    }
    headers = {"Referer": f"{logged_in_student_client.base_url}{page_url}"}
    post_resp = logged_in_student_client.post(page_url, data=data, headers=headers, follow_redirects=True)
    assert post_resp.status_code == 200
    assert "presente" in post_resp.text
    

   
   
    

