import { useState, useEffect } from 'react';
import { Toaster, toast } from 'sonner';
import { getApiUrlByKey } from '../../api/config';
import LoadingSpinner from '../ui/LoadingSpinner';

function AdminUsers() {
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    tipo_usuario: '',
    telefono: '',
    direccion: '',
    nacionalidad: '',
    fecha_nacimiento: '',
    is_staff: false,
    activo: true,
  });

  const usuariosUrl = getApiUrlByKey('usuarios');

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(usuariosUrl, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Error cargando usuarios');
      const data = await response.json();
      setUsers(data);
    } catch (e) {
      toast.error('No se pudieron cargar los usuarios');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  // Abrir modal para editar usuario
  const openModal = (user) => {
    setFormData({
      username: user.username || '',
      email: user.email || '',
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      tipo_usuario: user.tipo_usuario || 'LECTOR',
      telefono: user.telefono || '',
      direccion: user.direccion || '',
      nacionalidad: user.nacionalidad || '',
      fecha_nacimiento: user.fecha_nacimiento || '',
      is_staff: user.is_staff || false,
      activo: user.activo !== false,
    });
    setSelectedUser(user);
    setModalOpen(true);
  };

  // Cerrar modal
  const closeModal = () => {
    setModalOpen(false);
    setSelectedUser(null);
  };

  // Manejar cambios en el formulario
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value,
    });
  };

  // Guardar cambios del usuario
  const handleSubmit = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem('token');
    
    if (!formData.email || !formData.first_name) {
      toast.error('Email y nombre son requeridos');
      return;
    }

    try {
      // Limpiar datos antes de enviar
      const cleanData = {};
      Object.keys(formData).forEach(key => {
        if (formData[key] !== '' && formData[key] !== null && formData[key] !== undefined) {
          cleanData[key] = formData[key];
        }
      });

      const response = await fetch(`${usuariosUrl}${selectedUser.id}/`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(cleanData)
      });

      if (!response.ok) {
        let errorMessage = 'Error al guardar usuario';
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (typeof errorData === 'object') {
            const errorMessages = [];
            Object.keys(errorData).forEach(field => {
              if (Array.isArray(errorData[field])) {
                errorMessages.push(`${field}: ${errorData[field].join(', ')}`);
              } else {
                errorMessages.push(`${field}: ${errorData[field]}`);
              }
            });
            if (errorMessages.length > 0) {
              errorMessage = errorMessages.join('\n');
            }
          }
        } catch (parseError) {
          errorMessage = `Error ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      toast.success('Usuario actualizado correctamente');
      closeModal();
      fetchUsers();
    } catch (error) {
      console.error('Error:', error);
      toast.error(error.message || 'Error al guardar usuario');
    }
  };

  return (
    <div className="p-4 md:p-6">
      <Toaster position="top-center" richColors />
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl md:text-3xl font-bold">Gestión de Usuarios</h1>
      </div>
      {loading ? (
        <LoadingSpinner message="Cargando usuarios..." />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usuario</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nombre</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Staff</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Activo</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">#{u.id}</td>
                  <td className="px-4 py-4 text-sm text-gray-900">{u.username}</td>
                  <td className="px-4 py-4 text-sm text-gray-900">{u.email}</td>
                  <td className="px-4 py-4 text-sm text-gray-900">{u.first_name} {u.last_name}</td>
                  <td className="px-4 py-4 text-sm text-gray-900">{u.tipo_usuario}</td>
                  <td className="px-4 py-4 text-sm text-gray-900">
                    <span className={`px-2 py-1 rounded ${u.is_staff ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}>
                      {u.is_staff ? 'Sí' : 'No'}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-sm text-gray-900">
                    <span className={`px-2 py-1 rounded ${u.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {u.activo ? 'Sí' : 'No'}
                    </span>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <button
                      onClick={() => openModal(u)}
                      className="text-blue-600 hover:underline">
                      Editar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal para editar usuario */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">Editar Usuario: {selectedUser.username}</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Fila 1: Username y Email */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Usuario *</label>
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    disabled
                    className="w-full p-2 border rounded bg-gray-100 text-gray-600"
                  />
                  <p className="text-xs text-gray-500 mt-1">No se puede cambiar</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    className="w-full p-2 border rounded"
                    required
                  />
                </div>
              </div>

              {/* Fila 2: Nombre y Apellido */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
                  <input
                    type="text"
                    name="first_name"
                    value={formData.first_name}
                    onChange={handleChange}
                    placeholder="Nombre"
                    className="w-full p-2 border rounded"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Apellido</label>
                  <input
                    type="text"
                    name="last_name"
                    value={formData.last_name}
                    onChange={handleChange}
                    placeholder="Apellido"
                    className="w-full p-2 border rounded"
                  />
                </div>
              </div>

              {/* Fila 3: Tipo de Usuario y Teléfono */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Usuario</label>
                  <select
                    name="tipo_usuario"
                    value={formData.tipo_usuario}
                    onChange={handleChange}
                    className="w-full p-2 border rounded"
                  >
                    <option value="LECTOR">Lector</option>
                    <option value="BIBLIOTECARIO">Bibliotecario</option>
                    <option value="ADMIN">Administrador</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
                  <input
                    type="tel"
                    name="telefono"
                    value={formData.telefono}
                    onChange={handleChange}
                    placeholder="+34 123456789"
                    className="w-full p-2 border rounded"
                  />
                </div>
              </div>

              {/* Fila 4: Nacionalidad y Fecha de Nacimiento */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nacionalidad</label>
                  <input
                    type="text"
                    name="nacionalidad"
                    value={formData.nacionalidad}
                    onChange={handleChange}
                    placeholder="Ej: Española"
                    className="w-full p-2 border rounded"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Fecha de Nacimiento</label>
                  <input
                    type="date"
                    name="fecha_nacimiento"
                    value={formData.fecha_nacimiento}
                    onChange={handleChange}
                    className="w-full p-2 border rounded"
                  />
                </div>
              </div>

              {/* Dirección */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dirección</label>
                <input
                  type="text"
                  name="direccion"
                  value={formData.direccion}
                  onChange={handleChange}
                  placeholder="Calle, número, ciudad"
                  className="w-full p-2 border rounded"
                />
              </div>

              {/* Checkboxes: Staff y Activo */}
              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    name="is_staff"
                    checked={formData.is_staff}
                    onChange={handleChange}
                    className="w-4 h-4 rounded border-gray-300"
                  />
                  <span className="text-sm font-medium text-gray-700">
                    ¿Es bibliotecario/a? (Puede gestionar contenido)
                  </span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    name="activo"
                    checked={formData.activo}
                    onChange={handleChange}
                    className="w-4 h-4 rounded border-gray-300"
                  />
                  <span className="text-sm font-medium text-gray-700">
                    ¿Está activo? (Puede iniciar sesión)
                  </span>
                </label>
              </div>

              {/* Botones */}
              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#3B4CBF] text-white rounded hover:bg-blue-700"
                >
                  Guardar Cambios
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminUsers;
