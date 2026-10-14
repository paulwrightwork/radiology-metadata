from pathlib import Path

from pydicom import dcmread
from tqdm import tqdm
import pandas as pd
import re


def mod11(x):
    """Does the modulus 11 test on NHS numbers. Expects a string of ten digits. See:
     https://en.wikipedia.org/wiki/NHS_number#Format"""
    if not isinstance(x, str):
        return False
    x = re.sub(r'\D', '', x)
    if not re.match(r'^[0-9]{10}$', x):
        return False
    checksum = 0
    for digit in range(9):
        checksum += int(x[digit]) * (10 - digit)
    check_digit = checksum % 11
    check_digit = 11 - check_digit
    if check_digit == 11:
        check_digit = 0
    return check_digit == int(x[9])


# Tags to remove supplied by Sharaf Ayinla
tags_to_remove = [(0x0002, 0x0016), (0x0008, 0x0080), (0x0008, 0x0081), (0x0008, 0x0090), (0x0008, 0x1032),
                  (0x0008, 0x0201), (0x0008, 0x1010), (0x0008, 0x1040), (0x0008, 0x1070), (0x0008, 0x1048),
                  (0x0010, 0x0010), (0x0010, 0x0020), (0x0010, 0x0021), (0x0010, 0x0030), (0x0018, 0x1000),
                  (0x0010, 0x1002), (0x0018, 0x1020), (0x0018, 0x1030), (0x0018, 0x9506), (0x0008, 0x1050),
                  (0x0010, 0x0021), (0x0010, 0x0032), (0x0010, 0x0050), (0x0010, 0x0101), (0x0010, 0x0102),
                  (0x0010, 0x1000), (0x0010, 0x1001), (0x0010, 0x1002), (0x0010, 0x1005), (0x0010, 0x1040),
                  (0x0010, 0x1050), (0x0010, 0x1060), (0x0010, 0x1080), (0x0010, 0x1081), (0x0010, 0x1090),
                  (0x0010, 0x2000), (0x0010, 0x2110), (0x0010, 0x2150), (0x0010, 0x2152), (0x0010, 0x2154),
                  (0x0010, 0x2180), (0x0010, 0x21B0), (0x0010, 0x21D0), (0x0010, 0x21F0), (0x0010, 0x2297),
                  (0x0010, 0x2299), (0x0010, 0x4000), (0x0029, 0x1009), (0x0029, 0x1019), (0x0032, 0x0012),
                  (0x0032, 0x1020), (0x0032, 0x1021), (0x0032, 0x1030), (0x0032, 0x1032), (0x0032, 0x1033),
                  (0x0032, 0x1070), (0x0032, 0x4000), (0x0038, 0x0010), (0x0038, 0x0011), (0x0038, 0x001E),
                  (0x0038, 0x0020), (0x0038, 0x0021), (0x0038, 0x0040), (0x0038, 0x0050), (0x0038, 0x0060),
                  (0x0038, 0x0061), (0x0038, 0x0062), (0x0038, 0x0300), (0x0038, 0x0400), (0x0038, 0x0500),
                  (0x0038, 0x1234), (0x0038, 0x4000), (0x0040, 0x0001), (0x0040, 0x0002), (0x0040, 0x0003),
                  (0x0040, 0x0004), (0x0040, 0x0005), (0x0040, 0x0006), (0x0040, 0x0007), (0x0040, 0x000B),
                  (0x0040, 0x0010), (0x0040, 0x0011), (0x0040, 0x0012), (0x0040, 0x0241), (0x0040, 0x0242),
                  (0x0040, 0x0243), (0x0040, 0x0244), (0x0040, 0x0245), (0x0040, 0x0248), (0x0040, 0x0253),
                  (0x0040, 0x0254), (0x0040, 0x0275), (0x0040, 0x0280), (0x0040, 0x0555), (0x0040, 0x1004),
                  (0x0040, 0x1005), (0x0040, 0x1010), (0x0040, 0x1011), (0x0040, 0x1102), (0x0040, 0x1103),
                  (0x0040, 0x1400), (0x0040, 0x2001), (0x0040, 0x2008), (0x0040, 0x2009), (0x0040, 0x2010),
                  (0x0040, 0x2400), (0x0040, 0x3001), (0x0040, 0x4025), (0x0040, 0x4027), (0x0040, 0x4030),
                  (0x0040, 0x4034), (0x0040, 0x4035), (0x0040, 0x4036), (0x0040, 0x4037), (0x0040, 0xA027),
                  (0x0040, 0xA078), (0x0040, 0xA07A), (0x0040, 0xA07C), (0x0040, 0xA730), (0x0040, 0xA123),
                  (0x0054, 0x0200), (0x0054, 0x0410), (0x0070, 0x0086), (0x0088, 0x0200), (0x0088, 0x0904),
                  (0x0088, 0x0906), (0x0088, 0x0910), (0x0088, 0x0912), (0x0400, 0x0100), (0x0400, 0x0402),
                  (0x0400, 0x0403), (0x0400, 0x0404), (0x0400, 0x0550), (0x0400, 0x0561), (0x2030, 0x0020),
                  (0x4000, 0x0010), (0x4000, 0x4000), (0x4008, 0x0042), (0x4008, 0x0102), (0x4008, 0x010A),
                  (0x4008, 0x010B), (0x4008, 0x010C), (0x4008, 0x0111), (0x4008, 0x0114), (0x4008, 0x0115),
                  (0x4008, 0x0118), (0x4008, 0x0119), (0x4008, 0x011A), (0x4008, 0x0202), (0x4008, 0x0300),
                  (0x4008, 0x4000)]

