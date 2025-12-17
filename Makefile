#  __  __  _____ _______ _____
# |  \/  |/ ____|__   __/ ____|
# | \  / | (___    | | | |  __
# | |\/| |\___ \   | | | | |_ |
# | |  | |____) |  | | | |__| |
# |_|  |_|_____/   |_|  \_____|

GEN_DIR=generator
DOCKER_DIR=docker-images
PYTHON=python3
CONFIG?=config.yaml

.PHONY: default
default: ipv4 images

# -----------------------------------------------
# DOCKER IMAGES
# -----------------------------------------------

.PHONY: images mstg_service mstg_router mstg_fw mstg_switch
.PHONY: images_clt mstg_service_clt mstg_router_clt mstg_ioam_collector mstg_fw mstg_switch

images: mstg_router mstg_service mstg_fw mstg_switch

images_clt: mstg_router_clt mstg_service_clt mstg_ioam_collector mstg_fw mstg_switch

mstg_service: $(DOCKER_DIR)/service/Dockerfile $(CONFIG)
	@echo ""
	@echo "Building Docker image for service"
	@echo "Using config file $(CONFIG)"
	cp $(CONFIG) $(DOCKER_DIR)/service/config.yaml
	docker build -t $@ -f $< $(DOCKER_DIR)/service

mstg_service_clt: $(DOCKER_DIR)/service/Dockerfile_clt $(CONFIG)
	@echo ""
	@echo "Building Docker image for service with CLT"
	@echo "Using config file $(CONFIG)"
	cp $(CONFIG) $(DOCKER_DIR)/service/config.yaml
	docker build -t $@ -f $< $(DOCKER_DIR)/service

mstg_router: $(DOCKER_DIR)/router/Dockerfile
	@echo ""
	@echo "Building Docker image for router"
	@echo "Using config file $(CONFIG)"
	docker build -t $@ -f $< $(DOCKER_DIR)/router

mstg_router_clt: $(DOCKER_DIR)/router/Dockerfile_clt
	@echo ""
	@echo "Building Docker image for router with CLT"
	docker build -t $@ -f $< $(DOCKER_DIR)/router

mstg_fw: $(DOCKER_DIR)/fw/Dockerfile
	@echo ""
	@echo "Building Docker image for firewall"
	docker build -t $@ -f $< $(DOCKER_DIR)/fw

mstg_switch: $(DOCKER_DIR)/switch/Dockerfile
	@echo ""
	@echo "Building Docker image for switch"
	docker build -t $@ -f $< $(DOCKER_DIR)/switch

mstg_ioam_collector: $(DOCKER_DIR)/ioam-collector/Dockerfile $(DOCKER_DIR)/ioam-collector/*.go
	@echo ""
	@echo "Building Docker image for IOAM collector"
	docker build -t $@ $(DOCKER_DIR)/ioam-collector

# -----------------------------------------------
# GENERATOR - DOCKER COMPOSE
# -----------------------------------------------

.PHONY: ipv6 ipv6_https ipv6_jaeger ipv6_jaeger_https ipv6_ioam ipv6_ioam_jaeger
.PHONY: ipv4 ipv4_https ipv4_jaeger ipv4_jaeger_https
.PHONY: clt clt_https

ipv6: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv6"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6

ipv6_https: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv6"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --https

ipv6_jaeger: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv6"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --jaeger

ipv6_ioam: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv6 with IOAM (no CLT)"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --ioam

ipv6_ioam_jaeger: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv6 with IOAM (no CLT)"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --ioam --jaeger

ipv6_jaeger_https: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv6"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --jaeger --https

ipv4: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv4"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 4

ipv4_https: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv4"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 4 --https

ipv4_jaeger: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv4"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 4 --jaeger

ipv4_jaeger_https: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv4"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 4 --jaeger --https

clt: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv6 with CLT"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --clt --jaeger

clt_https: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating the docker compose for IPv6 with CLT"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --clt --jaeger --https

# -----------------------------------------------
# GENERATOR - KUBERNETES
# -----------------------------------------------

.PHONY: k8s_ipv6 k8s_ipv6_https k8s_ipv6_jaeger k8s_ipv6_jaeger_https
.PHONY: k8s_ipv4 k8s_ipv4_https k8s_ipv4_jaeger k8s_ipv4_jaeger_https
.PHONY: k8s_clt k8s_clt_https

k8s_ipv6: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating configurations for Kubernetes"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --kubernetes

k8s_ipv6_https: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating configurations for Kubernetes"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --kubernetes --https

k8s_ipv6_jaeger: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating configurations for Kubernetes"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --kubernetes --jaeger

k8s_ipv6_jaeger_https: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating configurations for Kubernetes"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --kubernetes --jaeger --https

k8s_ipv4: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating configurations for Kubernetes"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 4 --kubernetes

k8s_ipv4_https: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating configurations for Kubernetes"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 4 --kubernetes --https

k8s_ipv4_jaeger: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating configurations for Kubernetes"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 4 --kubernetes --jaeger

k8s_ipv4_jaeger_https: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating configurations for Kubernetes"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 4 --kubernetes --jaeger --https

k8s_clt: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating configurations for Kubernetes"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --kubernetes --clt --jaeger

k8s_clt_https: $(GEN_DIR)/*.py $(CONFIG)
	@echo ""
	@echo "Generating configurations for Kubernetes"
	$(PYTHON) $(GEN_DIR)/generator.py --config $(CONFIG) --ip 6 --kubernetes --clt --jaeger --https

# -----------------------------------------------
# UTILITIES
# -----------------------------------------------

.PHONY: clean start stop restart
.PHONY: k8s_start k8s_stop kind_add_images
.PHONY: mstg_help mstg_tests

clean:
	rm docker-compose.yaml || true
	docker rmi -f mstg_service 2>/dev/null || true
	docker rmi -f mstg_service_clt 2>/dev/null || true
	docker rmi -f mstg_router 2>/dev/null || true
	docker rmi -f mstg_router_clt 2>/dev/null || true
	docker rmi -f mstg_ioam_collector 2>/dev/null || true
	docker rmi -f mstg_fw 2>/dev/null || true

start:
	docker compose up --force-recreate --remove-orphans --detach
	@chmod +x commands.sh && sudo ./commands.sh || true
	@echo ""
	@echo "All microservices are running."
	@grep -q jaegertracing/all-in-one docker-compose.yaml && echo "Go to http://localhost:16686 for the Jaeger UI." || true

stop:
	docker compose down --remove-orphans --volumes -t 0
	@echo ""
	@echo "All microservices have been stopped."

restart: stop start
	@echo "Restarted"

# commands.sh is executed for external images
k8s_start: kind_add_images
	kubectl apply -f k8s_configs
	sleep 5
	@chmod +x commands.sh && bash commands.sh || true
	@echo "All pods and services have been deployed"

k8s_stop:
	kubectl delete --grace-period 1 -f k8s_configs
	@echo "All pods and services have been stopped"

kind_add_images: images images_clt
	@echo ""
	@echo "Adding the Docker images to the Kind cluster"
	kind load docker-image --name meshnet mstg_service
	kind load docker-image --name meshnet mstg_service_clt
	kind load docker-image --name meshnet mstg_router
	kind load docker-image --name meshnet mstg_router_clt
	kind load docker-image --name meshnet mstg_ioam_collector
	kind load docker-image --name meshnet mstg_fw

mstg_help: $(GEN_DIR)/*.py
	$(PYTHON) $(GEN_DIR)/generator.py --help

mstg_tests: $(GEN_DIR)/*.py
	cd $(GEN_DIR) && pytest
