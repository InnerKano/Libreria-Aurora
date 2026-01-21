## 1. Visión General del Proyecto

El sistema se dividirá en módulos claramente definidos que cubrirán desde la administración de libros hasta la gestión de usuarios, compras, noticias, búsqueda, mensajería y recomendaciones. La idea es construir una solución escalable y modular, donde cada funcionalidad se encapsule en una aplicación (app) de Django y se consuma mediante APIs desde un front-end desarrollado en Next.js.

**Objetivos principales:**
- **Back-end robusto:** Utilizando Django (y Django REST Framework) para definir y exponer APIs seguras y escalables.
- **Front-end moderno:** Con Next.js se garantizará una experiencia de usuario dinámica y optimizada (renderizado híbrido y SSR).
- **Despliegue sencillo:** Separar los repositorios o carpetas para back-end y front-end, facilitando el despliegue en Render para Django y en github pages para Next.js.

---

## 2. Arquitectura del Proyecto

### A. División de Capas
- **Capa de presentación:** Next.js para la interfaz de usuario, consumo de APIs y rutas.
- **Capa de lógica de negocio y datos:** Django como back-end, gestionando la lógica de negocio, persistencia y seguridad.
- **Comunicación:** APIs RESTful (posiblemente con autenticación JWT) para comunicar front-end y back-end.

### B. Tecnologías y Herramientas
- **Lenguajes:** Python (Django) y JavaScript/TypeScript (Next.js).
- **Frameworks:** Django, Django REST Framework, Next.js.
- **Base de datos:** Inicialmente SQLite para desarrollo; en producción se puede migrar a PostgreSQL.
- **Control de versiones:** Git (con repositorios en GitHub).
- **Despliegue:** Heroku para Django y Vercel para Next.js.
- **Otras herramientas:** Entornos virtuales (virtualenv, pipenv o poetry), testing (pytest o unittest en Django, Jest para Next.js) y CI/CD si es posible.

---

## 3. Estructura del Proyecto y Organización de Carpetas

Dado que se tratará de un proyecto modular, se recomienda separar el back-end y el front-end en carpetas o incluso repositorios independientes. Un ejemplo de estructura podría ser:

