import { useState } from 'react';
import { Upload, FileSpreadsheet, AlertCircle, X, Search, CheckCircle } from 'lucide-react';
import api from '../../lib/api';
import { Button } from '../../components/ui/Button';
import LoadingModal from '../../components/ui/LoadingModal';

interface CleanerProps {
    toolType: 'sales' | 'analysis' | 'production';
}

interface FileMetadata {
    filename: string;
    sucursal: string;
    rango_fechas: string;
}

const TOOL_CONFIG = {
    sales: {
        title: 'Limpieza de Ventas',
        description: 'Sube reportes de ventas diarios (CSV/Excel). Detecta sucursal, ofertas y genera hash único.',
        endpoint: '/tools/clean-sales'
    },
    analysis: {
        title: 'Análisis de Tamales',
        description: 'Genera reporte con pestañas: Total, Fuera de Paquete y En Combos. (Sube múltiples CSV/Excel).',
        endpoint: '/tools/clean-analysis'
    },
    production: {
        title: 'Filtro de Producción',
        description: 'Procesa reporte semanal de producción. Extrae Tradicional, HP y Borracho.',
        endpoint: '/tools/clean-production'
    }
};

export default function Cleaner({ toolType }: CleanerProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [fileMetadata, setFileMetadata] = useState<FileMetadata[]>([]);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [downloadFormat, setDownloadFormat] = useState<'csv' | 'xlsx'>('csv');
  const [isScanning, setIsScanning] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const config = TOOL_CONFIG[toolType];

  const scanFiles = async (filesToScan: File[]) => {
      setIsScanning(true);
      const formData = new FormData();
      filesToScan.forEach(f => formData.append('files', f));

      try {
          const response = await api.post('/tools/scan', formData);
          setFileMetadata(prev => [...prev, ...response.data]);
      } catch (err) {
          console.error("Error scanning files", err);
      } finally {
          setIsScanning(false);
      }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setFiles(prev => [...prev, ...newFiles]);
      setError(null);
      setSuccess(false);
      
      // Auto scan new files
      scanFiles(newFiles);
    }
  };

  const removeFile = (index: number) => {
      setFiles(prev => prev.filter((_, i) => i !== index));
      setFileMetadata(prev => prev.filter((_, i) => i !== index));
  };

  const handleProcess = async () => {
    if (files.length === 0) return;

    setIsProcessing(true);
    setLoadingMessage('Procesando archivos...');
    setError(null);

    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    formData.append('format', downloadFormat);
    
    if (toolType === 'production') {
        if (!startDate || !endDate) {
            setError("Debes seleccionar un rango de fechas para el reporte.");
            setIsProcessing(false);
            return;
        }
        formData.append('start_date', startDate);
        formData.append('end_date', endDate);
    }

    try {
      const response = await api.post(config.endpoint, formData, {
        responseType: 'blob',
      });

      // Download logic
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Get filename from header or default
      const contentDisposition = response.headers['content-disposition'];
      
      // Default name fallback if header fails (dynamic part handled by backend usually)
      let filename = `result_${toolType}.${downloadFormat}`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch && filenameMatch.length >= 2) {
            // Remove quotes if present and decode
            filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setSuccess(true);
    } catch (err: unknown) {
      console.error(err);
      const error = err as { response?: { data?: Blob } };
      if (error.response?.data instanceof Blob) {
         // Read blob error
         const text = await error.response.data.text();
         try {
             const json = JSON.parse(text);
             setError(json.detail || 'Error al procesar archivos');
         } catch {
             setError('Error al procesar archivos');
         }
      } else {
          setError('Error de conexión o del servidor');
      }
    } finally {
      setIsProcessing(false);
      setUploadProgress(0);
    }
  };

  return (
    <div className="space-y-6">
      <LoadingModal 
        isOpen={isProcessing} 
        message={loadingMessage} 
        progress={uploadProgress < 100 ? uploadProgress : undefined}
        isIndeterminate={uploadProgress === 100}
      />
      <div className="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
        <div className="md:grid md:grid-cols-3 md:gap-6">
          <div className="md:col-span-1">
            <h3 className="text-lg font-medium leading-6 text-gray-900">{config.title}</h3>
            <p className="mt-1 text-sm text-gray-500">
              {config.description}
            </p>
            <div className="mt-4 text-xs text-gray-400">
                <p>Soporta múltiples archivos.</p>
                <p>Formatos: .xlsx, .csv</p>
            </div>
          </div>
          <div className="mt-5 md:mt-0 md:col-span-2">
            <div className="flex flex-col items-center justify-center w-full">
              <label
                htmlFor="dropzone-file"
                className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors"
              >
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <Upload className="w-8 h-8 text-gray-400 mb-2" />
                    <p className="mb-1 text-sm text-gray-500">
                    <span className="font-semibold">Click para subir</span> o arrastra archivos
                    </p>
                </div>
                <input id="dropzone-file" type="file" className="hidden" onChange={handleFileChange} multiple accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel" />
              </label>
            </div>
            
            {/* Date Range for Production Tool */}
            {toolType === 'production' && (
                <div className="mt-4 grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Fecha Inicial</label>
                        <input 
                            type="date" 
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Fecha Final</label>
                        <input 
                            type="date" 
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                        />
                    </div>
                </div>
            )}

            {/* File List & Quick Scan Results */}
            {files.length > 0 && (
                <div className="mt-6 bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
                    <div className="px-4 py-3 border-b border-gray-200 bg-gray-100 flex justify-between items-center">
                        <h4 className="text-sm font-medium text-gray-700">Archivos Cargados ({files.length})</h4>
                        {isScanning && <span className="text-xs text-blue-600 flex items-center"><Search className="w-3 h-3 mr-1 animate-spin" /> Escaneando metadatos...</span>}
                    </div>
                    <ul className="divide-y divide-gray-200 max-h-60 overflow-y-auto">
                        {files.map((f, idx) => {
                            const meta = fileMetadata.find(m => m.filename === f.name);
                            return (
                                <li key={idx} className="px-4 py-3 flex items-center justify-between hover:bg-white transition-colors">
                                    <div className="flex items-center space-x-3 overflow-hidden">
                                        <FileSpreadsheet className="w-5 h-5 text-green-600 flex-shrink-0" />
                                        <div className="min-w-0">
                                            <p className="text-sm font-medium text-gray-900 truncate">{f.name}</p>
                                            <div className="flex space-x-2 text-xs text-gray-500">
                                                <span>{(f.size / 1024).toFixed(1)} KB</span>
                                                {meta && (
                                                    <>
                                                        <span className="text-gray-300">|</span>
                                                        <span className={meta.sucursal === 'Desconocida' ? 'text-orange-500' : 'text-blue-600 font-medium'}>
                                                            {meta.sucursal}
                                                        </span>
                                                        {meta.rango_fechas && meta.rango_fechas !== 'No detectado' && (
                                                            <>
                                                                <span className="text-gray-300">|</span>
                                                                <span className="text-gray-700">{meta.rango_fechas}</span>
                                                            </>
                                                        )}
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <button onClick={() => removeFile(idx)} className="text-gray-400 hover:text-red-500 transition-colors">
                                        <X className="w-5 h-5" />
                                    </button>
                                </li>
                            );
                        })}
                    </ul>
                </div>
            )}

            {/* Format Selection */}
            <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">Formato de Descarga</label>
                <div className="flex space-x-4">
                    <label className="inline-flex items-center">
                        <input
                            type="radio"
                            className="form-radio text-blue-600"
                            name="format"
                            value="csv"
                            checked={downloadFormat === 'csv'}
                            onChange={(e) => setDownloadFormat(e.target.value as 'csv')}
                        />
                        <span className="ml-2 text-sm text-gray-700">CSV (.csv)</span>
                    </label>
                    <label className="inline-flex items-center">
                        <input
                            type="radio"
                            className="form-radio text-blue-600"
                            name="format"
                            value="xlsx"
                            checked={downloadFormat === 'xlsx'}
                            onChange={(e) => setDownloadFormat(e.target.value as 'xlsx')}
                        />
                        <span className="ml-2 text-sm text-gray-700">Excel (.xlsx)</span>
                    </label>
                </div>
            </div>

            {error && (
              <div className="mt-4 bg-red-50 border border-red-200 rounded-md p-4 flex items-start">
                <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 mr-3" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {success && (
              <div className="mt-4 bg-green-50 border border-green-200 rounded-md p-4 flex items-start">
                <CheckCircle className="h-5 w-5 text-green-400 mt-0.5 mr-3" />
                <p className="text-sm text-green-700">¡Proceso completado! La descarga comenzó automáticamente.</p>
              </div>
            )}

            <div className="mt-6 flex justify-end">
              <Button onClick={handleProcess} disabled={files.length === 0} isLoading={isProcessing}>
                {isProcessing ? 'Procesando...' : `Ejecutar ${config.title}`}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
