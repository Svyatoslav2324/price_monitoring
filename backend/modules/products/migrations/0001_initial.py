import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('marketplace', models.CharField(max_length=32)),
                ('external_id', models.CharField(max_length=64)),
                ('url', models.URLField(max_length=500)),
                ('title', models.CharField(max_length=500)),
                ('current_price', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('in_stock', models.BooleanField(default=False)),
                ('last_checked_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('marketplace', 'external_id'), name='uniq_product_per_marketplace')],
            },
        ),
        migrations.CreateModel(
            name='PricePoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('checked_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='products.product')),
            ],
            options={
                'ordering': ['checked_at'],
                'indexes': [models.Index(fields=['product', 'checked_at'], name='products_pr_product_c95ea6_idx')],
            },
        ),
    ]
