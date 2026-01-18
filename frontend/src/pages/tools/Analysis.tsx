import { useState, useMemo, useEffect } from 'react';
import { Upload, Search, BarChart3, TrendingUp, PieChart, Filter, Pin, PinOff } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend, PieChart as RePieChart, Pie, Cell } from 'recharts';
import api from '../../lib/api';
import { Button } from '../../components/ui/Button';

// Colores para gráficos
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

export default function Analysis() {
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  
  // Filtros
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedSucursales, setSelectedSucursales] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [isPinned, setIsPinned] = useState(false);

  useEffect(() => {
    // Check for pinned analysis on mount
    api.get('/tools/pinned-analysis')
      .then(res => {
        if (res.data) {
          setData(res.data);
          setIsPinned(true);
          // Try to restore date range if available in data
          if (res.data.data_range?.min) setStartDate(res.data.data_range.min);
          if (res.data.data_range?.max) setEndDate(res.data.data_range.max);
        }
      })
      .catch(err => console.error("Error loading pinned analysis:", err));
  }, []);

  const handlePin = async () => {
    if (!data) return;
    try {
      if (isPinned) {
        // Unpin
        await api.delete('/tools/pinned-analysis');
        setIsPinned(false);
        // Optionally clear data? No, keep it visible.
      } else {
        // Pin
        await api.post('/tools/pin-analysis', data);
        setIsPinned(true);
      }
    } catch (err) {
      console.error("Error toggling pin:", err);
      alert("Error al guardar/eliminar el análisis.");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files));
      setData(null); // Reset data on new file
      setIsPinned(false); // Reset pin state on new file
    }
  };

  const handleAnalyze = async () => {
    if (files.length === 0) return;
    setLoading(true);
    // Remove setData(null) to avoid full reload flickering
    // setData(null);

    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    if (startDate) formData.append('start_date', startDate);
    if (endDate) formData.append('end_date', endDate);
    if (selectedSucursales.length > 0) formData.append('sucursales', selectedSucursales.join(','));
    if (selectedCategory.length > 0) formData.append('category_filter', selectedCategory.join(','));
    if (selectedProduct.length > 0) formData.append('product_filter', selectedProduct.join(','));
    formData.append('view_mode', viewMode);

    try {
      const response = await api.post('/tools/data-analysis', formData);
      setData(response.data);
      
      // Auto-fill dates if empty
      if (!startDate && response.data.data_range?.min) setStartDate(response.data.data_range.min);
      if (!endDate && response.data.data_range?.max) setEndDate(response.data.data_range.max);
      
    } catch (err: any) {
      console.error(err);
      if (err.response?.status === 401) {
          alert("Tu sesión ha expirado. Por favor inicia sesión nuevamente.");
          window.location.href = '/login';
      } else {
          const msg = err.response?.data?.detail || "Error al analizar datos. Verifica que el archivo sea correcto.";
          alert(msg);
      }
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

  return (
    <div className="space-y-6">
      {/* Header & Upload Section */}
      <div className="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
        <div className="md:grid md:grid-cols-3 md:gap-6">
          <div className="md:col-span-1">
            <h3 className="text-lg font-medium leading-6 text-gray-900">Análisis de Datos</h3>
            <p className="mt-1 text-sm text-gray-500">
              Sube tus archivos de ventas para visualizar tendencias, rendimiento por sucursal y mix de productos.
            </p>
          </div>
          <div className="mt-5 md:mt-0 md:col-span-2">
            <div className="flex flex-col items-center justify-center w-full">
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <Upload className="w-8 h-8 text-gray-400 mb-2" />
                        <p className="mb-1 text-sm text-gray-500"><span className="font-semibold">Click para subir reporte</span></p>
                        <p className="text-xs text-gray-500">.xlsx, .csv (Soporta múltiples)</p>
                    </div>
                    <input type="file" className="hidden" onChange={handleFileChange} multiple accept=".csv, .xlsx" />
                </label>
            </div>
            {files.length > 0 && <p className="mt-2 text-sm text-green-600">{files.length} archivo(s) seleccionado(s)</p>}
            
            <div className="mt-4 flex justify-end space-x-3">
                {data && (
                    <Button onClick={handlePin} variant={isPinned ? "secondary" : "outline"} title={isPinned ? "Desanclar análisis" : "Anclar análisis al inicio"}>
                        {isPinned ? <PinOff className="w-4 h-4 mr-2" /> : <Pin className="w-4 h-4 mr-2" />}
                        {isPinned ? "Desanclar" : "Anclar"}
                    </Button>
                )}
                <Button onClick={handleAnalyze} isLoading={loading} disabled={files.length === 0}>
                    <BarChart3 className="w-4 h-4 mr-2" /> Analizar Datos
                </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Dashboard Section */}
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
                        {data.available_sucursales.map((s: string) => (
                            <label key={s} className="flex items-center space-x-2 p-1 hover:bg-gray-50 cursor-pointer">
                                <input 
                                    type="checkbox" 
                                    checked={selectedSucursales.includes(s)} 
                                    onChange={() => toggleSucursal(s)}
                                    className="rounded text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-700">{s}</span>
                            </label>
                        ))}
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

                {/* Product Filter Dropdown (Multi-select Grouped) */}
                <div className="relative group">
                    <button className="flex items-center space-x-2 bg-gray-100 hover:bg-gray-200 px-3 py-2 rounded-md text-sm text-gray-700 transition-colors">
                        <Filter className="w-4 h-4" />
                        <span>Productos ({selectedProduct.length || 'Todos'})</span>
                    </button>
                    <div className="absolute z-10 hidden group-hover:block w-72 bg-white border border-gray-200 rounded-md shadow-lg mt-1 p-2 max-h-80 overflow-y-auto">
                        {['Tamal', 'Bebida', 'Otro', 'Paquete'].map(cat => {
                            const productsInCat = data.available_products?.filter((p: any) => p.Categoria === cat);
                            if (!productsInCat || productsInCat.length === 0) return null;
                            
                            return (
                                <div key={cat} className="mb-2">
                                    <div className="text-xs font-bold text-gray-500 uppercase px-1 py-1 bg-gray-50 mb-1">{cat}s</div>
                                    {productsInCat.map((p: any) => (
                                        <label key={p.Producto_Normalizado} className="flex items-center space-x-2 p-1 hover:bg-gray-50 cursor-pointer">
                                            <input 
                                                type="checkbox" 
                                                checked={selectedProduct.includes(p.Producto_Normalizado)} 
                                                onChange={() => toggleProduct(p.Producto_Normalizado)}
                                                className="rounded text-blue-600 focus:ring-blue-500"
                                            />
                                            <span className="text-sm text-gray-700 truncate">{p.Producto_Normalizado}</span>
                                        </label>
                                    ))}
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="flex-grow"></div>
                <Button onClick={handleAnalyze} isLoading={loading} variant="secondary">Actualizar Filtros</Button>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
                <div className="bg-white overflow-hidden shadow rounded-lg px-4 py-5 sm:p-6">
                    <dt className="text-sm font-medium text-gray-500 truncate">Ventas Totales</dt>
                    <dd className="mt-1 text-3xl font-semibold text-gray-900">${data.raw_data_summary.total_sales.toLocaleString()}</dd>
                </div>
                <div className="bg-white overflow-hidden shadow rounded-lg px-4 py-5 sm:p-6">
                    <dt className="text-sm font-medium text-gray-500 truncate">Productos Vendidos</dt>
                    <dd className="mt-1 text-3xl font-semibold text-gray-900">{data.raw_data_summary.total_items.toLocaleString()}</dd>
                </div>
                <div className="bg-white overflow-hidden shadow rounded-lg px-4 py-5 sm:p-6">
                    <dt className="text-sm font-medium text-gray-500 truncate">Transacciones</dt>
                    <dd className="mt-1 text-3xl font-semibold text-gray-900">{data.raw_data_summary.transaction_count.toLocaleString()}</dd>
                </div>
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Specific Product Trend (Conditional) */}
                {selectedProduct.length > 0 && data.product_trend && (
                    <div className="bg-white shadow rounded-lg p-6 lg:col-span-2 border-l-4 border-green-500">
                        <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4 flex items-center">
                            <TrendingUp className="w-5 h-5 mr-2 text-green-600" /> Tendencia: {selectedProduct.length === 1 ? selectedProduct[0] : 'Productos Seleccionados'}
                        </h3>
                        <div className="h-80 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={data.product_trend}>
                                    <defs>
                                        <linearGradient id="colorProd" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#10B981" stopOpacity={0.8}/>
                                            <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis dataKey="Periodo" />
                                    <YAxis />
                                    <Tooltip formatter={(val: number) => [`${val} unidades`, 'Cantidad']} />
                                    <Area type="monotone" dataKey="Cantidad" stroke="#059669" fillOpacity={1} fill="url(#colorProd)" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {/* Sales Over Time */}
                <div className="bg-white shadow rounded-lg p-6 lg:col-span-2">
                    <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4 flex items-center">
                        <TrendingUp className="w-5 h-5 mr-2 text-blue-500" /> Tendencia de Ventas
                    </h3>
                    <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={data.sales_over_time}>
                                <defs>
                                    <linearGradient id="colorVentas" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.8}/>
                                        <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="Periodo" />
                                <YAxis tickFormatter={(val) => `$${val/1000}k`} />
                                <Tooltip formatter={(val: number) => [`$${val.toLocaleString()}`, 'Venta']} />
                                <Area type="monotone" dataKey="Total_Venta" stroke="#2563EB" fillOpacity={1} fill="url(#colorVentas)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Product Table (Excluding Packages) */}
                <div className="bg-white shadow rounded-lg p-6 lg:col-span-2">
                    <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4 flex items-center">
                        <BarChart3 className="w-5 h-5 mr-2 text-indigo-600" /> Detalle de Productos
                    </h3>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Producto</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categoría</th>
                                    <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total Unidades</th>
                                    <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Venta Normal</th>
                                    <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Promoción</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {data.product_table?.map((row: any, idx: number) => (
                                    <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{row.Producto_Normalizado}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                                row.Categoria === 'Tamal' ? 'bg-green-100 text-green-800' : 
                                                row.Categoria === 'Bebida' ? 'bg-blue-100 text-blue-800' : 
                                                'bg-gray-100 text-gray-800'
                                            }`}>
                                                {row.Categoria}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right font-bold">{row.Unidades_Totales.toLocaleString()}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{row.Venta_Normal.toLocaleString()}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{row.Venta_Promo.toLocaleString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Package Breakdown Table */}
                <div className="bg-white shadow rounded-lg p-6 lg:col-span-2">
                    <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4 flex items-center">
                        <Filter className="w-5 h-5 mr-2 text-orange-600" /> Análisis de Paquetes
                    </h3>
                    <p className="text-sm text-gray-500 mb-4">Desglose de qué productos se venden dentro de cada tipo de paquete.</p>
                    <div className="overflow-x-auto max-h-96">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50 sticky top-0">
                                <tr>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Paquete</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Producto Contenido</th>
                                    <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Unidades Vendidas</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {data.package_breakdown?.map((row: any, idx: number) => (
                                    <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{row.Paquete_Origen}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{row.Producto_Normalizado}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">{row.Unidades_Reales.toLocaleString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Top Products */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4 flex items-center">
                        <BarChart3 className="w-5 h-5 mr-2 text-purple-500" /> Top 10 Productos
                    </h3>
                    <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart layout="vertical" data={data.product_mix}>
                                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                                <XAxis type="number" hide />
                                <YAxis dataKey="Producto_Normalizado" type="category" width={150} tick={{fontSize: 12}} />
                                <Tooltip />
                                <Bar dataKey="Cantidad" fill="#8884d8" radius={[0, 4, 4, 0]}>
                                    {data.product_mix.map((entry: any, index: number) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Sucursal Performance */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Rendimiento por Sucursal</h3>
                    <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <RePieChart>
                                <Pie
                                    data={data.sucursal_performance}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={100}
                                    fill="#8884d8"
                                    paddingAngle={5}
                                    dataKey="Total_Venta"
                                    nameKey="Sucursal"
                                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                >
                                    {data.sucursal_performance.map((entry: any, index: number) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip formatter={(val: number) => `$${val.toLocaleString()}`} />
                            </RePieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
      )}
    </div>
  );
}
