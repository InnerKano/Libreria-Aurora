# Documentacion Tecnica - Libreria Aurora

## Proposito y alcance
- **Por que existe:** Consolidar en un unico lugar la vision tecnica real del sistema para soportar mantenimiento, escalabilidad y onboarding.
- **Para que se usa:** Guiar decisiones de arquitectura, descubrir puntos de integracion y evaluar impacto de nuevas capacidades (incluyendo agentes de IA) sin depender de conocimiento tacito.

## Panorama general del sistema
- Arquitectura de dos capas: backend Django + frontend React; comunicacion exclusiva via API REST sobre HTTP.
- Persistencia centralizada en PostgreSQL; archivos en Cloudinary; notificaciones por correo via SMTP.
- Despliegue recomendado: backend en Render (WSGI/ASGI con Gunicorn + Channels) y frontend estatico en GitHub Pages; entorno local via docker-compose o servidores individuales.

## Topologia de entornos
| Entorno | Backend | Frontend | Base de datos | Objetivo |
|---------|---------|----------|---------------|----------|
| Desarrollo | Servidor Django local (manage.py runserver) | React con npm start | PostgreSQL local (DATABASE_URL_LOCAL) | Experimentacion y debugging.
| Produccion | Render con Gunicorn/ASGI, STATIC con WhiteNoise | GitHub Pages (build React) | Render PostgreSQL (DATABASE_URL) | Servicio publico estable.

**Variables de entorno clave (backend/.env):**
- DJANGO_SECRET_KEY, DEBUG, ENVIRONMENT, ALLOWED_HOSTS, DATABASE_URL[_LOCAL], EMAIL_HOST_USER/PASSWORD.
- FRONTEND_URL_LOCAL/PROD para enlaces transaccionales.
- CLOUDINARY_* para gestion de medios.

## Estructura de codigo relevante
| Directorio | Rol principal | Responsabilidad
|------------|---------------|----------------
| backend/apps | Conjunto modular de apps Django alineadas a dominios de negocio. | Cada subcarpeta encapsula modelos, vistas, serializers, urls y pruebas.
| backend/config | Configuracion global de Django (settings, enroutamiento, WSGI/ASGI). | Define autenticacion, DRF, Channels, CORS, integraciones externas.
| libreria-aurora/src | Codigo React (componentes, hooks, utils) para UI. | Renderiza rutas, coordina llamadas a API, integra bibliotecas UI.
| docker-compose.yml | Orquestacion opcional para entornos locales. | Servicio web + base de datos si se desea contenedores.

## Backend Django
### Configuracion central
- **Autenticacion:** Modelo de usuario personalizado (apps.usuarios.Usuario) declarado en AUTH_USER_MODEL; autenticacion por JWT via djangorestframework-simplejwt.
- **API REST:** DRF con esquema generado por drf-spectacular; permisos por defecto IsAuthenticated excepto endpoints abiertos explicitamente.
- **Tiempo real y tareas asincronas:** Channels con InMemoryChannelLayer habilita evolucion a WebSockets (no hay consumidores activos aun).
- **Cross cutting:** corsheaders controla origenes (localhost:3000, GitHub Pages). WhiteNoise sirve activos estaticos en despliegues WSGI.

