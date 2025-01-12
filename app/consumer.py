import time
import threading
from rediscluster import RedisCluster

# Redis Cluster 접속 정보
startup_nodes = [{"host": "10.0.0.1", "port": "7001"}]
rc = RedisCluster(startup_nodes=startup_nodes, decode_responses=True)

CHANNEL = "broadcast_channel"


def process_broadcast(message):
    """
    메시지 처리 함수
    """
    print(f"[{threading.current_thread().name}] Received: {message}")


def consumer():
    pubsub = rc.pubsub()
    # 채널 구독
    pubsub.subscribe(CHANNEL)
    print("Subscribed to broadcast channel.")

    for item in pubsub.listen():
        # item 형태 예시: {'type': 'message', 'pattern': None, 'channel': 'broadcast_channel', 'data': '...'}
        if item and item.get("type") == "message":
            process_broadcast(item.get("data"))


if __name__ == "__main__":
    # 여러 consumer 스레드 실행 (예제: 2개)
    consumer_threads = []
    for i in range(2):
        t = threading.Thread(
            target=consumer, daemon=True, name=f"BroadcastConsumer-{i}"
        )
        t.start()
        consumer_threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Broadcast Consumer stopped.")
