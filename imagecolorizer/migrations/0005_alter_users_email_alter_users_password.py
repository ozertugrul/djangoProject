# Generated by Django 5.0.7 on 2024-07-25 12:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("imagecolorizer", "0004_alter_users_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="users",
            name="email",
            field=models.EmailField(max_length=100),
        ),
        migrations.AlterField(
            model_name="users",
            name="password",
            field=models.CharField(max_length=100),
        ),
    ]
