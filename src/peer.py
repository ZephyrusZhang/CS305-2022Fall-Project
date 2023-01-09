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
DEFAULT_TIMEOUT = 11451  # 默认的超时时限
INIT_ESTIMATED_RTT = 10000
INIT_DEV_RTT_BETA = 10000

start_time = dict()  # 用于记录测量RTT时的开始时间

cwnd = 5
base = 1  # 发送窗口的起点
next_seq_num = base + cwnd  # 发送窗口的重终点的下一个

# 接收方收到最大的max_data_pkt_seq
max_data_pkt_seq = 0


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
    ack_cnt_map[(addr, seq)] = 0
    un_acked_data_pkt_map[(addr, seq)] = packet


def get_chunk_data(hashcode, seq):
    return config.haschunks[hashcode][MAX_PAYLOAD * (seq - 1):min(MAX_PAYLOAD * seq, CHUNK_DATA_SIZE)]


def update_rtt(addr, sample_rtt):
    if addr in ESTIMATED_RTT.keys():
        assert addr in DEV_RTT.keys()
        ESTIMATED_RTT[addr] = (1 - ALPHA) * ESTIMATED_RTT[addr] + ALPHA * sample_rtt
        DEV_RTT[addr] = (1 - BETA) * DEV_RTT[addr] + BETA * abs(sample_rtt - ESTIMATED_RTT[addr])
        logger.debug(f'更新到 {addr} EstimatedRTT={ESTIMATED_RTT[addr]}, DevRTT={DEV_RTT[addr]}')
    else:
        ESTIMATED_RTT[addr] = (1 - ALPHA) * INIT_ESTIMATED_RTT + ALPHA * sample_rtt
        DEV_RTT[addr] = (1 - BETA) * INIT_DEV_RTT_BETA * abs(sample_rtt - ESTIMATED_RTT[addr])


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
    global cwnd
    global base
    global next_seq_num
    global max_data_pkt_seq

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
    global config, ex_sending_chunkhash, base, next_seq_num, max_data_pkt_seq

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
        logger.info(f'收{from_addr} *GET   * for {bytes.hex(pkt[HEADER_LEN:])}')

        # 直接发送 cwnd 个data pkt
        for i in range(base, next_seq_num):
            chunk_data = get_chunk_data(ex_sending_chunkhash, i)
            data_pkt = P2pPacket.data(chunk_data, i)
            logger.info(f'发{from_addr} *DATA  * seq {i}')
            # 发送之前处理一下，方便收到ack的时候测量rtt
            before_send_data(from_addr, i, data_pkt)
            sock.sendto(data_pkt, from_addr)

    elif Type == DATA:
        # if Seq == 2: return
        # received a DATA pkt
        # 查session list中，用addr查询hash
        ex_downloading_chunkhash = session_list[from_addr]
        # logger.warning(f'收到从{from_addr}的分段{ex_downloading_chunkhash}')
        ex_received_chunk[ex_downloading_chunkhash] += data
        logger.info(f'收{from_addr} *DATA  * seq {Seq}')

        if Seq == max_data_pkt_seq + 1:
            # send back ACK
            ack_pkt = P2pPacket.ack(Seq)
            logger.info(f'发{from_addr} *ACK   * seq {Seq}')
            sock.sendto(ack_pkt, from_addr)
            max_data_pkt_seq += 1
        else:
            # 乱序data包，ack 需要的包的前一个
            ack_pkt = P2pPacket.ack(max_data_pkt_seq)
            logger.info(f'发{from_addr} *ACK   * seq {max_data_pkt_seq}')
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
        # 打印一下窗口，观察一下
        logger.warning(f"收到ack时候 窗口 {base}-{next_seq_num - 1}")

        print("ACK")
        ack_num = Ack
        logger.info(f'收{from_addr} *ACK   * seq {ack_num}')

        # 在收到ack之后处理，得到rtt的测量值
        sample_rtt = time.time() - start_time[(from_addr, ack_num)]
        update_rtt(from_addr, sample_rtt)

        #   1.在un_acked_data_pkt_map中删除{seq:pkt}
        un_acked_data_pkt_map.pop((from_addr, ack_num))
        start_time.pop((from_addr, ack_num))
        ack_cnt_map[(from_addr, ack_num)] += 1

        #   2.查看在ack_cnt_map中记录的{seq:cnt}（如果等于3的话，重新传整个窗口，其余情况，cnt+1）
        cnt = ack_cnt_map[(from_addr, ack_num)]
        if cnt == 3:
            logger.warning(f'快速重传 整个窗口 窗口为{base}-{next_seq_num - 1}')
            for seq in range(base, next_seq_num):
                chunk_data = get_chunk_data(ex_sending_chunkhash, seq)  # 根据hash和seq构造装进包里的data
                data_pkt = P2pPacket.data(chunk_data, seq)  # 根据data构造pkt
                ack_cnt_map[(from_addr, seq)] = 0  # 这个seq的ack cnt 设置为0
                un_acked_data_pkt_map[(from_addr, seq)] = data_pkt  # 将pkt存到，已经发送但是没有ack的map里，方便后面重新传
                # 发出去包
                logger.info(f'发{from_addr} *DATA  * seq {seq}')
                sock.sendto(data_pkt, from_addr)
                before_send_data(from_addr, seq, data_pkt)

        # 收到ack的时候,检查ack的序号是不是窗口后沿
        if ack_num == base:
            logger.warning("收到低序号ack，更新窗口")
            if base + 1 <= next_seq_num: base += 1
            next_seq_num = base + cwnd
            # 注意(next_seq_num - 1)是窗口最后一个包的seq
            # 所以 (next_seq_num - 1) * MAX_PAYLOAD 不能大于 CHUNK_DATA_SIZE
            while (next_seq_num - 1) * MAX_PAYLOAD > CHUNK_DATA_SIZE:
                next_seq_num -= 1
        else:
            logger.warning("收到高序号ack，窗口不变")

        # 判断一下是否对方已经接收了ack了所有的pkt
        if ack_num * MAX_PAYLOAD >= CHUNK_DATA_SIZE:
            logger.warning(f'对方ACK了所有pkt，应该结束传输')
            return

        # 检查窗口内是否还有没发出去的pkt，如果有，则发出去
        for seq in range(base, next_seq_num):
            if (from_addr, seq) not in un_acked_data_pkt_map:  # 如果这个包不在已经发送但是还没有被ack的map里，表明还没有发出去
                chunk_data = get_chunk_data(ex_sending_chunkhash, seq)  # 根据hash和seq构造装进包里的data
                data_pkt = P2pPacket.data(chunk_data, seq)  # 根据data构造pkt
                ack_cnt_map[(from_addr, seq)] = 0  # 这个seq的ack cnt 设置为0
                un_acked_data_pkt_map[(from_addr, seq)] = data_pkt  # 将pkt存到，已经发送但是没有ack的map里，方便后面重新传
                # 发出去包
                logger.info(f'发{from_addr} *DATA  * seq {seq}')
                sock.sendto(data_pkt, from_addr)
                before_send_data(from_addr, seq, data_pkt)

        # 打印一下窗口，观察一下
        logger.warning(f"ACK 结束 窗口 {base}-{next_seq_num - 1}")


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
            logger.warning(f"time out retransmission {seq}")
            before_send_data(addr, seq, un_acked_data_pkt_map[key])
            sock.sendto(un_acked_data_pkt_map[key], addr)


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
