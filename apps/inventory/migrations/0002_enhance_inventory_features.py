# Generated migration for enhanced inventory features
# apps/inventory/migrations/0002_enhance_inventory_features.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        # Add new fields to InventoryEntry
        migrations.AddField(
            model_name='inventoryentry',
            name='unit_type',
            field=models.CharField(default='pieces', help_text='kg, ltr, pieces, etc.', max_length=50),
        ),
        migrations.AddField(
            model_name='inventoryentry',
            name='is_recurring',
            field=models.BooleanField(default=False, help_text='Is this a regular purchase?'),
        ),
        migrations.AddField(
            model_name='inventoryentry',
            name='priority',
            field=models.CharField(
                choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')],
                default='medium',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='inventoryentry',
            name='tags',
            field=models.CharField(blank=True, help_text='Comma-separated tags for filtering', max_length=500),
        ),

        # Create SpendingBudget model
        migrations.CreateModel(
            name='SpendingBudget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('budget_name', models.CharField(max_length=200)),
                ('budget_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('period_type', models.CharField(
                    choices=[
                        ('monthly', 'Monthly'),
                        ('quarterly', 'Quarterly'),
                        ('yearly', 'Yearly'),
                        ('custom', 'Custom Period')
                    ],
                    default='monthly',
                    max_length=20
                )),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='inventory.inventorycategory')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.customuser')),
            ],
            options={
                'db_table': 'inventory_spending_budget',
                'verbose_name': 'Spending Budget',
                'verbose_name_plural': 'Spending Budgets',
                'ordering': ['-created_at'],
            },
        ),

        # Add indexes for better performance
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_inventory_entry_purchase_date ON inventory_entry(purchase_date);",
            reverse_sql="DROP INDEX IF EXISTS idx_inventory_entry_purchase_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_inventory_entry_category_date ON inventory_entry(category_id, purchase_date);",
            reverse_sql="DROP INDEX IF EXISTS idx_inventory_entry_category_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_inventory_entry_supplier ON inventory_entry(supplier_name);",
            reverse_sql="DROP INDEX IF EXISTS idx_inventory_entry_supplier;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_inventory_entry_priority ON inventory_entry(priority);",
            reverse_sql="DROP INDEX IF EXISTS idx_inventory_entry_priority;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_inventory_entry_total_cost ON inventory_entry(total_cost);",
            reverse_sql="DROP INDEX IF EXISTS idx_inventory_entry_total_cost;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_inventory_budget_period ON inventory_spending_budget(start_date, end_date);",
            reverse_sql="DROP INDEX IF EXISTS idx_inventory_budget_period;"
        ),
    ]
