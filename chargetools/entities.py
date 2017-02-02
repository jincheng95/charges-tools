from collections import OrderedDict
import os
import itertools
import re

import numpy as np
from copy import deepcopy

from collections import Iterable
from scipy.spatial.distance import cdist

from chargetools import constants, grids
from chargetools.exceptions import InputError
from chargetools.utils.utils import int_if_close, atomic_number_to_symbol, symbol_to_atomic_number


class Atom(object):
    """
    A container for basic properties for an atom.
    """

    def __init__(self, label, atomic_number, charge, position=None):
        self.label = int(label)
        self.atomic_number = int(atomic_number)
        self.symbol = atomic_number_to_symbol(atomic_number)
        self.charge = charge

        if isinstance(position, Iterable):
            self.position = np.array(list(map(float, position)))
        else:
            self.position = None

    def __repr__(self):
        if self.charge > 0:
            charge_str = "{0}+".format(self.charge)
        elif self.charge < 0:
            charge_str = "{0}-".format(abs(self.charge))
        else:
            charge_str = "neutral"

        return "<{0} ({1})>".format(self.symbol, charge_str)

    def __eq__(self, other):
        if isinstance(other, Atom):
            return other.label == self.label
        elif isinstance(other, int):
            return self.label == other

    def descriptor_compare(self, descriptor):
        if isinstance(descriptor, str):
            return self.symbol == descriptor
        elif isinstance(descriptor, int):
            return self.label == descriptor
        elif isinstance(descriptor, Atom) or issubclass(descriptor, Atom):
            return self is descriptor

    @classmethod
    def copy(cls, atom):
        """Construct a deep copy of an ``Atom`` object.

        :type atom: :class:`charges.molecule.Atom`
        :param atom: An instance of ``Atom`` to be copied.
        :rtype: :class:`charges.molecule.Atom`
        :return: A deep copy of the input ``Atom``.
        """
        return cls(atom.label, atom.atomic_number, atom.charge,
                   deepcopy(atom.position))

    @classmethod
    def from_ac_line(cls, ac_line_string):
        """
        Construct an ``Atom`` object from a line of ``.ac`` file generated by the AnteChamber tool.

        :type ac_line_string: str
        :param ac_line_string: A single, unmodified line from a AnteChamber format file,
            which starts with the word `ATOM`.
        :return: The ``Atom`` object representation filled with information extracted from input.
        """
        segments = ac_line_string.split()
        label, atom_str = segments[1:3]
        position = np.array(segments[5:8])
        charge = int_if_close(float(segments[8]))

        # Atom description in the format of Symbol + Label, e.g. N1, C2, etc.
        # Extract atom symbol by regex
        symbol = re.findall(r'[A-Z][a-z]?', atom_str)[0]
        return cls(label, symbol_to_atomic_number(symbol), charge, position=position)


class Bond(object):
    """
    A container for basic properties for a bond. Refers to instances of the :class:`Atom` object.
    """

    def __init__(self, *bonding_atoms, bond_order=1):
        self.bonding_atoms = bonding_atoms
        self.bond_order = bond_order

    @classmethod
    def copy(cls, bond, all_atoms):

        def find_atom_by_label(label, atoms):
            for _ in atoms:
                if label == _.label:
                    return _
            return None

        return cls(*[find_atom_by_label(atom.label, all_atoms) for atom in bond.bonding_atoms],
                   bond_order=bond.bond_order)

    @classmethod
    def from_ac_line(cls, ac_line_string, all_atoms):
        """
        Construct a ``Bond`` object from a line of ``.ac`` file generated by the AnteChamber tool.

        :type ac_line_string: str
        :param ac_line_string: A single, unmodified line from a AnteChamber format file,
            which starts with the word `BOND`.
        :type all_atoms: [Atom, ...]
        :param all_atoms: A list of :class:charges.molecule.Atom objects.
            Order of the atoms must confer to the order labelled by the AnteChamber file format.
        :return: The ``Bond`` object representation filled with information extracted from input.
        """
        segments = ac_line_string.split()
        bonding_atom_labels = segments[2:4]
        bond_order = int(segments[4])
        return cls(*[all_atoms[int(label) - 1] for label in bonding_atom_labels],
                   bond_order=bond_order)

    def contains(self, atom, label_only=False):
        """
        Checks if an atom is contained in this bond.

        :param atom: Atom to be checked.
        :param label_only: If `True`, perform a label comparison only.
            If `False`, check if the atom objects are same instances.
        :return: Whether the atom argument is one of the bonding atoms.
        """
        for bonding_atom in self.bonding_atoms:
            if not label_only and bonding_atom == atom:
                return True
            if label_only and atom.label == bonding_atom.label:
                return True
        return False


