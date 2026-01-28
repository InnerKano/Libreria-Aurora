from django.db import models
from django.conf import settings
import uuid
from apps.libros.models import Libro
from apps.usuarios.models import Usuario
from apps.finanzas.models import Saldo
from datetime import timedelta, timezone
from django.utils import timezone


class CarritoLibro(models.Model):
    carrito = models.ForeignKey('Carrito', on_delete=models.CASCADE)
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('carrito', 'libro')
        
class PedidoLibro(models.Model):
    pedido = models.ForeignKey('Pedidos', on_delete=models.CASCADE)
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('pedido', 'libro')
    
class Carrito(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    libros = models.ManyToManyField(Libro, blank=True, related_name='carritos')
    fecha = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Carrito #{self.id} - {self.fecha.strftime('%Y-%m-%d')}"
    
    def agregar_libro(self, libro, cantidad):
        """Añade un libro al carrito"""
        obj, created = CarritoLibro.objects.get_or_create(carrito=self, libro=libro)
        if not created:
            obj.cantidad += cantidad
        else:
            obj.cantidad = cantidad
        obj.save()
    
    def quitar_libro(self, libro, cantidad):
        """Elimina un libro del carrito"""
        try:
            obj = CarritoLibro.objects.get(carrito=self, libro=libro)
            if obj.cantidad > cantidad and obj.cantidad - cantidad > 0:
                obj.cantidad -= cantidad
                obj.save()
            else:
                obj.delete()
        except CarritoLibro.DoesNotExist:
            pass
        
    def limpiar_carrito(self):
        """Vacía el carrito por completo"""
        self.libros.clear()
        CarritoLibro.objects.filter(carrito=self).delete()
    
    def obtener_libros(self):
        """Devuelve una lista de los libros en el carrito"""
        return CarritoLibro.objects.filter(carrito=self).all()
    
    def pagar(self):
        """Procesa el pago del carrito con los importes correctos por libro."""
        items = list(CarritoLibro.objects.filter(carrito=self).select_related('libro'))
        if not items:
            return {
                "estado": "error",
                "mensaje": "El carrito está vacío."
            }

        total = sum(item.libro.precio * item.cantidad for item in items)
        total_libros = sum(item.cantidad for item in items)

        saldo, _ = Saldo.objects.get_or_create(usuario=self.usuario, defaults={"saldo": Decimal('0')})
        if saldo.mostrar_saldo() < total:
            return {
                "estado": "error",
                "mensaje": "Saldo insuficiente para realizar la compra."
            }

        for carrito_libro in items:
            if carrito_libro.libro.stock >= carrito_libro.cantidad:
                carrito_libro.libro.stock -= carrito_libro.cantidad
                carrito_libro.libro.save()
            else:
                return {
                    "estado": "error",
                    "mensaje": f"El libro {carrito_libro.libro.titulo} no tiene suficiente stock."
                }

        pedido = Pedidos.objects.create(usuario=self.usuario, estado='Pendiente', fecha=timezone.now())
        for carrito_libro in items:
            PedidoLibro.objects.create(
                pedido=pedido,
                libro=carrito_libro.libro,
                cantidad=carrito_libro.cantidad
            )

        saldo.descontar_saldo(total)
        self.limpiar_carrito()
        return {
            "estado": "exito",
            "total": total,
            "mensaje": f"Procesando pago de ${total} para {total_libros} libros"
        }

def default_expiracion():
    return timezone.now() + timedelta(days=1)

class Reserva(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='reservas')
    estado_choices = [
        ('Completado', 'Completado'),
        ('Reservado', 'Reservado'),
        ('Cancelado', 'Cancelado'),
        ('Expirado', 'Expirado'),
    ]
    estado = models.CharField(max_length=10, choices=estado_choices, default='Reservado')
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE, related_name='reservas')
    cantidad = models.PositiveIntegerField(default=1)
    fecha_reserva = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField(default=default_expiracion) # Expira en 1 día


    def __str__(self):
        return f"Reserva de {self.libro.titulo} hasta {self.fecha_expiracion.strftime('%Y-%m-%d')}"
    
    def reservar_libro(self, libro, usuario, cantidad=1):
        """
        Reserva un libro para un usuario.
        """
        if libro.stock <= 0:
            return {
                "estado": "error",
                "mensaje": "El libro no está disponible para reserva."
            }
            
        if cantidad > libro.stock:
            return {
                "estado": "error",
                "mensaje": f"No hay suficiente stock para reservar {cantidad} copias de {libro.titulo}."
            }
        
        #Verificar si 3 libros con el mismo titulo ya fueron reservados
        reservas_existentes = Reserva.objects.filter(libro=libro, usuario=usuario, estado='Reservado')
        cantidad_total = reservas_existentes.aggregate(total=models.Sum('cantidad'))['total'] or 0
        if cantidad_total + cantidad > 3:
            return {
                "estado": "error",
                "mensaje": f"Ya tienes {cantidad_total} reservas de {libro.titulo}, no puedes reservar más de 3."
            }
        
        #Verificar si el usuario tiene mas 5 reservas activas
        reservas_activas = Reserva.objects.filter(usuario=usuario, estado='Reservado')
        cantidad_reservas_activas = reservas_activas.aggregate(total=models.Sum('cantidad'))['total'] or 0
        if cantidad_reservas_activas + cantidad > 5:
            return {
                "estado": "error",
                "mensaje": f"Ya tienes {cantidad_reservas_activas} reservas activas, no puedes reservar más de 5."
            }
            
        # Crear la reserva
        reserva = Reserva.objects.create(
            usuario=usuario,
            libro=libro,
            cantidad=cantidad,
            estado='Reservado',
            fecha_reserva=timezone.now(),
            fecha_expiracion=timezone.now() + timedelta(days=1)  # Expira en 1 día
        )
        libro.stock -= cantidad
        libro.save()
        return {
            "estado": "exito",
            "mensaje": f"Reserva creada para {cantidad} copias de {libro.titulo}.",
            "reserva": reserva
        }
    
    def cancelar_reserva(self):
        """
        Cancela una reserva.
        """
        if self.estado == 'Reservado':
            self.estado = 'Cancelado'
            self.libro.stock += self.cantidad
            self.libro.save()
            self.save()
            return {
                "estado": "exito",
                "mensaje": f"Reserva de {self.libro.titulo} cancelada."
            }
        else:
            return {
                "estado": "error",
                "mensaje": "La reserva ya ha sido cancelada o expiró."
            }
        
    def verificar_expiracion(self):
        """
        Verifica si la reserva ha expirado.
        """
        if timezone.now() > self.fecha_expiracion:
            self.estado = 'Expirado'
            self.libro.stock += self.cantidad
            self.libro.save()
            self.save()
            return {
                "estado": "exito",
                "mensaje": f"La reserva de {self.libro.titulo} ha expirado."
            }
        else:
            return {
                "estado": "error",
                "mensaje": "La reserva aún está activa."
            }
    
    def pagar_reserva(self):
        """
        Paga la reserva.
        """
        saldo = Saldo.objects.get(usuario=self.usuario)
        total = self.libro.precio * self.cantidad
        
        if saldo.mostrar_saldo() < total:
            return {
                "estado": "error",
                "mensaje": "Saldo insuficiente para realizar el pago de la reserva."
            }
        
        saldo.descontar_saldo(total)
        PedidoLibro.objects.create(
            pedido=Pedidos.objects.create(usuario=self.usuario, estado='Pendiente'),
            libro=self.libro,
            cantidad=self.cantidad
        )
        self.estado = 'Completado'
        self.save()
        
        return {
            "estado": "exito",
            "mensaje": f"Pago realizado para la reserva de {self.cantidad} copias de {self.libro.titulo}."
        }

