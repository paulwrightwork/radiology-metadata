"""Parse PatientID entries from BIDS dataframe"""
import pandas as pd
import re


def mod11(x):
    """Does the modulus 11 test on NHS numbers. Expects a string of ten digits. See:
     https://en.wikipedia.org/wiki/NHS_number#Format"""
    checksum = 0
    for digit in range(9):
        checksum += int(x[digit]) * (10 - digit)
    check_digit = checksum % 11
    check_digit = 11 - check_digit
    if check_digit == 11:
        check_digit = 0
    return check_digit == int(x[9])


# MAIN SCRIPT

# Change this line to load a different dicom index:
print("Loading.")
bdf = pd.read_parquet('/nfs/project/NeuroRadKCH/metadata/bids/bids_df.parquet')
print("Assigning subject IDs.")
ids_to_assign = bdf.shape[0]
print(f"Total records: {ids_to_assign}.")
bdf['nAllPatientIDs'] = bdf[['nHospitalNumber', 'nNHSnumber', 'nOtherPatientIDs']].sum(axis=1)
bdf['id_pref'] = ''
bdf['id_pref_type'] = 'Unassigned'
bdf.loc[bdf['nAllPatientIDs'] == 0, 'id_pref'] = 'No ID'
bdf.loc[bdf['nAllPatientIDs'] == 0, 'id_pref_type'] = 'No ID'
print(f"{(bdf['nAllPatientIDs'] == 0).sum()} records have no ID.")

# Use hospital number if available
# One hospital number: easy! (the pd.DataFrame().iloc bit is to convert from list to string)
i = bdf['nHospitalNumber'] == 1
if sum(i) > 0:
    bdf.loc[i, 'id_pref'] = pd.DataFrame(bdf.loc[i, 'HospitalNumber'].to_list(), index=bdf.loc[i, :].index
                                         ).iloc[:, 0]
    bdf.loc[i, 'id_pref_type'] = "Hospital number (single)"
    assigned_ids = (bdf['id_pref'].str.len() > 0).sum()
    print(f"Assigned {assigned_ids} of {ids_to_assign} patient IDs from single hospital numbers.")

if assigned_ids < ids_to_assign:
    # Multiple hospital numbers; use the most frequently or first occurring.
    i = bdf['nHospitalNumber'] > 1
    if sum(i) > 0:
        before = assigned_ids
        hospital_number_counts = bdf.loc[i, 'HospitalNumber'].explode().value_counts()
        log_multi = []
        for index, row in bdf.loc[i, :].iterrows():
            bdf.loc[index, 'id_pref'] = hospital_number_counts.loc[row['HospitalNumber']].idxmax()
            bdf.loc[index, 'id_pref_type'] = "Hospital number (multiple)"
            log_multi.append(f"Multiple hospital numbers: {row['HospitalNumber']}. Used: {bdf.loc[index, 'id_pref']}.")

        # Log multiple hospital numbers, removing duplicate lines
        if len(log_multi) > 0:
            print(f"Found multiple hospital numbers in {len(log_multi)} records. Used the most frequently or first occurring.")
            log_multi = list(dict.fromkeys(log_multi))
            for line in log_multi:
                print(line)

        assigned_ids = (bdf['id_pref'].str.len() > 0).sum()
        print(f"Assigned {assigned_ids - before} patient IDs from one of multiple hospital numbers.")
        print(f"Assigned {assigned_ids} of {ids_to_assign} patient IDs.")

if assigned_ids < ids_to_assign:
    # Fill in hospital numbers based on NHS numbers, if present in one scan and missing in another
    print("Cross-referencing NHS numbers to fill in missing hospital numbers.")
    before = assigned_ids
    i = (bdf['nNHSnumber'] == 1) & (bdf['nHospitalNumber'] == 0)
    j = (bdf['nNHSnumber'] == 1) & (bdf['nHospitalNumber'] > 0)
    if sum(i) > 0 and sum(j) > 0:
        hospital_number_counts = bdf.loc[j, 'HospitalNumber'].explode().value_counts()
        hn_lookup = bdf.loc[j, ['NHSnumber', 'HospitalNumber']].copy()
        hn_lookup['NHSnumber'] = pd.DataFrame(hn_lookup['NHSnumber'].to_list(), index=hn_lookup.index).iloc[:, 0]
        hn_lookup = hn_lookup.explode('HospitalNumber').drop_duplicates()
        print(f"Found {hn_lookup.shape[0]} unique pairs of hospital and NHS numbers.")
        to_check = bdf.loc[i, ['NHSnumber', 'HospitalNumber']]
        n_to_check = to_check.shape[0]
        print(f"Found {n_to_check} records with one NHS number and no hospital number.")
        zeros = len(str(n_to_check))
        row_number = 0
        assigned_hn_secondary = 0
        for index, row in to_check.iterrows():
            # Find all the hospital numbers matching all of the NHS numbers in this row
            row_number += 1
            print(f"\rRecord: {row_number:0{zeros}d} / {n_to_check:0{zeros}d}. "
                  f"Matches: {assigned_hn_secondary:0{zeros}d}.",
                  end='', flush=True)
            this_nhs = row['NHSnumber'][0]
            hn_hits = hn_lookup.loc[hn_lookup['NHSnumber'] == this_nhs, 'HospitalNumber'].explode().to_list()
            if len(hn_hits) == 0:
                continue
            # Remove duplicate hospital numbers
            hn_hits = list(dict.fromkeys(hn_hits))
            # Find most frequent or first used from lookup table
            bdf.at[index, 'id_pref'] = hospital_number_counts.loc[hn_hits].idxmax()
            bdf.at[index, 'id_pref_type'] = "Hospital number (from other record)"
            assigned_hn_secondary += 1
        print('\n')  # Add newline after counter
        print(f"NHS numbers matched to hospital numbers in other scans: {assigned_hn_secondary}")
        assigned_ids = (bdf['id_pref'].str.len() > 0).sum()
        print(f"Assigned {assigned_ids} of {ids_to_assign} patient IDs.")
    else:
        print("No records with NHS number but no hospital number.")

