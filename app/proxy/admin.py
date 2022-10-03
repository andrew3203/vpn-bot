from django.contrib import admin
from proxy.models import Proxy, ProxyOrder


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'country', 'ptype', 'version', 'date_end'
    ]
    search_fields = ('version', 'ptype', 'country')
    fieldsets = (
        ('Основное', {
            'fields': (
                ('proxy',),
                ('proxy_id',),
                ("updated_at", 'created_at',)
            ),
        }),
    )
    readonly_fields = (
        'created_at', 
        'updated_at', 
        'proxy',
        'ptype','country', 'version',
        'proxy_id', 'date_end'
    )

class ProxyInline(admin.TabularInline):
    model = Proxy
    extra = 1
    fields = ['proxy_id', 'proxy', 'created_at', 'updated_at']
    readonly_fields = ['proxy_id', 'proxy', 'created_at', 'updated_at']



@admin.register(ProxyOrder)
class ProxyOrderAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'proxy_country', 'proxy_type', 'proxy_version', 'date_end'
    ]
    search_fields = ('proxy_version', 'proxy_type', 'proxy_country')
    inlines = [ProxyInline]
    fieldsets = (
        ('Основное', {
            'fields': (
                ("user",),
                ('date_end'),
                ('proxy_type','proxy_country', 'proxy_version'),
                ("updated_at", 'created_at',)
            ),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'proxy_country', 'proxy_version')