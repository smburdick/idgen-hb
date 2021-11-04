from datetime import datetime
from sys import argv
import asyncio, random, time, uvloop
from datetime import datetime
from RPCUtil import get_client_stub
from aiorpc import server

MAX_LIFETIME_MS = 60 * 1000

class PrimaryServer:
    def __init__(self, pri_port) -> None:
        self.port = pri_port
        if not isinstance(self, HeartbeatServer):
            # Primary should selfdestruct eventually
            self.time_of_death = time.time() + random.randint(0, MAX_LIFETIME_MS)
            print("Time of death = " + str(self.time_of_death))
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

    async def rpc_getID(self):
        # TODO: move this into event loop instead, so API d
        self.check_death()        
        id_to_return = self.id_to_send
        self.id_to_send += 10
        with open("id_to_send", "w") as f:
            f.write(str(self.id_to_send))
        return id_to_return

    async def rpc_isAlive(self):
        return True
    
    def check_death(self):
        if not isinstance(self, HeartbeatServer) and time.time() > self.time_of_death:
            self.log("Exiting...")
            exit()
    
    def log(self, msg):
        print(("[%s]::[%s] %s") % (datetime.now(), self.port, msg))

class HeartbeatServer(PrimaryServer):
    def __init__(self, hb_port , pri_port) -> None:
        super().__init__(hb_port)
        self.pri_port = pri_port
    
    def event_loop(self): # TODO:
        asyncio.sleep(0.001)

    async def rpc_getID(self):
        if self.pri_port == None: # we are the primary
            super().rpc_getID()
        # ping the primary server. No response means we make ourselves the primary.
        else:
            self.send_hb()
        elif get_client_stub(self.pri_port).rpc_isAlive() == None:
            self.pri_port = None
            with open("id_to_send", "r") as f: # The next ID the primary wanted to send
                self.id_to_send = int(f.read())
            self.rpc_getID()
    
    async def send_hb(self):
        # send a heartbeat to the primary process
        pass

if __name__ == '__main__':
    try:
        name = argv[1]
    except:
        print("Usage: server PR|HB")
    if name == "PR":
        asyncio.run(PrimaryServer(argv[2]).event_loop())
    elif name == "HB":
        pri_port = argv[3]
        asyncio.run(HeartbeatServer(argv[2], pri_port))
    else:
        print("Invalid server option")