### Modulos de dominio y responsabilidades
| App | Responsabilidades | Modelos/Clases destacadas | Integraciones | Extension prevista |
|-----|-------------------|---------------------------|---------------|--------------------|
| libros | Catalogo base: libros, categorias, portadas. | Libro (renombra portadas en Cloudinary), Categoria. | Cloudinary para imagenes. | Expandir con versionado de inventario o metadata externa.
| compras | Carrito, pedidos, reservas, historial y devoluciones (QR). | Carrito, Reserva, Pedidos, HistorialDeCompras. | apps.finanzas.Saldo, qrcode, Email SMTP. | Inyectar proveedores de pago alternativos o colas de pedidos.
| finanzas | Gestion de tarjetas y saldo monetario. | Tarjeta, Saldo, HistorialSaldo. | Validaciones Decimal, integra con compras. | Sustituir Saldo por wallet externa o pasarela real.
| usuarios | Identidad, perfiles enriquecidos, preferencias, recuperacion de password. | Usuario (AbstractUser), UsuarioPreferencias, TokenRecuperacionPassword. | Signals interaccion con mensajeria; almacenamiento de fotos local/Cloudinary. | Agregar MFA, delegar a SSO externo.
| mensajeria | Foros personales, mensajes encadenados, notificaciones. | ForoPersonal, Mensaje, NotificacionMensaje. | Signals crean foros y notificaciones; integra con Channels futuro. | Transformar en microservicio o chat en tiempo real.
| noticias | Administracion de noticias, estados y notificaciones asociadas. | (Ver models.py) Publicacion y plantillas. | Puede disparar emails o integrarse con IA para redactar. | Conectar a CMS externo.
| busqueda | API de busqueda con filtros y persistencia de queries. | SearchView (APIView), SearchQuery. | Usa Django ORM y Q lookups sobre libros. | Reemplazar por motor Elastics/Opensearch manteniendo contrato REST.
| recomendaciones | Origen para recomendaciones personalizadas (modelos y vistas base). | Modelos stub listos para algoritmos. | Consume historial de compras/busquedas. | Punto natural para agentes de IA.
| tiendas | Inventario distribuido y ubicaciones. | Modelos de sucursales y stock local. | Puede integrarse con mapas (Leaflet en frontend). | Expandir con sincronizacion ERP.

### Principios de diseno aplicados
- **Modularidad explicita:** Cada app encapsula logica y datos; facilita aislar deployments futuros o migraciones a microservicios.
- **Logica de dominio en modelos:** Metodos como Carrito.pagar o Reserva.cancelar concentran reglas de negocio cercanas a los datos; favorece consistencia aunque se recomienda evaluar services si crece complejidad.
- **Eventos via signals:** Creacion de foros y notificaciones se automatiza con post_save; puede evolucionar a event bus cuando se requiera desacoplar.
- **Validacion temprana:** Uso de validators y excepciones (ValidationError) evita estados inconsistentes.
- **Generacion de documentos:** drf-spectacular mantiene Swagger actualizado; usarlo para contratos de integracion.

### Integraciones externas
- Cloudinary para archivos multimedia (Libro.portada, foto_perfil).
- SMTP (Gmail) para notificaciones y recuperacion de contrasena.
- qrcode para devoluciones; BytesIO para adjuntos.
- psycopg2 como driver PostgreSQL; django-environ para carga de variables.

## Frontend React
### Arquitectura
- **Stack:** React 18 con react-router-dom (HashRouter) para routing integramente del lado del cliente; Tailwind opcional con PostCSS.
- **Estructura:**
  - components/ agrupa vistas y componentes UI (catalogo, carrito, perfiles). Subcarpetas como components/profile separan paneles administrativos.
  - api/config.js centraliza endpoints y toggles entre backend local vs produccion (useProductionBackend).
  - hooks/useIsStaff evalua roles; utils/media abstrae cargas multimedia.
- **Estado:** Predomina estado local por componente; integraciones a futuro pueden introducir context/state managers.
- **Testing:** React Testing Library + Jest (scripts npm test).

### Integracion con backend
- Todas las llamadas usan getApiUrl/getApiUrlByKey para construir URLs en base al entorno.
- Autenticacion JWT: se espera almacenamiento del token tras login (gestion omitida en fragmentos pero debe residir en componentes de usuario).
- Mapas: react-leaflet + leaflet alimentados por datos de tiendas.
- Formularios financieros y de compras consumen endpoints de finanzas/compras; UI de notificaciones puede ampliar Channels.

## Flujos de datos clave
1. **Autenticacion y perfiles:**
   - Usuario registra/login (apps.usuarios endpoints /api/usuarios/ y /api/token/).
   - JWT expira en 1 hora; refresh 24h; frontend debe renovar.
   - Recuperacion de password genera TokenRecuperacionPassword y correo con enlace FRONTEND_RESET_PASSWORD_URL.
2. **Catalogo y busqueda:**
   - Frontend consume /api/libros/ para listado basico.
   - Busqueda avanzada via /api/?q=... y filtros; SearchQuery guarda historial para analitica y recomendaciones.
