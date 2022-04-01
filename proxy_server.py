import uuid
import logging
import re, sys, requests, pickle, time
from flask import Flask, request, Response

def create_app():
    app = Flask(__name__)
    return app

app = create_app()

def forward(request, uid):
    headers = {key: value for (key, value) in request.headers if key != 'Host'}
    headers['proxy-id'] = uid
    url = request.url.replace(request.host_url, 'http://remote_host:remote_port/')
    cookies = {x: y for (x, y) in request.cookies.items() if x != 'proxy_id'}
    data = request.get_data()
    re = requests.request(
        request.method, url=url, data=data, headers=headers,
        cookies=cookies, allow_redirects=False
    )
    excluded_headers = [
        'content-encoding', 'content-length', 'transfer-encoding', 'connection'
    ]
    headers = [(name, value) for (name, value) in re.raw.headers.items()
               if name.lower() not in excluded_headers]
    return Response(re.content, re.status_code, headers)

mode = ''
apis = []
all_apis = []
current_apis = []
ui_attr = None
record_start = False

class Node:
    def __init__(self, id):
        self.id = id
        self.ch = {}
        self.fail = None
        self.end_uis_key = set()
        self.end_uis = []

def build_automation():
    print('building automation...')
    rt = Node(0)
    nodes = [rt]
    
    for apis, attrs in all_apis:
        now = rt
        for api in apis:
            if not api in now.ch:
                now.ch[api] = Node(len(nodes))
                nodes.append(now.ch[api])
            now = now.ch[api]
        key = {key: value for key, value in attrs.items() if key != 'url'}
        if not tuple(sorted(key.items())) in now.end_uis_key:
            now.end_uis.append(attrs)
            now.end_uis_key.add(tuple(sorted(key.items())))

    for node in nodes:
        for key, val in node.ch.items():
            tmp = node
            while tmp.fail != None:
                if key in tmp.fail.ch:
                    val.fail = tmp.fail.ch[key]
                    break
                tmp = tmp.fail
            if val.fail is None:
                val.fail = rt

    with open('./nodes.pk', 'wb') as dump:
        pickle.dump(nodes, dump)
    print('done.')

def build(request):
    global apis, all_apis, current_apis, record_start, ui_attr
    for key, val in request.headers:
        if key.lower() == 'record-op':
            print(key, val)
            if val == 'start':
                ui_attr = request.get_json()['attributes']
                record_start = True
                current_apis = []
            elif val == 'stop':
                record_start = False
                if len(current_apis) != 0:
                    all_apis.append((current_apis, ui_attr))
                    print(current_apis)
                current_apis = []
            else:
                build_automation()
                all_apis = []
                current_apis = []
                record_start = False
            return Response('succeed', 200)

    if record_start:
        current = -1
        for it, api in enumerate(apis):
            if request.method.lower() == api[0] and ((api[1].match(request.path + '/') is not None) or (api[1].match(request.path) is not None)):
                current = it
                break
        if current == -1:
            print('Cannot match api', request.path, request.method)
            return forward(request, str(uuid.uuid4()))
            # return Response('Cannot match api', 400)
        print(current, request.method, request.path, file=sys.stderr)
        current_apis.append(current)
            
    return forward(request, str(uuid.uuid4()))

def run(request):
    global nodes, apis
    current = -1
    for it, api in enumerate(apis):
        if request.method.lower() == api[0] and api[1].match(request.path) is not None:
            current = it
            break
        
    if current == -1:
        print('ban', '??', file=sys.stderr)
        return Response('Cannot match api', 400)
    
    if not 'proxy_id' in request.cookies:
        node_id = 0
    else:
        node_id = int(request.cookies['proxy_id'])
        
    node = nodes[node_id]
    while node != None:
        if current in node.ch:
            node_id = node.ch[current].id
            break
        node = node.fail

    if node == None:
        # print('ban', current, api[2], file=sys.stderr)
        return Response('Hack', 400)

    uid = str(uuid.uuid4())
    # print(uid, node_id, api[2], file=sys.stderr)
    # find_node(node_id)
    # with open('log', 'a+') as logger:
    # print(uid, node_id, api[2], file=logger)
    global logger
    logger.warn('%s %s %s', uid, node_id, api[2])
    
    resp = forward(request, uid)
    resp.set_cookie('proxy_id', str(node_id))
    return resp

@app.before_request
def proxy():
    if mode == 'build':
        return build(request)
    elif mode == 'run':
        return run(request)

'''
@app.after_request
def after(response):
    # print(response.status, file=sys.stderr)
    # print(response.headers, file=sys.stderr)
    # print(response.get_data(), file=sys.stderr)
    return response
'''

logs = []

def query_init():
    global logs
    with open('log', 'r') as inp:
        lines = inp.readlines()
        for line in lines:
            time, id, _ = line.split(' ')
            logs.append(((time), int(id)))

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
        print('The {}th possible elements:'.format(cnt))
        for key in ui:
            print('  {}: {}'.format(key, ui[key]))
    print('-------------')

import json
import argparse

def startup():
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

    import os
    if not os.path.exists('./request_log'):
        os.makedirs('request_log')
    global logger
    pid = str(os.getpid())
    logger = logging.getLogger('request-log')
    fh = logging.FileHandler('request_log/' + str(pid) + '_request.log')
    logger.addHandler(fh)
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

if __name__ != '__main__':
    startup()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['build', 'run', 'query'])
    parser.add_argument('-p', '--path', default='./openapi.json')
    args = parser.parse_args()

    mode = args.action
    
    if mode == 'build':
        with open(args.path, 'r') as load:
            doc = json.load(load)
            for api, val in doc['paths'].items():
                api_ = api
                for method in val.keys():
                    api = api_
                    api = '^{}$'.format(api)
                    while api.find('{') != -1:
                        lft = api.find('{')
                        rgt = api.find('}')
                        if rgt < lft:
                            break
                        api = api[:lft] + '([^/])+' + api[rgt+1:]
                    apis.append((method.lower(), re.compile(api), api_))
        with open('./api.pk', 'wb') as dump:
            pickle.dump(apis, dump)
    else:
        with open('./api.pk', 'rb') as load:
            apis = pickle.load(load)
        with open('./nodes.pk', 'rb') as load:
            nodes = pickle.load(load)

    if mode == 'query':
        # query_init()
        import code as interactor
        interactor.interact(local={'find_node': find_node, 'nodes': nodes, 'apis': apis})
        
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
        
    app.run(host='0.0.0.0', port=5000)
