from datetime import datetime
import sys
from sys import argv
import asyncio, random, time, uvloop, threading
from asyncio import events
from datetime import datetime
from RPCUtil import get_client_stub
from aiorpc import server

MAX_LIFETIME_MS = 60 * 1000

class PrimaryEventLoop(events.AbstractEventLoop):
    def __init__(self, pri):
        super().__init__()
        self.pri = pri
        
    def run_forever(self):
        """Run until stop() is called."""
        self._check_closed()
        self._check_running()
        self._set_coroutine_origin_tracking(self._debug)
        self._thread_id = threading.get_ident()
        old_agen_hooks = sys.get_asyncgen_hooks()
        sys.set_asyncgen_hooks(firstiter=self._asyncgen_firstiter_hook,
        finalizer=self._asyncgen_finalizer_hook)
        try:
            events._set_running_loop(self)
            while True:
                self.pri.check_death()
                self._run_once()
                if self._stopping:
                    break
        finally:
            self._stopping = False
            self._thread_id = None
            events._set_running_loop(None)
            self._set_coroutine_origin_tracking(False)
            sys.set_asyncgen_hooks(*old_agen_hooks)

class PrimaryServer:

    def __init__(self, pri_port):
        self.port = pri_port
        server.register("rpc_getID", self.rpc_getID)
        if not isinstance(self, HeartbeatServer):
            # Primary should selfdestruct eventually
            self.time_of_death = time.time() + random.randint(0, MAX_LIFETIME_MS)
            print("Time of death = " + str(self.time_of_death))
            server.register("rpc_isAlive", self.rpc_isAlive)
            self.id_to_send = 0
            self.is_pri = True
            self.loop = PrimaryEventLoop(self)
        asyncio.set_event_loop(self.loop)
        coro = asyncio.start_server(server.serve, '127.0.0.1', int(pri_port), loop=self.loop)
        s = self.loop.run_until_complete(coro)
        self.log("Listening")
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            s.close()
            self.loop.run_until_complete(s.wait_closed())


    async def rpc_getID(self) -> int:
        self.check_death()        
        id_to_return = self.id_to_send
        self.id_to_send += 10
        with open("id_to_send", "w") as f:
            f.write(str(self.id_to_send))
        return id_to_return

    async def rpc_isAlive(self):
        return True
    
    def check_death(self):
        if time.time() > self.time_of_death:
            self.log("Exiting...")
            exit()
    
    def log(self, msg):
        print(("[%s]::[%s]::[%s] %s") % (datetime.now(), self.port, "PR" if self.is_pri else "HB", msg))

class HeartbeatEventLoop(events.AbstractEventLoop):
    def __init__(self, hb):
        super().__init__()
        self.hb = hb
        
    async def run_forever(self):
        """Run until stop() is called."""
        self._check_closed()
        self._check_running()
        self._set_coroutine_origin_tracking(self._debug)
        self._thread_id = threading.get_ident()
        old_agen_hooks = sys.get_asyncgen_hooks()
        sys.set_asyncgen_hooks(firstiter=self._asyncgen_firstiter_hook,
        finalizer=self._asyncgen_finalizer_hook)
        try:
            events._set_running_loop(self)
            while True:
                if not self.is_pri:
                    self.hb.send_hb()
                self._run_once()
                if self._stopping:
                    break
        finally:
            self._stopping = False
            self._thread_id = None
            events._set_running_loop(None)
            self._set_coroutine_origin_tracking(False)
            sys.set_asyncgen_hooks(*old_agen_hooks)

class HeartbeatServer(PrimaryServer):
    def __init__(self, hb_port , pri_port) -> None:
        self.loop = HeartbeatEventLoop()
        super().__init__(hb_port)
        self.pri_port = pri_port
        self.is_pri = False
        self.primary_client = get_client_stub(self.pri_port)

    async def rpc_getID(self) -> int:
        if self.is_pri: # we are the primary
            return super().rpc_getID()
        # ping the primary server
        elif self.primary_client.rpc_isAlive() == None: # no response? make ourselves the primary server
            self.pri_port = None
            with open("id_to_send", "r") as f: # The next ID the primary wanted to send
                self.id_to_send = int(f.read())
            self.rpc_getID()
    
    async def send_hb(self):
        # send a heartbeat to the primary process
        if self.primary_client.rpc_isAlive() == None:
            self.is_pri = True # primary is dead, make ourselves the primary
    
async def start_pri(pri_port):
    await PrimaryServer(pri_port)

if __name__ == '__main__':
    try:
        name = argv[1]
    except:
        print("Usage: server PR|HB")
    if name == "PR":
         asyncio.run(start_pri(argv[2]))
    elif name == "HB":
        pri_port = argv[3]
        asyncio.run(HeartbeatServer(argv[2], pri_port))
    else:
        print("Invalid server option")
