from django.db import models

class Users(models.Model):
    id = models.IntegerField(primary_key=True)
    email = models.EmailField(max_length=30)
    password = models.CharField(max_length=50)
    name = models.CharField(max_length=70)
    surname = models.CharField(max_length=70)