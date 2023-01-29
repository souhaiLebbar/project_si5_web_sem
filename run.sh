echo "creating a project virtal environment"
python -m venv ./project_venv
source project_venv/bin/activate
echo "installing the requirements packages"
pip install -r requirements.txt
python -m spacy download en_core_web_lg
python -m coreferee install en
streamlit run app.py
