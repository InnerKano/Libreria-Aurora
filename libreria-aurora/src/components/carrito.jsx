import {useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import NavBar from "./navBar";
import { useNavigate } from "react-router-dom";
import { getApiUrl } from "../api/config";
import { CountryDropdown, RegionDropdown } from "react-country-region-selector";
import { toast, Toaster } from "sonner";


function CarritoLibro() {

  const navigate = useNavigate();
  const backendUser = getApiUrl("/api/usuarios/perfil/");
  const backendCartGet = getApiUrl("/api/compras/carritos/obtener_libros/");
  const backendCartDelete = getApiUrl("/api/compras/carritos/quitar_libro/");
  const backendCartBuy = getApiUrl("/api/compras/carritos/pagar/");
  const [carrito, setCarrito] = useState([]);
  const [usarDireccionGuardada, setUsarDireccionGuardada] = useState(true);
  const [userData, setUserData] = useState(null);
  const [recogerEnTienda, setRecogerEnTienda] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [userAddress, setUserAddress] = useState({
    direccion: "",
    nacionalidad: "",
    departamento: "",
  });

  const getCoverSrc = (libro) => {
    const raw = libro?.portada_url || libro?.portada;
    if (!raw) return "";

    // Ya viene como URL absoluta
    if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;

    // Fallback para cuando backend devuelve una ruta parcial tipo "image/upload/..."
    if (raw.startsWith("image/")) {
      const base = process.env.REACT_APP_CLOUDINARY_BASE_URL || "https://res.cloudinary.com/dvmyip4cp/";
      return `${base}${raw}`;
    }

    return raw;
  };

  useEffect(() => {
      getUserData();
  }, []);

  const getUserData = async () => {
      try {
          const token = localStorage.getItem("token");
          if (!token) return;

          const response = await fetch(backendUser, {
              method: "GET",
              headers: {
                  "Content-Type": "application/json",
                  "Authorization": `Bearer ${token}`
              }
          });

          if (!response.ok) {
              throw new Error("Error en la petición");
          }

          const data = await response.json();
          setUserData(data);
      } catch (error) {
          console.error("Error fetching user data:", error);
      }
  };

  useEffect(() => {
    getCartData();
  }, []);

  const getCartData = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;
      const response = await fetch(backendCartGet, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error("Error en la petición");
      }
      const data = await response.json();
      console.log("Carrito data:", data);
      setCarrito(data);
    } catch (error) {
      console.error("Error fetching cart data:", error);
    }
  };

  const removeBookFromCart = async (libroId,cantidad) => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;
      const response = await fetch(backendCartDelete, {
        method: "POST", // <-- Cambiado de DELETE a POST
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ libro_id: libroId, cantidad: cantidad }),
      });
      if (!response.ok) {
        throw new Error("Error en la petición");
      }
      // Actualiza el carrito localmente
      setCarrito(carrito.filter((libro) => libro.libro.id !== libroId));
    } catch (error) {
      console.error("Error removing book from cart:", error);
    }
  };

  const handleRemoveBook = (libroId,cantidad) => {
    console.log("Eliminar libro con ID:", libroId);
    removeBookFromCart(libroId,cantidad);
  };

  const handleBuy = async () => {
    setIsProcessing(true); // ⬅️ Activar bloqueo
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        toast.error("No estás autenticado.");
        return;
      }

      const response = await fetch(backendCartBuy, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          direccion: usarDireccionGuardada ? null : userAddress.direccion,
          nacionalidad: usarDireccionGuardada ? null : userAddress.nacionalidad,
          departamento: usarDireccionGuardada ? null : userAddress.departamento,
          recoger_en_tienda: recogerEnTienda,
        }),
      });

      const data = await response.json();

      if (!response.ok || (data.mensaje && data.mensaje.estado === "error")) {
        const msg = data.mensaje?.mensaje || "Error inesperado del servidor.";
        console.error("Error al procesar la compra:", msg);
        toast.error(msg);
        return;
      }

      toast.success("Compra realizada exitosamente.");
      localStorage.removeItem("carrito");

      setTimeout(() => {
        navigate("/");
      }, 1500);
    } catch (error) {
      console.error("Error al procesar la compra:", error);
      toast.error(error.message || "Error inesperado.");
    } finally {
      setIsProcessing(false); 
    }
  };

  const onBack = () => navigate(-1);

  const onConfirm = () => {
    if (usarDireccionGuardada) {
      handleBuy();
    } else {
      if (!userAddress.direccion || !userAddress.nacionalidad || !userAddress.departamento) {
        toast.error("Por favor, completa todos los campos de dirección.");
        return;
      }
      handleBuy();
    }
  };

  const calcularTotal = () => {
    const subtotal = carrito.reduce((acc, libro) => acc + libro.libro.precio * libro.cantidad, 0);
    const envio = recogerEnTienda ? 0 : 10;

    // Verificar si hoy es el cumpleaños del usuario
    let descuento = 0;
    if (userData && userData.fecha_nacimiento) {
      const hoy = new Date();
      const nacimiento = new Date(userData.fecha_nacimiento);
      if (
        hoy.getDate() === nacimiento.getDate() &&
        hoy.getMonth() === nacimiento.getMonth()
      ) {
        descuento = 10;
      }
    }

    const total = subtotal + envio - descuento;
    return { subtotal, envio, descuento, total };
  };

  const { envio, descuento, total } = calcularTotal();

  const handleIncrease = async (libroId) => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;

      const response = await fetch(getApiUrl("/api/compras/carritos/agregar_libro/"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          libro_id: libroId,
          cantidad: 1,
        }),
      });

      if (!response.ok) {
        throw new Error("Error al aumentar la cantidad.");
      }

      await getCartData(); // refrescar carrito
    } catch (error) {
      console.error("Error al aumentar libro:", error);
      toast.error("No se pudo aumentar la cantidad.");
    }
  };

  const handleDecrease = async (libroId) => {
    try {
      const token = localStorage.getItem("token");
      if (!token) return;

      const response = await fetch(getApiUrl("/api/compras/carritos/quitar_libro/"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          libro_id: libroId,
          cantidad: 1,
        }),
      });

      if (!response.ok) {
        throw new Error("Error al disminuir la cantidad.");
      }

      await getCartData(); // refrescar carrito
    } catch (error) {
      console.error("Error al disminuir libro:", error);
      toast.error("No se pudo disminuir la cantidad.");
    }
  };

  if (carrito.length === 0) {
    return (
      <div>
        <NavBar />
        <div className="flex justify-center items-center h-screen">
          <p className="text-gray-500 text-lg">Tu carrito está vacío.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#f9f9fc] min-h-screen">
      <Toaster />
      <NavBar />
      <div className="max-w-3xl mx-auto my-10 p-6 bg-white rounded-xl shadow-md border border-blue-200">
        <h2 className="text-2xl font-bold mb-6 text-gray-800">Tu Carrito</h2>
        {/* Imprime en consola el objeto libro */
        console.log(carrito)}

        {carrito.map((carrito,idx) => (
          <div className="flex gap-6 mb-6 items-start" key={idx}>
            <div className="flex-shrink-0">
                <img src={getCoverSrc(carrito.libro)} alt={`Portada del libro: ${carrito.libro.titulo}`} className="w-32 h-48 object-cover rounded-md" />
            </div>
            <div className="flex-1 space-y-2">
              <h3 className="text-lg font-semibold">{carrito.libro.titulo}</h3>
              <div className="bg-gray-200 rounded-md p-3 text-sm space-y-1">
                <p><span className="font-semibold">Descripción:</span> {carrito.libro.descripcion}</p>
                <p><span className="font-semibold">Categoría:</span> {carrito.libro.categoria_nombre}</p>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">Cantidad:</span>
                  <button className="px-2 py-1 bg-gray-300 rounded disabled:opacity-50" onClick={() => handleDecrease(carrito.libro.id)} disabled={carrito.cantidad <= 1} >
                    −
                  </button>
                  <span className="px-2">{carrito.cantidad}</span>
                  <button className="px-2 py-1 bg-gray-300 rounded" onClick={() => handleIncrease(carrito.libro.id)} >
                    +
                  </button>
              </div>
              </div>
            </div>
            <div className="text-right">
              <p className="text-lg font-semibold text-gray-700">Precio:</p>
              <p className="text-black">${carrito.libro.precio}</p>
              <button onClick={() => handleRemoveBook(carrito.libro.id , carrito.cantidad)} className="text-blue-600 hover:text-red-500 mt-2">
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        ))}

        <hr className="my-6 border-gray-300" />

        <div className="flex items-center mb-4">
          <input
            type="checkbox"
            checked={usarDireccionGuardada}
            onChange={(e) => setUsarDireccionGuardada(e.target.checked)}
            className="mr-2"
          />
          <label className="text-gray-700">Usar dirección guardada</label>
        </div>

        {/* Dirección */}
        {usarDireccionGuardada && userData ? (
          <div className="grid grid-cols-1 gap-2 bg-gray-100 p-4 rounded-md text-sm mb-3">
            <p><strong>País:</strong> {userData.nacionalidad}</p>
            <p><strong>Departamento:</strong> {userData.departamento}</p>
            <p><strong>Dirección:</strong> {userData.direccion}</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 mb-6 bg-white p-4 border rounded-lg">
            <div className="col-span-2">
              <CountryDropdown
                value={userAddress.nacionalidad}
                onChange={(val) => setUserAddress({ ...userAddress, nacionalidad: val, departamento: "" })}
                className="w-full p-2 bg-gray-200 rounded-md"
              />
            </div>
            <div className="col-span-2">
              <RegionDropdown
                country={userAddress.nacionalidad}
                value={userAddress.departamento}
                onChange={(val) => setUserAddress({ ...userAddress, departamento: val })}
                className="w-full p-2 bg-gray-200 rounded-md"
              />
            </div>
            <input
              type="text"
              placeholder="Dirección"
              value={userAddress.direccion}
              onChange={(e) => setUserAddress({ ...userAddress, direccion: e.target.value })}
              className="bg-gray-200 p-2 rounded-md col-span-2"
            />
          </div>
        )}

        {((usarDireccionGuardada && userData?.nacionalidad === "Colombia") ||
          (!usarDireccionGuardada && userAddress.nacionalidad === "Colombia")) && (
          <div className="flex items-center mb-4">
            <input
              type="checkbox"
              checked={recogerEnTienda}
              onChange={(e) => setRecogerEnTienda(e.target.checked)}
              className="mr-2"
            />
            <label className="text-gray-700">Recoger en tienda</label>
          </div>
        )}

        {/* Totales */}
        <div className="bg-gray-200 p-4 rounded-md mb-6 text-sm text-gray-700 mt-4">
          <p>Costo Envío: ${envio.toLocaleString()}</p>
          <p>Descuento: ${descuento.toLocaleString()}</p>
          <p className="text-right text-lg font-bold">Total: ${total}</p>
        </div>

        {/* Botones */}
        <div className="flex justify-end gap-3">
          <button onClick={onBack} className="bg-[#9f7f4f] text-white px-4 py-2 rounded hover:bg-[#87683e]">Volver</button>
          <button onClick={onConfirm} disabled={isProcessing} className={`px-4 py-2 rounded text-white ${isProcessing ? 'bg-gray-400' : 'bg-[#f3c57b] hover:bg-[#e0b362]'}`} > {isProcessing ? "Procesando..." : "Confirmar"} </button>
        </div>
      </div>
    </div>
  );
}

export default CarritoLibro;
