"""Premium setup help in a GTK4/WebKitGTK 6 window."""
import sys
import webbrowser
from pathlib import Path
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
from RepeaterStartCommon import userFile
from GtkSupport import message

try:
    gi.require_version('WebKit', '6.0')
    from gi.repository import WebKit
except (ImportError, ValueError):
    WebKit = None


class HelpDialog(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title='Repeater Setup Help',
                         default_width=600, default_height=900)
        if WebKit is None:
            self.set_child(Gtk.Label(label='Install WebKitGTK 6 introspection to display premium setup help.', wrap=True))
            return
        self.helpview = WebKit.WebView()
        self.helpview.set_vexpand(True)
        self.helpview.set_hexpand(True)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(6)
        toolbar.set_margin_start(6)
        toolbar.set_margin_end(6)

        self.backButton = self.iconLabelButton('go-previous-symbolic', 'Back')
        self.backButton.set_sensitive(False)
        self.backButton.connect('clicked', self.onBack)
        toolbar.append(self.backButton)

        zoomin = self.iconLabelButton('zoom-in', 'Zoom in')
        zoomin.connect('clicked', self.onZoomIn)
        toolbar.append(zoomin)
        zoomout = self.iconLabelButton('zoom-out', 'Zoom out')
        zoomout.connect('clicked', self.onZoomOut)
        toolbar.append(zoomout)

        self.printButton = self.iconLabelButton('document-print-symbolic', 'Print')
        self.printButton.connect('clicked', self.onPrint)
        toolbar.append(self.printButton)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(toolbar)
        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        box.append(self.helpview)
        self.set_child(box)

        self.helpview.connect('decide-policy', self.decidePolicy)
        self.helpview.connect('load-changed', self.onLoadChanged)
        # Also refresh when the back/forward list changes (covers in-page history)
        self.helpview.get_back_forward_list().connect('changed', self.updateNav)

        settings = self.helpview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_allow_file_access_from_file_urls(True)
        self.helpview.load_uri(Path(userFile('.hidden/index.html')).as_uri())

    def iconLabelButton(self, iconName, text):
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        content.append(Gtk.Image.new_from_icon_name(iconName))
        content.append(Gtk.Label(label=text))
        button = Gtk.Button()
        button.set_child(content)
        return button

    def onZoomIn(self, button):
        self.helpview.set_zoom_level(self.helpview.get_zoom_level()+.1)

    def onZoomOut(self, button):
            self.helpview.set_zoom_level(self.helpview.get_zoom_level()-.1)

    def onBack(self, button):
        if self.helpview.can_go_back():
            self.helpview.go_back()

    def onPrint(self, button):
        printOp = WebKit.PrintOperation.new(self.helpview)
        printOp.run_dialog(self)

    def onLoadChanged(self, web_view, event):
        self.updateNav()

    def updateNav(self, *args):
        self.backButton.set_sensitive(self.helpview.can_go_back())

    def decidePolicy(self, web_view, decision, decision_type):
        if decision_type == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
            uri = decision.get_navigation_action().get_request().get_uri()
            decision.ignore()
            webbrowser.open(uri)
            return True
        return False


class HelpApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='com.hearham.repeaterstart.help')

    def do_activate(self):
        window = self.get_active_window() or HelpDialog(self)
        window.present()


if __name__ == '__main__':
    sys.exit(HelpApplication().run(sys.argv))
