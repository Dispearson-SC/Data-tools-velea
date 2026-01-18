import { Link } from 'react-router-dom';
import { FileSpreadsheet, BarChart3, Settings, Factory, TrendingUp } from 'lucide-react';

export default function Home() {
  const tools = [
    {
      title: 'Limpieza de Ventas',
      description: 'Procesa reportes de ventas diarios. Detecta sucursal y ofertas.',
      icon: FileSpreadsheet,
      href: '/tools/cleaner',
      color: 'bg-blue-500',
    },
    {
      title: 'Reporte de Tamales',
      description: 'Genera reporte de análisis Excel (Total, Fuera de Paquete, En Combos).',
      icon: BarChart3,
      href: '/tools/analysis',
      color: 'bg-purple-500',
    },
    {
      title: 'Análisis de Datos',
      description: 'Visualiza tendencias de ventas, mix de productos y gráficos interactivos.',
      icon: TrendingUp,
      href: '/tools/data-analysis',
      color: 'bg-indigo-600',
    },
    {
      title: 'Filtro de Producción',
      description: 'Procesa reporte de producción semanal (Tradicional, HP, Borracho).',
      icon: Factory,
      href: '/tools/production',
      color: 'bg-orange-500',
    },
    {
      title: 'Configuración',
      description: 'Ajustes del sistema y usuarios.',
      icon: Settings,
      href: '#',
      color: 'bg-gray-500',
      disabled: true,
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Panel de Herramientas</h1>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {tools.map((tool) => {
          const Icon = tool.icon;
          return (
            <Link
              key={tool.title}
              to={tool.href}
              className={`block p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow ${
                tool.disabled ? 'opacity-60 cursor-not-allowed pointer-events-none' : ''
              }`}
            >
              <div className={`inline-flex p-3 rounded-lg ${tool.color} text-white mb-4`}>
                <Icon className="w-6 h-6" />
              </div>
              <h5 className="mb-2 text-xl font-bold tracking-tight text-gray-900">
                {tool.title}
              </h5>
              <p className="font-normal text-gray-700">
                {tool.description}
              </p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
