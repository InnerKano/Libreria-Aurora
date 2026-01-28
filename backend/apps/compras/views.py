from django.shortcuts import get_object_or_404, render
from apps.libros.models import Libro
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from .models import Carrito, HistorialDeCompras, Pedidos, Reserva
from .serializers import AgregaroQuitarLibroSerializer, CarritoLibroSerializer, HistorialDeComprasSerializer, PedidoLibroSerializer, PedidosSerializer
from .serializers import ReservaSerializer, CrearReservaSerializer, IdReservaSerializer, CancelarPedidoSerializer, CambiarEstadoPedidoSerializer, IdHistorialSerializer
from .serializers import AdminPedidosSerializer, AdminHistorialDeComprasSerializer

@extend_schema_view(
    list=extend_schema(description="Obtiene la lista de todos los carritos"),
    retrieve=extend_schema(description="Obtiene un carrito específico por su ID"),
    create=extend_schema(description="Crea un nuevo carrito"),
    update=extend_schema(description="Actualiza un carrito existente"),
    destroy=extend_schema(description="Elimina un carrito existente"),
)
class CarritoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para ver y editar carritos.
    
    Este ViewSet permite gestionar los carritos de compra con operaciones CRUD completas.
    Se pueden agregar y quitar libros del carrito, así como calcular el total.
    """
    queryset = Carrito.objects.all()
    
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    @extend_schema(
        description="Vacía un carrito eliminando todos sus libros",
        responses={200: "Carrito vaciado", 400: None},
    )
    @action(detail=False, methods=['post'])
    def vaciar(self, request, pk=None):
        carrito = Carrito.objects.get(usuario=request.user)
        carrito.limpiar_carrito()
        return Response({"Carrito vaciado"}, status=status.HTTP_200_OK)
    
    @extend_schema(
        description="Agrega un libro al carrito",
        request = AgregaroQuitarLibroSerializer,
        responses={200: "Libro agregado: (Nombre del libro)", 400: None}
    )
    @action(detail=False, methods=['post'])
    def agregar_libro(self, request, pk=None):
        carrito = Carrito.objects.get(usuario=request.user)
        serializer = AgregaroQuitarLibroSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({"error": "Se requiere el ID del libro"}, status=status.HTTP_400_BAD_REQUEST)
        
        libro_id = serializer.validated_data.get('libro_id')
        cantidad = serializer.validated_data.get('cantidad', 1)

        try:
            from apps.libros.models import Libro
            libro = Libro.objects.get(id=libro_id)
            carrito.agregar_libro(libro, cantidad)
            carrito.save()
            return Response({"Libro agregado": libro.titulo}, status=status.HTTP_200_OK)
        except Libro.DoesNotExist:
            return Response({"error": "Libro no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        description="Quita un libro del carrito",
        request=AgregaroQuitarLibroSerializer,
        responses={200: 'Libro eliminado con exito', 400: None}
    )
    @action(detail=False, methods=['post'])
    def quitar_libro(self, request, pk=None):
        carrito = Carrito.objects.get(usuario=request.user)
        serializer = AgregaroQuitarLibroSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({"error": "Se requiere el ID del libro"}, status=status.HTTP_400_BAD_REQUEST)
        
        libro_id = serializer.validated_data.get('libro_id')
        cantidad = serializer.validated_data.get('cantidad', 1)
        try:
            from apps.libros.models import Libro
            libro = Libro.objects.get(id=libro_id)
            carrito.quitar_libro(libro, cantidad)
            return Response({"Libro eliminado": libro.titulo}, status=status.HTTP_200_OK)
        except Libro.DoesNotExist:
            return Response({"error": "Libro no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(description="Obtiene una lista de los libros en el carrito", responses={200: "Libros: []", 400: None})
    @action(detail=False, methods=['get'])
    def obtener_libros(self, request):
        carrito = Carrito.objects.get(usuario=request.user)
        libros = carrito.obtener_libros()
        serializer = CarritoLibroSerializer(libros, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(description="Pagar", responses={200: "Carrito pagado con exito", 400: None})
    @action(detail=False, methods=['post'])
    def pagar(self, request):
        carrito = Carrito.objects.get(usuario=request.user)
        resultado = carrito.pagar()
        return Response({"mensaje": resultado})
        
    
class PedidoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar pedidos.
    Este ViewSet permite a los usuarios ver su historial de pedidos y obtener detalles de cada pedido.
    """
    queryset = Pedidos.objects.all()
    serializer_class = PedidosSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    @extend_schema(
        description="Obtiene el historial de pedidos del usuario",
        responses={200: PedidosSerializer(many=True)},
    )
    @action(detail=False, methods=['get'])
    def historial_pedidos(self, request):
        """
        Obtiene el historial de pedidos del usuario.
        
        Este método devuelve una lista de todos los pedidos realizados por el usuario.
        """
        from .models import Pedidos
        pedidos = Pedidos.objects.filter(usuario=request.user)
        serializer = PedidosSerializer(pedidos, many=True)
        PedidoLibroSerializer(pedidos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        description="(Staff) Obtiene todos los pedidos del sistema",
        responses={200: AdminPedidosSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def admin_list(self, request):
        pedidos = Pedidos.objects.select_related('usuario').prefetch_related('pedidolibro_set__libro').order_by('-fecha')
        serializer = AdminPedidosSerializer(pedidos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @extend_schema(
        description = "Cancela un pedido",
        request = CancelarPedidoSerializer,
        responses = {200: "Pedido cancelado con éxito", 400: None}
    )
    @action(detail=False, methods=['post'])
    def cancelar_pedido(self, request):
        """
        Cancela un pedido específico.
        
        Este método permite al usuario cancelar un pedido existente.
        """
        serializer = CancelarPedidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        pedido_id = serializer.validated_data['pedido_id']
        try:
            pedido = Pedidos.objects.get(id=pedido_id, usuario=request.user)
            if pedido.estado == 'Cancelado':
                return Response({"error": "El pedido ya está cancelado"}, status=status.HTTP_400_BAD_REQUEST)
            pedido.cancelar_pedido()
            return Response({"mensaje": "Pedido cancelado con éxito"}, status=status.HTTP_200_OK)
        except Pedidos.DoesNotExist:
            return Response({"error": "Pedido no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    
    @extend_schema(
        description="Cambia el estado de un pedido",
        request = CambiarEstadoPedidoSerializer,
        responses = {200: "Estado del pedido actualizado con éxito", 400: None}
    )
    @action(detail=False, methods=['post'])
    def cambiar_estado(self, request):
        """
        Cambia el estado de un pedido específico.
        
        Este método permite al usuario cambiar el estado de un pedido existente.
        """
        serializer = CambiarEstadoPedidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        pedido_id = serializer.validated_data['pedido_id']
        nuevo_estado = serializer.validated_data['nuevo_estado']
        
        try:
            pedido = Pedidos.objects.get(id=pedido_id, usuario=request.user)
            resultado = pedido.cambiar_estado(nuevo_estado)
            if resultado['estado'] == 'exito':
                return Response({"mensaje": "Estado del pedido actualizado con éxito"}, status=status.HTTP_200_OK)
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
        except Pedidos.DoesNotExist:
            return Response({"error": "Pedido no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        description="(Staff) Cambia el estado de cualquier pedido",
        request = CambiarEstadoPedidoSerializer,
        responses = {200: "Estado del pedido actualizado con éxito", 400: None}
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def admin_cambiar_estado(self, request):
        serializer = CambiarEstadoPedidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pedido_id = serializer.validated_data['pedido_id']
        nuevo_estado = serializer.validated_data['nuevo_estado']

        try:
            pedido = Pedidos.objects.get(id=pedido_id)
            resultado = pedido.cambiar_estado(nuevo_estado)
            if resultado['estado'] == 'exito':
                return Response({"mensaje": "Estado del pedido actualizado con éxito"}, status=status.HTTP_200_OK)
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
        except Pedidos.DoesNotExist:
            return Response({"error": "Pedido no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    
class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.all()
    serializer_class = ReservaSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    @extend_schema(
        description="Obtiene la lista de reservas del usuario autenticado",
        responses={200: ReservaSerializer(many=True)}
    )
    def get_queryset(self):
        # Solo mostrar reservas del usuario autenticado
        return Reserva.objects.filter(usuario=self.request.user)

    @extend_schema(
        description="Crea una nueva reserva de libro",
        request=CrearReservaSerializer,
        responses={201: ReservaSerializer, 400: None}
    )
    @action(detail=False, methods=['post'])
    def reservar(self, request):
        serializer = CrearReservaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        libro = get_object_or_404(Libro, pk=serializer.validated_data['libro_id'])
        cantidad = serializer.validated_data['cantidad']
        usuario = request.user

        resultado = Reserva().reservar_libro(libro, usuario, cantidad)
        if resultado['estado'] == 'exito':
            reserva = resultado['reserva']
            return Response(ReservaSerializer(reserva).data, status=status.HTTP_201_CREATED)
        return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Cancela una reserva de libro",
        request=IdReservaSerializer,
        responses={200: ReservaSerializer, 400: None}
    )
    @action(detail=False, methods=['post'])
    def cancelar(self, request, pk=None):
        serializer = IdReservaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reserva = get_object_or_404(Reserva, pk=serializer.validated_data['reserva_id'])
        resultado = reserva.cancelar_reserva()
        if resultado['estado'] == 'exito':
            return Response(resultado, status=status.HTTP_200_OK)
        return Response(resultado, status=status.HTTP_400_BAD_REQUEST)


    @extend_schema(
        description="Verifica si todas las reservas hechas por un usuario han expirado",
        request=None,
        responses={200: ReservaSerializer, 400: None}
    )
    @action(detail=False, methods=['post'])
    def verificar_expiracion(self, request):
        reservas = Reserva.objects.filter(usuario=request.user, estado='Reservado')
        expiradas = 0
        for reserva in reservas:
            resultado = reserva.verificar_expiracion()
            if resultado['estado'] == 'exito':
                expiradas += 1
        return Response(
            {"estado": "exito", "mensaje": f"Se han expirado {expiradas} reservas."},
            status=status.HTTP_200_OK
        )
    
    @extend_schema(
        description="Paga una reserva",
        request=IdReservaSerializer,
        responses={200: "Reserva pagada con éxito", 400: None}
    )
    @action(detail=False, methods=['post'])
    def pagar_reserva(self, request, pk=None):
        serializer = IdReservaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reserva = get_object_or_404(Reserva, pk=serializer.validated_data['reserva_id'])
        resultado = reserva.pagar_reserva()
        if resultado['estado'] == 'exito':
            return Response({"mensaje": "Reserva pagada con éxito"}, status=status.HTTP_200_OK)
        return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
    

class HistorialDeComprasViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HistorialDeComprasSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Solo muestra el historial del usuario autenticado
        return HistorialDeCompras.objects.filter(usuario=self.request.user).select_related('pedido').order_by('-fecha')
    
    @extend_schema(
        description="Obtiene el historial de compras del usuario autenticado",
        responses={200: HistorialDeComprasSerializer(many=True)}
    )
    def listar_historial(self, request):
        queryset = self.get_queryset()
        return Response(HistorialDeComprasSerializer(queryset, many=True).data)

    @extend_schema(
        description="(Staff) Obtiene el historial de compras global",
        responses={200: AdminHistorialDeComprasSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def admin_list(self, request):
        queryset = HistorialDeCompras.objects.select_related('usuario', 'pedido').prefetch_related('pedido__pedidolibro_set__libro').order_by('-fecha')
        return Response(AdminHistorialDeComprasSerializer(queryset, many=True).data)
    
    @extend_schema(
        description="Devolucion de una compra",
        request=IdHistorialSerializer,
        responses={200: "Devolución exitosa", 400: None}
    )
    @action(detail=False, methods=['post'])
    def devolver_compra(self, request):
        serializer = IdHistorialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        historial_id = serializer.validated_data['historial_id']

        try:
            historial = HistorialDeCompras.objects.get(id=historial_id, usuario=request.user)
            resultado = historial.devolucion_compra()
            if resultado['estado'] == 'exito':
                return Response({"mensaje": "Se ha enviado un correo electronico con un codigo qr"}, status=status.HTTP_200_OK)
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
        except HistorialDeCompras.DoesNotExist:
            return Response({"error": "Compra no encontrada"}, status=status.HTTP_404_NOT_FOUND)