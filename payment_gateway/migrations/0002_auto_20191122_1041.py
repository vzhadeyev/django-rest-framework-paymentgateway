# Generated by Django 2.2.4 on 2019-11-22 10:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment_gateway', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='captured_total',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=11, null=True, verbose_name='captured total'),
        ),
        migrations.AlterField(
            model_name='transactionstatuschange',
            name='from_status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'PENDING'), (1, 'SUCCESS'), (2, 'DECLINED'), (3, 'INVALID_MONEY_AMOUNT'), (4, 'INVOICE_EXPIRED'), (5, 'ERROR')], verbose_name='from status'),
        ),
        migrations.AlterField(
            model_name='transactionstatuschange',
            name='to_status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'PENDING'), (1, 'SUCCESS'), (2, 'DECLINED'), (3, 'INVALID_MONEY_AMOUNT'), (4, 'INVOICE_EXPIRED'), (5, 'ERROR')], verbose_name='to status'),
        ),
    ]
