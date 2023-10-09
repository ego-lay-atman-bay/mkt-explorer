import csv
import json
import logging
import os
import pathlib
import shutil
import subprocess
import threading
import time
import tkinter as tk
import tkinter.filedialog as filedialog
import tkinter.ttk as ttk
from datetime import datetime
from tkinter import messagebox
from settings import Settings
from zipfile import ZipFile
import py7zr
import tempfile

import internetarchive as ia
import lxml
import UnityPy
from lxml import etree

from assetTypes import WWiseAudio

UnityPyVersion = '1.9.24'

if UnityPy.__version__ != UnityPyVersion:
    raise ImportError(f"Invalid UnityPy version detected. Please use version {UnityPyVersion}")

logger = logging.getLogger(__name__)

def createLogger(type = 'console'):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    format = '[%(levelname)s] %(message)s'
    datefmt = '%I:%M:%S %p'
    level = logging.DEBUG

    filename = f'logs/{datetime.now().strftime("%m-%d-%y_%H-%M-%S")}.log'
    # filename = 'log.log'

    handlers = []

    if type == 'file':
        try:
            os.mkdir('logs')
        except:
            pass

        handlers.append(logging.FileHandler(filename))
        format = '[%(asctime)s] [%(levelname)s] %(message)s'

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

        this.threads = set()

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
        this.stop = threading.Event()

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
        this.createProgress()

        this.initialize()

    def createProgress(this):


        this.progress = {
            'frame': ttk.Frame(this),
            'primary': {
                'bar': None,
                'label': None,
                'text_var': tk.StringVar(this),
                'text': '',
                'event': '',
                'progress': tk.IntVar(this, value=0),
            },
            'secondary': {
                'bar': None,
                'label': None,
                'text_var': tk.StringVar(this, ),
                'text': '',
                'event': '',
                'progress': tk.IntVar(this, value=0),
            },
        }

        this.progress['primary']['bar'] = ttk.Progressbar(this.progress['frame'], variable=this.progress['primary']['progress'])
        this.progress['primary']['label'] = ttk.Label(this.progress['frame'], textvariable=this.progress['primary']['text_var'])

        this.progress['primary']['bar'].grid(column=0, row=0, sticky='ew', pady=2, padx=2)
        this.progress['primary']['label'].grid(column=1, row=0, sticky='w', pady=2, padx=2)

        # this.progress['frame'].columnconfigure(0, weight=1)
        # this.progress['frame'].columnconfigure(1, weight=1)

        this.progress['secondary']['bar'] = ttk.Progressbar(this.progress['frame'], variable=this.progress['secondary']['progress'])
        this.progress['secondary']['label'] = ttk.Label(this.progress['frame'], textvariable=this.progress['secondary']['text_var'])

        this.progress['secondary']['bar'].grid(column=0, row=1, sticky='ew', pady=2, padx=2)
        this.progress['secondary']['label'].grid(column=1, row=1, sticky='w', pady=2, padx=2)

        this.progress['frame'].columnconfigure(0, weight=1, uniform='column')
        this.progress['frame'].columnconfigure(1, weight=1, uniform='column')

        this.progress['frame'].pack(fill='x', side='bottom')

        # events

        this.event_generate('<<UpdatePrimaryProgress>>')
        this.bind('<<UpdatePrimaryProgress>>', this.addProgress)

        this.event_generate('<<UpdateSecondaryProgres>>')
        this.bind('<<UpdateSecondaryProgress>>', lambda e : this.addProgress(e, 'secondary'))

        this.event_generate('<<ResetPrimaryProgress>>')
        this.bind('<<ResetPrimaryProgress>>', this.resetProgress)

        this.event_generate('<<ResetSecondaryProgress>>')
        this.bind('<<ResetSecondaryProgress>>', lambda e : this.resetProgress(e, 'secondary'))

        this.event_generate('<<UpdatePrimaryProgressText>>')
        this.bind('<<UpdatePrimaryProgressText>>', this.setProgressText)

        this.event_generate('<<UpdateSecondaryProgressText>>')
        this.bind('<<UpdateSecondaryProgressText>>', lambda e : this.setProgressText(e, 'secondary'))

    def removeProgressEvents(this):
        this.event_delete('<<UpdatePrimaryProgress>>')
        this.event_delete('<<UpdateSecondaryProgres>>')
        this.event_delete('<<ResetPrimaryProgress>>')
        this.event_delete('<<ResetSecondaryProgress>>')
        this.event_delete('<<UpdatePrimaryProgressText>>')
        this.event_delete('<<UpdateSecondaryProgressText>>')

    def addProgress(this, event, bar = 'primary'):
        if not this.stop.is_set():
            this.progress[bar]['progress'].set(this.progress[bar]['progress'].get() + 1)

    def resetProgress(this, event, bar = 'primary'):
        if not this.stop.is_set():
            this.progress[bar]['progress'].set(0)

    def setProgressText(this, event, bar = 'primary'):
        if not this.stop.is_set():
            this.progress[bar]['text_var'].set(f"{this.progress[bar]['event']} ({this.progress[bar]['progress'].get()}/{this.progress[bar]['bar']['max']}) {this.progress[bar]['text']}")

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
        this.pages['structure']['contents']['columns'] = ['file']
        this.pages['structure']['contents']['treeview'] : ttk.Treeview = ttk.Treeview(this.pages['structure']['frame'], show='tree headings', columns = this.pages['structure']['contents']['columns'])
        this.pages['structure']['contents']['treeview'].pack(fill='both', expand=True)

        this.pages['structure']['contents']['scrollbar'] = ttk.Scrollbar(this.pages['structure']['contents']['treeview'], orient='vertical', command=this.pages['structure']['contents']['treeview'].yview)

        this.pages['structure']['contents']['treeview'].config(yscrollcommand=this.pages['structure']['contents']['scrollbar'].set)
        this.pages['structure']['contents']['scrollbar'].pack(fill='y', side='right')

        columnWidth = 1

        this.pages['structure']['contents']['treeview'].heading('file', text='Filename', anchor='w')
        this.pages['structure']['contents']['treeview'].column('file', width=columnWidth)

        def showPopup(event):
            item = this.pages['structure']['contents']['treeview'].identify_row(event.y)
            logger.info(f'clicked item: {item}')

            this.pages['structure']['contents']['popup'] = tk.Menu(this.pages['structure']['contents']['treeview'], tearoff=0)
            this.pages['structure']['contents']['popup'].add_command(label = 'export', command = lambda : this.exportFile(this.pages['structure']['contents']['treeview'].item(item)['value']))

            try:
                this.pages['structure']['contents']['popup'].tk_popup(event.x_root, event.y_root, 0)
            finally:
                this.pages['structure']['contents']['popup'].grab_release()

        this.pages['structure']['contents']['treeview'].bind("<Button-3>", showPopup)

    def createEnvPage(this):
        this.pages['env']['contents']['treeview'] : ttk.Treeview = ttk.Treeview(this.pages['env']['frame'], show='tree')
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
        logger.info('updating environment')
        this.pages['env']['contents']['treeview'].delete(*this.pages['env']['contents']['treeview'].get_children())
        this.progress['primary']['bar']['max'] = len(this.environment.cabs)
        this.progress['primary']['event'] = "Updating environment"
        this.event_generate('<<ResetPrimaryProgress>>')

        for cab in this.environment.cabs:
            if this.stop.is_set():
                return

            this.progress['primary']['text'] = "{cab}"
            this.event_generate('<<UpdatePrimaryProgress>>')
            # this.event_generate('<<UpdatePrimaryProgressText>>')

            this.pages['env']['contents']['treeview'].insert('', 'end', text=cab)


    def updateAssets(this):
        logger.info('Updating assets')
        this.pages['assets']['contents']['treeview'].delete(*this.pages['assets']['contents']['treeview'].get_children())
        this.progress['primary']['bar']['max'] = len(this.assets)
        this.progress['primary']['event'] = "Updating assets"
        this.event_generate('<<ResetPrimaryProgress>>')

        for asset in this.assets:
            if this.stop.is_set():
                return
            this.progress['primary']['text'] = ""
            this.event_generate('<<UpdatePrimaryProgress>>')
            # this.event_generate('<<UpdatePrimaryProgressText>>')

        #   ['name', 'container', 'type', 'pathID', 'size']
            if isinstance(asset, WWiseAudio):
                values = [asset.container, asset.container, 'WWise_Audio', 0, asset.FileSize]
            else:
                values = [asset.name, asset.container, asset.type.name, asset.path_id, '']

            this.pages['assets']['contents']['treeview'].insert('', 'end', values=values)

    def updateStructure(this):
        logger.info('Updating file stucture')
        this.pages['structure']['contents']['treeview'].delete(*this.pages['structure']['contents']['treeview'].get_children())
        this.progress['primary']['bar']['max'] = this.fileStructureLength
        this.progress['primary']['event'] = "Updating filesystem"
        this.event_generate('<<ResetPrimaryProgress>>')


        def addToStructure(data : dict, id = ''):
            for d in data:
                if this.stop.is_set():
                    return
                this.progress['primary']['text'] = f"{d}"

                this.event_generate('<<UpdatePrimaryProgress>>')
                # this.event_generate('<<UpdatePrimaryProgressText>>')

                if hasattr(data[d], 'filename'):
                    filename = data[d].filename
                else:
                    filename = ''

                newID = this.pages['structure']['contents']['treeview'].insert(
                    id,
                    'end',
                    text=d,
                    values = filename,
                )
                if isinstance(data[d], dict):
                    addToStructure(data[d], newID)
                logger.debug(f'{data[d] = }\n{newID = }')

        logger.debug(this.fileStructure)
        addToStructure(this.fileStructure)

    def chooseFile(this):
        file = filedialog.askopenfilename(title='Choose File', defaultextension='*.*', filetypes=((('any', '*.*'), ('WWise audio', '*.pck'), )))
        return file

    def chooseCatalog(this):
        file = filedialog.askopenfilename(
            title='Choose Catalog',
            defaultextension='*.csv',
            filetypes=((('Catalog file', '*.csv'), ('any', '*.*'), )),
            initialdir = os.path.dirname(this.settings.get('catalog')),
        )
        this.loadCatalog(file)
        return file

    def chooseFolder(this):
        folder = filedialog.askdirectory(title='Pick Folder')
        return folder

    def loadFolder(this):
        folder = this.chooseFolder()
        if folder:
            this.nabe = folder
            thread = threading.Thread(target=this.loadNabe)
            this.threads.add(thread)
            thread.start()

    def loadNabe(this):
        start = time.time()

        thread = threading.current_thread()
        # messagebox.showinfo('Start loading', 'Start loading nabe')

        this.assets = []
        this.fileStructure = {}
        this.environment = UnityPy.Environment()

        # logger.info(this.catalog)

        this.progress['primary']['bar']['max'] = len(this.catalog)
        this.progress['primary']['event'] = "Loading nabe"
        this.event_generate('<<ResetPrimaryProgress>>')


        for key,state,type,path in this.catalog:
            nabepath = pathlib.Path(path)
            parts = nabepath.parts[2:]
            nabepath = pathlib.Path(this.nabe, *parts)
            nabepath = nabepath.as_posix()

            # logger.debug(f'after nabepath {this.stop = }')
            if not this.stop.is_set():
                this.progress['primary']['text'] = f"{os.path.basename(key)}"
                this.event_generate('<<UpdatePrimaryProgress>>')
                # this.event_generate('<<UpdatePrimaryProgressText>>')
            else:
                logger.debug(f'{this.stop = }')
                break

            # this.update()

            # try:
            # logger.info(nabepath)
            this.loadFile(nabepath, container=key)
            logger.info('loaded file')
            logger.debug(f'{this.stop = }')
            print(f'{this.stop = }')
            # except Exception as e:
            #     logger.warning(f'unable to load file {nabepath}')
            #     logger.error(str(e))

        logger.debug(f'after loop {this.stop = }')

        if not this.stop.is_set():

            this.assets = this.assets + this.environment.objects
            this.fileStructureLength = 0

            # messagebox.showinfo('Loading complete', 'Loading complete. Now starting updating gui.')

            this.progress['primary']['bar']['max'] = len(this.assets)
            this.progress['primary']['event'] = "creating filesystem"
            this.event_generate('<<ResetPrimaryProgress>>')

            logger.info('Creating filesystem')
            for asset in this.assets:


                if not this.stop.is_set():
                    this.progress['primary']['text'] = f""
                    this.event_generate('<<UpdatePrimaryProgress>>')
                    # this.event_generate('<<UpdatePrimaryProgressText>>')
                else:
                    logger.debug(f'{this.stop = }')
                    break


                if asset.container:
                    this.fileStructureLength += 1
                    this.addToFilesystem(asset.container, asset)

            if not this.stop.is_set():
                this.progress['primary']['text'] = "Done!"
                this.event_generate('<<UpdatePrimaryProgressText>>')

                logger.debug(f'{this.stop = }')
                this.updateEnv()
                this.updateAssets()

                this.updateStructure()

        this.threads.discard(thread)

        end = time.time()

        logger.info(f'Completed in: {end - start}')

        # return True

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

    def exportFile(this, file):
        logger.debug(file)

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
            logger.info('loading WWise audio')
            asset = WWiseAudio(path, container=container)
            this.assets.append(asset)
        else:
            logger.info('loading Unity asset')
            asset = this.environment.load_file(path)

            def getObjects(item):
                ret = []
                if not isinstance(item, UnityPy.Environment) and getattr(item, "objects", None):
                    # serialized file
                    return [val for val in item.objects.values()]

                elif getattr(item, "files", None):  # WebBundle and BundleFile
                    # bundle
                    for item in item.files.values():
                        ret.extend(getObjects(item))
                    return ret

                return ret

            logger.info(asset)
            objects = getObjects(asset)
            logger.info(f'{objects = }')

            for obj in objects:
                obj.filename = os.path.basename(path)

            logger.info('loaded Unity asset')
            # env = UnityPy.load(path)
            # this.assets = this.assets + env.objects

        this.files.append(path)

        # this.assets = objects

        # logger.info(this.files)
        # logger.info(this.assets)

    def extractAudio(this):
        thread = threading.current_thread()

        DEBUG_STEP = 0

        this.progress['primary']['bar']['max'] = len(this.catalog)

        this.event_generate('<<ResetPrimaryProgress>>')
        this.progress['primary']['event'] = 'Extracting audio'
        # this.event_generate('<<UpdatePrimaryProgressText>>')

        files = os.listdir(os.path.join(this.nabe, 'b'))

        if DEBUG_STEP == 0:
            for key,state,type,path in this.catalog:
                try:
                    files.remove(os.path.basename(path))
                except:
                    pass

                nabepath = pathlib.Path(path)
                parts = nabepath.parts[-2:]
                nabepath = pathlib.Path(this.nabe, *parts)
                nabepath = nabepath.as_posix()

                # this.event_generate('<<UpdatePrimaryProgressText>>')
                # this.progress['primary']['progress'].set(this.progress['primary']['progress'].get() + 1)

                # this.update()

                if parts and parts[0] == 'b':

                    file = os.path.basename(key)
                    name, type = os.path.splitext(file)
                    type = type[1:]

                    if type == 'pck':

                        logger.info(f'exporting {file}')

                        pckdestination = os.path.join(this.output, 'PCK', file)
                        os.makedirs(os.path.dirname(pckdestination), exist_ok=True)
                        try:
                            shutil.copy(nabepath, pckdestination)
                        except Exception as e:
                            logger.exception(f'unable to copy file {nabepath}')

                        try:
                            destination = os.path.join(this.output, 'WAV', name)
                            object = WWiseAudio(nabepath)
                            this.progress['secondary']['bar']['max'] = len(object.files)
                            this.progress['secondary']['progress'].set(0)
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
                            logger.exception(f'unable to load WWise audio {nabepath}')

                        try:
                            if len(os.listdir(destination)) <= 0:
                                shutil.rmtree(destination, ignore_errors=True)
                        except:
                            pass

                    elif type == 'bytes':
                        destination = os.path.join(this.output, 'PCK', file)
                        os.makedirs(os.path.dirname(destination), exist_ok=True)
                        try:
                            shutil.copy(nabepath, destination)
                        except:
                            pass

                this.progress['secondary']['text_var'].set('Done!')

                if not this.stop.is_set():
                    this.progress['primary']['text'] = os.path.basename(key)
                    this.event_generate('<<UpdatePrimaryProgress>>')
                else:
                    logger.debug(f'{this.stop = }')
                    break

            DEBUG_STEP += 1

        if DEBUG_STEP == 1:
            if not this.stop.is_set():
                this.progress['primary']['bar']['max'] = len(files)
                this.event_generate('<<ResetPrimaryProgress>>')

                logger.info(f'UNKNOWN: \n{files}')
                for file in files:
                    pckdestination = os.path.join(this.output, 'UNKNOWN', file)
                    nabepath = os.path.join(this.nabe, 'b', file)
                    os.makedirs(os.path.dirname(pckdestination), exist_ok=True)

                    try:
                        shutil.copy(nabepath, pckdestination)
                    except Exception as e:
                        logger.exception(f'unable to copy file {nabepath}')

                    try:
                        object = WWiseAudio(nabepath)
                        # this.progress['secondary']['bar']['max'] = len(object.files)
                        # this.progress['secondary']['progress'].set(0)
                        destination = os.path.join(this.output, 'UNKNOWN_EXTRACTED', file)
                        os.makedirs(destination, exist_ok=True)
                        object.extractAudio(destination)

                    except Exception as e:
                        logger.exception(f'unable to load WWise audio {nabepath}')

                    try:
                        if len(os.listdir(destination)) <= 0:
                            shutil.rmtree(destination, ignore_errors=True)
                            shutil.rmtree(pckdestination, ignore_errors=True)
                    except:
                        pass

                    if not this.stop.is_set():
                        this.progress['primary']['text'] = os.path.basename(key)
                        this.event_generate('<<UpdatePrimaryProgress>>')
                    else:
                        logger.debug(f'{this.stop = }')
                        break

                this.progress['primary']['text_var'].set('Done!')

            if len(os.listdir(os.path.join(this.output, 'UNKNOWN'))) <= 0:
                shutil.rmtree(os.path.join(this.output, 'UNKNOWN'), ignore_errors=True)
                shutil.rmtree(os.path.join(this.output, 'UNKNOWN_EXTRACTED'), ignore_errors=True)

            DEBUG_STEP += 1

        logger.info('Done! extracting')

        if DEBUG_STEP == 2:
            output_archive = filedialog.asksaveasfilename(
                defaultextension = '.7z',
                filetypes = (
                    ('*.7z', '7zip file'),
                    ('*.*', 'any'),
                ),
                title = 'output archive',
            )

            if not output_archive in ['', None]:
                this.make7ZipFile(
                    output_archive,
                    this.output,
                )

        this.threads.discard(thread)

    def extractNabeAudio(this):
        this.nabe = filedialog.askdirectory(title='choose nabe')
        if not this.nabe:
            return
        this.output = filedialog.askdirectory(title='choose output folder')
        if not this.output:
            return

        thread = threading.Thread(target=this.extractAudio)
        this.threads.add(thread)
        thread.start()

    def make7ZipFile(this, filename : str, folder : str):
        folder : pathlib.Path = pathlib.Path(folder)

        if not folder.exists():
            raise FileNotFoundError(f'path "{folder.as_posix()}" not found')
        if not folder.is_dir():
            raise NotADirectoryError(f'path "{folder.as_posix()}" is not a directory')

        folder = folder.absolute().as_posix()

        logger.info(f'destination: {folder}')

        tmp = tempfile.mkstemp(suffix = os.path.splitext(filename)[1])
        os.close(tmp[0])

        logger.info(f'temp file: {tmp[1]}')

        tmp_7zip_file = py7zr.SevenZipFile(tmp[1], 'w')

        for dir, subdir, files in os.walk(folder):
            for file in files:
                relpath = pathlib.Path(os.path.relpath(os.path.join(dir, file), folder)).as_posix()
                # print(path)

                tmp_7zip_file.write(os.path.join(dir, file), relpath)

        tmp_7zip_file.close()

        raw_data = b''

        with open(tmp[1], 'r') as file:
            raw_data = file.read()

        with open(filename, 'w') as file:
            file.write(raw_data)

        if os.path.exists(tmp[1]):
            os.remove(tmp[1])

        return filename

    def setStopState(this, state = False):
        this.stop = state
        return this.stop

    # settings
    def loadSettings(this, **kwargs):
        this.settings = Settings(this.settingsFile, {
            'catalog': 'catalog.csv',
            'RavioliGameTools': {
               'path': 'tools/RavioliGameTools_v2.10'
            },
            'internetarchive': {
                's3': {
                    'access': '',
                    'secret': '',
                },
                'identifier': '',
            }
        })

    def loadCatalog(this, path = None):
        if path:
            this.settings.set('catalog', path)
        try:
            this.catalog = loadCSV(this.settings.get('catalog'), delimiter=',', quotechar='"')
        except:
            logger.warning(f'Unable to load catalog: {this.settings.get("catalog")}')

    def close(this):
        logger.info('Safely stopping threads')
        # this.setStopState(True)
        # this.stop = True
        this.stop.set()
        # this.waitThreads()
        # this.removeProgressEvents()

        # time.sleep(1)

        logger.info('Safely stopped')

        this.destroy()

    def waitThreads(this):

        for thread in this.threads:
            if thread.is_alive():
                thread.join()

        # over_threads = iter(threading.enumerate())
        # curr_th = next(over_threads)
        # while True:
        #     if curr_th.daemon:
        #         continue
        #     try:
        #         curr_th.join()
        #     except RuntimeError as err:
        #         if 'cannot join current thread' in err.args[0]:
        #             # catchs main thread
        #             try:
        #                 curr_th = next(over_threads)
        #             except StopIteration:
        #                 break
        #         else:
        #             raise

        #     if curr_th.is_alive():
        #         continue
        #     try:
        #         curr_th = next(over_threads)
        #     except StopIteration:
        #         break

        # for thread in threading.enumerate():
        #     if thread.daemon:
        #         continue
        #     try:
        #         thread.join()
        #     except RuntimeError as err:
        #         if 'cannot join current thread' in err.args[0]:
        #             # catchs main thread
        #             continue
        #         else:
        #             raise

        return True


def main():
    COUNT = threading.active_count()
    THREAD_LIMIT = COUNT + 7

    global app
    app = Window()
    app.mainloop()
    print('mainloop ended')
    while threading.active_count() > COUNT: #simulate join
        time.sleep(0.1)
        print(threading.active_count())
    print('all threads ended, mainthread ends now')

if __name__ == '__main__':
    createLogger('file')
    main()
