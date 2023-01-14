import os
import subprocess
import shutil
import json
import csv
import logging
from datetime import datetime

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog

import UnityPy

UnityPyVersion = '1.9.24'

if UnityPy.__version__ != UnityPyVersion:
    raise ImportError(f"Invalid UnityPy version detected. Please use version {UnityPyVersion}")

def createLogger(type = 'console'):
    format = '%(levelname)s: %(message)s'
    datefmt = '%I:%M:%S %p'
    level = logging.DEBUG

    filename = f'logs/{datetime.now().strftime("%m-%d-%y_%H-%M-%S")}.log'

    if type == 'file':
        format = '%(asctime)s %(levelname)s: %(message)s'
        try:
            os.mkdir('logs')
        except:
            pass

        logging.basicConfig(filename=filename, filemode='w', format=format, datefmt=datefmt, level=level)
    else:
        logging.basicConfig(format=format, datefmt=datefmt, level=level)

def loadCSV(path, **kwargs) -> list:
    output = []

    with open(path) as csvfile:
        reader = csv.reader(csvfile, **kwargs)
        for row in reader:
            output.append([c.strip() for c in row])

    return output

createLogger()
# createLogger('file')

class Window(tk.Tk):
    def __init__(this, *args, **kwargs):
        super().__init__(*args, **kwargs)
        this.title('')
        this.geometry('%dx%d' % (760 , 610) )
        
        # this.style = ttk.Style()
        # print(this.style.theme_names())
        # this.style.theme_use('winnative')
        
        this.loadSettings()
        this.loadCatalog()
        
        this.output = 'tmp'
        
        this.createMenuBar()
        
        this.files = []
        this.assets = []
        this.fileStructure = {}
        this.environment = UnityPy.Environment()

        this.notebook = ttk.Notebook()
        this.notebook.pack(fill='both', expand=True)
        
        this.pages = {
            'assets': {
                'frame': ttk.Frame(this.notebook),
                'contents': {}
            }
        }
        
        this.notebook.add(this.pages['assets']['frame'], text='Assets')
        
        this.createAssets()
        
        this.initialize()
        
    def createMenuBar(this):
        this.menuBar = tk.Menu(this, name='system')
        this.config(menu=this.menuBar)

        this.fileMenu = tk.Menu(this.menuBar, tearoff=0)
        this.fileMenu.add_command(label= 'Load File')
        this.fileMenu.add_command(label= 'Load Folder')
        this.fileMenu.add_separator()
        this.fileMenu.add_command(label='Extract File')
        this.fileMenu.add_command(label='Extract Folder')

        this.menuBar.add_cascade(label= 'File', menu=this.fileMenu)
        
    def initialize(this):
        pass
    
    def createAssets(this):
        this.pages['assets']['columns'] = ['name', 'container', 'type', 'pathID', 'size']
        this.pages['assets']['contents']['treeview'] = ttk.Treeview(this.pages['assets']['frame'], columns=this.pages['assets']['columns'], show='headings')
        
        columnWidth = 1
        
        this.pages['assets']['contents']['treeview'].heading('name', text='Name', anchor='w')
        this.pages['assets']['contents']['treeview'].column('name', width=columnWidth)

        this.pages['assets']['contents']['treeview'].heading('container', text='Container', anchor='w')
        this.pages['assets']['contents']['treeview'].column('container', width=columnWidth)

        this.pages['assets']['contents']['treeview'].heading('type', text='Type', anchor='w')
        this.pages['assets']['contents']['treeview'].column('type', width=columnWidth)

        this.pages['assets']['contents']['treeview'].heading('pathID', text='PathID', anchor='w')
        this.pages['assets']['contents']['treeview'].column('pathID', width=columnWidth)

        this.pages['assets']['contents']['treeview'].heading('size', text='Size', anchor='w')
        this.pages['assets']['contents']['treeview'].column('size', width=columnWidth)
        
        this.pages['assets']['contents']['treeview'].pack(fill='both', expand=True)
        
    def chooseFile(this):
        file = filedialog.askopenfilename(title='Choose File', defaultextension='*.*', filetypes=('any', '*.*'))
        return file
    
    def chooseFolder(this):
        folder = filedialog.askdirectory(title='Pick Folder')
        return folder
    
    def loadFile(this, path):
        pass
    
    class Audio():
        def __init__(self, file) -> None:
            pass
    
    def extractAudio(this, path):
        os.makedirs('tmp/audio', exist_ok=True)
        
        subprocess.run([f"{this.settings['RavioliGameTools']['path']}/RExtractorConsole.exe", path, 'tmp/audio', this.settings['RavioliGameTools']['args']])
        
        
        
    
    # settings
    def loadSettings(this, **kwargs):
        try:
            this.settings = kwargs['settings']
        except:
            try:
                with open(this.settingsFile, 'r') as file:
                    this.settings = json.load(file)

                logging.info(this.settings)
            except:
                this.initSettings()
                this.saveSettings()
                
    def loadCatalog(this):
        try:
            this.catalog = loadCSV(this.settings['catalog'], delimiter=',', quotechar='"')
        except:
            logging.warning(f'Unable to load catalog: {this.settings["catalog"]}')
        
    def initSettings(this):
        this.settings = {
            'catalog': 'catalog.csv',
            'RavioliGameTools': {
               'path': 'tools/RavioliGameTools_v2.10',
               'args': '/s /sf:wav /as'
            },
        }
        
        """
        Ravioli Tools Options:
        /subdir                   Create subdirectory for each input file
            (short form: /s)
        /imageformat:<extension>  Convert image format during extraction
            (short form: /if)
        /soundformat:<extension>  Convert sound format during extraction
            (short form: /sf)
        /fallbacksoundformat:<extension>  Convert to this format if conversion
            (short form: /fsf)            to the format specified in /soundformat is
                                          not possible
        /extract                  Start extraction automatically and exit
            (short form: /e)      when finished (for GUI version only)
        /archivetype:<name>       Specify the archive type to use for extraction
            (short form: /at)
        /allowscanning            Allow scanning of unknown files
            (short form: /as)
        /rootdir:<RootDirectory>[;<RootDirectory>;...]  Specify root directories
            (short form: /rd)
        /help                     Show this help message
            (short form: /?)
        """
        

    def saveSettings(this):
        file = open(this.settingsFile, 'w+')
        json.dump(this.settings, file, indent=2)
        
def main():
    app = Window()
    app.mainloop()

if __name__ == '__main__':
    main()