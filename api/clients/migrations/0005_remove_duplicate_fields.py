# Generated migration to remove duplicate fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0004_make_user_required'),
    ]

    operations = [
        # Eliminar campos duplicados que ahora están en auth_user y user_profiles
        migrations.RemoveField(
            model_name='client',
            name='email',
        ),
        migrations.RemoveField(
            model_name='client',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='client',
            name='last_name',
        ),
        migrations.RemoveField(
            model_name='client',
            name='phone',
        ),
    ]
