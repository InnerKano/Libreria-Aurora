from django.shortcuts import render
from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from django.core.mail import send_mail
import logging
from smtplib import SMTPException
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from .serializers import (
    ListaPreferenciasSerializer,
    PreferenciasUsuarioPorCategoriauAutorSerializer,
    UsuarioSerializer,
    UsuarioRegistroSerializer,
    CambioContraseñaSerializer,
    RecuperarContraseñaSerializer,
    ProfileUpdateSerializer,
    PreferenciasUsuarioSerializer,
    ValidarTokenSerializer,
    RestablecerContraseñaSerializer
)
from .models import UsuarioPreferencias, TokenRecuperacionPassword, Libro, Categoria
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from django.utils.http import urlencode

logger = logging.getLogger(__name__)
Usuario = get_user_model()

@extend_schema_view(
    list=extend_schema(
        description="Obtiene la lista de todos los usuarios",
        responses={200: UsuarioSerializer(many=True)}
    ),
    retrieve=extend_schema(
        description="Obtiene un usuario específico por su ID",
        responses={
            200: UsuarioSerializer,
            404: {"description": "Usuario no encontrado"}
        }
    ),
    create=extend_schema(
        description="Registra un nuevo usuario",
        request=UsuarioRegistroSerializer,
        responses={
            201: UsuarioSerializer,
            400: {"description": "Datos inválidos"}
        },
        examples=[
            OpenApiExample(
                'Ejemplo Registro',
                value={
                    "email": "usuario@ejemplo.com",
                    "username": "usuario1",
                    "password": "contraseña123",
                    "password2": "contraseña123",
                    "first_name": "Nombre",
                    "last_name": "Apellido",
                    "tipo_usuario": "LECTOR",
                    "nacionalidad" : "Colombia",
                    "departamento" : "Cundinamarca",
                    "numero_identificacion": "12345678910",
                }
            )
        ]
    ),
    update=extend_schema(
        description="Actualiza todos los campos de un usuario existente",
        request=UsuarioSerializer,
        responses={
            200: UsuarioSerializer,
            400: {"description": "Datos inválidos"},
            404: {"description": "Usuario no encontrado"}
        }
    ),
    partial_update=extend_schema(
        description="Actualiza parcialmente los campos de un usuario existente",
        request=UsuarioSerializer,
        responses={
            200: UsuarioSerializer,
            400: {"description": "Datos inválidos"},
            404: {"description": "Usuario no encontrado"}
        }
    ),
    destroy=extend_schema(
        description="Elimina un usuario existente",
        responses={
            204: None,
            404: {"description": "Usuario no encontrado"}
        }
    )
)
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'recuperar_contraseña', 'validar_token', 'restablecer_contraseña']:
            return [AllowAny()]  # Permitir acceso público a estos métodos
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return UsuarioRegistroSerializer
        elif self.action == 'actualizar_perfil':
            return ProfileUpdateSerializer
        elif self.action in ['preferencias_suscripcion', 'actualizar_preferencias']:
            return PreferenciasUsuarioSerializer
        elif self.action == 'validar_token':
            return ValidarTokenSerializer
        elif self.action == 'restablecer_contraseña':
            return RestablecerContraseñaSerializer
        elif self.action == 'preferencias_libros':  # 👈 ¡ESTO ES LO QUE FALTABA!
            return ListaPreferenciasSerializer
        return self.serializer_class

    @extend_schema(
        description="Cambia la contraseña de un usuario",
        request=CambioContraseñaSerializer,
        responses={
            200: {"description": "Contraseña actualizada correctamente"},
            400: {"description": "Contraseña actual incorrecta o datos inválidos"},
            404: {"description": "Usuario no encontrado"}
        },
        examples=[
            OpenApiExample(
                'Ejemplo Cambio Contraseña',
                value={
                    "old_password": "contraseña_actual",
                    "new_password": "nueva_contraseña"
                }
            )
        ]
    )
    @action(detail=True, methods=['post'])
    def cambiar_contraseña(self, request, pk=None):
        usuario = self.get_object()
        serializer = CambioContraseñaSerializer(data=request.data)
        
        if serializer.is_valid():
            if not usuario.check_password(serializer.validated_data['old_password']):
                return Response(
                    {"old_password": "Contraseña incorrecta"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            usuario.set_password(serializer.validated_data['new_password'])
            usuario.save()
            return Response(
                {'message': 'Contraseña actualizada correctamente'},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Obtiene el perfil del usuario autenticado",
        responses={
            200: UsuarioSerializer,
            401: {"description": "No autenticado"}
        }
    )
    @action(detail=False, methods=['get'])
    def perfil(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    

    @extend_schema(
        description="Genera un token para recuperar la contraseña y envía un correo electrónico con un código de recuperación",
        request=RecuperarContraseñaSerializer,
        responses={
            200: {"description": "Correo enviado correctamente"},
            400: {"description": "Email no proporcionado"},
            404: {"description": "Usuario no encontrado"}
        },
        examples=[
            OpenApiExample(
                "Ejemplo de solicitud",
                value={"email": "usuario@ejemplo.com"},
                description="Ejemplo de cómo enviar el correo electrónico en el cuerpo de la solicitud"
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def recuperar_contraseña(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email no proporcionado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            usuario = Usuario.objects.get(email=email)
            
            # Generar token de recuperación
            token_obj = TokenRecuperacionPassword.generar_token(usuario)
            token = token_obj.token
            
            # Enviar email con el token
            frontend_url = "https://pausa11.github.io/LIbreria-Aurora/#/reset-password"
            reset_url = f"{frontend_url}?token={token}"
            
            # Construir mensaje de correo
            mensaje = f"""
Hola {usuario.username},

Has solicitado restablecer tu contraseña. Para crear una nueva contraseña, haz clic en el siguiente enlace:

{reset_url}

Este enlace será válido durante 15 minutos.

Si no has solicitado cambiar tu contraseña, puedes ignorar este mensaje.

Saludos,
El equipo de Librería Aurora
"""

            try:
                send_mail(
                    'Recuperación de contraseña - Librería Aurora',
                    mensaje,
                    'auroralibreria05@gmail.com',
                    [email],
                    fail_silently=False,
                )
            except SMTPException as exc:
                logger.exception("Error enviando correo de recuperación para %s", email)
                return Response(
                    {
                        'error': 'No fue posible enviar el correo de recuperación. Inténtalo nuevamente en unos minutos.'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            except Exception as exc:  # Capturamos cualquier otro error inesperado
                logger.exception("Error inesperado durante la recuperación de contraseña")
                return Response(
                    {'error': 'Ocurrió un error inesperado al procesar la solicitud.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            return Response(
                {'message': 'Correo de recuperación enviado'},
                status=status.HTTP_200_OK
            )
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        description="Valida un token de recuperación de contraseña",
        request=ValidarTokenSerializer,
        responses={
            200: {"description": "Token válido"},
            400: {"description": "Token inválido o expirado"}
        },
        examples=[
            OpenApiExample(
                "Ejemplo de solicitud",
                value={"token": "550e8400-e29b-41d4-a716-446655440000"},
                description="Ejemplo de cómo validar un token de recuperación"
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def validar_token(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            return Response(
                {'message': 'Token válido'},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        description="Restablece la contraseña usando un token válido",
        request=RestablecerContraseñaSerializer,
        responses={
            200: {"description": "Contraseña restablecida correctamente"},
            400: {"description": "Datos inválidos o token expirado"}
        },
        examples=[
            OpenApiExample(
                "Ejemplo de solicitud",
                value={
                    "token": "550e8400-e29b-41d4-a716-446655440000",
                    "new_password": "NuevaContraseña123",
                    "new_password2": "NuevaContraseña123"
                },
                description="Ejemplo de cómo restablecer una contraseña con un token"
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def restablecer_contraseña(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            token_str = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            # Obtener el token y el usuario
            try:
                token_obj = TokenRecuperacionPassword.objects.get(token=token_str, usado=False)
                if not token_obj.esta_activo:
                    return Response(
                        {'error': 'El token ha expirado'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Actualizar contraseña
                usuario = token_obj.usuario
                usuario.set_password(new_password)
                usuario.save()
                
                # Marcar token como usado
                token_obj.usado = True
                token_obj.save()
                
                return Response(
                    {'message': 'Contraseña restablecida correctamente'},
                    status=status.HTTP_200_OK
                )
            
            except TokenRecuperacionPassword.DoesNotExist:
                return Response(
                    {'error': 'Token inválido o ya utilizado'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Permite al usuario actualizar su información de perfil",
        request=ProfileUpdateSerializer,
        responses={
            200: UsuarioSerializer,
            400: {"description": "Datos inválidos"},
        },
        examples=[
            OpenApiExample(
                'Ejemplo de actualización de perfil',
                value={
                    "username": "nuevo_usuario",
                    "first_name": "Nuevo Nombre",
                    "last_name": "Nuevo Apellido",
                    "telefono": "+573001234567",
                    "direccion": "Nueva Dirección #123",
                    "fecha_nacimiento": "1990-01-01",
                    "nacionalidad": "Colombia",
                    "departamento": "Cundinamarca",
                }
            )
        ]
    )
    @action(detail=False, methods=['put', 'patch'])
    def actualizar_perfil(self, request):
        usuario = request.user
        serializer = self.get_serializer(usuario, data=request.data, partial=True)
        
        if 'foto_perfil' in request.FILES:
            # Verificar tamaño de imagen (opcional)
            if request.FILES['foto_perfil'].size > 2 * 1024 * 1024:
                return Response(
                    {"error": "La imagen no debe exceder 2MB"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if serializer.is_valid():
            serializer.save()
            # Devolver los datos actualizados usando el serializer completo
            return Response(
                UsuarioSerializer(usuario).data,
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        description="Obtiene la imagen de perfil del usuario autenticado",
        responses={
            200: {"description": "URL de la imagen de perfil"},
            404: {"description": "Imagen no encontrada"}
        }
    )
    @action(detail=False, methods=['get'])
    def obtener_imagen_perfil(self, request):
        """
        Devuelve la URL de la imagen de perfil del usuario autenticado.
        """
        usuario = request.user
        if usuario.foto_perfil:
            return Response(
                {'foto_perfil': usuario.foto_perfil.url},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'error': 'No se encontró la imagen de perfil'},
            status=status.HTTP_404_NOT_FOUND
        )

    @extend_schema(
        description="Obtiene las preferencias de suscripción del usuario",
        responses={
            200: PreferenciasUsuarioSerializer,
            404: {"description": "Preferencias no encontradas"}
        }
    )
    @action(detail=False, methods=['get'])
    def preferencias_suscripcion(self, request):
        """
        Obtiene las preferencias de suscripción del usuario autenticado.
        Si no existen, las crea con valores predeterminados.
        """
        usuario = request.user
        preferencias, created = UsuarioPreferencias.objects.get_or_create(usuario=usuario)
        
        serializer = self.get_serializer(preferencias)
        return Response(serializer.data)
    
    @extend_schema(
        description="Actualiza las preferencias de suscripción del usuario",
        request=PreferenciasUsuarioSerializer,
        responses={
            200: PreferenciasUsuarioSerializer,
            400: {"description": "Datos inválidos"}
        },
        examples=[
            OpenApiExample(
                'Ejemplo de actualización de preferencias',
                value={
                    "recibir_actualizaciones": True,
                    "recibir_noticias": False,
                    "recibir_descuentos": True,
                    "recibir_mensajes_foro": False
                }
            )
        ]
    )
    @action(detail=False, methods=['put', 'patch'])
    def actualizar_preferencias(self, request):
        """
        Actualiza las preferencias de suscripción del usuario autenticado.
        Si no existen, las crea con los valores proporcionados.
        """
        usuario = request.user
        preferencias, created = UsuarioPreferencias.objects.get_or_create(usuario=usuario)
        
        serializer = self.get_serializer(preferencias, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Agrega una preferencia u autor a la lista de preferencias del usuario",
        request=PreferenciasUsuarioPorCategoriauAutorSerializer,
        responses={
            200: PreferenciasUsuarioPorCategoriauAutorSerializer,
            400: {"description": "Datos inválidos"}
        },
        examples=[
            OpenApiExample(
                'Ejemplo de agregar preferencia',
                value={
                    "preferencias": "Ficción"
                }
            )
        ]
    )
    @action(detail=False, methods=['post'])
    def agregar_preferencia(self, request):
        """
        Agrega una preferencia a la lista de preferencias del usuario autenticado.
        """
        usuario = request.user
        usuario_preferencias, created = UsuarioPreferencias.objects.get_or_create(usuario=usuario)
        
        serializer = PreferenciasUsuarioPorCategoriauAutorSerializer(data=request.data)
        if serializer.is_valid():
            preferencias = serializer.validated_data['preferencias']
            usuario_preferencias.agregar_preferencia(preferencias)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        description="Elimina una preferencia de la lista de preferencias del usuario",
        request=PreferenciasUsuarioPorCategoriauAutorSerializer,
        responses={
            200: PreferenciasUsuarioPorCategoriauAutorSerializer,
            400: {"description": "Datos inválidos"}
        },
        examples=[
            OpenApiExample(
                'Ejemplo de eliminar preferencia',
                value={
                    "preferencias": "Ficción"
                }
            )
        ]
    )
    @action(detail=False, methods=['delete'])
    def eliminar_preferencia(self, request):
        """
        Elimina una preferencia de la lista de preferencias del usuario autenticado.
        """
        usuario = request.user
        usuario_preferencias, created = UsuarioPreferencias.objects.get_or_create(usuario=usuario)
        
        serializer = PreferenciasUsuarioPorCategoriauAutorSerializer(data=request.data)
        if serializer.is_valid():
            preferencias = serializer.validated_data['preferencias']
            usuario_preferencias.eliminar_preferencia(preferencias)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    @extend_schema(
        description="GET: Lista las preferencias de libros. PUT: Reemplaza toda la lista.",
        request=ListaPreferenciasSerializer,
        responses={200: ListaPreferenciasSerializer}
    )
    @action(detail=False, methods=['get', 'put'], url_path='preferencias_libros')
    def preferencias_libros(self, request):
        usuario = request.user
        preferencias_obj, _ = UsuarioPreferencias.objects.get_or_create(usuario=usuario)

        if request.method == 'GET':
            serializer = ListaPreferenciasSerializer(preferencias_obj)
            return Response(serializer.data)

        elif request.method == 'PUT':
            serializer = ListaPreferenciasSerializer(data=request.data)
            if serializer.is_valid():
                nuevas_preferencias = serializer.validated_data['preferencias']
                autores = set(Libro.objects.values_list('autor', flat=True))
                categorias = set(Categoria.objects.values_list('nombre', flat=True))

                for pref in nuevas_preferencias:
                    if pref not in autores and pref not in categorias:
                        return Response(
                            {"error": f"'{pref}' no es un autor ni una categoría válida."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                preferencias_obj.preferencias = nuevas_preferencias
                preferencias_obj.save()
                return Response(serializer.data)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)