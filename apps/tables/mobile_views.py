from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from datetime import datetime

from .models import Table
from .serializers import TableSerializer
from apps.menu.models import MenuItem, MenuCategory
from apps.menu.serializers import MenuItemSerializer, MenuCategorySerializer
from apps.bills.models import Bill, BillItem

class MobileOrderingViewSet(viewsets.ViewSet):
    """Mobile Ordering System for Waiters/Staff"""
    
    @action(detail=False, methods=['get'])
    def available_tables(self, request):
        """Get all available tables for ordering"""
        tables = Table.objects.filter(is_active=True)
        return Response(TableSerializer(tables, many=True).data)
    
    @action(detail=False, methods=['get'])
    def menu_for_ordering(self, request):
        """Get complete menu with categories for mobile ordering"""
        categories = MenuCategory.objects.all()
        menu_data = []
        
        for category in categories:
            items = MenuItem.objects.filter(category=category, available=True)
            menu_data.append({
                'category': MenuCategorySerializer(category).data,
                'items': MenuItemSerializer(items, many=True).data
            })
        
        return Response(menu_data)
    
    @action(detail=False, methods=['post'])
    def create_table_order(self, request):
        """Create new order for specific table"""
        table_id = request.data.get('table_id')
        items = request.data.get('items', [])  # [{'item_id': 1, 'quantity': 2}, ...]
        customer_name = request.data.get('customer_name', 'Walk-in Customer')
        
        if not table_id or not items:
            return Response(
                {'error': 'table_id and items are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            table = Table.objects.get(id=table_id)
        except Table.DoesNotExist:
            return Response(
                {'error': 'Table not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create bill for the order
        bill = Bill.objects.create(
            user=request.user,
            bill_type='restaurant',
            customer_name=f"Table {table.table_number} - {customer_name}",
            customer_phone=request.data.get('customer_phone', 'N/A'),
            total_amount=0
        )
        
        # Add items to bill
        total_amount = 0
        for item_data in items:
            try:
                menu_item = MenuItem.objects.get(id=item_data['item_id'])
                quantity = item_data['quantity']
                
                BillItem.objects.create(
                    bill=bill,
                    item_name=menu_item.name_en,  # Using English name
                    quantity=quantity,
                    price=menu_item.price
                )
                
                total_amount += menu_item.price * quantity
            except MenuItem.DoesNotExist:
                continue
        
        # Update bill total
        bill.total_amount = total_amount
        bill.save()
        
        # Mark table as occupied (if not already)
        table.status = 'occupied'
        table.save()
        
        return Response({
            'message': 'Order created successfully',
            'bill_id': bill.id,
            'receipt_number': bill.receipt_number,
            'total_amount': bill.total_amount,
            'table_number': table.table_number
        })
    
    @action(detail=False, methods=['post'])
    def add_items_to_existing_order(self, request):
        """Add more items to existing table order"""
        table_id = request.data.get('table_id')
        items = request.data.get('items', [])
        
        if not table_id or not items:
            return Response(
                {'error': 'table_id and items are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find latest bill for this table
        try:
            table = Table.objects.get(id=table_id)
            latest_bill = Bill.objects.filter(
                customer_name__contains=f"Table {table.table_number}"
            ).order_by('-created_at').first()
            
            if not latest_bill:
                return Response(
                    {'error': 'No active order found for this table'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Add new items
            additional_amount = 0
            for item_data in items:
                try:
                    menu_item = MenuItem.objects.get(id=item_data['item_id'])
                    quantity = item_data['quantity']
                    
                    BillItem.objects.create(
                        bill=latest_bill,
                        item_name=menu_item.name_en,
                        quantity=quantity,
                        price=menu_item.price
                    )
                    
                    additional_amount += menu_item.price * quantity
                except MenuItem.DoesNotExist:
                    continue
            
            # Update bill total
            latest_bill.total_amount += additional_amount
            latest_bill.save()
            
            return Response({
                'message': 'Items added successfully',
                'bill_id': latest_bill.id,
                'new_total': latest_bill.total_amount,
                'added_amount': additional_amount
            })
            
        except Table.DoesNotExist:
            return Response(
                {'error': 'Table not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def table_current_orders(self, request, pk=None):
        """Get current orders for a specific table"""
        try:
            table = Table.objects.get(id=pk)
            bills = Bill.objects.filter(
                customer_name__contains=f"Table {table.table_number}"
            ).order_by('-created_at')
            
            orders_data = []
            for bill in bills:
                items = bill.items.all()
                orders_data.append({
                    'bill_id': bill.id,
                    'receipt_number': bill.receipt_number,
                    'total_amount': bill.total_amount,
                    'created_at': bill.created_at,
                    'items': [
                        {
                            'name': item.item_name,
                            'quantity': item.quantity,
                            'price': item.price,
                            'total': item.quantity * item.price
                        }
                        for item in items
                    ]
                })
            
            return Response({
                'table_number': table.table_number,
                'table_status': getattr(table, 'status', 'available'),
                'orders': orders_data
            })
            
        except Table.DoesNotExist:
            return Response(
                {'error': 'Table not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
