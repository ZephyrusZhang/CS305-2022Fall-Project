import os
import re
import sys

from config import *
from info import *
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
logger = get_logger(__name__)

# types
types = ['WHOHAS', 'IHAVE', 'GET', 'DATA', 'ACK', 'DENIED']

# 发送data的时候
#   1.在ack_cnt_map中记录{(addr,seq):0}
#   2.在un_acked_data_pkt_map中记录{(addr,seq):pkt}
# 收到ack的时候
#   1.在un_acked_data_pkt_map中删除{(addr,seq):pkt}
#   2.查看在ack_cnt_map中记录的{(addr,seq):cnt}（如果大于等于3的话，重新传下一个，cnt重置成1，如果没超过的话，cnt+1）

ALPHA = 0.125
BETA = 0.25
DEFAULT_TIMEOUT = 999_999_999  # 默认的超时时限
INIT_ESTIMATED_RTT = 999_999_999
INIT_DEV_RTT_BETA = 999_999_999
b = True

sending_map = dict()
# key: addr
# val: receiver_info
# (
# hash, base, next_seq_num, fsm, ESTIMATED_RTT, DEV_RTT
# ack_cnt{seq;num}, un_acked_data_pkt{seq:pkt}, timers{seq:time}
# )
# 收到第一个GET的时候，加入
# 收到最后一个ACK的时候，移除
receiving_map = dict()
# key: addr
# val: { hash, max_data_pkt_seq }
# 收到IHAVE的时候，加入
# 收到顺序到来的最后一个DATA的时候，移除

# receiving hash set存放作为接收方，正在下载的所有任务，用于判断是否完成下载并生成文件
receiving_hash_set = set()


# val: hash
# 在收到IHAVE的时候，加入
# 收到一个完整的包的时候
#   1.移除该任务
#   2.判断是否完成所有任务，如果是，清空receiving list，完成下载，生成文件


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
    receiver = sending_map[addr]
    receiver.timers[seq] = time.time()
    # 处理一下这些包的ack cnt和存档pkt
    receiver.ack_cnt[seq] = 0
    receiver.un_acked_data_pkt[seq] = packet


def get_chunk_data(hashcode, seq):
    return config.haschunks[hashcode][MAX_PAYLOAD * (seq - 1):min(MAX_PAYLOAD * seq, CHUNK_DATA_SIZE)]


def get_receive_data(hashcode, seq):
    return ex_received_chunk[hashcode][MAX_PAYLOAD * (seq - 1):min(MAX_PAYLOAD * seq, CHUNK_DATA_SIZE)]


def update_rtt(addr, sample_rtt):
    receiver = sending_map[addr]
    ESTIMATED_RTT = receiver.estimated_rtt
    DEV_RTT = receiver.dev_rtt
    if ESTIMATED_RTT != 999_999_999:
        if DEV_RTT != 999_999_999:
            ESTIMATED_RTT = (1 - ALPHA) * ESTIMATED_RTT + ALPHA * sample_rtt
            DEV_RTT = (1 - BETA) * DEV_RTT + BETA * abs(sample_rtt - ESTIMATED_RTT)
            logger.debug(f'更新到 {addr} EstimatedRTT={ESTIMATED_RTT}, DevRTT={DEV_RTT}')
    else:
        ESTIMATED_RTT = (1 - ALPHA) * INIT_ESTIMATED_RTT + ALPHA * sample_rtt
        DEV_RTT = (1 - BETA) * INIT_DEV_RTT_BETA * abs(sample_rtt - ESTIMATED_RTT)
    receiver.estimated_rtt = ESTIMATED_RTT
    receiver.dev_rtt = DEV_RTT


