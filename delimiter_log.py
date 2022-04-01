import types

import asyncio
import inspect

import logging
import concurrent.futures

import os
import contextvars
header = contextvars.ContextVar('rq-hd')

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send, Message
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.middleware.session import SessionMiddleware

import ctypes
libc = ctypes.CDLL(None)
syscall = libc.syscall
syscall_id = 0

class Node:
    def __init__(self, id):
        self.id = id
        self.ch = {}
        self.fail = None
        self.end_uis_key = set()
        self.end_uis = []

def add_child(node, res):
    if node in res:
        return res
    res.add(node)
    for key, val in node.ch.items():
        res = add_child(val, res)
    return res

def find_node(node_id: int):
    res = set()
    node = nodes[node_id]
    while node.id != 0:
        res = add_child(node, res)
        node = node.fail

    ret = []
    for ui in res:
        ret += ui.end_uis

    cnt = 0
    ret_key = set()
    for it, ui in enumerate(ret):
        key = {key: value for key, value in ui.items() if key != 'url'}
        if tuple(sorted(key.items())) in ret_key:
            continue
        ret_key.add(tuple(sorted(key.items())))
        cnt += 1
        print('The {}th possible ui-elements:'.format(cnt))
        for key in ui:
            print('  {}: {}'.format(key, ui[key]))
    print('-------------')

pre_request = ''
    
class NewCoro(asyncio.coroutines.CoroWrapper):
    def send(self, value):
        global syscall_id, syscall, pre_request
        request = header.get(None)
        if request != pre_request:
            pre_request = request
            syscall(404, syscall_id)
            syscall_id += 1
        return super().send(value)

    @property
    def cr_running(self):
        return self.gen.cr_running

async def run(request):
    global nodes, apis, mode
    current = -1
    for it, api in enumerate(apis):
        if request.method.lower() == api[0] and api[1].match(request.url.path) is not None:
            current = it
            break
        
    if current == -1:
        response = PlainTextResponse('Cannot match api', status_code=400)
        await response
        return None
    
    if not 'proxy-id' in request.cookies:
        node_id = 0
    else:
        node_id = int(request.cookies['proxy-id'])
        
    node = nodes[node_id]
    while node != None:
        if current in node.ch:
            node_id = node.ch[current].id
            break
        node = node.fail

    if node == None:
        response = PlainTextResponse('Hack', status_code=400)
        await response
        return None

    return str(node_id)
    
class HeaderMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        global loop
        if not scope['type'] in ('http', 'websocket'):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        node_id = await run(request)

        if node_id == None:
            return

        header.set(node_id)
        
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                header_value = "%s=%s; path=/; httponly" % (
                    'proxy-id', node_id
                )
                headers.append("Set-Cookie", header_value)
            await send(message)
        
        task = loop.create_task(self.app(scope, receive, send_wrapper))
        await task
        
        
def coro_deco(loop, coro):
    if header.get(None) != None:
        coro = NewCoro(coro)
    task = asyncio.Task(coro, loop=loop)
    return task

def coro_secure(app):
    global pid
    pid = str(os.getpid())
    
    @app.on_event("startup")
    def startup():
        global pid, loop

        loop = asyncio.get_running_loop()
        loop.set_task_factory(coro_deco)

        global apis, nodes, mode
    
        class CustomUnpickler(pickle.Unpickler):
            def find_class(self, module, name):
                if name == 'Node':
                    return Node
                return super().find_class(module, name)
    
        with open('./api.pk', 'rb') as load:
            apis = pickle.load(load)
        with open('./nodes.pk', 'rb') as load:
            nodes = CustomUnpickler(load).load()
        mode = 'run'
