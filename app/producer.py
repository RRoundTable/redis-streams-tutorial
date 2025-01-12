import time
from rediscluster import RedisCluster

# Redis Cluster 접속 정보
startup_nodes = [{"host": "10.0.0.1", "port": "7001"}]
rc = RedisCluster(startup_nodes=startup_nodes, decode_responses=True)

CHANNEL = "broadcast_channel"

if __name__ == "__main__":
    counter = 0
    try:
        while True:
            message = f"Broadcast message {counter}"
            # channel에 메시지 발행
            rc.publish(CHANNEL, message)
            print(f"Published: {message}")
            counter += 1
            time.sleep(3)  # 3초 간격 발행
    except KeyboardInterrupt:
        print("Broadcast Producer stopped.")
