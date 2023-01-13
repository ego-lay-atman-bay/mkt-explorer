import os

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog

class Window(tk.Tk):
    def __init__(this, *args, **kwargs):
        super().__init__(*args, **kwargs)
        this.title('')
        this.geometry('%dx%d' % (760 , 610) )
        
        this.files = []
        this.assets = []
        this.fileStructure = {}

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
        this.menuBar = tk.Menu(this)
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
        
        
        
def main():
    app = Window()
    app.mainloop()

if __name__ == '__main__':
    main()