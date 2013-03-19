'''
Created on Mar 17, 2013

@author: nino
'''
import unittest
from voom.amqp.gateway import AMQPGateway
from mock import Mock, call
from voom.bus import DefaultBus
import pika
from voom.codecs import ContentCodecRegistry
from pika.connection import Parameters
from voom.amqp.events import AMQPSenderReady, AMQPGatewayReady, AMQPDataReceived,\
    AMQPRawDataReceived
from pika.adapters.select_connection import IOLoop
from logging import basicConfig
from voom.priorities import BusPriority
from voom.gateway import GatewayShutdownCmd, GatewayMessageDecodeError
from voom.codecs.json_codec import JSONCodec
import json
from voom.context import SessionKeys
from voom.amqp.config import AMQPQueueDescriptor
from voom.decorators import receiver
import os
from tests import no_jython

basicConfig()

class Test(unittest.TestCase):
    def test_on_complete(self):
        params = Mock(spec=Parameters)
        bus = Mock(spec=DefaultBus)
        g = AMQPGateway("test_on_complete", 
                        params, 
                        [], 
                        bus,
                        Mock(spec=ContentCodecRegistry))
        
        assert len(g.spec.queues) == 1
        assert g.spec.queues[0].queue.startswith("test_on_complete")
        assert g.spec.connection_params == params
        bus.subscribe.assert_called_with(GatewayShutdownCmd, g.shutdown, BusPriority.LOW_PRIORITY)
        g._on_complete(g.spec,
                       Mock(spec=pika.connection.Connection),
                       Mock(spec=pika.channel.Channel))
        
        assert g.sender is not None
        bus.send.assert_has_calls([call(AMQPSenderReady(g.sender)),
                                   call(AMQPGatewayReady(g))])
        g.connection.ioloop = Mock(spec=IOLoop)
        g.shutdown()
        g.connection.close.assert_called_with()
        g.connection.ioloop.stop.assert_called_with()
        
    def test_on_receive_1(self):
        bus = Mock(spec=DefaultBus)
        g = AMQPGateway("test_on_complete", 
                        Mock(spec=Parameters), 
                        [], 
                        bus,
                        ContentCodecRegistry([JSONCodec()]))
        
        bus.reset_mock()
        #codec = g.supported_types_registry.get_by_content_type.return_value = Mock()
        #codec.decode.return_value = 
        properties = pika.BasicProperties(reply_to="123",
                                          content_type='application/json',
                                          content_encoding="zip",
                                          headers={'Session-Id': "abc"})
        
        data = dict(key=1)
        event = AMQPRawDataReceived(Mock(spec=pika.channel.Channel),
                                    Mock(routing_key="r"), 
                                    properties, 
                                    json.dumps(data).encode("zip"))
        
        g.on_receive(event)
        assert bus.send.call_count == 1
        calls = bus.send.call_args_list
        #bus.send.assert_called_once_with(GatewayMessageDecodeError(event, None, None))
        _call = calls[0][0]
        assert len(_call) == 2
        assert isinstance(_call[0], AMQPDataReceived), type(_call[0])

        _event = _call[0]
        context = _call[1]
        
        headers = _event.headers
        #
        assert 'Session-Id' in headers, headers
        assert headers['Reply-To'] == '123'
        assert 'User-Id' not in headers
        assert headers == context[SessionKeys.GATEWAY_HEADERS]
        
        assert _event.messages == [data]
        assert callable(context[SessionKeys.RESPONDER])
        
    def test_on_receive_2(self):
        bus = Mock(spec=DefaultBus)
        g = AMQPGateway("test_on_complete", 
                        Mock(spec=Parameters), 
                        [], 
                        bus,
                        ContentCodecRegistry([JSONCodec()]))
        
        bus.reset_mock()
        #codec = g.supported_types_registry.get_by_content_type.return_value = Mock()
        #codec.decode.return_value = 
        properties = pika.BasicProperties(reply_to="http://example.com/123",
                                          content_type='application/json',
                                          content_encoding="zip",
                                          headers={'Session-Id': "abc"})
        
        data = dict(key=1)
        event = AMQPRawDataReceived(Mock(spec=pika.channel.Channel),
                                    Mock(), 
                                    properties, 
                                    json.dumps(data).encode("zip"))
        
        g.on_receive(event)
        assert bus.send.call_count == 1
        calls = bus.send.call_args_list
        _call = calls[0][0]
        assert len(_call) == 2
        assert isinstance(_call[0], AMQPDataReceived), type(_call[0])

        _event = _call[0]
        context = _call[1]

    def test_receive_decode_error(self):
        bus = Mock(spec=DefaultBus)
        g = AMQPGateway("test_decode_error", 
                        Mock(spec=Parameters), 
                        [], 
                        bus,
                        ContentCodecRegistry([JSONCodec()]))
        
        bus.reset_mock()
        properties = pika.BasicProperties(reply_to="123",
                                          content_type='application/json',
                                          content_encoding="garbage",
                                          headers={'Session-Id': "abc"})
        
        data = dict(key=1)
        event = AMQPRawDataReceived(Mock(spec=pika.channel.Channel), 
                                    Mock(routing_key="route"),
                                    properties, 
                                    json.dumps(data).encode("zip"))
        
        g.on_receive(event)
        assert bus.send.call_count == 1
        calls = bus.send.call_args_list
        _call = calls[0][0]
        assert len(_call) == 2
        assert isinstance(_call[0], GatewayMessageDecodeError), type(_call[0])

        _event = _call[0]
        context = _call[1]
        
        assert isinstance(_event.exception, LookupError)
        assert _event.event == event        

        assert callable(context[SessionKeys.RESPONDER])