class HistorialDeCompras(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='historial_compras')
    pedido = models.ForeignKey('Pedidos', on_delete=models.CASCADE, related_name='historial_compras')
    fecha = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Compra #{self.id} - {self.fecha.strftime('%Y-%m-%d')} - Usuario: {self.usuario.username}"
    
    #Enviar codigo qr al usuario por email para relalizar la devolucion
    def devolucion_compra(self):
        import qrcode
        from io import BytesIO
        from django.core.mail import EmailMessage
        
        if self.fecha < timezone.now() - timedelta(days=8):
            return {
                "estado": "error",
                "mensaje": "La compra no puede ser devuelta, ya que han pasado más de 8 días desde la fecha de compra."
            }

        if self.pedido.estado not in ['Entregado', 'En Devolución']:
            return {
                "estado": "error",
                "mensaje": "El pedido no está disponible para devolución."
            }

        devolucion, created = Devolucion.objects.get_or_create(
            pedido=self.pedido,
            defaults={
                'usuario': self.usuario,
                'estado': 'Solicitada'
            }
        )

        if created:
            for item in PedidoLibro.objects.filter(pedido=self.pedido).select_related('libro'):
                DevolucionItem.objects.create(
                    devolucion=devolucion,
                    libro=item.libro,
                    cantidad=item.cantidad
                )

            self.pedido.estado = 'En Devolución'
            self.pedido.save()

        return_url = f"{settings.FRONTEND_BASE_URL}/#/devolucion/{devolucion.token}"

        qr_data = return_url
        qr = qrcode.make(qr_data)
        img_io = BytesIO()
        qr.save(img_io, format='PNG')
        img_io.seek(0)

        # Envía el correo con el QR adjunto (sin guardarlo en el modelo)
        subject = f"Enlace de devolución para compra #{self.id}"
        message = (
            f"Hola {self.usuario.username},\n\n"
            f"Adjuntamos el código QR y el enlace para la devolución de tu compra #{self.id}.\n"
            "Recuerda que solo puedes devolver la compra dentro de los 8 días posteriores a la compra.\n\n"
            f"Enlace directo: {return_url}\n\n"
            "Saludos,\nLibrería Aurora"
        )
        email = EmailMessage(
            subject,
            message,
            to=[self.usuario.email]
        )
        email.attach(f"qr_devolucion_{self.id}.png", img_io.read(), "image/png")
        email.send()

        return {
            "estado": "exito",
            "mensaje": f"Enlace de devolución generado y enviado para la compra #{self.id}.",
            "return_url": return_url,
            "token": str(devolucion.token)
        }
        
    def MostrarHistorialCompras(self):
        """
        Muestra el historial de compras del usuario.
        """
        return HistorialDeCompras.objects.filter(usuario=self.usuario).all()

