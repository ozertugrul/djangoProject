from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import base64

class Users(models.Model):
    id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=100)
    password = models.CharField(max_length=100)
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
    image_hash = models.CharField(max_length=64, blank=True, null=True)

        
class ProcessedImage(models.Model):
    image = models.ImageField(upload_to='processed_images/')
    result = models.TextField(blank=True, null=True)
    image_hash = models.CharField(max_length=64, unique=True)  # Hash'ler benzersiz olmalı

@receiver(post_save, sender=UploadedImage)
def create_or_update_processed_image(sender, instance, created, **kwargs):
    # Her UploadedImage kaydedildiğinde çalışacak
    processed_image, _ = ProcessedImage.objects.get_or_create(
        image_hash=instance.image_hash
    )
    processed_image.image = instance.image
    if instance.result:
        processed_image.result = instance.result
    processed_image.save()
 
class UserCredits(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_credits = models.IntegerField(default=10)
    remaining_credits = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.user.email} - Kalan Kredi: {self.remaining_credits}"

@receiver(post_save, sender=User)
def create_user_credits(sender, instance, created, **kwargs):
    if created:
        UserCredits.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_credits(sender, instance, **kwargs):
    instance.usercredits.save()

class Gallery(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    image_score = models.FloatField(null=True, blank=True)

    
    class Meta:
        unique_together = ('user', 'image_url')
        


class Coupon(models.Model):
    code = models.CharField(max_length=255, unique=True)  # Coupon code
    credits = models.PositiveIntegerField() 
    limits = models.PositiveIntegerField(default=50)  
    used_count = models.PositiveIntegerField(default=0)  

    def __str__(self):
        return self.code

    def is_valid(self):
        return self.limits > self.used_count

class CouponUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    used_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'coupon')

    def __str__(self):
        return f"{self.user.username} - {self.coupon.code}"