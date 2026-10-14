# DICOM anonymisation

In this anonymisation schema, patient IDs were replaced with a salted hash ID.
Only a trusted person had access to the key. This was to allow future data to be linked to existing data.
Accession numbers were kept and used to complete retrieve the hash ID.

Anonymisation steps:
1. `anonymise.py` simply removes DICOM tags that might contain identifying information.
2. The other scripts are to prepare an ID index to allow a trusted person (e.g. clinician) to maintain a key linking original IDs to anonymous IDs so future data can be reliably linked.
  a. `select_id_pref_hn.py` picks an ID for each patient, preferring the hospital number (note the bidsify script prefers NHS number).
  b. `fix_accession.py` removes accession numbers that contain the patient ID and fills in missing accession numbers.
  c. `anonymise_bad_accessions.py` removed a broader range of accession numbers that contain strings resembling patient IDs, as well as any in a manually curated list.

`tags_to_anonymise.py` simply represents the list of hex duples as a dictionary with keywords for readability.
