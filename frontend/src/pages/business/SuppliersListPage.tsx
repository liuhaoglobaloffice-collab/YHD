/**
 * LiuHao AI-OS Y1.0
 * Suppliers List Page - 供应商列表页面
 * Week 6 Day 3-4 + Week 7 Day 1-2
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getSuppliers,
  Supplier,
  SupplierStatus,
  SupplierType,
  SupplierQueryParams,
  PaginatedResponse,
} from '../../services/supplierAPI';

const SuppliersListPage = () => {
  const navigate = useNavigate();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  // 分页状态
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalItems, setTotalItems] = useState<number>(0);
  const pageSize = 20;
  
  // 筛选条件
  const [statusFilter, setStatusFilter] = useState<SupplierStatus | ''>('');
  const [typeFilter, setTypeFilter] = useState<SupplierType | ''>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  /**
   * 加载供应商列表
   */
  const loadSuppliers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params: SupplierQueryParams = {
        page: currentPage,
        page_size: pageSize,
      };
      
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.supplier_type = typeFilter;
      if (searchQuery) params.search = searchQuery;
      
      const response: PaginatedResponse<Supplier> = await getSuppliers(params);
      
      setSuppliers(response.items);
      setTotalPages(response.total_pages);
      setTotalItems(response.total);
    } catch (err: any) {
      console.error('加载供应商列表失败:', err);
      setError(err.response?.data?.detail || '加载供应商列表失败');
      setSuppliers([]);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 初始加载 & 条件变化时重新加载
   */
  useEffect(() => {
    loadSuppliers();
  }, [currentPage, statusFilter, typeFilter, searchQuery]);

  /**
   * 处理搜索
   */
  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setCurrentPage(1); // 搜索时重置到第一页
  };

  /**
   * 处理分页
   */
  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  /**
   * 跳转到供应商详情页
   */
  const handleViewSupplier = (supplierId: number) => {
    navigate(`/business/suppliers/${supplierId}`);
  };

  /**
   * 状态标签样式
   */
  const getStatusBadge = (status: SupplierStatus) => {
    const badges = {
      active: 'bg-green-600 text-white',
      inactive: 'bg-gray-600 text-gray-300',
      suspended: 'bg-yellow-600 text-gray-900',
      blacklisted: 'bg-red-600 text-white',
    };
    return badges[status] || 'bg-gray-600 text-white';
  };

  /**
   * 类型标签样式
   */
  const getTypeBadge = (type: SupplierType) => {
    const badges = {
      manufacturer: 'bg-blue-600 text-white',
      trader: 'bg-purple-600 text-white',
      agent: 'bg-orange-600 text-white',
      service_provider: 'bg-teal-600 text-white',
    };
    return badges[type] || 'bg-gray-600 text-white';
  };

  /**
   * 格式化供应商类型
   */
  const formatSupplierType = (type: SupplierType) => {
    const types = {
      manufacturer: '制造商',
      trader: '贸易商',
      agent: '代理商',
      service_provider: '服务商',
    };
    return types[type] || type;
  };

  /**
   * 格式化状态
   */
  const formatStatus = (status: SupplierStatus) => {
    const statuses = {
      active: '正常',
      inactive: '停用',
      suspended: '暂停',
      blacklisted: '黑名单',
    };
    return statuses[status] || status;
  };

  return (
    <div className="p-6 bg-gray-900 min-h-screen text-white">
      {/* 页面标题 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">供应商管理</h1>
        <p className="text-gray-400 mt-2">管理和查看所有供应商信息</p>
      </div>

      {/* 筛选栏 */}
      <div className="bg-gray-800 rounded-lg p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* 搜索框 */}
          <div className="md:col-span-2">
            <input
              type="text"
              placeholder="搜索供应商名称..."
              className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 focus:outline-none focus:border-blue-500"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
            />
          </div>

          {/* 状态筛选 */}
          <div>
            <select
              className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 focus:outline-none focus:border-blue-500"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as SupplierStatus | '');
                setCurrentPage(1);
              }}
            >
              <option value="">所有状态</option>
              <option value="active">正常</option>
              <option value="inactive">停用</option>
              <option value="suspended">暂停</option>
              <option value="blacklisted">黑名单</option>
            </select>
          </div>

          {/* 类型筛选 */}
          <div>
            <select
              className="w-full px-4 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 focus:outline-none focus:border-blue-500"
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value as SupplierType | '');
                setCurrentPage(1);
              }}
            >
              <option value="">所有类型</option>
              <option value="manufacturer">制造商</option>
              <option value="trader">贸易商</option>
              <option value="agent">代理商</option>
              <option value="service_provider">服务商</option>
            </select>
          </div>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-600 text-white px-4 py-3 rounded-lg mb-6">
          <p className="font-semibold">错误</p>
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* 加载状态 */}
      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      )}

      {/* 供应商列表 */}
      {!loading && suppliers.length > 0 && (
        <>
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    供应商名称
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    类型
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    行业
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    状态
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    风险评分
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {suppliers.map((supplier) => (
                  <tr key={supplier.id} className="hover:bg-gray-700 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <div className="font-semibold text-white">{supplier.name}</div>
                        {supplier.name_en && (
                          <div className="text-sm text-gray-400">{supplier.name_en}</div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs font-semibold rounded ${getTypeBadge(supplier.supplier_type)}`}>
                        {formatSupplierType(supplier.supplier_type)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-300">
                      {supplier.industry || '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs font-semibold rounded ${getStatusBadge(supplier.status)}`}>
                        {formatStatus(supplier.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {supplier.risk_score !== undefined ? (
                        <span
                          className={`px-2 py-1 text-xs font-semibold rounded ${
                            supplier.risk_score < 30
                              ? 'bg-green-600 text-white'
                              : supplier.risk_score < 60
                              ? 'bg-yellow-600 text-gray-900'
                              : supplier.risk_score < 80
                              ? 'bg-orange-600 text-white'
                              : 'bg-red-600 text-white'
                          }`}
                        >
                          {supplier.risk_score}
                        </span>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleViewSupplier(supplier.id)}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                      >
                        查看
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 分页控件 */}
          <div className="mt-6 flex justify-between items-center">
            <div className="text-gray-400 text-sm">
              共 {totalItems} 条记录，第 {currentPage} / {totalPages} 页
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                上一页
              </button>
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下一页
              </button>
            </div>
          </div>
        </>
      )}

      {/* 空状态 */}
      {!loading && suppliers.length === 0 && (
        <div className="bg-gray-800 rounded-lg p-12 text-center">
          <p className="text-gray-400 text-lg">暂无供应商数据</p>
          <p className="text-gray-500 text-sm mt-2">请调整筛选条件或添加新供应商</p>
        </div>
      )}
    </div>
  );
};

export default SuppliersListPage;
