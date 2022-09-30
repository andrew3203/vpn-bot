from django.contrib import admin
from proxy.models import Proxy


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'country', 'ptype', 'version', 'date_end'
    ]
    search_fields = ('version', 'ptype', 'country')
    fieldsets = (
        ('Основное', {
            'fields': (
                ("user",),
                ('proxy',),
                ('proxy_id', 'date_end'),
                ('ptype','country', 'version'),
                ("updated_at",),
                ('created_at',)
            ),
        }),
    )
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'proxy', 'user',
        'ptype','country', 'version',
        'proxy_id', 'date_end'
    )
