/**
 * Supplier Detail Page
 * 
 * LiuHao AI-OS - Week 7 Day 3
 * 供应商详情页面 - 显示供应商完整信息、联系人、证书、风险评估
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  getSupplier, 
  Supplier, 
  getSupplierRiskHistory, 
  SupplierRiskAssessment,
  getSupplierContacts,
  SupplierContact,
  createSupplierContact,
  updateSupplierContact,
  deleteSupplierContact,
  CreateContactRequest,
  UpdateContactRequest
} from '../../services/supplierAPI';

const SupplierDetailPage: React.FC = () => {
  const { supplierId } = useParams<{ supplierId: string }>();
  const navigate = useNavigate();
  
  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'info' | 'contacts' | 'certificates' | 'risk'>('info');
  
  // 风险评估历史
  const [riskHistory, setRiskHistory] = useState<SupplierRiskAssessment[]>([]);
  const [loadingRisk, setLoadingRisk] = useState(false);
  
  // 联系人管理
  const [contacts, setContacts] = useState<SupplierContact[]>([]);
  const [loadingContacts, setLoadingContacts] = useState(false);
  const [showContactModal, setShowContactModal] = useState(false);
  const [editingContact, setEditingContact] = useState<SupplierContact | null>(null);
  const [contactForm, setContactForm] = useState<CreateContactRequest>({
    name: '',
    job_title: '',
    phone: '',
    email: '',
    wechat: '',
    qq: '',
    is_primary: false,
    remarks: ''
  });

  useEffect(() => {
    if (supplierId) {
      loadSupplier();
    }
  }, [supplierId]);

  // 当切换到风险评估标签时加载数据
  useEffect(() => {
    if (supplierId && activeTab === 'risk' && riskHistory.length === 0) {
      loadRiskHistory();
    }
  }, [supplierId, activeTab]);

  // 当切换到联系人标签时加载数据
  useEffect(() => {
    if (supplierId && activeTab === 'contacts' && contacts.length === 0) {
      loadContacts();
    }
  }, [supplierId, activeTab]);

  const loadSupplier = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getSupplier(parseInt(supplierId!));
      setSupplier(data);
    } catch (err: any) {
      setError(err.message || '加载供应商详情失败');
    } finally {
      setLoading(false);
    }
  };

  const loadRiskHistory = async () => {
    try {
      setLoadingRisk(true);
      const data = await getSupplierRiskHistory(parseInt(supplierId!));
      setRiskHistory(data);
    } catch (err: any) {
      console.error('加载风险评估历史失败:', err);
      setRiskHistory([]);
    } finally {
      setLoadingRisk(false);
    }
  };

  // 加载联系人列表
  const loadContacts = async () => {
    try {
      setLoadingContacts(true);
      const data = await getSupplierContacts(parseInt(supplierId!));
      setContacts(data);
    } catch (err: any) {
      console.error('加载联系人列表失败:', err);
      setContacts([]);
    } finally {
      setLoadingContacts(false);
    }
  };

  // 打开联系人模态框（新建）
  const openAddContactModal = () => {
    setEditingContact(null);
    setContactForm({
      name: '',
      job_title: '',
      phone: '',
      email: '',
      wechat: '',
      qq: '',
      is_primary: false,
      remarks: ''
    });
    setShowContactModal(true);
  };

  // 打开联系人模态框（编辑）
  const openEditContactModal = (contact: SupplierContact) => {
    setEditingContact(contact);
    setContactForm({
      name: contact.name,
      job_title: contact.job_title || '',
      phone: contact.phone || '',
      email: contact.email || '',
      wechat: contact.wechat || '',
      qq: contact.qq || '',
      is_primary: contact.is_primary,
      remarks: contact.remarks || ''
    });
    setShowContactModal(true);
  };

  // 保存联系人
  const handleSaveContact = async () => {
    try {
      if (editingContact) {
        // 更新
        await updateSupplierContact(parseInt(supplierId!), editingContact.id, contactForm);
      } else {
        // 新建
        await createSupplierContact(parseInt(supplierId!), contactForm);
      }
      setShowContactModal(false);
      loadContacts(); // 重新加载列表
    } catch (err: any) {
      alert(err.message || '保存联系人失败');
    }
  };

  // 删除联系人
  const handleDeleteContact = async (contactId: number) => {
    if (!confirm('确认删除该联系人？')) return;
    try {
      await deleteSupplierContact(Number(supplierId!), contactId);
      loadContacts(); // 重新加载列表
    } catch (err: any) {
      alert(err.message || '删除联系人失败');
    }
  };

  // 获取风险评分颜色
  const getRiskScoreColor = (score: number): string => {
    if (score < 30) return 'text-green-400';
    if (score < 60) return 'text-yellow-400';
    if (score < 80) return 'text-orange-400';
    return 'text-red-400';
  };

  // 获取风险评分背景色
  const getRiskScoreBg = (score: number): string => {
    if (score < 30) return 'bg-green-900/30 border-green-700/50';
    if (score < 60) return 'bg-yellow-900/30 border-yellow-700/50';
    if (score < 80) return 'bg-orange-900/30 border-orange-700/50';
    return 'bg-red-900/30 border-red-700/50';
  };

  // 获取风险等级徽章颜色
  const getRiskLevelBadge = (level: string): string => {
    const badges: Record<string, string> = {
      low: 'bg-green-900 text-green-200',
      medium: 'bg-yellow-900 text-yellow-200',
      high: 'bg-orange-900 text-orange-200',
      critical: 'bg-red-900 text-red-200',
    };
    return badges[level] || 'bg-gray-800 text-gray-400';
  };

  // 获取风险等级中文名
  const getRiskLevelText = (level: string): string => {
    const texts: Record<string, string> = {
      low: '低风险',
      medium: '中风险',
      high: '高风险',
      critical: '极高风险',
    };
    return texts[level] || level;
  };

  // 获取状态颜色
  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      active: 'text-green-400 bg-green-900/30',
      inactive: 'text-gray-400 bg-gray-800',
      suspended: 'text-orange-400 bg-orange-900/30',
      blacklist: 'text-red-400 bg-red-900/30',
    };
    return colors[status] || 'text-gray-400 bg-gray-800';
  };

  // 格式化日期
  const formatDate = (dateString?: string): string => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  };

  // 格式化日期时间
  const formatDateTime = (dateString?: string): string => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 格式化资本
  const formatCapital = (capital?: number): string => {
    if (!capital) return '-';
    if (capital >= 100000000) {
      return `${(capital / 100000000).toFixed(2)}亿`;
    }
    if (capital >= 10000) {
      return `${(capital / 10000).toFixed(2)}万`;
    }
    return capital.toFixed(2);
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-screen">
        <div className="text-gray-400 text-lg">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-screen">
        <div className="text-red-400 text-lg mb-4">错误: {error}</div>
        <button
          onClick={() => navigate('/business/suppliers/list')}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
        >
          返回列表
        </button>
      </div>
    );
  }

  if (!supplier) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-screen">
        <div className="text-gray-400 text-lg mb-4">供应商不存在</div>
        <button
          onClick={() => navigate('/business/suppliers/list')}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
        >
          返回列表
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* 头部：返回按钮 + 标题 + 状态 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/business/suppliers/list')}
            className="text-blue-400 hover:text-blue-300"
          >
            ← 返回列表
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white">{supplier.name}</h1>
            {supplier.name_en && (
              <p className="text-gray-400 mt-1">{supplier.name_en}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className={`px-3 py-1 rounded text-sm font-medium ${getStatusColor(supplier.status)}`}>
            {supplier.status === 'active' ? '活跃' : 
             supplier.status === 'inactive' ? '未激活' :
             supplier.status === 'suspended' ? '暂停' : '黑名单'}
          </span>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded">
            编辑
          </button>
        </div>
      </div>

      {/* 风险评分卡片（如果有） */}
      {supplier.risk_score !== undefined && (
        <div className={`border rounded-lg p-6 ${getRiskScoreBg(supplier.risk_score)}`}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white mb-2">风险评分</h3>
              <p className="text-gray-400 text-sm">最新评估结果</p>
            </div>
            <div className="text-right">
              <div className={`text-5xl font-bold ${getRiskScoreColor(supplier.risk_score)}`}>
                {supplier.risk_score.toFixed(1)}
              </div>
              <div className="text-gray-400 text-sm mt-2">
                {supplier.risk_score < 30 ? '低风险' :
                 supplier.risk_score < 60 ? '中风险' :
                 supplier.risk_score < 80 ? '高风险' : '极高风险'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab导航 */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg">
        <div className="flex border-b border-gray-700">
          <button
            onClick={() => setActiveTab('info')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'info' 
                ? 'text-blue-400 border-b-2 border-blue-400' 
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            基本信息
          </button>
          <button
            onClick={() => setActiveTab('contacts')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'contacts' 
                ? 'text-blue-400 border-b-2 border-blue-400' 
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            联系人
          </button>
          <button
            onClick={() => setActiveTab('certificates')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'certificates' 
                ? 'text-blue-400 border-b-2 border-blue-400' 
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            证书资质
          </button>
          <button
            onClick={() => setActiveTab('risk')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'risk' 
                ? 'text-blue-400 border-b-2 border-blue-400' 
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            风险评估
          </button>
        </div>

        {/* Tab内容区 */}
        <div className="p-6">
          {/* 基本信息 Tab */}
          {activeTab === 'info' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gray-700 rounded-lg p-6 space-y-4">
                <h3 className="text-lg font-semibold text-white mb-4">基本信息</h3>
                <div>
                  <label className="text-gray-400 text-sm">供应商ID</label>
                  <p className="text-white mt-1">{supplier.id}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">中文名称</label>
                  <p className="text-white mt-1">{supplier.name}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">英文名称</label>
                  <p className="text-white mt-1">{supplier.name_en || '-'}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">供应商类型</label>
                  <p className="text-white mt-1">{supplier.supplier_type || '-'}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">供应商等级</label>
                  <p className="text-white mt-1">{supplier.supplier_type || '-'}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">创建时间</label>
                  <p className="text-white mt-1">{formatDateTime(supplier.created_at)}</p>
                </div>
              </div>

              <div className="bg-gray-700 rounded-lg p-6 space-y-4">
                <h3 className="text-lg font-semibold text-white mb-4">公司信息</h3>
                <div>
                  <label className="text-gray-400 text-sm">统一社会信用代码</label>
                  <p className="text-white mt-1">{supplier.registration_number || '-'}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">注册资本</label>
                  <p className="text-white mt-1">
                    {supplier.registered_capital 
                      ? `${formatCapital(supplier.registered_capital)}元`
                      : '-'}
                  </p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">成立日期</label>
                  <p className="text-white mt-1">{formatDate(supplier.established_date)}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">法定代表人</label>
                  <p className="text-white mt-1">{supplier.legal_representative || '-'}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">注册地址</label>
                  <p className="text-white mt-1">{supplier.address || '-'}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">经营范围</label>
                  <p className="text-white mt-1 text-sm">{supplier.business_scope || '-'}</p>
                </div>
              </div>

              <div className="bg-gray-700 rounded-lg p-6 space-y-4">
                <h3 className="text-lg font-semibold text-white mb-4">联系方式</h3>
                <div>
                  <label className="text-gray-400 text-sm">联系电话</label>
                  <p className="text-white mt-1">{supplier.phone || '-'}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">联系邮箱</label>
                  <p className="text-white mt-1">{supplier.contact_email || '-'}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">官方网站</label>
                  <p className="text-white mt-1">
                    {supplier.website ? (
                      <a 
                        href={supplier.website} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:underline"
                      >
                        {supplier.website}
                      </a>
                    ) : '-'}
                  </p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">办公地址</label>
                  <p className="text-white mt-1">{supplier.address || '-'}</p>
                </div>
              </div>

              <div className="bg-gray-700 rounded-lg p-6 space-y-4">
                <h3 className="text-lg font-semibold text-white mb-4">备注信息</h3>
                <div>
                  <label className="text-gray-400 text-sm">备注</label>
                  <p className="text-white mt-1 text-sm">{supplier.description || '-'}</p>
                </div>
                <div>
                  <label className="text-gray-400 text-sm">最后更新</label>
                  <p className="text-white mt-1">{formatDateTime(supplier.updated_at)}</p>
                </div>
              </div>
            </div>
          )}

          {/* 联系人 Tab */}
          {activeTab === 'contacts' && (
            <div>
              {/* 操作栏 */}
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-semibold text-white">联系人列表</h3>
                <button
                  onClick={openAddContactModal}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  + 添加联系人
                </button>
              </div>

              {/* 联系人列表 */}
              {loadingContacts ? (
                <div className="text-center text-gray-400 py-12">加载中...</div>
              ) : contacts.length === 0 ? (
                <div className="text-center text-gray-400 py-12">
                  <p>暂无联系人</p>
                  <p className="text-sm mt-2">点击上方按钮添加联系人</p>
                </div>
              ) : (
                <div className="bg-gray-800 rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-700">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">姓名</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">职位</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">电话</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">邮箱</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">微信</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">主要联系人</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">操作</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {contacts.map((contact) => (
                        <tr key={contact.id} className="hover:bg-gray-700/50 transition-colors">
                          <td className="px-6 py-4 text-white">{contact.name}</td>
                          <td className="px-6 py-4 text-gray-400">{contact.job_title || '-'}</td>
                          <td className="px-6 py-4 text-gray-400">{contact.phone || '-'}</td>
                          <td className="px-6 py-4 text-gray-400">{contact.email || '-'}</td>
                          <td className="px-6 py-4 text-gray-400">{contact.wechat || '-'}</td>
                          <td className="px-6 py-4">
                            {contact.is_primary && (
                              <span className="inline-block px-2 py-1 bg-blue-600 text-white text-xs rounded">
                                主要联系人
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            <button
                              onClick={() => openEditContactModal(contact)}
                              className="text-blue-400 hover:text-blue-300 mr-4"
                            >
                              编辑
                            </button>
                            <button
                              onClick={() => handleDeleteContact(contact.id)}
                              className="text-red-400 hover:text-red-300"
                            >
                              删除
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* 证书资质 Tab */}
          {activeTab === 'certificates' && (
            <div className="text-center text-gray-400 py-12">
              <p className="mb-4">证书资质管理功能即将上线</p>
              <p className="text-sm">将在 Week 7 Day 5 实现完整的证书管理功能</p>
            </div>
          )}

          {/* 风险评估 Tab */}
          {activeTab === 'risk' && (
            <div>
              {loadingRisk ? (
                <div className="text-center text-gray-400 py-12">加载中...</div>
              ) : riskHistory.length === 0 ? (
                <div className="text-center text-gray-400 py-12">
                  <p className="mb-4">暂无风险评估记录</p>
                  <p className="text-sm">该供应商还没有进行过风险评估</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* 最新风险评估卡片 */}
                  <div className="bg-gray-700 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">最新风险评估</h3>
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                      <div className="text-center">
                        <p className="text-gray-400 text-sm mb-2">综合风险评分</p>
                        <p className={`text-3xl font-bold ${getRiskScoreColor(riskHistory[0].risk_score)}`}>
                          {riskHistory[0].risk_score}
                        </p>
                        <p className={`text-sm mt-2 px-2 py-1 rounded inline-block ${getRiskLevelBadge(riskHistory[0].risk_level)}`}>
                          {getRiskLevelText(riskHistory[0].risk_level)}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-400 text-sm mb-2">财务风险</p>
                        <p className="text-2xl font-bold text-white">{riskHistory[0].financial_risk || 0}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-400 text-sm mb-2">运营风险</p>
                        <p className="text-2xl font-bold text-white">{riskHistory[0].operational_risk || 0}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-400 text-sm mb-2">合规风险</p>
                        <p className="text-2xl font-bold text-white">{riskHistory[0].compliance_risk || 0}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-gray-400 text-sm mb-2">声誉风险</p>
                        <p className="text-2xl font-bold text-white">{riskHistory[0].reputation_risk || 0}</p>
                      </div>
                    </div>
                    <div className="mt-4 pt-4 border-t border-gray-600 flex justify-between items-center text-sm">
                      <span className="text-gray-400">
                        评估时间：
                        <span className="text-white ml-2">{formatDateTime(riskHistory[0].assessment_date)}</span>
                      </span>
                      <span className="text-gray-400">
                        评估人：
                        <span className="text-white ml-2">{riskHistory[0].assessed_by || '系统自动'}</span>
                      </span>
                    </div>
                    {riskHistory[0].findings && (
                      <div className="mt-3 pt-3 border-t border-gray-600">
                        <p className="text-gray-400 text-sm mb-1">评估说明：</p>
                        <p className="text-white text-sm">{riskHistory[0].findings}</p>
                      </div>
                    )}
                  </div>

                  {/* 历史评估记录表格 */}
                  <div className="bg-gray-700 rounded-lg overflow-hidden">
                    <h3 className="text-lg font-semibold text-white p-6 pb-4">风险评估历史</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-800">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">评估时间</th>
                            <th className="px-6 py-3 text-center text-xs font-medium text-gray-400 uppercase">综合评分</th>
                            <th className="px-6 py-3 text-center text-xs font-medium text-gray-400 uppercase">风险等级</th>
                            <th className="px-6 py-3 text-center text-xs font-medium text-gray-400 uppercase">财务</th>
                            <th className="px-6 py-3 text-center text-xs font-medium text-gray-400 uppercase">运营</th>
                            <th className="px-6 py-3 text-center text-xs font-medium text-gray-400 uppercase">合规</th>
                            <th className="px-6 py-3 text-center text-xs font-medium text-gray-400 uppercase">声誉</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">评估人</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-600">
                          {riskHistory.map((assessment) => (
                            <tr key={assessment.id} className="hover:bg-gray-600 transition-colors">
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                                {formatDate(assessment.assessment_date)}
                              </td>
                              <td className="px-6 py-4 text-center">
                                <span className={`text-sm font-semibold ${getRiskScoreColor(assessment.risk_score)}`}>
                                  {assessment.risk_score}
                                </span>
                              </td>
                              <td className="px-6 py-4 text-center">
                                <span className={`px-2 py-1 text-xs font-medium rounded ${getRiskLevelBadge(assessment.risk_level)}`}>
                                  {getRiskLevelText(assessment.risk_level)}
                                </span>
                              </td>
                              <td className="px-6 py-4 text-center text-sm text-white">
                                {assessment.financial_risk || '-'}
                              </td>
                              <td className="px-6 py-4 text-center text-sm text-white">
                                {assessment.operational_risk || '-'}
                              </td>
                              <td className="px-6 py-4 text-center text-sm text-white">
                                {assessment.compliance_risk || '-'}
                              </td>
                              <td className="px-6 py-4 text-center text-sm text-white">
                                {assessment.reputation_risk || '-'}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                                {assessment.assessed_by || '系统自动'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 联系人编辑模态框 */}
      {showContactModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-xl font-semibold text-white mb-4">
              {editingContact ? '编辑联系人' : '添加联系人'}
            </h3>

            <div className="space-y-4">
              {/* 姓名 */}
              <div>
                <label className="block text-gray-400 text-sm mb-1">姓名 *</label>
                <input
                  type="text"
                  value={contactForm.name}
                  onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                  placeholder="请输入姓名"
                />
              </div>

              {/* 职位 */}
              <div>
                <label className="block text-gray-400 text-sm mb-1">职位</label>
                <input
                  type="text"
                  value={contactForm.job_title}
                  onChange={(e) => setContactForm({ ...contactForm, job_title: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                  placeholder="例：销售经理"
                />
              </div>

              {/* 电话 */}
              <div>
                <label className="block text-gray-400 text-sm mb-1">电话</label>
                <input
                  type="text"
                  value={contactForm.phone}
                  onChange={(e) => setContactForm({ ...contactForm, phone: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                  placeholder="请输入电话号码"
                />
              </div>

              {/* 邮箱 */}
              <div>
                <label className="block text-gray-400 text-sm mb-1">邮箱</label>
                <input
                  type="email"
                  value={contactForm.email}
                  onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                  placeholder="请输入邮箱地址"
                />
              </div>

              {/* 微信 */}
              <div>
                <label className="block text-gray-400 text-sm mb-1">微信</label>
                <input
                  type="text"
                  value={contactForm.wechat}
                  onChange={(e) => setContactForm({ ...contactForm, wechat: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                  placeholder="请输入微信号"
                />
              </div>

              {/* QQ */}
              <div>
                <label className="block text-gray-400 text-sm mb-1">QQ</label>
                <input
                  type="text"
                  value={contactForm.qq}
                  onChange={(e) => setContactForm({ ...contactForm, qq: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                  placeholder="请输入QQ号"
                />
              </div>

              {/* 主要联系人 */}
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={contactForm.is_primary}
                  onChange={(e) => setContactForm({ ...contactForm, is_primary: e.target.checked })}
                  className="mr-2"
                />
                <label className="text-gray-400 text-sm">设为主要联系人</label>
              </div>

              {/* 备注 */}
              <div>
                <label className="block text-gray-400 text-sm mb-1">备注</label>
                <textarea
                  value={contactForm.remarks}
                  onChange={(e) => setContactForm({ ...contactForm, remarks: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                  rows={3}
                  placeholder="选填"
                />
              </div>
            </div>

            {/* 按钮 */}
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowContactModal(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSaveContact}
                disabled={!contactForm.name}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default SupplierDetailPage;

