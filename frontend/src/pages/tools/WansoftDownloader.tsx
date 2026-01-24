import { useState } from 'react';
import { Download, AlertCircle, CheckCircle, Shield } from 'lucide-react';
import api from '../../lib/api';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import LoadingModal from '../../components/ui/LoadingModal';

export default function WansoftDownloader() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [outputType, setOutputType] = useState<'processed' | 'raw'>('processed');
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [abortController, setAbortController] = useState<AbortController | null>(null);

  // Poll function to check status
  const pollStatus = async (jobId: string, controller: AbortController) => {
      if (controller.signal.aborted) return;

      try {
          const res = await api.get(`/tools/wansoft-status/${jobId}`);
          const status = res.data;
          
          if (controller.signal.aborted) return;

          if (status.status === 'failed') {
              throw new Error(status.message || 'Error en el proceso');
          }

          if (status.status === 'completed') {
              setProgress(100);
              setLoadingMessage('¡Completado! Descargando archivo...');
              
              // Trigger file download
              const downloadRes = await api.get(`/tools/wansoft-result/${jobId}`, {
                  responseType: 'blob'
              });
              
              const url = window.URL.createObjectURL(new Blob([downloadRes.data]));
              const link = document.createElement('a');
              link.href = url;
              
              const contentDisposition = downloadRes.headers['content-disposition'];
              let filename = `wansoft_result.${outputType === 'processed' ? 'xlsx' : 'zip'}`;
              
              if (contentDisposition) {
                  const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
                  if (filenameMatch && filenameMatch.length >= 2) {
                      filename = filenameMatch[1].replace(/['"]/g, '');
                  }
              }
              
              link.setAttribute('download', filename);
              document.body.appendChild(link);
              link.click();
              link.remove();
              
              setSuccess(true);
              setIsProcessing(false);
              setAbortController(null);
              return;
          }

          // Update progress and continue polling
          setLoadingMessage(status.message || 'Procesando...');
          setProgress(status.progress || 0);
          
          // Poll again in 2 seconds
          setTimeout(() => pollStatus(jobId, controller), 2000);

      } catch (err: any) {
          if (!controller.signal.aborted) {
            console.error(err);
            setError(err.message || 'Error al consultar estado');
            setIsProcessing(false);
            setAbortController(null);
          }
      }
  };

  const handleCancel = () => {
    if (abortController) {
      abortController.abort();
      setIsProcessing(false);
      setLoadingMessage('');
      setError('Operación cancelada por el usuario.');
      setAbortController(null);
    }
  };

  const handleProcess = async () => {
    if (!username || !password || !startDate || !endDate) {
        setError("Por favor completa todos los campos.");
        return;
    }

    // Create new controller for this request
    const controller = new AbortController();
    setAbortController(controller);

    setIsProcessing(true);
    setLoadingMessage('Iniciando sesión...');
    setProgress(0);
    setError(null);
    setSuccess(false);

    try {
      // Start Job
      const startRes = await api.post('/tools/wansoft-download', {
        username,
        password,
        start_date: startDate,
        end_date: endDate,
        output_type: outputType
      });
      
      const jobId = startRes.data.job_id;
      
      // Start polling
      pollStatus(jobId, controller);
      
    } catch (err: unknown) {
      console.error(err);
      setError('Error al iniciar el proceso. Verifica tu conexión.');
      setIsProcessing(false);
      setAbortController(null);
    }
  };

  return (
    <div className="space-y-6">
      <LoadingModal 
        isOpen={isProcessing} 
        message={loadingMessage} 
        progress={progress}
        isIndeterminate={false}
        onCancel={handleCancel}
      />
      <div className="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
        <div className="md:grid md:grid-cols-3 md:gap-6">
          <div className="md:col-span-1">
            <h3 className="text-lg font-medium leading-6 text-gray-900">Descarga Wansoft</h3>
            <p className="mt-1 text-sm text-gray-500">
              Automatiza la descarga de reportes de ventas desde el portal de Wansoft.
            </p>
            <div className="mt-4 p-3 bg-blue-50 rounded-md border border-blue-100">
                <div className="flex items-start">
                    <Shield className="h-5 w-5 text-blue-400 mt-0.5 mr-2" />
                    <p className="text-xs text-blue-700">
                        <strong>Seguridad:</strong> Tus credenciales se envían de forma segura solo para esta sesión y no se almacenan en ninguna base de datos.
                    </p>
                </div>
            </div>
          </div>
          
          <div className="mt-5 md:mt-0 md:col-span-2 space-y-4">
            
            {/* Credentials */}
            <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
                <div className="sm:col-span-3">
                    <label className="block text-sm font-medium text-gray-700">Usuario Wansoft</label>
                    <div className="mt-1">
                        <Input 
                            type="text" 
                            value={username} 
                            onChange={(e) => setUsername(e.target.value)} 
                            placeholder="Usuario"
                        />
                    </div>
                </div>

                <div className="sm:col-span-3">
                    <label className="block text-sm font-medium text-gray-700">Contraseña</label>
                    <div className="mt-1">
                        <Input 
                            type="password" 
                            value={password} 
                            onChange={(e) => setPassword(e.target.value)} 
                            placeholder="••••••••"
                        />
                    </div>
                </div>
            </div>

            {/* Date Range */}
            <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
                <div className="sm:col-span-3">
                    <label className="block text-sm font-medium text-gray-700">Fecha Inicial</label>
                    <div className="mt-1">
                        <Input 
                            type="date" 
                            value={startDate} 
                            onChange={(e) => setStartDate(e.target.value)} 
                        />
                    </div>
                </div>

                <div className="sm:col-span-3">
                    <label className="block text-sm font-medium text-gray-700">Fecha Final</label>
                    <div className="mt-1">
                        <Input 
                            type="date" 
                            value={endDate} 
                            onChange={(e) => setEndDate(e.target.value)} 
                        />
                    </div>
                </div>
            </div>

            {/* Output Type */}
            <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">Tipo de Salida</label>
                <div className="flex space-x-6">
                    <label className="inline-flex items-center cursor-pointer">
                        <input
                            type="radio"
                            className="form-radio text-blue-600 h-4 w-4"
                            name="outputType"
                            value="processed"
                            checked={outputType === 'processed'}
                            onChange={() => setOutputType('processed')}
                        />
                        <span className="ml-2 text-sm text-gray-900">Procesado (Limpieza de Datos)</span>
                    </label>
                    <label className="inline-flex items-center cursor-pointer">
                        <input
                            type="radio"
                            className="form-radio text-blue-600 h-4 w-4"
                            name="outputType"
                            value="raw"
                            checked={outputType === 'raw'}
                            onChange={() => setOutputType('raw')}
                        />
                        <span className="ml-2 text-sm text-gray-900">Datos Crudos (ZIP)</span>
                    </label>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                    {outputType === 'processed' 
                        ? "Genera un solo archivo Excel con todas las ventas limpias y consolidadas."
                        : "Descarga los 11 archivos originales tal cual vienen de Wansoft."}
                </p>
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
                <p className="text-sm text-green-700">¡Descarga completada con éxito!</p>
              </div>
            )}

            <div className="mt-6 flex justify-end">
              <Button onClick={handleProcess} disabled={isProcessing} isLoading={isProcessing}>
                <Download className="w-4 h-4 mr-2" />
                {isProcessing ? 'Procesando...' : 'Descargar Reportes'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
