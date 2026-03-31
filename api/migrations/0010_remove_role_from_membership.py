# Generated manually on 2026-03-30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_userprofile_userrole'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='financialinstitutionmembership',
            name='role',
        ),
    ]
