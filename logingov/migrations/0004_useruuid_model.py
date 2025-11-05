from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('logingov', '0003_logingovspsettings_token_expire'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserUUID',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(help_text='The UUID provided by Login.gov for this user', unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(help_text='The Django User object linked to this UUID', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User UUID',
                'verbose_name_plural': 'User UUIDs',
            },
        ),
    ]
