from RepeaterStartCommon import userFile
import os

class HelpDialog():
    def __init__(self, parent, repeater):
        pro = userFile('.hidden')
        loadfile = 'file://'+pro+"/index.html"
        with open(os.path.join(pro,'base.data.js'), 'w') as outfile:
            outfile.write("CALL=\""+repeater.callsign+"\"; "+
                "FREQ=\""+str(repeater.freq)+"\";"+
                "OFFSET=\""+str(repeater.offset)+"\";"+
                "MODE=\""+str(repeater.mode)+"\";"+
                "PL=\""+str(repeater.pl)+"\";"+
                "URL=\""+str(repeater.url)+"\";");
        # Open built in Edge app view - inprivate so it does not pollute browser history:
        os.system('start msedge -inprivate --app='+loadfile)
