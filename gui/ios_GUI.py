from tkinter import *
from tkinter.ttk import Treeview,Combobox,Style
from tkinter import filedialog,messagebox
import pip._internal as pip
import platform
import sys,os
import logging,requests

from rich.logging import RichHandler
#mvt module imports, if not exit install it
try:
    from mvt.ios.decrypt import DecryptBackup
    from mvt.ios.modules.backup import BACKUP_MODULES
    from mvt.ios.modules.fs import FS_MODULES
    from mvt.ios.modules.mixed import MIXED_MODULES
    from mvt.common.module import run_module,save_timeline
    from mvt.common.indicators import Indicators, IndicatorsFileBadFormat
except ImportError:
    pip.main(['install', 'mvt'])
    from mvt.ios.decrypt import DecryptBackup
    from mvt.ios.modules.backup import BACKUP_MODULES
    from mvt.ios.modules.fs import FS_MODULES
    from mvt.ios.modules.mixed import MIXED_MODULES
    from mvt.common.indicators import Indicators, IndicatorsFileBadFormat
    from mvt.common.module import run_module,save_timeline

# Setup logging using Rich.
LOG_FORMAT = "[%(name)s] %(message)s"
logging.basicConfig(level="INFO", format=LOG_FORMAT, handlers=[
    RichHandler(show_path=False, log_time_format="%X")])
log = logging.getLogger(__name__)

# If is windows, use the default path as default
backupFolder:str =''
if platform.system()=='Windows':
    backupFolder = os.path.expanduser('~\Apple') + '\MobileSync\Backup'
elif platform.system()=='Darwin':
    backupFolder = 'C:\\'
else:
    sys.exit("Operating system is not compatible")

#use the correct slashes according to OS
decryptedFolder:str =''
resultsFolder:str =''
if platform.system()=='Windows':
    decryptedFolder = 'C:/'
elif platform.system()=='Darwin':
    decryptedFolder = 'C:\\'
else:
    sys.exit("Operating system is not compatible")
#function to download automatic the STIX files
def dowload_STIX(output):
    pegasus = 'https://raw.githubusercontent.com/AmnestyTech/investigations/master/2021-07-18_nso/pegasus.stix2'
    predator = 'https://raw.githubusercontent.com/AmnestyTech/investigations/master/2021-12-16_cytrox/cytrox.stix2'
    r1 = requests.get(pegasus, allow_redirects=False)
    r2 = requests.get(predator, allow_redirects=False)
    h = open(output + 'pegasus.stix2', 'wb').write(r1.content)
    h = open(output +'cytrox.stix2', 'wb').write(r2.content)
    return [output + 'pegasus.stix2',output +'cytrox.stix2']
    
def browseFileAction(event,obj, id):
    global backupFolder,decryptedFolder,resultsFolder
    searchPathDirectory = filedialog.askdirectory(title="select", initialdir=backupFolder)
    #update the path in the label's text
    obj["text"] = searchPathDirectory
    #update the #Global variable
    if id=="INPUT":
        backupFolder = searchPathDirectory
    else :
        #set output and results folder
        decryptedFolder = searchPathDirectory
        if platform.system()=='Windows':
           resultsFolder = decryptedFolder + '/Results/'
        elif platform.system()=='Darwin':
           resultsFolder = decryptedFolder + '\Results\\'
        else:
           sys.exit("Operating system is not compatible")

