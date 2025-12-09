#!/bin/bash
# AWS EC2 初始化脚本
# 用于在 Ubuntu 22.04 上设置环境

set -e  # 遇到错误立即退出

echo "================================"
echo "开始初始化 AWS EC2 实例"
echo "================================"

# 1. 更新系统
echo "步骤 1: 更新系统包..."
sudo apt-get update
sudo apt-get upgrade -y

# 2. 安装必要的系统依赖
echo "步骤 2: 安装系统依赖..."
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    curl \
    build-essential \
    nginx

# 3. 安装 Docker (可选，如果想用 Docker 部署)
echo "步骤 3: 安装 Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
rm get-docker.sh

# 4. 安装 Docker Compose
echo "步骤 4: 安装 Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 5. 克隆项目代码
echo "步骤 5: 克隆项目代码..."
cd /home/ubuntu
if [ ! -d "uoft-assistant" ]; then
    git clone https://github.com/D1NG1/uoft-assistant.git
else
    echo "项目目录已存在，跳过克隆"
fi

cd uoft-assistant

# 6. 创建 Python 虚拟环境
echo "步骤 6: 创建 Python 虚拟环境..."
python3.11 -m venv venv
source venv/bin/activate

# 7. 安装 Python 依赖
echo "步骤 7: 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 8. 创建必要的目录
echo "步骤 8: 创建必要的目录..."
mkdir -p logs data chroma_db

# 9. 配置环境变量
echo "步骤 9: 配置环境变量..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，填入你的 GROQ_API_KEY 和其他配置"
    echo "   使用命令: nano .env"
else
    echo ".env 文件已存在"
fi

# 10. 配置防火墙
echo "步骤 10: 配置防火墙..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # FastAPI (开发用)
sudo ufw --force enable

# 11. 配置 Nginx (反向代理)
echo "步骤 11: 配置 Nginx..."
sudo tee /etc/nginx/sites-available/uoft-assistant > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/uoft-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 12. 创建 systemd 服务
echo "步骤 12: 创建 systemd 服务..."
sudo tee /etc/systemd/system/uoft-assistant.service > /dev/null <<EOF
[Unit]
Description=UofT Assistant API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/uoft-assistant
Environment="PATH=/home/ubuntu/uoft-assistant/venv/bin"
ExecStart=/home/ubuntu/uoft-assistant/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable uoft-assistant.service

echo "================================"
echo "初始化完成！"
echo "================================"
echo ""
echo "下一步操作:"
echo "1. 编辑 .env 文件: nano /home/ubuntu/uoft-assistant/.env"
echo "2. 填入 GROQ_API_KEY 和其他配置"
echo "3. 启动服务: sudo systemctl start uoft-assistant"
echo "4. 查看状态: sudo systemctl status uoft-assistant"
echo "5. 查看日志: sudo journalctl -u uoft-assistant -f"
echo ""
echo "你的应用将运行在: http://YOUR_EC2_PUBLIC_IP"