### A. Repositorio General
```
/
├── .git/                         # Metadatos y hooks de control de versiones
├── .gitignore                    # Reglas de exclusión para Git
├── README.md                     # Resumen general del repositorio
├── docker-compose.yml            # Orquestación de servicios locales
├── backend/                      # Proyecto Django con apps modulares
│   ├── .env                      # Variables de entorno activas
│   ├── .env.example              # Plantilla de variables de entorno
│   ├── manage.py                 # Utilidades de administración de Django
│   ├── requirements.txt          # Lista de dependencias Python
│   ├── venv/                     # Entorno virtual local (opcional)
│   ├── config/                   # Configuración base del proyecto
│   │   ├── __init__.py
│   │   ├── asgi.py               # Punto de entrada ASGI
│   │   ├── settings.py           # Ajustes y parámetros globales
│   │   ├── urls.py               # Enrutamiento raíz del backend
│   │   └── wsgi.py               # Punto de entrada WSGI
│   └── apps/                     # Aplicaciones de dominio
│       ├── busqueda/             # Funcionalidad de búsqueda de libros
│       │   ├── __init__.py
│       │   ├── admin.py          # Registro en el admin de Django
│       │   ├── apps.py           # Configuración de la app
│       │   ├── models.py         # Modelos de búsqueda
│       │   ├── serializers.py    # Serializadores DRF
│       │   ├── urls.py           # Rutas específicas
│       │   ├── views.py          # Endpoints de búsqueda
│       │   ├── tests.py          # Pruebas unitarias del módulo
│       │   └── migrations/       # Migraciones (0001_initial.py, ...)
│       ├── compras/              # Gestión de pedidos y reservas
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py         # Entidades de compra
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   ├── tests.py
│       │   └── migrations/       # Migraciones (0001_initial.py, ...)
│       ├── finanzas/             # Procesos contables y financieros
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py         # Modelado financiero
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   ├── tests.py
│       │   └── migrations/
│       ├── libros/               # Administración de catálogos
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py         # Entidades de libros y ejemplares
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   ├── tests.py
│       │   ├── fixtures/         # Datos semilla (libros_prueba.json)
│       │   ├── scripts/          # Herramientas (manage_images.py, ...)
│       │   └── migrations/       # Migraciones (0001_initial.py, ...)
│       ├── mensajeria/           # Comunicación interna y notificaciones
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py         # Entidades de mensajes
│       │   ├── serializers.py
│       │   ├── signals.py        # Automatización de mensajes
│       │   ├── urls.py
│       │   ├── views.py
│       │   ├── tests.py
│       │   └── migrations/
│       ├── noticias/             # Gestión de noticias y avisos
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── notifications.py  # Manejo de notificaciones
│       │   ├── serializers.py
│       │   ├── signals.py        # Eventos de contenido
│       │   ├── urls.py
│       │   ├── views.py
│       │   ├── tests.py
│       │   ├── templates/        # Plantillas HTML específicas
│       │   └── migrations/
│       ├── tiendas/              # Integración de sucursales y stock
│       │   ├── __init__.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── migrations/
│       ├── recomendaciones/      # Sugerencias personalizadas
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── migrations/
│       │   ├── tests.py
│       │   └── views.py
│       ├── reseñas/              # Opiniones y valoraciones
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   └── views.py
│       └── usuarios/             # Gestión de usuarios y perfiles
│           ├── __init__.py
│           ├── admin.py
│           ├── apps.py
│           ├── models.py         # Modelos de identidad
│           ├── serializers.py
│           ├── signals.py        # Eventos de usuario
│           ├── urls.py
│           ├── views.py
│           ├── tests.py
│           ├── fixtures/         # Datos semilla (usuarios_prueba.json)
│           └── migrations/
├── docs/                         # Documentación complementaria
│   ├── TECHNICAL_REFERENCE.md    # Referencia técnica vigente
│   ├── readme.txt                # Notas informativas
│   ├── registro.md               # Registro de decisiones
│   └── agent_llm_docs/           # Recursos adicionales de agentes
└── libreria-aurora/              # Proyecto React (frontend)
  ├── .gitignore                # Reglas de exclusión frontend
  ├── package.json              # Dependencias y scripts npm
  ├── package-lock.json         # Versiones bloqueadas
  ├── postcss.config.js         # Ajustes de PostCSS
  ├── tailwind.config.js        # Configuración de Tailwind CSS
  ├── README.md                 # Documentación del frontend
  ├── node_modules/             # Dependencias instaladas
  ├── public/                   # Recursos estáticos públicos
  │   ├── favicon.ico
  │   ├── index.html            # Contenedor HTML principal
  │   ├── libro.ico             # Ícono alternativo
  │   ├── logo192.png
  │   ├── logo512.png
  │   ├── manifest.json         # PWA manifest
  │   └── robots.txt            # Política para buscadores
  └── src/                      # Código fuente React
    ├── api/                  # Configuración de cliente HTTP
    │   └── config.js
    ├── components/           # Componentes reutilizables
    │   ├── book/             # Componentes de tarjetas de libros
    │   │   ├── addTocCartButton.jsx
    │   │   └── bookCard.jsx
    │   ├── carrito.jsx
    │   ├── catalogo.jsx
    │   ├── DetalleLibro.jsx
    │   ├── Home.jsx
    │   ├── login.jsx
    │   ├── miPerfil.jsx
    │   ├── navBar.jsx
    │   ├── profile/          # Paneles de perfil y administración
    │   │   ├── addPaymentMethod.jsx
    │   │   ├── adminForumMessages.jsx
    │   │   ├── adminLibros.jsx
    │   │   ├── ChangePassword.jsx
    │   │   ├── editContentPreference.jsx
    │   │   ├── editProfile.jsx
    │   │   ├── financialManagement.jsx
    │   │   ├── forumMessages.jsx
    │   │   ├── gestionarTiendas.jsx
    │   │   ├── handleNewsSubscription.jsx
    │   │   ├── pedidos.jsx
    │   │   └── reservas.jsx
    │   ├── recuperarContraseña.jsx
    │   ├── registro.jsx
    │   ├── ResetPassword.jsx
    │   ├── SearchBook.jsx
    │   ├── Tiendas.jsx
    │   └── ui/               # Componentes UI atómicos
    │       ├── authFrame.jsx
    │       ├── buttonA.jsx
    │       ├── input.jsx
    │       ├── LoadingSpinner.jsx
    │       └── README.md
    ├── hooks/                # Hooks personalizados
    │   └── useIsStaff.js
    ├── images/               # Activos gráficos
    │   ├── Logo.jpg
    │   └── Logo.svg
    ├── utils/                # Utilidades compartidas
    │   └── media.js
    ├── App.js
    ├── App.test.js
    ├── index.css
    ├── index.js
    ├── logo.svg
    ├── reportWebVitals.js
    └── setupTests.js
```

