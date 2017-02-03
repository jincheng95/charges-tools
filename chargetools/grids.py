from collections import OrderedDict
import itertools

import numpy as np
from scipy.spatial.distance import cdist

from chargetools.constants import AXES_NAMES
from chargetools.exceptions import InputError
from chargetools.utils.utils import chained_or


class Cube(object):
    """
    A object that stores information extracted from Gaussian Cube files,
        including the Cartesian axes, the volume of the cube, the density of points,
        atom identities, atom positions,
        and of course the value at each point of the 3D volume.
    """

    def __init__(self, file_name, field_type, values, axes, molecule,
                 origins=None, unit_vectors=None, n_voxels=None,
                 ):
        self.from_file = file_name
        self.field_type = field_type
        self.values = values
        self.axes = axes
        self.molecule = molecule
        self.origins, self.unit_vectors, self.n_voxels = origins, unit_vectors, n_voxels

    @classmethod
    def from_cube_file(cls, file_name, base_molecule=None, header_only=False, field_type="potential"):
        """
        Instantiate a ``Cube`` object by reading from a stored Gaussian cube (``.cub``) file.

        :type header_only: bool
        :param header_only: If True, this function will parse the header of the ``.cub`` file only,
            using an empty numpy array as its value.
            Shape of the empty numpy array will be of the dimensions specified in the header.
            Useful if using a cube file as template.
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
            from chargetools.entities import Molecule
            base_molecule = Molecule.from_cube_header(atom_header)

        # Create a 1-dimensional flat array containing values in the .cub file
        if header_only:
            values = np.empty(n_voxels)
        else:
            value_str = ''.join(lines[6+n_atoms:])
            values = np.fromstring(value_str, sep=" ").reshape(n_voxels)

        # Create 1D arrays describing 3 coordinates
        axes = OrderedDict()
        zipped_axes_attributes = zip(AXES_NAMES, origins, unit_vectors, n_voxels)
        for axis_name, origin, unit_vector, n_voxel in zipped_axes_attributes:
            axes[axis_name] = np.arange(0, n_voxel) * unit_vector + origin

        return cls(file_name, field_type, values, axes, base_molecule,
                   origins, unit_vectors, n_voxels)

    def save(self, file_path):
        with open(file_path, 'x') as f:
            # meta data
            f.write(' Cube file generated by charges-tools.\n')
            f.write(' Cube file for field of type {0}.\n'.format(self.field_type))

            # no. of atoms followed by origin coordinates
            f.write(' {0:4}   {1: .6f}   {2: .6f}   {3: .6f}    1\n'.format(len(self.molecule), *self.origins))

            # lines of axes data: points density then vector
            for index, (unit_vector, n_voxel) in enumerate(zip(self.unit_vectors, self.n_voxels)):
                unit_vectors = ['{0: .6f}'.format(0.)] * index + \
                               ['{0: .6f}'.format(unit_vector)] + \
                               ['{0: .6f}'.format(0.)] * (len(self.unit_vectors) - index - 1)
                f.write(" {0:4}   {1}\n".format(n_voxel, '   '.join(unit_vectors)))

            # lines for atomic data: atomic number, charge, then positions
            for atom in self.molecule.atoms:
                f.write(' {0:4}   {1: .6f}   {2: .6f}   {3: .6f}   {4: .6f}\n'.format(
                    atom.atomic_number, atom.atomic_number + atom.charge, *atom.position))

            # write actual field values
            for counter, value in enumerate(self.values.flatten(), start=1):
                s = (' {0: .5E}'.format(value))

                # cube file format requires line break every 6 values
                if not counter % 6:
                    s += '\n'
                # cube file format requires line break after every z value has been depleted for x_i, y_j
                elif not counter % self.n_voxels[-1]:
                    s += '\n'

                f.write(s)

    def plot(self, distance=200, global_max=None, grid=True, **kwargs):
        from pyqtgraph.Qt import QtCore, QtGui
        from chargetools.plotting.PyQtGraph import widgets, renderers
        app = QtGui.QApplication([])
        widget = widgets.SyncedWidget(cube_file=self, **kwargs)
        widget.opts['distance'] = distance
        widget.setWindowTitle(self.from_file)

        # Add in atoms
        for atom_shader in renderers.get_atoms(self):
            widget.addItem(atom_shader)

        # Plot actual cube field value
        # this needs to be plotted last, its density will hide most other components
        elements = renderers.get_volume(self, global_max=global_max, grid=grid, midpoint=0)
        for element in elements:
            widget.addItem(element)

        widget.show()

        QtGui.QApplication.instance().exec_()

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
        return cls(original_cube.from_file, original_cube.field_type, new_values, *args)

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
        else:
            mask_array = condition
        return np.where(mask_array, self.values, replace_with)

    def points_labelled_by_closest_atom(self, *atom_descriptors, **kwargs):
        """
        Label all points in the 3D space with label of closest atom to the point in question.

        :rtype: numpy.array
        :return: Numpy array containing labels of closest atom at various points.
        """
        # if no arg, then all atoms are used
        if atom_descriptors:
            atoms = self.molecule.select_descriptor(*atom_descriptors)
        else:
            atoms = self.molecule.atoms

        atom_positions = np.array([atom.position for atom in atoms])
        closest_by_args = cdist(self.flat_coordinates, atom_positions, **kwargs
                                ).argmin(axis=1).reshape(self.n_voxels)

        # Turn indices of argument in atom_label_numbers into actual label
        return np.vectorize(atoms.__getitem__)(closest_by_args)

    def distance_to_closest_atom(self, *atom_descriptors):
        """
        Label all points in the 3D space with Euclidean distance distance to closest atom.

        :type atom_label_numbers: [int, ...]
        :param atom_label_numbers: Atom labels to be evaluated,
            if one is included, points closest to this atom will be considered for the next closest atom.
            If no arguments are passed to this function, then all atom labels will be evaluated.
        :rtype: numpy.array
        :return: Numpy array containing distance to closest atom at various points.
        """
        # if no arg, then all atoms are used
        if atom_descriptors:
            atoms = self.molecule.select_descriptor(atom_descriptors)
        else:
            atoms = self.molecule.atoms

        atom_positions = [atom.position for atom in atoms]
        return cdist(self.flat_coordinates, np.array(atom_positions)
                     ).min(axis=1).reshape(self.n_voxels)

    def value_by_atom(self, selected_descriptors, filter_descriptors):
        # Get an array of closest atoms
        atom_values = self.points_labelled_by_closest_atom(*filter_descriptors)

        # Select values which are in selected values
        select_args = []
        for selected_descriptor in selected_descriptors:
            atoms = self.molecule.select_descriptor(selected_descriptor)
            for atom in atoms:
                select_args.append(atom_values == atom)

        chained_or_mask = chained_or(*select_args)
        return self.filter_values(chained_or_mask)

    @property
    def _grid_args(self):
        """Provides ``self.__init__`` arguments for metadata. Useful for copying an instance of cube."""
        return self.axes, self.molecule, self.origins, self.unit_vectors, self.n_voxels

    """
    Several native Python magic methods for performing cube_1 + cube_2, cube_1 * cube_2 operations, etc.
    """
    def __add__(self, other):
        args = self._grid_args
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
        args = self._grid_args
        if isinstance(other, int) or isinstance(other, float) or isinstance(other, np.ndarray):
            return Cube(self.from_file, self.values * other, *args)
        elif isinstance(other, Cube):
            if self.values.shape != other.values.shape:
                raise AttributeError("Cube files must have the same coordinates to be summed.")
            return Cube(self.from_file, self.values * other.values, *args)
        else:
            raise AttributeError

    def __truediv__(self, other):
        args = self._grid_args
        if isinstance(other, int) or isinstance(other, float) or isinstance(other, np.ndarray):
            return Cube(self.from_file, self.values * other, *args)
        elif isinstance(other, Cube):
            if self.values.shape != other.values.shape:
                raise AttributeError("Cube files must have the same coordinates to be summed.")
            return Cube(self.from_file, self.values * other.values, *args)
        else:
            raise AttributeError

    def __pow__(self, power, modulo=None):
        args = self._grid_args
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


