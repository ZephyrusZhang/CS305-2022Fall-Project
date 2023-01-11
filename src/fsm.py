import math
import time

import matplotlib.pyplot as plt

from formatter import *

logger = get_logger(__name__)


class State:
    SlowStart = 'SlowStart'
    CongestionAvoidance = 'CongestionAvoidance'


class Event:
    Timeout = 'Timeout'
    Duplicate3Ack = 'Duplicate3Ack'
    NewAck = 'NewAck'
    CwndBtSsthresh = 'CwndBtSsthresh'  # cwnd >= ssthresh


class Trigger:
    one = (State.SlowStart, Event.Timeout)
    two = (State.SlowStart, Event.Duplicate3Ack)
    three = (State.SlowStart, Event.NewAck)
    four = (State.SlowStart, Event.CwndBtSsthresh)
    five = (State.CongestionAvoidance, Event.NewAck)
    six = (State.CongestionAvoidance, Event.Timeout)
    seven = (State.CongestionAvoidance, Event.Duplicate3Ack)


class FSM:
    _TRANSITION = {
        Trigger.one: State.SlowStart,
        Trigger.two: State.SlowStart,
        Trigger.three: State.SlowStart,
        Trigger.four: State.CongestionAvoidance,
        Trigger.five: State.CongestionAvoidance,
        Trigger.six: State.SlowStart,
        Trigger.seven: State.SlowStart
    }

    def __init__(self):
        self.cwnd = 1
        self.ssthresh = 64
        self.state = State.SlowStart
        self.cwnd_record = ([time.time()], [self.cwnd])

    def update(self, event):
        trigger = (self.state, event)
        tmp_state, tmp_cwnd, tmp_ssthresh = self.state, self.cwnd, self.ssthresh
        if trigger == Trigger.one or trigger == Trigger.two or trigger == Trigger.six or trigger == Trigger.seven:
            self.ssthresh = max(math.floor(self.cwnd / 2), 2)
            # self.cwnd = 1
            self.change_cwnd_to(1)
        elif trigger == Trigger.three:
            # self.cwnd += 1
            self.change_cwnd_to(self.cwnd + 1)
        elif trigger == Trigger.four:
            pass
        elif trigger == Trigger.five:
            # self.cwnd = self.cwnd + (1 / self.cwnd)
            # self.change_cwnd_to(self.cwnd + (1 / self.cwnd))
            self.change_cwnd_to(self.cwnd + 1)
        else:
            raise ValueError('No such trigger')
        self.state = FSM._TRANSITION[trigger]
        logger.info(f'Event {event},Trigger {trigger}, State <{tmp_state} -> {self.state}>, cwnd <{tmp_cwnd} -> {self.cwnd}>, ssthresh <{tmp_ssthresh} -> {self.ssthresh}>')
        if self.cwnd >= self.ssthresh:
            self.update(Event.CwndBtSsthresh)

    def change_cwnd_to(self, value):
        self.cwnd = value
        self.cwnd_record[0].append(time.time())
        self.cwnd_record[1].append(value)

    def cwnd_visualizer(self, identification):
        plt.plot(self.cwnd_record[0], self.cwnd_record[1])
        plt.title(f'Peer-{identification} cwnd变化趋势')
        plt.xlabel('time')
        plt.ylabel('cwnd')
        plt.show()

    def get_cwnd(self):
        return math.floor(self.cwnd)
