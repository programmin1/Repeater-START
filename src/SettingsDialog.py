import gi
import os
import urllib

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk
import configparser
from CsvRepeaterListing import CsvRepeaterListing
from RepeaterStartCommon import userFile
from urllib.error import HTTPError

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
        if not 'DownloadOptions' in self.config:
            self.config['DownloadOptions'] = {
                'mobile' : False
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
        self.config['DownloadOptions'] = {
          'mobile' : self.builder.get_object('allowMobile').get_active()
        }
        with open(userFile('settings.ini'),'w') as outfile:
            self.config.write(outfile)
    
    def getAllowMobile(self):
        #note the STRING value of config values:
        return self.config['DownloadOptions']['mobile'].lower() != 'false'
    
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
            try:
                for name in self.config['Repeaters']:
                    row = Gtk.ListBoxRow()
                    row.add(Gtk.Label(name))
                    row.url = self.config['Repeaters'][name]
                    self.repolist.add(row)
                self.repolist.show_all()
            except AttributeError:
                print('Repeater row not found?')
        else:
            #Default case
            self.config['Repeaters'] = {
                'Hearham Amateur Radio Repeaters': "https://hearham.com/api/repeaters/v1"
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
        self.builder.get_object('allowMobile').set_active(self.getAllowMobile())

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
        
    def doMsg(self, title, msg):
        dialogWindow = Gtk.MessageDialog(self.dialog,
              Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
              Gtk.MessageType.WARNING,
              Gtk.ButtonsType.OK,
              title)
        dialogWindow.set_title(title)
        dialogBox = dialogWindow.get_content_area()
        userEntry = Gtk.Label()
        userEntry.set_size_request(140,12);
        userEntry.set_text(msg)
        dialogBox.pack_end(userEntry, False, False, 0)
        dialogWindow.show_all()
        print('shown')
        response = dialogWindow.run()
        dialogWindow.destroy()
        return
    
    def addRpt(self, *args):
        url = self.doDialog('Add repeaters by URL of listing:')
        tmpfile = userFile('repeater-temp-file.csv')
        if url and url.find('.csv') > -1 :
            try:
                #verify and get the name:
                #TODO should be in a background thread somehow
                urllib.request.urlretrieve(url, tmpfile)
                csv = CsvRepeaterListing(tmpfile)
                if csv.name:
                    row = Gtk.ListBoxRow()
                    row.add(Gtk.Label(csv.name))
                    row.url = url
                    self.repolist.add(row)
                    self.repolist.show_all()
                    self.config['Repeaters'][csv.name] = url
                else:
                    self.doMsg('Error:','Invalid entry? Must be a .csv file available on a server.')
            except HTTPError:
                self.doMsg('Error:','HTTP error- Must be a .csv file available on a server.')
            os.remove(tmpfile)
        elif url and url.find("hearham.com/api/repeaters/v1") > -1:
            #Re-add default:
            row = Gtk.ListBoxRow()
            row.add(Gtk.Label('Hearham Amateur Radio Repeaters'))
            row.url = "https://hearham.com/api/repeaters/v1"
            self.repolist.add(row)
            self.repolist.show_all()
            self.config['Repeaters']['Hearham Amateur Radio Repeaters'] = "https://hearham.com/api/repeaters/v1"
        elif len(url):
            self.doMsg('Error:','You must enter a full url of a .csv file.')
            return
        
    def rmRpt(self, *args):
        row = self.repolist.get_selected_row()
        for item in self.config['Repeaters']:
            if self.config['Repeaters'][item] == row.url:
                del self.config['Repeaters'][item]
                #TODO clean up files
        self.repolist.remove( row )
        
    def propertyRpt(self, *args):
        url = self.doDialog('Re/set current selected url:',self.repolist.get_selected_row().url)
        tmpfile = userFile('repeater-temp-file.csv')
        if url and url.find('.csv') > -1 :
            #verify and get the name:
            try:
                #TODO should be in a background thread somehow
                urllib.request.urlretrieve(url, tmpfile)
                csv = CsvRepeaterListing(tmpfile)
                if csv.name:
                    self.config['Repeaters'][csv.name] = url
                    self.repolist.get_selected_row().url = url
                    self.repolist.show_all()
                else:
                    self.doMsg('Error:','Invalid entry? Must be a .csv file available on a server.')
                os.remove(tmpfile)
            except HTTPError:
                self.doMsg('Error:','HTTP error- Must be a .csv file available on a server.')
            

    def onDestroy(self, *args):
        pass
        
    # Note this is also set as the close button's clicked signal.
    def onClosed(self, *args):
        self.writeSettings()
        self.parentWin.displayNodes()
        self.parentWin.refreshListing()
        self.dialog.destroy()
