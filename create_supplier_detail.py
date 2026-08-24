# -*- coding: utf-8 -*-
import os

# 内容太长,分段写入
part1 = r"""/**
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
  SupplierRiskAssessment 
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

  const loadSupplier = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getSupplier(supplierId!);
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
      const data = await getSupplierRiskHistory(supplierId!);
      setRiskHistory(data);
    } catch (err: any) {
      console.error('加载风险评估历史失败:', err);
      setRiskHistory([]);
    } finally {
      setLoadingRisk(false);
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
"""

# Part 2 内容（Tab Content继续）
part2 = r"""
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
                  <p className="text-white mt-1">{supplier.supplier_level || '-'}</p>
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
                  <p className="text-white mt-1">{supplier.unified_social_credit_code || '-'}</p>
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
                  <p className="text-white mt-1">{supplier.registered_address || '-'}</p>
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
                  <p className="text-white mt-1">{supplier.contact_phone || '-'}</p>
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
                  <p className="text-white mt-1">{supplier.office_address || '-'}</p>
                </div>
              </div>

              <div className="bg-gray-700 rounded-lg p-6 space-y-4">
                <h3 className="text-lg font-semibold text-white mb-4">备注信息</h3>
                <div>
                  <label className="text-gray-400 text-sm">备注</label>
                  <p className="text-white mt-1 text-sm">{supplier.remarks || '-'}</p>
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
            <div className="text-center text-gray-400 py-12">
              <p className="mb-4">联系人管理功能即将上线</p>
              <p className="text-sm">将在 Week 7 Day 4 实现完整的联系人 CRUD 功能</p>
            </div>
          )}

          {/* 证书资质 Tab */}
          {activeTab === 'certificates' && (
            <div className="text-center text-gray-400 py-12">
              <p className="mb-4">证书资质管理功能即将上线</p>
              <p className="text-sm">将在 Week 7 Day 5 实现完整的证书管理功能</p>
            </div>
          )}
"""

# Part 3 风险评估Tab
part3 = r"""
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
                    {riskHistory[0].notes && (
                      <div className="mt-3 pt-3 border-t border-gray-600">
                        <p className="text-gray-400 text-sm mb-1">评估说明：</p>
                        <p className="text-white text-sm">{riskHistory[0].notes}</p>
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
    </div>
  );
};

export default SupplierDetailPage;
"""

# 合并并写入文件
full_content = part1 + part2 + part3

target_file = os.path.join('frontend', 'src', 'pages', 'business', 'SupplierDetailPage.tsx')
with open(target_file, 'w', encoding='utf-8') as f:
    f.write(full_content)

print(f"✅ File created successfully: {target_file}")
print(f"📝 Total lines: {len(full_content.splitlines())}")
