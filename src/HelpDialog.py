import gi
gi.require_version("Gtk", "3.0")
try:    
    gi.require_version('WebKit2', '4.1')
except:
    gi.require_version('WebKit2', '4.0') #older Ubuntu 22.04 etc.
from gi.repository import Gtk
from gi.repository import WebKit2
from RepeaterStartCommon import userFile
import os

class HelpDialog(Gtk.Dialog):
    def __init__(self, parent, repeater):
        super().__init__(title="Repeater Setup Help", transient_for=parent, flags=0)
        self.set_default_size(600, 900)
        box = self.get_content_area()
        self.helpview = WebKit2.WebView()
        
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        sw.add(self.helpview)
        self.helpview.connect('decide_policy',self.decidePolicy)
        box.pack_start(sw, True,True, 0)
        
        pro = userFile('.hidden')
        loadfile = 'file://'+pro+"/index.html"
        if not os.path.exists(pro):
            os.mkdir(pro)
        settings = self.helpview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_allow_file_access_from_file_urls(True)
        #TODO unzip.
        with open(os.path.join(pro,'base.data.js'), 'w') as outfile:
            outfile.write("CALL=\""+repeater.callsign+"\"; "+
                "FREQ=\""+str(repeater.freq)+"\";"+
                "OFFSET=\""+str(repeater.offset)+"\";"+
                "MODE=\""+str(repeater.mode)+"\";"+
                "PL=\""+str(repeater.pl)+"\";"+
                "PLDECODE=\""+str(repeater.decode if hasattr(repeater,'decode') else "")+"\";"+
                "DISABLED="+('true' if repeater.isDown() else 'false')+";"+
                "URL=\""+str(repeater.url)+"\";");
        self.helpview.load_uri(loadfile)
        #box.show()
        self.show_all()
    
    def decidePolicy(self, web_view, decision, decision_type):
        if decision_type == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION:
            navigation_action = decision.get_navigation_action()
            request = navigation_action.get_request()
            uri = request.get_uri()
            decision.ignore()
            os.system(f'xdg-open "{uri}"')
            return True
        decision.use()
        return False #Default behavior