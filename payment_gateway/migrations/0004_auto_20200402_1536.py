# Generated by Django 3.0.2 on 2020-04-02 09:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment_gateway', '0003_auto_20200210_1233'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cloudpaymentstransaction',
            name='CardType',
            field=models.CharField(max_length=32),
        ),
    ]