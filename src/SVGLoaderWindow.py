"""Scalable GTK4 elevation profile with asynchronous, generation-safe loading."""
import threading
import urllib.request
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Rsvg', '2.0')
from gi.repository import Gtk, GLib, Rsvg


class SVGLoaderWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, svg_url, call=''):
        super().__init__(application=parent_window.get_application(),
                         transient_for=parent_window, destroy_with_parent=True,
                         title='Elevation profile to ' + call,
                         default_width=600, default_height=300)
        self.svg_url = None
        self.svg_handle = None
        self._generation = 0
        self._closed = False
        self.connect('close-request', self._on_close)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.set_child(self.stack)
        loading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                          halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.spinner = Gtk.Spinner(width_request=32, height_request=32)
        loading.append(self.spinner)
        self.status_label = Gtk.Label(label='Loading image from server…', wrap=True)
        loading.append(self.status_label)
        self.stack.add_named(loading, 'loading')
        self.canvas = Gtk.DrawingArea(hexpand=True, vexpand=True)
        self.canvas.set_draw_func(self._on_draw)
        self.stack.add_named(self.canvas, 'image')
        self.loadsvg(svg_url)

    def _on_close(self, *args):
        self._closed = True
        self._generation += 1
        return False

    def loadsvg(self, svg_url):
        if self._closed or svg_url == self.svg_url:
            return
        self.svg_url = svg_url
        self._generation += 1
        generation = self._generation
        self.status_label.set_text('Loading image from server…')
        self.stack.set_visible_child_name('loading')
        self.spinner.start()
        def fetch():
            try:
                with urllib.request.urlopen(svg_url, timeout=15) as response:
                    data = response.read()
                GLib.idle_add(self._on_image_downloaded, data, generation)
            except OSError as error:
                GLib.idle_add(self._on_download_error, str(error), generation)
        threading.Thread(target=fetch, daemon=True).start()

    def _on_image_downloaded(self, data, generation):
        if self._closed or generation != self._generation:
            return False
        try:
            self.svg_handle = Rsvg.Handle.new_from_data(data)
        except GLib.Error as error:
            return self._on_download_error(str(error), generation)
        self.spinner.stop()
        self.stack.set_visible_child_name('image')
        self.canvas.queue_draw()
        return False

    def _on_download_error(self, error, generation):
        if not self._closed and generation == self._generation:
            self.spinner.stop()
            self.status_label.set_text('Unable to load elevation profile: ' + error)
        return False

    def _on_draw(self, area, cr, width, height):
        if not self.svg_handle or width <= 0 or height <= 0:
            return
        # render_document respects the SVG viewBox and preserveAspectRatio;
        # GTK's Cairo context already has the correct device scale.
        viewport = Rsvg.Rectangle()
        viewport.x = viewport.y = 0
        viewport.width, viewport.height = width, height
        self.svg_handle.render_document(cr, viewport)


def create_centered_loader(parent, url):
    window = SVGLoaderWindow(parent, url)
    window.present()
    return window
