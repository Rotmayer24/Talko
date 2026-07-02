from django.db import models
from django.contrib.auth.models import User


# Card rarities — single source of truth for drop weights, sell value and color.
# Ordered low → high; higher index = rarer.
RARITY_META = {
    "common":    {"label": "Common",    "weight": 60,  "value": 40,    "color": "#9aa5b8"},
    "rare":      {"label": "Rare",      "weight": 25,  "value": 150,   "color": "#7aa2f7"},
    "epic":      {"label": "Epic",      "weight": 11,  "value": 500,   "color": "#bb9af7"},
    "legendary": {"label": "Legendary", "weight": 3.5, "value": 2000,  "color": "#ff9e64"},
    "mythic":    {"label": "Mythic",    "weight": 0.5, "value": 10000, "color": "#f7768e"},
}
RARITY_ORDER = list(RARITY_META)  # low → high


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


class Card(models.Model):
    """A collectible card template (the catalog). Seeded once via migration."""
    RARITY_CHOICES = [(key, meta["label"]) for key, meta in RARITY_META.items()]

    name = models.CharField(max_length=80, unique=True)
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default="common")
    emoji = models.CharField(max_length=8, default="🎴")
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["rarity", "name"]

    def __str__(self):
        return f"{self.name} ({self.rarity})"

    @property
    def sell_value(self):
        return RARITY_META[self.rarity]["value"]

    @property
    def rarity_label(self):
        return RARITY_META[self.rarity]["label"]

    @property
    def rarity_color(self):
        return RARITY_META[self.rarity]["color"]

    @property
    def rarity_rank(self):
        return RARITY_ORDER.index(self.rarity)


class UserCard(models.Model):
    """How many copies of a given card a user owns."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cards")
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="owners")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("user", "card")

    def __str__(self):
        return f"{self.user.username} ×{self.quantity} {self.card.name}"
