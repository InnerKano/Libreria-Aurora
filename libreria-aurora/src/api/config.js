// Configuration for API endpoints
const config = {
  // Change this to false when you want to use local backend
  useProductionBackend: false,
  
  // Base URLs
  baseURLs: {
    production: "https://proyecto-libreria-k9xr.onrender.com",
    local: "http://localhost:8000"
  },
  
  // API endpoints
  endpoints: {
    // Usuarios
    usuariosPerfil: "/api/usuarios/perfil/",
    usuarios: "/api/usuarios/",
    validarToken: "/api/usuarios/validar_token/",
    restablecerContraseña: "/api/usuarios/restablecer_contraseña/",
    recuperarContraseña: "/api/usuarios/recuperar_contraseña/",
    actualizarPerfil: "/api/usuarios/actualizar_perfil/",
    
    // Auth
    token: "/api/token/",
    tokenRefresh: "/api/token/refresh/",
    
    // Libros
    libros: "/api/libros/",
    
    // Finanzas
    tarjetas: "/api/finanzas/tarjetas/",
    saldos: "/api/finanzas/saldos/",
    recargarSaldo: "/api/finanzas/saldos/recargar_saldo/",
    historialTransacciones: "/api/finanzas/historial/",
    
    // Otros módulos
    mensajeria: "/api/mensajeria/",
    noticias: "/api/noticias/",
    compras: "/api/compras/",
    busqueda: "/api/",

    // Agente LLM
    agentChat: "/api/agent/",
    agentSearch: "/api/agent/search/",
    agentActions: "/api/agent/actions/"
  }
};

// Helper function to get the full API URL
export const getApiUrl = (endpoint) => {
  const baseURL = config.useProductionBackend ? config.baseURLs.production : config.baseURLs.local;
  return `${baseURL}${endpoint}`;
};

// Alternative function that uses the predefined endpoints
export const getApiUrlByKey = (endpointKey) => {
  const baseURL = config.useProductionBackend ? config.baseURLs.production : config.baseURLs.local;
  const endpoint = config.endpoints[endpointKey];
  
  if (!endpoint) {
    console.error(`Endpoint key "${endpointKey}" not found in config.endpoints`);
    return null;
  }
  
  return `${baseURL}${endpoint}`;
};

export default config;