class Pedidos(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    libros = models.ManyToManyField(Libro, blank=True, related_name='pedidos')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='pedidos')
    estado_choices = [
        ('Pendiente', 'Pendiente'),
        ('Cancelado', 'Cancelado'),
        ('En Proceso', 'En Proceso'),
        ('Entregado', 'Entregado'),
        ('En Devolución', 'En Devolución'),
        ('Devuelto', 'Devuelto'),
    ]
    estado = models.CharField(max_length=20, choices=estado_choices, default='Pendiente')
    def save(self, *args, **kwargs):
        if not self.pk and not self.fecha:  
            self.fecha = timezone.now()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Pedido #{self.id} - {self.fecha.strftime('%Y-%m-%d')}" 
    
    def crear_pedido(self, usuario, libros, cantidad):
        """
        Crea un nuevo pedido.
        """
        self.usuario = usuario
        self.libros.set(libros)
        self.save()
        
        for libro in libros:
            PedidoLibro.objects.create(pedido=self, libro=libro, cantidad=cantidad)
        
        return self
    
    def MostrarPedidos(self):
        return PedidoLibro.objects.filter(pedido=self).all()
    
    def cancelar_pedido(self):
        """
        Cancela un pedido.
        """
        if self.estado != 'Pendiente':
            return {
                "estado": "error",
                "mensaje": "El pedido ya ha sido completado o cancelado."
            }

        resultado = self._aplicar_cancelacion()
        if resultado["estado"] == "exito":
            return {
                "estado": "exito",
                "mensaje": f"Pedido #{self.id} cancelado."
            }
        return resultado
    
    def cambiar_estado(self, nuevo_estado):
        """
        Cambia el estado del pedido.
        """
        if nuevo_estado in dict(self.estado_choices):
            if nuevo_estado == 'Cancelado':
                if self.estado == 'Cancelado':
                    return {
                        "estado": "error",
                        "mensaje": "El pedido ya está cancelado."
                    }
                return self._aplicar_cancelacion()
            self.estado = nuevo_estado
            if nuevo_estado == 'Entregado':
                # Si el pedido es entregado, se registra en el historial de compras
                HistorialDeCompras.objects.get_or_create(usuario=self.usuario, pedido=self)
            self.save()
            
            return {
                "estado": "exito",
                "mensaje": f"Estado del pedido #{self.id} cambiado a {nuevo_estado}."
            }
        else:
            return {
                "estado": "error",
                "mensaje": "Estado no válido."
            }

    def _aplicar_cancelacion(self):
        """
        Aplica la cancelación: devuelve saldo, repone stock y registra historial.
        """
        from decimal import Decimal
        from apps.finanzas.models import HistorialSaldo
        items = PedidoLibro.objects.filter(pedido=self).select_related('libro')
        if not items.exists():
            return {
                "estado": "error",
                "mensaje": "No hay libros asociados al pedido."
            }

        total = Decimal('0')
        for item in items:
            total += item.libro.precio * item.cantidad
            item.libro.stock += item.cantidad
            item.libro.save()

        saldo = Saldo.objects.get(usuario=self.usuario)
        saldo.saldo += total
        saldo.save()
        HistorialSaldo.objects.create(
            usuario=self.usuario,
            tipo_transaccion='AJUSTE',
            monto=total,
            saldo_resultante=saldo.saldo,
            descripcion=f"Reembolso por cancelación del pedido #{self.id}",
        )

        self.estado = 'Cancelado'
        self.save()

        HistorialDeCompras.objects.get_or_create(usuario=self.usuario, pedido=self)

        return {
            "estado": "exito",
            "mensaje": f"Pedido #{self.id} cancelado y reembolsado.",
            "total_reembolsado": str(total)
        }


class Devolucion(models.Model):
    estado_choices = [
        ('Solicitada', 'Solicitada'),
        ('En Proceso', 'En Proceso'),
        ('Devuelta', 'Devuelta'),
        ('Rechazada', 'Rechazada'),
    ]

    pedido = models.OneToOneField(Pedidos, on_delete=models.CASCADE, related_name='devolucion')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='devoluciones')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    estado = models.CharField(max_length=20, choices=estado_choices, default='Solicitada')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    motivo = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Devolución #{self.id} - Pedido #{self.pedido.id}"


class DevolucionItem(models.Model):
    devolucion = models.ForeignKey(Devolucion, on_delete=models.CASCADE, related_name='items')
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('devolucion', 'libro')


class PedidoEstadoOverride(models.Model):
    pedido = models.ForeignKey(Pedidos, on_delete=models.CASCADE, related_name='overrides')
    staff = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='pedido_overrides')
    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    motivo = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Override pedido #{self.pedido.id} ({self.estado_anterior} -> {self.estado_nuevo})"