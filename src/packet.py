import struct

from config import *


class P2pPacket:
    """
        The format of p2p packet format is listed below.
    
            0                   1                   2                   3
            0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
           +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
           |             Magic             |     Team      |   Type Code   |
           +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
           |         Header Length         |        Packet Length          |
           +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
           |                       Sequence Number                         |
           +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
           |                          ACK Number                           |
           +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
           |                                                               :
           :                            Payload                            :
           :                                                               |
           +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


        Attributes
        ----------
        magic : int
            To check if you correctly deal with endian issue, or to check if the packet is spoofed.
        team : int
            Team index.
        type : int
            Indicate what type is this packet
        hlen : int
            Header length.
        plen : int
            Packet length.
        seq : int
            The sequence number for packet, i.e., it counts packets rather than bytes. This field is only
            valid for DATA packet. For other packet, it should always be 0.
        ack : int
            Only valid for ACK packet. For other packets, it should always be 0.
        payload : bytes
            Data to be transferred.
    """

    _PACKET_FORMAT = '!HBBHHII'

    _MAGIC = 52305
    _TEAM = 77

    def __init__(self):
        self.magic = P2pPacket._MAGIC
        self.team = P2pPacket._TEAM
        self.type = -1
        self.hlen = struct.calcsize(self._PACKET_FORMAT)
        self.plen = 0
        self.seq = 0
        self.ack = 0
        self.payload = bytes()

    def make_header(self):
        return struct.pack(self._PACKET_FORMAT,
                           self.magic,
                           self.team,
                           self.type,
                           self.hlen,
                           self.plen,
                           self.seq,
                           self.ack)

    def make_packet(self):
        return self.make_header() + self.payload

    def parse_packet(self, packet: bytes):
        header, self.payload = packet[:16], packet[16:]
        self.magic, self.team, self.type, self.hlen, self.plen, self.seq, self.ack = struct.unpack(self._PACKET_FORMAT, header)

    @staticmethod
    def whohas(chunkhash):
        """
            Generate WHOHAS packet

            Parameters
            ----------
            chunkhash : bytes
                The chunkhash of the chunk peer wants.
        """
        return struct.pack(P2pPacket._PACKET_FORMAT,
                           P2pPacket._MAGIC,
                           P2pPacket._TEAM,
                           WHOHAS,
                           HEADER_LEN,
                           HEADER_LEN + len(chunkhash),
                           0, 0) + chunkhash

    @staticmethod
    def ihave(chunkhash):
        """
            Generate IHAVE packet

            Parameters
            ----------
            chunkhash : bytes
                The requested chunk that peer has.
        """
        return struct.pack(P2pPacket._PACKET_FORMAT,
                           P2pPacket._MAGIC,
                           P2pPacket._TEAM,
                           IHAVE,
                           HEADER_LEN,
                           HEADER_LEN + len(chunkhash),
                           0, 0) + chunkhash

    @staticmethod
    def get(chunkhash):
        """
            Generate GET packet

            Parameters
            ----------
            chunkhash : bytes
                The chunk peer wants to download.
        """
        return struct.pack(P2pPacket._PACKET_FORMAT,
                           P2pPacket._MAGIC,
                           P2pPacket._TEAM,
                           GET,
                           HEADER_LEN,
                           HEADER_LEN + len(chunkhash),
                           0, 0) + chunkhash

    @staticmethod
    def data(chunkdata, seq: int):
        """
            Generate DATA packet

            Parameters
            ----------
            chunkdata : bytes
                The chunkdata peer needs to send
            seq : int
                Sequence number of packet to be sent
        """
        return struct.pack(P2pPacket._PACKET_FORMAT,
                           P2pPacket._MAGIC,
                           P2pPacket._TEAM,
                           DATA,
                           HEADER_LEN,
                           HEADER_LEN + len(chunkdata),
                           seq,
                           0) + chunkdata

    @staticmethod
    def ack(ack: int):
        """
            Generate ACK packet

            Parameters
            ----------
            ack : int
                The packet peer has received
        """
        return struct.pack(P2pPacket._PACKET_FORMAT,
                           P2pPacket._MAGIC,
                           P2pPacket._TEAM,
                           ACK,
                           HEADER_LEN,
                           HEADER_LEN,
                           0,
                           ack)
