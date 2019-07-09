import socket
import json

class Netlog:
    def __init__(self, address, port=4125):
        self._connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = address
        self.port = port
        self._setenv = False
        self.env = None
        try:
            self._connection.connect((self.address, self.port))
        except ConnectionRefusedError:
            raise ConnectionRefusedError("Destination host unreachable")

        data = self._recv()
        if not data:
            raise ConnectionRefusedError("Protocol missmatch, maybe the server isn't running netlog")

        if data["type"] != "welcome":
            raise ConnectionRefusedError("Protocol missmatch, maybe the server isn't running netlog")

        self.serverversion = data["content"]
        self._isdead = False

    def setEnvironment(self, environment, key=None):
        if self.env is not None:
            return False

        if self._isdead:
            raise ConnectionResetError("Connection closed by remote host")

        self._send("environment", environment)
        data = self._recv()
        if not data:
            raise ConnectionRefusedError("Protocol missmatch, maybe the server isn't running netlog")

        if data["type"] == "ok":
            self.env = environment
            return True

        elif data["type"] == "protected":
            if key is None:
                self._connection.close()
                self._isdead = True
                raise ConnectionAbortedError("Environment is protected, but no password was provided")

            self._send("key", key)
            data = self._recv()
            if not data:
                self._isdead = True
                raise ConnectionRefusedError("Protocol missmatch, maybe the server isn't running netlog")

            if data["type"] == "ok":
                self.env = environment
                return True

            else:
                self._isdead = True
                raise ConnectionRefusedError("Protocol missmatch, maybe the server isn't running netlog")

        else:
            self._isdead = True
            raise ConnectionRefusedError("Protocol missmatch, maybe the server isn't running netlog")

    def log(self, file, message):
        if self.env is None:
            return False

        if self._isdead:
            raise ConnectionResetError("Connection closed by remote host")

        self._send("log", {"logfile":file, "logmsg":message})
        data = self._recv()
        if not data:
            self._isdead = True
            raise ConnectionRefusedError("Protocol missmatch, maybe the server isn't running netlog")

        if data["type"] == "ok":
            return True

        else:
            self._isdead = True
            raise ConnectionRefusedError("Protocol missmatch, maybe the server isn't running netlog")

    def close(self):
        if self._isdead:
            raise ConnectionResetError("Connection closed by remote host")

        self._send("exit", "Connection closed by client")
        self._connection.close()
        self._isdead = True
        return True

    def _send(self, form, content=None):
        message = {"type": form, "content": content}
        message = json.dumps(message, ensure_ascii=False)
        try:
            self._connection.send(bytes(message, "utf-8"))
        except BrokenPipeError:
            self._isdead = True
            return
        except OSError:
            self._isdead = True
            return

    def _recv(self):
        try:
            data = str(self._connection.recv(2048), "utf-8")
            if len(data) == 0:
                self._connection.close()
                return False
            try:
                data = json.loads(data)
                if "type" in data.keys() and "content" in data.keys():
                    return data
                else:
                    self._connection.close()
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
