import time
import threading

from helpers.loggers import get_logger

logger = get_logger(__file__)


class WordSender(threading.Thread):
    def __init__(self, chat_id: int, delay_time: int, target=None, args=()):
        super().__init__(target=target, args=args)
        self.pause_cond = threading.Condition(threading.Lock())
        self.is_stopped = False
        self.chat_id = chat_id
        self.delay_time = delay_time

    def pause(self):
        # If in sleep, we acquire immediately, otherwise we wait for thread
        # to release condition. In race, worker will still see self.word_sender_paused
        # and begin waiting until it's set back to False
        self.pause_cond.acquire()

    def resume(self):
        # Notify so thread will wake after lock released
        self.pause_cond.notify()
        # Now release the lock
        self.pause_cond.release()

    def stop(self):
        self.is_stopped = True
