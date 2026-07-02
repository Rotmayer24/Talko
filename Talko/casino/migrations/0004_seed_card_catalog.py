from django.db import migrations


# (name, rarity, emoji, description)
CARD_CATALOG = [
    # common
    ("Lucky Cherry", "common", "🍒", "A sweet little token of beginner's luck."),
    ("Ace of Spades", "common", "♠️", "The classic card every player knows."),
    ("Loaded Die", "common", "🎲", "Rolls your way... sometimes."),
    ("Copper Coin", "common", "🪙", "Pocket change of the casino floor."),
    # rare
    ("Golden Bell", "rare", "🔔", "Ring it three times for fortune."),
    ("Wild Joker", "rare", "🃏", "Wild by nature, unpredictable by trade."),
    ("Cash Stack", "rare", "💵", "A tidy little bankroll."),
    # epic
    ("Brilliant Diamond", "epic", "💎", "Flawless, dazzling, and rare to find."),
    ("High Roller Crown", "epic", "👑", "Worn only by those who bet big."),
    ("Jackpot Machine", "epic", "🎰", "Three reels of pure adrenaline."),
    # legendary
    ("Dragon's Hoard", "legendary", "🐉", "A treasure guarded for a thousand years."),
    ("Star of Fortune", "legendary", "🌟", "Said to grant the bearer impossible luck."),
    ("Phoenix Chip", "legendary", "🔥", "Rises again no matter how often you lose."),
    # mythic
    ("Talko Trident", "mythic", "🔱", "The crown jewel of the Talko collection."),
    ("Infinity Chip", "mythic", "♾️", "An endless wager that never runs dry."),
]


def seed_cards(apps, schema_editor):
    Card = apps.get_model("casino", "Card")
    for name, rarity, emoji, description in CARD_CATALOG:
        Card.objects.get_or_create(
            name=name,
            defaults={"rarity": rarity, "emoji": emoji, "description": description},
        )


def unseed_cards(apps, schema_editor):
    Card = apps.get_model("casino", "Card")
    Card.objects.filter(name__in=[c[0] for c in CARD_CATALOG]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("casino", "0003_card_usercard"),
    ]

    operations = [
        migrations.RunPython(seed_cards, unseed_cards),
    ]
