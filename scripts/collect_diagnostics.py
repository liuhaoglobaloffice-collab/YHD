#!/usr/bin/env python3
"""
LiuHao AI OS - 容器日志诊断收集工具

用法：
    python scripts/collect_diagnostics.py [--output diagnostics.tar.gz]

收集内容：
  - 容器日志（stdout/stderr）
  - docker-compose ps 输出
  - 容器资源使用情况
  - 网络配置
  - 环境变量摘要（脱敏）
"""

import os
import subprocess
import json
import tarfile
import tempfile
from pathlib import Path
from datetime import datetime

def run_cmd(cmd, shell=True):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "[超时]"
    except Exception as e:
        return f"[错误] {str(e)}"

def collect_diagnostics():
    """收集诊断信息"""
    diagnostics = {}
    
    print("📊 收集诊断信息...")
    
    # 1. Compose 状态
    print("  - Compose 状态")
    diagnostics["compose_ps"] = run_cmd("docker compose ps")
    diagnostics["compose_config"] = run_cmd("docker compose config")
    
    # 2. 容器日志
    print("  - 容器日志")
    for service in ["backend", "frontend", "database"]:
        diagnostics[f"logs_{service}"] = run_cmd(f"docker compose logs --tail 100 {service}")
    
    # 3. 容器检查
    print("  - 容器详情")
    for container in ["liuhao-backend", "liuhao-frontend", "liuhao-database"]:
        try:
            result = subprocess.run(
                ["docker", "inspect", container],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                diagnostics[f"inspect_{container}"] = result.stdout
        except:
            pass
    
    # 4. 网络
    print("  - 网络信息")
    diagnostics["networks"] = run_cmd("docker network ls")
    try:
        networks = subprocess.run(
            ["docker", "network", "ls", "-q"],
            capture_output=True,
            text=True,
            timeout=10
        ).stdout.strip().split("\n")
        for net in networks:
            if net:
                diagnostics[f"network_inspect_{net[:12]}"] = run_cmd(f"docker network inspect {net}")
    except:
        pass
    
    # 5. 资源使用
    print("  - 资源使用")
    diagnostics["docker_stats"] = run_cmd("docker stats --no-stream")
    diagnostics["docker_system_df"] = run_cmd("docker system df")
    
    # 6. 环境变量（脱敏）
    print("  - 环境变量")
    if Path(".env").exists():
        with open(".env") as f:
            lines = f.readlines()
        sanitized = []
        for line in lines:
            if "=" in line:
                key, value = line.split("=", 1)
                if any(x in key.lower() for x in ["password", "key", "token", "secret"]):
                    sanitized.append(f"{key}=***REDACTED***")
                else:
                    sanitized.append(line.rstrip())
        diagnostics["env_sanitized"] = "\n".join(sanitized)
    
    # 7. Docker 版本
    print("  - 版本信息")
    diagnostics["docker_version"] = run_cmd("docker --version")
    diagnostics["docker_compose_version"] = run_cmd("docker compose --version")
    
    return diagnostics

def save_diagnostics(diagnostics, output_file="diagnostics.txt"):
    """保存诊断信息到文件"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"LiuHao AI OS 诊断报告\n")
        f.write(f"生成时间: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        for key, value in diagnostics.items():
            f.write(f"{'=' * 60}\n")
            f.write(f"[{key}]\n")
            f.write(f"{'=' * 60}\n")
            f.write(value)
            f.write("\n\n")
    
    print(f"✅ 诊断信息已保存到 {output_file}")
    return output_file

def create_archive(diagnostics_file, output_archive="diagnostics.tar.gz"):
    """创建诊断信息归档"""
    with tarfile.open(output_archive, "w:gz") as tar:
        tar.add(diagnostics_file, arcname=Path(diagnostics_file).name)
        
        # 添加 docker-compose.yml 和 .env.example
        if Path("docker-compose.yml").exists():
            tar.add("docker-compose.yml")
        if Path(".env.example").exists():
            tar.add(".env.example")
        if Path("Dockerfile").exists():
            tar.add("Dockerfile")
    
    print(f"📦 诊断包已创建：{output_archive}")
    print(f"   包含文件：")
    with tarfile.open(output_archive, "r:gz") as tar:
        for member in tar.getmembers():
            print(f"     - {member.name}")
    
    return output_archive

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="收集 LiuHao AI OS 诊断信息"
    )
    parser.add_argument(
        "--output",
        default="diagnostics",
        help="输出文件名（无扩展名）"
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="创建 tar.gz 归档"
    )
    
    args = parser.parse_args()
    
    print("🔍 LiuHao AI OS 诊断工具")
    print("=" * 60)
    
    # 检查 Docker
    result = subprocess.run(
        ["docker", "compose", "ps"],
        capture_output=True,
        timeout=10
    )
    if result.returncode != 0:
        print("❌ Docker Compose 不可用，请确保：")
        print("  1. Docker 守护进程正在运行")
        print("  2. 当前目录是 Docker Compose 项目根目录")
        return
    
    # 收集诊断信息
    diagnostics = collect_diagnostics()
    
    # 保存到文件
    diagnostics_file = f"{args.output}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    save_diagnostics(diagnostics, diagnostics_file)
    
    # 创建归档（可选）
    if args.archive:
        archive_name = diagnostics_file.replace(".txt", ".tar.gz")
        create_archive(diagnostics_file, archive_name)
    
    print("\n" + "=" * 60)
    print("✅ 诊断收集完成")
    print(f"📄 主文件：{diagnostics_file}")
    if args.archive:
        print(f"📦 归档文件：{archive_name}")

if __name__ == "__main__":
    main()
