import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtCore


class SyncedWidget(gl.GLViewWidget):
    def __init__(self, update_callback=None, cube_file=None, sync_with=[], *args, **kwargs):
        self.update_callback = update_callback
        self.cube_file = cube_file
        self.sync_with = sync_with
        super(SyncedWidget, self).__init__(*args, **kwargs)

    def update(self, *args, **kwargs):
        super(SyncedWidget, self).update(*args, **kwargs)
        # if picture needs updating, then user must have changed camera position
        # perform callback function to sync camera
        camera_sync(self.opts['distance'], self.opts['elevation'],
                    self.opts['azimuth'], self)

    def pan(self, x, y, z, from_callback=False, *args, **kwargs):
        super(SyncedWidget, self).pan(x, y, z, *args, **kwargs)
        if not from_callback:
            pan_sync(x, y, z, self, *args)

    def evalKeyState(self):
        if len(self.keysPressed) > 0:
            key_map = {
                QtCore.Qt.Key_Right: (5, 0, 0),
                QtCore.Qt.Key_Left: (-5, 0, 0),
                QtCore.Qt.Key_Up: (0, 0, -5),
                QtCore.Qt.Key_Down: (0, 0, 5),
            }
            control_key_map = {
                QtCore.Qt.Key_Up: (0, -5, 0),
                QtCore.Qt.Key_Down: (0, -5, 0)
            }
            control_pressed = QtCore.Qt.Key_Control in self.keysPressed
            for key in self.keysPressed:
                if control_pressed and key in control_key_map:
                    self.pan(*control_key_map[key], relative=True)
                elif key in key_map:
                    self.pan(*key_map[key], relative=True)
            self.keyTimer.start(16)
        else:
            self.keyTimer.stop()


def camera_sync(dist_active, elev_active, azi_active, active_widget):
    widgets = active_widget.sync_with
    for w in widgets:
        dist, elev, azi, cent = w.opts['distance'], w.opts['elevation'], w.opts['azimuth'], w.opts['center']
        if dist_active != dist or elev_active != elev or azi_active != azi:
            w.setCameraPosition(distance=dist_active, elevation=elev_active,
                                azimuth=azi_active)


def pan_sync(dx, dy, dz, active_widget, *args):
    widgets = active_widget.sync_with
    for w in widgets:
        if w.cube_file != active_widget.cube_file:
            w.pan(dx, dy, dz, True, relative=True, *args)
