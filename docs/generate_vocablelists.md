# How to generate vocablelist

 * write it by hand in excel, numbers or in your favorite ediot
 * ask AI engines 

    WARNING: If you use AI, always check the result, AI is far away from perfect, even good.

## example prompts

    A1, A2, B1, ... Language levels
    German-Spanish  Language pair

    age

### csv Typ 1:

    Column 3        alwyays in your mutter langugage

    ```
    Create a German-Spanish vocabulary list for A1 level language learners in the travel theme. Use this exact CSV format with 5 columns separated by commas:

    german_word,spanish_word,spanish,info,groups

    Requirements:
    - First line is exact header: mutter_word,foreign_word,foreign_lang,info,groups
    - Column 1: German word (e.g. "das Restaurant")
    - Column 2: Spanish translation (e.g. "el restaurante") 
    - Column 3: ALWAYS "spanisch"
    - Column 4: Leave empty (two commas: ",,")
    - Column 5: Semicolon-separated groups (e.g. "Reisen;A1")
    - Include 20-30 common travel vocabulary words
    - Use proper Spanish articles (el/la/un/una/los/las)
    - Include Spanish accents where needed (avión, autobús, etc.)
    - Groups should be "Reisen;A1" for all entries

    Example:
    mutter_word,foreign_word,foreign_lang,info,groups
    das Restaurant,el restaurante,spanisch,,Reisen;A1
    das Hotel,el hotel,spanisch,,Reisen;A1
    das Flugzeug,el avión,spanisch,,Reisen;A1
    ```


### csv Typ 2:

    Column 3        alwyays in your mutter langug
    Column 4        your langugage level
    Tense Format    supports up to 8 tenses, allwasy in foreigne language

    ```
    Create a German-Spanish A1 verb conjugation CSV for vocabulary trainer import. Use this EXACT CSV format with 6 columns:

    mutter_word,foreign_word,foreign_lang,info,groups,declinations

    Requirements:
    - First line: mutter_word,foreign_word,foreign_lang,info,groups,declinations
    - Column 1: German infinitive (gehen, kommen, ankommen, sein)
    - Column 2: Spanish infinitive (ir, venir, llegar, ser, estar)
    - Column 3: ALWAYS "spanisch"
    - Column 4: ALWAYS "A1"
    - Column 5: Semicolon-separated groups like "unregelmäßig;A1-Verben;Gruppe 1" or "regelmäßig;A1-Verben;Gruppe 1"
    - Column 6: Pipe-separated tenses with person forms: "TenseName:s1=form,s2=form,s3=form,m1=form,m2=form,m3=form|TenseName2:s1=form..."

    Tense format (4 tenses per verb):
    - Presente: s1=1sg,s2=2sg,s3=3sg,m1=1pl,m2=2pl,m3=3pl
    - Perfecto: he/habéis + participle
    - Indefinido: preterite forms  
    - Futuro: future tense (iré, llegaré)

    Generate 10-15 A1 verbs including:
    - gehen=ir, kommen=venir, ankommen=llegar, sein=ser/estar
    - Plus: haben=tener, sagen=decir, machen=hacer, essen=comer, etc.
    - Mix regular (comer) and irregular (ir, ser, estar, tener)
    - Use proper Spanish accents: estás, llegué, habéis, avión

    Example exact format:
    gehen,ir,spanisch,A1,"unregelmäßig;A1-Verben;Gruppe 1","Presente:s1=voy,s2=vas,s3=va,m1=vamos,m2=vais,m3=van|Perfecto:s1=he ido,s2=has ido,s3=ha ido,m1=hemos ido,m2=habéis ido,m3=han ido|Indefinido:s1=fui,s2=fuiste,s3=fue,m1=fuimos,m2=fuisteis,m3=fueron|Futuro:s1=iré,s2=irás,s3=irá,m1=iremos,m2=iréis,m3=irán"
    ```