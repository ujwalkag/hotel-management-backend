import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_management.settings')
django.setup()

from apps.restaurant.models import Table, Order, OrderSession, MenuItem, MenuCategory
from apps.users.models import CustomUser
from django.utils import timezone

# Test session creation manually
print("🔧 MANUAL SESSION TEST")
print("=" * 30)

# Get Table T1
try:
    table = Table.objects.get(table_number='T1')
    print(f"✅ Found Table: {table.table_number}")
except Table.DoesNotExist:
    print("❌ Table T1 not found")
    exit()

# Check existing sessions
existing = table.order_sessions.filter(is_active=True)
print(f"📋 Existing Active Sessions: {existing.count()}")

# Try to create session manually
if not existing.exists():
    print("🎫 Creating Manual Session...")
    try:
        user = CustomUser.objects.first()  # Get any user
        session = OrderSession.objects.create(
            table=table,
            created_by=user,
            is_active=True
        )
        print(f"✅ Manual Session Created: {session.id}")
    except Exception as e:
        print(f"❌ Manual Session Failed: {e}")

# Test get_session_orders
session_orders = table.get_session_orders()
print(f"📦 Session Orders: {session_orders.count()}")

for order in session_orders:
    print(f"   - {order.menu_item.name} | {order.status} | {order.created_at}")

print(f"💰 Total Bill: ₹{table.get_total_bill_amount()}")

