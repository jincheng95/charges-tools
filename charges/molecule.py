import os

import numpy as np

from charges.exceptions import InputError
from charges.utils import int_if_close


class Atom(object):
    def __init__(self, label, atomic_number, charge, position=None):
        self.label = label
        self.atomic_number = atomic_number
        self.charge = charge
        self.position = position

    @classmethod
    def from_ac_line(cls, ac_line_string):
        segments = ac_line_string.split()
        label, atomic_number = segments[1:3]
        position = np.array(segments[5:8])
        charge = int_if_close(float(segments[8]))
        return cls(label, atomic_number, charge, position=position)


class Bond(object):
    def __init__(self, *bonding_atoms, bond_order=1):
        self.bonding_atoms = bonding_atoms
        self.bond_order = bond_order

    @classmethod
    def from_ac_line(cls, ac_line_string, all_atoms):
        segments = ac_line_string.split()
        bonding_atom_labels = segments[2:4]
        bond_order = int(segments[4])
        return cls(*[all_atoms[int(label) - 1] for label in bonding_atom_labels],
                   bond_order=bond_order)


class Molecule(object):
    def __init__(self, atoms, bonds=None, name=None, charge=0):
        self.atoms = atoms
        self.bonds = bonds
        self.name = name
        self.charge = charge

    def __sizeof__(self):
        return len(self.atoms)

    @classmethod
    def from_ac_file(cls, ac_file_name, **kwargs):
        with open(ac_file_name, 'r') as f:
            lines = f.readlines()
        atom_lines, bond_lines = [], []
        for line in lines:
            if 'ATOM' in line:
                atom_lines.append(line)
            elif 'BOND' in line:
                bond_lines.append(line)

        # Read charge from first line
        # prefer integer if within 0.01 of a whole number
        charge = int_if_close(
            float(lines.pop(0).split()[1])
        )

        # Read atoms
        atoms = []
        for atom_line in atom_lines:
            atoms.append(Atom.from_ac_line(atom_line))

        # Read bonds
        bonds = []
        for bond_line in bond_lines:
            bonds.append(Bond.from_ac_line(bond_line, atoms))

        return cls(atoms, bonds=bonds, charge=charge, **kwargs)

    def __repr__(self):
        d = {
            'name': self.name,
            'no_atoms': len(self.atoms),
        }
        if len(self.atoms) > 1:
            d['no_atoms'] = "{0} atoms".format(d['no_atoms'])
        else:
            d['no_atoms'] = "1 atom"

        return "<Molecule: {name}, {no_atoms} atoms>".format(**d)


class MoleculeWithCharge(Molecule):
    all_sampling_schemes = {
        'CHelpG': ["(full, chelpg)", "chelpg"],
        "MK": ["(full, mk)", "mk"],
        "CHelp": ["(full, chelp)", "chelp"],
        "MK-UFF": ["(full, mkuff)", "mkuff"],
    }

    def __init__(self, charge_method, charge_file_name,
                 sampling_scheme=None,
                 is_restrained=None, is_averaged=None, is_equivalenced=None, is_compromised=None,
                 *args, **kwargs):
        self.charge_method = charge_method
        self.sampling_scheme = sampling_scheme
        self.charge_file_name = charge_file_name

        self.guess_charge_method(charge_file_name)
        if is_restrained is not None:
            self.is_restrained = is_restrained
        if is_averaged is not None:
            self.is_averaged = is_averaged
        if is_equivalenced is not None:
            self.is_equivalenced = is_equivalenced
        if is_compromised is not None:
            self.is_compromised = is_compromised

        super(MoleculeWithCharge, self).__init__(*args, **kwargs)

    def guess_charge_method(self, file_name):
        file_name = os.path.splitext(file_name)[0].lower()

        self.is_averaged = "compromise" in file_name
        self.is_restrained = "resp" in file_name or "restrain" in file_name
        self.is_equivalenced = "equivalence" in file_name or self.is_restrained
        self.is_compromised = "compromise" in file_name

        found = False
        for sampling_scheme_name, sampling_scheme_identifiers in self.all_sampling_schemes.items():
            for sampling_scheme_identifier in sampling_scheme_identifiers:
                if sampling_scheme_identifier.lower() in file_name:
                    self.sampling_scheme = sampling_scheme_name
                    found = True
                    break
            if found:
                break

    @classmethod
    def from_list(cls, file_name_full, base_molecule):
        with open(file_name_full, 'r') as f:
            line = f.read()

        if len(line.split()) != len(base_molecule):
            raise InputError('The list-formatted charge file must have the same number of list as the base molecule. '
                             'The base molecule (.ac file?) may point to a different molecule than this charges list.')



    @classmethod
    def mulliken_from_gaussian_log(cls, file_name_full, base_molecule):
        pass

    @classmethod
    def from_file(cls, file_name_full, *args, **kwargs):
        file_name, extension = os.path.splitext(file_name_full)

        parsers = {
            '.txt': cls.from_list,
        }
        parser_function = parsers.get(extension.lower())
        if parser_function is not None:
            return parser_function(file_name_full, *args, **kwargs)
