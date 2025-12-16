# Attaching a GPU Compute Worker on AWS to a Codabench Competition

This guide explains how to set up and attach a **GPU-enabled Codabench compute worker** running on an **AWS EC2 instance**.

---

## 1. Overview

Codabench uses **compute workers** to execute competition submissions.  
Each worker connects to a **broker URL** (defined in your Codabench admin panel) and runs submissions inside **competition Docker images**.

For GPU-based evaluations, workers must:
- Run on GPU-capable hardware (e.g. AWS `g4dn.xlarge`, `g5.xlarge`, or `p3.2xlarge`)
- Have NVIDIA drivers and CUDA-compatible Docker support
- Use the image `codalab/competitions-v2-compute-worker:gpu1.3` or a custom image based on it.

---

## 2. Launch an AWS EC2 GPU Instance

1. Open **AWS EC2 Console** → “Launch instance”
2. Choose an **Ubuntu 24.04 LTS** (64-bit x86) AMI
3. Select a **GPU instance type**, e.g.:
   - `g4dn.xlarge` (Tesla T4)
   - `g5.xlarge` (A10G)
4. Configure:
   - Storage: at least **50 GB**
   - Key pair: securely connect to instance
   - Security group: allow inbound **SSH (port 22)**
5. Launch the instance and connect via SSH (you can find 'ec2-public-ip' in instance summary->Public DNS):
   ```bash
   ssh -i your-key.pem ubuntu@<ec2-public-ip>
   ```


## 3. Install NVIDIA GPU Drivers

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y nvidia-driver-580
sudo reboot
```
After reboot:
```bash
nvidia-smi
```
You should see the GPU (e.g. Tesla T4)


## 4. Install Docker

Set up Docker's apt repository:
```bash
# Add Docker's official GPG key:
sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
```

Install Docker packages:
```bash
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Enable Docker at startup:
```bash
sudo systemctl enable docker
```
Allow the ubuntu user to use Docker without sudo:
```bash
sudo usermod -aG docker ubuntu
```
Log out and back in for the group change to take effect.


## 5. Install NVIDIA Container Toolkit

Prerequisites:
```bash
sudo apt-get update && sudo apt-get install -y --no-install-recommends curl gnupg2
```
Configure the production repository:
```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```
```bash
sudo apt-get update
```
Install the NVIDIA Container Toolkit packages:
```bash
export NVIDIA_CONTAINER_TOOLKIT_VERSION=1.18.0-1
  sudo apt-get install -y \
      nvidia-container-toolkit=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      nvidia-container-toolkit-base=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      libnvidia-container-tools=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
      libnvidia-container1=${NVIDIA_CONTAINER_TOOLKIT_VERSION}
```

Configuring Docker to use NVIDIA runtime:
```bash
sudo nvidia-ctk runtime configure --runtime=docker
```

Restart Docker:
```bash
sudo systemctl restart docker
```
This will generate or update:
```bash
/etc/docker/daemon.json
```
The JSON file now contains:
```bash
{
    "runtimes": {
        "nvidia": {
            "args": [],
            "path": "nvidia-container-runtime"
        }
    }
```

We can test the runtime manually with:
```bash
sudo docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```


## 6. Configure the Codabench Worker

Create a working directory on the EC2 host:
```bash
mkdir -p /home/ubuntu/codabench
```

Create an ```.env``` file in ```/home/ubuntu/codabench```:
```bash
BROKER_URL=<your-codabench-broker-url>
BROKER_USE_SSL=True
HOST_DIRECTORY=/home/ubuntu/codabench
```
The broker URL corresponding to the selected queue can be found on Codabench website under Admin panel->My Resources->Queues and then Actions->Copy Broker URL. The queue is to be specified in the Edit section of the competition on Codabench. 


## 7. Create ```docker-compose.yml``` for the GPU Worker

Inside ```/home/ubuntu/codabench```, create a file named ```docker-compose.yml``` and copy:
```yaml
# Codabench GPU worker (NVIDIA)
services:
    worker:
        image: codalab/competitions-v2-compute-worker:gpu1.3
        container_name: compute_worker
        volumes:
            - /home/ubuntu/codabench:/codabench
            - /var/run/docker.sock:/var/run/docker.sock
        env_file:
            - .env
        restart: unless-stopped
        #hostname: ${HOSTNAME}
        logging:
            options:
                max-size: 50m
                max-file: 3
        deploy:
            resources:
                reservations:
                    devices:
                        - driver: nvidia
                          count: all
                          capabilities:
                              - gpu
```


## 8. Start the GPU Worker

From ```/home/ubuntu/codabench```:
```bash
docker compose up -d
```
Check running containers:
```bash
docker ps
```
Check logs of the ```compute_worker``` container:
```bash
docker logs -f compute_worker
```
The compute worker container should be ready to receive submissions from Codabench.

## 9. Stop compute worker instance

First stop the container:
```bash
docker compose down
```
Then stop the EC2 instance from AWS console.

