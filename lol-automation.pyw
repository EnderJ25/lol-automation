import os, sys, time, threading, asyncio, PIL, pystray, logging, webbrowser, configparser
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
    app.exit()

class autoChatFrame(tk.LabelFrame):
    def __init__(self, parent):
        # Initialize Frame widget
        super().__init__(parent, text="Automensajes: Carril")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(7, weight=1)

        # Role selection variable and widgets
        self.role = tk.IntVar()
        self.hiddenOnly = tk.BooleanVar()
        tk.Radiobutton(self, text="Ninguno", variable=self.role, value=0).grid(column=0, row=0, sticky="w")
        tk.Radiobutton(self, text="Superior", variable=self.role, value=1).grid(column=0, row=1, sticky="w")
        tk.Radiobutton(self, text="Jungla", variable=self.role, value=2).grid(column=0, row=2, sticky="w")
        tk.Radiobutton(self, text="Medio", variable=self.role, value=3).grid(column=0, row=3, sticky="w")
        tk.Radiobutton(self, text="Inferior", variable=self.role, value=4).grid(column=0, row=4, sticky="w")
        tk.Radiobutton(self, text="Soporte", variable=self.role, value=5).grid(column=0, row=5, sticky="w")
        tk.Checkbutton(self, text="Solo en ocultas", variable=self.hiddenOnly).grid(column=0, row=6, sticky="w")

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
        