class Molecule(object):
    def __init__(self, atoms, bonds=None, name=None, charge=0):
        self.atoms = atoms
        self.bonds = bonds
        self.name = name
        self.charge = charge

    def __repr__(self):
        d = {
            'name': self.name,
            'no_atoms': len(self.atoms),
        }
        if len(self.atoms) > 1:
            d['no_atoms'] = "{0} atoms".format(d['no_atoms'])
        else:
            d['no_atoms'] = "1 atom"

        return "<Molecule: {name}, {no_atoms}>".format(**d)

    def __len__(self):
        return len(self.atoms)

    @classmethod
    def copy(cls, molecule):
        atoms = [Atom.copy(atom) for atom in molecule.atoms]

        if molecule.bonds:
            bonds = [Bond.copy(bond, atoms) for bond in molecule.bonds]
        else:
            bonds = None

        return cls(atoms, bonds, molecule.name, molecule.charge)

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

    @classmethod
    def from_cube_header(cls, header_lines, *args, **kwargs):
        atoms = []
        for index, line in enumerate(header_lines):
            segments = line.split()
            atomic_number = int(segments[0])
            atoms.append(Atom(index+1, atomic_number,
                              charge=int_if_close(float(segments[1]) - atomic_number),
                              position=np.array(list(map(float, segments[2:]))))
                         )
        return cls(atoms, *args, **kwargs)

    def select_label(self, *labels):
        try:
            if len(labels) == 1:
                return self.atoms[labels[0]-1]
            else:
                return zip([self.atoms[label-1] for label in labels])
        except IndexError:
            raise InputError('Label number argument is larger than the number of atoms contained in this molecule.')

    def select_symbol(self, *symbols):
        atoms = [atom for atom in self.atoms if atom.symbol in symbols]
        if len(atoms) == 1:
            return atoms[0]
        return atoms

    def list_of_atom_property(self, property_name):
        """
        Outputs a list of atom properties within field ``property_name`.
            For example, if ``property_name = 'atomic_number'``,
            this function will output a list of atomic numbers ordered by their labels.
        :param property_name: Key of the property of interest.
            Valid properties are: ``atomic_number``, ``label``, ``symbol``, ``position``, ``charge``.
        :return: List of properties.
        """
        return [vars(atom)[property_name] for atom in self.atoms]

    def if_bonded(self, atom, descriptor, min_bond_order=0.):
        """
        Check if argument atoms are bonded within the same bond.

        :param atom: can be either:
            *. a string of atom symbols, in which case all atoms with that atomic symbol count as being included.
            *. an integer of the atom's label.
            *. an atom object, in which case its label will be compared rather than an identity comparison.
        :param min_bond_order: Minimum bond order that counts as a chemical `bond`.
        :return: If all argument atoms are bonded in the same bond.
        """

        for i, bond in enumerate(self.bonds):
            has_atom, has_descriptor = False, False
            for bonding_atom in bond.bonding_atoms:
                if bonding_atom.descriptor_compare(atom):
                    has_atom = True
                elif bonding_atom.descriptor_compare(descriptor):
                    has_descriptor = True
            if has_atom and has_descriptor:
                return True
        return False

    def select_bonded(self, atom, min_bond_order=0.):
        """
        Select all atoms bonded to the input atom.

        :param min_bond_order: Minimum bond order with which an atom is bonded, for the atom to be included.
        :param atom: Atom descriptors, can be either:
            *. a string of atom symbols, in which case all atoms with that atomic symbol count as being included.
            *. an integer of the atom's label.
            *. an atom object, in which case its label will be compared rather than an identity comparison.
        :return: A list of all bonded atoms.
        """
        bonded_atoms = []
        for bond in self.bonds:
            if bond.contains(atom):
                bonded_atoms += [bonding_atom for bonding_atom in bond.bonding_atoms
                                 if bonding_atom is not atom and bond.bond_order > min_bond_order]
        return bonded_atoms

    def number_connections(self, atom_a, atom_b, min_bond_order=0.):
        """
        Get the number of bonds connecting atom A and atom B.

        :param atom_a: Atom A, must be an :class:`entities.Atom` object.
        :param atom_b: Atom B, must be an :class:`entities.Atom` object.
        :param min_bond_order: Minimum bond order for a connection to be counted.
        :return: Number of chemical bonds between two input atoms.
        """

        def iter_atoms(_a, _b, n, min_bond_order_, stop):
            if _a in self.select_bonded(_b, min_bond_order_):
                return n
            else:
                _n = n + 1
                if _n > stop:
                    return float("inf")
                for bonded in self.select_bonded(_b):
                    return iter_atoms(_a, bonded, _n, min_bond_order_, stop)

        return iter_atoms(atom_a, atom_b, 1, min_bond_order, len(self.bonds))


