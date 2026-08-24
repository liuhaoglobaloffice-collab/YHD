#!/usr/bin/env python3
"""
修复测试文件中的数据唯一性问题
"""

import re

def fix_test_file():
    with open("tests/integration/test_supplier_api.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 修复所有固定名称供应商
    replacements = [
        # test_get_supplier_api
        (r'"name": "获取测试供应商",', '"name": f"获取测试供应商-{timestamp}",'),
        (r'"code": "SUP6002",', '"code": f"SUP6002{timestamp[:8]}",'),
        
        # test_update_supplier_api
        (r'"name": "更新测试供应商",', '"name": f"更新测试供应商-{timestamp}",'),
        (r'"code": "SUP6003",', '"code": f"SUP6003{timestamp[:8]}",'),
        
        # test_delete_supplier_api
        (r'"name": "删除测试供应商",', '"name": f"删除测试供应商-{timestamp}",'),
        (r'"code": "SUP6004",', '"code": f"SUP6004{timestamp[:8]}",'),
        
        # test_list_suppliers_api
        (r'"name": f"列表测试供应商{i}",', '"name": f"列表测试供应商{i}-{timestamp}",'),
        (r'"code": f"SUP610{i}",', '"code": f"SUP610{i}{timestamp[:8]}",'),
        
        # test_search_suppliers_api
        (r'"name": "搜索特定供应商",', '"name": f"搜索特定供应商-{timestamp}",'),
        (r'"code": "SUP6201",', '"code": f"SUP6201{timestamp[:8]}",'),
        
        # test_batch_create_api
        (r'"name": f"批量API测试{i}",', '"name": f"批量API测试{i}-{timestamp}",'),
        (r'"code": f"SUP630{i}",', '"code": f"SUP630{i}{timestamp[:8]}",'),
        
        # test_batch_update_api
        (r'"name": f"批量更新测试{i}",', '"name": f"批量更新测试{i}-{timestamp}",'),
        (r'"code": f"SUP640{i}",', '"code": f"SUP640{i}{timestamp[:8]}",'),
        
        # test_batch_delete_api
        (r'"name": f"批量删除测试{i}",', '"name": f"批量删除测试{i}-{timestamp}",'),
        (r'"code": f"SUP650{i}",', '"code": f"SUP650{i}{timestamp[:8]}",'),
        
        # test_advanced_search_api
        (r'"name": f"高级搜索测试{country}{i}",', '"name": f"高级搜索测试{country}{i}-{timestamp}",'),
        (r'"code": f"SUP700{i}",', '"code": f"SUP700{i}{timestamp[:8]}",'),
        
        # test_add_contact_api
        (r'"name": "联系人测试供应商",', '"name": f"联系人测试供应商-{timestamp}",'),
        (r'"code": "SUP8001",', '"code": f"SUP8001{timestamp[:8]}",'),
        
        # test_add_certificate_api
        (r'"name": "证书测试供应商",', '"name": f"证书测试供应商-{timestamp}",'),
        (r'"code": "SUP8002",', '"code": f"SUP8002{timestamp[:8]}",'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # 在需要的地方添加 timestamp 定义
    # test_get_supplier_api
    content = re.sub(
        r'(async def test_get_supplier_api.*?\n.*?"""测试获取供应商API"""\n)',
        r'\1        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n',
        content,
        flags=re.DOTALL
    )
    
    # test_update_supplier_api
    content = re.sub(
        r'(async def test_update_supplier_api.*?\n.*?"""测试更新供应商API"""\n)',
        r'\1        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n',
        content,
        flags=re.DOTALL
    )
    
    # test_delete_supplier_api
    content = re.sub(
        r'(async def test_delete_supplier_api.*?\n.*?"""测试删除供应商API"""\n)',
        r'\1        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n',
        content,
        flags=re.DOTALL
    )
    
    # test_list_suppliers_api
    content = re.sub(
        r'(async def test_list_suppliers_api.*?\n.*?"""测试列表查询API"""\n.*?# 创建测试数据\n)',
        r'\1        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n',
        content,
        flags=re.DOTALL
    )
    
    # test_search_suppliers_api
    content = re.sub(
        r'(async def test_search_suppliers_api.*?\n.*?"""测试搜索API"""\n)',
        r'\1        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n',
        content,
        flags=re.DOTALL
    )
    
    # test_batch_create_api
    content = re.sub(
        r'(async def test_batch_create_api.*?\n.*?"""测试批量创建API"""\n)',
        r'\1        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n',
        content,
        flags=re.DOTALL
    )
    
    # test_batch_update_api
    content = re.sub(
        r'(async def test_batch_update_api.*?\n.*?"""测试批量更新API"""\n)',
        r'\1        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n',
        content,
        flags=re.DOTALL
    )
    
    # test_batch_delete_api
    content = re.sub(
        r'(async def test_batch_delete_api.*?\n.*?"""测试批量删除API"""\n)',
        r'\1        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n',
        content,
        flags=re.DOTALL
    )
    
    # test_advanced_search_api
    content = re.sub(
        r'(async def test_advanced_search_api.*?\n.*?"""测试高级搜索API"""\n)',
        r'\1        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n',
        content,
        flags=re.DOTALL
    )
    
    # test_add_contact_api
    content = re.sub(
        r'(async def test_add_contact_api.*?\n.*?"""测试添加联系人API"""\n)',
        r'\1        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n',
        content,
        flags=re.DOTALL
    )
    
    # test_add_certificate_api
    content = re.sub(
        r'(async def test_add_certificate_api.*?\n.*?"""测试添加证书API"""\n)',
        r'\1        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n',
        content,
        flags=re.DOTALL
    )
    
    # 修复重复的 product_category 行
    content = re.sub(
        r'                "product_category": "Electronics",\n\s+"product_category": "Electronics",',
        '            "product_category": "Electronics",',
        content
    )
    
    # 修复断言
    content = re.sub(
        r'assert data\["name"\] == "获取测试供应商"',
        'assert data["name"] == f"获取测试供应商-{timestamp}"',
        content
    )
    content = re.sub(
        r'assert data\["code"\] == "SUP6002"',
        'assert data["code"] == f"SUP6002{timestamp[:8]}"',
        content
    )
    
    with open("tests/integration/test_supplier_api.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ 测试文件已修复")

if __name__ == "__main__":
    fix_test_file()
