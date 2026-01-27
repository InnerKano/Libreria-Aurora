import React from "react";
import { useNavigate } from "react-router-dom";

function BookCard({ book, color = "black" }) {
  const navigate = useNavigate();

  const handleNavigate = () => {
    navigate(`/${book.titulo}`, { state: { libro: book } });
  };

  return (
    <div
      onClick={handleNavigate}
      className="relative w-40 sm:w-48 md:w-52 lg:w-56 xl:w-60 p-3 sm:p-4 flex flex-col items-center justify-between shadow-md rounded-xl cursor-pointer transition-transform duration-300 ease-in-out hover:scale-105 group overflow-hidden"
    >

      <div className="w-full aspect-[2/3] overflow-hidden rounded-md relative">
        <img
          src={book.portada_url || "https://via.placeholder.com/150"}
          alt={`Portada del libro ${book.titulo}`}
          className="w-full h-full object-cover transition duration-300 ease-in-out group-hover:blur-sm"
        />

        {/* Overlay con detalles adicionales */}
        <div className="absolute inset-0 bg-black bg-opacity-60 text-white opacity-0 group-hover:opacity-100 transition duration-300 flex flex-col justify-center items-center p-4 text-center text-sm space-y-2">
          <p><strong>Editorial:</strong> {book.editorial}</p>
          <p><strong>Género:</strong> {book.categoria_nombre}</p>
          <p><strong>ISBN:</strong> {book.isbn}</p>
        </div>
      </div>

      {/* Información básica */}
      <div className="w-full text-center mt-2">
        <p className="text-sm sm:text-base font-semibold truncate" style={{ color }}>
          {book.titulo}
        </p>
        <p className="text-xs sm:text-sm font-light" style={{ color }}>
          {book.author}
        </p>
        <p className="text-xs sm:text-sm font-light" style={{ color }}>
          Año: {book.año_publicacion}
        </p>
        <p className="text-xs sm:text-sm font-medium" style={{ color }}>
          ${book.precio}
        </p>
      </div>
    </div>
  );
}

export default BookCard;
