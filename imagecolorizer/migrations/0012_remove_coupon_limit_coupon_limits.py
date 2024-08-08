# Generated by Django 5.0.7 on 2024-08-07 12:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("imagecolorizer", "0011_coupon"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="coupon",
            name="limit",
        ),
        migrations.AddField(
            model_name="coupon",
            name="limits",
            field=models.PositiveIntegerField(default=50),
        ),
    ]
