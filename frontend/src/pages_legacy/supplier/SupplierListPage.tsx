/**
 * 供应商情报系统 - 供应商列表页面
 * Module 48 - Supplier Intelligence
 */

import { useState, useEffect } from 'react';
import { 
  Building2, 
  Search, 
  Filter, 
  Plus, 
  Edit, 
  Trash2, 
  Eye,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { apiService } from '../../services/api';

interface Supplier {
  id: string;
  name: string;
  business_type: string;
  status: string;
  risk_level: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  website?: string;
  address?: string;
  created_at: string;
  updated_at: string;
}

const SupplierListPage = () => {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterBusinessType, setFilterBusinessType] = useState<string>('all');

  useEffect(() => {
    loadSuppliers();
  }, [filterStatus, filterBusinessType]);

  const loadSuppliers = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (filterStatus !== 'all') params.status = filterStatus;
      if (filterBusinessType !== 'all') params.supplier_type = filterBusinessType;
      
      const response = await apiService.get('/api/v1/suppliers', { params });
      setSuppliers(response.data);
    } catch (error) {
      console.error('加载供应商列表失败:', error);
      // 使用模拟数据用于演示
      setSuppliers([
        {
          id: '1',
          name: '深圳科技有限公司',
          business_type: 'manufacturer',
          status: 'active',
          risk_level: 'low',
          contact_name: '张伟',
          contact_email: 'zhangwei@example.com',
          contact_phone: '13800138000',
          website: 'https://example.com',
          address: '深圳市南山区科技园',
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-01-20T15:30:00Z'
        },
        {
          id: '2',
          name: '广州贸易集团',
          business_type: 'trading',
          status: 'active',
          risk_level: 'medium',
          contact_name: '李娜',
          contact_email: 'lina@example.com',
          contact_phone: '13900139000',
          website: 'https://example.org',
          address: '广州市天河区商业大道',
          created_at: '2024-01-10T09:00:00Z',
          updated_at: '2024-01-18T14:20:00Z'
        },
        {
          id: '3',
          name: '上海代理商',
          business_type: 'agent',
          status: 'inactive',
          risk_level: 'high',
          contact_name: '王强',
          contact_email: 'wangqiang@example.com',
          contact_phone: '13700137000',
          address: '上海市浦东新区',
          created_at: '2024-01-05T08:00:00Z',
          updated_at: '2024-01-12T11:45:00Z'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const filteredSuppliers = suppliers.filter(supplier => 
    supplier.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    supplier.contact_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusBadge = (status: string) => {
    const styles = {
      active: 'bg-green-100 text-green-800 border-green-300',
      inactive: 'bg-gray-100 text-gray-800 border-gray-300',
      blacklist: 'bg-red-100 text-red-800 border-red-300',
      pending: 'bg-yellow-100 text-yellow-800 border-yellow-300'
    };
    const labels = {
      active: '活跃',
      inactive: '停用',
      blacklist: '黑名单',
      pending: '待审核'
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${styles[status as keyof typeof styles] || styles.active}`}>
        {labels[status as keyof typeof labels] || status}
      </span>
    );
  };

  const getRiskBadge = (risk: string) => {
    const config = {
      low: { icon: CheckCircle, color: 'text-green-600', label: '低风险' },
      medium: { icon: TrendingUp, color: 'text-yellow-600', label: '中等' },
      high: { icon: TrendingDown, color: 'text-orange-600', label: '高风险' },
      critical: { icon: AlertTriangle, color: 'text-red-600', label: '极高' }
    };
    const { icon: Icon, color, label } = config[risk as keyof typeof config] || config.low;
    return (
      <div className={`flex items-center space-x-1 ${color}`}>
        <Icon size={14} />
        <span className="text-xs font-medium">{label}</span>
      </div>
    );
  };

  const getBusinessTypeLabel = (type: string) => {
    const labels = {
      manufacturer: '制造商',
      trading: '贸易商',
      agent: '代理商',
      distributor: '分销商',
      service: '服务商'
    };
    return labels[type as keyof typeof labels] || type;
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* 页面头部 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Building2 className="text-blue-600" size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">供应商情报系统</h1>
              <p className="text-sm text-gray-500">管理和监控供应商信息</p>
            </div>
          </div>
          <button 
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            onClick={() => alert('添加供应商功能开发中')}
          >
            <Plus size={18} />
            <span>添加供应商</span>
          </button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="px-6 py-4 bg-white border-b border-gray-200">
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
            <div className="text-sm text-blue-700 font-medium mb-1">总供应商</div>
            <div className="text-3xl font-bold text-blue-900">{suppliers.length}</div>
          </div>
          <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4 border border-green-200">
            <div className="text-sm text-green-700 font-medium mb-1">活跃中</div>
            <div className="text-3xl font-bold text-green-900">
              {suppliers.filter(s => s.status === 'active').length}
            </div>
          </div>
          <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded-lg p-4 border border-yellow-200">
            <div className="text-sm text-yellow-700 font-medium mb-1">待审核</div>
            <div className="text-3xl font-bold text-yellow-900">
              {suppliers.filter(s => s.status === 'pending').length}
            </div>
          </div>
          <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-lg p-4 border border-red-200">
            <div className="text-sm text-red-700 font-medium mb-1">高风险</div>
            <div className="text-3xl font-bold text-red-900">
              {suppliers.filter(s => s.risk_level === 'high' || s.risk_level === 'critical').length}
            </div>
          </div>
        </div>
      </div>

      {/* 搜索和筛选栏 */}
      <div className="px-6 py-4 bg-white border-b border-gray-200">
        <div className="flex items-center space-x-4">
          {/* 搜索框 */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
            <input
              type="text"
              placeholder="搜索供应商名称或联系人..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* 状态筛选 */}
          <div className="flex items-center space-x-2">
            <Filter size={18} className="text-gray-500" />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">全部状态</option>
              <option value="active">活跃</option>
              <option value="inactive">停用</option>
              <option value="pending">待审核</option>
              <option value="blacklist">黑名单</option>
            </select>
          </div>

          {/* 类型筛选 */}
          <select
            value={filterBusinessType}
            onChange={(e) => setFilterBusinessType(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">全部类型</option>
            <option value="manufacturer">制造商</option>
            <option value="trading">贸易商</option>
            <option value="agent">代理商</option>
            <option value="distributor">分销商</option>
            <option value="service">服务商</option>
          </select>
        </div>
      </div>

      {/* 供应商列表 */}
      <div className="flex-1 overflow-auto px-6 py-4">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
          </div>
        ) : filteredSuppliers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <Building2 size={48} className="mb-4 opacity-50" />
            <p className="text-lg">暂无供应商数据</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    供应商信息
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    类型
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    状态
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    风险等级
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    联系方式
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredSuppliers.map((supplier) => (
                  <tr key={supplier.id} className="hover:bg-gray-50 transition">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 bg-gradient-to-br from-blue-400 to-blue-600 rounded-lg flex items-center justify-center">
                          <Building2 size={20} className="text-white" />
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{supplier.name}</div>
                          <div className="text-xs text-gray-500">{supplier.address}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-700">
                        {getBusinessTypeLabel(supplier.business_type)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(supplier.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getRiskBadge(supplier.risk_level)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">{supplier.contact_name}</div>
                      <div className="text-xs text-gray-500">{supplier.contact_email}</div>
                      <div className="text-xs text-gray-500">{supplier.contact_phone}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end space-x-2">
                        <button
                          onClick={() => alert(`查看供应商: ${supplier.name}`)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition"
                          title="查看详情"
                        >
                          <Eye size={16} />
                        </button>
                        <button
                          onClick={() => alert(`编辑供应商: ${supplier.name}`)}
                          className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition"
                          title="编辑"
                        >
                          <Edit size={16} />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`确定要删除供应商 "${supplier.name}" 吗？`)) {
                              alert('删除功能开发中');
                            }
                          }}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                          title="删除"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default SupplierListPage;