*Nota:* Python genera carpetas __pycache__/ en varias rutas; no concentran lógica propia y pueden regenerarse automáticamente.

### B. Organización Interna de cada App en Django

La estructura interna de las apps ahora incluye archivos adicionales según las necesidades específicas:

```
app_nombre/
├── migrations/        # Migraciones de la base de datos
├── __init__.py
├── admin.py           # Configuración del panel de administración
├── apps.py            # Configuración de la app
├── models.py          # Definición de modelos (Libro, Ejemplar, etc.)
├── serializers.py     # Serializadores para la API REST
├── views.py           # Vistas o endpoints de la API
├── urls.py            # Rutas específicas del módulo
├── tests.py           # Pruebas unitarias
├── signals.py         # Señales de Django (en algunas apps)
├── notifications.py   # Funciones de notificación (en algunas apps)
├── fixtures/          # Datos iniciales para la base de datos (en algunas apps)
├── templates/         # Plantillas HTML específicas (en algunas apps)
└── scripts/           # Scripts adicionales para la app (en algunas apps)
```

---

## 4. Planificación de Módulos y Funcionalidades (RF)

Cada módulo deberá implementar los requerimientos funcionales (RF) correspondientes:

### A. Módulo de Administración de Libros
- **RF1 a RF5:**
  - Formularios/API para registrar libros (validación de campos obligatorios).
  - Generación de un código único por ejemplar.
  - Funciones CRUD (crear, editar, eliminar).
  - Lógica para mover libros agotados a un histórico.
  - Registro automático de noticias al agregar libros nuevos.

### B. Módulo de Compra y Reserva de Libros
- **RF6 a RF20:**
  - Búsqueda y filtrado de libros.
  - Lógica de reserva (limitaciones de cantidad, tiempo de reserva de 24 horas).
  - Carrito de compras e integración con módulos financieros.
  - Gestión de pagos con tarjetas y manejo de saldo.
  - Funcionalidad para cancelar compras/reservas y registrar histórico.
  - Proceso de devolución (incluyendo generación de código QR, validación de plazos y razones).
  - Seguimiento del envío y opciones de recogida en tienda o visualización de tiendas en el mapa.

### C. Módulo de Usuarios
- **RF21 a RF28:**
  - Gestión de diferentes roles: Root, Administrador, Cliente y Visitante.
  - Registro y edición de perfil, validación de datos personales.
  - Suscripción al sistema de noticias.
  - Automatización de mensajes de cumpleaños con descuentos.

### D. Módulo de Noticias y Mensajería
- **RF29 a RF31 y RF35:**
  - Subscripción a novedades y catálogo de nuevos libros.
  - Sistema de mensajería para interacción entre usuarios y administradores:
    - Foros personales por usuario
    - Sistema de mensajes con estados (abierto/respondido/cerrado)
    - Respuestas anidadas a mensajes
    - Notificaciones automáticas para nuevos mensajes y respuestas
    - Panel de administración para gestión de foros y mensajes
    - API REST completa con documentación Swagger
    - Integración con el sistema de autenticación y permisos
    - Señales automáticas para creación de foros y notificaciones

### E. Módulo de Búsqueda
- **RF32:**
  - Endpoint de búsqueda con filtros por distintos criterios (puede implementarse con Django ORM o soluciones más avanzadas de búsqueda, si se requiere).

### F. Módulo de Gestión Financiera
- **RF33 y RF34:**
  - Gestión de tarjetas y saldo.
  - Integración de gateways de pago (simulada para fines universitarios o con librerías de prueba).

### G. Módulo de Recomendación
- **RF36 y RF37:**
  - Algoritmo para recomendaciones basado en historial de compras y búsquedas.
  - Envío de recomendaciones por correo (integración con un servicio de email).

