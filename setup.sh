#!/bin/bash

# 更新系统
echo "更新系统..."
sudo apt update && sudo apt upgrade -y

# 安装 Python 3 和 pip
echo "安装 Python3 和 pip..."
sudo apt install python3 python3-pip -y

# 安装 FFmpeg
echo "安装 FFmpeg..."
sudo apt install ffmpeg -y

# 检查 Python 和 FFmpeg 版本
echo "检查 Python 和 FFmpeg 版本..."
python3 --version
ffmpeg -version

# 进入项目目录
echo "进入项目目录..."
cd mygo_serifu_bot_cloud

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv venv

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装项目依赖
echo "安装项目依赖..."
pip install -r requirements.txt

# 运行主程序
echo "运行主程序..."
screen -R bot
python main.py