dicom_in = Path('/nfs/project/NeuroRadKCH/sourcedata/dicom')
bad_accession_dirs_file = Path('/nfs/project/NeuroRadKCH/metadata/dicom_anon/bad_accession_dirs.csv')
dicom_out = Path('/nfs/project/NeuroRadKCH/sourcedata/dicom_anon')
overwrite = True
bad_pat = re.compile(r'^[a-zA-Z]\d{6}20')

# Script body
print(f'Anonymising DICOM files with bad accession numbers in {dicom_in}')
#print('Listing DICOM files.')
#dicom_files = [d for d in dicom_in.glob('**/*.dcm')]
print('Loading list of DICOM directories with bad accession numbers.')
bad_accession_dirs = pd.read_csv(bad_accession_dirs_file, dtype=str)
n_dicom = bad_accession_dirs.shape[0]
print(f"Found {n_dicom} dirs.")

print(f"Checking DICOM index for any additional possible bad accession numbers using regex: '{bad_pat}'.")
di = pd.read_parquet('/nfs/project/NeuroRadKCH/metadata/dicom_index.parquet')
di['accession_like_hn'] = di['AccessionNumber'].str.contains(bad_pat, na=False)
print(f"Found {di['accession_like_hn'].sum()} accession numbers that look like hospital numbers.")
di['accession_like_nhs'] = di['AccessionNumber'].apply(mod11)
print(f"Found {di['accession_like_nhs'].sum()} accession numbers that look like NHS numbers.")
di['bad_accession'] = di['accession_like_hn'] | di['accession_like_nhs']
bad_accession_dirs_extra = di.loc[di['bad_accession'], ['dcmdir', 'dcmsubdir']].drop_duplicates()
if bad_accession_dirs_extra.shape[0] > 0:
    print(f"Found total {bad_accession_dirs_extra.shape[0]} directories with possible bad accession numbers ", end="")
    bad_accession_dirs_extra.rename(columns={'dcmdir': 'dcm_dir', 'dcmsubdir': 'dcm_subdir'}, inplace=True)
    bad_accession_dirs = pd.concat([bad_accession_dirs, bad_accession_dirs_extra], ignore_index=True
                                   ).drop_duplicates()
    if bad_accession_dirs.shape[0] > n_dicom:
        print(f"and added {bad_accession_dirs.shape[0] - n_dicom} new directories to the list.")
        n_dicom = bad_accession_dirs.shape[0]
    else:
        print("but all of them were already in the list of bad dirs.")

skipped = 0
query_files = []
for index, row in tqdm(bad_accession_dirs.iterrows(), total=n_dicom):
    dicom_dir = dicom_in / row['dcm_dir'] / row['dcm_subdir']
    dicom_files = [d for d in dicom_dir.glob('*.dcm')]
    for dicom_file in dicom_files:
        dicom_file_anon = Path(str(dicom_file).replace(str(dicom_in), str(dicom_out)))
        if dicom_file_anon.exists() and not overwrite:
            skipped += 1
            continue

        d = dcmread(dicom_file)
        del d['AccessionNumber']
        for group, tag in tags_to_remove:
            # Delete tags to remove
            if (group, tag) in d:
                del d[group, tag]

        if not dicom_file_anon.parent.exists():
            dicom_file_anon.parent.mkdir(parents=True)
        d.save_as(dicom_file_anon)
        del d, dicom_file, dicom_file_anon
print("\nDone.\n")

if skipped > 0:
    print(f'Skipped {skipped} files that already existed.\n')
print('\n')
