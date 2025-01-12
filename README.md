# redis-streams-tutorial


## 베이스라인: RabbitMQ

ACK설정, Message Persistence에 따라서 메세지 유실이 발생할 수 있습니다.
- 설정이 다소 복잡할 수 있습니다.

큐 동기화 지연 문제를 가지고 있습니다.
- Master Node와 Replica Node간의 동기화 지연이 발생할 수 있습니다.

RabbitMQ는 Cluster구성시 Master Node를 Single로 운영합니다. 따라서 Single Master Node의 한계점을 가집니다.
- Master node가 장애로 인해 중단되기 전에 replication이 완료되지 않았다면, 데이터 손실이 발생할 수 있습니다.
- Master node가 다운되면 slave 중 하나를 새로운 master로 승격해야 하며, 이 과정에서 downtime이 발생할 수 있습니다.


## 제안: Redis Stream

Redis는 비교적 설정이 간단한 편이고 Shard기반 Multi Master를 제공합니다. 따라서 부하를 분산시킬 수 있으며 Master 오류시 문제를 최소화하고 데이터 손실을 최소화 할 수 있습니다.
Redis로 처리하기 힘든 수준의 부하라면 Kafka를 제안드릴 수 있을 것 같습니다. 다만, On-Premise 배포 특성상 Redis로도 충분한 부하일 것으로 예상되어 Redis를 먼저 제안드리게되었습니다.

### 설정의 복잡도

Redis 자체가 비교적 간단한 설정 방식을 가지며, Stream 관련 명령(XADD, XREADGROUP, XACK 등) 역시 직관적입니다.
추가 브로커 없이 Redis 인스턴스(또는 클러스터)에서 곧바로 스트림 기능을 사용할 수 있으므로 구성 난이도가 낮습니다.

RDB(주기적 스냅샷)와 AOF(Append Only File) 옵션을 통해 메시지 유실을 최소화할 수 있습니다.
Redis는 기본적으로 인메모리 구조이지만, 필요에 따라 영속성(Persistence) 관련 파라미터를 간단히 조정하여 원하는 수준의 신뢰성을 확보할 수 있습니다.

Redis Streams의 컨슈머 그룹은 XACK 명령어를 사용해 메시지 처리가 완료되었음을 간단히 알릴 수 있으며, 미처리 메시지(ACK가 되지 않은 메시지)를 재할당할 수 있는 구조를 제공합니다.
RabbitMQ의 ACK, NACK 설정과 달리, Redis Streams에서 컨슈머 그룹 기반으로 ACK/재처리 로직을 구현하는 과정이 좀 더 단순화되어 있습니다.

### Master Replica 동기화

Redis는 클러스터 모드(Sharding)와 Sentinel을 활용한 자동 장애 감지 및 Failover 시스템을 갖추고 있습니다.
클러스터 구성 시, 각 샤드가 독립적인 키 스페이스를 담당해 부하가 분산되므로, 한 노드에 집중되는 부하가 상대적으로 줄어드는 이점이 있습니다.

Redis의 Replica는 master-slave 구조로, 비동기 또는 반동기 복제를 수행하며, 일반적으로 Mirror Queue 대비 구조가 단순합니다.
동기화 지연이 완전히 없어지는 것은 아니지만, Redis 내부 로직이 단순해 운영 및 모니터링이 상대적으로 용이하고 문제가 발생해도 빠르게 파악하기 쉽습니다.

Redis Streams는 인메모리 기반이어서, 장애 복구 후에 정상 노드(혹은 새 마스터)가 컨슈머 그룹 상태를 빠르게 되찾고, ACK되지 않은 메시지를 신속히 재할당할 수 있습니다.
Redis Sentinel과 연동하면 장애 발생 시점을 탐지하고 즉시 자동으로 마스터 교체를 진행하므로, 복구 지연 시간이 상대적으로 짧은 편입니다.


### 샤딩(Shard) 기반 다중 마스터

![](https://redis.io/wp-content/uploads/2022/07/Cluster-Architecture-Diagram-Outline-01.svg?&auto=webp&quality=85,75&width=1200)

Redis Cluster는 여러 샤드 각각에 마스터-슬레이브(Replica)를 구성하여, 전체적으로 다수의 마스터가 분산되어 운영됩니다.
특정 노드 장애 시, 해당 노드의 Replica 중 하나가 빠르게 승격됨으로써 부분적인 다운타임만 발생하며, 다른 샤드는 정상 동작을 유지합니다.

Redis Sentinel 혹은 Cluster는 자동으로 마스터를 감지하고 Failover를 수행해줍니다.
장애 시점에 따른 일부 데이터(메시지) 손실 가능성은 여전히 존재할 수 있지만, Failover 속도가 상대적으로 빠르고, RDB/AOF를 활용해 유실 범위를 줄일 수 있습니다.

Redis Cluster는 키를 해시 슬롯으로 분산 저장하므로, 특정 노드 장애가 전체 스트림 운영에 치명타가 될 가능성을 줄여줍니다.
RabbitMQ처럼 하나의 큐 마스터에 모든 메시지가 집중되지 않으므로, 부하 분산 및 점진적 확장(노드 증설)이 용이합니다.

Reference: https://redis.io/technology/redis-enterprise-cluster-architecture/


## Tutorial

```
docker compose up -d
```

Create redis cluster

```
docker exec -it redis-1 redis-cli -p 7001 --cluster create 10.0.0.11:7001 10.0.0.12:7002 10.0.0.13:7003 10.0.0.14:7004 10.0.0.15:7005 10.0.0.16:7006 --cluster-replicas 1 --cluster-yes
```

Produce message
```
docker-compose exec producer python /usr/local/cluster-tester/producer.py  
```

Consume message
```
docker-compose exec consumer python /usr/local/cluster-tester/consumer.py  
```