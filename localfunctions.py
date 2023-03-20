import psutil, ping3

def checkProcess(processName):
    for proc in psutil.process_iter():
        try:
            if processName.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False;

def ping(host):
    try:
        pingResult = ping3(host, unit='ms', timeout=1)
    except OSError:
        return "SysError"
    if type(pingResult) == float:
        pingColor = "red"
        if int(pingResult) <= 20:
            pingColor = "white"
        elif int(pingResult) <= 200:
            pingColor = "green"
        elif int(pingResult) <= 500:
            pingColor = "yellow"
        return str(int(pingResult)) + "ms" #style=pingColor
    elif type(pingResult) == bool and not pingResult:
        return "unreach"
    elif pingResult == None:
        return "timeout"
    else:
        logging.error("Error de ping: " + str(type(pingResult)))
        return "PingError"
