import time
import uuid
from rediscluster import RedisCluster

# Redis Cluster 접속 정보 (환경에 맞게 수정)
startup_nodes = [{"host": "10.0.0.1", "port": "7001"}]
rc = RedisCluster(startup_nodes=startup_nodes, decode_responses=True)

STREAM_KEY = "mystream"


def add_task(task_data):
    """
    고유 id와 작업 데이터를 포함한 메시지를 스트림에 추가합니다.
    """
    task_id = str(uuid.uuid4())
    # 메시지 필드 : id와 data (원하는 다른 정보도 추가 가능)
    message_id = rc.xadd(STREAM_KEY, {"task_id": task_id, "data": task_data})
    print(f"Task {task_id} added as message {message_id}")


if __name__ == "__main__":
    counter = 0
    try:
        while True:
            add_task(f"Sample data {counter}")
            counter += 1
            time.sleep(3)
    except KeyboardInterrupt:
        print("Producer stopped.")
