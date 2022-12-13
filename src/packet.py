import struct


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

    def __init__(self):
        self.magic = 52305
        self.team = 77
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
