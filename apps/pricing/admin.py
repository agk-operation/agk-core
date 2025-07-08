from django.contrib import admin
from . import models


@admin.register(models.CustomerItemMargin)
class CustomerItemMarginAdmin(admin.ModelAdmin):
    list_display = ('customer','item','margin')
    list_filter  = ('customer',)
    search_fields= ('item__name',)