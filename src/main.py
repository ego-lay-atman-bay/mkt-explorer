import os

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog

class Window(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title('')
        self.geometry('%dx%d' % (760 , 610) )

        self.initialize()

    def initialize(self):
        pass

def main():
    app = Window()
    app.mainloop()

if __name__ == '__main__':
    main()