---

## 5. Planificación del Desarrollo

### Fase 1: Análisis y Diseño
- **Revisión de Requerimientos:** Estudiar cada RF y definir casos de uso y diagramas (UML o ER) para la base de datos.
- **Diseño de la Arquitectura:** Diagrama de componentes, flujo de datos entre Django y Next.js, autenticación y manejo de roles.
- **Definición de Endpoints:** Especificar la API RESTful para cada módulo.

### Fase 2: Configuración del Entorno y Estructura Base
- **Back-end:** Configurar el entorno virtual, instalar Django y Django REST Framework, generar el proyecto y las apps iniciales.
- **Front-end:** Inicializar el proyecto Next.js, definir rutas básicas y conectar con las APIs del back-end.
- **Control de Versiones:** Crear el repositorio en GitHub y definir ramas para desarrollo, testing y despliegue.

### Fase 3: Desarrollo de Módulos (Iterativo)
- **Iteración 1:** 
  - Desarrollo del módulo de Usuarios y autenticación.
  - Creación de endpoints para registro, login y perfil.
- **Iteración 2:** 
  - Módulo de Administración de Libros (CRUD, asignación de código único, manejo de stock y noticias).
- **Iteración 3:** 
  - Módulo de Compra y Reserva de Libros y Gestión Financiera (carrito, pagos simulados, devoluciones).
- **Iteración 4:** 
  - Módulo de Noticias y Mensajería (integración de mensajería instantánea).
- **Iteración 5:** 
  - Módulo de Búsqueda y Recomendación (implementación de filtros y lógica de recomendaciones).

Cada iteración incluirá:
- Desarrollo de nuevas funcionalidades.
- Pruebas unitarias e integración.
- Revisión de código y actualización de la documentación.

### Fase 4: Integración y Pruebas Finales
- **Integración Completa:** Unir todas las APIs y funcionalidades.
- **Pruebas de Usuario:** Testing funcional y de usabilidad en ambos entornos.
- **Documentación:** Generar documentación técnica y de usuario (README, diagramas, manual de despliegue).

---

## 6. Despliegue y Mantenimiento

### A. Despliegue
- **GitHub:** Repositorio central para control de versiones y colaboración.
- **Render (Back-end):**  
  - Configurar el `Procfile`, variables de entorno y base de datos (usando PostgreSQL en Render).
  - Asegurar que las migraciones y configuraciones de tu framework backend (por ejemplo, Django, Express.js) sean compatibles con producción.
- **GitHub Pages (Front-end):**
  - Configurar el despliegue de tu proyecto React.
  - Usar Tailwind CSS para el diseño y estilos.
  - Asegurar que el archivo `package.json` tenga los scripts necesarios para el despliegue en GitHub Pages.
- **Configuraciones adicionales:**  
  - Configurar variables de entorno necesarias (por ejemplo, URL base de la API).
  - Integrar Tailwind CSS con tu proyecto React adecuadamente.

### B. Consideraciones Post-Despliegue
- **Monitoreo:** Implementar herramientas básicas de logging y monitoreo.
- **Feedback:** Establecer un mecanismo para recibir feedback de usuarios y pruebas en vivo.
- **Documentación Continua:** Mantener actualizada la documentación del proyecto.

---

## 7. Consideraciones Finales

- **Modularidad:** Asegúrate de que cada módulo esté bien desacoplado y se comunique a través de APIs para facilitar el mantenimiento y la escalabilidad.
- **Seguridad:** Gestiona adecuadamente la autenticación, autorización y protección de datos sensibles (especialmente en módulos financieros y de usuarios).
- **Iteración y Pruebas:** Adopta un enfoque ágil para desarrollar y probar cada funcionalidad, integrando pruebas unitarias e integrales en cada fase.
- **Despliegue Simple:** Dado que es un proyecto universitario, evita configuraciones complejas (como Docker) a menos que sea estrictamente necesario. La simplicidad en el despliegue facilitará la demostración del proyecto.

Esta planificación te servirá como hoja de ruta para desarrollar tu librería virtual, asegurando que cada parte del proyecto se aborde de manera estructurada y profesional. ¡Éxito en tu proyecto!