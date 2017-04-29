import re
from copy import copy

import numpy as np

from chargetools.utils.utils import consume_lines, genfromstring


class AIM:
    """Contains data output from the AIMALL program in the .sumviz format."""

    def __init__(self, fname, **kwargs):
        self.file_name = fname

        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def read(cls, fname):

        # Ideally should do this in a context manager,
        # but here we close file wrapper manually to avoid a long block of indentation
        f = open(fname, 'r')

        d = dict(critical_points=[])
        for line in f:
            # Nuclear charge & coordinates
            if line.split() == ['Nuclear', 'Charges', 'and', 'Cartesian', 'Coordinates:']:
                block = consume_lines(f)
                d['nuclear_charges'] = genfromstring(block, usecols=(1,), dtype=float)
                d['coordinates'] = genfromstring(block, usecols=(2, 3, 4), dtype=float)

            # Atomic properties
            elif line.split() == ['Some', 'Atomic', 'Properties:']:
                block = consume_lines(f, skip=9)
                (_, d['atom_charges'], d['atom_lagrangians'], d['atomic_kinetic_energies'],
                 d['atomic_k_scaled'], d['atomic_dipole_moment']
                 ) = genfromstring(block, dtype=float, unpack=True, skip_footer=2)

            # Individual critical points
            elif line[:3] == 'CP#':
                header_line = copy(line)
                block = header_line + consume_lines(f, skip=0)
                d['critical_points'].append(CriticalPoint.from_aimall(block))

            # Atomic electron populations
            elif line.split() == 'Atomic Electron Populations, Localization and Delocalization Data:'.split():
                block = consume_lines(f, 16)
                d['electron_pop'], d['localized_electron_pop'] = genfromstring(
                    block, usecols=(1,2), dtype=float, unpack=True, skip_footer=2
                )

        f.close()
        return cls(fname, **d)


class CriticalPoint:

    def __init__(self, coords, point_type, critical_type, related_atoms, rho, grad_rho,
                 hessian_eigenvals, hessian_eigenvec):
        self.coords = coords
        self.type = point_type # tuple e.g. (3, -1)
        self.critical_type = critical_type
        self.related_atoms = related_atoms # labels
        self.rho = rho
        self.grad_rho = grad_rho
        self.hess_eigenvals = hessian_eigenvals
        self.hess_eigenvec = hessian_eigenvec


    @classmethod
    def from_aimall(cls, string):
        # type of critical point and related atoms
        point_type_1, point_type_2, critical_type, atoms_text = re.search(
            r'Type = \(([\-\+]?[1-3]),([\-\+]?[1-3])\)\s+(\w+)\s+(..+)', string
        ).groups()
        related_atoms = np.array(re.findall(r'\d+', atoms_text), dtype=int)

        # coordinates of this critical point
        coords = np.array(re.search(
            r'Coords\s+=\s+(-?\d+\.?\d+E[\+\-]\d+)\s+(-?\d+\.?\d+E[\+\-]\d+)\s+(-?\d+\.?\d+E[\+\-]\d+)', string
        ).groups(), dtype=float)

        # other info
        rho = float(re.search(
            r'Rho\s+=\s+(-?\d+\.?\d+E[\+\-]\d+)', string
        ).group(1))
        grad_rho = np.array(re.search(
            r'GradRho\s+=\s+(-?\d+\.?\d+E[\+\-]\d+)\s+(-?\d+\.?\d+E[\+\-]\d+)\s+(-?\d+\.?\d+E[\+\-]\d+)', string
        ).groups(), dtype=float)
        hess_eigenvals = np.array(re.search(
            r'HessRho_EigVals\s+=\s+(-?\d+\.?\d+E[\+\-]\d+)\s+(-?\d+\.?\d+E[\+\-]\d+)\s+(-?\d+\.?\d+E[\+\-]\d+)', string
        ).groups(), dtype=float)
        hess_eigenvectors = np.array(
            re.findall(r'HessRho_EigVec[1-3]\s+=\s+(-?\d+\.?\d+E[\+\-]\d+)\s+(-?\d+\.?\d+E[\+\-]\d+)\s+(-?\d+\.?\d+E[\+\-]\d+)', string), dtype=float
        )

        return cls(coords, (point_type_1, point_type_2), critical_type, related_atoms,
                   rho, grad_rho, hess_eigenvals, hess_eigenvectors
                   )

