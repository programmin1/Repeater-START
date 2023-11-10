#Common functions
import os
from gi.repository import GLib

def userFile(name):
    """ Returns available filename in user data dir for this app. """
    mydir = os.path.join(GLib.get_user_data_dir(),'repeater-START')
    if not os.path.exists(mydir):
        os.mkdir(mydir)
    return os.path.join(mydir,name)
