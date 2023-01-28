echo "lifting data from the data folder..."
# lift dataset
./csv2rdf -u ./metadata/meta_dataset.json -o output/dataset.ttl
./csv2rdf -u ./metadata/meta_symptom_Description.json -o output/symptom_Description.ttl
./csv2rdf -u ./metadata/meta_symptom_precaution.json -o output/symptom_precaution.ttl
./csv2rdf -u ./metadata/meta_symptom-severity.json -o output/symptom_severity.ttl