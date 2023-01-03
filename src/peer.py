import logging
import os
import re
import sys
import time

from config import *
from formatter import CustomFormatter
from packet import P2pPacket

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import select
import util.simsocket as simsocket
import struct
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

# types
types = ['WHOHAS', 'IHAVE', 'GET', 'DATA', 'ACK', 'DENIED']

# TODO: 通过维护session list来和不同peer通信
# session list 里面存的是(地址：20位hash)的dictionary
# 方便后面每次收到一个包的时候，从地址-->hash-->分段data
session_list = dict()

ack_cnt_map = {}
un_acked_data_pkt_map = {}

# 发送data的时候
#   1.在ack_cnt_map中记录{(addr,seq):0}
#   2.在un_acked_data_pkt_map中记录{(addr,seq):pkt}
# 收到ack的时候
#   1.在un_acked_data_pkt_map中删除{(addr,seq):pkt}
#   2.查看在ack_cnt_map中记录的{(addr,seq):cnt}（如果大于等于3的话，重新传下一个，cnt重置成1，如果没超过的话，cnt+1）

ESTIMATED_RTT = dict()
DEV_RTT = dict()
ALPHA = 0.125
BETA = 0.25
DEFAULT_TIMEOUT = 11.4  # 默认的超时时限

start_time = dict()  # 用于记录测量RTT时的开始时间
unacked_map = dict()
ack_count = dict()


def before_send_data(addr, seq, packet):
    """
        发送DATA包前调用该函数。用于开始RTT的测量等一系列事宜

        Parameters
        ----------
        addr : tuple
            目的地的地址
        seq : int
            要发的DATA包的序列号
        packet : bytes
            要发的包
    """
    start_time[(addr, seq)] = time.time()
    ack_count[(addr, seq)] = 0
    unacked_map[(addr, seq)] = packet


def after_receive_ack(addr, ack):
    """
        收到ACK包后调用该函数。用于完成RTT的测量等事宜

        Parameters
        ----------
        addr : tuple
            源地址
        ack : int
            收到的包的ACK号
    """
    sample_rtt = time.time() - start_time[(addr, ack)]
    update_rtt(addr, sample_rtt)
    ack_count[(addr, ack)] += 1
    unacked_map.pop((addr, ack))
    start_time.pop((addr, ack))


def update_rtt(addr, sample_rtt):
    if addr in ESTIMATED_RTT.keys():
        assert addr in DEV_RTT.keys()
        ESTIMATED_RTT[addr] = (1 - ALPHA) * ESTIMATED_RTT[addr] + ALPHA * sample_rtt
        DEV_RTT[addr] = (1 - BETA) * DEV_RTT[addr] + BETA * abs(sample_rtt - ESTIMATED_RTT[addr])
    else:
        ESTIMATED_RTT[addr] = ALPHA * sample_rtt
        DEV_RTT[addr] = BETA * abs(sample_rtt - ESTIMATED_RTT[addr])


def timeout_interval_of(addr) -> float:
    if addr in ESTIMATED_RTT.keys():
        assert addr in DEV_RTT.keys()
        return ESTIMATED_RTT[addr] + 4 * DEV_RTT[addr]
    return DEFAULT_TIMEOUT


def process_download(sock, chunkfile, outputfile):
    """
    if DOWNLOAD is used, the peer will keep getting files until it is done
    """
    global ex_output_file
    global ex_received_chunk
    global ex_downloading_chunkhash

    ex_output_file = outputfile
    # Step 1: read chunkhash to be downloaded from chunkfile
    download_hashes = bytes()
    with open(chunkfile, 'r') as cf:
        for line in cf:
            index, datahash_str = line.strip().split(" ")
            download_hashes += bytes.fromhex(datahash_str)
            # 本地存档先置空
            ex_downloading_chunkhash = datahash_str
            ex_received_chunk[ex_downloading_chunkhash] = bytes()
    # Step 2: create whohas pkt
    whohas_pkt = P2pPacket.whohas(download_hashes)
    # 按照长度为20分割开，方便展示log
    download_list = re.findall('.{40}', bytes.hex(download_hashes))
    # Step 3: send to every peer
    for peer in config.peers:
        id = int(peer[0])
        ip = peer[1]
        port = int(peer[2])
        if id != config.identity:
            logger.info(f'发({ip}, {port}) *WHOHAS* for {download_list}')
            sock.sendto(whohas_pkt, (ip, port))


