import os
import pathlib
import subprocess
import shutil
import json
import csv
import logging
from datetime import datetime
import lxml
from lxml import etree

import threading

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog

import UnityPy

from AssetTypes import WWiseAudio

UnityPyVersion = '1.9.24'

if UnityPy.__version__ != UnityPyVersion:
    raise ImportError(f"Invalid UnityPy version detected. Please use version {UnityPyVersion}")

logger = logging.getLogger(__name__)

def createLogger(type = 'console'):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    format = '%(levelname)s: %(message)s'
    datefmt = '%I:%M:%S %p'
    level = logging.DEBUG

    filename = f'logs/{datetime.now().strftime("%m-%d-%y_%H-%M-%S")}.log'
    # filename = 'log.log'
    
    handlers = []

    if type == 'file':
        handlers.append(logging.FileHandler(filename))
        format = '%(asctime)s %(levelname)s: %(message)s'
        try:
            os.mkdir('logs')
        except:
            pass

        # logging.basicConfig(filename=filename, filemode='w', format=format, datefmt=datefmt, level=level)
        # logger.info('logging file')
    
    handlers.append(logging.StreamHandler())
    logging.basicConfig(format=format, datefmt=datefmt, level=level, handlers=handlers)
    
    logger = logging.getLogger(__name__)
    logger.info(filename)
        

def loadCSV(path, **kwargs) -> list:
    output = []

    with open(path) as csvfile:
        reader = csv.reader(csvfile, **kwargs)
        for row in reader:
            output.append([c.strip() for c in row])

    return output

# logging.basicConfig(filename='log.log')

# createLogger()
# createLogger('file')

