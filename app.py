import streamlit as st
import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Graph,Namespace,Dataset
#from rdflib_owl import OWL_NS, OWLRL_Profile
import json 
import scispacy
import spacy
import spacyfishing
import coreferee
from uuid import uuid4
from datetime import datetime
from pyshacl import validate

def coref_resolution(name, text):
    final_text = ""
    doc = coref(text)
    
    for i, token in enumerate(doc):
        if token.tag_ == "PRP":
            resolution = doc._.coref_chains.resolve(doc[i])
            final_text += resolution[0].text
        else:
            final_text += token.text
        final_text += " "
    
    final_text = final_text.replace(name, "patient")
    return final_text.strip()

def extract_duples(folder_id, text):
    doc = disease(text)
    
    verbs = []
    
    for sent in doc.sents:
        for token in sent:
            if token.pos_ == "VERB" or token.pos_ == "AUX":
                verbs.append(token)
                
    duples = []
    
    for verb in verbs:
        children = [x for x in verb.children]
        subject = [x for x in children if x.dep_ == "nsubj"]
        object = [x for x in children if x.dep_ == "dobj" or x.dep_ == "nmod"]
        
        if len(subject) == 0 or len(object) == 0:
            continue
            
        subject = subject[0]
        object = object[0]
        
        subject_ent = None
        object_ent = None
        for ent in doc.ents:
            if subject.i in range(ent.start, ent.start + len(ent)) and not ent._.kb_qid is None:
                subject_ent = ent
            elif object.i in range(ent.start, ent.start + len(ent)) and not ent._.kb_qid is None:
                object_ent = ent
                
        if subject_ent is None or object_ent is None:
            continue
            
        if subject_ent._.kb_qid != "Q181600":
            continue
            
        sparql.setQuery("""
            PREFIX wd: <http://www.wikidata.org/entity/>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>

            SELECT ?x
            WHERE {
                wd:""" + object_ent._.kb_qid + """ wdt:P31 ?x
            }
            """
        )
        
        try:
            predicate = None
            ret = sparql.queryAndConvert()
            
            result = [r['x']['value'].split('/')[-1] for r in ret["results"]["bindings"]]

            if 'Q112965645' in result or 'Q12136' in result:
                predicate = "mp:declaredSymptom"
            elif 'Q12140' in result:
                predicate = "mp:triedMed"
                
            if not predicate is None:
                duples.append((predicate, f'wd:{object_ent._.kb_qid}'))
                
        except Exception as e:
            print(e)
            
    return duples

def create_query(name, ssm, consultation, duples, doctor_id):
    
    folder_properties = '\n                '.join([f'{item[0]} {item[1]} ;' for item in duples])[:-1]
    symptoms = [item[1] for item in duples if item[0] == "mp:declaredSymptom"]
    symptom_instances = '\n                '.join([f"{symptom} a mc:Symptom ." for symptom in symptoms])
    meds = [item[1] for item in duples if item[0] == "mp:triedMed"]
    med_instances = '\n                '.join([f"{med} a mc:Medicine ." for med in meds])
    
    return """
    PREFIX pat: <http://www.inria.org/patients/>
    PREFIX doc: <http://www.inria.org/doctors/>
    PREFIX cons: <http://www.inria.org/consultations/>
    PREFIX mc: <http://www.inria.org/entity/>
    PREFIX mp: <http://www.inria.org/property/>
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    INSERT DATA {
        GRAPH <http://localhost:8082> {
            pat:""" + ssm + """
                a mc:Patient ;
                mp:name \"""" + name + """\" ;
                mp:consulted cons:""" + str(consultation) + """ .
                
            cons:""" + str(consultation) + """
                a mc:Consultation ;
                mp:docInCharge doc:""" + str(doctor_id) + """ ;
                mp:tookPlace \"""" + str(datetime.now()).replace(' ', 'T').split('.')[0] + """\"^^xsd:dateTime ;
                """ + folder_properties + """.

                """ + symptom_instances + """
                """ + med_instances + """
                doc:""" + str(doctor_id) + """ a mc:Doctor
            
        }
    }"""

def text_2_sparql(name, ssm, text, doctor_id):
    folder_id = uuid4()
    preprocessed = coref_resolution(name, text)
    duples = extract_duples(folder_id, preprocessed)
    return folder_id, create_query(name, ssm, folder_id, duples, doctor_id)


st.title("Doctor's visit")


with st.form("Patient form"):
   fname = st.text_input('First name', 'Johnson')
   lname = st.text_input('Last name', 'Dwayn')
   nss = st.text_input('NSS', '160 40 50 22 35 00')
   d= st.date_input("Patient birthday",) 
   txt = st.text_area('How do your patient feel ?',"Johnson suffered from a fever. He also had a headache for 3 days. He also has hypocalcemia. He already tried peramivir")
   # Every form must have a submit button.
   option = st.selectbox(
     'Which sparql request would you execute ?',
     ('Query1_symtoms', 'Query2_flags'))
   submitted = st.form_submit_button("Submit")

