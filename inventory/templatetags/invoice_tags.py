from django import template
from django.db.models import Sum

register = template.Library()

@register.filter
@template.defaultfilters.stringfilter
def total_payments(queryset):
    return queryset.aggregate(total=Sum('amount'))['total'] or 0
