"""GTK4/libshumate map, repeater markers, paths and bounded offline prefetch."""
import math
import time

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Shumate', '1.0')
from gi.repository import Gtk, Gdk, Gio, GLib, GObject, Shumate


def visible_tiles(latitude, longitude, zoom, width, height, rotation=0,
                  max_zoom=19, tile_size=256):
    """Tiles covering the rotated viewport at this zoom and two deeper levels.

    Work in unwrapped Mercator pixels so antimeridian views stay small. Return
    an iterator so callers can reject oversized jobs before downloading.
    """
    latitude = max(-85.05112878, min(85.05112878, latitude))
    world = tile_size * 2 ** zoom
    cx = ((longitude + 180) / 360) * world
    cy = (1 - math.asinh(math.tan(math.radians(latitude))) / math.pi) / 2 * world
    c, s = abs(math.cos(rotation)), abs(math.sin(rotation))
    dx, dy = (width*c + height*s)/2, (width*s + height*c)/2
    start = max(0, min(max_zoom, math.floor(zoom)))
    for z in range(start, min(max_zoom, start + 2) + 1):
        n = 2 ** z
        factor = n / world
        left, right = math.floor((cx-dx)*factor), math.floor((cx+dx)*factor)
        top = max(0, math.floor((cy-dy)*factor))
        bottom = min(n-1, math.floor((cy+dy)*factor))
        # At most one copy of each tile even when the world repeats onscreen.
        for x in range(left, min(right+1, left+n)):
            for y in range(top, bottom+1):
                yield x % n, y, z


