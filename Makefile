
redis-cluster:
	docker compose up -d
	docker exec -it redis-1 redis-cli -p 7001 --cluster create 10.0.0.11:7001 10.0.0.12:7002 10.0.0.13:7003 10.0.0.14:7004 10.0.0.15:7005 10.0.0.16:7006 --cluster-replicas 1 --cluster-yes

redis-cluster-down:
	docker compose down

producer:
	docker-compose exec producer python /usr/local/cluster-tester/producer.py

consumer:
	docker-compose exec consumer python /usr/local/cluster-tester/consumer.py