## CSV Import Format
### Basic Format (no conjugations)

    mutter_word,foreign_word,foreign_lang,info,groups
    gehen,ir,spanisch,A1,"unregelmäßig;A1-Verben"
 
### Extended Format (with conjugations)
    mutter_word,foreign_word,foreign_lang,info,groups,declinations
    gehen,ir,spanisch,A1,"unregelmäßig;A1-Verben;Gruppe 1","Presente:s1=voy,s2=vas,s3=va,m1=vamos,m2=vais,m3=van|Perfecto:s1=he ido,s2=has ido,s3=ha ido,m1=hemos ido,m2=habéis ido,m3=han ido"

### Declinations Format:

    TenseName:s1=val,s2=val,s3=val,m1=val,m2=val,m3=val | NextTense:s1=val,...