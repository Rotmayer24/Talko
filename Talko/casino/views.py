import json
import random
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from .models import CasinoProfile, Bet, Card, UserCard, RARITY_META, RARITY_ORDER


# ─── Collectible cards ──────────────────────────────────────

# Chance to win a card each time a game resolves.
CARD_DROP_CHANCE = 0.15


def maybe_drop_card(user):
    """Roll for a card drop. On success, grant a rarity-weighted random card
    and return its display info; otherwise return None."""
    if random.random() > CARD_DROP_CHANCE:
        return None

    rarity = random.choices(
        RARITY_ORDER,
        weights=[RARITY_META[r]["weight"] for r in RARITY_ORDER],
    )[0]

    cards = list(Card.objects.filter(rarity=rarity))
    if not cards:
        return None
    card = random.choice(cards)

    user_card, created = UserCard.objects.get_or_create(user=user, card=card)
    if not created:
        UserCard.objects.filter(pk=user_card.pk).update(quantity=F("quantity") + 1)

    return {
        "name": card.name,
        "emoji": card.emoji,
        "rarity": card.rarity,
        "label": card.rarity_label,
        "color": card.rarity_color,
        "value": card.sell_value,
    }



def get_or_create_profile(user):
    profile, created = CasinoProfile.objects.get_or_create(user=user)
    return profile


@login_required
def casino_home(request):
    profile = get_or_create_profile(request.user)
    recent_bets = Bet.objects.filter(user=request.user)[:10]
    return render(request, "casino/casino.html", {
        "profile": profile,
        "recent_bets": recent_bets,
    })


# ─── Slot Machine ───────────────────────────────────────────

SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎", "7️⃣"]

SLOT_PAYOUTS = {
    ("🍒", "🍒", "🍒"): 5,
    ("🍋", "🍋", "🍋"): 8,
    ("🍊", "🍊", "🍊"): 10,
    ("🍇", "🍇", "🍇"): 15,
    ("🔔", "🔔", "🔔"): 20,
    ("💎", "💎", "💎"): 30,
    ("7️⃣", "7️⃣", "7️⃣"): 50,
}

# Two matching symbols (partial wins)
PARTIAL_PAYOUTS = {
    "🍒": 2,
    "🍋": 3,
    "🍊": 4,
    "🍇": 5,
    "🔔": 6,
    "💎": 8,
    "7️⃣": 10,
}


def slot_spin_reels():
    return [random.choice(SLOT_SYMBOLS) for _ in range(3)]


def slot_check_result(reels):
    key = tuple(reels)
    if key in SLOT_PAYOUTS:
        return {"win": True, "multiplier": SLOT_PAYOUTS[key], "match": "three"}
    if reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        sym = reels[0] if reels[0] == reels[1] else reels[2]
        return {"win": True, "multiplier": PARTIAL_PAYOUTS[sym], "match": "two"}
    return {"win": False, "multiplier": 0, "match": "none"}


@login_required
def slots(request):
    profile = get_or_create_profile(request.user)
    return render(request, "casino/slots.html", {
        "profile": profile,
    })


@login_required
@require_POST
def slots_spin(request):
    get_or_create_profile(request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        bet_amount = int(data.get("bet_amount", 0))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid bet amount"}, status=400)

    reels = slot_spin_reels()
    result = slot_check_result(reels)

    with transaction.atomic():
        profile = CasinoProfile.objects.select_for_update().get(user=request.user)

        if bet_amount <= 0 or bet_amount > profile.balance:
            return JsonResponse({"error": "Invalid bet amount"}, status=400)

        if result["win"]:
            payout = bet_amount * result["multiplier"]
            profile.balance += payout
            profile.total_won += payout
        else:
            payout = -bet_amount
            profile.balance -= bet_amount
            profile.total_lost += bet_amount

        profile.total_bets += 1
        profile.save()

        Bet.objects.create(
            user=request.user,
            game="slots",
            bet_amount=bet_amount,
            payout=payout,
            result_data={"reels": reels, "match": result["match"]},
        )

    card_drop = maybe_drop_card(request.user)

    return JsonResponse({
        "reels": reels,
        "win": result["win"],
        "match": result["match"],
        "multiplier": result["multiplier"],
        "payout": payout,
        "balance": profile.balance,
        "card_drop": card_drop,
    })


# ─── Blackjack ──────────────────────────────────────────────

DECK = []
for suit in ["♠", "♥", "♦", "♣"]:
    for rank in ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]:
        DECK.append(f"{rank}{suit}")


def card_value(card):
    rank = card[:-1]
    if rank in ("J", "Q", "K"):
        return 10
    elif rank == "A":
        return 11
    return int(rank)


