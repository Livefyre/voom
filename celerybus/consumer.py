import collections
import logging
from celery.task import Task
from celery.app.task import TaskType
from .decorators import make_async_task

class ConsumerMeta(TaskType):
    def __new__(cls, name, bases, attrs):        
        msgs = attrs.get('_receiver_of', set())
        receiving = attrs.get('_receivers', collections.defaultdict(list))
        for attr in attrs.values():
            if hasattr(attr, '_receiver_of'):
                msgs.update(attr._receiver_of)
                for m in attr._receiver_of:
                    receiving[m].append(attr)
                    
        attrs['_receiver_of'] = msgs
        attrs['_receivers'] = receiving
        attrs['_celery_task_kwargs'] = attrs.pop("celery_task_kwargs", {})
        
        cls = super(ConsumerMeta, cls).__new__(cls, name, bases, attrs)
        return cls



class MessageConsumer(Task):
    """A message consumer, which could process many types of messages.  To make it async, decorate it AsyncConsumer.
    
    E.g.

    @AsyncConsumer
    class Foo(MessageConsumer):
        queue = "some_celery_queue"
        
        @consumer(some_message)
        def handle_some_message(self, msg): ...
        
        @consumer(other_message, one_more_message)
        def handle_stuff(self, msg): ...
        
    Bus.register(Foo)
    
    Bus.send(some_message())
    """
    
    __metaclass__ = ConsumerMeta
    
    def run(self, msg):
        self(msg)

    def __call__(self, message):
        exception = None
        try:
            self.pre_dispatch(message)
            self.dispatch(message)
        except Exception, e:
            exception = e
            self.on_dispatch_failure(message, e)
        finally:
            self.post_dispatch(message, exception)

    def dispatch(self, message):
        for receiver in self._receivers[type(message)]:
            receiver(self, message)
    
    def pre_dispatch(self, message):
        pass
    
    def post_dispatch(self, message, exception):
        pass
    
    def on_dispatch_failure(self, msg, exception):
        logging.getLogger(self.__class__.__name__).error("Failed to process %s: %s", msg, exception)


def AsyncConsumer(cls):
    return make_async_task(cls, cls._receiver_of, **cls._celery_task_kwargs)


def consumer(*messages):
    """Decorator for a function that identifies it as a consumer of a collection of messages.
    
    E.g.:
    
    class Foo(Consumer):
        @consumer(str)
        def strPrinter(self, ...)
            pass
    
    """
    def consuming(func):
        func._receiver_of = set(messages)
        return func
    return consuming