#use underscore to avoid conflict
def check_backup__(output, backup_path,iocs):

    log.info("Checking iTunes backup located at: %s", backup_path)

    if output and not os.path.exists(output):
        try:
            os.makedirs(output)
        except Exception as e:
            log.critical("Unable to create output folder %s: %s", output, e)
            os.exit(1)

    indicators = Indicators(log=log)
    for ioc_path in iocs:
        try:
            indicators.parse_stix2(ioc_path)
        except IndicatorsFileBadFormat as e:
            log.critical(e)
            os.exit(1)
    log.info("Loaded a total of %d indicators", indicators.ioc_count)

    timeline = []
    timeline_detected = []
    for backup_module in BACKUP_MODULES + MIXED_MODULES:
        
        m = backup_module(base_folder=backup_path, output_folder=output, fast_mode=False,
                          log=logging.getLogger(backup_module.__module__))
        m.is_backup = True
        
        if iocs:
            m.indicators = indicators
            m.indicators.log = m.log
        
        run_module(m)
        timeline.extend(m.timeline)
        timeline_detected.extend(m.timeline_detected)

    if output:
        if len(timeline) > 0:
            save_timeline(timeline, os.path.join(output, "timeline.csv"))
        if len(timeline_detected) > 0:
            save_timeline(timeline_detected, os.path.join(output, "timeline_detected.csv"))
    log.info("Checking completed")

def run(event,arg, id):
    global backupFolder,decryptedFolder,resultsFolder
    password = arg.get()
    if len(password)==0:
        messagebox.showerror("Password required", "Please enter first your backup password.")
        return
    
    backup = DecryptBackup(backupFolder, decryptedFolder)
    backup.decrypt_with_password(password)
    #start decryption
    backup.process_backup()
    l = dowload_STIX(resultsFolder)
    #check the stored links against the STIX
    check_backup__(resultsFolder,decryptedFolder,l)
    

app = Tk()
#Create first frame for some infos
frameInfo = LabelFrame(app, text="Info",pady=5)
frameInfo.grid(row=0, column=0,padx=5,sticky=W)
lblRootFolder = Label(frameInfo, text='Select backup folder: ',
                   font=('normal', 11),padx=10)
lblRootFolder.grid(row=0, column=0)
lblRootFolderName = Label(frameInfo, text=backupFolder,
                   font=('normal', 11),width=40,wraplength=280)
lblRootFolderName.grid(row=0, column=1)
browseButton = Button(frameInfo, text = 'Browse', width = 14)
browseButton.grid(row=0, column=2,pady=4)
outputFolder = Button(frameInfo, text='Browse', width=14)
outputFolder.grid(row=1, column=2,padx=4)
lblSessionStatus = Label(frameInfo, text='Browse decrypted path: ',
                   font=('normal', 11))
lblSessionStatus.grid(row=1, column=0,padx=10)
lblSessionStatusMessage = Label(frameInfo, text=decryptedFolder,
                   font=('normal', 11),width=40,wraplength=280)
lblSessionStatusMessage.grid(row=1, column=1)

labelEnterPassword = Label(frameInfo, text='Enter your backup password: ',
                   font=('normal', 11),padx=10)
labelEnterPassword.grid(row=3, column=0)

passwordEnrty = Entry(frameInfo, show="*", width=15)
passwordEnrty.grid(row=3, column=2,padx=4)


runButton = Button(frameInfo,text='Run analysis', width=14)
runButton.grid(row=4, column=0,padx=4)

# Create bind
#connect browse button with the action function.
browseButton.bind("<ButtonRelease-1>",lambda event, objToLabel=lblRootFolderName: browseFileAction(event,objToLabel, 'INPUT') )
outputFolder.bind("<ButtonRelease-1>",lambda event, objToLabel=lblSessionStatusMessage: browseFileAction(event,objToLabel, 'OUTPUT') )
runButton.bind("<ButtonRelease-1>",lambda event, objToLabel=passwordEnrty: run(event,objToLabel, 'buttonRelease1') )

#Create and call main window
app.title('Predator/Pegasus iOS scanner GUI')
app.geometry('720x150')
# Add Some Style
style = Style()


# Pick A Theme
style.theme_use('default')

# Main window
#add some action before closing window.
def on_closing():
    app.destroy()
app.protocol("WM_DELETE_WINDOW",on_closing)
# Start program
app.mainloop()
