import logging
import sys
import os

from formatter import CustomFormatter
from packet import P2pPacket
from config import *
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import select
import util.simsocket as simsocket
import struct
import socket
import util.bt_utils as bt_utils
import hashlib
import argparse
import pickle

"""
This is CS305 project skeleton code.
Please refer to the example files - example/dumpreceiver.py and example/dumpsender.py - to learn how to play with this skeleton.
"""

config = None
ex_sending_chunkhash: str = ''
ex_output_file: str = ''
ex_received_chunk = dict()
ex_downloading_chunkhash: str = ''

# Set logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

# TODO: 通过维护session list来和不同peer通信


def process_download(sock, chunkfile, outputfile):
    """
    if DOWNLOAD is used, the peer will keep getting files until it is done
    """
    global ex_output_file
    global ex_received_chunk
    global ex_downloading_chunkhash

    ex_output_file = outputfile
    # Step 1: read chunkhash to be downloaded from chunkfile
    download_hash = bytes()
    with open(chunkfile, 'r') as cf:
        index, datahash_str = cf.readline().strip().split(" ")
        ex_received_chunk[datahash_str] = bytes()
        ex_downloading_chunkhash = datahash_str

        # hex_str to bytes
        datahash = bytes.fromhex(datahash_str)
        download_hash = download_hash + datahash

    whohas_pkt = P2pPacket.whohas(download_hash)

    # Step3: flooding whohas to all peers in peer list
    peer_list = config.peers
    for p in peer_list:
        if int(p[0]) != config.identity:
            sock.sendto(whohas_pkt, (p[1], int(p[2])))


def process_inbound_udp(sock):
    # Receive pkt
    global config, ex_sending_chunkhash

    pkt, from_addr = sock.recvfrom(BUF_SIZE)
    Magic, Team, Type, hlen, plen, Seq, Ack = struct.unpack(PACKET_FORMAT, pkt[:HEADER_LEN])
    data = pkt[HEADER_LEN:]
    if Type == WHOHAS:
        # received an WHOHAS pkt
        # see what chunk the sender has
        whohas_chunk_hash = data[:20]
        # bytes to hex_str
        chunkhash_str = bytes.hex(whohas_chunk_hash)
        ex_sending_chunkhash = chunkhash_str

        logger.info(f'Receive: WHOHAS {chunkhash_str}. Has {list(config.haschunks.keys())}')
        if chunkhash_str in config.haschunks:
            # send back IHAVE pkt
            ihave_pkt = P2pPacket.ihave(whohas_chunk_hash)
            sock.sendto(ihave_pkt, from_addr)
    elif Type == IHAVE:
        # received an IHAVE pkt
        # see what chunk the sender has
        get_chunk_hash = data[:20]

        # send back GET pkt
        get_pkt = P2pPacket.get(get_chunk_hash)
        sock.sendto(get_pkt, from_addr)
    elif Type == GET:
        # received a GET pkt
        chunk_data = config.haschunks[ex_sending_chunkhash][:MAX_PAYLOAD]

        # send back DATA
        data_pkt = P2pPacket.data(chunk_data, 1)
        sock.sendto(data_pkt, from_addr)
    elif Type == DATA:
        # received a DATA pkt
        ex_received_chunk[ex_downloading_chunkhash] += data

        # send back ACK
        ack_pkt = P2pPacket.ack(Seq)
        sock.sendto(ack_pkt, from_addr)

        # see if finished
        if len(ex_received_chunk[ex_downloading_chunkhash]) == CHUNK_DATA_SIZE:
            # finished downloading this chunkdata!
            # dump your received chunk to file in dict form using pickle
            with open(ex_output_file, "wb") as wf:
                pickle.dump(ex_received_chunk, wf)

            # add to this peer's haschunk:
            config.haschunks[ex_downloading_chunkhash] = ex_received_chunk[ex_downloading_chunkhash]

            # you need to print "GOT" when finished downloading all chunks in a DOWNLOAD file
            logger.info(f'GOT {ex_output_file}')

            # The following things are just for illustration, you do not need to print out in your design.
            sha1 = hashlib.sha1()
            sha1.update(ex_received_chunk[ex_downloading_chunkhash])
            received_chunkhash_str = sha1.hexdigest()
            logger.info(f'Expected chunkhash: {ex_downloading_chunkhash}')
            logger.info(f'Received chunkhash: {received_chunkhash_str}')
            success = ex_downloading_chunkhash == received_chunkhash_str
            logger.info(f'Successful received: {success}')
            if success:
                logger.info('Congrats! You have completed the example!')
            else:
                logger.warning('Example fails. Please check the example files carefully.')
    elif Type == ACK:
        ack_num = socket.ntohl(Ack)
        if ack_num * MAX_PAYLOAD >= CHUNK_DATA_SIZE:
            # finished
            logger.info(f'Finished sending {ex_sending_chunkhash}')
            pass
        else:
            left = ack_num * MAX_PAYLOAD
            right = min((ack_num + 1) * MAX_PAYLOAD, CHUNK_DATA_SIZE)
            next_data = config.haschunks[ex_sending_chunkhash][left: right]
            # send next data
            data_pkt = P2pPacket.data(next_data, ack_num + 1)
            sock.sendto(data_pkt, from_addr)


def process_user_input(sock):
    command, chunkf, outf = input().split(' ')
    if command == 'DOWNLOAD':
        process_download(sock, chunkf, outf)
    else:
        pass


# noinspection PyShadowingNames
def peer_run(config):
    addr = (config.ip, config.port)
    sock = simsocket.SimSocket(config.identity, addr, verbose=config.verbose)

    try:
        while True:
            ready = select.select([sock, sys.stdin], [], [], 0.1)
            read_ready = ready[0]
            if len(read_ready) > 0:
                if sock in read_ready:
                    process_inbound_udp(sock)
                if sys.stdin in read_ready:
                    process_user_input(sock)
            else:
                # No pkt nor input arrives during this period
                pass
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()


if __name__ == '__main__':
    """
    -p: Peer list file, it will be in the form "*.map" like nodes.map.
    -c: Chunkfile, a dictionary dumped by pickle. It will be loaded automatically in bt_utils. The loaded dictionary has the form: {chunkhash: chunkdata}
    -m: The max number of peer that you can send chunk to concurrently. If more peers ask you for chunks, you should reply "DENIED"
    -i: ID, it is the index in nodes.map
    -v: verbose level for printing logs to stdout, 0 for no verbose, 1 for WARNING level, 2 for INFO, 3 for DEBUG.
    -t: pre-defined timeout. If it is not set, you should estimate timeout via RTT. If it is set, you should not change this time out.
        The timeout will be set when running test scripts. PLEASE do not change timeout if it set.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', type=str, help='<peerfile>     The list of all peers', default='nodes.map')
    parser.add_argument('-c', type=str, help='<chunkfile>    Pickle dumped dictionary {chunkhash: chunkdata}')
    parser.add_argument('-m', type=int, help='<maxconn>      Max # of concurrent sending')
    parser.add_argument('-i', type=int, help='<identity>     Which peer # am I?')
    parser.add_argument('-v', type=int, help='verbose level', default=0)
    parser.add_argument('-t', type=int, help="pre-defined timeout", default=0)
    args = parser.parse_args()

    config = bt_utils.BtConfig(args)
    logger.name = f'PEER{config.identity}_LOGGER'
    peer_run(config)