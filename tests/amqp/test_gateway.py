import unittest
from voom.amqp.gateway import AMQPGateway
from mock import Mock, call
from voom.bus import VoomBus
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

basicConfig()

class Test(unittest.TestCase):
    def test_on_complete(self):
        params = Mock(spec=Parameters)
        bus = Mock(spec=VoomBus)
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
        bus = Mock(spec=VoomBus)
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
        bus = Mock(spec=VoomBus)
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
        bus = Mock(spec=VoomBus)
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

        