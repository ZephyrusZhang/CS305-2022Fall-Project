import struct

WHOHAS = 0
IHAVE = 1
GET = 2
DATA = 3
ACK = 4
DENIED = 5
STOP = 6

BUF_SIZE = 1400
CHUNK_DATA_SIZE = 512 * 1024
MAX_PAYLOAD = 1024
HEADER_LEN = struct.calcsize("!HBBHHII")
PACKET_FORMAT = '!HBBHHII'
