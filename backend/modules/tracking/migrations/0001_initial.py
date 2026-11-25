import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('products', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Tracking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('active', 'Активен'), ('paused', 'На паузе'), ('error', 'Ошибка')], default='active', max_length=16)),
                ('check_interval', models.PositiveIntegerField(choices=[(60, 'Каждый час'), (360, 'Раз в 6 часов'), (1440, 'Раз в день')], default=60)),
                ('target_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('target_reached_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trackings', to='products.product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trackings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['status', 'product'], name='tracking_tr_status_142982_idx')],
                'constraints': [models.UniqueConstraint(fields=('user', 'product'), name='uniq_tracking_per_user'), models.CheckConstraint(condition=models.Q(('target_price__gt', 0)), name='tracking_target_positive')],
            },
        ),
    ]
