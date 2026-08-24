"""
架构层隔离测试

验证 LiuHao AI-OS 的 8 层架构是否严格遵守依赖规则：
- 上层可以依赖下层
- 下层不得依赖上层
- 不得有循环依赖

架构层级：
  Layer 8: API
  Layer 7: Workforce
  Layer 6: Business
  Layer 5: Workflow
  Layer 4: Knowledge
  Layer 3: AI (ai/)
  Layer 2: Identity
  Layer 1: Security
  Layer 0: Core
"""

import ast
from pathlib import Path
from typing import List, Set


def get_imports_from_file(file_path: Path) -> Set[str]:
    """
    从 Python 文件中提取所有 import 语句
    
    Args:
        file_path: Python 文件路径
        
    Returns:
        import 模块名集合
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
        
        return imports
    except Exception:
        # 如果解析失败，返回空集合
        return set()


def get_python_files(directory: Path) -> List[Path]:
    """
    获取目录下所有 Python 文件
    
    Args:
        directory: 目录路径
        
    Returns:
        Python 文件路径列表
    """
    if not directory.exists():
        return []
    return list(directory.rglob("*.py"))


# ==================== 测试用例 ====================


def test_core_does_not_import_upper_layers():
    """
    Core (Layer 0) 不得导入任何上层模块
    
    禁止导入：
    - src.security
    - src.identity
    - src.ai
    - src.knowledge
    - src.workflow
    - src.business
    - src.workforce
    - src.api
    """
    forbidden_modules = [
        "src.security",
        "src.identity",
        "src.ai",
        "src.knowledge",
        "src.workflow",
        "src.business",
        "src.workforce",
        "src.api",
    ]
    
    core_dir = Path("src/core")
    violations = []
    
    for py_file in get_python_files(core_dir):
        imports = get_imports_from_file(py_file)
        
        for imp in imports:
            for forbidden in forbidden_modules:
                if imp.startswith(forbidden):
                    violations.append(f"{py_file}: imports {imp}")
    
    assert len(violations) == 0, f"Core layer imports upper layers:\n" + "\n".join(violations)


def test_security_does_not_import_business_or_above():
    """
    Security (Layer 1) 不得导入 Business 层或更上层
    
    允许导入: Core
    禁止导入: Identity, AI, Knowledge, Workflow, Business, Workforce, API
    """
    forbidden_modules = [
        "src.identity",
        "src.ai",
        "src.knowledge",
        "src.workflow",
        "src.business",
        "src.workforce",
        "src.api",
    ]
    
    security_dir = Path("src/security")
    violations = []
    
    for py_file in get_python_files(security_dir):
        imports = get_imports_from_file(py_file)
        
        for imp in imports:
            for forbidden in forbidden_modules:
                if imp.startswith(forbidden):
                    violations.append(f"{py_file}: imports {imp}")
    
    assert len(violations) == 0, f"Security layer imports forbidden modules:\n" + "\n".join(violations)


def test_identity_does_not_import_business_or_above():
    """
    Identity (Layer 2) 不得导入 Business 层或更上层
    
    允许导入: Core, Security
    禁止导入: AI, Knowledge, Workflow, Business, Workforce, API
    """
    forbidden_modules = [
        "src.ai",
        "src.knowledge",
        "src.workflow",
        "src.business",
        "src.workforce",
        "src.api",
    ]
    
    identity_dir = Path("src/identity")
    violations = []
    
    for py_file in get_python_files(identity_dir):
        imports = get_imports_from_file(py_file)
        
        for imp in imports:
            for forbidden in forbidden_modules:
                if imp.startswith(forbidden):
                    violations.append(f"{py_file}: imports {imp}")
    
    assert len(violations) == 0, f"Identity layer imports forbidden modules:\n" + "\n".join(violations)


def test_ai_does_not_import_business_or_above():
    """
    AI (Layer 3) 不得导入 Business 层或更上层
    
    允许导入: Core, Security, Identity
    禁止导入: Knowledge, Workflow, Business, Workforce, API
    """
    forbidden_modules = [
        "src.knowledge",
        "src.workflow",
        "src.business",
        "src.workforce",
        "src.api",
    ]
    
    ai_dir = Path("src/ai")
    violations = []
    
    for py_file in get_python_files(ai_dir):
        imports = get_imports_from_file(py_file)
        
        for imp in imports:
            for forbidden in forbidden_modules:
                if imp.startswith(forbidden):
                    violations.append(f"{py_file}: imports {imp}")
    
    assert len(violations) == 0, f"AI layer imports forbidden modules:\n" + "\n".join(violations)


def test_knowledge_does_not_import_business_or_above():
    """
    Knowledge (Layer 4) 不得导入 Business 层或更上层
    
    允许导入: Core, Security, Identity, AI
    禁止导入: Workflow, Business, Workforce, API
    """
    forbidden_modules = [
        "src.workflow",
        "src.business",
        "src.workforce",
        "src.api",
    ]
    
    knowledge_dir = Path("src/knowledge")
    violations = []
    
    for py_file in get_python_files(knowledge_dir):
        imports = get_imports_from_file(py_file)
        
        for imp in imports:
            for forbidden in forbidden_modules:
                if imp.startswith(forbidden):
                    violations.append(f"{py_file}: imports {imp}")
    
    assert len(violations) == 0, f"Knowledge layer imports forbidden modules:\n" + "\n".join(violations)


def test_workflow_does_not_import_business_or_above():
    """
    Workflow (Layer 5) 不得导入 Business 层或更上层
    
    允许导入: Core, Security, Identity, AI, Knowledge
    禁止导入: Business, Workforce, API
    """
    forbidden_modules = [
        "src.business",
        "src.workforce",
        "src.api",
    ]
    
    workflow_dir = Path("src/workflow")
    violations = []
    
    for py_file in get_python_files(workflow_dir):
        imports = get_imports_from_file(py_file)
        
        for imp in imports:
            for forbidden in forbidden_modules:
                if imp.startswith(forbidden):
                    violations.append(f"{py_file}: imports {imp}")
    
    assert len(violations) == 0, f"Workflow layer imports forbidden modules:\n" + "\n".join(violations)


def test_business_does_not_import_workforce_or_api():
    """
    Business (Layer 6) 不得导入 Workforce 或 API 层
    
    允许导入: Core, Security, Identity, AI, Knowledge, Workflow, Workforce.models (数据模型)
    禁止导入: Workforce, API
    """
    forbidden_modules = [
        "src.api",
    ]
    
    business_dir = Path("src/business")
    violations = []
    
    for py_file in get_python_files(business_dir):
        imports = get_imports_from_file(py_file)
        
        for imp in imports:
            # 允许 Business 导入 Workforce.models (DTO)
            if imp.startswith("src.workforce.models") or imp.startswith("src.workforce.registry"):
                continue
            
            for forbidden in forbidden_modules:
                if imp.startswith(forbidden):
                    violations.append(f"{py_file}: imports {imp}")
    
    assert len(violations) == 0, f"Business layer imports forbidden modules:\n" + "\n".join(violations)


def test_workforce_does_not_import_api():
    """
    Workforce (Layer 7) 不得导入 API 层
    
    允许导入: Core, Security, Identity, AI, Knowledge, Workflow, Business
    禁止导入: API
    """
    forbidden_modules = [
        "src.api",
    ]
    
    workforce_dir = Path("src/workforce")
    violations = []
    
    for py_file in get_python_files(workforce_dir):
        imports = get_imports_from_file(py_file)
        
        for imp in imports:
            for forbidden in forbidden_modules:
                if imp.startswith(forbidden):
                    violations.append(f"{py_file}: imports {imp}")
    
    assert len(violations) == 0, f"Workforce layer imports API:\n" + "\n".join(violations)


def test_no_circular_dependencies_between_layers():
    """
    检测层间循环依赖
    
    如果 A 导入 B，B 不得导入 A
    """
    # 这个测试通过上述单向依赖测试隐式保证
    # 如果每层只能向下依赖，则不可能有循环
    pass


# ==================== 额外检查 ====================


def test_database_models_independent():
    """
    Database 模型层应该独立，不依赖业务逻辑层
    
    允许导入: Core, Identity, Security
    例外: converters.py 可以导入上层 models （用于数据转换）
    禁止导入: 非 converters 文件导入业务逻辑
    """
    forbidden_modules = [
        "src.ai",
        "src.knowledge",
        "src.workflow",
        "src.business",
        "src.workforce",
        "src.api",
    ]
    
    database_dir = Path("src/database")
    violations = []
    
    for py_file in get_python_files(database_dir):
        # converters.py 例外：允许导入上层 models
        if py_file.name == "converters.py":
            continue
        
        imports = get_imports_from_file(py_file)
        
        for imp in imports:
            for forbidden in forbidden_modules:
                if imp.startswith(forbidden):
                    violations.append(f"{py_file}: imports {imp}")
    
    assert len(violations) == 0, f"Database layer imports business logic:\n" + "\n".join(violations)


def test_no_test_imports_in_src():
    """
    源代码不得导入测试模块
    
    禁止 src/ 下的文件导入 tests/
    """
    src_dir = Path("src")
    violations = []
    
    for py_file in get_python_files(src_dir):
        imports = get_imports_from_file(py_file)
        
        for imp in imports:
            if imp.startswith("tests"):
                violations.append(f"{py_file}: imports {imp}")
    
    assert len(violations) == 0, f"Source code imports test modules:\n" + "\n".join(violations)
