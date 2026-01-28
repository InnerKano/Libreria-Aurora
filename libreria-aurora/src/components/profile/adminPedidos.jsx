import { useEffect, useMemo, useState } from "react";
import { Toaster, toast } from "sonner";
import { getApiUrl } from "../../api/config";
import LoadingSpinner from "../ui/LoadingSpinner";

const ESTADOS = ["Pendiente", "En Proceso", "Entregado", "Cancelado"];

const formatDate = (dateString) => {
  const options = {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  };
  return new Date(dateString).toLocaleDateString("es-ES", options);
};

const getOrderTotals = (pedido) => {
  const cantidadTotal = pedido.pedidolibro_set.reduce(
    (acc, item) => acc + item.cantidad,
    0
  );

  const precioTotal = pedido.pedidolibro_set.reduce(
    (acc, item) => acc + item.cantidad * parseFloat(item.libro.precio),
    0
  );

  return { cantidadTotal, precioTotal };
};

function AdminPedidos() {
  const [loading, setLoading] = useState(true);
  const [loadingAction, setLoadingAction] = useState(false);
  const [pedidos, setPedidos] = useState([]);
  const [historial, setHistorial] = useState([]);
  const [activeTab, setActiveTab] = useState("pedidos");
  const [selectedPedido, setSelectedPedido] = useState(null);
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const pedidosUrl = getApiUrl("/api/compras/pedidos/admin_list/");
  const cambiarEstadoUrl = getApiUrl("/api/compras/pedidos/admin_cambiar_estado/");
  const historialUrl = getApiUrl("/api/compras/historial-compras/admin_list/");

  const fetchPedidos = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(pedidosUrl, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("No se pudieron cargar los pedidos");
      }

      const data = await response.json();
      setPedidos(data);
    } catch (error) {
      console.error("Error al cargar pedidos:", error);
      toast.error("No se pudieron cargar los pedidos");
    } finally {
      setLoading(false);
    }
  };

  const fetchHistorial = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(historialUrl, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("No se pudo cargar el historial");
      }

      const data = await response.json();
      setHistorial(data);
    } catch (error) {
      console.error("Error al cargar historial:", error);
      toast.error("No se pudo cargar el historial");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPedidos();
  }, []);

  const handleTabChange = async (tab) => {
    setActiveTab(tab);
    setSelectedPedido(null);

    if (tab === "historial" && historial.length === 0) {
      await fetchHistorial();
    }
  };

  const handleStatusChange = async (pedidoId, nuevoEstado) => {
    try {
      setLoadingAction(true);
      const token = localStorage.getItem("token");

      const response = await fetch(cambiarEstadoUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ pedido_id: pedidoId, nuevo_estado: nuevoEstado }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData?.mensaje || errorData?.error || "No se pudo actualizar el estado";
        throw new Error(message);
      }

      toast.success("Estado del pedido actualizado");
      await fetchPedidos();
      if (activeTab === "historial") {
        await fetchHistorial();
      }
      if (selectedPedido?.id === pedidoId) {
        setSelectedPedido((prev) => ({ ...prev, estado: nuevoEstado }));
      }
    } catch (error) {
      console.error("Error al cambiar estado:", error);
      toast.error(error.message || "No se pudo actualizar el estado");
    } finally {
      setLoadingAction(false);
    }
  };

  const filteredPedidos = useMemo(() => {
    let data = pedidos;

    if (filterStatus !== "ALL") {
      data = data.filter((pedido) => pedido.estado === filterStatus);
    } else {
      data = data.filter((pedido) => pedido.estado !== "Entregado" && pedido.estado !== "Cancelado");
    }

    if (searchQuery.trim()) {
      const lowerQuery = searchQuery.toLowerCase();
      data = data.filter((pedido) => {
        const user = pedido.usuario || {};
        return (
          String(pedido.id).includes(lowerQuery) ||
          user.username?.toLowerCase().includes(lowerQuery) ||
          user.email?.toLowerCase().includes(lowerQuery)
        );
      });
    }

    return data;
  }, [pedidos, filterStatus, searchQuery]);

  const groupedPedidos = useMemo(() => {
    const grouped = filteredPedidos.reduce((acc, pedido) => {
      const dateKey = new Date(pedido.fecha).toISOString().slice(0, 10);
      if (!acc[dateKey]) {
        acc[dateKey] = [];
      }
      acc[dateKey].push(pedido);
      return acc;
    }, {});

    return Object.entries(grouped)
      .map(([dateKey, items]) => ({
        dateKey,
        items,
        sortValue: new Date(dateKey).getTime(),
      }))
      .sort((a, b) => b.sortValue - a.sortValue);
  }, [filteredPedidos]);

  const historialPedidos = useMemo(() => {
    return historial.map((registro) => registro.pedido).filter(Boolean);
  }, [historial]);

  if (selectedPedido) {
    const { cantidadTotal, precioTotal } = getOrderTotals(selectedPedido);
    const user = selectedPedido.usuario || {};

    return (
      <div className="p-4 md:p-6">
        <Toaster position="top-center" richColors />
        <button
          onClick={() => setSelectedPedido(null)}
          className="mb-4 text-[#3B4CBF] hover:underline flex items-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Volver a pedidos
        </button>

        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Pedido #{selectedPedido.id}</h1>
              <p className="text-sm text-gray-500">Fecha: {formatDate(selectedPedido.fecha)}</p>
              <p className="text-sm text-gray-500">
                Usuario: <span className="font-medium">{user.username || "Desconocido"}</span>
              </p>
              <p className="text-sm text-gray-500">Correo: {user.email || "Sin email"}</p>
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-gray-700">Estado</label>
              <select
                value={selectedPedido.estado}
                onChange={(e) => handleStatusChange(selectedPedido.id, e.target.value)}
                disabled={loadingAction}
                className="border rounded px-3 py-2 text-sm"
              >
                {ESTADOS.map((estado) => (
                  <option key={estado} value={estado}>
                    {estado}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-4">
            {selectedPedido.pedidolibro_set.map((item) => (
              <div key={`${selectedPedido.id}-${item.libro.id}`} className="border rounded-lg p-4">
                <p className="font-semibold text-gray-800">{item.libro.titulo}</p>
                <p className="text-sm text-gray-600">Autor: {item.libro.autor}</p>
                <p className="text-sm text-gray-600">Cantidad: {item.cantidad}</p>
                <p className="text-sm text-gray-600">Precio unitario: ${parseFloat(item.libro.precio).toFixed(2)}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 border-t pt-4 text-right">
            <p className="text-lg font-semibold text-gray-900">Total libros: {cantidadTotal}</p>
            <p className="text-lg font-semibold text-green-600">Total pedido: ${precioTotal.toFixed(2)}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6">
      <Toaster position="top-center" richColors />
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <h1 className="text-2xl md:text-3xl font-bold">Administrar pedidos</h1>
        <div className="flex gap-2">
          <button
            onClick={() => handleTabChange("pedidos")}
            className={`px-4 py-2 rounded-lg text-sm ${
              activeTab === "pedidos" ? "bg-[#3B4CBF] text-white" : "bg-gray-100 text-gray-700"
            }`}
          >
            Pedidos activos
          </button>
          <button
            onClick={() => handleTabChange("historial")}
            className={`px-4 py-2 rounded-lg text-sm ${
              activeTab === "historial" ? "bg-[#3B4CBF] text-white" : "bg-gray-100 text-gray-700"
            }`}
          >
            Historial
          </button>
        </div>
      </div>

      {activeTab === "pedidos" && (
        <div className="mb-6 bg-white rounded-lg shadow-md p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <input
              type="text"
              placeholder="Buscar por usuario o ID de pedido"
              className="p-2 border border-gray-300 rounded w-full"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <select
              className="p-2 border border-gray-300 rounded"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="ALL">Todos los activos</option>
              {ESTADOS.map((estado) => (
                <option key={estado} value={estado}>
                  {estado}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {loading ? (
        <LoadingSpinner message="Cargando pedidos..." />
      ) : activeTab === "pedidos" ? (
        groupedPedidos.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-6 text-gray-500">
            No hay pedidos activos para mostrar.
          </div>
        ) : (
          <div className="space-y-6">
            {groupedPedidos.map((group) => (
              <div key={group.dateKey} className="bg-white rounded-lg shadow-md p-4">
                <h2 className="text-lg font-semibold text-[#2B388C] mb-3">
                  {new Date(group.dateKey).toLocaleDateString("es-ES", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </h2>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usuario</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Correo</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Libros</th>
                        <th className="px-4 py-3"></th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {group.items.map((pedido) => {
                        const user = pedido.usuario || {};
                        const { cantidadTotal } = getOrderTotals(pedido);
                        return (
                          <tr key={pedido.id} className="hover:bg-gray-50">
                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">#{pedido.id}</td>
                            <td className="px-4 py-4 text-sm text-gray-900">{user.username || "Usuario"}</td>
                            <td className="px-4 py-4 text-sm text-gray-600">{user.email || "-"}</td>
                            <td className="px-4 py-4 text-sm text-gray-900">{pedido.estado}</td>
                            <td className="px-4 py-4 text-sm text-gray-600">{cantidadTotal}</td>
                            <td className="px-4 py-4 text-sm">
                              <button
                                onClick={() => setSelectedPedido(pedido)}
                                className="text-blue-600 hover:underline"
                              >
                                Ver detalle
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )
      ) : historialPedidos.length === 0 ? (
        <div className="bg-white rounded-lg shadow-md p-6 text-gray-500">
          No hay historial de pedidos entregados.
        </div>
      ) : (
        <div className="space-y-4">
          {historialPedidos.map((pedido) => {
            const user = pedido.usuario || {};
            const { cantidadTotal, precioTotal } = getOrderTotals(pedido);
            return (
              <div key={`historial-${pedido.id}`} className="bg-white rounded-lg shadow-md p-4">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">Pedido #{pedido.id}</h2>
                    <p className="text-sm text-gray-500">Fecha: {formatDate(pedido.fecha)}</p>
                    <p className="text-sm text-gray-500">Usuario: {user.username || "Usuario"}</p>
                  </div>
                  <div className="text-sm text-gray-600">Estado: {pedido.estado}</div>
                </div>
                <div className="mt-4">
                  <p className="text-sm text-gray-600">Libros: {cantidadTotal}</p>
                  <p className="text-sm text-green-600 font-semibold">Total: ${precioTotal.toFixed(2)}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default AdminPedidos;