class Window(tk.Tk):
    def __init__(this, *args, **kwargs):
        super().__init__(*args, **kwargs)
        this.title('MKT Explorer')
        this.geometry('%dx%d' % (760 , 610) )
        
        # this.style = ttk.Style()
        # print(this.style.theme_names())
        # this.style.theme_use('winnative')
        
        this.settingsFile = 'settings.json'
        this.loadSettings()
        this.loadCatalog()
        
        this.output = 'tmp'
        this.nabe = ''
        
        this.createMenuBar()
        
        this.files = []
        this.assets = []
        this.fileStructure = {}
        this.environment = UnityPy.Environment()
        this.extracting = False

        this.notebook = ttk.Notebook()
        this.notebook.pack(fill='both', expand=True)
        
        this.pages = {
            'env': {
                'frame': ttk.Frame(this.notebook),
                'contents': {}
            },
            'assets': {
                'frame': ttk.Frame(this.notebook),
                'contents': {}
            },
            'structure': {
                'frame': ttk.Frame(this.notebook),
                'contents': {}
            }
        }
        
        this.notebook.add(this.pages['env']['frame'], text='Environment')
        this.notebook.add(this.pages['assets']['frame'], text='Assets')
        this.notebook.add(this.pages['structure']['frame'], text='Filesystem')
        
        this.createAssetsPage()
        this.createEnvPage()
        this.createStructurePage()
        
        this.progress = {
            'frame': ttk.Frame(this, borderwidth=2),
            'primary': {
                'bar': None,
                'label': None,
                'text_var': tk.StringVar(),
                'progress': tk.IntVar(value=0),
            },
            'secondary': {
                'bar': None,
                'label': None,
                'text_var': tk.StringVar(),
                'progress': tk.IntVar(value=0),
            },
        }
        
        this.progress['primary']['bar'] = ttk.Progressbar(this.progress['frame'], variable=this.progress['primary']['progress'])
        this.progress['primary']['label'] = ttk.Label(this.progress['frame'], textvariable=this.progress['primary']['text_var'])
        
        this.progress['primary']['bar'].grid(column=0, row=0, sticky='ew', pady=2, padx=2)
        this.progress['primary']['label'].grid(column=1, row=0, sticky='ew', pady=2, padx=2)
        
        this.progress['frame'].columnconfigure(0, weight=1)
        this.progress['frame'].columnconfigure(1, weight=1)
        
        this.progress['secondary']['bar'] = ttk.Progressbar(this.progress['frame'], variable=this.progress['secondary']['progress'])
        this.progress['secondary']['label'] = ttk.Label(this.progress['frame'], textvariable=this.progress['secondary']['text_var'])
        
        this.progress['secondary']['bar'].grid(column=0, row=1, sticky='ew', pady=2, padx=2)
        this.progress['secondary']['label'].grid(column=1, row=1, sticky='ew', pady=2, padx=2)
        
        # this.progress['frame'].columnconfigure(0, weight=1)
        # this.progress['frame'].columnconfigure(1, weight=1)
        
        this.progress['frame'].pack(fill='x')
        
        this.initialize()
        
    def createMenuBar(this):
        this.menuBar = tk.Menu(this, name='system')
        this.config(menu=this.menuBar)

        this.fileMenu = tk.Menu(this.menuBar, tearoff=0)
        this.fileMenu.add_command(label= 'Load Catalog', command=this.chooseCatalog)
        this.fileMenu.add_command(label= 'Load File', command=lambda : this.loadFile(this.chooseFile()))
        this.fileMenu.add_command(label= 'Load Nabe', command=this.loadFolder)
        this.fileMenu.add_separator()
        this.fileMenu.add_command(label='Extract File')
        this.fileMenu.add_command(label='Extract Audio Folder', command=this.extractNabeAudio)

        this.menuBar.add_cascade(label= 'File', menu=this.fileMenu)
        
    def initialize(this):
        this.protocol("WM_DELETE_WINDOW", this.close)
        
    def createStructurePage(this):
        this.pages['structure']['contents']['treeview'] = ttk.Treeview(this.pages['structure']['frame'], show='tree')
        this.pages['structure']['contents']['treeview'].pack(fill='both', expand=True)
        
        this.pages['structure']['contents']['scrollbar'] = ttk.Scrollbar(this.pages['structure']['contents']['treeview'], orient='vertical', command=this.pages['structure']['contents']['treeview'].yview)
        
        this.pages['structure']['contents']['treeview'].config(yscrollcommand=this.pages['structure']['contents']['scrollbar'].set)
        this.pages['structure']['contents']['scrollbar'].pack(fill='y', side='right')
        
    def createEnvPage(this):
        this.pages['env']['contents']['treeview'] = ttk.Treeview(this.pages['env']['frame'], show='tree')
        this.pages['env']['contents']['treeview'].pack(fill='both', expand=True)
        
        this.pages['env']['contents']['scrollbar'] = ttk.Scrollbar(this.pages['env']['contents']['treeview'], orient='vertical', command=this.pages['env']['contents']['treeview'].yview)
        
        this.pages['env']['contents']['treeview'].config(yscrollcommand=this.pages['env']['contents']['scrollbar'].set)
        this.pages['env']['contents']['scrollbar'].pack(fill='y', side='right')
    
    def createAssetsPage(this):
        this.pages['assets']['columns'] = ['name', 'container', 'type', 'pathID', 'size']
        this.pages['assets']['contents']['treeview'] = ttk.Treeview(this.pages['assets']['frame'], columns=this.pages['assets']['columns'], show='headings')
        this.pages['assets']['contents']['scrollbar'] = ttk.Scrollbar(this.pages['assets']['contents']['treeview'], orient='vertical', command=this.pages['assets']['contents']['treeview'].yview)
        
        this.pages['assets']['contents']['treeview'].config(yscrollcommand=this.pages['assets']['contents']['scrollbar'].set)
        this.pages['assets']['contents']['scrollbar'].pack(fill='y', side='right')
        
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
        
    def updateEnv(this):
        this.pages['env']['contents']['treeview'].delete(*this.pages['env']['contents']['treeview'].get_children())
        for cab in this.environment.cabs:
            this.pages['env']['contents']['treeview'].insert('', 'end', text=cab)
        
    
    def updateAssets(this):
        this.pages['assets']['contents']['treeview'].delete(*this.pages['assets']['contents']['treeview'].get_children())
        for asset in this.assets:
        # ['name', 'container', 'type', 'pathID', 'size']
            if isinstance(asset, WWiseAudio):
                values = [asset.container, asset.container, 'WWise_Audio', 0, asset.FileSize]
            else:
                values = [asset.name, asset.container, asset.type.name, asset.path_id, '']
                
            this.pages['assets']['contents']['treeview'].insert('', 'end', values=values)
    
    def updateStructure(this):
        this.pages['structure']['contents']['treeview'].delete(*this.pages['structure']['contents']['treeview'].get_children())
        
        def addToStructure(data : dict, id = ''):
            for d in data:
                newID = this.pages['structure']['contents']['treeview'].insert(id, 'end', text=d)
                if isinstance(data[d], dict):
                    addToStructure(data[d], newID)
                logger.debug(f'{data[d] = }\n{newID = }')
        
        logger.debug(this.fileStructure)
        addToStructure(this.fileStructure)
        
    def chooseFile(this):
        file = filedialog.askopenfilename(title='Choose File', defaultextension='*.*', filetypes=((('any', '*.*'), ('WWise audio', '*.pck'), )))
        return file
    
    def chooseCatalog(this):
        file = filedialog.askopenfilename(title='Choose Catalog', defaultextension='*.csv', filetypes=((('Catalog file', '*.csv'), ('any', '*.*'), )))
        this.loadCatalog(file)
        return file
    
    def chooseFolder(this):
        folder = filedialog.askdirectory(title='Pick Folder')
        return folder
    
    def loadFolder(this):
        folder = this.chooseFolder()
        thread = threading.Thread(target=lambda : this.loadNabe(folder))
        thread.start()
    
    def loadNabe(this, folder):
        if not folder:
            return
        
        this.nabe = folder
        
        this.assets = []
        this.fileStructure = {}
        this.environment = UnityPy.Environment()
        
        # logger.info(this.catalog)
        
        this.progress['primary']['bar']['max'] = len(this.catalog)
        
        for key,state,type,path in this.catalog:
            # if not this.extracting:
            #     break
            
            this.progress['primary']['progress'].set(this.progress['primary']['progress'].get() + 1)
            nabepath = pathlib.Path(path)
            parts = nabepath.parts[2:]
            nabepath = pathlib.Path(this.nabe, *parts)
            nabepath = nabepath.as_posix()
            
            this.progress['primary']['text_var'].set(f"({this.progress['primary']['progress'].get()}/{this.progress['primary']['bar']['max']}) {os.path.basename(key)}")
            # this.update()
            
            # try:
            # logger.info(nabepath)
            this.loadFile(nabepath, container=key)
            # except Exception as e:
            #     logger.warning(f'unable to load file {nabepath}')
            #     logger.error(str(e))
        
        this.assets = this.assets + this.environment.objects
        
        for asset in  this.assets:
            if asset.container:
                this.addToFilesystem(asset.container, asset)
        
        this.updateEnv()
        this.updateAssets()
        this.updateStructure()
    
    def addToFilesystem(this, path, file, **kwargs):
        if isinstance(path, (list, tuple)):
            data = kwargs['data']
            if len(path) <= 1:
                data[path[0]] = file
                return data
            
            try:
                data[path[0]]
                # if not isinstance(data[path[0]], dict):
                #     logging.error(f'Path {data} taken')
            except:
                data[path[0]] = {}
                
            if not isinstance(data[path[0]], dict):
                logging.error(f'Path {data} taken')
                return data
            
            data = data[path[0]]
            
            this.addToFilesystem(path[1:], file, data=data)
        else:
            parts = pathlib.Path(path).parts
            if parts[0] == '':
                parts = parts[1:]
            
            this.addToFilesystem(parts, file, data=this.fileStructure)
            
    
    def loadFile(this, path, container = None):
        logger.info(path)
        if not os.path.isfile(path):
            return
        type = UnityPy.helpers.ImportHelper.check_file_type(path)
        logger.info(type[0].value)
        
        # File types:
            
        #     AssetsFile = 0
        #     BundleFile = 1
        #     WebFile = 2
        #     ResourceFile = 9
        #     ZIP = 10
        
        if type[0].value == 9:
            this.assets.append(WWiseAudio(path, container=container))
        else:
            this.environment.load_file(path)
            # env = UnityPy.load(path)
            # this.assets = this.assets + env.objects
            
        this.files.append(path)
            
        # this.assets = objects
        
        # logger.info(this.files)
        # logger.info(this.assets)
        
    def extractAudio(this):
        this.extracting = True
        this.progress['primary']['bar']['max'] = len(this.catalog)
        
        this.progress['primary']['progress'].set(0)
        
        for key,state,type,path in this.catalog:
            if not this.extracting:
                break
            
            this.progress['primary']['progress'].set(this.progress['primary']['progress'].get() + 1)
            nabepath = pathlib.Path(path)
            parts = nabepath.parts[2:]
            nabepath = pathlib.Path(this.nabe, *parts)
            nabepath = nabepath.as_posix()
            
            this.progress['primary']['text_var'].set(os.path.basename(key))
            # this.progress['primary']['progress'].set(this.progress['primary']['progress'].get() + 1)
            
            # this.update()
            
            if not parts or parts[0] != 'b':
                continue
            
            file = os.path.basename(key)
            name, type = os.path.splitext(file)
            type = type[1:]
            
            if type != 'pck':
                continue
            
            logger.info(f'exporting {file}')
            
            pckdestination = os.path.join(this.output, 'PCK', file)
            os.makedirs(os.path.dirname(pckdestination), exist_ok=True)
            try:
                shutil.copy(nabepath, pckdestination)
            except Exception as e:
                logger.warning(f'unable to copy file {nabepath}')
                logger.error(str(e))
            
            try:
                object = WWiseAudio(nabepath)
                # this.progress['secondary']['bar']['max'] = len(object.files)
                this.progress['secondary']['progress'].set(0)
                destination = os.path.join(this.output, 'WAV', name)
                os.makedirs(destination, exist_ok=True)
                object.extractAudio(destination)
                
                # for wem in object.files:
                #     logger.info(f'  {os.path.splitext(wem.name)[0] + ".wav"}')
                #     destination = os.path.join(this.output, 'WAV', name)
                    
                #     this.progress['secondary']['progress'].set(this.progress['secondary']['progress'].get() + 1)
                #     this.progress['secondary']['text_var'].set(wem.name)
                    
                #     os.makedirs(destination, exist_ok=True)
                #     wem.read('wav')
                #     wem.export(os.path.join(destination, (os.path.splitext(wem.name)[0] + '.wav')))
                 
            except Exception as e:
                logger.warning(f'unable to load WWise audio {nabepath}')
                logger.error(str(e))
                
            this.progress['secondary']['text_var'].set('Done!')
            
        this.progress['primary']['text_var'].set('Done!')
        logger.info('Done!')
        this.extracting = False
        
    def extractNabeAudio(this):
        this.nabe = filedialog.askdirectory(title='choose nabe')
        if not this.nabe:
            return
        this.output = filedialog.askdirectory(title='choose output folder')
        if not this.output:
            return
        
        thread = threading.Thread(target=this.extractAudio)
        thread.start()
        
        
    def setExtractingState(this, state = False):
        this.extracting = state
        return this.extracting
        
    # settings
    def loadSettings(this, **kwargs):
        try:
            this.settings = kwargs['settings']
        except:
            try:
                with open(this.settingsFile, 'r') as file:
                    this.settings = json.load(file)

                logger.info(this.settings)
            except:
                this.initSettings()
                this.saveSettings()
                
    def loadCatalog(this, path = None):
        if path:
            this.settings['catalog'] = path
        try:
            this.catalog = loadCSV(this.settings['catalog'], delimiter=',', quotechar='"')
        except:
            logger.warning(f'Unable to load catalog: {this.settings["catalog"]}')
            
        this.saveSettings()
        
    def initSettings(this):
        this.settings = {
            'catalog': 'catalog.csv',
            'RavioliGameTools': {
               'path': 'tools/RavioliGameTools_v2.10'
            },
        }
        
    def saveSettings(this):
        file = open(this.settingsFile, 'w+')
        json.dump(this.settings, file, indent=2)
        
    def close(this):
        this.setExtractingState(False)
        this.destroy()
        
def main():
    app = Window()
    app.mainloop()

if __name__ == '__main__':
    createLogger('file')
    main()