'''
Created on Mar 2, 2013

@author: nino
'''
import urlparse

import redis
from voom.channels import Sender

class RedisChannelSender(Sender):
    """Sends a command to a redis key.
    
    redis://username:password@host/db/<cmd>/<key>
    
    e.g. redis://username:password@host/db/set/a_key
    """

    default_encoding = None
    
    _clients = {}
    def __init__(self, **extra_redis_kwargs):
        self._extra_redis_kwargs = extra_redis_kwargs
    
    def parse_address(self, address):
        parts = urlparse.urlparse(address)
        _, db, cmd, key = parts.path.split("/", 3)
        return "redis://%s/%s" % (parts.netloc, db), cmd, key

    def get_connection(self, addr):
        if addr not in self._clients:
            # the client is self pooling
            self._clients[addr] = redis.Client.from_url(addr, **self._extra_redis_kwargs)
        return self._clients[addr]

    def _send(self, address, message, mimetype):
        url, cmd, key = self.parse_address(address)
        client = self.get_connection(url)
        getattr(client, cmd)(key, message)
