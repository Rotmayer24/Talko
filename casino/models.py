from django.db import models
from django.contrib.auth.models import User


class CasinoProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="casino_profile")
    balance = models.IntegerField(default=1000)
    total_bets = models.IntegerField(default=0)
    total_won = models.IntegerField(default=0)
    total_lost = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.balance} coins"


class Bet(models.Model):
    GAME_CHOICES = [
        ("slots", "Slots"),
        ("blackjack", "Blackjack"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="casino_bets")
    game = models.CharField(max_length=20, choices=GAME_CHOICES)
    bet_amount = models.IntegerField()
    payout = models.IntegerField()
    result_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.game} - {self.bet_amount}"
