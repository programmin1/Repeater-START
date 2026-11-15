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
        self.set_child(self.helpview)
        self.helpview.connect('decide-policy', self.decidePolicy)
        settings = self.helpview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_allow_file_access_from_file_urls(True)
        self.helpview.load_uri(Path(userFile('.hidden/index.html')).as_uri())

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
