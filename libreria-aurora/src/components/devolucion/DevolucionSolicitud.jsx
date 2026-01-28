import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast, Toaster } from "sonner";
import { getApiUrl } from "../../api/config";
import LoadingSpinner from "../ui/LoadingSpinner";

function DevolucionSolicitud() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [devolucion, setDevolucion] = useState(null);
  const [items, setItems] = useState([]);

  const resolveUrl = getApiUrl(`/api/compras/devoluciones/resolve/${token}/`);
  const confirmarUrl = getApiUrl(`/api/compras/devoluciones/confirmar/${token}/`);

  useEffect(() => {
    const fetchDevolucion = async () => {
      try {
        const response = await fetch(resolveUrl, {
          headers: { "Content-Type": "application/json" },
        });
        if (!response.ok) {
          throw new Error("No se pudo cargar la devolución");
        }
        const data = await response.json();
        setDevolucion(data);
        const mapped = (data.items || []).map((item) => ({
          libro_id: item.libro?.id,
          titulo: item.libro?.titulo,
          cantidad: item.cantidad,
          max: item.cantidad,
        }));
        setItems(mapped);
      } catch (error) {
        console.error(error);
        toast.error("No se pudo cargar la devolución");
      } finally {
        setLoading(false);
      }
    };

    fetchDevolucion();
  }, [resolveUrl]);

  const handleCantidadChange = (index, value) => {
    const cantidad = Math.max(0, Math.min(value, items[index].max));
    setItems((prev) =>
      prev.map((item, idx) =>
        idx === index ? { ...item, cantidad } : item
      )
    );
  };

  const handleSubmit = async () => {
    if (devolucion?.estado !== "Solicitada") {
      toast.error("La devolución ya fue procesada o está en revisión.");
      return;
    }

    if (!items.some((item) => item.cantidad > 0)) {
      toast.error("Selecciona al menos un libro para devolver");
      return;
    }

    try {
      setSubmitting(true);
      const tokenAuth = localStorage.getItem("token");
      if (!tokenAuth) {
        toast.error("Necesitas iniciar sesión para confirmar la devolución");
        navigate("/login");
        return;
      }

      const payload = {
        items: items
          .filter((item) => item.cantidad > 0)
          .map((item) => ({
            libro_id: item.libro_id,
            cantidad: item.cantidad,
          })),
      };

      const response = await fetch(confirmarUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tokenAuth}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData?.mensaje || errorData?.error || "No se pudo confirmar la devolución";
        throw new Error(message);
      }

      toast.success("Devolución confirmada. Un staff la revisará pronto.");
      navigate("/miPerfil");
    } catch (error) {
      console.error(error);
      toast.error(error.message || "No se pudo confirmar la devolución");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner message="Cargando devolución..." />
      </div>
    );
  }

  if (!devolucion) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-600">No se encontró la devolución.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <Toaster position="top-center" richColors />
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold mb-2">Solicitud de devolución</h1>
        <p className="text-sm text-gray-600 mb-4">
          Pedido #{devolucion.pedido?.id} • Estado actual: {devolucion.estado}
        </p>
        {devolucion.estado !== "Solicitada" && (
          <div className="mb-4 rounded border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
            Esta devolución ya fue confirmada o está en revisión. No puedes volver a enviarla.
          </div>
        )}

        <div className="space-y-4">
          {items.map((item, index) => (
            <div key={`${item.libro_id}-${index}`} className="flex items-center justify-between border rounded p-3">
              <div>
                <p className="font-medium text-gray-800">{item.titulo}</p>
                <p className="text-xs text-gray-500">Cantidad máxima: {item.max}</p>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min={0}
                  max={item.max}
                  value={item.cantidad}
                  onChange={(e) => handleCantidadChange(index, parseInt(e.target.value, 10))}
                  className="w-20 border rounded px-2 py-1"
                  disabled={devolucion.estado !== "Solicitada"}
                />
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={() => navigate("/miPerfil")}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || devolucion.estado !== "Solicitada"}
            className="px-4 py-2 bg-[#3B4CBF] text-white rounded"
          >
            {submitting ? "Enviando..." : "Confirmar devolución"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default DevolucionSolicitud;
