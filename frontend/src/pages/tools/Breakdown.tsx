
import { useState, useEffect } from 'react';
import { Upload, Filter, Table, Pin } from 'lucide-react';
import api from '../../lib/api';
import { Button } from '../../components/ui/Button';

export default function Breakdown() {
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  
  // Pinned File State
  const [hasPinnedFile, setHasPinnedFile] = useState(false);
  const [usePinnedFile, setUsePinnedFile] = useState(false);
  const [pinnedFileInfo, setPinnedFileInfo] = useState<any>(null);

  // Filters
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedSucursales, setSelectedSucursales] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<'daily' | 'weekly' | 'monthly'>('daily');

  useEffect(() => {
    // Check for pinned file
    api.get('/tools/pinned-analysis')
      .then(res => {
        if (res.data.file_info) {
          setHasPinnedFile(true);
          setPinnedFileInfo(res.data.file_info);
          setUsePinnedFile(true); // Default to use pinned if available
        }
      })
      .catch(err => console.error("Error checking pinned file:", err));
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files));
      setUsePinnedFile(false); // Switch to manual upload
      setData(null);
    }
  };

  const handleAnalyze = async () => {
    if (files.length === 0 && !usePinnedFile) return;
    
    setLoading(true);

    const formData = new FormData();
    
    if (usePinnedFile) {
        formData.append('use_pinned_file', 'true');
    } else {
        files.forEach(f => formData.append('files', f));
    }

    if (startDate) formData.append('start_date', startDate);
    if (endDate) formData.append('end_date', endDate);
    if (selectedSucursales.length > 0) formData.append('sucursales', selectedSucursales.join(','));
    if (selectedCategory.length > 0) formData.append('category_filter', selectedCategory.join(','));
    if (selectedProduct.length > 0) formData.append('product_filter', selectedProduct.join(','));
    formData.append('view_mode', viewMode);

    try {
      const response = await api.post('/tools/breakdown', formData);
      setData(response.data);
    } catch (err: any) {
      console.error(err);
      const msg = err.response?.data?.detail || "Error al procesar el desglose.";
      alert(msg);
    } finally {
      setLoading(false);
    }
  };

  const toggleSucursal = (sucursal: string) => {
      setSelectedSucursales(prev => 
          prev.includes(sucursal) ? prev.filter(s => s !== sucursal) : [...prev, sucursal]
      );
  };
  
  const toggleCategory = (cat: string) => {
      setSelectedCategory(prev => 
          prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
      );
  };

  const toggleProduct = (product: string) => {
      setSelectedProduct(prev => 
          prev.includes(product) ? prev.filter(p => p !== product) : [...prev, product]
      );
  };

  const handleExport = async (format: 'csv' | 'xlsx') => {
      if (!data) return;
      
      const formData = new FormData();
      if (usePinnedFile) formData.append('use_pinned_file', 'true');
      else files.forEach(f => formData.append('files', f));
      
      if (startDate) formData.append('start_date', startDate);
      if (endDate) formData.append('end_date', endDate);
      if (selectedSucursales.length > 0) formData.append('sucursales', selectedSucursales.join(','));
      if (selectedCategory.length > 0) formData.append('category_filter', selectedCategory.join(','));
      if (selectedProduct.length > 0) formData.append('product_filter', selectedProduct.join(','));
      formData.append('view_mode', viewMode);
      formData.append('format', format);

      try {
          const response = await api.post('/tools/breakdown', formData, {
              responseType: 'blob'
          });
          
          const url = window.URL.createObjectURL(new Blob([response.data]));
          const link = document.createElement('a');
          link.href = url;
          const extension = format === 'xlsx' ? 'xlsx' : 'csv';
          link.setAttribute('download', `Desglose_Ventas.${extension}`);
          document.body.appendChild(link);
          link.click();
          link.parentNode?.removeChild(link);
      } catch (err) {
          console.error("Export error:", err);
          alert("Error al exportar archivo.");
      }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
        <div className="md:grid md:grid-cols-3 md:gap-6">
          <div className="md:col-span-1">
            <h3 className="text-lg font-medium leading-6 text-gray-900">Desglose de Ventas</h3>
            <p className="mt-1 text-sm text-gray-500">
              Genera tablas detalladas por día, semana o mes, cruzando sucursales y productos.
            </p>
          </div>
          <div className="mt-5 md:mt-0 md:col-span-2">
            
            {/* Source Selection */}
            {hasPinnedFile && (
                <div className="mb-4 bg-blue-50 p-4 rounded-md border border-blue-200">
                    <label className="flex items-center space-x-3 cursor-pointer">
                        <input 
                            type="checkbox" 
                            checked={usePinnedFile} 
                            onChange={(e) => setUsePinnedFile(e.target.checked)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <span className="text-sm font-medium text-blue-900 flex items-center">
                            <Pin className="w-4 h-4 mr-2" />
                            Usar archivo anclado: {pinnedFileInfo?.filename}
                        </span>
                    </label>
                </div>
            )}

            {!usePinnedFile && (
                <div className="flex flex-col items-center justify-center w-full mb-4">
                    <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
                        <div className="flex flex-col items-center justify-center pt-5 pb-6">
                            <Upload className="w-8 h-8 text-gray-400 mb-2" />
                            <p className="mb-1 text-sm text-gray-500"><span className="font-semibold">Click para subir reporte</span></p>
                            <p className="text-xs text-gray-500">.xlsx, .csv</p>
                        </div>
                        <input type="file" className="hidden" onChange={handleFileChange} multiple accept=".csv, .xlsx" />
                    </label>
                    {files.length > 0 && <p className="mt-2 text-sm text-green-600">{files.length} archivo(s) seleccionado(s)</p>}
                </div>
            )}
            
            <div className="mt-4 flex justify-end">
                <Button onClick={handleAnalyze} isLoading={loading} disabled={files.length === 0 && !usePinnedFile}>
                    <Table className="w-4 h-4 mr-2" /> Generar Desglose
                </Button>
            </div>
          </div>
        </div>
      </div>

      {data && (
        <div className="space-y-6 animate-fade-in">
             {/* Filters Bar */}
             <div className="bg-white shadow px-4 py-4 sm:rounded-lg flex flex-wrap gap-4 items-end">
                <div>
                    <label className="block text-xs font-medium text-gray-500">Fecha Inicio</label>
                    <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border" />
                </div>
                <div>
                    <label className="block text-xs font-medium text-gray-500">Fecha Fin</label>
                    <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border" />
                </div>
                <div>
                    <label className="block text-xs font-medium text-gray-500">Agrupar por</label>
                    <select value={viewMode} onChange={(e: any) => setViewMode(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border">
                        <option value="daily">Día</option>
                        <option value="weekly">Semana</option>
                        <option value="monthly">Mes</option>
                    </select>
                </div>
                
                {/* Sucursal Filter Dropdown */}
                <div className="relative group">
                    <button className="flex items-center space-x-2 bg-gray-100 hover:bg-gray-200 px-3 py-2 rounded-md text-sm text-gray-700 transition-colors">
                        <Filter className="w-4 h-4" />
                        <span>Sucursales ({selectedSucursales.length || 'Todas'})</span>
                    </button>
                    <div className="absolute z-10 hidden group-hover:block w-56 bg-white border border-gray-200 rounded-md shadow-lg mt-1 p-2 max-h-60 overflow-y-auto">
                        {data.available_sucursales?.map((s: string) => (
                            <label key={s} className="flex items-center space-x-2 p-1 hover:bg-gray-50 cursor-pointer">
                                <input 
                                    type="checkbox" 
                                    checked={selectedSucursales.includes(s)} 
                                    onChange={() => toggleSucursal(s)}
                                    className="rounded text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-700">{s}</span>
                            </label>
                        )) || <div className="p-2 text-sm text-gray-500">No hay sucursales</div>}
                    </div>
                </div>

                 {/* Category Filter Dropdown */}
                 <div className="relative group">
                    <button className="flex items-center space-x-2 bg-gray-100 hover:bg-gray-200 px-3 py-2 rounded-md text-sm text-gray-700 transition-colors">
                        <Filter className="w-4 h-4" />
                        <span>Categorías ({selectedCategory.length || 'Todas'})</span>
                    </button>
                    <div className="absolute z-10 hidden group-hover:block w-56 bg-white border border-gray-200 rounded-md shadow-lg mt-1 p-2 max-h-60 overflow-y-auto">
                        {['Tamal', 'Bebida', 'Paquete', 'Otro'].map((cat: string) => (
                            <label key={cat} className="flex items-center space-x-2 p-1 hover:bg-gray-50 cursor-pointer">
                                <input 
                                    type="checkbox" 
                                    checked={selectedCategory.includes(cat)} 
                                    onChange={() => toggleCategory(cat)}
                                    className="rounded text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-700">{cat}</span>
                            </label>
                        ))}
                    </div>
                </div>

                {/* Product Filter Dropdown */}
                 <div className="relative group">
                    <button className="flex items-center space-x-2 bg-gray-100 hover:bg-gray-200 px-3 py-2 rounded-md text-sm text-gray-700 transition-colors">
                        <Filter className="w-4 h-4" />
                        <span>Productos ({selectedProduct.length || 'Todos'})</span>
                    </button>
                    <div className="absolute z-10 hidden group-hover:block w-72 bg-white border border-gray-200 rounded-md shadow-lg mt-1 p-2 max-h-80 overflow-y-auto">
                        {data.available_products?.map((p: string) => (
                            <label key={p} className="flex items-center space-x-2 p-1 hover:bg-gray-50 cursor-pointer">
                                <input 
                                    type="checkbox" 
                                    checked={selectedProduct.includes(p)} 
                                    onChange={() => toggleProduct(p)}
                                    className="rounded text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-700 truncate">{p}</span>
                            </label>
                        ))}
                    </div>
                </div>

                <div className="flex-grow"></div>
                <div className="flex space-x-2">
                    <Button onClick={() => handleExport('xlsx')} variant="outline" className="text-green-700 border-green-200 hover:bg-green-50">
                        <Download className="w-4 h-4 mr-2" /> Excel
                    </Button>
                    <Button onClick={handleAnalyze} isLoading={loading} variant="secondary">Actualizar</Button>
                </div>
            </div>

            {/* Results Table */}
            {data.columns && data.data ? (
            <div className="bg-white shadow rounded-lg overflow-hidden">
                <div className="px-4 py-5 sm:px-6 flex justify-between items-center bg-gray-50 border-b">
                    <h3 className="text-lg font-medium leading-6 text-gray-900">Resultados del Desglose</h3>
                    <span className="text-sm text-gray-500">{data.data.length} productos encontrados</span>
                </div>
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider sticky left-0 bg-gray-50 z-0 shadow-sm">Producto</th>
                                {data.columns.map((col: string) => (
                                    <th key={col} scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">
                                        {col}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {data.data.map((row: any, idx: number) => (
                                <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 sticky left-0 bg-inherit z-0 shadow-sm">{row.Producto_Normalizado}</td>
                                    {data.columns.map((col: string) => (
                                        <td key={col} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                                            {row[col] ? row[col].toLocaleString() : '-'}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            ) : (
                <div className="bg-white shadow rounded-lg p-6 text-center text-gray-500">
                    No hay datos disponibles para mostrar.
                </div>
            )}
        </div>
      )}
    </div>
  );
}
