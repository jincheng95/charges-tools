from collections import OrderedDict
import numpy as np
from scipy.spatial.distance import cdist


AXES_NAMES = ('x', 'y', 'z',)
empty_ndarray = np.array([])


class Cube(object):

    def __init__(self, file_name, values, axes,
                 n_atoms=0, atom_positions=empty_ndarray, atomic_numbers=empty_ndarray, atom_charges=empty_ndarray,
                 origins=empty_ndarray, unit_vectors=empty_ndarray, n_voxels=empty_ndarray,
                 ):
        self.from_file = file_name
        self.values = values
        self.axes = axes
        self.n_atoms = n_atoms
        self.atom_positions, self.atomic_numbers, self.atom_charges = atom_positions, atomic_numbers, atom_charges
        self.origins, self.unit_vectors, self.n_voxels = origins, unit_vectors, n_voxels

    @classmethod
    def from_cube_file(cls, file_name):

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
        atom_str = ''.join(lines[6:6+n_atoms])
        atom_array = np.fromstring(atom_str, sep=" ").reshape(-1, 5)
        atomic_numbers = atom_array[..., 0]
        atom_charges = atom_array[..., 1]
        atom_positions = atom_array[..., 2:]

        # Create a 1-dimensional flat array containing values in the .cub file
        value_str = ''.join(lines[6+n_atoms:])
        values = np.fromstring(value_str, sep=" ").reshape(n_voxels)

        # Create 1D arrays describing 3 coordinates
        axes = OrderedDict()
        zipped_axes_attributes = zip(AXES_NAMES, origins, unit_vectors, n_voxels)
        for axis_name, origin, unit_vector, n_voxel in zipped_axes_attributes:
            axes[axis_name] = np.arange(0, n_voxel) * unit_vector + origin

        return cls(file_name, values, axes,
                   n_atoms, atom_positions, atomic_numbers, atom_charges,
                   origins, unit_vectors, n_voxels)

    @classmethod
    def assign_new_values_to(cls, original_cube, new_values):
        args = (original_cube.axes,
                original_cube.n_atoms, original_cube.atom_positions, original_cube.atomic_numbers,
                original_cube.atom_charges,
                original_cube.origins, original_cube.unit_vectors, original_cube.n_voxels,
                )
        return cls(original_cube.from_file, new_values, *args)

    @property
    def meshgrid(self):
        return np.meshgrid(*list(self.axes.values()))

    @property
    def flat_coordinates(self):
        meshgrid = np.array(self.meshgrid)
        return np.vstack(meshgrid.reshape(len(self.axes), -1)).T

    def filter_values(self, condition, replace_with=np.nan):
        if callable(condition):
            mask_array = condition(self.values)
        elif isinstance(condition, (np.ndarray, np.generic,)):
            mask_array = condition
        else:
            raise InputError("Condition argument must be a callable function or a masking numpy array.")
        return np.where(mask_array, self.values, replace_with)

    def closest_atom(self, *atom_label_numbers):
        if atom_label_numbers:
            atom_positions = self.atom_positions[[atom_label_numbers]]
            closest_by_args = cdist(self.flat_coordinates, atom_positions).argmin(axis=1).reshape(self.n_voxels)
            return np.vectorize(atom_label_numbers.__getitem__)(closest_by_args)
        else:
            atom_positions = self.atom_positions
            return cdist(self.flat_coordinates, atom_positions).argmin(axis=1).reshape(self.n_voxels)

    def distance_to_closest_atom(self, *atom_label_numbers):
        if atom_label_numbers:
            atom_positions = self.atom_positions[[atom_label_numbers]]
        else:
            atom_positions = self.atom_positions
        return cdist(self.flat_coordinates, atom_positions).min(axis=1).reshape(self.n_voxels)

    def __add__(self, other):
        args = (self.axes, self.n_atoms, self.atom_positions, self.atomic_numbers, self.atom_charges,
                self.origins, self.unit_vectors, self.n_voxels, )
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
        args = (self.axes, self.n_atoms, self.atom_positions, self.atomic_numbers, self.atom_charges,
                self.origins, self.unit_vectors, self.n_voxels, )
        if isinstance(other, int) or isinstance(other, float) or isinstance(other, np.ndarray):
            return Cube(self.from_file, self.values * other, *args)
        elif isinstance(other, Cube):
            if self.values.shape != other.values.shape:
                raise AttributeError("Cube files must have the same coordinates to be summed.")
            return Cube(self.from_file, self.values * other.values, *args)
        else:
            raise AttributeError

    def __truediv__(self, other):
        args = (self.axes, self.n_atoms, self.atom_positions, self.atomic_numbers, self.atom_charges,
                self.origins, self.unit_vectors, self.n_voxels, )
        if isinstance(other, int) or isinstance(other, float) or isinstance(other, np.ndarray):
            return Cube(self.from_file, self.values * other, *args)
        elif isinstance(other, Cube):
            if self.values.shape != other.values.shape:
                raise AttributeError("Cube files must have the same coordinates to be summed.")
            return Cube(self.from_file, self.values * other.values, *args)
        else:
            raise AttributeError

    def __pow__(self, power, modulo=None):
        args = (self.axes, self.n_atoms, self.atom_positions, self.atomic_numbers, self.atom_charges,
                self.origins, self.unit_vectors, self.n_voxels, )
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


