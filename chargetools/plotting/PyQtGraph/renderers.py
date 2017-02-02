import numpy as np
import pyqtgraph.opengl as gl


def clip_and_normalize(arr, minimum, maximum):
    clipped = np.clip(arr, minimum, maximum)
    return np.where(clipped > 0, np.log(clipped**2), -np.inf)


def color_scale(arr, max_num=None):
    return arr * (255 / (max_num or arr.max()))


def get_volume(cube, global_max=None, grid=False, midpoint=0):
    c = cube
    val = cube.values

    # convert midpoint to a.u. charge

    # create new array with additional colorscale and transparency info
    d2 = np.empty(val.shape + (4,), dtype=np.ubyte)
    # d2 is essentially values of the cube,
    # except that the scalar value is swapped with a 4-member array
    # each representing R G B A values for graphing purposes.

    # On synced multiple plots, allow subplots to use one maximum to represent 100% opacity
    abs_max = np.fabs(val).max()
    if global_max:
        pos_upper, neg_upper = global_max, global_max
        print("{0} – using {1} as 100% opacity, {2} is this file's maximum."
              .format(cube.from_file, pos_upper, abs_max))
    else:
        pos_upper, neg_upper = abs_max, abs_max
        print("{0} – using {1} as 100% opacity, which is this file's maximum."
              .format(cube.from_file, pos_upper))

    # R
    positive = clip_and_normalize(val, midpoint, pos_upper)
    d2[..., 0] = color_scale(positive)
    # G
    negative = clip_and_normalize(-val, midpoint, neg_upper)
    d2[..., 1] = color_scale(negative)
    # B
    d2[..., 2] = d2[..., 1]
    # Alpha (opacity)
    d2[..., 3] = d2[..., 0] * 0.3 + d2[..., 1] * 0.3
    d2[..., 3] = (d2[..., 3].astype(float) / 255.)**2 * 255

    # show axes at origin
    ax = gl.GLAxisItem()

    # create three grids, add each to the view
    grid_names = ('xgrid_min',
                  'ygrid_min',
                  'zgrid_min',
                  )
    grids = []
    if grid:
        for grid_name in grid_names:
            grid = gl.GLGridItem()
            grids.append(grid)

            # one grid = 1 / unit vector
            grid.setSpacing(*(1 / c.unit_vectors))
            # make the grid enclose the volume, but hide if not in multiples of ten
            grid.setSize(*c.n_voxels)

            # min - shift to lower bound, max - shift to higher bound
            if 'min' in grid_name:
                multiplier = 0
            elif 'max' in grid_name:
                multiplier = 1
            else:
                multiplier = 0

            # Rotate if necessary for the corresponding axes direction
            # Translate min and max in the axis direction
            if 'x' in grid_name:
                grid.rotate(90, 0, 1, 0)
                grid.translate(multiplier * val.shape[0], val.shape[1] * 0.5, val.shape[2] * 0.5)
            elif 'y' in grid_name:
                grid.rotate(90, 1, 0, 0)
                grid.translate(val.shape[0] * 0.5, multiplier * val.shape[0], val.shape[2] * 0.5)
            elif 'z' in grid_name:
                grid.translate(val.shape[0] * 0.5, val.shape[1] * 0.5, multiplier * val.shape[0])

    return grids + [ax, gl.GLVolumeItem(d2)]


def get_atoms(cube):
    atom_shaders = []
    md = gl.MeshData.sphere(rows=20, cols=20, radius=3.0)

    for atom_pos in cube.molecule.list_of_atom_property('position'):
        atom = gl.GLMeshItem(meshdata=md, smooth=True, shader='shaded', glOptions='opaque')
        translation = (atom_pos - cube.origins) / cube.unit_vectors
        atom.translate(*translation.flatten())
        atom_shaders.append(atom)
    return atom_shaders
