"""测试用的小工具。"""
from sim.data import load
from sim.state import State
from sim.month import Game, Hooks

D = load()


def fresh(seed=1, origin=(0, 0, 0)):
    return State.new(D, seed, origin)


def bare(seed=1):
    """只有底值、不选开局三问的状态。"""
    st = State(D)
    from sim.rng import Rng
    st.rng = Rng(seed)
    return st


class Rec(Hooks):
    """记下钩子被调用的情况。"""
    def __init__(self):
        self.calls = []

    def class_chain(self, st, chain, n): self.calls.append(('chain', chain, n))
    def book_done(self, st, bid): self.calls.append(('book_done', bid))
    def job_period(self, st, jid, good): self.calls.append(('job', jid, good))
    def outing(self, st, place): self.calls.append(('outing', place))
    def board(self, st): self.calls.append(('board', st.date))
    def film_breach(self, st): self.calls.append(('breach',))
