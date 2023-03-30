import logging, asyncio, psutil, aioping, socket

def checkProcess(processName):
    for proc in psutil.process_iter():
        try:
            if processName.lower() in proc.name().lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False;

async def ping(host):
    try:
        pingResult = await aioping.ping(host, timeout=1)
    except TimeoutError:
        return "timeout"
    except socket.gaierror:
        return "unreach"
    except Exception as err:
        logging.error("Error de ping inesperado: " + str(type(err)) + " - " + str(err) + "\n")
        return "unk-err"
    return int(pingResult * 1000) # pingResult is a float of seconds. Multiply to 1000 to return ms.
