import os
import subprocess
import shutil
import json
import csv
import logging
from datetime import datetime
import lxml
from lxml import etree
from pydub import AudioSegment

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
            this._scanFile()
            
            
        def _scanFile(this):
            os.makedirs('tmp/audio', exist_ok=True)
        
            this._scanName = f'tmp/audio/{os.path.splitext(os.path.basename(this.filename))[0]}.xml'
            logging.info(f'Scanning {this.filename}')
            logging.info(f'Result {this._scanName}')
            result = subprocess.run([f"{this.settings['RavioliGameTools']['path']}/RScannerConsole.exe", this.filename, f"/s:{this._scanName}"], capture_output=True, text=True)
                    
            logging.info(result.stdout)
            
            logging.info(f'Contents: \n{etree.tostring(etree.parse(this._scanName).getroot(), pretty_print=True, encoding="utf-8").decode("utf-8")}\n')
            
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
                        results = {
                            'Name': wem.name,
                            'TypeName': wem.typeName,
                            'PerceivedType': wem.PerceivedType,
                            'Offset': wem.offset,
                            'Length': wem.length,
                        }
                        this.scanResults['Entries'].append(results)
                        
                        logging.info(results)
            
        def extractAudio(this, out, format = 'wav', subdir = False):
            format = format.lower()
            if not format in ['wem', 'wav', 'ogg']:
                logging.warning(f'format "{format}" is not supported.\nUsing "wav" format.')
                format = 'wav'
                
            args = [f'/sf:{format}', '/as']
            if subdir:
                args.append('/s')
                
            cmd = [os.path.join(this.settings['RavioliGameTools']['path'], "RExtractorConsole.exe"), this.filename, out] + args
            # logging.debug(cmd)
            result = subprocess.run(cmd, capture_output=True, text=True)
            logging.info(result.stdout)
            
            logging.info('Done!')
            
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
                this.raw_wav = None
                this._wavPath = None
                this.ogg = None
                this.raw_ogg = None
                this._oggPath = None
                
                this.audio = None
                
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
                
                scannerArgs = [f'/e:{outPath}', f'/r:{this.offset}-{str((int(this.offset) + int(this.length)) - 1)}', '/l']
                logging.info(f'{scannerArgs = }')
                
                if this._wemPath == None:
                    shutil.rmtree(outPath, ignore_errors=True)
                    result = subprocess.run([f"{this.settings['RavioliGameTools']['path']}/RScannerConsole.exe", this.filename] + scannerArgs, capture_output=True, text=True)
                    logging.info(result.stdout)
                    
                    files = [i for i in os.listdir(outPath) if i.endswith('wem')]
                    
                    this._wemPath = os.path.abspath(os.path.join(outPath, files[0]))
                    
                    with open(this._wemPath, 'rb') as file:
                        this.wem = file.read()
                
                if format != 'wem':
                    result = subprocess.run([f"{this.settings['RavioliGameTools']['path']}/RExtractorConsole.exe", this._wemPath, outPath] + extracterArgs.split(' '), capture_output=True, text=True)
                    
                    logging.info(result.stdout)
                    
                    files = [i for i in os.listdir(outPath) if i.endswith(format)]
                    
                    if format == 'wav':
                        this._wavPath = os.path.join(outPath, files[0])
                        with open(this._wavPath, 'rb') as file:
                            this.raw_wav = file.read()
                        this.audio = AudioSegment.from_file(this._wavPath, format)
                    elif format == 'ogg':
                        this._oggPath = os.path.join(outPath, files[0])
                        with open(this._oggPath, 'rb') as file:
                            this.raw_ogg = file.read()
                        this.audio = AudioSegment.from_file(this._oggPath, format)
                            
                # logging.info(
                #     this.wem,
                #     this.wav,
                #     this.ogg,
                # )
                
                formats = {
                    'wem': this.wem,
                    'wav': this.raw_wav,
                    'ogg': this.raw_ogg,
                }
                
                return formats[format]
            
            def export(this, path, format = 'wav'):
                format = format.lower()
                if not format in ['wem', 'wav', 'ogg']:
                    logging.warning(f'format "{format}" is not supported.\nUsing "wav" format.')
                    format = 'wav'
                    
                formats = {
                    'wem': this.wem,
                    'wav': this.raw_wav,
                    'ogg': this.raw_ogg,
                }
                
                if formats[format] == None:
                    logging.error(f'Unable to get format "{format}"')
                    return
                
                output = os.path.dirname(path)
                os.makedirs(output, exist_ok=True)
                
                with open(path, 'wb') as file:
                    file.write(formats[format])
                
            
class UnityAsset():
    def __init__(this) -> None:
        pass
    

                