""" Fix accession numbers in id index
"""
import pandas as pd


idf = pd.read_parquet('/nfs/project/NeuroRadKCH/metadata/dicom_anon/id_index.parquet')

# Remove accession numbers that contain the patient ID (unless it's an Other ID)
idf['bad_accession'] = idf.apply(lambda x: x['id_pref'] in x['AccessionNumber']
                                 if x['id_pref'] and x['AccessionNumber'] and x['id_pref_type'] != 'Other ID'
                                 else False, axis=1)
# Leave the regex check to a later script.
# idf['bad_accession'] = idf['bad_accession'] | idf['AccessionNumber'].str.contains(r'^[a-zA-Z]\d{6}20')

if idf['bad_accession'].any():
    print(f"ID found in accession number for {idf['bad_accession'].sum()} records. Clearing these and saving to CSV.")
    idf.loc[idf['bad_accession'], 'AccessionNumber'] = None
    bad_accession_dirs = idf.loc[idf['bad_accession'], ['dcm_dir','dcm_subdir']].drop_duplicates()
    bad_accession_dirs.to_csv('/nfs/project/NeuroRadKCH/metadata/dicom_anon/bad_accession_dirs.csv', index=False)

blank_accession_index = idf['AccessionNumber'].isnull()
if not blank_accession_index.any():
    print("None of the records have blank accession numbers. Lucky you. Stopping.")
    exit()

# Fill in blank accession numbers.
dirs_with_blank_accession = idf.loc[blank_accession_index, 'dcm_dir'].drop_duplicates()
all_dirs = idf['dcm_dir'].drop_duplicates()
print(f"Found {blank_accession_index.sum()} records with blank accession number.")
print(f"These occur in {len(dirs_with_blank_accession)} out of {len(all_dirs)} directories.")

# Directories with blank accession numbers that only occur once cannot be filled. Use dcm_dir.
dirs_occurring_once = idf['dcm_dir'].value_counts().loc[idf['dcm_dir'].value_counts() == 1].index.values
single_blank_index = blank_accession_index & idf['dcm_dir'].isin(dirs_occurring_once)
if single_blank_index.any():
    print(f"Of the {len(dirs_with_blank_accession)} directories with blank accession numbers, "
          f"{single_blank_index.sum()} have only one record.")
    print("These cannot be filled in from other records, so will be filled using the dicom directory.")
    idf.loc[single_blank_index, 'AccessionNumber'] = idf.loc[single_blank_index, 'dcm_dir']
    blank_accession_index = idf['AccessionNumber'].isnull()
    if blank_accession_index.any():
        dirs_with_blank_accession = idf.loc[blank_accession_index, 'dcm_dir'].drop_duplicates()
        print(f"There remain {blank_accession_index.sum()} records with blank accession numbers")
        print(f"These occur in {len(dirs_with_blank_accession)} out of {len(all_dirs)} directories.")
    else:
        print("No remaining records have blank accession numbers. Stopping.")
        exit()

# Directories where every record has a blank accession number cannot be filled. Use dcm_dir.
dir_count_all = idf['dcm_dir'].value_counts().rename(
    'count_all').reset_index().rename(columns={'index': 'dcm_dir'})
dir_count_blank = idf.loc[blank_accession_index, 'dcm_dir'].value_counts().rename(
    'count_blank').reset_index().rename(columns={'index': 'dcm_dir'})
dir_counts = dir_count_all.merge(dir_count_blank, on='dcm_dir', how='left')
all_blank_dirs = dir_counts.loc[dir_counts['count_all'] == dir_counts['count_blank'], 'dcm_dir']
all_blank_index = idf['dcm_dir'].isin(all_blank_dirs)
if all_blank_index.any():
    print(f"Found {all_blank_index.sum()} records with no accession numbers in the same directory.")
    print("These cannot be filled in from other records, so will be filled using the dicom directory.")
    idf.loc[all_blank_index, 'AccessionNumber'] = idf.loc[all_blank_index, 'dcm_dir']
    blank_accession_index = idf['AccessionNumber'].isnull()
    if blank_accession_index.any():
        dirs_with_blank_accession = idf.loc[blank_accession_index, 'dcm_dir'].drop_duplicates()
        print(f"There remain {blank_accession_index.sum()} records with blank accession numbers")
        print(f"These occur in {len(dirs_with_blank_accession)} out of {len(all_dirs)} directories.")
    else:
        print("No remaining records have blank accession numbers. Stopping.")
        exit()

# Make numeric sort of dcm_subdir.
print("Sorting index by directory and numeric version of subdirectory.")
idf['dcm_subdir_sort'] = idf['dcm_subdir'].str.replace('im_', '').str.replace('-', '.').astype(float)
idf = idf.sort_values(by=['dcm_dir', 'dcm_subdir_sort'])

# Fill the blank records for AccessionNumber by grouping by dcm_dir, sorting by dcm_subdir_sort, then filling forward
# and backward.
print("Filling blank accession numbers by forward and backward copying of non-blank records in the same directory.")
idf['AccessionNumber'] = idf.groupby('dcm_dir')['AccessionNumber'].ffill().bfill()

# # Iterate the remaining directories and fill blank accessions
# n_blank = len(dirs_with_blank_accession)
# zeros = len(str(n_blank))
# counter = 0
# print("Filling blank accession numbers.")
# for this_dir in dirs_with_blank_accession:
#     counter += 1
#     print(f"\r{counter:0{zeros}} / {n_blank}", end='')
#     this_df = idf.loc[idf['dcm_dir'] == this_dir, :]
#     if sort_subdirs and (blank_multi == this_dir).any():
#         idf.loc[idf['dcm_dir'] == this_dir, 'AccessionNumber'] = this_df.sort_values(by='dcm_subdir_sort')['AccessionNumber'
#         ].fillna(method='ffill').fillna(method='bfill')
#     else:
#         idf.loc[idf['dcm_dir'] == this_dir, 'AccessionNumber'] = this_df['AccessionNumber'].fillna(method='ffill').fillna(method='bfill')

print("\nDone. Checking.")
n_blank = idf['AccessionNumber'].isnull().sum()
if n_blank == 0:
    print("Success: all blank accession numbers have been filled.")
    idf.to_parquet('/nfs/project/NeuroRadKCH/metadata/dicom_anon/id_index_fix_accessions.parquet')
else:
    print(f"Error: {n_blank} records still have blank accession numbers.")
    idf.to_parquet('/nfs/project/NeuroRadKCH/metadata/dicom_anon/id_index_fix_accessions_error.parquet')
