import os, sys, time, threading, psutil, colorama, league_connection, configparser
from msvcrt import getch, kbhit
from ping3 import ping as ping3
from rich.console import Console
from rich import box
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.style import Style
from rich.progress import Progress

lockfile = 'C:\\Riot Games\\League of Legends\\lockfile'
inifile = os.path.dirname(sys.argv[0]) + '\\lol-automation.ini'

status="init"
leagueDetected=False
exitScript=False
apiTimeout=10

def configuration(write=False):
    global config, pingTargets, pingLapse, pingEnabled, Lapse1, Lapse2, Lapse, logErr_enabled
    config = configparser.ConfigParser()
    if write:
        config["general"] = {"logErrors": logErr_enabled}
        config["ping"] = {"pingEnabled": pingEnabled, "pingLapse": pingLapse}
        config["timer"] = {"Lapse1": Lapse1, "Lapse2": Lapse2}
        try:
            config['pingTargets'] = pingTargets
        except:
            logErr("Error de configuración. Restableciendo...")
            try:
                os.remove(inifile)
            except:
                pass
            configuration()
            return
        with open(inifile, 'w') as configfile:
            config.write(configfile)
        log(Text("Configuración guardada.", style="green"))
    else:
        pingTargets = {}
        try:
            config.read(inifile)
        except:
            logErr("Error de configuración. Restableciendo...")
            try:
                os.remove(inifile)
            except:
                pass
            configuration(True)
            return
        logErr_enabled = config.getboolean("general", "logErrors", fallback=True)
        pingLapse = config.getfloat("ping", "pingLapse", fallback=1)
        pingEnabled = config.getboolean("ping", "pingEnabled", fallback=False)
        Lapse1 = config.getfloat("timer", "Lapse1", fallback=1)
        Lapse = Lapse1
        Lapse2 = config.getfloat("timer", "Lapse2", fallback=0.5)
        if config.has_section("pingTargets"):
            for i in config["pingTargets"]:
                pingTargets[i] = eval(config["pingTargets"][i])
        else:
            pingTargets = {1:["Google", "www.google.com"]}
        log(Text("Configuración cargada.", style="green"))
            

def logErr (text):
    if logErr_enabled: log(Text(text, style="red"))
    
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
        statusBar("Inicializando...")
        log("Detectando Cliente de League of Legends... ")
        while True:
            if checkProcess("LeagueClient.exe"):
                log(Text("Cliente de League of Legends detectado.", style="green"))
                log("Conectando a la API...")
                api = league_connection.LeagueConnection(lockfile, timeout=apiTimeout)
                while True:
                    try:
                        api.get("/lol-gameflow/v1/gameflow-phase")
                        log(Text("Conectado!", style="green"))
                        break
                    except:
                        time.sleep(0.5)
                statusBar("Inicializado")
                leagueDetected=True
                return False
            time.sleep(3)
    elif not checkProcess("LeagueClient.exe"):
        log(Text("Cliente cerrado.", style="red"))
        exitScript=True

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
        
def main():
    global Lapse, status, exitScript
    while True:
        try:
            if exitScript: return
            checkLeague()
            #print("Router: " + ping("192.168.1.1"))
            #print("League: " + ping("lan.leagueoflegends.com"))
            request = api.get("/lol-gameflow/v1/gameflow-phase")
            if not request.status_code == 200:
                logErr("Error " + str(request.status_code) + " consultando fase de partida: " + request.text + "\n")
            else:
                stat=request.text.replace('"', "")
        
            if stat == "None" and status != stat:
                statusBar("Esperando entrar a una sala...")
                status=stat
            elif stat == "Lobby" and status != stat:
                statusBar("En sala.")
                status=stat
            elif stat == "CheckedIntoTournament" and status != stat:
                statusBar("Confirmado en Clash.")
                status=stat
            elif stat == "Matchmaking" and status != stat:
                statusBar("Buscando partida...")
                status=stat
            elif stat == "ReadyCheck" and status != stat:
                request = api.post('/lol-matchmaking/v1/ready-check/accept')
                if request.status_code == 200 or request.status_code == 204:
                    log(Text("Partida aceptada!", style="green"))
                    status=stat
                else:
                    logErr("Error " + str(request.status_code) + " aceptando partida: " + request.text + "\n")
            elif stat == "ChampSelect" and status != stat:
                statusBar("Selección de campeón...")
                status=stat
            elif stat == "InProgress" and status != stat:
                statusBar("Partida en progreso...")
                status=stat
            elif stat == "Reconnect" and status != stat:
                statusBar("Desconectado de la partida.")
                status=stat
            elif stat == "WaitingForStats" and status != stat:
                statusBar("Esperando estadísticas...")
                status=stat
            elif stat == "PreEndOfGame" and status != stat:
                statusBar("Finalizando partida...")
                status=stat
            elif stat == "EndOfGame" and status != stat:
                statusBar("Partida finalizada.")
                status=stat
            elif status != stat:
                log(stat)
            
        except ConnectionError as err:
            logErr("Error conectando a la API: " + str(err) + "\n")
            status="error"
        except ConnectionRefusedError as err:
            logErr("Error conectando a la API. Conexión rechazada: " + str(err) + "\n")
            status="error"
        except AttributeError as err:
            logErr("Error de atributos: " + str(err) + "\n")
            status="error"
        except league_connection.exceptions.ConnectionTimeoutError as err:
            logErr("Tiempo de espera de conexión agotado: " + str(err) + "\n")
            status="error"
        except Exception as err:
            logErr("Error desconocido: " + str(type(err)) + " - " + str(err) + "\n")
            status="error"
            
        time.sleep(Lapse)

