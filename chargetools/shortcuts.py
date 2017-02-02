"""
Convenience functions to parse files in mass.
"""
import glob
import os

from chargetools.exceptions import InputError


def parse_directory_for_charge(directory_path, extensions=None, base_molecule=None, **kwargs):
    """
    Parse all charge assignment files within a directory into a list of :class:`entities.MoleculeWithCharge` objects.

    :param directory_path: Path of directory to be searched.
    :param extensions: Extensions of files to be parsed.
    :param base_molecule: Base molecule for construction of all molecules.
    :param kwargs: Extra keyword arguments for the instantiation method of the charge objects.
    :return: A list of :class:`entities.MoleculeWithCharge` objects, parsed from files.
    """
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


