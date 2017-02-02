"""
Convenience functions to parse files in mass.
"""
import glob
import os

from chargetools.exceptions import InputError


def parse_directory_for_charge(directory_path, extensions=None, base_molecule=None, **kwargs):
    valid_files = []
    # For each possible extension, produce glob matching string, e.g. /path/*.log, /path/*.txt, etc.
    if extensions is not None:
        for extension in extensions:
            extension = extension.lower()
            if extension[0] != ".":
                extension = "." + extension

            query = os.path.join(directory_path, '*' + extension)

            # the glob module matches * with any wild cards
            # keep a list of all file paths that need parsing
            valid_files += glob.glob(query)
    else:
        valid_files = glob.glob(directory_path + '*')

    from chargetools import entities
    if base_molecule is None:
        ac_query = os.path.join(directory_path, '*.ac')
        files = glob.glob(ac_query)[0]
        if len(files) > 0:
            raise InputError('Multiple .ac files found within directory. '
                             'Please specify base molecule, or delete duplicate .ac files from directory.')
        base_molecule = entities.Molecule.from_ac_file(ac_query, **kwargs)

    return [entities.MoleculeWithCharge.from_file(valid_file, base_molecule) for valid_file in valid_files]


