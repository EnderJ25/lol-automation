import os, time, urllib3, json, logging
from urllib.parse import urljoin
from requests import Session

__all__ = [
    "init_lcu",
    "gameFlow",
    "acceptMatch",
    "getChampSelect",
    "sendChat",
    "autoChat",
    "ConnectionTimeoutError"
]

#####=============================================================#####
#####                           Internal                          #####
#####=============================================================#####

##---------------------------- Variables ----------------------------##
## Initialize variables
__lockfile__ = None
__timeout__ = None
__lcu_info__ = None
__lcu_api__ = None

## ChampSelect variables
__chatID__ = None
__hiddenMatch = False

##----------------------------- Classes -----------------------------##
class LeagueConnection(Session):
    def __init__(self):
        super().__init__()
        urllib3.disable_warnings()
        
    def request(self, method, url, *args, **kwargs):
        url = urljoin(__lcu_info__['url'], url)
        kwargs['auth'] = __lcu_info__['username'], __lcu_info__['password']
        kwargs['verify'] = False
        return super().request(method, url, *args, **kwargs)
    
##---------------------------- Functions ----------------------------##
def get_connection_info():
    global __lcu_info__
    start = time.time()
    while True:
        if time.time() - start > __timeout__:
            raise ConnectionTimeoutError('Asegúrese de que el cliente de League of Legends ha iniciado')
        if not os.path.exists(__lockfile__):
            time.sleep(1)
            continue
        with open(__lockfile__, 'r') as fp:
            data = fp.read()
            data = data.split(':')

            if len(data) < 5:
                time.sleep(1)
                continue
            
            __lcu_info__ = {
                'url': f'{data[4]}://127.0.0.1:{data[2]}',
                'port': int(data[2]),
                'username': 'riot',
                'password': data[3],
                'method': data[4],
            }
            break
#####=============================================================#####

#####=============================================================#####
#####                            Public                           #####
#####=============================================================#####

##--------------------------- Error classes -------------------------##
class LeagueConnectionError(Exception):
    pass

class ConnectionTimeoutError(LeagueConnectionError):
    pass

##------------------------ Initialize function ----------------------##
def init_lcu(lockfile, timeout=30):
    global __lockfile__, __timeout__, __lcu_api__
    __lockfile__ = lockfile
    __timeout__ = timeout
    get_connection_info()
    __lcu_api__ = LeagueConnection()

##---------------------------- Functions ----------------------------##
def gameFlow():
    global __chatID__ , __hiddenMatch__
    result = __lcu_api__.get("/lol-gameflow/v1/gameflow-phase")
    if result.status_code == 200:
        ## Get Champion selection data if available
        if result.text.replace('"', "") == "ChampSelect":
            champSelect = json.loads(__lcu_api__.get("/lol-champ-select/v1/session").text)
            if not champSelect["chatDetails"]["multiUserChatId"] == __chatID__:
                __chatID__ = champSelect["chatDetails"]["multiUserChatId"]
                logging.info("chatID: " + str(__chatID__))
            __hiddenMatch__ = champSelect["hasSimultaneousPicks"]
        ## Return GameFlow Phase
        return result.text.replace('"', "")
    
def acceptMatch():
    result = __lcu_api__.post('/lol-matchmaking/v1/ready-check/accept')
    if result.status_code == 200 or result.status_code == 204:
        return True

def getChampSelect():
    champSelect = json.loads(__lcu_api__.get("/lol-champ-select/v1/session").text)
    return champSelect

def sendChat(msg):
    result = __lcu_api__.post("/lol-chat/v1/conversations/" + __chatID__ + "/messages", json={"body": msg})
    if not result.status_code == 200:
        logging.error("Error " + str(result.status_code) + " enviando mensaje al chat: " + json.loads(result.text)["message"])
    else:
        return True

def autoChat(role, hiddenOnly):
        if hiddenOnly and not __hiddenMatch__: return
        if role == 0: return
        if role == 1: sendChat("TOP")# TOP
        if role == 2: sendChat("JG")# JG
        if role == 3: sendChat("MID")# MID
        if role == 4: sendChat("ADC")# ADC
        if role == 5: sendChat("SUPP")# SUPP
                            
