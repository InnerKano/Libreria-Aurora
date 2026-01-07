import { useLocation, useNavigate } from "react-router-dom";
import NavBar from "./navBar.jsx";
import BuyBookSection from "./book/addTocCartButton";
import { toast, Toaster } from "sonner";
import { getApiUrl } from "../api/config.js";
import { useIsStaff } from "../hooks/useIsStaff.js";

function DetalleLibro() {
  const navigate = useNavigate();
  const location = useLocation();
  const libroData = location.state?.libro;
  const { isStaff: userIsStaff, loading: staffLoading } = useIsStaff();

  const backendCartPost = getApiUrl("/api/compras/carritos/agregar_libro/");

  if (!libroData) {
    return (
      <div>
        <NavBar />
        <div className="flex justify-center items-center h-screen">
          <p className="text-gray-500 text-lg">No se encontró la información del libro.</p>
        </div>
      </div>
    );
  }

  const handleBuy = async (quantity) => {
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        toast.error("No estás autenticado. Por favor, inicia sesión.");
        return;
      }

      const response = await fetch(backendCartPost, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          libro_id: libroData.id,
          cantidad: quantity,
        }),
      });

      if (!response.ok) {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          const errorJson = await response.json();
          throw new Error(errorJson.detail || "Error al agregar al carrito");
        } else {
          const errorText = await response.text();
          console.error("Respuesta no JSON:", errorText);
          throw new Error("Error inesperado del servidor.");
        }
      }

      toast.success("Libro agregado al carrito");
      navigate("/carrito");
    } catch (error) {
      console.error("Error al agregar libro al carrito:", error);
      toast.error(`Error: ${error.message}`);
    }
  };

    const handleReserva = async (quantity) => {
        if (quantity > 3) {
            toast.warning("No puedes reservar más de 3 ejemplares.");
            return;
        }

        try {
            const token = localStorage.getItem("token");
            if (!token) {
            toast.error("No estás autenticado. Por favor, inicia sesión.");
            return;
            }

            const response = await fetch(getApiUrl("/api/compras/reservas/reservar/"), {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
                libro_id: libroData.id,  
                cantidad: quantity,
            }),
            });

            if (!response.ok) {
              const contentType = response.headers.get("content-type");
              if (contentType && contentType.includes("application/json")) {
                  const errorJson = await response.json();
                  throw new Error(errorJson.detail || "Error al reservar el libro");
              } else {
                const errorText = await response.text();
                console.error("Respuesta no JSON:", errorText);
                throw new Error("Error inesperado del servidor.");
            }
            }

            toast.success("Libro reservado exitosamente");
            navigate("/");
        } catch (error) {
            console.error("Error al reservar libro:", error);
            toast.error(`Error: ${error.message}`);
        }
    };


  return (
    <div className="min-h-screen bg-gray-100">
      <Toaster position="top-center" richColors />
      <NavBar />
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-white shadow-xl rounded-2xl overflow-hidden">
          <div className="flex flex-col md:flex-row">
            <div className="md:w-1/3 p-6 flex justify-center items-center">
              <img
                src={libroData.portada_url}
                alt={`Portada del libro: ${libroData.titulo}`}
                className="rounded-xl object-cover w-full h-auto max-h-[400px]"
              />
            </div>
            <div className="md:w-2/3 p-6 space-y-4">
              <h1 className="text-2xl font-bold text-gray-800">{libroData.titulo}</h1>
              <p className="text-gray-700">{libroData.descripcion}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-gray-600">
                <p><strong>Autor:</strong> {libroData.author}</p>
                <p><strong>Año de publicación:</strong> {libroData.año_publicacion}</p>
                <p><strong>Precio:</strong> ${libroData.precio}</p>
                <p><strong>ISBN:</strong> {libroData.isbn}</p>
                <p><strong>Editorial:</strong> {libroData.editorial}</p>
                <p><strong>Género:</strong> {libroData.categoria_nombre}</p>
              </div>
              {!staffLoading && !userIsStaff && (
                <BuyBookSection
                  stock={libroData.stock}
                  onBuy={handleBuy}
                  onReserve={handleReserva}
                />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DetalleLibro;
