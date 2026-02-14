# Tense System Documentation

## Overview
The Tense System extends the vocabulary trainer with support for verb conjugations across multiple languages. It uses 8 generic tense tables ( Tense1  -  Tense8 ) and a flexible mapping table ( TenseMapping ) that assigns language-specific tense names to these generic tables.
Key Features:
	•	Store 6 conjugation forms per tense:  s1,s2,s3,m1,m2,m3  (singular/plural persons)
	•	Different tense names per language pair (Presente=Spanish, Present Simple=English)
	•	Automatic tense table assignment during CSV import
	•	No hardcoded tense names - fully configurable

## Database Schema

    ''' bash

    Tense Tables (Tense1 - Tense8):
    ┌──────────────┬──────────────┐
    │ id (PK)      │ INTEGER      │
    │ s1           │ VARCHAR(100) │ Singular 1st person (yo/ich)
    │ s2           │ VARCHAR(100) │ Singular 2nd person (tú/du)
    │ s3           │ VARCHAR(100) │ Singular 3rd person (él/sie)
    │ m1           │ VARCHAR(100) │ Plural 1st person (nosotros/wir)
    │ m2           │ VARCHAR(100) │ Plural 2nd person (vosotros/ihr)
    │ m3           │ VARCHAR(100) │ Plural 3rd person (ellos/sie)
    └──────────────┴──────────────┘

    Word Table Extensions:
    ┌─────────────────┬──────────────┐
    │ tense1_id       │ FK(Tense1)   │ Presente/Present Simple
    │ tense2_id       │ FK(Tense2)   │ Perfecto/Past Simple
    │ ...             │ ...          │
    │ tense8_id       │ FK(Tense8)   │
    └─────────────────┴──────────────┘

    TenseMapping Table:
    ┌────────────────────┬──────────────┐
    │ id (PK)            │ INTEGER      │
    │ language_pair_id   │ FK           │ LanguagePair.id
    │ tense_table        │ VARCHAR(10)  │ 'Tense1', 'Tense2', ...
    │ tense_name         │ VARCHAR(50)  │ 'Presente', 'Perfecto', ...
    └────────────────────┴──────────────┘
    UNIQUE(language_pair_id, tense_name)


    '''

## Example Mappings

    LanguagePair: deutsch-spanisch (ID=1)
    ├── Tense1 → "Presente"
    ├── Tense2 → "Perfecto" 
    ├── Tense3 → "Indefinido"
    └── Tense4 → "Futuro"

    LanguagePair: deutsch-englisch (ID=2)
    ├── Tense1 → "Present Simple"
    ├── Tense2 → "Past Simple"
    └── Tense3 → "Present Perfect"

## Data Integrity

- UniqueConstraint prevents duplicate mappings per language pair + tense name
- Automatic table assignment prevents tense table collisions
- Fallback to Tense1 if all 8 tables are used
- CSV header detection supports both basic and extended formats

