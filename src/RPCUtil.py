from aiorpc import RPCClient
__url = '127.0.0.1'

def get_client_stub(port: str) -> RPCClient:
    return RPCClient(__url, int(port))
