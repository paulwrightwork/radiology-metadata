import argparse
from pathlib import Path

import pydicom


def main(input_dir: str, desc: str | None = None):
    """Fix SeriesDescription in DICOM files from Insight46

    If the `desc` argument is not set, the script will output the unique series descriptions in the series directory. If the `desc` argument is set, the script will update the SeriesDescription in all DICOM files in the series directory to the new value.
    
    Args:
        input_dir (str): Path to series directory containing DICOM files.
        desc (str, optional): New SeriesDescription to set.

    Outputs:
        DICOM files with updated SeriesDescription.

    Returns:
        None
    """
    print(f"Fixing SeriesDescription in {input_dir}")
    input_path = Path(input_dir)
    
    dcm_files  = list(input_path.glob("*.dcm"))
    if len (dcm_files) == 0:
        raise FileNotFoundError(f"No .dcm files found in {input_dir}")

    if desc:
        for dcm in dcm_files:
            try:
                ds = pydicom.dcmread(dcm)
                if ds.SeriesDescription != desc:
                    print(f"{dcm.name}: '{ds.SeriesDescription}' -> '{desc}'")
                    ds.SeriesDescription = desc
                    ds.save_as(dcm)
            except Exception as e:
                print(f"Failed to read DICOM file {dcm}: {e}")
    else:
        descs = set()
        for dcm in dcm_files:
            try:
                ds = pydicom.dcmread(dcm)
                descs.add(ds.SeriesDescription)
            except Exception as e:
                print(f"Failed to read DICOM file {dcm}: {e}")
        print(f"Unique SeriesDescriptions in {input_dir}:")
        for d in descs:
            print(f"  {d}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fix SeriesDescription in DICOM files.")
    parser.add_argument(
        '--input_dir',
        required=True,
        help='Path to series directory containing DICOM files.'
    )
    parser.add_argument(
        '--desc',
        required=False,
        help='New SeriesDescription to set.'
    )
    args = parser.parse_args()

    main(input_dir=args.input_dir, desc=args.desc)