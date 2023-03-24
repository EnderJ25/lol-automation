import asyncio, psutil, aioping

def checkProcess(processName):
    for proc in psutil.process_iter():
        try:
            if processName.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False;

async def updEntry(host, index):
    try:
        pingResult = await aioping.ping(host, timeout=1)
    except OSError:
        return "sys-err"
    if type(pingResult) == float:
        return int(pingResult * 1000)
    elif type(pingResult) == bool and not pingResult:
        return "unreach"
    elif pingResult == None:
        return "timeout"
    else:
        logging.error("Error de ping: " + str(type(pingResult)))
        return "error"
