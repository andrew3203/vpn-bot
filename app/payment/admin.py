from django.contrib import admin
from payment.models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'price', 'paid', 'created_at']
    search_fields = ('user',)
    list_filter = ["price", 'paid', 'refounded', 'canceled']
    fieldsets = (
        ('Основное', {
            'fields': (
                ("user",),
                ("price",),
                ('paid', 'canceled', 'refounded'),
                ('notes',)
            ),
        }),
        ('Важные даты', {
            'fields': (
                ("created_at"),
            ),
        })
    )
    readonly_fields = ('created_at',)
    

