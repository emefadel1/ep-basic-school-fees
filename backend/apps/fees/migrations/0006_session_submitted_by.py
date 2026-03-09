from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('fees', '0005_alter_distribution_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='submitted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submitted_sessions', to=settings.AUTH_USER_MODEL),
        ),
    ]
