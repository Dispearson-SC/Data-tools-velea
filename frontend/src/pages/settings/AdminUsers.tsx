import { useEffect, useState } from 'react';
import api from '../../lib/api';
import { Button } from '../../components/ui/Button';
import { useAuthStore } from '../../store/authStore';
import { Check, X, Shield, ShieldOff, User } from 'lucide-react';

interface UserData {
  username: string;
  email: string;
  disabled: boolean;
  is_admin: boolean;
}

export default function AdminUsers() {
  const [users, setUsers] = useState<UserData[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const isAdmin = useAuthStore(state => state.isAdmin);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await api.get('/users');
      setUsers(res.data);
    } catch (err) {
      console.error("Failed to fetch users", err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (username: string) => {
    setActionLoading(username);
    try {
      await api.post(`/users/${username}/toggle-status`);
      // Optimistic update
      setUsers(prev => prev.map(u => 
        u.username === username ? { ...u, disabled: !u.disabled } : u
      ));
    } catch (err) {
      console.error("Failed to toggle status", err);
      alert("Error al cambiar estado del usuario");
    } finally {
      setActionLoading(null);
    }
  };

  if (!isAdmin) {
    return <div className="p-4 text-red-600">No tienes permisos para ver esta página.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
        <div className="md:grid md:grid-cols-3 md:gap-6">
          <div className="md:col-span-1">
            <h3 className="text-lg font-medium leading-6 text-gray-900">Gestión de Usuarios</h3>
            <p className="mt-1 text-sm text-gray-500">
              Administra los usuarios registrados. Aprueba nuevos registros o desactiva cuentas existentes.
            </p>
          </div>
          <div className="mt-5 md:mt-0 md:col-span-2">
            <div className="flex justify-between mb-4">
                 <h4 className="text-md font-medium text-gray-700">Lista de Usuarios ({users.length})</h4>
                 <Button onClick={fetchUsers} variant="secondary" size="sm">Actualizar</Button>
            </div>
            
            {loading ? (
                <p className="text-sm text-gray-500">Cargando usuarios...</p>
            ) : (
                <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
                    <table className="min-w-full divide-y divide-gray-300">
                        <thead className="bg-gray-50">
                            <tr>
                                <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Usuario</th>
                                <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Email</th>
                                <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Rol</th>
                                <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Estado</th>
                                <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                                    <span className="sr-only">Acciones</span>
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 bg-white">
                            {users.map((user) => (
                                <tr key={user.username}>
                                    <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">
                                        {user.username}
                                        {user.username === 'gerardoj.suastegui' && <span className="ml-2 text-xs text-blue-600">(Tú)</span>}
                                    </td>
                                    <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{user.email}</td>
                                    <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                        {user.is_admin ? (
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                                <Shield className="w-3 h-3 mr-1" /> Admin
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                                <User className="w-3 h-3 mr-1" /> Usuario
                                            </span>
                                        )}
                                    </td>
                                    <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                                        {user.disabled ? (
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                                Pendiente / Inactivo
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                Activo
                                            </span>
                                        )}
                                    </td>
                                    <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                                        {!user.is_admin && (
                                            <Button
                                                onClick={() => handleToggleStatus(user.username)}
                                                isLoading={actionLoading === user.username}
                                                variant={user.disabled ? "primary" : "outline"}
                                                size="sm"
                                                className={user.disabled ? "bg-green-600 hover:bg-green-700" : "text-red-600 hover:text-red-700 border-red-200 hover:bg-red-50"}
                                            >
                                                {user.disabled ? (
                                                    <>
                                                        <Check className="w-4 h-4 mr-1" /> Aprobar/Activar
                                                    </>
                                                ) : (
                                                    <>
                                                        <X className="w-4 h-4 mr-1" /> Desactivar
                                                    </>
                                                )}
                                            </Button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