3. **Carrito, reservas y compras:**
   - Carrito Libro se maneja server-side; Carrito.pagar valida Saldo y stock.
   - Reserva impone limites (<=3 por libro, <=5 activas) y ajusta stock temporalmente.
   - HistorialDeCompras registra pedidos entregados y orquesta devoluciones con QR por email.
4. **Finanzas:**
   - Saldo.recargar_saldo normaliza Decimal y registra HistorialSaldo.
   - Integracion directa con compras: Carrito.pagar y Reserva.pagar_reserva invocan Saldo.descontar_saldo.
5. **Mensajeria y noticias:**
   - post_save de Usuario crea ForoPersonal.
   - Mensajes generan NotificacionMensaje; estado se actualiza automaticamente al recibir respuesta.
   - Noticias y suscripciones (apps.noticias) coordinan comunicacion con usuarios.
6. **Tiendas y geolocalizacion:**
   - Datos de tiendas alimentan vistas de mapa en frontend; futuros endpoints deben exponer geojson o lat/lng consistentes.

## Dependencias criticas
### Backend
- Django 4.2.x, djangorestframework, django-filter, django-cors-headers.
- drf-spectacular (documentacion API), channels (ASGI), simplejwt (JWT), pytest + pytest-django (tests).
- cloudinary + django-cloudinary-storage, Pillow (imagenes), qrcode (devoluciones).

### Frontend
- react, react-router-dom, react-leaflet/leaflet (mapas), react-credit-cards-2 (pagos UI), aos (animaciones), lucide-react (iconos).
- Testing: @testing-library/*, jest-dom.
- Construccion: tailwindcss, postcss, autoprefixer, gh-pages para despliegue.

## Estrategia de extensibilidad
- **Nuevos modulos backend:**
  1. Crear app Django bajo backend/apps; registrar en INSTALLED_APPS.
  2. Definir modelos + serializers + views; documentar con drf-spectacular via decorators extend_schema.
  3. Exponer rutas en urls.py de la app y agregarlas a config/urls.py con prefijo /api/<modulo>/.
  4. Aislar logica de negocio en servicios o managers para facilitar pruebas unitarias.
- **Agentes de IA:**
  - Ubicar en apps.recomendaciones o modulos dedicados; consumir historiales (compras, busquedas) mediante servicios consulta.
  - Exponer endpoints asincronicos via Channels o vistas DRF; considerar colas para procesamiento pesado.
  - Para interaccion conversacional, aprovechar ForoPersonal como contexto y ampliar con WebSockets.
- **Servicios compartidos:**
  - Extraer utilidades repetidas (emails, generacion de QR, calculos financieros) a paquetes internos (ej. backend/shared/services).
  - Encapsular integraciones externas (Cloudinary, email) en wrappers para sustituir proveedores sin tocar dominio.
- **Versionado de API:**
  - Mantener /api/v1/ como prefijo futuro; drf-spectacular facilita coexistencia de esquemas.

## Recomendaciones operativas
- Ejecutar pytest y python manage.py test en continuo; cubrir reglas de negocio en modelos (pagar, reservar, recargar).
- Mantener migraciones al dia; revisar que cada app tenga migrations versionadas.
- Monitorizar logs y errores de solicitudes; habilitar herramientas como Sentry en despliegue.
- Documentar contratos de endpoints mediante schema export (python manage.py spectacular --file schema.yaml) y compartir con frontend.
- Al introducir nuevas dependencias, actualice requirements.txt y package.json con bloqueo de versiones.

## Lineamientos para mejoras futuras
- Refactorizar metodos extensos en modelos hacia servicios dedicados para mejorar testabilidad.
- Sustituir InMemoryChannelLayer por backend Redis cuando se habiliten notificaciones en tiempo real.
- Implementar cache selectiva (ej. django-redis) para operaciones de catalogo y busqueda.
- Adoptar control de permisos granular (DRF permissions) por rol (ADMIN, BIBLIOTECARIO, LECTOR).
- Preparar un pipeline CI/CD (GitHub Actions) con linting, tests y despliegue automatizado.
- Diseñar contratos para integraciones de IA: endpoints de recomendacion, analisis de consultas de foro, generacion automatica de noticias.

---
Esta documentacion es la referencia actual y debe actualizarse junto con cambios significativos en arquitectura o dependencias.
