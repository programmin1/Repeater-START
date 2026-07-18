import gi
import threading
import requests
from gi.repository import Gtk, GdkPixbuf, GLib

class SVGLoaderWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window: Gtk.ApplicationWindow, svg_url: str):
        super().__init__()
        self.svg_url = svg_url
        self.current_image = None

        self.set_title("Elevation profile")
        # Set a default size, it will be adjusted after loading the actual image size/content
        self.set_default_size(400, 300)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.vbox)
        
        # --- Status Label / Spinner Area ---
        # We will use a simple label to act as the 'spinner' state placeholder initially
        self.status_label = Gtk.Label(label="Loading image from server...")
        self.vbox.pack_start(self.status_label, True, True, 0)

        # --- Image Placeholder Area (Initially invisible/small until loaded) ---
        # We use a GtkImage initially, but it will hold the Pixbuf object later
        self.image_widget = Gtk.Image()
        self.vbox.pack_start(self.image_widget, True, True, 0)

        # 3. Start Loading Thread
        # IMPORTANT: Network I/O MUST happen in a background thread to keep the GTK UI responsive!
        loader_thread = threading.Thread(target=self._load_image_from_url)
        loader_thread.daemon = True  # Allows main program to exit even if this thread is running
        loader_thread.start()

    def _load_image_from_url(self):
        """Runs in a separate thread to download and load the image asynchronously."""
        try:
            print("--- Thread Started: Starting network request ---")
            # 1. Download raw bytes from URL
            response = requests.get(self.svg_url, timeout=15)
            response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)

            image_bytes = response.content
            print("--- Thread Finished: Bytes received ---")

            # 2. Use GdkPixbuf to load the image data in memory
            # THIS relies on your confirmation that Pixbuf can handle the remote SVG structure!

            # loader = GdkPixbuf.PixbufLoader()
            # loader.write(image_bytes.encode())
            # loader.close()
            # pixbuf = loader.get_pixbuf()

            with open('/tmp/tmp.svg', 'wb') as outfile:
                outfile.write(image_bytes)

            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale('/tmp/tmp.svg',width=400,height=300,preserve_aspect_ratio=True)
            
            #image = Gtk.Image.new_from_pixbuf(pixbuf)
            print("--- Thread Finished: Pixbuf created successfully ---")

            # 3. Post the result back to the main GTK thread using GLib.idle_add
            GLib.idle_add(self._on_image_loaded, pixbuf)


        except requests.exceptions.RequestException as e:
            # Handle network errors (DNS failure, timeout, connection refused)
            error_msg = f"Network Error while fetching image: {e}"
            GLib.idle_add(self._on_image_loaded, None, error=error_msg)


    def _on_image_loaded(self, pixbuf, error: str = None):
        """Runs back in the main GTK thread to update the UI."""
        if not pixbuf:
            # Handle failure case (error provided by loading function)
            self.status_label.set_text(f"ERROR: {error}")
            return

        try:
            # Set the Pixbuf into the GtkImage widget, making it visible instantly upon UI update cycle
            self.current_image = pixbuf
            self.image_widget.set_from_pixbuf(pixbuf)

            # Hide status label and ensure image takes focus area (re-layout might be needed here depending on exact flow)
            self.status_label.set_text("") # Clear spinner text
            self.show_all()
        except Exception as e:
             self.status_label.set_text(f"CRITICAL GTK Error Displaying Image: {e}")


def create_centered_loader(parent: Gtk.ApplicationWindow, url: str) -> SVGLoaderWindow:
    """Creates and starts the loading window."""
    loader = SVGLoaderWindow(parent, url)
    return loader
