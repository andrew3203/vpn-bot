from django.contrib import admin
from vpn.models import VpnServer, Peer, Tariff, VpnOrder


@admin.register(VpnServer)
class VpnServerAdmin(admin.ModelAdmin):
    list_display = [
        'country', 'link', 'traffic'
    ]
    search_fields = ('country', 'link')
    fieldsets = (
        ('Основное', {
            'fields': (
                ("country",),
                ("link",),
                ('traffic',),
                ('public_key',),
                ('secret',),
            ),
        }),
    )


@admin.register(Peer)
class PeerAdmin(admin.ModelAdmin):
    list_display = [
        'server', 'traffic', 'created_at'
    ]
    search_fields = ('server', 'traffic')
    fieldsets = (
        ('Основное', {
            'fields': (
                ("server",),
                ("traffic",),
                ('public_key',),
                ('created_at',)
            ),
        }),
    )
    readonly_fields = ('created_at',)


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'traffic_lim', 'price', 'period', 'peers_lim'
    ]
    search_fields = ('name', 'traffic')
    fieldsets = (
        ('Основное', {
            'fields': (
                ("name",),
                ("traffic_lim", 'price'),
                ('period', 'peers_lim'),
            ),
        }),
    )

@admin.register(VpnOrder)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'tariff', 'active'
    ]
    search_fields = ('user', 'tariff')
    list_filter = ["tariff", 'active', 'refounded',]
    fieldsets = (
        ('Основное', {
            'fields': (
                ("user",),
                ("tariff",),
                ('active',),
                ('refounded',)
            ),
        }),
        ('Подключения', {
            'fields': (
                ('peers',),
            ),
        }),
    )
    filter_horizontal = ('peers',)
