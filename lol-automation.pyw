import os, sys, time, threading, PIL, pystray, logging, webbrowser, configparser
import json
from localfunctions import *
from lcu_api import *
from ping3 import ping as ping3
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import *
import tkinter.scrolledtext as ScrolledText

lockfile = 'C:\\Riot Games\\League of Legends\\lockfile'
inifile = os.path.dirname(sys.argv[0]) + '\\lol-automation.ini'

leagueDetected=False
exitScript=False
apiTimeout=10

state="none"

status = lambda msg: app.status.config(text = msg)

def closeApp():
    global exitScript
    exitScript=True
    app.destroy()

def toTray():
   app.withdraw()
   image=PIL.Image.open("lol-automation.ico")
   menu=(pystray.MenuItem('Mostrar', unTray, default=True), pystray.MenuItem('Salir', closeApp))#, pystray.MenuItem('XD', lambda icon, item: icon.notify('Hello World!')))
   icon=pystray.Icon(name="lol-automation", icon=image, title="LOL Automation", menu=menu)
   icon.run_detached()

def unTray(icon, item):
   icon.stop()
   app.deiconify()

class TextHandler(logging.Handler):
    # This class allows you to log to a ScrolledText widget
    def __init__(self, text):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        self.setLevel(logging.DEBUG)
        self.text = text
        self.text.config(state='disabled')
        self.text.tag_config("INFO", foreground="black")
        self.text.tag_config("DEBUG", foreground="grey")
        self.text.tag_config("WARNING", foreground="orange")
        self.text.tag_config("ERROR", foreground="red")
        self.text.tag_config("CRITICAL", foreground="red", underline=1)

        #self.red = self.text.tag_configure("red", foreground="red")
        # Store a reference to the Text it will log to
        self.text = text

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text.configure(state='normal')
            self.text.insert(tk.END, msg + '\n', record.levelname)
            self.text.configure(state='disabled')
            # Autoscroll to the bottom
            self.text.yview(tk.END)
        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        ## Setting up Initial Things
        self.title("League of Legends Automation")
        self.geometry("600x200")
        self.resizable(True, True)
        #self.overrideredirect(True)
        self.iconphoto(False, tk.PhotoImage(file="lol-automation.png"))
        self.protocol("WM_DELETE_WINDOW", closeApp) ## Handle Close event from WM
        #self.attributes('-topmost', True)

        self.columnconfigure(0, weight=2)
        self.rowconfigure(0, weight=1)
        
        ## Menu Bar
        menubar = tk.Menu(self , bd=3, relief=RAISED, activebackground="#80B9DC")

        ## Filemenu
        filemenu = Menu(menubar, tearoff=0, relief=RAISED, activebackground="#026AA9")
        menubar.add_cascade(label="Archivo", menu=filemenu)
        filemenu.add_command(label="Cargar configuración", command=configuration)
        filemenu.add_command(label="Guardar configuración", command=lambda: configuration(True))
        filemenu.add_separator()
        filemenu.add_command(label="Minimizar a la bandeja", command=toTray)  
        filemenu.add_separator()
        filemenu.add_command(label="Salir", command=closeApp)  

        ## functions menu
        functions_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Opciones", menu=functions_menu)
        functions_menu.add_command(label="Mensajes automáticos")
        functions_menu.add_separator()
        self.pingEnabled = tk.BooleanVar()
        functions_menu.add_checkbutton(label="Habilitar ping", onvalue=1, offvalue=0, variable=self.pingEnabled)
        functions_menu.add_separator()
        self.enableTray = tk.BooleanVar()
        self.minTray = tk.BooleanVar()
        self.closeTray = tk.BooleanVar()
        functions_menu.add_checkbutton(label="Habilitar icono en la bandeja", onvalue=1, offvalue=0, variable=self.enableTray)
        functions_menu.add_checkbutton(label="Minimizar la bandeja", onvalue=1, offvalue=0, variable=self.minTray)
        functions_menu.add_checkbutton(label="Cerrar a la bandeja", onvalue=1, offvalue=0, variable=self.closeTray)
        
        ## help menu
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        help_menu.add_command(label="EnderJ25 en GitHub", command=lambda: webbrowser.open("https://github.com/EnderJ25"))
        help_menu.add_separator()
        help_menu.add_command(label="Acerca de", command=lambda: webbrowser.open("https://github.com/EnderJ25/lol-automation\#readme"))

        self.configure(menu=menubar)

        # Add text widget to display logging info
        st = ScrolledText.ScrolledText(self, state='disabled')
        st.configure(font='TkFixedFont')
        st.pack(expand=True)
        st.grid(column=0, row=0, sticky='nsew')

        # Create textLogger
        text_handler = TextHandler(st)

        # Logging configuration
        logging.basicConfig(filename='lol-automation.log',
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s')        

        # Add the handler to logger
        logger = logging.getLogger()        
        logger.addHandler(text_handler)

        self.status = tk.Label(self, text="…", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.grid(column=0, row=1, sticky='nsew')

#####==============================================================#####
##### Configuration function. Using "inifile" as ini path variable #####
#####==============================================================#####
def configuration(write=False):
    ## Declare global variables
    global config, pingTargets, pingLapse, pingEnabled, Lapse1, Lapse2, Lapse, logErr_enabled
    ## Declare config parser module class variable
    config = configparser.ConfigParser()
    if write:
    ## Write mode. get actual values and write to ini file
        ### Config sections ###
        ## General
        config["general"] = {"logErrors": logErr_enabled}
        ## System tray
        config["tray"] = {"enableTray": app.enableTray.get(), "minTray": app.minTray.get(), "closeTray": app.closeTray.get()}
        ## Timers
        config["timers"] = {"Lapse1": Lapse1, "Lapse2": Lapse2}
        ## Ping 
        config["ping"] = {"pingEnabled": app.pingEnabled.get(), "pingLapse": pingLapse}
        try:
            config['pingTargets'] = pingTargets
        except:
            logging.error("Error de configuración. Restableciendo...")
            try:
                os.remove(inifile)
            except:
                pass
            configuration()
            return
        #### Write to ini file ####
        with open(inifile, 'w') as configfile:
            config.write(configfile)
        ## Successfully config write
        logging.info("Configuración guardada.")
    else:
    ## Read mode. get values from ini file and return fallback values if not found
        #### Read from ini file ####
        try:
            config.read(inifile)
        except:
            logging.error("Error de configuración. Restableciendo...")
            try:
                os.remove(inifile)
            except:
                pass
            configuration(True)
            return
        ### Config sections ###
        ## General
        logErr_enabled = config.getboolean("general", "logErrors", fallback=True)
        ## System tray
        app.enableTray.set(config.getboolean("tray", "enableTray", fallback=True))
        app.minTray.set(config.getboolean("tray", "minTray", fallback=True))
        app.closeTray.set(config.getboolean("tray", "closeTray", fallback=True))
        ## Timers
        Lapse1 = config.getfloat("timers", "Lapse1", fallback=1)
        Lapse2 = config.getfloat("timers", "Lapse2", fallback=0.5)
        Lapse = Lapse1
        ## Ping
        pingLapse = config.getfloat("ping", "pingLapse", fallback=1)
        app.pingEnabled.set(config.getboolean("ping", "pingEnabled", fallback=False))
        ## pingTargets
        # Reset ping targets dictionary and fill from ini file
        pingTargets = {}
        if config.has_section("pingTargets"):
            for i in config["pingTargets"]:
                pingTargets[i] = eval(config["pingTargets"][i])
        else:
            pingTargets = {1:["Google", "www.google.com"]}
        ## Successfully config read
        logging.info("Configuración cargada.")

def checkLeague():
    global leagueDetected, exitScript
    if not leagueDetected:
        status("Inicializando...")
        logging.info("Detectando Cliente de League of Legends... ")
        while True:
            if checkProcess("LeagueClient.exe"):
                logging.info("Cliente de League of Legends detectado.")
                logging.info("Conectando a la API...")
                init_lcu(lockfile, apiTimeout)
                while True:
                    try:
                        gameFlow()
                        logging.info("Conectado!")
                        break
                    except:
                        time.sleep(0.5)
                status("Inicializado")
                leagueDetected=True
                return False
            time.sleep(3)
    elif not checkProcess("LeagueClient.exe"):
        logging.info("Cliente cerrado.")
        closeApp()

def main():
    global Lapse, state, exitScript
    while True:
        try:
            checkLeague()
            if exitScript: return
            stat = gameFlow()
        
            if stat == "None" and state != stat:
                status("Esperando entrar a una sala...")
                state=stat
            elif stat == "Lobby" and state != stat:
                status("En sala.")
                state=stat
            elif stat == "CheckedIntoTournament" and state != stat:
                status("Confirmado en Clash.")
                state=stat
            elif stat == "Matchmaking" and state != stat:
                status("Buscando partida...")
                state=stat
            elif stat == "ReadyCheck" and state != stat:
                if acceptMatch():
                    logging.info("Partida aceptada!")
                    state=stat
            elif stat == "ChampSelect":
                getChampSelect()
                if state != stat:
                    status("Selección de campeón...")
                    state=stat
                    sendChat("XD")
            elif stat == "InProgress" and state != stat:
                status("Partida en progreso...")
                state=stat
            elif stat == "Reconnect" and state != stat:
                status("Desconectado de la partida.")
                state=stat
            elif stat == "WaitingForStats" and state != stat:
                status("Esperando estadísticas...")
                state=stat
            elif stat == "PreEndOfGame" and state != stat:
                status("Finalizando partida...")
                state=stat
            elif stat == "EndOfGame" and state != stat:
                status("Partida finalizada.")
                state=stat
            elif status != stat:
                pass
            
        except ConnectionError as err:
            logging.error("Error conectando a la API: " + str(err) + "\n")
            state="error"
        except ConnectionRefusedError as err:
            logging.error("Error conectando a la API. Conexión rechazada: " + str(err) + "\n")
            state="error"
        except AttributeError as err:
            logging.error("Error de atributos: " + str(err) + "\n")
            state="error"
        except ConnectionTimeoutError as err:
            logging.error("Tiempo de espera de conexión agotado: " + str(err) + "\n")
            state="error"
        except Exception as err:
            logging.error("Error desconocido: " + str(type(err)) + " - " + str(err) + "\n")
            state="error"
            
        time.sleep(Lapse)

def asyncPing():
    while True:
        if exitScript: return
        if pingEnabled:
            pingTable = Table.grid(expand=True)
            pingTable.add_column(justify="left", no_wrap=True)
            pingTable.add_column(justify="right", no_wrap=True)
            for target in pingTargets:
                pingTable.add_row(Text(pingTargets[target][0], style="bright_white"), ping(pingTargets[target][1]))
            l["main"]["side"]["ping"].update(Panel(pingTable, title="Ping", style="blue"))
        time.sleep(pingLapse)
    
if __name__ == '__main__':
    app = App()
    logging.info("Archivo de configuración: " + inifile)
    configuration()
    p1 = threading.Thread(target=main)
    p2 = threading.Thread(target=asyncPing)
    p1.start() #;p2.start()
    status("Inicializando...")
    app.mainloop()
    #p1.join() #;p2.join()