if assigned_ids < ids_to_assign:
    # Use NHS number if no hospital number
    before = assigned_ids
    i = (bdf['nNHSnumber'] == 1) & (bdf['id_pref'].str.len() == 0)
    if sum(i) > 0:
        bdf.loc[i, 'id_pref'] = pd.DataFrame(bdf.loc[i, 'NHSnumber'].to_list(), index=bdf.loc[i, :].index).iloc[:, 0]
        bdf.loc[i, 'id_pref_type'] = "NHS number"
        assigned_ids = (bdf['id_pref'].str.len() > 0).sum()
        print(f"Assigned {assigned_ids - before} patient IDs from NHS number.")
        print(f"Assigned {assigned_ids} of {ids_to_assign} patient IDs.")

# Note patients with more than one NHS number. This should never happen and there is not an obvious way to
# determine the correct NHS number programmatically. Use instead the most frequently or first used hospital
# number. Previous versions in_validated these patients but a note in the log is sufficient.
multi_nhs = bdf.loc[bdf['nNHSnumber'] > 1, 'NHSnumber']
if multi_nhs.shape[0] > 0:
    multi_nhs_assigned = (bdf.loc[(bdf['nNHSnumber'] > 1), 'id_pref'].str.len() > 0).sum()
    print(f"Multiple NHS numbers found for {multi_nhs.shape[0]} records.")
    print(f"Of these, {multi_nhs_assigned} were already identified using hospital numbers.")
    print("Multiple NHS numbers, duplicate records removed:")
    print(multi_nhs.astype(str).drop_duplicates().to_csv(index=False, header=False))

if assigned_ids < ids_to_assign:
    # Neither NHS nor hospital number found. Take first of OtherPatientIDs and remove non-alphanumeric characters.
    before = assigned_ids
    i = (bdf['id_pref'].str.len() == 0) & (bdf['nOtherPatientIDs'] > 0)
    if sum(i) > 0:
        bdf.loc[i, 'id_pref'] = pd.DataFrame(bdf.loc[i, 'OtherPatientIDs'].to_list(), index=bdf.loc[i, :].index
                                             ).iloc[:, 0].str.replace(r'[^a-zA-Z0-9]', '', regex=True)
        bdf.loc[i, 'id_pref_type'] = "Other ID"
        assigned_ids = (bdf['id_pref'].str.len() > 0).sum()
        print(f"No NHS or hospital number, other ID used: {assigned_ids - before}")
        print("Assigned {} of {} patient IDs.".format(assigned_ids, ids_to_assign))

# If there are still unassigned subject IDs, then there is a problem with the data.
if assigned_ids < ids_to_assign:
    bdf.loc[bdf['valid'] & (bdf['id_pref'].str.len() == 0), 'comment'] = "Could not assign patient ID."
    bdf.loc[bdf['valid'] & (bdf['id_pref'].str.len() == 0), 'valid'] = False
    bdf.loc[bdf['valid'] & (bdf['id_pref'].str.len() == 0), 'id_pref_type'] = "Could not assign"
    print(f"Subject ID could not be assigned for {ids_to_assign - assigned_ids} records. Check results.")

# Done!
print(f"Finished. Here are the numbers for each type of ID assignment:")
print(bdf['id_pref_type'].value_counts())
print("Saving ...")
try:
    bdf.to_parquet('/nfs/project/NeuroRadKCH/metadata/dicom_anon/bids_df_hnid.parquet')
except:
    bdf.to_pickle('/nfs/project/NeuroRadKCH/metadata/dicom_anon/bids_df_hnid.pkl')
print("Done.")
