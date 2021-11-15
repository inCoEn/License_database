from django.contrib import admin
from .models import Vendors, Servers, Products, Increments, Software, Departments, Users, Hosts, MainTable

admin.site.register(Vendors)
admin.site.register(Servers)
admin.site.register(Products)
admin.site.register(Increments)
admin.site.register(Software)
admin.site.register(Departments)
admin.site.register(Users)
admin.site.register(Hosts)


@admin.register(MainTable)
class MainTableAdmin(admin.ModelAdmin):
    list_display = ['start_date', 'end_date', 'increment', 'user', 'amount']
