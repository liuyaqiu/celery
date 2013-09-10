from celery import current_app, task, uuid
from celery.five import Queue, range
from celery.worker.consumer import Consumer
from celery.worker.job import Request
from celery.concurrency.solo import TaskPool
from celery.app.amqp import TASK_BARE
from time import time
from librabbitmq import Message
import socket
import sys

@task(accept_magic_kwargs=False)
def T():
    pass

tid = uuid()
P = TaskPool()
hostname = socket.gethostname()
task = {'task': T.name, 'args': (), 'kwargs': {}, 'id': tid, 'flags': 0}
app = current_app._get_current_object()

def on_task(req):
    req.execute_using_pool(P)

def on_ack(*a): pass


m = Message(None, {}, {}, task)

x = Consumer(on_task, hostname=hostname, app=app)
x.update_strategies()
name = T.name
ts = time()
from celery.datastructures import AttributeDict
from celery.app.trace import trace_task_ret
request = AttributeDict(
                {'called_directly': False,
                 'callbacks': [],
                 'errbacks': [],
                 'chord': None}, **task)
for i in range(100000):
    trace_task_ret(T, tid, (), {}, request)
print(time() - ts)

