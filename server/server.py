import socket
import threading
import json
import os

from functions import *
from threading import Event

VERSIONSTRING = "netlog server v0.1 alpha"
connDict = { } # This dictionary contains all threaded user connections
envDict = { } # This dictionary contains all log environments
CONFIGPATH = "/etc/netlog/environments.conf"

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("0.0.0.0", 4125))
server_socket.listen(5)

class Connection(threading.Thread):
    def __init__(self, connection, address, iD):
        self._connection = connection
        self._ip, self._port = address
        self._id = iD
        self._isonline = True

        # starting the connection as thread
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()

    def _setup(self):
        Log("Started setup process with " + self.getconndetails())
        self._send("welcome", VERSIONSTRING)

        data = self._recv()
        if data is False:
            self.exit("Protocol Missmatch")
            return False

        if data["type"] != "environment":
            self.exit("Protocol Mismatch")
            return False

        if data["content"] not in envDict.keys():
            self.exit("Environment doesn't exist")
            return False

        self._environment = data["content"]
        if "key" not in envDict[self._environment].keys():
            self._send("ok")
            Log(self.getconndetails() + " successfully authenticated on " + self._environment)
            return True

        self._send("protected")
        data = self._recv()
        if data is False:
            self.exit("Protocol Missmatch")
            return False

        if data["type"] != "key":
            self.exit("Protocol Mismatch")
            return False

        if data["content"] == envDict[self._environment]["key"]:
            self._send("ok")
            Log(self.getconndetails() + " successfully authenticated on " + self._environment)
            return True
        else:
            self.exit("Invalid key")


    def run(self) -> None:
        status = self._setup()
        if not status:
            return

        while True:
            data = self._recv()
            if data is False:
                self.exit("Protocol Missmatch")
                return

            if data["type"] == "ping":
                self._send("pingresponse", data["content"])
                continue

            elif data["type"] == "exit":
                self.exit("Connection closed by client")
                return

            elif data["type"] == "log":
                if type(data["content"]) is not dict:
                    self.exit("Protocol Missmatch")
                    return
                if not ("logfile" in data["content"].keys() and "logmsg" in data["content"].keys()):
                    self.exit("Protocol Missmatch")
                    return

                with open(envDict[self._environment]["location"] + "/" + data["content"]["logfile"], "a+") as logfile:
                    logfile.write(data["content"]["logmsg"])
                    logfile.close()
                self._send("ok", "Log written")

            else:
                self.exit("Protocol Missmatch")
                return


    def _recv(self):
        try:
            data = str(self._connection.recv(2048), "utf-8")
            if len(data) == 0:
                return False
            if data[-2:] == "\r\n":
                data = data[:-2]
            try:
                data = json.loads(data)
                if "type" in data.keys() and "content" in data.keys():
                    return data
                else:
                    return False
            except json.JSONDecodeError:
                return False
        except UnicodeDecodeError:
            self._connection.close()
            return False
        except ConnectionResetError:
            self._connection.close()
            return False
        except TimeoutError:
            self._connection.close()
            return False
        except OSError:
            self._connection.close()
            return False


    def _send(self, form, content=None):
        message = {"type":form, "content":content}
        message = json.dumps(message, ensure_ascii=False)
        try:
            self._connection.send(bytes(message, "utf-8"))
        except BrokenPipeError:
            return
        except OSError:
            return


    def exit(self, msg):
        self._send("exit", msg)
        self._isonline = False
        self._connection.close()
        Log("Connection closed to " + self.getconndetails() + " with message: " + msg)

    def getconndetails(self):
        conndetails = "(" + self._ip + ":" + str(self._port) + ",PID:" + str(self._id) + ")"
        return conndetails


def acceptConnections():
    global connDict
    connectionCounter = 0
    while True:
        connection, address = server_socket.accept()
        connDict["conn" + str(connectionCounter)] = Connection(connection, address, connectionCounter)
        connectionCounter += 1


def parseConfig():
    global envDict
    try:
        with open(CONFIGPATH, 'r') as configfile:
            try:
                environments = json.loads(configfile.read())
                configfile.close()
            except json.JSONDecodeError:
                configfile.close()
                return False
    except FileNotFoundError:
        return False
    return environments


envDict = parseConfig()
if not envDict:
    print("Config file invalid or not found")
    exit(1)

for envs in envDict.keys():
    try:
        os.makedirs(envDict[envs]["location"])
    except FileExistsError:
        pass

acceptConnectionsThread = threading.Thread(target=acceptConnections)
acceptConnectionsThread.daemon = True
acceptConnectionsThread.start()

print("Started " + VERSIONSTRING + ". Listening for incoming connections...")

try:
    Event().wait() # a better more cpu efficient way to write while True: pass
except KeyboardInterrupt:
    exit(1)
except EOFError:
    exit(1)
