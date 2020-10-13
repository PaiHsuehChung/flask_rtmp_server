import os, sys
import redis
import traceback
import time


sys.path.append(os.path.abspath(os.path.join(".", "utils")))
from log_handler.log_lab import get_logger


REDIS_SERVER_IP = os.environ.get('REDIS_SERVER_IP', 'localhost')
REDIS_SERVER_PORT = os.environ.get('REDIS_SERVER_PORT', 6379)
REDIS_SERVER_DB_NUM = os.environ.get('REDIS_SERVER_DB_NUM', 0)



class RedisHandler():
    def __init__(self):
        self.logger = get_logger()
        self.pool = None
        self.redis = None
        self.connect_to_redis()

    def connect_to_redis(self):
        self.pool = redis.ConnectionPool(host=REDIS_SERVER_IP, port=REDIS_SERVER_PORT, db=REDIS_SERVER_DB_NUM, decode_responses=True)
        self.redis = redis.StrictRedis(connection_pool=self.pool)
        self.redis.config_set('notify-keyspace-events', 'KAE')
        # self.redis.flushdb()

        self.pubsub = self.redis.pubsub()
        self.pubsub.psubscribe(**{f"__keyevent@{REDIS_SERVER_DB_NUM}__:expired": self.expired_notification})
        self.pubsub.run_in_thread(sleep_time=0.1)

        self.logger.info('redis server connected successful.')

    def get_redis_client(self):
        return self.redis


    def expired_notification(self, msg):
        print(msg)







if __name__ == "__main__":
    redis_connection = RedisHandler()
    redis_worker = redis_connection.get_redis_client()

    redis_worker.set("Test", "1")
    print(redis_worker.get("Test"))
