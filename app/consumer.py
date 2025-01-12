import time
import threading
from rediscluster import RedisCluster

# Redis Cluster 접속 정보 (환경에 맞게 수정)
startup_nodes = [{"host": "10.0.0.1", "port": "7001"}]
rc = RedisCluster(startup_nodes=startup_nodes, decode_responses=True)

STREAM_KEY = "mystream"
CONSUMER_GROUP = "mygroup"
CONSUMER_NAME = "consumer_1"  # 각 워커마다 고유 consumer 이름 사용
IDLE_TIMEOUT = 30000  # 재처리 대상으로 간주할 최대 idle 시간 (밀리초, 예: 30초)
RECLAIM_INTERVAL = 5  # 재처리 확인 간격 (초)


def create_consumer_group():
    """
    Consumer group 생성 (존재하지 않으면 생성)
    """
    try:
        # "$"부터 시작하면 이후 추가되는 메시지만 받게 됨
        rc.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="$", mkstream=True)
        print(f"Consumer group '{CONSUMER_GROUP}' created.")
    except Exception as e:
        # 그룹이 이미 존재하는 경우 예외가 발생하므로 무시
        if "BUSYGROUP" in str(e):
            print(f"Consumer group '{CONSUMER_GROUP}' already exists.")
        else:
            print(f"Error creating consumer group: {e}")


def process_task(message_id, task):
    """
    작업을 처리하는 함수 (실제 비즈니스 로직 구현)
    """
    task_id = task.get("task_id")
    data = task.get("data")
    print(
        f"[{threading.current_thread().name}] Processing task {task_id} ({message_id}): {data}"
    )
    # 모의 작업 처리
    time.sleep(2)
    return True


def consumer():
    while True:
        try:
            # 블록킹 모드로 스트림에서 메시지 읽기 (최대 1개, 10초 대기)
            messages = rc.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME, {STREAM_KEY: ">"}, count=1, block=10000
            )
            if not messages:
                continue
            # messages 예시: [(stream_key, [(message_id, {field: value, ...}), ...])]
            for stream, msgs in messages:
                for message_id, data in msgs:
                    # 실제 작업 처리
                    success = process_task(message_id, data)
                    if success:
                        # ACK 보내기: 메시지 처리 완료
                        rc.xack(STREAM_KEY, CONSUMER_GROUP, message_id)
                        print(
                            f"Task {data.get('task_id')} with message id {message_id} ACKed."
                        )
                    else:
                        print(
                            f"Task {data.get('task_id')} with message id {message_id} FAILED. Not ACKed!"
                        )
        except Exception as e:
            print("Consumer error:", e)
            time.sleep(1)


def reclaim_pending():
    """
    pending 상태의 메시지를 주기적으로 확인하여, idle 시간이 IDLE_TIMEOUT 초과된 메시지를 재할당합니다.
    """
    while True:
        try:
            # XPENDING: 그룹의 pending 메시지 요약을 가져옴
            pending_info = rc.xpending_range(
                STREAM_KEY, CONSUMER_GROUP, min="-", max="+", count=10
            )
            for item in pending_info:
                message_id = item["message_id"]
                consumer = item["consumer"]
                idle = int(item["idle"])  # 메시지가 idle 상태인 시간 (밀리초)
                if idle >= IDLE_TIMEOUT:
                    # 메시지 재할당 (현재 consumer로 claim)
                    claimed = rc.xclaim(
                        STREAM_KEY,
                        CONSUMER_GROUP,
                        CONSUMER_NAME,
                        min_idle_time=IDLE_TIMEOUT,
                        message_ids=[message_id],
                    )
                    if claimed:
                        print(
                            f"Reclaimed message {message_id} (idle for {idle}ms) for {CONSUMER_NAME}."
                        )
        except Exception as e:
            print("Reclaim error:", e)
        time.sleep(RECLAIM_INTERVAL)


if __name__ == "__main__":
    # 그룹이 없으면 생성 (여러 consumer가 동시에 실행되는 환경에서는 최초 한 번만 수행)
    create_consumer_group()

    # consumer 스레드 실행 (예: 여러 워커)
    consumer_threads = []
    for i in range(2):
        t = threading.Thread(target=consumer, name=f"Consumer_{i}")
        t.start()
        consumer_threads.append(t)

    # 재처리(재할당) 스레드 실행
    reclaim_thread = threading.Thread(
        target=reclaim_pending, daemon=True, name="Reclaimer"
    )
    reclaim_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Consumer stopped.")
