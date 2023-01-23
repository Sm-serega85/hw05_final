from django.conf import settings
from django.core.paginator import Paginator


def get_page_paginator(request, queryset):
    paginator = Paginator(queryset, settings.NUNBER_POSTS)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
