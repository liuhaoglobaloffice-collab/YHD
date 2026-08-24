#!/usr/bin/env python3
"""完整修复 supplier.py 文件"""

import re

# 读取损坏的文件
with open('src/api/routes/supplier.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("Step 1: Removing orphaned code fragment...")

# 找到孤立的 assessment_date 片段并删除
# 这个片段从 "assessment_date=assessment.assessment_date.isoformat()," 开始
# 到 "raise HTTPException(status_code=500, detail="风险评估失败")" 结束

orphan_start = content.find('            assessment_date=assessment.assessment_date.isoformat(),')
if orphan_start > 0:
    # 找到这个片段的结束位置（下一个 @router 之前）
    next_router = content.find('\n\n@router.get("/{supplier_id}/risk-history"', orphan_start)
    if next_router > 0:
        # 删除孤立片段
        content = content[:orphan_start] + content[next_router:]
        print(f"  Removed orphaned fragment ({next_router - orphan_start} chars)")

# Step 2: 修复 assess-risk 函数（确保它有完整的 return 语句）
print("\nStep 2: Fixing assess-risk function...")

assess_risk_start = content.find('@router.post("/{supplier_id}/assess-risk"')
if assess_risk_start > 0:
    # 找到这个函数的 return RiskAssessmentResponse 部分
    response_start = content.find('return RiskAssessmentResponse(', assess_risk_start)
    if response_start > 0:
        # 找到这个 return 语句的结束位置
        # 应该是在 risk_factors= 之后
        risk_factors_pos = content.find('risk_factors=assessment.risk_factors,', response_start)
        if risk_factors_pos > 0:
            # 检查是否有完整的闭合
            next_line = content[risk_factors_pos:risk_factors_pos+200]
            if 'assessment_date=' not in next_line:
                # 需要添加剩余字段
                insertion_point = risk_factors_pos + len('risk_factors=assessment.risk_factors,')
                missing_fields = '''
            assessment_date=assessment.assessment_date.isoformat(),
            assessor=assessment.assessor,
            recommendations=assessment.recommendations,
            is_active=assessment.is_active,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("risk_assessment_failed", supplier_id=supplier_id, error=str(e))
        raise HTTPException(status_code=500, detail="风险评估失败")

'''
                content = content[:insertion_point] + missing_fields + content[insertion_point:]
                print("  Added missing fields to assess-risk return statement")

# Step 3: 移动 batch 路由到 /{supplier_id} 之前
print("\nStep 3: Moving batch routes before /{supplier_id}...")

# 找到 batch 路由块
batch_post_start = content.find('@router.post("/batch", status_code=201)')
batch_import_start = content.find('@router.post("/import")', batch_post_start)

if batch_post_start > 0 and batch_import_start > 0:
    # 提取 batch 路由块
    batch_block = content[batch_post_start:batch_import_start]
    
    # 删除原位置的 batch 路由
    content = content[:batch_post_start] + content[batch_import_start:]
    
    # 找到 /{supplier_id} 路由
    supplier_id_get = content.find('@router.get("/{supplier_id}", response_model=SupplierResponse)')
    
    if supplier_id_get > 0:
        # 在 /{supplier_id} 之前插入 batch 路由
        content = content[:supplier_id_get] + batch_block + '\n' + content[supplier_id_get:]
        print(f"  Moved batch routes ({len(batch_block)} chars) before /{supplier_id}")
    else:
        print("  WARNING: Could not find /{supplier_id} route")
else:
    print("  WARNING: Could not find batch routes")

# 写回文件
with open('src/api/routes/supplier.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n=== Repair Complete ===")
print("File written successfully")
