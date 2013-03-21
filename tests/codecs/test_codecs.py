'''
Created on Mar 13, 2013

@author: nino
'''
import unittest
from voom.codecs.json_codec import MIMEJSONCodec
from voom.codecs.mime_codec import MIMEMessageCodec
from voom.codecs.pickle_codec import MIMEPickleCodec

from google.protobuf.descriptor_pb2 import FileOptions
from voom.codecs.protobuf_codec import MIMEProtobufBinaryCodec,\
    ProtobufBinaryCodec
    
import google.protobuf.descriptor_pb2
from mock import patch
import nose.tools

class TestProtobuf(unittest.TestCase):
    def test_protobuf_1(self):
        codec = ProtobufBinaryCodec()
        with patch('importlib.import_module', 
                   return_value=google.protobuf.descriptor_pb2) as mock:
            codec.get_class("foo.FileOptions")
            mock.assert_called_with("foo_pb2")
            
        nose.tools.assert_raises(TypeError, codec.decode, "stuff")
        nose.tools.assert_raises(ImportError, codec.decode, "stuff", "foo.FileOptions")


class TestMIME(unittest.TestCase):
    def test_type(self):
        assert len(MIMEMessageCodec().mimetypes()) == 1
    
    def test_json(self):
        supported = [MIMEJSONCodec()]
        self.run_it(supported, [range(0, 10)])

    def test_pickle(self):
        supported = [MIMEPickleCodec()]
        self.run_it(supported, [range(0, 10)])
        
    def test_protobuf(self):
        codec = MIMEProtobufBinaryCodec()
        codec.registry['google.protobuf.FileOptions'] = FileOptions
        supported = [codec]
        obj = FileOptions()
        obj.java_package = "com.meow"
        self.run_it(supported, [obj])
        
    def test_mixed(self):
        codec = MIMEProtobufBinaryCodec()
        codec.registry['google.protobuf.FileOptions'] = FileOptions
        supported = [MIMEJSONCodec(), codec]

        obj = FileOptions()
        obj.java_package = "com.meow"
        self.run_it(supported, [obj, {'meow': True}])


    def run_it(self, supported, objs):
        codec = MIMEMessageCodec(supported)

        addr = "where"
        headers = {'To': addr, 'Meow': 'yes'}
        msg_str = codec.encode_message(objs, headers)
        print msg_str
        _headers, parts = codec.decode_message(msg_str)
        assert len(parts) == len(objs)
        assert parts == objs, parts
        for header in headers:
            assert headers[header] == _headers[header]
