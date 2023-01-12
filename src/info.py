from fsm import *


class ReceiverInfo:
    def __init__(self):
        self.sending_hash = ''
        self.fsm = FSM()
        self.base = 1
        self.next_seq_num = self.base + self.fsm.get_cwnd()
        self.estimated_rtt = 999_999_999
        self.dev_rtt = 999_999_999
        self.ack_cnt = dict()
        self.un_acked_data_pkt = dict()
        self.timers = dict()


class SenderInfo:
    def __init__(self):
        self.downloading_hash = ''
        self.max_data_pkt_seq = 0

