import re


class NBO:
    """A class to help parsing E(2) perturbation energies from NBO analysis outputted by Gaussian."""

    def __init__(self, file_name, **kwargs):
        self.file_name = file_name

        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def read(cls, fname):
        d = dict(perturbation=[])
        e2_parsing = False

        f = open(fname, 'r')
        for line in f:
            # SECOND ORDER PERTURBATION THEORY ANALYSIS OF FOCK MATRIX IN NBO BASIS.
            if e2_parsing:
                if not re.search(r'\S+', line):
                    next_line = next(f)
                    if not re.search(r'\S+', next_line):
                        e2_parsing = False
                else:
                     segments = [s for s in line.split(sep='  ') if s]

                     if len(segments) == 5:
                        donor_str, acceptor_str, e2, energy_diff, fock_param = segments
                        donor = NaturalOrbital.from_nbo_log(donor_str)
                        acceptor = NaturalOrbital.from_nbo_log(acceptor_str)
                        e2, energy_diff, fock_param = map(float, segments[-3:])
                        d['perturbation'].append(NBOPerturbation(donor, acceptor, e2, energy_diff, fock_param))

            else:
                if line.split() == '  Donor NBO (i)   Acceptor NBO (j)  kcal/mol   a.u.    a.u.'.split():
                    e2_parsing = True

        f.close()
        return cls(fname, **d)


class NBOPerturbation:
    def __init__(self, donor, acceptor, e2, energy_diff, fock_param):
        self.donor, self.acceptor = donor, acceptor
        self.e2 = e2
        self.energy_diff = energy_diff
        self.fock_param = fock_param
        self.related_atoms = self.donor.related_atoms + self.acceptor.related_atoms


class NaturalOrbital:
    """A NBO natural orbital."""

    def __init__(self, is_lewis, orbital_type, related_atoms):
        self.is_lewis = is_lewis
        self.orbital_type = orbital_type
        self.related_atoms = [int(related_atom) for related_atom in related_atoms]

    @classmethod
    def from_nbo_log(cls, string):
        main, *segments = string.split('-')
        orbital_type, asterisk_str, orbital_number, atom_label_1 = re.search(
            r'\d+\.\s+(BD|RY|CR|LP)(\*?)\s*\((\s*\d+)\)\s*\w+\s*(\d+)', main).groups()

        related_atoms = [atom_label_1]
        for segment in segments:
            atom_label = re.search(r'\w+\s*(\d+)', segment).group(1)
            related_atoms.append(atom_label)

        return cls(asterisk_str == '*', orbital_type, related_atoms)