def hand_value(hand):
    total = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[:-1] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def card_display(card):
    rank = card[:-1]
    suit = card[-1]
    color = "red" if suit in ("♥", "♦") else "black"
    return {"card": card, "rank": rank, "suit": suit, "color": color}


def deal_cards():
    deck = DECK.copy()
    random.shuffle(deck)
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]
    return deck, player, dealer


@login_required
def blackjack(request):
    profile = get_or_create_profile(request.user)
    return render(request, "casino/blackjack.html", {
        "profile": profile,
    })


@login_required
@require_POST
def blackjack_deal(request):
    get_or_create_profile(request.user)

    # Refuse to start a new hand while one is already in progress.
    if request.session.get("blackjack"):
        return JsonResponse({"error": "Finish the current hand first"}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        bet_amount = int(data.get("bet_amount", 0))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid bet amount"}, status=400)

    deck, player, dealer = deal_cards()
    pv = hand_value(player)
    dv = hand_value(dealer)
    game_over = False
    result = None
    payout = 0

    with transaction.atomic():
        profile = CasinoProfile.objects.select_for_update().get(user=request.user)

        if bet_amount <= 0 or bet_amount > profile.balance:
            return JsonResponse({"error": "Invalid bet amount"}, status=400)

        if pv == 21 and dv == 21:
            game_over = True
            result = "push"
            payout = 0
        elif pv == 21:
            game_over = True
            result = "blackjack"
            payout = int(bet_amount * 1.5)
            profile.balance += payout
            profile.total_won += payout
        elif dv == 21:
            game_over = True
            result = "dealer_blackjack"
            payout = -bet_amount
            profile.balance -= bet_amount
            profile.total_lost += bet_amount

        if game_over:
            profile.total_bets += 1
            profile.save()
            Bet.objects.create(
                user=request.user,
                game="blackjack",
                bet_amount=bet_amount,
                payout=payout,
                result_data={"result": result, "player": player, "dealer": dealer},
            )

    # Only persist a playable session when the hand is still open.
    # Otherwise hit/stand could replay it and pay out again.
    if not game_over:
        request.session["blackjack"] = {
            "deck": deck,
            "player": player,
            "dealer": dealer,
            "bet": bet_amount,
            "standing": False,
        }

    # A natural blackjack/dealer blackjack ends the hand on the deal.
    card_drop = maybe_drop_card(request.user) if game_over else None

    return JsonResponse({
        "player": [card_display(c) for c in player],
        "dealer": [card_display(dealer[0])] + [{"card": "🂠", "rank": "?", "suit": "", "color": "black"}],
        "player_value": hand_value(player),
        "dealer_value": hand_value(dealer[:1]),
        "game_over": game_over,
        "result": result,
        "payout": payout,
        "balance": profile.balance,
        "card_drop": card_drop,
    })


@login_required
@require_POST
def blackjack_hit(request):
    get_or_create_profile(request.user)
    session = request.session.get("blackjack")
    if not session:
        return JsonResponse({"error": "No active game"}, status=400)

    deck = session["deck"]
    player = session["player"]
    dealer = session["dealer"]
    bet = session["bet"]

    card = deck.pop()
    player.append(card)
    pv = hand_value(player)
    game_over = False
    result = None
    payout = 0

    if pv > 21:
        game_over = True
        result = "bust"
        payout = -bet
        with transaction.atomic():
            profile = CasinoProfile.objects.select_for_update().get(user=request.user)
            profile.balance -= bet
            profile.total_lost += bet
            profile.total_bets += 1
            profile.save()
            Bet.objects.create(
                user=request.user,
                game="blackjack",
                bet_amount=bet,
                payout=payout,
                result_data={"result": result, "player": player, "dealer": dealer},
            )
        balance = profile.balance
        del request.session["blackjack"]
    else:
        session["deck"] = deck
        session["player"] = player
        request.session["blackjack"] = session
        balance = CasinoProfile.objects.get(user=request.user).balance

    card_drop = maybe_drop_card(request.user) if game_over else None

    return JsonResponse({
        "card": card_display(card),
        "player": [card_display(c) for c in player],
        "player_value": pv,
        "game_over": game_over,
        "result": result,
        "payout": payout,
        "balance": balance,
        "card_drop": card_drop,
    })


@login_required
@require_POST
def blackjack_stand(request):
    get_or_create_profile(request.user)
    session = request.session.get("blackjack")
    if not session:
        return JsonResponse({"error": "No active game"}, status=400)

    deck = session["deck"]
    player = session["player"]
    dealer = session["dealer"]
    bet = session["bet"]

    while hand_value(dealer) < 17:
        dealer.append(deck.pop())

    pv = hand_value(player)
    dv = hand_value(dealer)
    game_over = True
    result = None
    payout = 0

    with transaction.atomic():
        profile = CasinoProfile.objects.select_for_update().get(user=request.user)

        if dv > 21:
            result = "dealer_bust"
            payout = bet
            profile.balance += bet
            profile.total_won += bet
        elif dv > pv:
            result = "dealer_wins"
            payout = -bet
            profile.balance -= bet
            profile.total_lost += bet
        elif dv < pv:
            result = "player_wins"
            payout = bet
            profile.balance += bet
            profile.total_won += bet
        else:
            result = "push"
            payout = 0

        profile.total_bets += 1
        profile.save()
        Bet.objects.create(
            user=request.user,
            game="blackjack",
            bet_amount=bet,
            payout=payout,
            result_data={"result": result, "player": player, "dealer": dealer},
        )

    del request.session["blackjack"]

    card_drop = maybe_drop_card(request.user)

    return JsonResponse({
        "dealer": [card_display(c) for c in dealer],
        "player": [card_display(c) for c in player],
        "player_value": pv,
        "dealer_value": dv,
        "game_over": game_over,
        "result": result,
        "payout": payout,
        "balance": profile.balance,
        "card_drop": card_drop,
    })


# ─── Casino Shop ────────────────────────────────────────────

SHOP_ITEMS = [
    {"id": "coins_100", "name": "100 Coins", "cost": 1.00, "coins": 100, "emoji": "🪙"},
    {"id": "coins_500", "name": "500 Coins", "cost": 4.00, "coins": 500, "emoji": "🪙"},
    {"id": "coins_1000", "name": "1000 Coins", "cost": 7.00, "coins": 1000, "emoji": "🪙"},
    {"id": "coins_5000", "name": "5000 Coins", "cost": 30.00, "coins": 5000, "emoji": "🪙"},
]

@login_required
def shop(request):
    profile = get_or_create_profile(request.user)
    return render(request, "casino/shop.html", {
        "profile": profile,
        "shop_items": SHOP_ITEMS,
    })


@login_required
@require_POST
def buy_coins(request):
    profile = get_or_create_profile(request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    item_id = data.get("item_id")
    for item in SHOP_ITEMS:
        if item["id"] == item_id:
            with transaction.atomic():
                profile = CasinoProfile.objects.select_for_update().get(user=request.user)
                profile.balance += item["coins"]
                profile.save()
            return JsonResponse({
                "success": True,
                "coins_added": item["coins"],
                "balance": profile.balance,
                "message": f"Purchased {item['name']}!",
            })

    return JsonResponse({"error": "Invalid item"}, status=400)


# ─── Card Collection ────────────────────────────────────────

@login_required
def cards(request):
    profile = get_or_create_profile(request.user)

    owned = {
        uc.card_id: uc.quantity
        for uc in UserCard.objects.filter(user=request.user)
    }

    # Full catalog, rarest first; owned copies are highlighted, the rest locked.
    catalog = []
    owned_count = 0
    collection_value = 0
    for card in Card.objects.all():
        qty = owned.get(card.id, 0)
        if qty:
            owned_count += 1
            collection_value += card.sell_value * qty
        catalog.append({
            "id": card.id,
            "name": card.name,
            "emoji": card.emoji,
            "description": card.description,
            "rarity": card.rarity,
            "label": card.rarity_label,
            "color": card.rarity_color,
            "rank": card.rarity_rank,
            "value": card.sell_value,
            "quantity": qty,
        })

    catalog.sort(key=lambda c: (-c["rank"], c["name"]))

    return render(request, "casino/cards.html", {
        "profile": profile,
        "catalog": catalog,
        "owned_count": owned_count,
        "total_count": len(catalog),
        "collection_value": collection_value,
    })


@login_required
@require_POST
def sell_card(request):
    get_or_create_profile(request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        card_id = int(data.get("card_id"))
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid request"}, status=400)

    if quantity < 1:
        return JsonResponse({"error": "Invalid quantity"}, status=400)

    with transaction.atomic():
        try:
            user_card = (
                UserCard.objects
                .select_for_update()
                .select_related("card")
                .get(user=request.user, card_id=card_id)
            )
        except UserCard.DoesNotExist:
            return JsonResponse({"error": "You don't own this card"}, status=400)

        if quantity > user_card.quantity:
            return JsonResponse({"error": "Not enough copies"}, status=400)

        earned = user_card.card.sell_value * quantity
        remaining = user_card.quantity - quantity
        if remaining:
            user_card.quantity = remaining
            user_card.save()
        else:
            user_card.delete()

        profile = CasinoProfile.objects.select_for_update().get(user=request.user)
        profile.balance += earned
        profile.save()

    return JsonResponse({
        "success": True,
        "earned": earned,
        "remaining": remaining,
        "balance": profile.balance,
    })