class TestRoundtrip(unittest.TestCase):
    @no_jython
    def test_1(self):
        work = AMQPQueueDescriptor("test_round_trip", declare=True, exclusive=False, auto_delete=True)
        
        g = AMQPGateway(work.queue,
                        pika.ConnectionParameters(host='localhost'),
                        [work],
                        DefaultBus(),
                        ContentCodecRegistry([JSONCodec()]))
        
        bus = g.bus
        bus.raise_errors = True
        self.msgs = []
        
        @receiver(AMQPDataReceived)
        def receives(msg):
            assert isinstance(msg, AMQPDataReceived)
            self.msgs.append(msg)
            if len(self.msgs) == 1:
                properties = pika.BasicProperties(content_type='application/json',
                                                  content_encoding='zip',
                                                  reply_to=g.return_queue.queue)
                g.send(range(0, 100), properties, exchange='', routing_key=g.return_queue.queue)
                return
            if len(self.msgs) == 2:
                assert bus.session[SessionKeys.RESPONDER]
                #print bus.session.keys()
                bus.reply(msg.messages[0])
                return
            
            bus.send(GatewayShutdownCmd())
        
        @receiver(AMQPGatewayReady)
        def on_ready(msg):
            properties = pika.BasicProperties(content_type='application/json',
                                              reply_to=g.return_queue.queue)
            g.send(range(0, 10), properties, exchange='', routing_key=work.queue)
            
        bus.register(receives)
        bus.register(on_ready)
                 
        g.run()
        assert len(self.msgs) == 3
        msg = self.msgs.pop(0)
        assert isinstance(msg, AMQPDataReceived)
        assert msg.headers['From'] == g.return_queue.queue
        assert msg.headers['Content-Type'] == 'application/json'
        assert msg.headers['Reply-To'] == g.return_queue.queue
        assert msg.headers['Routing-Key'] == work.queue
        assert msg.messages == [range(10)]
        for msg in self.msgs:
            assert isinstance(msg, AMQPDataReceived)
            assert msg.headers['From'] == g.return_queue.queue
            assert msg.headers['Content-Type'] == 'application/json'
            assert msg.headers['Content-Encoding'] == 'zip'
            assert msg.headers['Reply-To'] == g.return_queue.queue
            assert msg.headers['Routing-Key'] == g.return_queue.queue, msg.headers
            assert msg.messages == [range(100)], msg.messages
        