import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getApiUrl } from "../../api/config";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

function Tiendas() {
  const [tiendas, setTiendas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    nombre: "",
    direccion: "",
    latitud: "",
    longitud: "",
  });

  const fetchTiendas = async () => {
    try {

      const response = await fetch(getApiUrl("/api/tiendas/tiendas/"), {
        headers: {
          "Content-Type": "application/json"
        },
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data?.detail || "Error al cargar tiendas");
        return;
      }

      setTiendas(data);
    } catch (err) {
      console.error(err);
      setError("Error de red al consultar las tiendas");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        setError("No hay token de autenticación");
        return;
      }

      const response = await fetch(getApiUrl("/api/tiendas/tiendas/"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data?.detail || "Error al crear la tienda");
        return;
      }

      setTiendas((prev) => [...prev, data]);
      setFormData({ nombre: "", direccion: "", latitud: "", longitud: "" });
      setError(""); // limpiar errores
    } catch (err) {
      console.error(err);
      setError("Error al enviar la tienda");
    }
  };

  useEffect(() => {
    fetchTiendas();
  }, []);

  return (
    <div className="min-h-screen w-full bg-gray-100 ">
        <div className="mx-auto bg-white rounded-lg shadow-lg border border-blue-200 p-[1vw] ">
            <h2 className="text-xl font-bold text-black border-b-2 border-yellow-400 pb-1">Tiendas</h2>

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
                <label className="block text-sm font-medium text-gray-700">Nombre</label>
                <input
                type="text"
                className="mt-1 p-2 w-full border rounded-md"
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                required
                />
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700">Dirección</label>
                <input
                type="text"
                className="mt-1 p-2 w-full border rounded-md"
                value={formData.direccion}
                onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
                required
                />
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div>
                <label className="block text-sm font-medium text-gray-700">Latitud</label>
                <input
                    type="text"
                    className="mt-1 p-2 w-full border rounded-md"
                    value={formData.latitud}
                    onChange={(e) => setFormData({ ...formData, latitud: e.target.value })}
                    required
                />
                </div>

                <div>
                <label className="block text-sm font-medium text-gray-700">Longitud</label>
                <input
                    type="text"
                    className="mt-1 p-2 w-full border rounded-md"
                    value={formData.longitud}
                    onChange={(e) => setFormData({ ...formData, longitud: e.target.value })}
                    required
                />
                </div>
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Selecciona la ubicación en el mapa</label>
                <MapContainer
                center={[4.6, -74.1]}
                zoom={6}
                style={{ height: "300px", borderRadius: "0.5rem", position: "sticky" }}
                >
                <TileLayer
                    attribution='&copy; OpenStreetMap contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <LocationSelector setFormData={setFormData} />
                {formData.latitud && formData.longitud && (
                    <Marker position={[parseFloat(formData.latitud), parseFloat(formData.longitud)]}>
                    <Popup>Ubicación seleccionada</Popup>
                    </Marker>
                )}
                </MapContainer>
            </div>

            <button
                type="submit"
                className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 mt-4"
            >
                Registrar Tienda
            </button>
            </form>

            {loading ? (
            <p className="mt-4 text-gray-600">Cargando tiendas...</p>
            ) : error ? (
            <p className="mt-4 text-red-500">{error}</p>
            ) : tiendas.length === 0 ? (
            <p className="mt-4 text-gray-600">No hay tiendas registradas.</p>
            ) : (
            <>
                <ul className="mt-6 space-y-4">
                {tiendas.map((tienda) => (
                    <li key={tienda.id} className="border p-4 rounded-md bg-gray-50 shadow-sm">
                    <h3 className="text-lg font-semibold text-gray-800">{tienda.nombre}</h3>
                    <p className="text-sm text-gray-600"><strong>Dirección:</strong> {tienda.direccion}</p>
                    <p className="text-sm text-gray-600"><strong>Coordenadas:</strong> {tienda.latitud}, {tienda.longitud}</p>
                    <a
                        href={`https://www.google.com/maps/search/?api=1&query=${tienda.latitud},${tienda.longitud}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-block mt-2 text-sm text-blue-600 hover:underline"
                    >
                        Ver en Google Maps
                    </a>
                    </li>
                ))}
                </ul>

                {/* Mapa de todas las tiendas */}
                <div className="mt-10">
                <h3 className="text-lg font-semibold text-gray-800 mb-2">Mapa de Tiendas Registradas</h3>
                <MapContainer
                    center={[4.6, -74.1]}
                    zoom={6}
                  style={{ height: "400px", borderRadius: "0.5rem", position: "sticky" }}
                >
                    <TileLayer
                    attribution='&copy; OpenStreetMap contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    {tiendas.map((tienda) => (
                    <Marker
                        key={tienda.id}
                        position={[parseFloat(tienda.latitud), parseFloat(tienda.longitud)]}
                    >
                        <Popup>
                        <strong>{tienda.nombre}</strong><br />
                        {tienda.direccion}
                        </Popup>
                    </Marker>
                    ))}
                </MapContainer>
                </div>
            </>
            )}
        </div>
    </div>
  );
}

// Componente para capturar clics en el mapa y actualizar lat/lon
function LocationSelector({ setFormData }) {
  useMapEvents({
    click(e) {
      const { lat, lng } = e.latlng;
      setFormData((prev) => ({
        ...prev,
        latitud: lat.toFixed(6),
        longitud: lng.toFixed(6),
      }));
    },
  });

  return null;
}

export default Tiendas;
