"""Small GTK4 helpers shared by the application windows."""
from pathlib import Path

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk


def asset(name):
    return str(Path(__file__).resolve().parent / name)


def margins(widget, amount):
    for edge in ('top', 'bottom', 'start', 'end'):
        getattr(widget, 'set_margin_' + edge)(amount)
    return widget


def message(parent, text, *, question=False, callback=None, title=None):
    dialog = Gtk.MessageDialog(
        transient_for=parent, modal=True, destroy_with_parent=True,
        message_type=Gtk.MessageType.QUESTION if question else Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.YES_NO if question else Gtk.ButtonsType.OK,
        text=text,
    )
    if title:
        dialog.set_title(title)

    def responded(dialog, response):
        dialog.destroy()
        if callback:
            callback(response)

    dialog.connect('response', responded)
    dialog.present()
    return dialog


def install_css(css):
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode())
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    return provider
