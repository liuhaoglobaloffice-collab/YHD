#!/usr/bin/env python3
"""
LiuHao AI OS - 生产部署前检查清单

用法：
    python scripts/pre_deploy_check.py

检查项：
  1. .env 文件存在且包含所有必需的密钥
  2. Docker 镜像构建状态
  3. docker-compose.yml 配置完整性
  4. 数据库连接信息
"""

import os
import sys
import subprocess
from pathlib import Path

def check_env_file():
    """检查 .env 文件和必需的环境变量"""
    print("📋 检查 .env 配置...")
    
    env_path = Path(".env")
    if not env_path.exists():
        print("  ⚠️  .env 文件不存在，从 .env.production 复制...")
        if Path(".env.production").exists():
            import shutil
            shutil.copy(".env.production", ".env")
            print("  ✅ 已创建 .env（从 .env.production）")
        else:
            print("  ❌ 无可用的 .env 模板（.env.example 或 .env.production）")
            return False
    
    required_vars = [
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "ENCRYPTION_KEY",
        "POSTGRES_PASSWORD",
        "DATABASE_URL",
        "LLM_PROVIDER",
    ]
    
    with open(env_path) as f:
        env_content = f.read()
    
    missing = []
    for var in required_vars:
        if f"{var}=" not in env_content or "change-me" in env_content:
            missing.append(var)
    
    if missing:
        print(f"  ⚠️  缺失或未配置的变量：{', '.join(missing)}")
        print("     请编辑 .env 填写实际值")
        return False
    
    print("  ✅ 所有必需变量已配置")
    return True

def check_docker():
    """检查 Docker 状态"""
    print("\n🐳 检查 Docker 环境...")
    
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"  ✅ Docker: {result.stdout.strip()}")
        else:
            print("  ❌ Docker 命令失败")
            return False
    except Exception as e:
        print(f"  ❌ Docker 不可用：{e}")
        return False
    
    try:
        result = subprocess.run(["docker", "compose", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"  ✅ Docker Compose: {result.stdout.strip()}")
        else:
            print("  ❌ Docker Compose 命令失败")
            return False
    except Exception as e:
        print(f"  ❌ Docker Compose 不可用：{e}")
        return False
    
    return True

def check_compose_config():
    """检查 docker-compose.yml 配置"""
    print("\n⚙️  检查 docker-compose.yml 配置...")
    
    try:
        result = subprocess.run(["docker", "compose", "config"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("  ✅ docker-compose.yml 配置有效")
            return True
        else:
            print(f"  ❌ docker-compose.yml 配置错误：\n{result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ 无法验证 docker-compose.yml：{e}")
        return False

def check_ports():
    """检查必需的端口可用性"""
    print("\n🔌 检查端口可用性...")
    
    import socket
    ports = {80: "frontend", 8000: "backend", 5432: "database"}
    
    for port, service in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        
        if result == 0:
            print(f"  ⚠️  端口 {port} ({service}) 已被占用")
        else:
            print(f"  ✅ 端口 {port} ({service}) 可用")

def main():
    print("=" * 60)
    print("🚀 LiuHao AI OS - 生产部署前检查")
    print("=" * 60)
    
    checks = [
        ("环境变量", check_env_file),
        ("Docker 环境", check_docker),
        ("Compose 配置", check_compose_config),
        ("端口可用性", check_ports),
    ]
    
    passed = 0
    failed = 0
    
    for name, check_fn in checks:
        try:
            if check_fn():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ 检查异常：{e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"✅ 通过：{passed}/{len(checks)} 项检查")
    if failed > 0:
        print(f"❌ 失败：{failed}/{len(checks)} 项检查")
        print("\n建议：")
        print("1. 检查 .env 文件中的所有必需变量")
        print("2. 确保 Docker 守护进程正在运行")
        print("3. 检查 docker-compose.yml 语法")
        print("4. 确保必需的端口未被其他应用占用")
        sys.exit(1)
    else:
        print("\n🎉 所有检查通过！可以安全部署")
        print("\n下一步：")
        print("  docker compose up -d --build")
        sys.exit(0)

if __name__ == "__main__":
    main()