def asyncInput():
    global exitScript, pingEnabled
    while True:
        if exitScript: return
        if kbhit():
            ch=str(getch()).replace("'","")[1:]
            #log("Tecla " + ch + " presionada.")
            if ch.lower() == ("q"):
                exitScript=True
            elif ch.lower() == ("p"):
                if pingEnabled:
                    log(Text("Ping deshabilitado.", style="red"))
                    pingEnabled=False
                else:
                    log(Text("Ping habilitado.", style="green"))
                    pingEnabled=True
            if ch.lower() == ("s"):
                configuration(True)
            if ch.lower() == ("a"):
                configuration()
        time.sleep(0.1)

def asyncScreen():
    with Live(l, refresh_per_second=10, screen=True, vertical_overflow='visible') as live:
        while True:
            if exitScript:
                log("Saliendo...")
                statusBar("Saliendo...")
                time.sleep(5)
                return

            #log(str(l["log"]))
            #f = open("demofile2.txt", "a", encoding='utf-8')
            #f.write(str(render_map[l["log"]].render))
            #f.close()
            time.sleep(2)

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

def initScreen():
    global c, l, logTable, pingTable, infoTable
    colorama.init()
    c = Console(log_path=False)
    l = Layout()
    os.system("title " + "League of Legends AutoAccept")
    l.split(
    Layout(name="header", size=3),
    Layout(ratio=1, name="main"),
    Layout(size=3, name="status"),
    )
    l["main"].split_row(
        Layout(name="log", ratio=2),
        Layout(name="side")
    )
    l["side"].split(
        Layout(name="info"),
        Layout(name="ping")
    )
    l["header"].update(Panel(Align.center("League of Legends Automation"), box=box.ROUNDED, style="green"))
    infoTable = Table.grid(expand=True)
    infoTable.add_column(justify="left", no_wrap=True)
    infoTable.add_column(justify="right", no_wrap=True)
    makeInfo()
    l["main"]["side"]["info"].update(Panel(infoTable, title="Info", style="blue"))
    pingTable = Table.grid(expand=True)
    pingTable.add_column(justify="left", no_wrap=True)
    pingTable.add_column(justify="right", no_wrap=True)
    l["main"]["side"]["ping"].update(Panel(pingTable, title="Ping", style="blue"))
    logTable = Table.grid(expand=True)
    logTable.add_column() #no_wrap=True)
    c.print(l)

def makeInfo():
    global infoTable
    infoTable.add_row("Tecla Q", Text("Salir.", style="red"))
    infoTable.add_row("Tecla P", Text("Alternar ping.", style="green"))
    infoTable.add_row("Tecla S", Text("Guardar configuración.", style="green"))
    infoTable.add_row("Tecla A", Text("Cargar configuración.", style="green"))

def log(data):
    global logTable
    logTable.add_row(data)
    l["main"]["log"].update(Panel(logTable, title="Registro", style="white"))

def statusBar(data):
    l["status"].update(Panel(data, style="bright_white"))
    
if __name__ == '__main__':
    initScreen()

    log("Archivo de configuración: " + inifile)
    configuration()
    
    p1 = threading.Thread(target=main)
    p2 = threading.Thread(target=asyncScreen)
    p3 = threading.Thread(target=asyncInput)
    p4 = threading.Thread(target=asyncPing)
    p1.start();p2.start();p3.start();p4.start()
    p1.join();p2.join();p3.join();p4.join()
    colorama.deinit()
