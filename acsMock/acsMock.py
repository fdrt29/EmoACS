from socket import gethostname, gethostbyname, socket, AF_INET, SOCK_STREAM

def sendDevice(sock: socket, msg: str) -> bytes:
    if not connected:
        return None
    hexMsg = MSGS.get(msg, None)
    if not hexMsg:
        return None
    sock.send(hexMsg.encode())
    data = sock.recv(BUFSIZE)
    return data.decode()

def sendMsgAndLog(conn, msg: str) -> None:
    hexMsg = MSGS.get(msg, None)
    print(f'sending: {msg}') #  | {hexMsg.encode()}
    conn.send(hexMsg.encode())
    print(f'sended: {msg}') #  | {hexMsg.encode()}


devicePORT = 17494
hostname = gethostname()
hostIP = gethostbyname(hostname)
BUFSIZE = 4 * 4
MSGS = {
    'init':  r'\x00\x06\x07\x00',
    'ready': r'\x00\x0D\x00\x00',

    'lock':  r'\x00\x07\x00\x00',
    'ok':  r'\x00\x05\x00\x00',

    'pass1': r'\x00\x09\x00\x00',
    'pass2': r'\x00\x0A\x00\x00',
    'out1':  r'\x00\x0B\x00\x00',
    'out2':  r'\x00\x0C\x00\x00',
}

#BYTESTOMSGS = {
#    r'\x00\x06\x07\x00' : 'init', 
#    r'\x00\x0D\x00\x00' : 'ready',
#    r'\x00\x07\x00\x00' : 'lock', 
#    r'\x00\x09\x00\x00' : 'pass1',
#    r'\x00\x0A\x00\x00' : 'pass2',
#    r'\x00\x0B\x00\x00' : 'out1', 
#    r'\x00\x0C\x00\x00' : 'out2', 
#    r'\x00\x05\x00\x00' : 'error'
#    }

sock = socket()
sock.bind(('', devicePORT))
sock.listen(1)
conn, addr = sock.accept()

print(f'connected: {addr}')

while True:
    bytes = conn.recv(BUFSIZE)
    data = bytes.decode()
    if not data:
        break
    print(f'received: {data}')
    if data == MSGS['init']:
        sendMsgAndLog(conn, 'ready')
    elif data == MSGS['pass1']:
        sendMsgAndLog(conn, 'out1')
    elif data == MSGS['pass2']:
        sendMsgAndLog(conn, 'out2')
    elif data == MSGS['lock']:
            sendMsgAndLog(conn, 'ok')

conn.close()
exit()
