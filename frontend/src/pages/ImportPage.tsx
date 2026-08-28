import { useEffect, useRef, useState } from 'react';
import {
  downloadImportTemplate,
  fetchImports,
  IMPORT_TYPES,
  uploadImport,
  type ImportRecordItem,
  type ImportResult,
} from '../services/imports';
import { useI18n } from '../i18n';

const STATUS_LABELS: Record<string, string> = {
  processing: '处理中',
  completed: '完成',
  partial: '部分成功',
  failed: '失败',
};

const TYPE_LABELS: Record<string, string> = {
  supplier: '供应商',
  customer: '客户',
  contract: '合同',
  quotation: '报价',
};

export function ImportPage() {
  const { t } = useI18n();
  const [importType, setImportType] = useState('supplier');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [records, setRecords] = useState<ImportRecordItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState('');

  const loadRecords = async () => {
    try {
      const data = await fetchImports(1, 20);
      setRecords(data.items);
    } catch (e) {
      console.error('Failed to load import records', e);
      setListError('加载导入记录失败');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadRecords();
  }, []);

  const handleFileChange = (file: File | null) => {
    setSelectedFile(file);
    setResult(null);
    setUploadError('');
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setUploadError('');
    setResult(null);
    const isCsv = selectedFile.name.toLowerCase().endsWith('.csv');
    try {
      const res = await uploadImport(importType, selectedFile, isCsv ? 'csv' : 'excel');
      setResult(res);
      loadRecords();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : '导入失败');
    }
    setUploading(false);
  };

  return (
    <section className="page">
      <h1>{t('dataImport')}</h1>
      <p className="card-desc">{t('dataImportDesc')}</p>

      {/* 导入区 */}
      <div className="import-panel">
        <div className="import-controls">
          <div className="form-group">
            <label>{t('importType')}</label>
            <select value={importType} onChange={(e) => setImportType(e.target.value)}>
              {IMPORT_TYPES.map((tp) => (
                <option key={tp.value} value={tp.value}>
                  {tp.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>{t('importFile')}</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
            />
          </div>
          <div className="import-actions">
            <button
              className="btn btn-sm"
              onClick={() => downloadImportTemplate(importType).catch((e) => setUploadError(e.message))}
            >
              {t('downloadTemplate')}
            </button>
            <button
              className="btn btn-submit"
              onClick={handleUpload}
              disabled={uploading || !selectedFile}
            >
              {uploading ? '导入中...' : t('startImport')}
            </button>
          </div>
        </div>

        {selectedFile && (
          <div className="import-file-chip">
            已选择: {selectedFile.name}（{(selectedFile.size / 1024).toFixed(1)} KB）
          </div>
        )}

        {uploadError && (
          <div className="modal-error">
            <strong>错误：</strong> {uploadError}
          </div>
        )}

        {result && (
          <div className={`import-result st-${result.status}`}>
            <div className="result-header">
              <span className={`result-status status-${result.status}`}>
                {STATUS_LABELS[result.status] ?? result.status}
              </span>
              <span className="result-time">记录 #{result.import_record_id}</span>
            </div>
            <div className="import-stats">
              <span>共 {result.total} 条</span>
              <span className="ok">成功 {result.success}</span>
              <span className="bad">失败 {result.failed}</span>
            </div>
            {result.errors && result.errors.length > 0 && (
              <div className="import-errors">
                {result.errors.slice(0, 10).map((err, i) => (
                  <div key={i} className="import-error-line">
                    第 {err.row} 行: {err.error}
                  </div>
                ))}
                {result.errors.length > 10 && (
                  <div className="import-error-more">... 共 {result.errors.length} 条错误</div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 导入历史 */}
      <div className="import-history">
        <div className="executions-header">
          <strong>{t('importHistory')}</strong>
          <span className="executions-count">{loading ? '...' : `${records.length} 条`}</span>
        </div>
        {loading ? (
          <p>{t('loading')}</p>
        ) : listError ? (
          <p className="error-text">{listError}</p>
        ) : records.length === 0 ? (
          <p className="executions-empty">{t('noImportRecords')}</p>
        ) : (
          <div className="import-record-list">
            {records.map((rec) => (
              <div key={rec.id} className={`import-record-item st-${rec.status}`}>
                <div className="execution-item-main">
                  <span className="execution-employee">{TYPE_LABELS[rec.import_type] ?? rec.import_type}</span>
                  <span className="import-filename">{rec.filename}</span>
                  <span className={`execution-status st-${rec.status}`}>
                    {STATUS_LABELS[rec.status] ?? rec.status}
                  </span>
                </div>
                <div className="execution-item-sub">
                  <span>
                    共 {rec.total} · 成功 {rec.success} · 失败 {rec.failed}
                  </span>
                  {rec.created_at && (
                    <span className="execution-time">
                      {new Date(rec.created_at).toLocaleString()}
                    </span>
                  )}
                </div>
                {rec.errors && rec.errors.length > 0 && (
                  <div className="execution-error">
                    {rec.errors.slice(0, 3).map((err, i) => (
                      <div key={i}>第 {err.row} 行: {err.error}</div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
