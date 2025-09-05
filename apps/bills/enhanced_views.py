from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from datetime import datetime, date

from .models import Bill, BillItem
from .serializers import BillSerializer
from apps.tables.models import Table
from apps.menu.models import MenuItem

class EnhancedBillingViewSet(viewsets.ModelViewSet):
    """Enhanced Billing System with GST and Dynamic Updates"""
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def active_tables_dashboard(self, request):
        """Get all tables with active orders for enhanced billing"""
        # Get tables with orders from your existing table system
        active_tables = Table.objects.filter(
            status='occupied'  # Based on your existing table model
        ).order_by('table_number')
        
        dashboard_data = []
        
        for table in active_tables:
            # Get any existing bills for this table
            table_bills = Bill.objects.filter(
                # Assuming you have table reference in Bill model
                customer_name__contains=f"Table {table.table_number}"
            )
            
            total_amount = sum(bill.total_amount for bill in table_bills)
            
            dashboard_data.append({
                'table_id': table.id,
                'table_number': table.table_number,
                'table_capacity': getattr(table, 'capacity', 4),
                'bills_count': table_bills.count(),
                'total_amount': total_amount,
                'can_generate_bill': table.status == 'occupied'
            })
        
        return Response({
            'active_tables': dashboard_data,
            'total_tables': len(dashboard_data),
            'total_revenue_pending': sum(table['total_amount'] for table in dashboard_data)
        })

    @action(detail=True, methods=['post'])
    def add_custom_item(self, request, pk=None):
        """Add custom item to bill - Admin can add/edit items"""
        bill = self.get_object()
        
        item_name = request.data.get('item_name')
        quantity = request.data.get('quantity', 1)
        price = request.data.get('price')
        
        if not item_name or not price:
            return Response(
                {'error': 'item_name and price are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new bill item
        BillItem.objects.create(
            bill=bill,
            item_name=item_name,
            quantity=quantity,
            price=Decimal(str(price))
        )
        
        # Recalculate bill total
        self._recalculate_bill_total(bill)
        
        return Response(BillSerializer(bill).data)

    @action(detail=True, methods=['patch'])
    def apply_gst(self, request, pk=None):
        """Apply GST to bill"""
        bill = self.get_object()
        
        apply_gst = request.data.get('apply_gst', True)
        interstate = request.data.get('interstate', False)
        
        if apply_gst:
            subtotal = bill.total_amount
            
            if interstate:
                # IGST 18%
                igst_amount = subtotal * Decimal('0.18')
                gst_total = igst_amount
            else:
                # CGST + SGST 9% each
                cgst_amount = subtotal * Decimal('0.09')
                sgst_amount = subtotal * Decimal('0.09')
                gst_total = cgst_amount + sgst_amount
            
            bill.total_amount = subtotal + gst_total
            bill.save()
            
            return Response({
                'bill': BillSerializer(bill).data,
                'gst_details': {
                    'subtotal': subtotal,
                    'gst_amount': gst_total,
                    'total_with_gst': bill.total_amount,
                    'interstate': interstate
                }
            })
        
        return Response(BillSerializer(bill).data)

    @action(detail=True, methods=['delete'])
    def delete_item(self, request, pk=None):
        """Delete item from bill - Admin functionality"""
        bill = self.get_object()
        item_id = request.data.get('item_id')
        
        if not item_id:
            return Response(
                {'error': 'item_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            item = BillItem.objects.get(id=item_id, bill=bill)
            item.delete()
            
            # Recalculate bill total
            self._recalculate_bill_total(bill)
            
            return Response({'message': 'Item deleted successfully'})
        except BillItem.DoesNotExist:
            return Response(
                {'error': 'Item not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def generate_final_bill(self, request, pk=None):
        """Generate final bill and mark table as available"""
        bill = self.get_object()
        
        # Mark bill as finalized
        bill.created_at = datetime.now()
        bill.save()
        
        # If you have table reference, mark it as available
        # This would depend on your table model structure
        
        return Response({
            'bill': BillSerializer(bill).data,
            'message': 'Bill generated successfully'
        })

    def _recalculate_bill_total(self, bill):
        """Recalculate bill total amount"""
        total = sum(item.quantity * item.price for item in bill.items.all())
        bill.total_amount = total
        bill.save()
