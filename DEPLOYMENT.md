# AWS EC2 部署指南

完整的 AWS EC2 Free Tier + Groq API 部署教程

---

## 📋 目录

1. [前置准备](#前置准备)
2. [创建 AWS EC2 实例](#创建-aws-ec2-实例)
3. [部署应用](#部署应用)
4. [配置域名（可选）](#配置域名可选)
5. [监控和维护](#监控和维护)
6. [故障排除](#故障排除)

---

## 前置准备

### 1. 注册 AWS 账户

- 访问 [AWS](https://aws.amazon.com)
- 注册账户（需要信用卡，但 Free Tier 12 个月免费）
- 完成身份验证

### 2. 获取 Groq API 密钥

- 访问 [Groq Console](https://console.groq.com)
- 注册并创建 API Key
- 保存密钥（格式：`gsk_...`）

### 3. 准备项目代码

```bash
# 推送代码到 GitHub
git push origin main

# 确认 .env 文件在 .gitignore 中（不要推送密钥！）
```

---

## 创建 AWS EC2 实例

### 步骤 1: 启动 EC2 实例

1. **登录 AWS Console**
   - 进入 [EC2 Dashboard](https://console.aws.amazon.com/ec2/)

2. **点击 "Launch Instance"**

3. **配置实例：**

   **名称和标签**
   ```
   Name: uoft-assistant
   ```

   **应用程序和操作系统映像 (AMI)**
   ```
   - 选择: Ubuntu Server 22.04 LTS
   - 架构: 64-bit (x86)
   ```

   **实例类型**
   ```
   - 选择: t2.micro (Free Tier eligible)
   - 1 vCPU, 1 GiB Memory
   ```

   **密钥对（登录）**
   ```
   - 创建新密钥对
   - 名称: uoft-assistant-key
   - 类型: RSA
   - 格式: .pem (Mac/Linux) 或 .ppk (Windows)
   - 下载并保存密钥文件
   ```

   **网络设置**
   ```
   ✅ 允许来自互联网的 SSH 流量
   ✅ 允许来自互联网的 HTTP 流量
   ✅ 允许来自互联网的 HTTPS 流量
   ```

   **配置存储**
   ```
   - 大小: 30 GiB (Free Tier 最大)
   - 卷类型: gp3 (General Purpose SSD)
   ```

4. **点击 "Launch Instance"**

5. **等待实例状态变为 "Running"**

### 步骤 2: 配置安全组

1. 进入 **EC2 > Security Groups**
2. 找到实例的安全组，点击编辑入站规则
3. 确保包含以下规则：

| 类型 | 协议 | 端口范围 | 源 | 说明 |
|------|------|----------|-----|------|
| SSH | TCP | 22 | 0.0.0.0/0 | SSH 访问 |
| HTTP | TCP | 80 | 0.0.0.0/0 | HTTP 流量 |
| HTTPS | TCP | 443 | 0.0.0.0/0 | HTTPS 流量 |
| 自定义 TCP | TCP | 8000 | 0.0.0.0/0 | FastAPI (开发) |

### 步骤 3: 连接到 EC2 实例

#### Windows 用户（使用 PuTTY）:

1. 下载并安装 [PuTTY](https://www.putty.org/)
2. 使用 PuTTYgen 转换 .pem 到 .ppk 文件
3. 在 PuTTY 中：
   - Host Name: `ubuntu@YOUR_EC2_PUBLIC_IP`
   - Port: 22
   - Connection > SSH > Auth: 选择你的 .ppk 密钥

#### Mac/Linux 用户:

```bash
# 设置密钥权限
chmod 400 uoft-assistant-key.pem

# SSH 连接
ssh -i uoft-assistant-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

---

## 部署应用

### 方法 1: 使用自动化脚本（推荐）

连接到 EC2 后：

```bash
# 1. 下载初始化脚本
curl -O https://raw.githubusercontent.com/YOUR_USERNAME/uoft-assistant/main/setup_ec2.sh

# 2. 添加执行权限
chmod +x setup_ec2.sh

# 3. 运行初始化脚本
./setup_ec2.sh

# 4. 编辑环境变量
nano /home/ubuntu/uoft-assistant/.env

# 在 .env 中设置:
# GROQ_API_KEY=你的Groq密钥
# API_KEY=生成一个强密码
# ALLOWED_ORIGINS=http://YOUR_EC2_PUBLIC_IP

# 保存并退出 (Ctrl+X, Y, Enter)

# 5. 启动应用
sudo systemctl start uoft-assistant

# 6. 检查状态
sudo systemctl status uoft-assistant

# 7. 查看实时日志
sudo journalctl -u uoft-assistant -f
```

### 方法 2: 手动部署

<details>
<summary>点击展开手动部署步骤</summary>

```bash
# 1. 更新系统
sudo apt-get update && sudo apt-get upgrade -y

# 2. 安装 Python 和依赖
sudo apt-get install -y python3.11 python3.11-venv python3-pip git nginx

# 3. 克隆代码
cd /home/ubuntu
git clone https://github.com/YOUR_USERNAME/uoft-assistant.git
cd uoft-assistant

# 4. 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 5. 安装依赖
pip install -r requirements.txt

# 6. 配置环境变量
cp .env.example .env
nano .env  # 编辑配置

# 7. 创建目录
mkdir -p logs data chroma_db

# 8. 测试运行
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 如果测试成功，按 Ctrl+C 停止，然后按照方法1配置 systemd 服务
```

</details>

---

## 验证部署

### 1. 检查应用状态

```bash
# 查看服务状态
sudo systemctl status uoft-assistant

# 查看日志
sudo journalctl -u uoft-assistant -f

# 测试 API
curl http://localhost:8000/health
```

### 2. 浏览器访问

打开浏览器，访问：
```
http://YOUR_EC2_PUBLIC_IP
```

应该能看到聊天界面！

### 3. 测试问答功能

在聊天界面输入：
```
What is the grading scheme for MAT235?
```

应该能收到基于 PDF 内容的回答。

---

## 配置域名（可选）

### 1. 获取域名

- 在 Namecheap、GoDaddy 或 AWS Route 53 购买域名
- 例如：`uoft-assistant.com`

### 2. 配置 DNS

在域名提供商处添加 A 记录：
```
Type: A
Name: @
Value: YOUR_EC2_PUBLIC_IP
TTL: 3600
```

### 3. 配置 Nginx

```bash
# 编辑 Nginx 配置
sudo nano /etc/nginx/sites-available/uoft-assistant

# 修改 server_name
server_name uoft-assistant.com www.uoft-assistant.com;

# 重启 Nginx
sudo systemctl restart nginx
```

### 4. 配置 HTTPS (Let's Encrypt)

```bash
# 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 获取 SSL 证书
sudo certbot --nginx -d uoft-assistant.com -d www.uoft-assistant.com

# 测试自动续期
sudo certbot renew --dry-run
```

---

## 监控和维护

### 常用命令

```bash
# 查看服务状态
sudo systemctl status uoft-assistant

# 启动服务
sudo systemctl start uoft-assistant

# 停止服务
sudo systemctl stop uoft-assistant

# 重启服务
sudo systemctl restart uoft-assistant

# 查看实时日志
sudo journalctl -u uoft-assistant -f

# 查看最近100行日志
sudo journalctl -u uoft-assistant -n 100

# 查看系统资源
htop
```

### 更新应用

```bash
# 方法 1: 使用部署脚本
cd /home/ubuntu/uoft-assistant
./deploy.sh

# 方法 2: 手动更新
cd /home/ubuntu/uoft-assistant
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart uoft-assistant
```

### 备份数据

```bash
# 备份向量数据库
tar -czf chroma_db_backup_$(date +%Y%m%d).tar.gz chroma_db/

# 备份日志
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/

# 下载到本地
scp -i uoft-assistant-key.pem ubuntu@YOUR_EC2_PUBLIC_IP:/home/ubuntu/uoft-assistant/*.tar.gz ./
```

---

## 故障排除

### 问题 1: 服务启动失败

```bash
# 查看详细错误日志
sudo journalctl -u uoft-assistant -xe

# 常见原因:
# - .env 文件配置错误
# - 端口被占用
# - Python 依赖未安装
```

### 问题 2: 无法访问网站

```bash
# 检查 Nginx 状态
sudo systemctl status nginx

# 检查防火墙
sudo ufw status

# 检查安全组配置 (AWS Console)
```

### 问题 3: Groq API 错误

```bash
# 验证 API 密钥
cat .env | grep GROQ_API_KEY

# 测试 API
curl -H "Authorization: Bearer YOUR_GROQ_API_KEY" \
  https://api.groq.com/openai/v1/models
```

### 问题 4: 内存不足

```bash
# 查看内存使用
free -h

# 创建 swap 空间 (临时解决)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 成本估算

### AWS EC2 Free Tier (12个月)

- ✅ **t2.micro 实例**: 750 小时/月（免费）
- ✅ **30 GB EBS 存储**: 免费
- ✅ **数据传输**: 15 GB/月（免费）

### Groq API

- ✅ **完全免费**
- 限制：30 请求/分钟，14,400 请求/天

### 总成本

- **前 12 个月**: $0
- **12 个月后**: 约 $10-15/月（取决于使用量）

---

## 安全最佳实践

1. **定期更新系统**
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ```

2. **更改 API_KEY**
   - 在 `.env` 中设置强密码
   - 不要使用默认值

3. **限制 SSH 访问**
   - 只允许特定 IP 访问 22 端口
   - 使用密钥认证，禁用密码登录

4. **监控日志**
   - 定期检查访问日志
   - 设置异常告警

5. **备份数据**
   - 定期备份向量数据库
   - 使用 AWS S3 存储备份

---

## 下一步

- ✅ 添加更多课程 PDF
- ✅ 配置自定义域名
- ✅ 启用 HTTPS
- ✅ 添加监控和告警
- ✅ 实现对话历史功能

---

## 需要帮助？

- GitHub Issues: [YOUR_REPO/issues](https://github.com/YOUR_USERNAME/uoft-assistant/issues)
- Groq 文档: https://console.groq.com/docs
- AWS EC2 文档: https://docs.aws.amazon.com/ec2/

---

**部署完成！享受你的 UofT Assistant 吧！** 🎉
