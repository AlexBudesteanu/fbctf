from threading import Thread
from flask import redirect

class ConsumerThread(Thread):

    def __init__(self, queue):
        super(ConsumerThread, self).__init__()
        self.queue = queue

    def run(self):
        while True:
            tag = queue.get()
            redirect("localhost:8888/pull?tag={}".format(tag))