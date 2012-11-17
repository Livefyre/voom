from collections import namedtuple

MessageEnvelope = namedtuple("Message", ["body", "request"])

class RequestContext(object):
    def __init__(self, headers):
        self._headers = {}
        if headers:
            self._headers.update(headers)
    
    def add_header(self, key, value):
        self._headers['key'] = value
        
    def __getitem__(self, key):
        return self._headers[key]