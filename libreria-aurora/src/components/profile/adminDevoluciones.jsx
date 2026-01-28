import { useEffect, useState } from "react";
import { Toaster, toast } from "sonner";
import { getApiUrl } from "../../api/config";
import LoadingSpinner from "../ui/LoadingSpinner";

const ESTADOS = ["Solicitada", "En Proceso", "Devuelta", "Rechazada"];

const getAllowedEstados = (estadoActual) => {
  if (estadoActual === "Solicitada") return ["En Proceso"];
  if (estadoActual === "En Proceso") return ["Devuelta", "Rechazada"];
  return [];
};

function AdminDevoluciones() {
  const [loading, setLoading] = useState(true);
  const [loadingAction, setLoadingAction] = useState(false);
  const [devoluciones, setDevoluciones] = useState([]);

  const devolucionesUrl = getApiUrl("/api/compras/devoluciones/admin_list/");

  const fetchDevoluciones = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(devolucionesUrl, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("No se pudieron cargar las devoluciones");
      }

      const data = await response.json();
      setDevoluciones(data);
    } catch (error) {
      console.error(error);
      toast.error("No se pudieron cargar las devoluciones");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevoluciones();
  }, []);

  const handleUpdateEstado = async (devolucionId, estado) => {
    try {
      setLoadingAction(true);
      const token = localStorage.getItem("token");
      const response = await fetch(
        getApiUrl(`/api/compras/devoluciones/${devolucionId}/admin_update_estado/`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ estado }),
        }
      );

      if (!response.ok) {
        throw new Error("No se pudo actualizar la devolución");
      }

      toast.success("Estado actualizado");
      fetchDevoluciones();
    } catch (error) {
      console.error(error);
      toast.error("No se pudo actualizar la devolución");
    } finally {
      setLoadingAction(false);
    }
  };

  return (
    <div className="p-4 md:p-6">
      <Toaster position="top-center" richColors />
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl md:text-3xl font-bold">Gestión de devoluciones</h1>
      </div>

      <div className="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
        Para cambios excepcionales de estado del pedido, usa el override en el detalle del pedido.
      </div>

      {loading ? (
        <LoadingSpinner message="Cargando devoluciones..." />
      ) : devoluciones.length === 0 ? (
        <div className="bg-white rounded-lg shadow-md p-6 text-gray-500">
          No hay devoluciones registradas.
        </div>
      ) : (
        <div className="overflow-x-auto bg-white rounded-lg shadow-md">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Pedido</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usuario</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha solicitud</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {devoluciones.map((devolucion) => (
                <tr key={devolucion.id} className="hover:bg-gray-50">
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">#{devolucion.id}</td>
                  <td className="px-4 py-4 text-sm text-gray-900">#{devolucion.pedido?.id}</td>
                  <td className="px-4 py-4 text-sm text-gray-600">{devolucion.pedido?.usuario?.username || devolucion.pedido?.usuario || "-"}</td>
                  <td className="px-4 py-4 text-sm text-gray-900">{devolucion.estado}</td>
                  <td className="px-4 py-4 text-sm text-gray-600">
                    {new Date(devolucion.fecha_solicitud).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm">
                    <select
                      value={devolucion.estado}
                      disabled={loadingAction || ["Devuelta", "Rechazada"].includes(devolucion.estado)}
                      onChange={(e) => handleUpdateEstado(devolucion.id, e.target.value)}
                      className="border rounded px-2 py-1 text-sm"
                    >
                      <option value={devolucion.estado}>{devolucion.estado}</option>
                      {getAllowedEstados(devolucion.estado).map((estado) => (
                        <option key={estado} value={estado}>
                          {estado}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default AdminDevoluciones;
