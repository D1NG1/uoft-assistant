#!/bin/bash
# 快速部署/更新脚本
# 用于在 EC2 上更新应用

set -e

echo "================================"
echo "开始部署更新"
echo "================================"

# 进入项目目录
cd /home/ubuntu/uoft-assistant

# 1. 拉取最新代码
echo "步骤 1: 拉取最新代码..."
git pull origin main

# 2. 激活虚拟环境
echo "步骤 2: 激活虚拟环境..."
source venv/bin/activate

# 3. 更新依赖
echo "步骤 3: 更新 Python 依赖..."
pip install -r requirements.txt --upgrade

# 4. 重启服务
echo "步骤 4: 重启服务..."
sudo systemctl restart uoft-assistant

# 5. 检查服务状态
echo "步骤 5: 检查服务状态..."
sleep 3
sudo systemctl status uoft-assistant --no-pager

echo "================================"
echo "部署完成！"
echo "================================"
echo ""
echo "查看实时日志: sudo journalctl -u uoft-assistant -f"
