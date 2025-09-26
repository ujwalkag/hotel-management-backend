from django.core.management.base import BaseCommand
from apps.restaurant.models import Table, Order, OrderSession
from django.utils import timezone

class Command(BaseCommand):
    help = 'Debug billing issues'

    def handle(self, *args, **options):
        print("🔍 HARDCORE BILLING DEBUG")
        print("=" * 50)
        
        # Check all tables
        tables = Table.objects.filter(is_active=True)
        print(f"📋 Active Tables: {tables.count()}")
        
        for table in tables:
            print(f"\n🏓 TABLE {table.table_number}:")
            print(f"   Status: {table.status}")
            print(f"   Last occupied: {table.last_occupied_at}")
            
            # Check all orders for this table
            all_orders = table.orders.all()
            print(f"   📦 Total Orders: {all_orders.count()}")
            
            if all_orders.exists():
                for order in all_orders:
                    print(f"      - {order.menu_item.name} | {order.status} | {order.created_at}")
            
            # Check sessions
            all_sessions = table.order_sessions.all()
            active_sessions = table.order_sessions.filter(is_active=True)
            print(f"   🎫 Total Sessions: {all_sessions.count()}")
            print(f"   ✅ Active Sessions: {active_sessions.count()}")
            
            if active_sessions.exists():
                for session in active_sessions:
                    print(f"      - Session ID: {session.id}")
                    print(f"      - Created: {session.created_at}")
                    print(f"      - Active: {session.is_active}")
            
            # Test get_session_orders
            session_orders = table.get_session_orders()
            print(f"   🔄 get_session_orders(): {session_orders.count()}")
            
            if session_orders.exists():
                for order in session_orders:
                    print(f"      - SESSION ORDER: {order.menu_item.name} | {order.status}")
            
            # Test get_total_bill_amount
            total = table.get_total_bill_amount()
            print(f"   💰 Total Bill Amount: ₹{total}")
            
            print("-" * 30)

        # Check order creation logic
        print("\n🔧 ORDER CREATION TEST")
        print("=" * 30)
        
        # Find orders created today
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        todays_orders = Order.objects.filter(created_at__gte=today)
        print(f"📅 Today's Orders: {todays_orders.count()}")
        
        for order in todays_orders:
            print(f"   - {order.menu_item.name} | Table: {order.table.table_number} | {order.created_at}")
            
        # Check if sessions were created for today's orders
        todays_sessions = OrderSession.objects.filter(created_at__gte=today)
        print(f"🎫 Today's Sessions: {todays_sessions.count()}")
        
        for session in todays_sessions:
            print(f"   - Table: {session.table.table_number} | Active: {session.is_active} | {session.created_at}")

