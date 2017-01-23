import os

from charges.exceptions import InputError


class Atom(object):
    def __init__(self, atomic_number, charge):
        self.atomic_number = atomic_number
        self.charge = charge


class Molecule(object):
    def __init__(self, *atoms, name=None):
        self.atoms = atoms
        self.name = name

    def __sizeof__(self):
        return len(self.atoms)


class MoleculeWithCharge(Molecule):
    def __init__(self, charge_method, charge_file_name,
                 is_restrained=False, is_averaged=False,
                 *args, **kwargs):
        self.charge_method = charge_method
        self.charge_file_name = charge_file_name
        self.is_restrained, self.is_averaged = is_restrained, is_averaged

        super(MoleculeWithCharge, self).__init__(*args, **kwargs)

    def guess_charge_method(self, file_name):
        file_name = os.path.splitext(file_name)[0]
        

    @classmethod
    def from_list(cls, file_name_full, base_molecule):
        with open(file_name_full, 'r') as f:
            line = f.read()

        if len(line.split()) != len(base_molecule):
            raise InputError('The list-formatted charge file must have the same number of list as the base molecule. '
                             'The base molecule (.ac file?) may point to a different molecule than this charges list.')

    @classmethod
    def from_file(cls, file_name_full, *args, **kwargs):
        file_name, extension = os.path.splitext(file_name_full)

        parsers = {
            '.txt': cls.from_list,
        }
        parser_function = parsers.get(extension.lower())
        if parser_function is not None:
            return parser_function(file_name_full, *args, **kwargs)
