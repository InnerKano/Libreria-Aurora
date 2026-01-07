import { useEffect, useState } from "react";
import { getApiUrl } from "../../api/config";
import { useNavigate } from "react-router-dom";
import { toast, Toaster } from "sonner";
import { getBookCoverSrc } from "../../utils/media";

function Pedidos() {
  const [pedidos, setPedidos] = useState([]);
  const [historialCompras, setHistorialCompras] = useState([]);
  const [modoVista, setModoVista] = useState("pedidos"); // "pedidos" o "historial"
  const navigate = useNavigate();

  useEffect(() => {
    fetchHistorialPedidos();
  }, []);

  const fetchHistorialPedidos = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;

      const response = await fetch(getApiUrl("/api/compras/pedidos/historial_pedidos/"), {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();
      if (response.ok) setPedidos(data);
    } catch (error) {
      console.error("Error al obtener pedidos:", error);
    }
  };

  const fetchHistorialCompras = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;

      const response = await fetch(getApiUrl("/api/compras/historial-compras/"), {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();
      console.log("Historial de compras:", data);
      if (response.ok) setHistorialCompras(data);
    } catch (error) {
      console.error("Error al obtener historial de compras:", error);
    }
  };

  const cancelarPedido = async (pedidoId) => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(getApiUrl("/api/compras/pedidos/cancelar_pedido/"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ pedido_id: pedidoId }),
      });

      if (!response.ok) {
        alert("No se pudo cancelar el pedido.");
        return;
      }

      alert("Pedido cancelado exitosamente.");
      fetchHistorialPedidos();
    } catch (error) {
      console.error("Error al cancelar el pedido:", error);
    }
  };

  const devolverCompra = async (historialId) => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;

      const response = await fetch(getApiUrl("/api/compras/historial-compras/devolver_compra/"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ historial_id: historialId }),
      });

      if (!response.ok) {
        alert("No se pudo procesar la devolución.");
        console.error("Error al procesar la devolución:", response.statusText);
        return;
      }

      toast.success("Devolución procesada exitosamente.Revisa tu correo para más detalles.", {
        duration: 5000,
        position: "top-right",
      });
      fetchHistorialCompras(); // Actualiza el historial
    } catch (error) {
      console.error("Error al procesar la devolución:", error);
    }
  };

  const renderPedido = (pedido, permitirCancelar = false) => {
    const cantidadTotal = pedido.pedidolibro_set.reduce(
      (acc, item) => acc + item.cantidad,
      0
    );

    const precioTotal = pedido.pedidolibro_set.reduce(
      (acc, item) => acc + item.cantidad * parseFloat(item.libro.precio),
      0
    );

    return (
      <div key={pedido.id} className="mb-8 border-t pt-6">
        <Toaster />
        {pedido.pedidolibro_set.map((item, index) => (
          <div key={index} className="flex gap-4 mb-4">
            <div className="flex-shrink-0">
              <img src={getBookCoverSrc(item.libro)} alt={item.libro.titulo} className="w-24 h-32 object-cover rounded-md" />
            </div>
            <div className="flex-1 bg-gray-100 rounded-md p-4">
              <p className="text-sm text-gray-600"><strong>Descripción:</strong> {item.libro.descripcion}</p>
              <p className="text-sm text-gray-600 mt-1"><strong>Fecha de Compra:</strong> {new Date(pedido.fecha).toLocaleDateString()}</p>
              <p className="text-md text-gray-800 mt-2"><strong>Estado:</strong> {pedido.estado}</p>
              <p className="text-sm text-gray-600 mt-1"><strong>Cantidad:</strong> {item.cantidad}</p>
              <p className="text-sm text-gray-600"><strong>Precio Unitario:</strong> ${parseFloat(item.libro.precio).toFixed(2)}</p>
            </div>
          </div>
        ))}

        <div className="text-right mt-4 pr-4">
          <p className="text-lg font-semibold text-black">📚 Total de libros: {cantidadTotal}</p>
          <p className="text-lg font-semibold text-green-600">💲 Total del pedido: ${precioTotal.toFixed(2)}</p>

          {permitirCancelar && pedido.estado === "Pendiente" && (
            <button
              onClick={() => cancelarPedido(pedido.id)}
              className="mt-4 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-all"
            >
              Cancelar pedido
            </button>
          )}
        </div>
      </div>
    );
  };

  const cambiarVista = async (nuevaVista) => {
    setModoVista(nuevaVista);
    if (nuevaVista === "historial" && historialCompras.length === 0) {
      await fetchHistorialCompras();
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-6 border border-blue-200">
        <div className="flex justify-between items-center mb-6">
          <div className="flex gap-6">
            <h2
              className={`text-xl font-bold pb-1 border-b-2 cursor-pointer ${
                modoVista === "pedidos" ? "text-black border-yellow-400" : "text-gray-500 border-transparent"
              }`}
              onClick={() => cambiarVista("pedidos")}
            >
              Tus Pedidos
            </h2>
            <h2
              className={`text-xl font-semibold pb-1 border-b-2 cursor-pointer ${
                modoVista === "historial" ? "text-black border-yellow-400" : "text-gray-500 border-transparent"
              }`}
              onClick={() => cambiarVista("historial")}
            >
              Historial de Compras
            </h2>
          </div>
          <button onClick={() => navigate(-1)} className="bg-[#c9a875] text-white px-4 py-1 rounded hover:bg-[#a9895e]">Volver</button>
        </div>

          {modoVista === "pedidos" ? (
            pedidos.filter((pedido) => pedido.estado !== "Entregado").length === 0 ? (
              <p className="text-gray-500">No hay pedidos registrados.</p>
            ) : (
              pedidos
                .filter((pedido) => pedido.estado !== "Entregado")
                .map((pedido) => renderPedido(pedido, true))
            )
          ) : (
            historialCompras.length === 0 ? (
              <p className="text-gray-500">No hay compras registradas.</p>
            ) : (
              historialCompras.map((compra) => {
                const pedido = compra.pedido;

                // Condición: entregado y dentro de 8 días
                const puedeDevolver =
                  pedido.estado === "Entregado" &&
                  (new Date() - new Date(pedido.fecha)) / (1000 * 60 * 60 * 24) <= 8;

                return (
                  <div key={pedido.id}>
                    {renderPedido(pedido, false)}
                    {puedeDevolver && (
                      <div className="text-right pr-4">
                        <button
                          onClick={() => devolverCompra(compra.id)}
                          className="mt-2 bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600 transition-all"
                        >
                          Devolver
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )
          )}

      </div>
    </div>
  );
}

export default Pedidos;
