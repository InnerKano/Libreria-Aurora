import os
import re
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from cloudinary.models import CloudinaryField

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.nombre

class Libro(models.Model):
    titulo = models.CharField(max_length=200)
    autor = models.CharField(max_length=200)
    isbn = models.CharField(max_length=13, unique=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    editorial = models.CharField(max_length=100, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    año_publicacion = models.IntegerField(
        validators=[MinValueValidator(1000), MaxValueValidator(2025)]
    )
    descripcion = models.TextField(blank=True)
    portada = CloudinaryField('image', blank=True, null=True, 
                              transformation={'quality': 'auto', 'fetch_format': 'auto'})
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def normalize_title_for_filename(self):
        """Normaliza el título para usar como nombre de archivo"""
        if not self.titulo:
            return "libro_sin_titulo"
        
        # Remover caracteres especiales y normalizar
        titulo_normalizado = re.sub(r'[^\w\s-]', '', self.titulo)
        titulo_normalizado = re.sub(r'[-\s]+', '_', titulo_normalizado)
        return titulo_normalizado

    def save(self, *args, **kwargs):
        # Si tenemos una nueva portada y un título, renombrar el archivo
        if self.portada and self.titulo and hasattr(self.portada, 'public_id'):
            try:
                import cloudinary.uploader as uploader
                from cloudinary.utils import cloudinary_url
                
                # Obtener el nuevo nombre basado en el título
                nuevo_nombre = self.normalize_title_for_filename()
                
                # Si el public_id actual no coincide con el título normalizado
                if self.portada.public_id != nuevo_nombre:
                    # Renombrar en Cloudinary
                    uploader.rename(self.portada.public_id, nuevo_nombre)
                    # Actualizar el campo con el nuevo public_id
                    self.portada.public_id = nuevo_nombre
            except Exception as e:
                print(f"Error al renombrar imagen en Cloudinary: {e}")
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.titulo} - {self.autor}"

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Libro'
        verbose_name_plural = 'Libros'
