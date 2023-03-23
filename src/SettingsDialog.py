import gi
import os
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
import configparser
from RepeaterStartCommon import userFile

class SettingsDialog:
    def __init__(self, parentWin):
        self.parentWin = parentWin
        self.config = configparser.ConfigParser()
        if os.path.exists(userFile('settings.ini')):
            self.config.read(userFile('settings.ini'))
        else: #defaults:
            self.config['ViewOptions'] = {
             'unitsLength': 'mi',
             'filterMin' : '',
             'filterMax' : ''
            }
        #Just ham radio constants:
        self.UHFMIN = '420'
        self.UHFMAX = '450'
        self.VHFMIN = '144'
        self.VHFMAX = '148'
            
    def writeSettings(self):
        # Save the config to the file:
        units = 'mi'
        if self.builder.get_object('distUnitsRadioKM').get_active():
            units = 'km'
        self.config['ViewOptions'] = {
         'unitsLength': units,
         'filterMin' : self.builder.get_object('lblMinFreq').get_text(),
         'filterMax' : self.builder.get_object('lblMaxFreq').get_text()
        }
        with open(userFile('settings.ini'),'w') as outfile:
            self.config.write(outfile)
    
    def getMinFilter(self):
        value = self.config['ViewOptions']['filterMin']
        try:
            return float(value)
        except ValueError:
            return -1

    def getMaxFilter(self):
        value = self.config['ViewOptions']['filterMax']
        try:
            return float(value)
        except ValueError:
            return 9e999

    def getUnit(self):
        return self.config['ViewOptions']['unitsLength']
        
    def getShown(self):
        if 'Repeaters' in self.config:
            print(self.config['Repeaters'])
            for name in self.config['Repeaters']:
                row = Gtk.ListBoxRow()
                row.add(Gtk.Label(name))
                row.url = self.config['Repeaters'][name]
                self.repolist.add(row)
            self.repolist.show_all()
        else:
            #Default case
            row = Gtk.ListBoxRow()
            row.add(Gtk.Label('Hearham Amateur Radio Repeaters'))
            row.url = 'https://hearham.com/api/repeaters/v1'
            self.repolist.add(row)
            self.repolist.show_all()
            self.config['Repeaters'] = {
                'Hearham': row.url
            }
        return self.config['Repeaters']

    def show(self):
        #Create GtkDialog
        self.builder = Gtk.Builder()
        self.builder.add_from_file('SettingsDialog.glade')
        self.builder.connect_signals(self)
        self.dialog = self.builder.get_object('SettingsDialog')
        #self.dialog.set_parent(parentWin)
        self.dialog.set_transient_for(self.parentWin) #Over the main window.
        self.dialog.set_modal(True)
        #self.dialog.set_redraw_on_allocate(True)
        self.dialog.set_title('Settings')
        
        self.repolist = self.builder.get_object('repeaterRepos')
        self.getShown()
        
        self.dialog.show_all()
        #Load the config to the form
        options = self.config['ViewOptions']
        if options['unitsLength'] == 'km':
            self.builder.get_object('distUnitsRadioKM').set_active(True)
        if self.getMinFilter() > 0:
            self.builder.get_object('filterFreqCustom').set_active(True)
            # ^ if nofilter is selected, the default, then they are cleared with NoFilterSet()
            self.builder.get_object('lblMinFreq').set_text(str(options['filterMin']))
        if self.getMaxFilter() < 9e999:
            self.builder.get_object('filterFreqCustom').set_active(True)
            self.builder.get_object('lblMaxFreq').set_text(str(options['filterMax']))
        if self.getMinFilter() == float(self.VHFMIN) and self.getMaxFilter() == float(self.VHFMAX):
            self.builder.get_object('freqFilterVHF').set_active(True)
        if self.getMinFilter() == float(self.UHFMIN) and self.getMaxFilter() == float(self.UHFMAX):
            self.builder.get_object('freqFilterUHF').set_active(True)

    # User actions on the form:
    def NoFilterSet(self, *args):
        self.builder.get_object('lblMinFreq').set_text('')
        self.builder.get_object('lblMaxFreq').set_text('')

    def VHFSet(self, *args):
        self.builder.get_object('lblMinFreq').set_text(self.VHFMIN)
        self.builder.get_object('lblMaxFreq').set_text(self.VHFMAX)
        
    def UHFSet(self, *args):
        self.builder.get_object('lblMinFreq').set_text(self.UHFMIN)
        self.builder.get_object('lblMaxFreq').set_text(self.UHFMAX)
    
    def doDialog(self, title, inputarea=''):
        dialogWindow = Gtk.MessageDialog(self.dialog,
              Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
              Gtk.MessageType.QUESTION,
              Gtk.ButtonsType.OK_CANCEL,
              title)

        dialogWindow.set_title(title)
        dialogBox = dialogWindow.get_content_area()
        userEntry = Gtk.Entry()
        userEntry.set_size_request(140,12);
        userEntry.set_text(inputarea)
        dialogBox.pack_end(userEntry, False, False, 0)
        dialogWindow.show_all()
        response = dialogWindow.run()
        text = userEntry.get_text()
        dialogWindow.destroy()
        return text
    
    def addRpt(self, *args):
        url = self.doDialog('Add repeaters by URL of listing:')
        if url and url.find('.csv') > -1 :
            row = Gtk.ListBoxRow()
            row.add(Gtk.Label(url))
            self.repolist.add(row)
            self.repolist.show_all()
            self.config['Repeaters']['yournamehere'] = url
        
    def rmRpt(self, *args):
        self.repolist.remove( self.repolist.get_selected_row() )
        
    def propertyRpt(self, *args):
        url = self.doDialog('Re/set current selected url:',self.repolist.get_selected_row().url)
        if url:
            self.repolist.get_selected_row().url = url

    def onDestroy(self, *args):
        pass
        
    # Note this is also set as the close button's clicked signal.
    def onClosed(self, *args):
        self.writeSettings()
        self.parentWin.displayNodes()
        self.parentWin.refreshListing()
        self.dialog.destroy()
