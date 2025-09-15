# Generated migration for payment control features
# apps/staff_management/migrations/0002_add_payment_control.py

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('staff_management', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='include_payment',
            field=models.BooleanField(default=True, help_text='Whether to include payment for this day'),
        ),
        migrations.AddField(
            model_name='monthlypayment',
            name='paid_days',
            field=models.IntegerField(default=0, help_text='Days for which payment is included'),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='remarks',
            field=models.TextField(blank=True, null=True, help_text='Additional remarks for attendance'),
        ),
        migrations.AlterField(
            model_name='monthlypayment',
            name='present_days',
            field=models.IntegerField(default=0, help_text='Days employee was present'),
        ),
        migrations.AlterField(
            model_name='monthlypayment',
            name='working_days',
            field=models.IntegerField(default=30, help_text='Total working days in month'),
        ),
    ]
