import { useEffect, useState } from "react";
import { getApiUrl } from "../../api/config";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { getBookCoverSrc } from "../../utils/media";

function Reservas() {
  const [reservas, setReservas] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchReservas();
  }, []);

  const fetchReservas = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;

      const response = await fetch(getApiUrl("/api/compras/reservas/"), {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();
      if (response.ok) {
        setReservas(data);
      }
    } catch (error) {
      console.error("Error al obtener reservas:", error);
    }
  };

  const cancelarReserva = async (reservaId) => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(getApiUrl("/api/compras/reservas/cancelar/"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ reserva_id: reservaId }),
      });

      if (!response.ok) {
        toast.error("No se pudo cancelar la reserva.");
        return;
      }

      toast.success("Reserva cancelada exitosamente.");
      fetchReservas(); // recargar lista
    } catch (error) {
      console.error("Error al cancelar reserva:", error);
      toast.error("Ocurrió un error al cancelar la reserva.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-6 border border-blue-200">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-black border-b-2 border-yellow-400 pb-1">Tus Reservas</h2>
          <button
            onClick={() => navigate(-1)}
            className="bg-[#c9a875] text-white px-4 py-1 rounded hover:bg-[#a9895e]"
          >
            Volver
          </button>
        </div>

        {reservas.length === 0 ? (
          <p className="text-gray-500">No hay reservas registradas.</p>
        ) : (
          reservas.map((reserva) => {
            const precioTotal = parseFloat(reserva.libro.precio) * reserva.cantidad;

            return (
              <div key={reserva.id} className="mb-8 border-t pt-6">
                <div className="flex gap-4 mb-4">
                  <div className="flex-shrink-0">
                    <img
                      src={getBookCoverSrc(reserva.libro)}
                      alt={reserva.libro.titulo}
                      className="w-24 h-32 object-cover rounded-md"
                    />
                  </div>
                  <div className="flex-1 bg-gray-100 rounded-md p-4">
                    <p className="text-md font-semibold text-gray-800">{reserva.libro.titulo}</p>
                    <p className="text-sm text-gray-600"><strong>Descripción:</strong> {reserva.libro.descripcion}</p>
                    <p className="text-sm text-gray-600 mt-1"><strong>Autor:</strong> {reserva.libro.autor}</p>
                    <p className="text-sm text-gray-600 mt-1"><strong>Fecha de reserva:</strong> {new Date(reserva.fecha_reserva).toLocaleDateString()}</p>
                    <p className="text-sm text-gray-600"><strong>Expira el:</strong> {new Date(reserva.fecha_expiracion).toLocaleDateString()}</p>
                    <p className="text-sm text-gray-600"><strong>Cantidad:</strong> {reserva.cantidad}</p>
                    <p className="text-sm text-gray-600"><strong>Precio Unitario:</strong> ${parseFloat(reserva.libro.precio).toFixed(2)}</p>
                    <p className="text-sm text-gray-600"><strong>Estado:</strong> {reserva.estado}</p>
                  </div>
                </div>

                <div className="text-right mt-2 pr-4">
                  {reserva.estado === "Reservado" && (
                    <button
                      onClick={() => cancelarReserva(reserva.id)}
                      className="mt-2 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-all"
                    >
                      Cancelar reserva
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default Reservas;
