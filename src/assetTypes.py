import os
import subprocess
import shutil
import json
import csv
import logging
from datetime import datetime
import lxml
from lxml import etree

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
        
createLogger()

class WWiseAudio():
        def __init__(this, file, options = None) -> None:
            if options:
                this.settings = options
            else:
                this.settings = {
                    'catalog': 'catalog.csv',
                    'RavioliGameTools': {
                        'path': 'tools/RavioliGameTools_v2.10',
                    },
                }
                
            this.filename = file
            this._extractAudio()
            
            
        def _extractAudio(this):
            os.makedirs('tmp/audio', exist_ok=True)
        
            this._scanName = f'tmp/audio/{os.path.splitext(os.path.basename(this.filename))[0]}.xml'
            subprocess.run([f"{this.settings['RavioliGameTools']['path']}/RScannerConsole.exe", this.filename, f"/s:{this._scanName}"])
            
            this.files = []
            this.scanResults = {
                'FileName': this.filename
            }
            
            with open(this._scanName, encoding='utf_8_sig') as file:
                tree = etree.parse(file)
                root = tree.getroot()
                
            for data in range(len(root)):
                if root[data].tag == 'FileSize':
                    this.FileSize = int(root[data].text)
                    this.scanResults['FileSize'] = this.FileSize
                    
                if root[data].tag == 'LastPosition':
                    this.LastPosition = int(root[data].text)
                    this.scanResults['LastPosition'] = this.LastPosition
                    
                if root[data].tag == 'Entries':
                    this.scanResults['Entries'] = []
                    for entry in range(len(root[data])):
                        wem = this.WEM(this.filename, root[data][entry].get('Name'), root[data][entry].get('Offset'), root[data][entry].get('Length'), this.FileSize, this.settings, root[data][entry].get('TypeName'), root[data][entry].get('PerceivedType'))
                        this.files.append(wem)
                        this.scanResults['Entries'].append({
                            'Name': wem.name,
                            'TypeName': wem.typeName,
                            'PerceivedType': wem.PerceivedType,
                            'Offset': wem.offset,
                            'Length': wem.length,
                        })
            
            
        class WEM():
            def __init__(this, filename, name, _from, to, filesize, options, typeName = 'Wwise Encoded Media', PerceivedType = 'Audio') -> None:
                if options:
                    this.settings = options
                else:
                    this.settings = {
                        'catalog': 'catalog.csv',
                        'RavioliGameTools': {
                        'path': 'tools/RavioliGameTools_v2.10',
                        'args': '/s /as'
                        },
                    }
                    
                this.name = name
                this.filename = filename
                this.offset, this._from = _from, _from
                this.length, this.to = to, to
                this.filesize = filesize
                this.typeName = typeName
                this.PerceivedType, this.type = PerceivedType, PerceivedType
                
                this.wem = None
                this._wemPath = None
                this.wav = None
                this._wavPath = None
                this.ogg = None
                this._oggPath = None
                
            def read(this, format = 'wem'):
                """
                Formats:
                    'wem'
                    'wav'
                    'ogg'
                """
                format = format.lower()
                
                if not format in ['wem', 'wav', 'ogg']:
                    logging.warning(f'format "{format}" is not supported.\nUsing "wem" format.')
                    format = 'wem'
                    
                
                extracterArgs = '/as'
                    
                if format != 'wem':
                    extracterArgs += f' /sf:{format}'
                    
                outPath = f'tmp/audio/{os.path.basename(os.path.splitext(this.filename)[0])}/{os.path.splitext(this.name)[0]}'
                
                scannerArgs = [f'/e:{outPath}', f'/r:{this.offset}-{this.length}']
                
                if this._wemPath == None:
                    this._wemPath = os.path.abspath(os.path.join(outPath, 'File0001.wem'))
                    subprocess.run([f"{this.settings['RavioliGameTools']['path']}/RScannerConsole.exe", this.filename] + scannerArgs)
                    with open(this._wemPath, 'rb') as file:
                        this.wem = file.read()
                
                if format != 'wem':
                    subprocess.run([f"{this.settings['RavioliGameTools']['path']}/RExtractorConsole.exe", this._wemPath, outPath] + extracterArgs.split(' '))
                    
                    if format == 'wav':
                        this._wavPath = os.path.join(outPath, 'File0001.wav')
                        with open(this._wavPath, 'rb') as file:
                            this.wav = file.read()
                    elif format == 'ogg':
                        this._oggPath = os.path.join(outPath, 'File0001.ogg')
                        with open(this._oggPath, 'rb') as file:
                            this.ogg = file.read()
                            
                # logging.info(
                #     this.wem,
                #     this.wav,
                #     this.ogg,
                # )
                
                formats = {
                    'wem': this.wem,
                    'wav': this.wav,
                    'ogg': this.ogg,
                }
                
                return formats[format]
                