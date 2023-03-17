import os, sys, time, threading, logging, webbrowser, psutil, json, league_connection, configparser
from ping3 import ping as ping3
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

class TextHandler(logging.Handler):
    # This class allows you to log to a Tkinter Text or ScrolledText widget
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
        #self.iconphoto(False, tk.PhotoImage(file="assets/title_icon.png"))
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
        help_menu.add_command(label="Acerca de", command=configuration)

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

        
def configuration(write=False):
    global config, pingTargets, pingLapse, pingEnabled, Lapse1, Lapse2, Lapse, logErr_enabled
    config = configparser.ConfigParser()
    if write:
        config["general"] = {"logErrors": logErr_enabled}
        config["ping"] = {"pingEnabled": app.pingEnabled.get(), "pingLapse": pingLapse}
        config["timer"] = {"Lapse1": Lapse1, "Lapse2": Lapse2}
        try:
            config['pingTargets'] = pingTargets
        except:
            logging.info("Error de configuración. Restableciendo...")
            try:
                os.remove(inifile)
            except:
                pass
            configuration()
            return
        with open(inifile, 'w') as configfile:
            config.write(configfile)
        logging.info("Configuración guardada.")
    else:
        pingTargets = {}
        try:
            config.read(inifile)
        except:
            logging.info("Error de configuración. Restableciendo...")
            try:
                os.remove(inifile)
            except:
                pass
            configuration(True)
            return
        logErr_enabled = config.getboolean("general", "logErrors", fallback=True)
        pingLapse = config.getfloat("ping", "pingLapse", fallback=1)
        app.pingEnabled.set(config.getboolean("ping", "pingEnabled", fallback=False))
        Lapse1 = config.getfloat("timer", "Lapse1", fallback=1)
        Lapse = Lapse1
        Lapse2 = config.getfloat("timer", "Lapse2", fallback=0.5)
        if config.has_section("pingTargets"):
            for i in config["pingTargets"]:
                pingTargets[i] = eval(config["pingTargets"][i])
        else:
            pingTargets = {1:["Google", "www.google.com"]}
        logging.info("Configuración cargada.")
            
    
def checkProcess(processName):
    for proc in psutil.process_iter():
        try:
            if processName.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False;

def checkLeague():
    global leagueDetected, api, exitScript
    if not leagueDetected:
        status("Inicializando...")
        logging.info("Detectando Cliente de League of Legends... ")
        while True:
            if checkProcess("LeagueClient.exe"):
                logging.info("Cliente de League of Legends detectado.")
                logging.info("Conectando a la API...")
                api = league_connection.LeagueConnection(lockfile, timeout=apiTimeout)
                while True:
                    try:
                        api.get("/lol-gameflow/v1/gameflow-phase")
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

def ping(host):
    try:
        pingResult = ping3(host, unit='ms', timeout=1)
    except OSError:
        return Text("SysError", style="red")
    if type(pingResult) == float:
        pingColor = "red"
        if int(pingResult) <= 20:
            pingColor = "white"
        elif int(pingResult) <= 200:
            pingColor = "green"
        elif int(pingResult) <= 500:
            pingColor = "yellow"
        return Text(str(int(pingResult)) + "ms", style=pingColor)
    elif type(pingResult) == bool and not pingResult:
        return Text("unreach", style="red")
    elif pingResult == None:
        return Text("timeout", style="red")
    else:
        logErr("Error de ping: " + str(type(pingResult)))
        return Text("PingError", style="red")

def getChampSelect():
    global chatID
    champSelect = json.loads(api.get("/lol-champ-select/v1/session").text)
    chatID = champSelect["chatDetails"]["multiUserChatId"]

def sendChat(msg):
    sAPI = api.post("/lol-chat/v1/conversations/" + chatID + "/messages", json={"body": msg})
    if not sAPI.status_code == 200:
        logErr("Error " + str(sAPI.status_code) + " enviando mensaje al chat: " + json.loads(sAPI.text)["message"] + "\n")
        
def main():
    global Lapse, state, exitScript
    while True:
        try:
            checkLeague()
            if exitScript: return
            request = api.get("/lol-gameflow/v1/gameflow-phase")
            if not request.status_code == 200:
                logErr("Error " + str(request.status_code) + " consultando fase de partida: " + request.text + "\n")
            else:
                stat=request.text.replace('"', "")
        
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
                request = api.post('/lol-matchmaking/v1/ready-check/accept')
                if request.status_code == 200 or request.status_code == 204:
                    logging.info("Partida aceptada!")
                    state=stat
                else:
                    logging.info("Error " + str(request.status_code) + " aceptando partida: " + request.text + "\n")
            elif stat == "ChampSelect":
                getChampSelect()
                if state != stat:
                    status("Selección de campeón...")
                    state=stat
                    #sendChat("TOP")
                    #sendChat("TOP")
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
            logging.info("Error conectando a la API: " + str(err) + "\n")
            state="error"
        except ConnectionRefusedError as err:
            logging.info("Error conectando a la API. Conexión rechazada: " + str(err) + "\n")
            state="error"
        except AttributeError as err:
            logging.info("Error de atributos: " + str(err) + "\n")
            state="error"
        except league_connection.exceptions.ConnectionTimeoutError as err:
            logging.info("Tiempo de espera de conexión agotado: " + str(err) + "\n")
            state="error"
        except Exception as err:
            logging.info("Error desconocido: " + str(type(err)) + " - " + str(err) + "\n")
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
