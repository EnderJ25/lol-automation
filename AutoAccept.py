import os, sys, time, threading, psutil, colorama, league_connection
from termcolor import colored, cprint
from msvcrt import getch, kbhit
from ping3 import ping as ping3

printErr_enabled=True

lockfile = 'C:\\Riot Games\\League of Legends\\lockfile'

LAPSE = 1
LAPSE1 = 1
LAPSE2 = 0.5
api=None
status="None"
leagueDetected=False
exitScript=False

ePrint = lambda text, color: print(colored(text, color))
lPrint = lambda text, color: print(cprint(text, color, end=""))
def printErr (text):
    if printErr_enabled: print(colored(text, "red"))
def move (y, x):
    print("\033[%d;%dH" % (y, x))
    
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
        print("Detectando Cliente de League of Legends... ")
        while True:
            if checkProcess("LeagueClient.exe"):
                ePrint("Cliente de League of Legends detectado.", "green")
                print("Conectando a la API...")
                api = league_connection.LeagueConnection(lockfile, timeout=5)
                while True:
                    try:
                        api.get("/lol-gameflow/v1/gameflow-phase")
                        ePrint("Conectado!", "green")
                        break
                    except:
                        pass
                leagueDetected=True
                return False
            time.sleep(3)
    elif not checkProcess("LeagueClient.exe"):
        print("Cliente cerrado.")
        exitScript=True

def ping(host):
    pingResult = ping3(host, unit='ms', timeout=1)
    if type(pingResult) == float:
        return str(int(pingResult)) + "ms"
    elif type(pingResult) == bool and not pingResult:
        return "unreachable"
    elif pingResult == None:
        return "timeout"
    else:
        printErr("Error de ping: " + str(type(pingResult)))
        return "error"
        
def backend():
    global LAPSE, status, exitScript
    while True:
        try:
            if exitScript: return
            checkLeague()
            #print("Router: " + ping("192.168.1.1"))
            #print("League: " + ping("lan.leagueoflegends.com"))
            request = api.get("/lol-gameflow/v1/gameflow-phase")
            if not request.status_code == 200:
                printErr("Error " + str(request.status_code) + " consultando fase de partida: " + request.text + "\n")
            else:
                stat=request.text.replace('"', "")
        
            if stat == "None" and status != stat:
                print("Esperando entrar a una sala...")
                status=stat
            elif stat == "Lobby" and status != stat:
                print("Sala ingresada.")
                status=stat
            elif stat == "Matchmaking" and status != stat:
                print("Buscando partida...")
                status=stat
            elif stat == "ReadyCheck" and status != stat:
                request = api.post('/lol-matchmaking/v1/ready-check/accept')
                if request.status_code == 200 or request.status_code == 204:
                    ePrint("Partida aceptada!", "green")
                    status=stat
                else:
                    printErr("Error " + str(request.status_code) + " aceptando partida: " + request.text + "\n")
            elif stat == "ChampSelect" and status != stat:
                print("Selección de campeón...")
                status=stat
            elif stat == "InProgress" and status != stat:
                print("Partida en progreso...")
                status=stat
            elif stat == "Reconnect" and status != stat:
                print("Desconectado de la partida.")
                status=stat
            elif stat == "WaitingForStats" and status != stat:
                print("Esperando estadísticas...")
                status=stat
            elif stat == "PreEndOfGame" and status != stat:
                print("Finalizando partida...")
                status=stat
            elif stat == "EndOfGame" and status != stat:
                print("Partida finalizada.")
                status=stat
            elif status != stat:
                print(stat)
            
        except ConnectionError as err:
            printErr("Error conectando a la API: " + str(err) + "\n")
            status="error"
        except ConnectionRefusedError as err:
            printErr("Error conectando a la API. Conexión rechazada: " + str(err) + "\n")
            status="error"
        except AttributeError as err:
            printErr("Error de atributos: " + str(err) + "\n")
            status="error"
        except league_connection.exceptions.ConnectionTimeoutError as err:
            printErr("Tiempo de espera de conexión agotado: " + str(err) + "\n")
            status="error"
        except Exception as err:
            printErr("Error desconocido: " + str(type(err)) + " - " + str(err) + "\n")
            status="error"
            
        time.sleep(LAPSE)

def frontend():
    global exitScript
    while True:
        if exitScript: return
        if kbhit():
            ch=str(getch()).replace("'","")[1:]
            #print(ch)
            if ch.lower() == ("q"):
                exitScript=True
        time.sleep(0.1)

if __name__ == '__main__':
    colorama.init()
    os.system("title " + "League of Legends AutoAccept")
    ePrint("Iniciado.","green")
    move(1,0)
    ePrint("Presione Q si desea salir.","yellow")
    p1 = threading.Thread(target=backend)
    p2 = threading.Thread(target=frontend)
    p1.start();p2.start();p1.join();p2.join()
    print("Saliendo...")
    colorama.deinit()
    time.sleep(5)
