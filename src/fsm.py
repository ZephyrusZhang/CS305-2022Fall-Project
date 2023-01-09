import math


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

    def update(self, event):
        trigger = (self.state, event)
        if trigger == Trigger.one or trigger == Trigger.two or trigger == Trigger.six or trigger == Trigger.seven:
            self.ssthresh = max(math.floor(self.cwnd / 2), 2)
            self.cwnd = 1
        elif trigger == Trigger.three:
            self.cwnd += 1
        elif trigger == Trigger.four:
            pass
        elif trigger == Trigger.five:
            self.cwnd = math.floor((self.cwnd + 1) / self.cwnd)
        else:
            raise ValueError('No such trigger')
        self.state = FSM._TRANSITION[trigger]
