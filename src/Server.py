from datetime import datetime
from sys import argv
import asyncio, random, time, uvloop
from datetime import datetime
from RPCUtil import get_client_stub
from aiorpc import server

MAX_LIFETIME_MS = 60 * 1000

class PrimaryServer:
    def __init__(self, pri_port) -> None:
        if not isinstance(self, HeartbeatServer):
            # Primary should selfdestruct eventually
            self.time_of_death = time.time() + random.randint(MAX_LIFETIME_MS)
            server.register("rpc_isAlive", self.rpc_isAlive)
            self.id_to_send = 0
        server.register("rpc_getID", self.rpc_getID)
        loop = uvloop.new_event_loop()
        asyncio.set_event_loop(loop)
        coro = asyncio.start_server(server.serve, '127.0.0.1', int(pri_port), loop=loop)
        s = loop.run_until_complete(coro)
        self.log("Listening")
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            s.close()
            loop.run_until_complete(s.wait_closed())

    async def event_loop(self):
        if time.time() > self.time_of_death:
            exit()
        asyncio.sleep(0.001)

    async def rpc_getID(self):
        id_to_return = self.id_to_send
        self.id_to_send += 10
        with open("id_to_send", "w") as f:
            f.write(self.id_to_send)
        return id_to_return

    async def rpc_isAlive(self):
        return True

class HeartbeatServer(PrimaryServer):
    def __init__(self, hb_port , pri_port) -> None:
        super().__init__(hb_port)
        self.pri_port = pri_port
    
    def event_loop(self):
        asyncio.sleep(0.001)

    async def rpc_getID(self):
        if self.pri_port == None: # we are the primary
            super().rpc_getID()
        # ping the primary server. No response means we make ourselves the primary.
        elif get_client_stub(self.pri_port).rpc_isAlive() == None:
            self.pri_port = None
            with open("id_to_send", "r") as f: # The next ID the primary wanted to send
                self.id_to_send = int(f.read())
            self.rpc_getID()

if __name__ == '__main__':
    try:
        name = argv[1]
    except:
        print("Usage: server PR|HB")
    if name == "PR":
        asyncio.run(PrimaryServer().event_loop())
    elif name == "HB":
        pri_port = argv[2]
        asyncio.run(HeartbeatServer(argv[1], pri_port))
    else:
        print("Invalid server option")
