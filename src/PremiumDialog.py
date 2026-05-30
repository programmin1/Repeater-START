import gi
import os
from RepeaterStartCommon import userFile
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango

CSS = """
.premium-dialog {
    background-color: #111622;
}

.premium-header {
    background-color: #1a1f2e;
    border-bottom: 1px solid #2d3550;
    padding: 16px 20px 14px 20px;
}

.premium-title {
    color: #e8ecf4;
    font-size: 20px;
    font-weight: bold;
}
.premium-features {
    background-color: #111622;
    border-bottom: 1px solid #2d3550;
    padding: 18px 20px;
}

.feature-text {
    color: #c8d4e8;
    font-size: 15px;
}

.check-icon {
    color: #2ecc71;
    font-weight: bold;
    font-size: 15px;
}
.price-box {
    background-color: #0d1526;
    border: 1px solid #2d3550;
    border-radius: 6px;
    padding: 10px 14px;
}
.price-amount {
    color: #4a9eff;
    font-size: 22px;
    font-weight: bold;
}

.price-period {
    color: #5a6a8a;
    font-size: 13px;
}
.btn-purchase {
    border: 1px solid #2ecc71;
    border-radius: 6px;
    font-size: 18px;
    font-weight: bold;
    padding: 9px 20px;
}

.btn-purchase:hover {
    background-color: #228844;
}
.premium-key-section {
    background-color: #111622;
    padding: 16px 20px 18px 20px;
}
.key-label {
    color: #FFF;
    font-size: 18px;
    letter-spacing: 1.5px;
}
.key-entry {
    background-color: #0d1526;
    border: 1px solid #2d3550;
    border-radius: 6px;
    color: #c8d4e8;
    caret-color: #4a9eff;
    font-size: 14px;
    padding: 8px 12px;
    font-family: monospace;
}
.key-entry:focus {
    border-color: #4a9eff;
    background-color: #0d1835;
}
.btn-cancel {
    background-color: #0d1f3d;
    border: 1px solid #1a4a8a;
    border-radius: 6px;
    color: #7a9ac0;
    font-size: 13px;
    letter-spacing: 1px;
    padding: 9px 16px;
}

.btn-cancel:hover {
    background-color: #1a2a4a;
}

.btn-activate {
    border: 1px solid #4a9eff;
    border-radius: 6px;
    font-size: 13px;
    letter-spacing: 1px;
    padding: 9px 24px;
}

.btn-activate:hover {
    background-color: #2255b0;
}
"""


def _apply_css():
    provider = Gtk.CssProvider()
    try:
        provider.load_from_data(CSS)#new
    except TypeError:
        provider.load_from_data(CSS.encode("utf-8"))#old

    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def _add_class(widget, *names):
    ctx = widget.get_style_context()
    for name in names:
        ctx.add_class(name)


class PremiumDialog(Gtk.Dialog):
    """
    Usage:
        dlg = PremiumDialog(parent_window)
        response = dlg.run()
        if response == Gtk.ResponseType.OK:
            key = dlg.get_license_key()
        dlg.destroy()
    """

    def __init__(self, parent):
        super().__init__(transient_for=parent, modal=True)
        self.set_title("HearHam Premium")
        self.set_resizable(False)
        self.set_border_width(0)
        self.set_default_size(400, -1)
        self.get_style_context().add_class("premium-dialog")

        # Remove default dialog button area — we build our own
        self.get_action_area().set_visible(False)
        # Remove default content padding
        content = self.get_content_area()
        content.set_border_width(0)
        content.set_spacing(0)
        firstline = True
        self.price = '?'
        self.features = []
        with open(userFile('promo.txt')) as infile:
            for line in infile:
                if firstline:
                    self.price = line.strip()
                    firstline = False
                else:
                    self.features.append(line.strip())
        content.add(self._build_header())
        content.add(self._build_features())
        content.add(self._build_key_section())
        _apply_css()
        self.show_all()

    def _build_header(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        _add_class(box, "premium-header")
        title = Gtk.Label(label="📡  Unlock RepeaterSTART Premium!")
        title.set_halign(Gtk.Align.START)
        _add_class(title, "premium-title")
        box.pack_start(title, False, False, 0)
        return box

    def _build_features(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        _add_class(outer, "premium-features")
        for text in self.features:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            check = Gtk.Label(label="✓")
            _add_class(check, "check-icon")
            check.set_valign(Gtk.Align.START)
            label = Gtk.Label(label=text)
            label.set_line_wrap(True)
            label.set_max_width_chars(42)
            label.set_xalign(0)
            _add_class(label, "feature-text")
            row.pack_start(check, False, False, 0)
            row.pack_start(label, True, True, 0)
            outer.pack_start(row, False, False, 0)

        # Price badge + purchase button side by side
        bottom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_row.set_margin_top(4)

        price_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        _add_class(price_row, "price-box")
        amount = Gtk.Label(label=self.price)
        _add_class(amount, "price-amount")
        period = Gtk.Label(label=" / month · billed annually")
        _add_class(period, "price-period")
        period.set_valign(Gtk.Align.CENTER)
        price_row.pack_start(amount, False, False, 0)
        price_row.pack_start(period, False, False, 0)

        purchase_btn = Gtk.Button(label="🛒  Purchase on Dashboard")
        _add_class(purchase_btn, "btn-purchase")
        purchase_btn.set_valign(Gtk.Align.CENTER)
        purchase_btn.connect("clicked", self._on_purchase_clicked)

        bottom_row.pack_start(price_row, False, False, 0)
        bottom_row.pack_start(purchase_btn, False, False, 0)
        outer.pack_start(bottom_row, False, False, 0)

        return outer

    def _build_key_section(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        _add_class(outer, "premium-key-section")

        key_label = Gtk.Label(label="LICENSE KEY")
        key_label.set_halign(Gtk.Align.START)
        _add_class(key_label, "key-label")
        outer.pack_start(key_label, False, False, 0)

        self._key_entry = Gtk.Entry()
        self._key_entry.set_placeholder_text("ENTER-HERE")
        self._key_entry.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        _add_class(self._key_entry, "key-entry")
        self._key_entry.connect("activate", lambda _: self.response(Gtk.ResponseType.OK))
        outer.pack_start(self._key_entry, False, False, 0)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_row.set_margin_top(4)

        cancel_btn = Gtk.Button(label="CANCEL")
        _add_class(cancel_btn, "btn-cancel")
        cancel_btn.connect("clicked", lambda _: self.response(Gtk.ResponseType.CANCEL))
        btn_row.pack_start(cancel_btn, True, True, 0)

        activate_btn = Gtk.Button(label="ACTIVATE LICENSE")
        _add_class(activate_btn, "btn-activate")
        activate_btn.connect("clicked", lambda _: self.response(Gtk.ResponseType.OK))
        btn_row.pack_start(activate_btn, True, True, 0)

        outer.pack_start(btn_row, False, False, 0)
        return outer

    def _on_purchase_clicked(self, _btn):
        os.system('xdg-open "https://hearham.com/gopremium"')

    def get_license_key(self):
        """Return the text typed into the license key field."""
        return self._key_entry.get_text().strip()
