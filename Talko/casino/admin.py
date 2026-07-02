from django.contrib import admin
from .models import CasinoProfile, Bet, Card, UserCard

admin.site.register(CasinoProfile)
admin.site.register(Bet)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("name", "rarity", "emoji", "sell_value")
    list_filter = ("rarity",)
    search_fields = ("name",)


@admin.register(UserCard)
class UserCardAdmin(admin.ModelAdmin):
    list_display = ("user", "card", "quantity")
    list_filter = ("card__rarity",)
    search_fields = ("user__username", "card__name")
