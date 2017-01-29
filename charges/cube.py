from collections import OrderedDict

import numpy as np

from charges.exceptions import InputError
from charges.molecule import Molecule

AXES_NAMES = ('x', 'y', 'z',)


class Cube(object):
    """
    A object that stores information extracted from Gaussian Cube files,
        including the Cartesian axes, the volume of the cube, the density of points,
        atom identities, atom positions,
        and of course the value at each point of the 3D volume.
    """

    def __init__(self, file_name, values, axes, molecule,
                 origins=None, unit_vectors=None, n_voxels=None,
                 ):
        self.from_file = file_name
        self.values = values
        self.axes = axes
        self.molecule = molecule
        self.origins, self.unit_vectors, self.n_voxels = origins, unit_vectors, n_voxels

    @classmethod
    def from_cube_file(cls, file_name, base_molecule=None):
        """
        Instantiate a ``Cube`` object by reading from a stored Gaussian cube (``.cub``) file.

        :type file_name: str
        :param file_name: Path to the ``.cub`` file.
        :param base_molecule: Give a base molecule related to this cube.
            Otherwise, the Gaussian cube file header will be parsed into a :class:`charges.molecule.Molecule`.
            Note the header only contains minimal information about the molecule.

        :rtype: charges.cube.Cube
        :return: A :class:`charges.cube.Cube` object.
        """

        with open(file_name, 'r') as f:
            lines = f.readlines()

        # Read the number of atoms and the origin of the volumetric data
        origin_line = lines[2].split()
        n_atoms = int(origin_line[0])
        origins = np.array(list(map(float, origin_line[1:4])))

        # Read the unit vectors and number of voxels per line
        unit_vectors = []
        n_voxels = []
        for line in lines[3:6]:
            segments = line.split()
            vector = map(float, segments[1:])
            for scalar_length in vector:
                # only support orthogonal axes for now
                if abs(scalar_length - 0.) >= 0.01:
                    unit_vectors.append(scalar_length)
            n_voxels.append(int(line.split()[0]))
        unit_vectors, n_voxels = np.array(unit_vectors), np.array(n_voxels)

        # Store atom positions
        if base_molecule is None:
            atom_header = lines[6:6+n_atoms]
            base_molecule = Molecule.from_cube_header(atom_header)

        # Create a 1-dimensional flat array containing values in the .cub file
        value_str = ''.join(lines[6+n_atoms:])
        values = np.fromstring(value_str, sep=" ").reshape(n_voxels)

        # Create 1D arrays describing 3 coordinates
        axes = OrderedDict()
        zipped_axes_attributes = zip(AXES_NAMES, origins, unit_vectors, n_voxels)
        for axis_name, origin, unit_vector, n_voxel in zipped_axes_attributes:
            axes[axis_name] = np.arange(0, n_voxel) * unit_vector + origin

        return cls(file_name, values, axes, base_molecule,
                   origins, unit_vectors, n_voxels)

    @classmethod
    def assign_new_values_to(cls, original_cube, new_values):
        """
        Provide a deep copy of the original cube but with new values assigned to each point in the 3D volume.

        :type: charges.cube.Cube
        :param original_cube: Original cube object from which meta-data should be copied.
        :type new_values: numpy.array
        :param new_values: New values for the cube.
            The numpy array should have the same shape as the value array of the original cube.

        :rtype: charges.cube.Cube
        :return: A new ``Cube`` object with new assigned values.
        """
        args = (original_cube.axes, original_cube.molecule,
                original_cube.origins, original_cube.unit_vectors, original_cube.n_voxels,
                )
        return cls(original_cube.from_file, new_values, *args)

    @property
    def meshgrid(self, sparse=False):
        """
        Returns coordinates matrices of the 3D Cartesian volumes.
        See `https://docs.scipy.org/doc/numpy/reference/generated/numpy.meshgrid.html` for details.

        For example, the x-axis meshgrid will contain
            [[x1 repeated for i times, where i is the number of points on the y axis],
             [x2 repeated for j times, where j is the number of points on the z axis],
             ...
             [xn ... i times], [xm ... j times] where n is the number of points on the x axis
            ]

        :rtype: tuple of numpy arrays
        :return: N-D coordinate arrays for vectorised N-D scalar fields over N-D grids,
            given the stored N 1D coordinate arrays x1 ... xn, y1 ... yn, z1 ... zn.
        """
        return np.meshgrid(*list(self.axes.values()), sparse=sparse)

    @property
    def flat_coordinates(self):
        """
        Returns a 1D array of N-coordinates of each point.

        :rtype: numpy.array
        :return: A numpy array which contains the value of coordinates at all three dimensions,
            i.e. [x1, y1, z1], [x2, y2, z2], ... [xn, yn, zn].
        """
        meshgrid = np.array(self.meshgrid)
        return np.vstack(meshgrid.reshape(len(self.axes), -1)).T

    def filter_values(self, condition, replace_with=np.nan):
        """
        Make a new numpy array containing values in the 3D volume,
            but with values replaced with a constant if the value satisfies a certain condition.

        :type condition: function | numpy.array
        :param condition: If a function, a value will be replaced if the function returns `True`.
            This function should accept one argument, which is a single value.

            If a numpy array, the value will be replaced if the argument's corresponding element
            at the same position within `self.values` is `False`.
        :param replace_with: Replace matching element with this constant. Defaults to `numpy.nan`.
        :return: A filtered numpy array with replaced values.
        """
        if callable(condition):
            mask_array = condition(self.values)
        elif isinstance(condition, (np.ndarray, np.generic,)):
            mask_array = condition
        else:
            raise InputError("Condition argument must be a callable function or a masking numpy array.")
        return np.where(mask_array, self.values, replace_with)

    def points_labelled_by_closest_atom(self, *atom_label_numbers):
        # if atom_label_numbers:
        #     atom_positions = self.atom_positions[[atom_label_numbers]]
        #     closest_by_args = cdist(self.flat_coordinates, atom_positions).argmin(axis=1).reshape(self.n_voxels)
        #     return np.vectorize(atom_label_numbers.__getitem__)(closest_by_args)
        # else:
        #     atom_positions = self.atom_positions
        #     return cdist(self.flat_coordinates, atom_positions).argmin(axis=1).reshape(self.n_voxels)
        pass

    def distance_to_closest_atom(self, *atom_label_numbers):
        # if atom_label_numbers:
        #     atom_positions = self.atom_positions[[atom_label_numbers]]
        # else:
        #     atom_positions = self.atom_positions
        # return cdist(self.flat_coordinates, atom_positions).min(axis=1).reshape(self.n_voxels)
        pass

    @property
    def grid_args(self):
        return self.axes, self.molecule, self.origins, self.unit_vectors, self.n_voxels

    def __add__(self, other):
        args = self.grid_args
        if isinstance(other, int) or isinstance(other, float) or isinstance(other, np.ndarray):
            return Cube(self.from_file, self.values + other, *args)
        elif isinstance(other, Cube):
            if self.values.shape != other.values.shape:
                raise AttributeError("Cube files must have the same coordinates to be summed.")
            return Cube(self.from_file, self.values + other.values, *args)
        else:
            raise AttributeError

    def __sub__(self, other):
        if isinstance(other, int) or isinstance(other, float) or isinstance(other, np.ndarray):
            return self.assign_new_values_to(self, self.values - other)
        elif isinstance(other, Cube):
            if self.values.shape != other.values.shape:
                raise AttributeError("Cube files must have the same coordinates to be summed.")
            return self.assign_new_values_to(self, self.values - other.values)
        else:
            raise AttributeError

    def __mul__(self, other):
        args = self.grid_args
        if isinstance(other, int) or isinstance(other, float) or isinstance(other, np.ndarray):
            return Cube(self.from_file, self.values * other, *args)
        elif isinstance(other, Cube):
            if self.values.shape != other.values.shape:
                raise AttributeError("Cube files must have the same coordinates to be summed.")
            return Cube(self.from_file, self.values * other.values, *args)
        else:
            raise AttributeError

    def __truediv__(self, other):
        args = self.grid_args
        if isinstance(other, int) or isinstance(other, float) or isinstance(other, np.ndarray):
            return Cube(self.from_file, self.values * other, *args)
        elif isinstance(other, Cube):
            if self.values.shape != other.values.shape:
                raise AttributeError("Cube files must have the same coordinates to be summed.")
            return Cube(self.from_file, self.values * other.values, *args)
        else:
            raise AttributeError

    def __pow__(self, power, modulo=None):
        args = self.grid_args
        if isinstance(power, int) or isinstance(power, float) or isinstance(power, np.ndarray):
            return Cube(self.from_file, self.values ** power, *args)
        elif isinstance(power, Cube):
            if self.values.shape != power.values.shape:
                raise AttributeError("Cube files must have the same coordinates to be summed.")
            return Cube(self.from_file, self.values ** power.values, *args)
        else:
            raise AttributeError

    def __abs__(self):
        return self.assign_new_values_to(self, np.abs(self.values))


