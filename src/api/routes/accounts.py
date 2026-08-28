"""
Sub-account management API (S1).

主账号可创建/管理子账号（受限），子账号不可指挥鎏灏。
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.cost_tracker import CostTracker
from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.schemas import UserResponse
from src.crm.models import SupplierInquiry
from src.crm.service import LeadService
from src.identity.audit import AuditService
from src.identity.auth import hash_password
from src.identity.models import AccountType, ApprovalStatus, BusinessRole, RoleEnum, User
from src.identity.rbac import BUSINESS_ROLE_PERMISSIONS, Permission
from src.integrations.models import PlatformMessage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/accounts", tags=["accounts"])


# ==================== Schemas ====================


class SubAccountCreate(BaseModel):
    """Create a sub-account request."""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None
    business_role: BusinessRole = BusinessRole.GENERAL
    data_scope: str = "self"


class SubAccountUpdate(BaseModel):
    """Update a sub-account (role/status/permissions)."""

    business_role: Optional[BusinessRole] = None
    is_active: Optional[bool] = None
    data_scope: Optional[str] = None
    full_name: Optional[str] = None


class ApproveSubAccountRequest(BaseModel):
    """主账号审批子账号时指定角色和权限。"""

    business_role: BusinessRole = BusinessRole.GENERAL
    data_scope: str = "self"
    full_name: Optional[str] = None


class PermissionUpdateRequest(BaseModel):
    """更新子账号的细粒度权限配置。"""

    permissions: dict[str, bool]  # {"lead:read": true, "whatsapp:send": false}


class DataScopeUpdate(BaseModel):
    """更新子账号的数据权限范围。"""

    data_scope: str = "self"  # all / department / self


class BusinessRoleInfo(BaseModel):
    """业务角色信息。"""

    role: str
    label: str
    description: str
    permissions: list[str]


class SubAccountListResponse(BaseModel):
    sub_accounts: list[UserResponse]
    total: int


class BudgetUpdate(BaseModel):
    """主账号为子账号设置月度 AI 预算（USD）。"""

    monthly_budget: float = Field(..., ge=0, description="月度 AI 预算（USD），0 表示限制为不使用")


# ==================== Helpers ====================


def _is_owner(user: User) -> bool:
    """主账号 = account_type owner 或 is_superuser."""
    return user.account_type == AccountType.OWNER or user.is_superuser


async def _get_own_sub(session: AsyncSession, owner: User, sub_id: int) -> User:
    """校验并返回 owner 名下的子账号。"""
    result = await session.execute(
        select(User).where(
            User.id == sub_id,
            User.account_type == AccountType.SUB,
            User.parent_user_id == owner.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="子账号不存在或不属于当前主账号")
    return sub


def _budget_out(sub: User, usage) -> dict:
    budget = sub.ai_budget_monthly
    used = usage.get("cost_usd", 0.0)
    return {
        "user_id": sub.id,
        "username": sub.username,
        "month": usage.get("month"),
        "monthly_budget": budget,
        "used_usd": used,
        "calls": usage.get("calls", 0),
        "remaining_usd": round(budget - used, 4) if budget is not None else None,
        "over_budget": budget is not None and used > budget,
    }


# ==================== Endpoints ====================


@router.post("/sub-accounts", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_sub_account(
    request: SubAccountCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    主账号创建子账号。

    子账号默认 viewer（只读），继承主账号的 tenant。
    只有主账号可调用。
    """
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以创建子账号")

    # 检查用户名/邮箱唯一
    existing = await session.execute(
        select(User).where(
            (User.username == request.username) | (User.email == request.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name or request.username,
        role=RoleEnum.VIEWER,
        business_role=request.business_role,
        data_scope=request.data_scope,
        account_type=AccountType.SUB,
        parent_user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        is_active=True,
        approval_status=ApprovalStatus.APPROVED.value,  # 主账号直接创建，无需审核
    )
    # 根据业务角色设置默认权限
    role_perms = BUSINESS_ROLE_PERMISSIONS.get(request.business_role, [])
    user.permissions_config = {p.value: True for p in role_perms}
    session.add(user)
    await session.commit()
    await session.refresh(user)

    await AuditService.log_success(
        session=session,
        action="create_sub_account",
        resource_type="user",
        resource_id=str(user.id),
        user_id=current_user.id,
        details={"username": user.username, "role": user.role.value},
    )

    logger.info("sub_account_created", owner_id=current_user.id, sub_id=user.id)
    return user


@router.get("/sub-accounts", response_model=SubAccountListResponse)
async def list_sub_accounts(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出当前账号（主账号或其子账号）名下的子账号。"""
    if _is_owner(current_user):
        # 主账号：自己的所有子账号
        stmt = select(User).where(
            User.account_type == AccountType.SUB,
            User.parent_user_id == current_user.id,
        )
    else:
        # 子账号：只能看到自己（或同级？S1: 只看自己）
        stmt = select(User).where(User.id == current_user.id)

    result = await session.execute(stmt.order_by(User.created_at.desc()))
    users = list(result.scalars().all())
    return SubAccountListResponse(
        sub_accounts=[UserResponse.model_validate(u) for u in users],
        total=len(users),
    )


@router.get("/pending-approvals", response_model=SubAccountListResponse)
async def list_pending_approvals(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出等待当前主账号审核的子账号申请。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以审核申请")

    stmt = select(User).where(
        User.account_type == AccountType.SUB,
        User.parent_user_id == current_user.id,
        User.approval_status == ApprovalStatus.PENDING.value,
    )
    result = await session.execute(stmt.order_by(User.created_at.asc()))
    users = list(result.scalars().all())
    return SubAccountListResponse(
        sub_accounts=[UserResponse.model_validate(u) for u in users],
        total=len(users),
    )


@router.post("/{sub_id}/approve", response_model=UserResponse)
async def approve_sub_account(
    sub_id: int,
    request: ApproveSubAccountRequest = ApproveSubAccountRequest(),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """主账号同意子账号注册申请，分配业务角色并启用账号。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以审核申请")

    result = await session.execute(
        select(User).where(
            User.id == sub_id,
            User.account_type == AccountType.SUB,
            User.parent_user_id == current_user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="子账号不存在")

    sub.approval_status = ApprovalStatus.APPROVED.value
    sub.is_active = True
    sub.business_role = request.business_role
    sub.data_scope = request.data_scope
    if request.full_name:
        sub.full_name = request.full_name

    # 根据业务角色设置默认权限配置
    role_perms = BUSINESS_ROLE_PERMISSIONS.get(request.business_role, [])
    sub.permissions_config = {p.value: True for p in role_perms}

    await session.commit()
    await session.refresh(sub)

    await AuditService.log_success(
        session=session,
        action="approve_sub_account",
        resource_type="user",
        resource_id=str(sub.id),
        user_id=current_user.id,
        details={
            "username": sub.username,
            "business_role": sub.business_role.value,
            "data_scope": sub.data_scope,
        },
    )
    logger.info(
        "sub_account_approved",
        owner_id=current_user.id,
        sub_id=sub.id,
        role=sub.business_role,
    )
    return sub


@router.post("/{sub_id}/reject", response_model=UserResponse)
async def reject_sub_account(
    sub_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """主账号拒绝子账号注册申请，申请作废。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以审核申请")

    result = await session.execute(
        select(User).where(
            User.id == sub_id,
            User.account_type == AccountType.SUB,
            User.parent_user_id == current_user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="子账号不存在")

    sub.approval_status = ApprovalStatus.REJECTED.value
    sub.is_active = False
    await session.commit()
    await session.refresh(sub)

    await AuditService.log_success(
        session=session,
        action="reject_sub_account",
        resource_type="user",
        resource_id=str(sub.id),
        user_id=current_user.id,
        details={"username": sub.username},
    )
    logger.info("sub_account_rejected", owner_id=current_user.id, sub_id=sub.id)
    return sub


# ==================== 业务角色与权限配置 ====================


BUSINESS_ROLE_META = {
    BusinessRole.SALES: {
        "label": "销售",
        "description": "客户开发、CRM跟进、WhatsApp/Facebook/LinkedIn营销、销售AI员工任务",
    },
    BusinessRole.PURCHASING: {
        "label": "采购",
        "description": "供应商搜索、供应商分析、价格分析、风险分析、采购AI员工",
    },
    BusinessRole.OPERATIONS: {
        "label": "运营",
        "description": "数据运营、SEO优化、独立站管理、内容发布、社媒运营",
    },
    BusinessRole.AI_ADMIN: {
        "label": "AI管理员",
        "description": "管理AI员工、技能市场、模型配置、AI运行监控",
    },
    BusinessRole.GENERAL: {
        "label": "通用",
        "description": "多功能综合岗位，可操作大部分业务模块",
    },
}


@router.get("/roles", response_model=list[BusinessRoleInfo])
async def list_business_roles(
    current_user: User = Depends(get_current_user),
):
    """获取所有可用的业务角色及其权限清单。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以查看")
    roles = []
    for role_enum, meta in BUSINESS_ROLE_META.items():
        perms = BUSINESS_ROLE_PERMISSIONS.get(role_enum, [])
        roles.append(BusinessRoleInfo(
            role=role_enum.value,
            label=meta["label"],
            description=meta["description"],
            permissions=[p.value for p in perms],
        ))
    return roles


@router.get("/permissions/all")
async def list_all_permissions(
    current_user: User = Depends(get_current_user),
):
    """获取系统中所有可用的权限项。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以查看")
    return {
        "permissions": [p.value for p in Permission],
    }


@router.get("/sub-accounts/{sub_id}/permissions", response_model=dict)
async def get_sub_permissions(
    sub_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取子账号的权限配置。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以查看")
    sub = await _get_own_sub(session, current_user, sub_id)
    return {
        "user_id": sub.id,
        "username": sub.username,
        "business_role": sub.business_role.value if sub.business_role else None,
        "data_scope": sub.data_scope,
        "permissions_config": sub.permissions_config or {},
    }


@router.put("/sub-accounts/{sub_id}/permissions")
async def update_sub_permissions(
    sub_id: int,
    request: PermissionUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新子账号的细粒度权限配置。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以修改")
    sub = await _get_own_sub(session, current_user, sub_id)
    sub.permissions_config = request.permissions
    await session.commit()
    await session.refresh(sub)

    await AuditService.log_success(
        session=session,
        action="update_sub_permissions",
        resource_type="user",
        resource_id=str(sub.id),
        user_id=current_user.id,
        details={"permissions_count": len(request.permissions)},
    )
    logger.info("sub_permissions_updated", sub_id=sub.id, count=len(request.permissions))
    return {
        "user_id": sub.id,
        "username": sub.username,
        "permissions_config": sub.permissions_config,
    }


@router.put("/sub-accounts/{sub_id}/data-scope")
async def update_sub_data_scope(
    sub_id: int,
    request: DataScopeUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新子账号的数据权限范围（all/department/self）。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以修改")
    if request.data_scope not in ("all", "department", "self"):
        raise HTTPException(status_code=400, detail="数据范围必须是 all/department/self")
    sub = await _get_own_sub(session, current_user, sub_id)
    sub.data_scope = request.data_scope
    await session.commit()
    await session.refresh(sub)

    await AuditService.log_success(
        session=session,
        action="update_sub_data_scope",
        resource_type="user",
        resource_id=str(sub.id),
        user_id=current_user.id,
        details={"data_scope": request.data_scope},
    )
    logger.info("sub_data_scope_updated", sub_id=sub.id, scope=request.data_scope)
    return {"user_id": sub.id, "username": sub.username, "data_scope": sub.data_scope}


# ==================== AI 预算（V4） ====================


@router.get("/budget/me")
async def my_budget(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看当前账号自己的当月 AI 预算使用情况。"""
    usage = await CostTracker(session).monthly_usage(current_user.id)
    return _budget_out(current_user, usage)


@router.get("/sub-accounts/{sub_id}/budget")
async def get_sub_budget(
    sub_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看子账号当月 AI 预算使用情况（仅主账号）。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以查看")
    sub = await _get_own_sub(session, current_user, sub_id)
    usage = await CostTracker(session).monthly_usage(sub.id)
    return _budget_out(sub, usage)


@router.get("/budgets")
async def list_sub_budgets(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出名下所有子账号的月度预算使用情况（仅主账号）。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以查看")
    result = await session.execute(
        select(User).where(
            User.account_type == AccountType.SUB,
            User.parent_user_id == current_user.id,
        )
    )
    subs = list(result.scalars().all())
    ret = []
    for sub in subs:
        usage = await CostTracker(session).monthly_usage(sub.id)
        ret.append(_budget_out(sub, usage))
    return {"items": ret, "total": len(ret)}


@router.patch("/sub-accounts/{sub_id}/budget")
async def set_sub_budget(
    sub_id: int,
    request: BudgetUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """主账号调整子账号的月度 AI 预算。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以设置")
    sub = await _get_own_sub(session, current_user, sub_id)
    sub.ai_budget_monthly = request.monthly_budget
    await session.commit()
    await session.refresh(sub)
    await AuditService.log_success(
        session=session,
        action="set_sub_budget",
        resource_type="user",
        resource_id=str(sub.id),
        user_id=current_user.id,
        details={"monthly_budget": request.monthly_budget},
    )
    usage = await CostTracker(session).monthly_usage(sub.id)
    return _budget_out(sub, usage)


# ==================== 子账号数据摘要（V4 · 主账号数据管理台） ====================


@router.get("/sub-accounts/{sub_id}/data-summary")
async def get_sub_data_summary(
    sub_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """主账号查看子账号的数据摘要（线索/消息/询价/AI 成本，只读）。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以查看")
    sub = await _get_own_sub(session, current_user, sub_id)

    uid = sub.id
    from src.crm.models import Lead as LModel

    r = await session.execute(select(LModel).where(LModel.owner_user_id == uid))
    all_leads = list(r.scalars().all())
    by_status = {}
    total_val = 0.0
    for l in all_leads:
        k = l.status.value
        by_status[k] = by_status.get(k, 0) + 1
        if l.estimated_value:
            total_val += l.estimated_value

    msg_r = await session.execute(
        select(func.count(PlatformMessage.id)).where(PlatformMessage.owner_user_id == uid)
    )
    msg_count = msg_r.scalar_one() or 0

    inq_r = await session.execute(
        select(func.count(SupplierInquiry.id)).where(SupplierInquiry.created_by == uid)
    )
    inq_count = inq_r.scalar_one() or 0

    cost = await CostTracker(session).monthly_usage(uid)

    return {
        "user_id": uid,
        "username": sub.username,
        "leads": {"total": len(all_leads), "by_status": by_status, "total_estimated_value": round(total_val, 2)},
        "messages": msg_count,
        "inquiries": inq_count,
        "ai_cost": cost,
        "budget": _budget_out(sub, cost),
    }


@router.patch("/sub-accounts/{sub_id}", response_model=UserResponse)
async def update_sub_account(
    sub_id: int,
    request: SubAccountUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """主账号更新子账号的角色或状态。"""
    if not _is_owner(current_user):
        raise HTTPException(status_code=403, detail="只有主账号可以管理子账号")

    result = await session.execute(
        select(User).where(
            User.id == sub_id,
            User.account_type == AccountType.SUB,
            User.parent_user_id == current_user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="子账号不存在")

    if request.business_role is not None:
        sub.business_role = request.business_role
    if request.is_active is not None:
        sub.is_active = request.is_active
    if request.data_scope is not None:
        if request.data_scope not in ("all", "department", "self"):
            raise HTTPException(status_code=400, detail="数据范围必须是 all/department/self")
        sub.data_scope = request.data_scope
    if request.full_name is not None:
        sub.full_name = request.full_name

    await session.commit()
    await session.refresh(sub)

    await AuditService.log_success(
        session=session,
        action="update_sub_account",
        resource_type="user",
        resource_id=str(sub.id),
        user_id=current_user.id,
        details={"role": sub.role.value, "is_active": sub.is_active},
    )

    logger.info("sub_account_updated", owner_id=current_user.id, sub_id=sub.id)
    return sub
