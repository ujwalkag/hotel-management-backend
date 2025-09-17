# apps/bills/templatetags/bill_extras.py - Template tags for D-mart style calculations
from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def div(value, arg):
    """Divide value by arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0

@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except ValueError:
        return value

@register.filter
def add_decimal(value, arg):
    """Add two decimal values"""
    try:
        return Decimal(str(value)) + Decimal(str(arg))
    except:
        return value

@register.filter
def currency(value):
    """Format value as Indian currency"""
    try:
        return f"₹{float(value):,.2f}"
    except:
        return f"₹0.00"

@register.filter
def percentage(value, total):
    """Calculate percentage of value from total"""
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except:
        return 0

@register.simple_tag
def calculate_gst(amount, rate, is_interstate=False):
    """Calculate GST breakdown"""
    try:
        amount = Decimal(str(amount))
        rate = Decimal(str(rate))

        if rate <= 0:
            return {
                'total_gst': 0,
                'cgst': 0,
                'sgst': 0,
                'igst': 0
            }

        total_gst = (amount * rate) / 100

        if is_interstate:
            return {
                'total_gst': float(total_gst),
                'cgst': 0,
                'sgst': 0,
                'igst': float(total_gst)
            }
        else:
            cgst = sgst = total_gst / 2
            return {
                'total_gst': float(total_gst),
                'cgst': float(cgst),
                'sgst': float(sgst),
                'igst': 0
            }
    except:
        return {
            'total_gst': 0,
            'cgst': 0,
            'sgst': 0,
            'igst': 0
        }

@register.inclusion_tag('bills/gst_breakdown.html')
def show_gst_breakdown(subtotal, gst_rate, is_interstate=False, discount=0):
    """Display GST breakdown in D-mart style"""
    try:
        subtotal = Decimal(str(subtotal))
        discount = Decimal(str(discount))
        taxable_amount = subtotal - discount

        gst_data = calculate_gst(taxable_amount, gst_rate, is_interstate)

        return {
            'subtotal': float(subtotal),
            'discount': float(discount),
            'taxable_amount': float(taxable_amount),
            'gst_rate': float(gst_rate),
            'is_interstate': is_interstate,
            **gst_data
        }
    except:
        return {}

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary"""
    return dictionary.get(key)

@register.filter
def format_phone(phone):
    """Format phone number for display"""
    if not phone or phone == 'N/A':
        return 'N/A'

    # Remove any non-digit characters
    digits = ''.join(filter(str.isdigit, phone))

    if len(digits) == 10:
        return f"{digits[:5]}-{digits[5:]}"
    elif len(digits) == 11 and digits[0] == '0':
        return f"{digits[:6]}-{digits[6:]}"
    else:
        return phone

@register.simple_tag
def bill_summary(items, discount_percent=0, discount_amount=0, gst_rate=0, is_interstate=False):
    """Generate complete bill summary for D-mart style receipt"""
    try:
        # Calculate subtotal
        subtotal = sum(Decimal(str(item.price)) * item.quantity for item in items)

        # Calculate discount
        percent_discount = (subtotal * Decimal(str(discount_percent))) / 100
        final_discount = max(percent_discount, Decimal(str(discount_amount)))

        # Taxable amount
        taxable_amount = subtotal - final_discount

        # GST calculation
        gst_data = calculate_gst(taxable_amount, gst_rate, is_interstate)

        # Final total
        total_amount = taxable_amount + Decimal(str(gst_data['total_gst']))

        return {
            'subtotal': float(subtotal),
            'discount': float(final_discount),
            'taxable_amount': float(taxable_amount),
            'total_amount': float(total_amount),
            'total_savings': float(final_discount),
            'item_count': len(items),
            'total_quantity': sum(item.quantity for item in items),
            **gst_data
        }
    except:
        return {}