def timeout_interval_of(addr) -> float:
    if config.timeout != 999_999_999: return config.timeout
    receiver = sending_map[addr]
    ESTIMATED_RTT = receiver.estimated_rtt
    DEV_RTT = receiver.dev_rtt
    if ESTIMATED_RTT != 999_999_999:
        if DEV_RTT != 999_999_999:
            return ESTIMATED_RTT + 4 * DEV_RTT
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
    global config, ex_sending_chunkhash, ex_downloading_chunkhash, receiving_map, receiving_hash_set, sending_map, b

    pkt, from_addr = sock.recvfrom(BUF_SIZE)
    Magic, Team, Type, hlen, plen, Seq, Ack = struct.unpack(PACKET_FORMAT, pkt[:HEADER_LEN])
    data = pkt[HEADER_LEN:]
    # print(config.timeout)
    # print(timeout_interval_of(from_addr))
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

        # 加入到receive list, hash set
        receiving_hash_set.add(bytes.hex(get_chunk_hash))
        receiving_map[from_addr] = SenderInfo()
        receiving_map[from_addr].downloading_hash = bytes.hex(get_chunk_hash)
        receiving_map[from_addr].max_data_pkt_seq = 0

        # send back GET pkt
        get_pkt = P2pPacket.get(get_chunk_hash)
        logger.info(f'发{from_addr} *GET   * for {bytes.hex(get_chunk_hash)}')
        sock.sendto(get_pkt, from_addr)
    elif Type == GET:
        # received a GET pkt
        hash = bytes.hex(pkt[HEADER_LEN:])
        logger.info(f'收{from_addr} *GET   * for {hash}')
        # 加入到发送列表中
        receiver = ReceiverInfo()
        sending_map[from_addr] = receiver
        receiver.sending_hash = hash
        # 查出来现在的窗口
        base = receiver.base
        next_seq_num = receiver.next_seq_num
        # 直接发送 cwnd 个data pkt
        for i in range(base, next_seq_num):
            chunk_data = get_chunk_data(hash, i)
            data_pkt = P2pPacket.data(chunk_data, i)
            logger.info(f'发{from_addr} *DATA  * seq {i}')
            # 发送之前处理一下，方便收到ack的时候测量rtt
            before_send_data(from_addr, i, data_pkt)
            sock.sendto(data_pkt, from_addr)
    elif Type == DATA:
        # if b:
        #     if Seq == 2:
        #         b = False
        #         return
        #         # received a DATA pkt

        # 检查是否已经收完了来自这个peer的chunk
        if from_addr in receiving_map.keys():
            ex_downloading_chunkhash = receiving_map[from_addr].downloading_hash
            # 检查data seq的位置
            # 1.比该收到的seq小
            if Seq < receiving_map[from_addr].max_data_pkt_seq + 1:
                # send back ACK
                ack_pkt = P2pPacket.ack(Seq)
                logger.info(f'发{from_addr} *ACK   * seq {Seq}')
                sock.sendto(ack_pkt, from_addr)
            # 2.等于该收到的seq
            if Seq == receiving_map[from_addr].max_data_pkt_seq + 1:
                receiving_map[from_addr].max_data_pkt_seq += 1
                ex_downloading_chunkhash = receiving_map[from_addr].downloading_hash
                if data == get_receive_data(ex_downloading_chunkhash, Seq):
                    logger.warning('已经从别的peer那里收到了这个hash-seq的data，直接抛弃')
                else:
                    logger.warning('第一次收到了这个hash-seq的data，加到下载文件的末尾')
                    ex_received_chunk[ex_downloading_chunkhash] += data
                    logger.info(f'收{from_addr} *DATA  * seq {Seq}')
                # send back ACK
                ack_pkt = P2pPacket.ack(Seq)
                logger.info(f'发{from_addr} *ACK   * seq {Seq}')
                sock.sendto(ack_pkt, from_addr)
            # 3.大于该收到的seq
            if Seq > receiving_map[from_addr].max_data_pkt_seq + 1:
                # 乱序data包，ack 需要的包的前一个
                logger.warning(
                    f'乱序到来的包 data {Seq},直接丢弃，并且ack最大号码{receiving_map[from_addr].max_data_pkt_seq}')
                ack_pkt = P2pPacket.ack(receiving_map[from_addr].max_data_pkt_seq)
                logger.info(f'发{from_addr} *ACK   * seq {receiving_map[from_addr].max_data_pkt_seq}')
                sock.sendto(ack_pkt, from_addr)

        # see if finished
        if len(ex_received_chunk[ex_downloading_chunkhash]) == CHUNK_DATA_SIZE:
            # 从receiving list中移除这个任务
            receiving_map.pop(from_addr)
            receiving_hash_set.remove(ex_downloading_chunkhash)
            # finished downloading this chunkdata!
            # dump your received chunk to file in dict form using pickle

            # 比对这个hash是不是对的
            # The following things are just for illustration, you do not need to print out in your design.
            sha1 = hashlib.sha1()
            sha1.update(ex_received_chunk[ex_downloading_chunkhash])
            received_chunkhash_str = sha1.hexdigest()
            logger.info(f'Expected chunkhash: {ex_downloading_chunkhash}')
            logger.info(f'Received chunkhash: {received_chunkhash_str}')
            success = ex_downloading_chunkhash == received_chunkhash_str
            logger.info(f'是否成功下载： {success}')
            if success:
                logger.info(f'Congrats! You have receive the right data for {received_chunkhash_str}')
            else:
                logger.warning(f'Fail! You have receive the wrong data for {received_chunkhash_str}')
            # fsm.cwnd_visualizer(config.identity)

            # add to this peer's haschunk:
            config.haschunks[ex_downloading_chunkhash] = ex_received_chunk[ex_downloading_chunkhash]

            # 检查下载任务是否全部完成，只有完成了所有下载，才能生成result文件
            if len(receiving_hash_set) == 0:
                logger.info(f'完成了所有下载，生成文件')
                receiving_map = dict()

                with open(ex_output_file, "wb") as wf:
                    pickle.dump(ex_received_chunk, wf)
                # you need to print "GOT" when finished downloading all chunks in a DOWNLOAD file
                logger.info(f'GOT {ex_output_file}')
                pass
            else:
                logger.info(f'完成了部分下载，剩余任务为{receiving_map}')
                pass
    elif Type == ACK:
        ack_num = Ack
        # 先搞清楚这个ack从那里来的，receiver是谁
        receiver = sending_map[from_addr]
        fsm = receiver.fsm
        fsm.update(Event.NewAck)
        # 查出来现在的窗口
        # base = receiver.base
        # next_seq_num = receiver.next_seq_num

        # 第零件事，判断一下是否对方已经接收了ack了所有的pkt
        if ack_num * MAX_PAYLOAD >= CHUNK_DATA_SIZE:
            logger.warning(f'{from_addr} ACK了所有pkt，应该结束传输')
            # 将这个人从sending list中移除
            sending_map.pop(from_addr)
            logger.warning(f'剩余发送任务为{sending_map}')
            # 关闭所有的定时器
            receiver.timers = dict()
            receiver.fsm.cwnd_visualizer(config.identity)
            return

        if from_addr in sending_map.keys():
            ex_sending_chunkhash = sending_map[from_addr].sending_hash

        # 第一件事，先检查收到的ack是不是在发送窗口内
        logger.warning(
            f'收到了ACK {ack_num}，当前窗口是[{receiver.base}-{receiver.next_seq_num - 1}]({receiver.next_seq_num - receiver.base})')
        # 在窗口内，检查是否是base
        if ack_num in range(receiver.base, receiver.next_seq_num):
            # print('在窗口内')
            # 如果是base，先ack它，再更新窗口
            if ack_num == receiver.base:
                # 先ack它
                receiver.ack_cnt[ack_num] += 1
                receiver.un_acked_data_pkt.pop(ack_num)
                # 更新rtt
                sample_rtt = time.time() - receiver.timers[ack_num]
                update_rtt(from_addr, sample_rtt)
                # 关闭这个data包的定时器
                receiver.timers.pop(ack_num)
                # 更新窗口
                receiver.base += 1
                receiver.next_seq_num = receiver.base + fsm.get_cwnd()
                # 注意(next_seq_num - 1)是窗口最后一个包的seq
                # 所以 (next_seq_num - 1) * MAX_PAYLOAD 不能大于 CHUNK_DATA_SIZE
                while (receiver.next_seq_num - 1) * MAX_PAYLOAD > CHUNK_DATA_SIZE:
                    receiver.next_seq_num -= 1
                logger.warning(
                    f'**更新** 窗口为[{receiver.base}-{receiver.next_seq_num - 1}]({receiver.next_seq_num - receiver.base})')
                # 更新窗口之后，检查窗口内是否有没有 被发出去的分组
                # 在窗口里，就是in range(base, next_seq_num)
                # 没有发出去，就是不在un_acked_data_pkt_map里面
                # 因为发出去之前会调用before函数，加入到un_acked_data_pkt_map中
                for i in range(receiver.base, receiver.next_seq_num):
                    if i not in receiver.un_acked_data_pkt:
                        i_data = get_chunk_data(ex_sending_chunkhash, i)
                        i_pkt = P2pPacket.data(i_data, i)
                        before_send_data(from_addr, i, i_pkt)
                        sock.sendto(i_pkt, from_addr)
                        # 发完之后，处理一下 ack cnt 和 un acked map
                        receiver.ack_cnt[i] = 0
                        receiver.un_acked_data_pkt[i] = i_pkt
                        # 记录发送信息
                        logger.warning(f'更新窗口时，发送data {i}')

            # 如果不是base，直接抛弃这个ack
            else:
                logger.warning(
                    f'**抛弃** 窗口为[{receiver.base}-{receiver.next_seq_num - 1}]({receiver.next_seq_num - receiver.base})')

        # 如果不在窗口里面，先ack它，再检查是否是ack 3次，需要重新传
        else:
            # 先ack它
            receiver.ack_cnt[ack_num] += 1
            # 再检查是否需要重传
            if receiver.ack_cnt[ack_num] == 3:
                print('窗口左边收到三个冗余ack，重传整个窗口')
                fsm.update(Event.Duplicate3Ack)
                for i in range(receiver.base, receiver.next_seq_num):
                    i_data = get_chunk_data(ex_sending_chunkhash, i)
                    i_pkt = P2pPacket.data(i_data, i)
                    before_send_data(from_addr, i, i_pkt)
                    sock.sendto(i_pkt, from_addr)
                    # 发完之后，处理一下 ack cnt 和 un acked map
                    receiver.ack_cnt[i] = 0
                    receiver.un_acked_data_pkt[i] = i_pkt
                    # 记录发送信息
                    logger.warning(f'快速重传时，发送data {i}')
            pass


def process_user_input(sock):
    command, chunkf, outf = input().split(' ')
    if command == 'DOWNLOAD':
        process_download(sock, chunkf, outf)
    else:
        pass


def check_timeout(sock):
    for addr in sending_map.keys():
        for seq in sending_map[addr].timers.keys():
            if time.time() - sending_map[addr].timers[seq] > timeout_interval_of(addr):
                sending_map[addr].fsm.update(Event.Timeout)
                logger.warning(f"{sending_map[addr].timers[seq]} time out retransmission {seq}")
                before_send_data(addr, seq, sending_map[addr].un_acked_data_pkt[seq])
                sock.sendto(sending_map[addr].un_acked_data_pkt[seq], addr)


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
    parser.add_argument('-t', type=int, help="pre-defined timeout", default=5)
    args = parser.parse_args()

    config = bt_utils.BtConfig(args)
    logger.name = f'PEER{config.identity}_LOGGER'
    peer_run(config)
