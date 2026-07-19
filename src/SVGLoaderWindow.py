import gi
gi.require_version('Rsvg', '2.0')

import threading
import requests
from gi.repository import Gtk, GLib, Rsvg


class SVGLoaderWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window: Gtk.ApplicationWindow, svg_url: str, call: str):
        super().__init__()
        self.svg_url = svg_url
        self.svg_handle = None  # Rsvg.Handle, set once the SVG has downloaded

        self.set_title("Elevation profile to "+call)
        self.set_default_size(600,300)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.vbox)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.vbox.pack_start(self.stack, True, True, 0)

        # --- Loading page: real GtkSpinner + status label, centered ---
        loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        loading_box.set_halign(Gtk.Align.CENTER)
        loading_box.set_valign(Gtk.Align.CENTER)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(32, 32)
        loading_box.pack_start(self.spinner, False, False, 0)

        self.status_label = Gtk.Label(label="Loading image from server...")
        loading_box.pack_start(self.status_label, False, False, 0)

        self.stack.add_named(loading_box, "loading")

        # --- Image page: draw the SVG directly instead of going through a
        # rasterized Gtk.Image. Deliberately no set_size_request() here -
        # that's what pinned the window's minimum size before and made it
        # impossible to shrink. A DrawingArea just paints whatever space
        # it's given.
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.connect("draw", self._on_draw)
        self.stack.add_named(self.canvas, "image")

        self.stack.set_visible_child_name("loading")
        self.spinner.start()

        loader_thread = threading.Thread(target=self._load_image_from_url)
        loader_thread.daemon = True
        loader_thread.start()

    # ------------------------------------------------------------------
    # Networking (background thread)
    # ------------------------------------------------------------------
    def _load_image_from_url(self):
        """Runs in a separate thread to download the SVG asynchronously."""
        try:
            response = requests.get(self.svg_url, timeout=15)
            response.raise_for_status()
            GLib.idle_add(self._on_image_downloaded, response.content)

        except requests.exceptions.RequestException as e:
            error_msg = f"Network Error while fetching image: {e}"
            GLib.idle_add(self._on_download_error, error_msg)

    # ------------------------------------------------------------------
    # Main-thread callbacks
    # ------------------------------------------------------------------
    def _on_image_downloaded(self, image_bytes: bytes):
        try:
            self.svg_handle = Rsvg.Handle.new_from_data(image_bytes)
        except GLib.Error as e:
            self._on_download_error(f"Could not parse SVG: {e}")
            return False

        self.spinner.stop()
        self.stack.set_visible_child_name("image")
        self.canvas.queue_draw()
        return False

    def _on_download_error(self, error: str):
        self.spinner.stop()
        self.status_label.set_text(f"ERROR: {error}")
        return False

    # ------------------------------------------------------------------
    # Drawing - runs on every redraw GTK schedules, including after resize.
    # No manual resize handling/debouncing needed since this is cheap.
    # ------------------------------------------------------------------
    def _on_draw(self, widget, cr):
        if not self.svg_handle:
            return False

        avail_w = widget.get_allocated_width()
        avail_h = widget.get_allocated_height()
        if avail_w <= 0 or avail_h <= 0:
            return False

        dim = self.svg_handle.get_dimensions()
        natural_w, natural_h = dim.width, dim.height
        if natural_w <= 0 or natural_h <= 0:
            return False

        # "object-fit: contain" - scale to fit, preserve aspect ratio, center.
        scale = min(avail_w / natural_w, avail_h / natural_h)
        draw_w = natural_w * scale
        draw_h = natural_h * scale
        offset_x = (avail_w - draw_w) / 2
        offset_y = (avail_h - draw_h) / 2

        try:
            # librsvg >= 2.46 preferred API - takes a target viewport
            # directly, no manual cr.scale needed.
            viewport = Rsvg.Rectangle()
            viewport.x, viewport.y = offset_x, offset_y
            viewport.width, viewport.height = draw_w, draw_h
            self.svg_handle.render_document(cr, viewport)
        except AttributeError:
            # Fallback for older librsvg builds without render_document.
            cr.save()
            cr.translate(offset_x, offset_y)
            cr.scale(scale, scale)
            self.svg_handle.render_cairo(cr)
            cr.restore()

        return False


def create_centered_loader(parent: Gtk.ApplicationWindow, url: str) -> SVGLoaderWindow:
    """Creates and starts the loading window."""
    loader = SVGLoaderWindow(parent, url)
    loader.show_all()
    return loader