if submitted & (txt!="") :
    st.title("Diagnostic report")
    coref = spacy.load("en_core_web_lg")
    coref.add_pipe('coreferee')

    disease = spacy.load("en_core_sci_sm")
    disease.add_pipe('entityfishing', config={
            "extra_info": True,
            "api_ef_base": "http://nerd.huma-num.fr/nerd/service"
        })
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setReturnFormat(JSON)

    doctor_id = uuid4()
    g = Dataset()
    st.subheader("INSERT query:")
    folder_id, insertQuery = text_2_sparql("Johnson", "684656-8146516-13520", txt, doctor_id)
    st.write("```"+insertQuery)
    g.update(insertQuery)
    st.subheader("Schacl validation report :")
    s = Graph().parse("disease_shacl.ttl", format="turtle")
    conforms, report, message = validate(g, shacl_graph=s, advanced=True, debug=False)
    st.write("```"+message)
    req1 = """
    SELECT ?disease ?name (count(?symptom) AS ?count) WHERE {
        GRAPH <http://localhost:8082> {
        cons:""" + str(folder_id) + """
            mp:declaredSymptom ?symptom  .

            SERVICE <https://query.wikidata.org/sparql> {
                ?disease
            wdt:P31 wd:Q112193867 ;
            wdt:P780 ?symptom ;
            rdfs:label ?name .

            filter(lang(?name) = 'en') 
            }

        }
    }
    GROUP BY ?disease
    ORDER BY DESC(?count)
    LIMIT 10
    """

    req2 = """
    select distinct ?s1 ?slabel (abs(5 - (count(?d1))) AS ?c1) where {
        SERVICE <https://query.wikidata.org/sparql> {
            ?d1 wdt:P780 ?s1 .
            ?s1 rdfs:label ?slabel .

            filter(lang(?slabel) = 'en')
        }
        {

            SELECT (?disease as ?d1) ?name (count(?symptom) AS ?count) WHERE {
                cons:""" + str(folder_id) + """
                    mp:declaredSymptom ?symptom  .

                SERVICE <https://query.wikidata.org/sparql> {
                    ?disease
                        wdt:P31 wd:Q112193867 ;
                        wdt:P780 ?symptom ;
                        rdfs:label ?name .

                    filter(lang(?name) = 'en')

                }
            }
            GROUP BY ?disease
            ORDER BY DESC(?count)
            LIMIT 10
        }
    }
    GROUP BY ?s1
    ORDER BY DESC(?c1)
    """
    if option == "Query1_symtoms":
        my_req = req1
    else:
        my_req = req2
    st.subheader("SELECT Query : ")
    q1res = g.query(my_req,initNs={
        'cons': 'http://www.inria.org/consultations/',
        'mp': 'http://www.inria.org/property/',
        'wd': 'http://www.wikidata.org/entity/',
        'wdt': 'http://www.wikidata.org/prop/direct/',
        'rdfs' : 'http://www.w3.org/2000/01/rdf-schema#'
    }
    )
    st.write("```" + my_req)
    st.subheader("RESULT")
    for item in q1res:
        st.write(item)

if submitted & (txt=="wiki"):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    # Below we SELECT both the hot sauce items & their labelsclear
    # in the WHERE clause we specify that we want labels as well as items
    sparql.setQuery("""
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX mc: <http://www.inria.org/entity/>
        PREFIX mp: <http://www.inria.org/property/>
        PREFIX owl:  <http://www.w3.org/2002/07/owl#>

        construct {
        ?id a mc:Disease ;
            owl:sameAs ?x ;
            mp:hasSyndrom ?idz ;
            mp:hasTherapy ?idy .

        ?idz owl:sameAs ?z .
        ?idy owl:sameAs ?y .
        } where {
        ?x wdt:P31 wd:Q12136 ;
            wdt:P2176 ?y ;
            wdt:P780 ?z ;
            wdt:P244 ?a .

        ?z wdt:P244 ?b .
        ?y wdt:P244 ?c .
        
        bind(iri(concat("http://www.inria.org/instance/", ?a)) as ?id)
        bind(iri(concat("http://www.inria.org/instance/", ?c)) as ?idy)
        bind(iri(concat("http://www.inria.org/instance/", ?b)) as ?idz)
        }
    """)
    sparql.setReturnFormat(JSON)
    wiki_results = sparql.query().convert()
    st.subheader("wikidata service result :")
    st.json(wiki_results)

if submitted & (txt=="csv"):
    st.title("Diagnostic report")
    # Load the turtle file into a graph
    g = Graph()
    g.parse("csv_lifting/output/dataset.ttl", format="turtle")
    g.parse("csv_lifting/output/symptom_Description.ttl", format="turtle")
    g.parse("csv_lifting/output/symptom_precaution.ttl", format="turtle")
    g.parse("csv_lifting/output/symptom_severity.ttl", format="turtle")
    # Create a namespace for the ontology
    ontology = Namespace("disease_owl.ttl")
    # Create a SPARQL endpoint from the graph
    # sparql = SPARQLWrapper(g)
    # Below we SELECT both the hot sauce items & their labels
    # in the WHERE clause we specify that we want labels as well as items
    qres = g.query("""
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX mc: <http://www.inria.org/entity/>
        PREFIX mp: <http://www.inria.org/property/>
        PREFIX owl:  <http://www.w3.org/2002/07/owl#>
        PREFIX schema: <http://schema.org/>

        SELECT ?diseaseName ?syndromName ?severity ?therapy WHERE {
            ?disease a mc:Disease;
                schema:name ?diseaseName;
                mp:hasSyndrom ?syndromName ;
                mp:hasTherapy ?therapy .
                ?syndrom schema:name ?syndromName;
                    mp:hasWeight ?severity .
            }

        """,
        initNs={"ontology": ontology},
        )
   
    #sparql.setReturnFormat(JSON)
    #csv_results = sparql.query().convert()
    st.subheader("CSV result :")
    # Convert the query results to JSON
    json_results = json.dumps([{'diseaseName':row[0], 'syndromName':row[1], 'severity':row[2], 'therapy':row[3] } for row in qres])

    # Print the results
    st.json(json_results)