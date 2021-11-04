from RPCUtil import get_client_stub
import asyncio, uvloop
from datetime import datetime
from sys import argv

class Client:
    def __init__(self, clnt_port, pri_port, hb_port) -> None:
        assert(all([get_client_stub(p) != None for p in [clnt_port, pri_port, hb_port]]))
        self.clnt_port = clnt_port
        self.pri_port = pri_port
        self.hb_port = hb_port
        loop = uvloop.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def event_loop(self):
        server = get_client_stub(self.pri_port)
        while True: # request IDs from the server
            self.log("Requesting ID from primary server")
            id = await server.call('rpc_getID')
            if id == None:
                if self.hb_port == None:
                    print("Primary and backup are down, aborting")
                    break
                self.pri_port = self.hb_port
                self.hb_port = None
                server = get_client_stub(self.pri_port)
            else:
                self.log("Received ID " + str(id))
            asyncio.sleep(0.001)
    
    def log(self, msg):
        print(("[%s]::[%s] %s") % (datetime.now(), self.clnt_port, msg))

if __name__ == '__main__':
    try:
        clnt = Client(argv[1], argv[2], argv[3])
    except:
        print("Usage: client clnt_port pri_port hb_port")
        exit()
    asyncio.run(clnt.event_loop())
        
