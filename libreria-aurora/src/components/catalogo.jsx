import 'aos/dist/aos.css';
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { getApiUrl } from "../api/config";
import NavBar from "./navBar";
import BookCard from "./book/bookCard";
import LoadingSpinner from "./ui/LoadingSpinner";

function Catalogo() {
  const backendURL = getApiUrl("/api/libros/");
  const location = useLocation();
  
  const [books, setBooks] = useState([]);
  const [filteredBooks, setFilteredBooks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [categorias, setCategorias] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [showSearchInterface, setShowSearchInterface] = useState(false);
  const [filters, setFilters] = useState({
    categoria: "",
    precio_min: "",
    precio_max: ""
  });
  const [sortConfig, setSortConfig] = useState({
    field: "titulo",
    direction: "asc"
  });
  
  // Verificar si debe mostrar la interfaz de búsqueda al cargar
  useEffect(() => {
    const searchParam = new URLSearchParams(location.search).get('search');
    if (searchParam === 'true') {
      setShowSearchInterface(true);
    }
  }, [location.search]);

  const toggleSearchInterface = () => {
    setShowSearchInterface(prev => !prev);
  };

  useEffect(() => {
    // No se requiere autenticación para ver el catálogo
    fetchBooks();
    fetchCategorias();
  }, []);

  const fetchBooks = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(backendURL);
      if (!response.ok) throw new Error("Error en la petición");
      const data = await response.json();
      setBooks(data);
      setFilteredBooks(data);
      setIsLoading(false);
    } catch (error) {
      console.error("Error fetching books:", error);
      setIsLoading(false);
    }
  };

  const fetchCategorias = async () => {
    try {
      const response = await fetch(getApiUrl("/api/libros/categorias/"));
      if (!response.ok) throw new Error("Error al obtener categorías");
      const data = await response.json();
      setCategorias(data);
    } catch (error) {
      console.error("Error fetching categories:", error);
    }
  };

  useEffect(() => {
    // Aplicar filtros y búsqueda
    let result = [...books];
    
    // Aplicar término de búsqueda
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(book => 
        book.titulo?.toLowerCase().includes(term) || 
        book.autor?.toLowerCase().includes(term) ||
        book.isbn?.toLowerCase().includes(term) ||
        book.descripcion?.toLowerCase().includes(term) ||
        book.editorial?.toLowerCase().includes(term) ||
        (book.año_publicacion && book.año_publicacion.toString().includes(term))
      );
    }
    
    // Aplicar filtros
    if (filters.categoria) {
      result = result.filter(book => book.categoria === parseInt(filters.categoria));
    }
    
    if (filters.precio_min) {
      result = result.filter(book => parseFloat(book.precio) >= parseFloat(filters.precio_min));
    }
    
    if (filters.precio_max) {
      result = result.filter(book => parseFloat(book.precio) <= parseFloat(filters.precio_max));
    }
    
    // Aplicar ordenamiento
    result = result.sort((a, b) => {
      // Manejar valores null o undefined
      const aValue = a[sortConfig.field] || '';
      const bValue = b[sortConfig.field] || '';
      
      if (aValue < bValue) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (aValue > bValue) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });
    
    setFilteredBooks(result);
  }, [books, searchTerm, filters, sortConfig]);

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSortChange = (field) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const clearFilters = () => {
    setFilters({
      categoria: "",
      precio_min: "",
      precio_max: ""
    });
    setSearchTerm("");
  };
  if (isLoading) {
    return (
      <LoadingSpinner 
        message="Cargando libros..." 
        height="h-screen" 
        size="lg"
        bgColor="bg-black"
        textColor="text-white"
      />
    );
  }

  return (
    <div className="w-full min-h-screen overflow-y-auto overflow-x-hidden bg-[#0B1026]">
      <NavBar toggleSearch={toggleSearchInterface} />

      <div className="w-full flex flex-col p-[2vw]">
        {/* Interfaz de búsqueda - visible según estado */}
        {showSearchInterface && (
          <>
            {/* Barra de búsqueda */}
            <div className="w-1/2  mb-6">
              <input
                type="text"
                placeholder="Buscar por título, autor, ISBN, año..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full p-3 rounded-lg text-black"
                autoFocus
              />
            </div>

            {/* Filtros y ordenamiento */}
            <div className="w-full flex flex-wrap gap-4 mb-6 ">
              
              <div className="flex flex-col h-full">
                <label className="text-white mb-1">Categoría</label>
                <select 
                  name="categoria" 
                  value={filters.categoria} 
                  onChange={handleFilterChange}
                  className="p-2 rounded-lg text-black h-10 "
                >
                  <option value="">Todas</option>
                  {categorias.map(cat => (
                    <option key={cat.id} value={cat.id}>{cat.nombre}</option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col h-full">
                <label className="text-white mb-1">Precio mínimo</label>
                <input
                  type="number"
                  name="precio_min"
                  placeholder="Min"
                  value={filters.precio_min}
                  onChange={handleFilterChange}
                  className="p-2 rounded-lg text-black h-10 "
                />
              </div>

              <div className="flex flex-col h-full">
                <label className="text-white mb-1">Precio máximo</label>
                <input
                  type="number"
                  name="precio_max"
                  placeholder="Max"
                  value={filters.precio_max}
                  onChange={handleFilterChange}
                  className="p-2 rounded-lg text-black h-10 "
                />
              </div>

              <div className="flex flex-col h-full">
                <label className="text-white mb-1">Ordenar por</label>
                <div className="flex gap-2 flex-wrap">
                  <button 
                    onClick={() => handleSortChange('titulo')}
                    className={`px-3 py-1 rounded  ${sortConfig.field === 'titulo' ? 'bg-[#3B4CBF] text-white' : 'bg-gray-300 text-black'} h-10`}
                  >
                    Título {sortConfig.field === 'titulo' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                  </button>
                  <button 
                    onClick={() => handleSortChange('precio')}
                    className={`px-3 py-1 rounded ${sortConfig.field === 'precio' ? 'bg-[#3B4CBF] text-white' : 'bg-gray-300 text-black'} h-10`}
                  >
                    Precio {sortConfig.field === 'precio' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                  </button>
                  <button 
                    onClick={() => handleSortChange('año_publicacion')}
                    className={`px-3 py-1 rounded ${sortConfig.field === 'año_publicacion' ? 'bg-[#3B4CBF] text-white' : 'bg-gray-300 text-black'} h-10`}
                  >
                    Año {sortConfig.field === 'año_publicacion' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                  </button>
                </div>
              </div>

              <button 
                onClick={clearFilters}
                className="self-end px-4 py-2 bg-red-500 text-white rounded-lg"
              >
                Limpiar filtros
              </button>
            </div>
          </>
        )}

        <div className="flex justify-between items-center mb-4">
          <h1 className="text-white font-[500] text-[3.5vw]">
            {searchTerm ? `Resultados para "${searchTerm}"` : "Catálogo de libros"}
          </h1>
          
          <button 
            onClick={toggleSearchInterface} 
            className="bg-[#3B4CBF] text-white px-4 py-2 rounded-lg"
          >
            {showSearchInterface ? "Ocultar búsqueda" : "Mostrar búsqueda"}
          </button>
        </div>

        {/* Resultados */}
        <div className="w-full flex flex-wrap gap-4 justify-center"> 
          {filteredBooks.length > 0 ? (
            filteredBooks.map((book) => (
              <BookCard
                key={book.id || book.isbn || book.titulo}
                book={book}
                color="white"
              />
            ))
          ) : (
            <p className="text-white text-xl w-full text-center py-8">
              No se encontraron libros que coincidan con tu búsqueda.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default Catalogo;
