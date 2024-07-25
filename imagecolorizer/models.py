from django.db import models

class Users(models.Model):
    id = models.IntegerField(primary_key=True)
    email = models.EmailField(max_length=30)
    password = models.CharField(max_length=50)
    name = models.CharField(max_length=70)
    surname = models.CharField(max_length=70)

class UploadedImage(models.Model):
    image = models.ImageField(upload_to='uploads/')
    processed = models.BooleanField(default=False)
    result = models.TextField(blank=True, null=True)
    queue_position = models.PositiveIntegerField(null=True, blank=True)  # Sıra numarası
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    processing_time = models.FloatField(null=True, blank=True)  # İşleme süresi saniye cinsinden
