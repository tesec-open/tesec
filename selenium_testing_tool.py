import requests
from selenium import webdriver

recorder_clock = False
host_name = 'http://localhost:5000'#'http://1.13.160.206:7777'

def set_hostname(url):
    global host_name
    host_name = url

def recorder_start(ui_data):
    global recorder_clock, host_name
    if recorder_clock:
        return
    recorder_stop()
    re = requests.post(host_name + '/api/build', headers={'record-op': 'start'}, json={
        'attributes': ui_data
    })
    assert re.text == 'succeed'
    recorder_clock = True

def recorder_stop():
    global recorder_clock, host_name
    re = requests.post(host_name + '/api/build', headers={'record-op': 'stop'})
    assert re.text == 'succeed'
    recorder_clock = False

def recorder_finish():
    global recorder_clock, host_name
    recorder_stop()
    re = requests.post(host_name + '/api/build', headers={'record-op': 'finish'})
    assert re.text == 'succeed'

def extract_attr(ele):
    resp = {attr['name']: attr['value'] for attr in ele.get_property('attributes')}
    resp['url'] = ele.parent.current_url
    resp['text'] = ele.text
    resp['tag'] = ele.tag_name
    return resp
    
class Recorder:
    def __init__(self, ele, parent=None):
        self.ele = ele
        self.parent = parent

    def __capsulate(self, obj):
        if obj is None:
            return obj
        if type(obj).__name__ in ['int', 'str', 'float']:
            return obj
        if type(obj).__name__ == 'list':
            ret = []
            for child in obj:
                ret.append(self.__capsulate(child))
            return ret
        if type(obj).__name__ == 'dict':
            ret = {}
            for key, val in obj.items():
                ret['key'] = self.__capsulate(val)
            return ret
        return Recorder(obj, self.ele)

    def __call__(self, *args, **argv):
        global host_name
        print(self.ele.__name__)
        
        if self.ele.__name__ == 'implicitly_wait':
            self.ele(*args, **argv)
            return
        
        if not recorder_clock:
            re = requests.post(host_name + '/api/build', headers={'record-op': 'stop'})
            assert re.text == 'succeed'
            
            if not hasattr(self.parent, 'get_property'):
                re = requests.post(host_name + '/api/build', headers={'record-op': 'start'}, json={
                    'attributes': {
                        # 'args': tuple(args),
                        # 'argv': tuple(sorted(argv.items())),
                        'name': self.__name__,
                        'url': self.parent.current_url if hasattr(self.parent, 'current_url') else ''
                    }
                })
            else:
                re = requests.post(host_name + '/api/build', headers={'record-op': 'start'}, json={
                    'attributes': extract_attr(self.parent)
                })
            assert re.text == 'succeed'
        res = self.__capsulate(self.ele(*args, **argv))
        return res
    
    def __getattr__(self, name):
        return self.__capsulate(getattr(self.ele, name))
