# Generated by Django 5.0.7 on 2024-07-30 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("imagecolorizer", "0007_gallery"),
    ]

    operations = [
        migrations.RenameField(
            model_name="usercredits",
            old_name="credits",
            new_name="remaining_credits",
        ),
        migrations.AddField(
            model_name="usercredits",
            name="total_credits",
            field=models.IntegerField(default=10),
        ),
    ]
