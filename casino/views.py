import json
import random
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import CasinoProfile, Bet



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
    profile = get_or_create_profile(request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    bet_amount = int(data.get("bet_amount", 0))
    if bet_amount <= 0 or bet_amount > profile.balance:
        return JsonResponse({"error": "Invalid bet amount"}, status=400)

    reels = slot_spin_reels()
    result = slot_check_result(reels)

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

    return JsonResponse({
        "reels": reels,
        "win": result["win"],
        "match": result["match"],
        "multiplier": result["multiplier"],
        "payout": payout,
        "balance": profile.balance,
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
    profile = get_or_create_profile(request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    bet_amount = int(data.get("bet_amount", 0))
    if bet_amount <= 0 or bet_amount > profile.balance:
        return JsonResponse({"error": "Invalid bet amount"}, status=400)

    deck, player, dealer = deal_cards()
    pv = hand_value(player)
    dv = hand_value(dealer)
    game_over = False
    result = None
    payout = 0

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

    request.session["blackjack"] = {
        "deck": deck,
        "player": player,
        "dealer": dealer,
        "bet": bet_amount,
        "standing": False,
    }

    return JsonResponse({
        "player": [card_display(c) for c in player],
        "dealer": [card_display(dealer[0])] + [{"card": "🂠", "rank": "?", "suit": "", "color": "black"}],
        "player_value": hand_value(player),
        "dealer_value": hand_value(dealer[:1]),
        "game_over": game_over,
        "result": result,
        "payout": payout,
        "balance": profile.balance,
    })


@login_required
@require_POST
def blackjack_hit(request):
    profile = get_or_create_profile(request.user)
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
        del request.session["blackjack"]
    else:
        session["deck"] = deck
        session["player"] = player
        request.session["blackjack"] = session

    return JsonResponse({
        "card": card_display(card),
        "player": [card_display(c) for c in player],
        "player_value": pv,
        "game_over": game_over,
        "result": result,
        "payout": payout,
        "balance": profile.balance,
    })


@login_required
@require_POST
def blackjack_stand(request):
    profile = get_or_create_profile(request.user)
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

    return JsonResponse({
        "dealer": [card_display(c) for c in dealer],
        "player": [card_display(c) for c in player],
        "player_value": pv,
        "dealer_value": dv,
        "game_over": game_over,
        "result": result,
        "payout": payout,
        "balance": profile.balance,
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
            profile.balance += item["coins"]
            profile.save()
            return JsonResponse({
                "success": True,
                "coins_added": item["coins"],
                "balance": profile.balance,
                "message": f"Purchased {item['name']}!",
            })

    return JsonResponse({"error": "Invalid item"}, status=400)
