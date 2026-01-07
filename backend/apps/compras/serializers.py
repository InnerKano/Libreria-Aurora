from rest_framework import serializers
from rest_framework.fields import URLField
from drf_spectacular.utils import extend_schema_field

from .models import Carrito, HistorialDeCompras, Pedidos, CarritoLibro, PedidoLibro, Reserva
from apps.libros.models import Libro

class CarritoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrito
        fields = '__all__'
        read_only_fields = ('fecha',)  # Debe ser una tupla con coma al final si solo hay un elemento

class AgregaroQuitarLibroSerializer(serializers.Serializer):
    libro_id = serializers.IntegerField(required=True)
    cantidad = serializers.IntegerField(required=False, default=1)
    

class PedidosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedidos
        fields = '__all__'
        read_only_fields = ('fecha',)  # Debe ser una tupla con coma al final si solo hay un elemento
        
    
class LibroSerializer(serializers.ModelSerializer):
    portada_url = serializers.SerializerMethodField()
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = Libro
        fields = '__all__'

    @extend_schema_field(URLField)
    def get_portada_url(self, obj):
        """Obtiene la URL de la portada desde Cloudinary"""
        if obj.portada:
            try:
                # CloudinaryField puede tener una URL directa
                if hasattr(obj.portada, 'url'):
                    return obj.portada.url

                from cloudinary.utils import cloudinary_url

                public_id = obj.portada.public_id if hasattr(obj.portada, 'public_id') else str(obj.portada)
                url, _ = cloudinary_url(public_id)
                return url
            except Exception:
                return None
        return None

class PedidoLibroSerializer(serializers.ModelSerializer):
    libro = LibroSerializer(read_only=True)  # Muestra el objeto libro completo

    class Meta:
        model = PedidoLibro
        fields = ['libro', 'cantidad']

class PedidosSerializer(serializers.ModelSerializer):
    pedidolibro_set = PedidoLibroSerializer(many=True, read_only=True)

    class Meta:
        model = Pedidos
        fields = ['id', 'fecha', 'usuario', 'estado', 'pedidolibro_set']
        read_only_fields = ('fecha',)

class CancelarPedidoSerializer(serializers.Serializer):
    pedido_id = serializers.IntegerField()

    def validate_pedido_id(self, value):
        try:
            Pedidos.objects.get(id=value)
        except Pedidos.DoesNotExist:
            raise serializers.ValidationError("El pedido no existe.")
        return value
    
    
# Si quieres mostrar los libros y cantidades en el carrito:
class CarritoLibroSerializer(serializers.ModelSerializer):
    libro = LibroSerializer(read_only=True)

    class Meta:
        model = CarritoLibro
        fields = ['libro', 'cantidad']
        
class ReservaSerializer(serializers.ModelSerializer):
    libro = LibroSerializer(read_only=True)

    class Meta:
        model = Reserva
        fields = ['id', 'usuario', 'libro', 'cantidad', 'estado', 'fecha_reserva', 'fecha_expiracion']
        read_only_fields = ['estado', 'fecha_reserva', 'fecha_expiracion']

class CrearReservaSerializer(serializers.Serializer):
    libro_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1)
    
class IdReservaSerializer(serializers.Serializer):
    reserva_id = serializers.IntegerField()
    
    def validate_reserva_id(self, value):
        try:
            Reserva.objects.get(id=value)
        except Reserva.DoesNotExist:
            raise serializers.ValidationError("La reserva no existe.")
        return value
    
class HistorialDeComprasSerializer(serializers.ModelSerializer):
    pedido = PedidosSerializer(read_only=True)

    class Meta:
        model = HistorialDeCompras
        fields = ['id', 'usuario', 'pedido', 'fecha']
        read_only_fields = ['id', 'usuario', 'pedido', 'fecha']
        
class CambiarEstadoPedidoSerializer(serializers.Serializer):
    pedido_id = serializers.IntegerField()
    nuevo_estado = serializers.ChoiceField(choices=Pedidos.estado_choices)

    def validate_pedido_id(self, value):
        try:
            Pedidos.objects.get(id=value)
        except Pedidos.DoesNotExist:
            raise serializers.ValidationError("El pedido no existe.")
        return value

    def validate_nuevo_estado(self, value):
        estados_validos = [estado[0] for estado in Pedidos.estado_choices]
        if value not in estados_validos:
            raise serializers.ValidationError("Estado no válido.")
        return value

class IdHistorialSerializer(serializers.Serializer):
    historial_id = serializers.IntegerField()

    def validate_historial_id(self, value):
        try:
            HistorialDeCompras.objects.get(id=value)
        except HistorialDeCompras.DoesNotExist:
            raise serializers.ValidationError("El historial de compras no existe.")
        return value