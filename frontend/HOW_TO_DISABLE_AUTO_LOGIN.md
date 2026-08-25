# 如何关闭自动登录

如果您需要恢复手动输入账号密码的登录方式：

## 方法1：注释自动登录代码

编辑 `frontend/src/pages/Login.tsx`，找到这段代码（约第18-38行）：

```tsx
// 🚀 自动登录功能：页面加载后自动使用admin账号登录
useEffect(() => {
  const autoLogin = async () => {
    setLoading(true);
    try {
      const response = await authAPI.login({ 
        username: 'admin', 
        password: 'Admin2026' 
      });
      login(response.access_token, response.user);
      navigate('/overview/dashboard/realtime');
    } catch (err) {
      // 自动登录失败，显示登录表单
      const error = err as any;
      setError(error?.detail || '自动登录失败，请手动登录');
      console.error('自动登录错误:', err);
    } finally {
      setLoading(false);
    }
  };
  
  // 延迟500ms执行自动登录（让用户看到加载动画）
  const timer = setTimeout(autoLogin, 500);
  return () => clearTimeout(timer);
}, [login, navigate]);
```

**注释掉整个useEffect**（在前面加 `/*` 后面加 `*/`）：

```tsx
/*
useEffect(() => {
  ...
}, [login, navigate]);
*/
```

## 方法2：添加开关控制

在 `frontend/src/pages/Login.tsx` 顶部添加常量：

```tsx
const AUTO_LOGIN_ENABLED = false; // 改为false关闭自动登录
```

然后修改useEffect：

```tsx
useEffect(() => {
  if (!AUTO_LOGIN_ENABLED) return; // 如果关闭，直接返回
  
  const autoLogin = async () => {
    // ... 自动登录逻辑
  };
  
  const timer = setTimeout(autoLogin, 500);
  return () => clearTimeout(timer);
}, [login, navigate]);
```

---

**当前状态**：✅ 自动登录已启用  
**账号**：admin / Admin2026  
**生效时间**：页面加载后500ms
