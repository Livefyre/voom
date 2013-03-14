'''
Created on Mar 13, 2013

@author: nino
'''
from email.mime.application import MIMEApplication

try:
    import cPickle as pickle
except ImportError:
    import pickle

class PickleCodec(object):
    """
    Warning The pickle module is not intended to be secure against erroneous or 
    maliciously constructed data. Never unpickle data received from an untrusted
    or unauthenticated source.
    """
    # https://groups.google.com/forum/?fromgroups=#!topic/it.comp.lang.python/9DZKiVsGAnk
    MIME_SUBTYPE = "x-pickle-binary.python"
    
    def __init__(self, protocol=pickle.HIGHEST_PROTOCOL):
        self.protocol = protocol
    
    def supported_types(self):
        return (object, type(None))
    
    def mimetypes(self):
        return ["application/" + self.MIME_SUBTYPE]
    
    def encode_mime_part(self, obj):
        return MIMEApplication(self.encode(obj), self.MIME_SUBTYPE, protocol=str(self.protocol))
    
    def decode_mime_part(self, part):
        protocol = int(part.get_param("protocol"))
        payload = part.get_payload(decode=True)
        return self.decode(payload, protocol)
        
    def encode(self, obj):
        return pickle.dumps(obj, self.protocol)
        
    def decode(self, input, protocol=None):
        protocol = self.protocol if protocol is None else protocol
        return pickle.loads(input)