class RepeaterMap(Shumate.SimpleMap):
    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'repeater-clicked': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, repo_uri):
        super().__init__(hexpand=True, vexpand=True)
        self.viewport = self.get_viewport()
        # OsmGpsMap's URL substitutions differ from libshumate's.
        url = repo_uri.replace('#Z', '{z}').replace('#X', '{x}').replace('#Y', '{y}')
        self.downloader = Shumate.TileDownloader.new(url)
        self.source = Shumate.RasterRenderer.new_full(
            'repeaterstart-mapbox', 'Mapbox',
            '© Mapbox © OpenStreetMap contributors',
            'https://www.mapbox.com/about/maps/', 0, 19, 256,
            Shumate.MapProjection.MERCATOR, self.downloader)
        self.set_map_source(self.source)
        self.set_show_zoom_buttons(True)
        self.markers = Shumate.MarkerLayer.new(self.viewport)
        self.add_overlay_layer(self.markers)
        self._repeaters = []
        self._visible = {}
        self._refresh_id = 0
        self._marker_job_id = 0
        self._closed = False
        self._prefetch = None
        self._info = None
        self.viewport.connect('notify', self._viewport_changed)
        self.add_tick_callback(self._size_tick)
        self._last_size = None
        self.get_map().set_focusable(True)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self._key_pressed)
        self.get_map().add_controller(keys)

    def _key_pressed(self, controller, key, code, state):
        steps = {Gdk.KEY_Left: (-80, 0), Gdk.KEY_Right: (80, 0),
                 Gdk.KEY_Up: (0, -80), Gdk.KEY_Down: (0, 80)}
        if key in steps:
            dx, dy = steps[key]
            lat, lon = self.screen_to_location(self.get_width()/2 + dx,
                                               self.get_height()/2 + dy)
            self.set_center(lat, lon)
            return True
        if key in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_minus):
            self.set_zoom(self.viewport.get_zoom_level() + (-1 if key == Gdk.KEY_minus else 1))
            return True
        return False

    def _size_tick(self, widget, clock):
        size = (self.get_width(), self.get_height())
        if size != self._last_size:
            self._last_size = size
            self._schedule_markers()
        return not self._closed

    def _viewport_changed(self, viewport, prop):
        if prop.name in ('latitude', 'longitude', 'zoom-level', 'rotation'):
            self.hide_info()
            self._schedule_markers()
            self.emit('changed')

    # Bound widget count independently of dataset size and zoom level.
    MAX_MARKERS = 200
    MARKER_BUDGET_SECONDS = 0.004

    def _cancel_marker_job(self):
        if self._marker_job_id:
            GLib.source_remove(self._marker_job_id)
            self._marker_job_id = 0

    def _schedule_markers(self):
        self._cancel_marker_job()
        if self._refresh_id:
            GLib.source_remove(self._refresh_id)
            self._refresh_id = 0
        if not self._closed:
            # Wait until the viewport settles instead of rebuilding during each
            # frame of a smooth zoom animation.
            self._refresh_id = GLib.timeout_add(150, self._refresh_markers)

    def set_center(self, latitude, longitude):
        if not self._closed:
            self.get_map().center_on(float(latitude), float(longitude))

    def set_zoom(self, zoom):
        self.viewport.set_zoom_level(max(0, min(19, float(zoom))))

    def set_center_and_zoom(self, latitude, longitude, zoom):
        self.set_zoom(zoom)
        self.set_center(latitude, longitude)

    def screen_to_location(self, x, y):
        return self.viewport.widget_coords_to_location(self.get_map(), x, y)

    def set_repeaters(self, repeaters):
        """Replace (repeater, image filename or pixbuf) pairs; retain only visible widgets."""
        self.hide_info()
        self.markers.remove_all()
        self._visible.clear()
        self._repeaters = list(repeaters)
        self._schedule_markers()

    def _refresh_markers(self):
        self._refresh_id = 0
        if self._closed:
            return False
        job = self._marker_steps()

        def advance():
            deadline = time.monotonic() + self.MARKER_BUDGET_SECONDS
            while time.monotonic() < deadline:
                try:
                    next(job)
                except StopIteration:
                    self._marker_job_id = 0
                    return False
            return True

        self._marker_job_id = GLib.idle_add(advance)
        return False

    def _marker_steps(self):
        width, height = self.get_width(), self.get_height()
        if width <= 0 or height <= 0:
            return
        # A bounded grid aggregates every visible repeater, including those at
        # identical coordinates. There are never more than MAX_MARKERS cells.
        cols = max(1, min(self.MAX_MARKERS,
                         int(math.sqrt(self.MAX_MARKERS * width / height))))
        rows = max(1, self.MAX_MARKERS // cols)
        cell_width, cell_height = (width + 48) / cols, (height + 48) / rows
        groups, singles = {}, []
        visible_count = 0
        for i, (repeater, icon) in enumerate(self._repeaters):
            x, y = self.viewport.location_to_widget_coords(
                self.get_map(), float(repeater.lat), float(repeater.lon))
            if -24 <= x <= width+24 and -24 <= y <= height+24:
                visible_count += 1
                if visible_count <= self.MAX_MARKERS:
                    singles.append((i,))
                key = (min(cols-1, int((x+24) / cell_width)),
                       min(rows-1, int((y+24) / cell_height)))
                groups.setdefault(key, []).append(i)
            yield
        selections = singles if visible_count <= self.MAX_MARKERS else groups.values()
        wanted = {tuple(indices) for indices in selections}
        # Remove first so even midway through an update the widget cap holds.
        for key in list(self._visible):
            if key not in wanted:
                self.markers.remove_marker(self._visible.pop(key))
            yield
        for indices in wanted:
            if indices not in self._visible:
                repeater, icon = self._repeaters[indices[0]]
                marker = Shumate.Marker()
                marker.set_location(float(repeater.lat), float(repeater.lon))
                if len(indices) == 1:
                    image = (Gtk.Image.new_from_file(icon) if isinstance(icon, str)
                             else Gtk.Image.new_from_pixbuf(icon))
                    image.set_pixel_size(20)
                    button = Gtk.Button(child=image)
                    button.add_css_class('repeater-marker')
                    button.set_tooltip_text(f'{repeater.callsign} · {repeater.freq} MHz')
                    button.connect('clicked', self._marker_clicked, repeater)
                else:
                    button = Gtk.Button(label=str(len(indices)))
                    button.add_css_class('circular')
                    button.set_tooltip_text(f'{len(indices)} repeaters — click to zoom in')
                    button.connect('clicked', self._cluster_clicked, indices)
                marker.set_child(button)
                self.markers.add_marker(marker)
                self._visible[indices] = marker
            yield

    def _cluster_clicked(self, button, indices):
        repeater = self._repeaters[indices[0]][0]
        zoom = self.viewport.get_zoom_level()
        if zoom < 19:
            self.set_center_and_zoom(repeater.lat, repeater.lon, min(19, zoom + 2))
        else:
            # Co-located repeaters cannot be separated by zooming further.
            self.hide_info()
            popover = Gtk.Popover()
            popover.set_parent(button)
            names = [f'{self._repeaters[i][0].callsign}  {self._repeaters[i][0].freq} MHz'
                     for i in indices[:25]]
            if len(indices) > 25:
                names.append(f'… and {len(indices)-25} more; see the nearby repeater list.')
            popover.set_child(Gtk.Label(label='\n'.join(names)))
            popover.connect('closed', self._info_closed)
            self._info = popover
            popover.popup()

    def _marker_clicked(self, button, repeater):
        self.hide_info()
        popover = Gtk.Popover()
        popover.set_parent(button)
        label = Gtk.Label(label=f'{repeater.callsign}  {repeater.freq} MHz')
        popover.set_child(label)
        popover.connect('closed', self._info_closed)
        self._info = popover
        popover.popup()
        self.emit('repeater-clicked', repeater)

    def _info_closed(self, popover):
        if self._info is popover:
            self._info = None
        if popover.get_parent():
            popover.unparent()

    def hide_info(self):
        if self._info:
            popover, self._info = self._info, None
            popover.popdown()
            if popover.get_parent():
                popover.unparent()

    def make_path(self, points, color='#ff0000', width=4):
        path = Shumate.PathLayer.new(self.viewport)
        rgba = Gdk.RGBA()
        rgba.parse(color)
        path.set_stroke_color(rgba)
        path.set_stroke_width(width)
        path.set_can_target(False)
        for lat, lon in points:
            coord = Shumate.Coordinate.new()
            coord.set_location(float(lat), float(lon))
            path.add_node(coord)
        return path

    def cache_view(self, progress, limit=1500):
        """Prefetch through the SAME downloader/cache as the displayed map.

        Four in-flight requests, cancellable, with a strict job size limit.
        progress(done, total, failures, cancelled) runs on GTK's main thread.
        """
        tiles = []
        for tile in visible_tiles(self.viewport.props.latitude,
                                  self.viewport.props.longitude,
                                  self.viewport.get_zoom_level(),
                                  self.get_width(), self.get_height(),
                                  self.viewport.props.rotation):
            tiles.append(tile)
            if len(tiles) > limit:
                raise ValueError('This view requires too many tiles. Zoom in or make the map smaller, then try Cache again.')
        self.cancel_cache()
        job = {'tiles': iter(tiles), 'total': len(tiles), 'done': 0, 'failed': 0,
               'active': 0, 'cancel': Gio.Cancellable(), 'progress': progress}
        self._prefetch = job
        self._pump(job)

    def _pump(self, job):
        while job['active'] < 4 and not job['cancel'].is_cancelled():
            tile = next(job['tiles'], None)
            if tile is None:
                break
            job['active'] += 1
            self.downloader.get_tile_data_async(*tile, job['cancel'], self._tile_done, job)
        if not job['active']:
            if self._prefetch is job:
                self._prefetch = None
            if not self._closed:
                job['progress'](job['done'], job['total'], job['failed'], job['cancel'].is_cancelled())

    def _tile_done(self, source, result, job):
        try:
            if source.get_tile_data_finish(result) is None:
                job['failed'] += 1
        except GLib.Error:
            job['failed'] += 1
        job['active'] -= 1
        job['done'] += 1
        if not self._closed and job['active']:
            job['progress'](job['done'], job['total'], job['failed'], job['cancel'].is_cancelled())
        self._pump(job)

    def cancel_cache(self):
        if self._prefetch:
            self._prefetch['cancel'].cancel()

    def close(self):
        self._closed = True
        self._cancel_marker_job()
        self.cancel_cache()
        self.hide_info()
        if self._refresh_id:
            GLib.source_remove(self._refresh_id)
            self._refresh_id = 0