class pingWidget(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title('Ping')
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", lambda: app.togglePing(True))
        #self.overrideredirect(True)
        #self.attributes('-topmost', True)
        self.attributes('-toolwindow', True)
        self.columnconfigure(0, weight=2)
        self.rowconfigure(0, weight=1)
        self.row_count=0
        self.entries=[]

    def add(self, name):
        tk.Label(self, text=name, anchor=tk.W).grid(column=0, row=self.row_count, sticky='nsew', ipadx=10)
        self.entries.append(tk.Label(self, text="...", anchor=tk.E))
        self.entries[len(self.entries)-1].grid(column=1, row=self.row_count, sticky='e')
        self.row_count+=1

class App(tk.Tk):
    def __init__(self):
        ##
        ## Initialize
        ##
        super().__init__()
        ## Setting up Initial Things
        self.title("League of Legends Automation")
        self.geometry("600x236")
        self.resizable(True, True)
        self.iconphoto(False, tk.PhotoImage(file= app_path + "\\assets\\icon.png"))
        self.columnconfigure(0, weight=4)
        self.rowconfigure(0, weight=1)

        ### Variables
        self.icon_running = False
        self.ping = None
        
        ## Menu Bar
        menubar = tk.Menu(self , bd=3, relief=RAISED, activebackground="#80B9DC")

        ## Filemenu
        filemenu = Menu(menubar, tearoff=0, relief=RAISED, activebackground="#026AA9")
        menubar.add_cascade(label="Archivo", menu=filemenu)
        filemenu.add_command(label="Cargar configuración", command=configuration)
        filemenu.add_command(label="Guardar configuración", command=lambda: configuration(True))
        filemenu.add_separator()
        filemenu.add_command(label="Minimizar a la bandeja", command=self.toTray)  
        filemenu.add_separator()
        filemenu.add_command(label="Salir", command=closeApp)  

        ## functions menu
        functions_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Opciones", menu=functions_menu)
        functions_menu.add_command(label="Mensajes automáticos")
        functions_menu.add_separator()
        self.pingEnabled = tk.BooleanVar()
        functions_menu.add_checkbutton(label="Habilitar ping", onvalue=1, offvalue=0, variable=self.pingEnabled, command=self.togglePing)
        functions_menu.add_separator()
        self.enableTray = tk.BooleanVar()
        self.minTray = tk.BooleanVar()
        self.closeTray = tk.BooleanVar()
        functions_menu.add_checkbutton(label="Habilitar icono en la bandeja", onvalue=1, offvalue=0, variable=self.enableTray, command=self.toggleTray)
        functions_menu.add_checkbutton(label="Minimizar la bandeja", onvalue=1, offvalue=0, variable=self.minTray, command=self.tMinTray)
        functions_menu.add_checkbutton(label="Cerrar a la bandeja", onvalue=1, offvalue=0, variable=self.closeTray, command=self.tCloseTray)
        
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
        st.grid(column=0, columnspan=3, row=0, sticky='nsew')

        # Create textLogger
        text_handler = TextHandler(st)

        # Logging configuration
        logging.basicConfig(filename= "lol-automation.log",
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s')        

        # Add the handler to logger
        logger = logging.getLogger()        
        logger.addHandler(text_handler)

        self.autoChat = autoChatFrame(self)
        self.autoChat.grid(column=3, columnspan=1, row=0, sticky='new')
        
        
        ## Status bar
        self.status = tk.Label(self, text="…", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.grid(column=0, columnspan=4, row=1, sticky='nsew')

        # Create system tray icon
        image=PIL.Image.open(app_path + "\\assets\\icon.ico")
        menu=(pystray.MenuItem('Mostrar', self.unTray, default=True), pystray.MenuItem('Salir', closeApp))
        self.icon=pystray.Icon(name="lol-automation", icon=image, title="LOL Automation", menu=menu)
        self.icon.run_detached()

    ### Functions

    ## General
    def exit(self):
        if self.icon._running: self.icon.stop()
        self.destroy()

    ## Ping
    def togglePing(self, invert=False):
        if invert: self.pingEnabled.set(not self.pingEnabled.get())
        if self.pingEnabled.get():
            self.ping = pingWidget(self)
            for target in pingTargets:
                self.ping.add(pingTargets[target][0])
        else:
            if app.ping.winfo_exists(): self.ping.destroy()

    ## Tray icon
    def toggleTray(self):
        if self.enableTray.get():
            self.icon.visible = True
        else:
            self.icon.visible = False

    def toTray(self, *args):
        if not self.icon.visible: self.icon.visible = True
        self.withdraw()

    def unTray(self, icon, item):
        if not self.enableTray.get(): self.icon.visible = False
        self.deiconify()

    def tMinTray(self):
        if self.minTray.get():
            self.bind("<Unmap>", self.toTray)
        else:
            self.unbind("<Unmap>")

    def tCloseTray(self):
        if self.closeTray.get():
            self.protocol("WM_DELETE_WINDOW", self.toTray)
        else:
            self.protocol("WM_DELETE_WINDOW", closeApp)

    def notify(self, msg):
        if not self.focus_displayof() and self.icon.visible and self.icon._running: self.icon.notify(msg)

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
        app.toggleTray(); app.tMinTray(); app.tCloseTray()
        ## Timers
        Lapse1 = config.getfloat("timers", "Lapse1", fallback=1)
        Lapse2 = config.getfloat("timers", "Lapse2", fallback=0.5)
        Lapse = Lapse1
        ## pingTargets
        # Reset ping targets dictionary and fill from ini file
        pingTargets = {}
        if config.has_section("pingTargets"):
            for i in config["pingTargets"]:
                pingTargets[i] = eval(config["pingTargets"][i])
        else:
            pingTargets = {1:["Google", "www.google.com"]}
        ## Ping
        pingLapse = config.getfloat("ping", "pingLapse", fallback=1)
        app.pingEnabled.set(config.getboolean("ping", "pingEnabled", fallback=False))
        if app.pingEnabled.get(): app.togglePing()
        ## Successfully config read
        logging.info("Configuración cargada.")

def checkLeague():
    global leagueDetected, exitScript
    if not leagueDetected:
        status("Inicializando...")
        logging.info("Detectando Cliente de League of Legends... ")
        while True:
            if exitScript: return
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
                    logging.info("Partida aceptada!"); app.notify("Partida aceptada!")
                    state=stat
            elif stat == "ChampSelect":
                if state != stat:
                    status("Selección de campeón...")
                    state=stat
                    autoChat(app.autoChat.role.get(), app.autoChat.hiddenOnly.get())
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
        #except Exception as err:
            #logging.error("Error desconocido: " + str(type(err)) + " - " + str(err) + "\n")
            #state="error"
            
        time.sleep(Lapse)

def pingThread():
    #occurs=0
    while True:
        if exitScript: return
        if app.pingEnabled.get() and app.ping.winfo_exists():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tasks=[]
            #occurs+=1
            for target in pingTargets:
                tasks.append(asyncio.ensure_future(ping(pingTargets[target][1])))
            loop.run_until_complete(asyncio.gather(*tasks))
            try:
                for target in pingTargets:
                    result= tasks[int(target)-1].result()
                    color = "red"
                    if type(result) == int:
                        if result <= 20:
                            color = "blue"
                        elif result <= 200:
                            color = "green"
                        elif result <= 500:
                            pingColor = "yellow"
                        result = str(result) + "ms"
                    app.ping.entries[int(target)-1].config(text=result, fg=color)
            except Exception:
                pass
        time.sleep(pingLapse)
    
if __name__ == '__main__':
    global app
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app 
        # path into variable _MEIPASS'.
        app_path = sys._MEIPASS
    else:
        app_path = os.path.dirname(os.path.abspath(__file__))
        
    app = App()
    p1 = threading.Thread(target=main)
    p2 = threading.Thread(target=pingThread)  #(target=lambda: asyncio.run(pingThread()))
    logging.info("Directorio de trabajo: " + app_path)
    logging.info("Archivo de configuración: " + inifile)
    configuration()
    p1.start(); p2.start()
    status("Inicializando...")
    app.mainloop()
    if p1.is_alive(): p1.join()
    if p2.is_alive():
        print("Ping is still alive")
        p2.join()
