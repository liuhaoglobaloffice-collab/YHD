# -*- coding: utf-8 -*-
import sys
import io

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

"""
Week 4 Day 2: Ollama 集成测试脚本

功能：
1. 检测 Ollama 服务状态
2. 列出可用模型
3. 下载推荐模型
4. 测试模型推理
5. 性能基准测试
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import ollama
    from ollama import AsyncClient
except ImportError:
    print("[FAIL] Ollama SDK 未安装")
    print("请运行: pip install ollama")
    sys.exit(1)


class OllamaIntegration:
    """Ollama 集成测试工具"""

    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self.client = AsyncClient(host=host)

    async def check_service(self) -> bool:
        """检查 Ollama 服务是否运行"""
        print("[CHECK] 检查 Ollama 服务...")
        try:
            # Try to list models as a health check
            await self.client.list()
            print(f"[OK] Ollama 服务运行中 ({self.host})")
            return True
        except Exception as e:
            print(f"[FAIL] Ollama 服务未运行: {e}")
            print("\n请启动 Ollama 服务:")
            print("  - Windows: 运行 Ollama 桌面应用")
            print("  - Linux/Mac: ollama serve")
            return False

    async def list_models(self) -> list:
        """列出已安装的模型"""
        print("\n[MODELS] 已安装的模型:")
        try:
            response = await self.client.list()
            models = response.get("models", [])
            
            if not models:
                print("  (无已安装模型)")
                return []
            
            for model in models:
                name = model.get("name", "unknown")
                size_gb = model.get("size", 0) / (1024**3)
                modified = model.get("modified_at", "")
                print(f"  • {name} ({size_gb:.2f} GB) - {modified[:10]}")
            
            return [m.get("name") for m in models]
        except Exception as e:
            print(f"[FAIL] 获取模型列表失败: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """下载模型"""
        print(f"\n[DOWNLOAD] 下载模型: {model_name}")
        print("  (这可能需要几分钟，取决于网络速度...)")
        
        try:
            # Note: ollama.pull() is synchronous in current SDK
            # We'll use the sync version
            import ollama as ollama_sync
            
            # Show progress
            stream = ollama_sync.pull(model_name, stream=True)
            last_status = ""
            
            for chunk in stream:
                status = chunk.get("status", "")
                if status != last_status:
                    print(f"  {status}")
                    last_status = status
            
            print(f"[OK] 模型 {model_name} 下载完成")
            return True
            
        except Exception as e:
            print(f"[FAIL] 下载失败: {e}")
            return False

    async def test_inference(self, model_name: str, prompt: str = "Hello!") -> dict:
        """测试模型推理"""
        print(f"\n[TEST] 测试模型推理: {model_name}")
        print(f"   提示词: {prompt}")
        
        try:
            start_time = time.time()
            
            response = await self.client.chat(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7, "num_predict": 50},
            )
            
            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000
            
            content = response.get("message", {}).get("content", "")
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            print(f"[OK] 推理成功")
            print(f"   响应: {content[:100]}{'...' if len(content) > 100 else ''}")
            print(f"   Tokens: {prompt_tokens} + {completion_tokens} = {prompt_tokens + completion_tokens}")
            print(f"   耗时: {elapsed_ms:.0f}ms")
            
            return {
                "success": True,
                "content": content,
                "tokens": prompt_tokens + completion_tokens,
                "time_ms": elapsed_ms,
            }
            
        except Exception as e:
            print(f"[FAIL] 推理失败: {e}")
            return {"success": False, "error": str(e)}

    async def benchmark(self, model_name: str, iterations: int = 3) -> dict:
        """性能基准测试"""
        print(f"\n[BENCHMARK] 性能基准测试: {model_name} (x{iterations})")
        
        prompts = [
            "What is 2+2?",
            "Translate 'hello' to Chinese",
            "Write a haiku about coding",
        ]
        
        results = []
        total_time = 0
        total_tokens = 0
        
        for i, prompt in enumerate(prompts[:iterations], 1):
            print(f"  测试 {i}/{iterations}...", end=" ")
            result = await self.test_inference(model_name, prompt)
            
            if result["success"]:
                results.append(result)
                total_time += result["time_ms"]
                total_tokens += result["tokens"]
                print(f"{result['time_ms']:.0f}ms")
            else:
                print("失败")
        
        if not results:
            return {"success": False}
        
        avg_time = total_time / len(results)
        avg_tokens = total_tokens / len(results)
        tokens_per_sec = (total_tokens / total_time) * 1000 if total_time > 0 else 0
        
        print(f"\n[RESULTS] 基准测试结果:")
        print(f"   平均响应时间: {avg_time:.0f}ms")
        print(f"   平均Token数: {avg_tokens:.0f}")
        print(f"   吞吐量: {tokens_per_sec:.1f} tokens/s")
        
        return {
            "success": True,
            "iterations": len(results),
            "avg_time_ms": avg_time,
            "avg_tokens": avg_tokens,
            "tokens_per_sec": tokens_per_sec,
        }

    async def run_full_test(self, recommended_model: str = "qwen2.5:7b"):
        """运行完整的集成测试流程"""
        print("=" * 60)
        print("[START] LiuHao AI-OS - Ollama 集成测试")
        print("=" * 60)
        
        # 1. 检查服务
        if not await self.check_service():
            return False
        
        # 2. 列出模型
        installed_models = await self.list_models()
        
        # 3. 检查推荐模型是否安装
        if recommended_model not in installed_models:
            print(f"\n[WARN]  推荐模型 {recommended_model} 未安装")
            print(f"   建议安装: ollama pull {recommended_model}")
            print(f"   或者手动运行此脚本安装")
            
            # Ask user if they want to download
            # (In automated mode, skip this)
            return False
        
        # 4. 测试推理
        test_result = await self.test_inference(
            recommended_model,
            "你好，请用中文回答：鎏灏AI-OS是什么？"
        )
        
        if not test_result["success"]:
            return False
        
        # 5. 性能基准测试
        benchmark_result = await self.benchmark(recommended_model)
        
        # 6. 总结
        print("\n" + "=" * 60)
        print("[OK] Ollama 集成测试完成")
        print("=" * 60)
        
        if benchmark_result["success"]:
            print(f"✓ 模型: {recommended_model}")
            print(f"✓ 平均响应时间: {benchmark_result['avg_time_ms']:.0f}ms")
            print(f"✓ 吞吐量: {benchmark_result['tokens_per_sec']:.1f} tokens/s")
        
        print("\n[SUCCESS] Ollama Provider 已就绪，可以在 LiuHao AI-OS 中使用！")
        return True


async def main():
    """主函数"""
    integration = OllamaIntegration()
    
    try:
        success = await integration.run_full_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[WARN]  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[FAIL] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
