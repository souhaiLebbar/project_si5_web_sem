# Projet_Knowledge_Ing
## to lunch this app, run the following command line :
```
pip install requirements.txt
streamlit run app.py
```
# or simply run the shell script :
```
bash utils/run.sh
```
# graph exploitation
    
    1.Find all patients who have consulted a doctor:

```
SELECT ?patient ?doctor WHERE {
    ?consultation mp:docInCharge ?doctor .
    ?patient mp:consulted ?consultation .
}
```

Use Case:

    To find out which patients have consulted with a doctor and who the doctor was.

    2.Find all patients with a specific symptom:

```
SELECT ?patient ?symptom WHERE {
    ?consultation mp:declaredSymptom ?symptom .
    ?patient mp:consulted ?consultation .
}
```

Use Case:

    To find out which patients have declared a specific symptom during a consultation.

    3.Find all medicines tried for a specific symptom:

```
SELECT ?medicine ?symptom WHERE {
    ?consultation mp:declaredSymptom ?symptom .
    ?consultation mp:triedMed ?medicine .
}
```

Use Case:

    To find out which medicines were tried for a specific symptom during a consultation.

    4.Find all patients with a specific diagnosis:

```
SELECT ?patient ?diagnosis WHERE {
    ?consultation mp:diagnosedWith ?diagnosis .
    ?patient mp:consulted ?consultation .
}
```

Use Case:

    To find out which patients have been diagnosed with a specific condition during a consultation.

    5.Find all patients who have consulted a specific doctor:

```
SELECT ?patient ?doctor WHERE {
    ?consultation mp:docInCharge ?doctor .
    ?patient mp:consulted ?consultation .
    FILTER (?doctor = doc:7124b686-5d7b-42d6-82f6-bbdd9b3c32e0)
}
```

Use Case:

    To find out which patients have consulted a specific doctor.