def process_inbound_udp(sock):
    # Receive pkt
    global config, ex_sending_chunkhash

    pkt, from_addr = sock.recvfrom(BUF_SIZE)
    Magic, Team, Type, hlen, plen, Seq, Ack = struct.unpack(PACKET_FORMAT, pkt[:HEADER_LEN])
    data = pkt[HEADER_LEN:]
    if Type == WHOHAS:
        # received an WHOHAS pkt
        # see what chunk the sender has
        whohas_chunk_hash = data[0:]
        # bytes to hex_str
        chunkhash_str = bytes.hex(whohas_chunk_hash)
        # request_hashes是peer请求的所有chunk的hash
        request_hashes = re.findall('.{40}', chunkhash_str)
        logger.info(f'收{from_addr} *WHOHAS* for {request_hashes}')
        logger.debug(f'{list(config.haschunks.keys())}')
        for hash in request_hashes:
            if hash in list(config.haschunks.keys()):
                ex_sending_chunkhash = hash
                # send back IHAVE pkt
                ihave_pkt = P2pPacket.ihave(bytes.fromhex(hash))
                logger.info(f'发{from_addr} *IHAVE * for {hash}')
                sock.sendto(ihave_pkt, from_addr)
    elif Type == IHAVE:
        # received an IHAVE pkt
        # see what chunk the sender has
        get_chunk_hash = data[:20]
        logger.info(f'收{from_addr} *IHAVE * for {bytes.hex(get_chunk_hash)}')
        # send back GET pkt
        get_pkt = P2pPacket.get(get_chunk_hash)
        logger.info(f'发{from_addr} *GET   * for {bytes.hex(get_chunk_hash)}')
        sock.sendto(get_pkt, from_addr)
        # 在这里加入session list
        session_list[from_addr] = bytes.hex(get_chunk_hash)
        # logger.warning(f'收到ihave，地址是{from_addr}，hash是{bytes.hex(get_chunk_hash)}')
        # logger.warning(session_list)
    elif Type == GET:
        # received a GET pkt
        chunk_data = config.haschunks[ex_sending_chunkhash][:MAX_PAYLOAD]
        logger.info(f'收{from_addr} *GET   * for {bytes.hex(pkt[HEADER_LEN:])}')
        # send back DATA
        data_pkt = P2pPacket.data(chunk_data, 1)
        logger.info(f'发{from_addr} *DATA  * seq {1}')
        sock.sendto(data_pkt, from_addr)
        ack_cnt_map[(from_addr, 1)] = 0
        un_acked_data_pkt_map[(from_addr, 1)] = data_pkt
    elif Type == DATA:
        # received a DATA pkt
        # 查session list中，用addr查询hash
        ex_downloading_chunkhash = session_list[from_addr]
        # logger.warning(f'收到从{from_addr}的分段{ex_downloading_chunkhash}')
        ex_received_chunk[ex_downloading_chunkhash] += data
        logger.info(f'收{from_addr} *DATA  * seq {Seq}')
        # send back ACK
        ack_pkt = P2pPacket.ack(Seq)
        logger.info(f'发{from_addr} *ACK   * seq {Seq}')
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
        ack_num = Ack
        logger.info(f'收{from_addr} *ACK   * seq {ack_num}')

        # 收到ack的时候
        #   1.在un_acked_data_pkt_map中删除{seq:pkt}
        un_acked_data_pkt_map.pop((from_addr, ack_num))
        #   2.查看在ack_cnt_map中记录的{seq:cnt}（如果大于等于3的话，重新传下一个，cnt重置成1，如果没超过的话，cnt+1）
        cnt = ack_cnt_map[(from_addr, ack_num)]
        if cnt >= 3:
            logger.warning(f'快速重传 data pkt seq {ack_num + 1}')
            data_pkt = un_acked_data_pkt_map[(from_addr, ack_num + 1)]
            sock.sendto(data_pkt, from_addr)
            ack_cnt_map[(from_addr, ack_num + 1)] = 0
            ack_cnt_map[(from_addr, ack_num)] = 1
        else:
            ack_cnt_map[(from_addr, ack_num)] = cnt + 1

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
            logger.info(f'发{from_addr} *DATA  * seq {ack_num + 1}')
            sock.sendto(data_pkt, from_addr)
            ack_cnt_map[(from_addr, ack_num + 1)] = 0
            un_acked_data_pkt_map[(from_addr, ack_num + 1)] = data_pkt


def process_user_input(sock):
    command, chunkf, outf = input().split(' ')
    if command == 'DOWNLOAD':
        process_download(sock, chunkf, outf)
    else:
        pass


def check_timeout(sock):
    for key, start in start_time.items():
        addr, seq = key
        if time.time() - start > timeout_interval_of(addr):
            before_send_data(addr, seq, unacked_map[key])
            sock.sendto(unacked_map[key], addr)


# noinspection PyShadowingNames
def peer_run(config):
    addr = (config.ip, config.port)
    sock = simsocket.SimSocket(config.identity, addr, verbose=config.verbose)

    try:
        while True:
            check_timeout(sock)
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