class MoleculeWithCharge(Molecule):
    all_sampling_schemes = OrderedDict()
    all_sampling_schemes['MK-UFF'] = ["(full, mkuff)", "mkuff", "mk-uff", "mk_uff", ]
    all_sampling_schemes['CHelpG'] = ["(full, chelpg)", "chelpg"]
    all_sampling_schemes['MK'] = ["(full, mk)", "mk", "merz", "kollman"]
    all_sampling_schemes['CHelp'] = ["(full, chelp)", "chelp"]

    all_charge_methods = {
        'NBO': ['nbo', 'natural'],
        'Mulliken': ['mulliken', 'mülliken'],
        "ESP": ['esp', 'potential', 'electrostatic'] + list(
            itertools.chain.from_iterable(all_sampling_schemes.values())
        ),
    }

    def __init__(self, charge_file_name, atoms,
                 charge_method=None,
                 sampling_scheme=None,
                 is_restrained=None, is_averaged=None, is_equivalenced=None, is_compromised=None,
                 *args, **kwargs):
        self.charge_file_name = charge_file_name

        self.guess_charge_method(charge_file_name)

        if charge_method is not None:
            self.charge_method = charge_method
        if sampling_scheme is not None:
            self.sampling_scheme = sampling_scheme
        if is_restrained is not None:
            self.is_restrained = is_restrained
        if is_averaged is not None:
            self.is_averaged = is_averaged
        if is_equivalenced is not None:
            self.is_equivalenced = is_equivalenced
        if is_compromised is not None:
            self.is_compromised = is_compromised

        super(MoleculeWithCharge, self).__init__(atoms, *args, **kwargs)

    def guess_charge_method(self, file_name):
        file_name = os.path.splitext(file_name)[0].lower()

        self.is_averaged = "average" in file_name
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
        else:
            self.sampling_scheme = None

        found = False
        for charge_method, charge_method_identifiers in self.all_charge_methods.items():
            for charge_method_identifier in charge_method_identifiers:
                if charge_method_identifier.lower() in file_name:
                    self.charge_method = charge_method
                    found = True
                    break
            if found:
                break
        else:
            self.charge_method = None

    @classmethod
    def from_plaintext_list(cls, file_name_full, base_molecule, *args, **kwargs):
        with open(file_name_full, 'r') as f:
            line = f.read()

        if len(line.split()) != len(base_molecule):
            raise InputError('The list-formatted charge file must have the same number of list as the base molecule. '
                             'The base molecule (.ac file?) may point to a different molecule than this charges list.')

        molecule = Molecule.copy(base_molecule)
        charge = 0
        for atom, charge_str in zip(molecule.atoms, line.split()):
            atom.charge = int_if_close(float(charge_str))
            charge += float(charge_str)

        return cls(file_name_full, molecule.atoms, bonds=molecule.bonds,
                   charge=int_if_close(charge), name=molecule.name, *args, **kwargs)

    @classmethod
    def from_gaussian_log(cls, file_name_full, base_molecule, *args, **kwargs):
        with open(file_name_full, 'r') as f:
            lines = f.readlines()

        # Locate starting point of ESP charges text block
        try:
            start_index = lines.index(" ESP charges:\n") + 2
        except ValueError:
            raise InputError('Cannot find charge information within this Gaussian log file.')

        # Parse the input keywords to find the sampling scheme
        sampling_scheme = False
        for line in lines[58:158]:
            if sampling_scheme:
                break
            for segment in line.split():
                if "pop=" in segment:
                    # look if keyword contains default set of keywords
                    for name, identifiers in cls.all_sampling_schemes.items():
                        if sampling_scheme:
                            break
                        for identifier in identifiers:
                            if identifier.lower() in segment.lower():
                                sampling_scheme = name
                            if sampling_scheme:
                                break

        if not sampling_scheme:
            raise InputError('Cannot find sampling scheme information within this Gaussian log file.')

        molecule = Molecule.copy(base_molecule)
        for atom, line in zip(molecule.atoms, lines[start_index:]):
            if "Sum of ESP charges" in line:
                total_charge_str = line.split()[-1]
                break
            if len(line.split()) >= 3:
                charge_str = line.split()[-1]
                atom.charge = int_if_close(float(charge_str))

        try:
            total_charge_str
        except NameError:
            total_charge_str = '0'

        return cls(file_name_full, molecule.atoms, bonds=molecule.bonds,
                   charge=int_if_close(float(total_charge_str)),
                   is_averaged=False, is_compromised=False, is_equivalenced=False, is_restrained=False)

    @classmethod
    def from_file(cls, file_name_full, base_molecule, *args, **kwargs):
        file_name, extension = os.path.splitext(file_name_full)

        parsers = {
            '.txt': cls.from_plaintext_list,
            '.log': cls.from_gaussian_log,
        }
        parser_function = parsers.get(extension.lower())
        if parser_function is not None:
            return parser_function(file_name_full, base_molecule, *args, **kwargs)
        raise InputError('Extension not supported by any of the parser functions.')

    @classmethod
    def mulliken_from_gaussian_log(cls, file_name_full, base_molecule):
        pass

    @property
    def charge_on(self, atom_label):
        """
        Output charge borne by a labelled atom.
        """
        for atom in self.atoms:
            if atom.label == atom_label:
                return atom.charge
        raise ValueError('Atom with this label has not been found.')

    def reproduce_cube(self, template_cube,  **kwargs):
        """
        Based on the respective charges of atoms within this molecule,
            reproduce the 3-dimensional electrostatic potential as a :class:`charges.cube.Cube` object.

        :param template_cube: The reproduced volume will have the same points density and size to this template cube.
        :param kwargs: Extra keyword arguments to pass to the :func:`scipy.spatial.distance.cdist` function,
            which calculates the distances.
            By default, the Euclidean distances are used.
        :return: Reproduced potential stored within a new :class:`charges.cube.Cube` object.
        """
        atomic_charges = np.array(self.list_of_atom_property('charge'))
        positions = np.array(template_cube.molecule.list_of_atom_property('position'))

        # Calculate the distances
        distances = cdist(template_cube.flat_coordinates, positions, **kwargs)
        # Calculate per-atom potential, then sum
        potentials = (np.array(atomic_charges) / distances).sum(axis=1)

        return grids.Cube.assign_new_values_to(template_cube, potentials.reshape(template_cube.n_voxels))

    def error_cube(self, potential, **kwargs):
        """
        Based on the respective charges of atoms within this molecule,
            calculate the 3D electrostatic potential subtracted by the actual potential values.
            This is a wrapper function for the :method:`entities.MoleculeWithCharge.reproduceCube` method.

        :param potential: A :class:`grids.Cube` object containing the actual potential.
        :param kwargs: Extra keyword arguments to be passed to the distance transform method,
            from which distances to atoms are evaluated.
        :return: Cube object containing errors of the electrostatic potential.
        """
        return grids.Cube.assign_new_values_to(potential,
                                               self.reproduce_cube(potential, **kwargs) - potential,
                                               )
