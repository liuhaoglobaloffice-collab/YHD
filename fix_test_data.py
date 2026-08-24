#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修改测试数据使其唯一"""

def main():
    filepath = r"tests/integration/test_supplier_api.py"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 添加时间戳生成
    old_supplier_data = '    @pytest.mark.asyncio\n    async def test_create_supplier_api(self, test_client: AsyncClient):\n        """测试创建供应商API"""\n        supplier_data = {'
    new_supplier_data = '    @pytest.mark.asyncio\n    async def test_create_supplier_api(self, test_client: AsyncClient):\n        """测试创建供应商API"""\n        timestamp = datetime.now().strftime(\'%Y%m%d%H%M%S%f\')\n        supplier_data = {'
    
    content = content.replace(old_supplier_data, new_supplier_data)
    
    # 修改固定值为使用时间戳
    content = content.replace('"name": "API测试供应商",', '"name": f"API测试供应商-{timestamp}",')
    content = content.replace('"legal_name": "API测试供应商有限公司",', '"legal_name": f"API测试供应商有限公司-{timestamp}",')
    content = content.replace('"code": "SUP6001",', '"code": f"SUP{timestamp[:12]}",')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("OK - 测试数据已修改为使用时间戳")

if __name__ == '__main__':
    main()
