'''
Created on Mar 13, 2013

@author: nino
'''

import google.protobuf.message
import imp
from email.mime.application import MIMEApplication
from voom.codecs import TypeCodec


class ProtobufBinaryCodec(TypeCodec):
    # https://groups.google.com/d/msg/protobuf/VAoJ-HtgpAI/mzWkRlIptBsJ
    MIME_SUBTYPE = "vnd.google.protobuf"

    def __init__(self, message_type=None):
        self.message_type = message_type
        self.registry = {}

    def supported_types(self):
        return (google.protobuf.message.Message,)

    def mimetypes(self):
        return ["application/" + self.MIME_SUBTYPE]

    def encode(self, obj, include_type=True):
        s = obj.SerializeToString()
        if include_type:
            s = u"%s;%s" % (obj.DESCRIPTOR.full_name, s)
        return s

    def decode(self, input, message_type=None):
        """Decodes a protobuf message. Message type is derived from:
        1) the input parameter
        2) the instance's message_type attribute
        3) encoded in the input as 'messagetype;protobuf_raw_data'
        """
        pos = input.find(";")
        if pos == -1:
            message_type = message_type or self.message_type
            if not message_type:
                raise Exception("no message type")
            pos = 0
        else:
            message_type = input[0:pos]
            pos += 1

        klass = self.get_class(message_type)
        obj = klass()
        obj.ParseFromString(input[pos:])
        return obj

    def get_class(self, type):
        """Resolve a python class from the protobuf full_name"""
        if type in self.registry:
            return self.registry[type]

        mod_name, cls_name = type.rsplit('.', 1)
        mod_name += '_pb2'

        mod = self.import_module(mod_name)
        klass = getattr(mod, cls_name)
        return klass

    def import_module(self, mod_name):
        parts = mod_name.split('.')
        mod_info = imp.find_module(parts[0])
        for part in parts[1:]:
            mod_info = imp.find_module(part, [mod_info[1]])
        return imp.load_module(mod_name, *mod_info)


class MIMEProtobufBinaryCodec(ProtobufBinaryCodec):
    def encode_part(self, obj):
        return MIMEApplication(self.encode(obj, include_type=False), self.MIME_SUBTYPE, proto=obj.DESCRIPTOR.full_name)

    def decode_part(self, part):
        msg_type = part.get_param('proto')
        return self.decode(part.get_payload(decode=True), msg_type or self.message_type)


