from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.bills.models import Bill
from apps.menu.models import MenuItem
from apps.bills.serializers import BillSerializer,BillHistorySerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class StaffPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and getattr(request.user, 'role', '') == 'staff'

class CreateRestaurantBillView(APIView):
    permission_classes = [permissions.IsAuthenticated, StaffPermission]

    def post(self, request):
        try:
            items = request.data.get("items", [])  # Expects [{id: 1, qty: 2}]
            if not items:
                return Response({"error": "No items provided"}, status=400)

            total = 0
            bill = Bill.objects.create(
                created_by=request.user,
                bill_type='restaurant',
                total_amount=0  # Will update below
            )

            for item in items:
                menu_item = MenuItem.objects.get(id=item["id"])
                quantity = item.get("qty", 1)
                total_price = menu_item.price * quantity
                BillItem.objects.create(
                    bill=bill,
                    item=menu_item,
                    quantity=quantity,
                    total_price=total_price
                )
                total += total_price

            bill.total_amount = total
            bill.save()

            return Response({"message": "Bill created", "total": total}, status=201)

        except MenuItem.DoesNotExist:
            return Response({"error": "Menu item not found"}, status=404)

        except Exception as e:
            return Response({"error": str(e)}, status=400)


class CreateRoomBillView(APIView):
    permission_classes = [permissions.IsAuthenticated, StaffPermission]

    def post(self, request):
        try:
            room_number = request.data.get("room_number")
            days = int(request.data.get("days", 1))
            price_per_day = 1500  # Ideally fetch from DB
            total = days * price_per_day

            bill = Bill.objects.create(
                created_by=request.user,
                room=Room.objects.get(number=room_number),
                total_amount=total,
                bill_type='room',
                remarks=f"Room {room_number} x {days} days"
            )

            return Response({"message": "Room bill created", "total": total}, status=201)

        except Room.DoesNotExist:
            return Response({"error": "Room not found"}, status=404)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

class BillHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        bills = Bill.objects.all().order_by("-created_at")[:20]
        serializer = BillHistorySerializer(bills, many=True)
        return Response(serializer.data, status=200)
