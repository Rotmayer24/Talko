from django.urls import path
from . import views

app_name = "casino"

urlpatterns = [
    path("", views.casino_home, name="home"),
    path("slots/", views.slots, name="slots"),
    path("slots/spin/", views.slots_spin, name="slots_spin"),
    path("blackjack/", views.blackjack, name="blackjack"),
    path("blackjack/hit/", views.blackjack_hit, name="blackjack_hit"),
    path("blackjack/stand/", views.blackjack_stand, name="blackjack_stand"),
    path("blackjack/deal/", views.blackjack_deal, name="blackjack_deal"),
    path("shop/", views.shop, name="shop"),
    path("shop/buy/", views.buy_coins, name="buy_coins"),
]
