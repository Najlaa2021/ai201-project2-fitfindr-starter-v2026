"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# Words that say nothing about the item. Dropped before scoring, so "looking
# for a tee" scores the same as "tee".
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "in", "on", "with", "of", "to",
    "i", "im", "i'm", "me", "my", "want", "wanted", "need", "looking", "find",
    "some", "something", "any", "that", "this", "is", "it", "under", "below",
    "size", "sized", "around", "about", "please", "like", "would", "love",
}

_LETTER_SIZES = {"XXS", "XS", "S", "M", "L", "XL", "XXL"}


def _words(text: str) -> list[str]:
    """Lowercase words, with a trailing plural 's' dropped so jeans ~ jean."""
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def _size_tokens(size: str) -> set[str]:
    """
    Split a listing's size into whole tokens.

    "S/M" -> {S, M}. "XL (fits oversized)" -> {XL}. "W30 L30" -> {W30, L30}.
    "US 8.5" -> {8.5}. Matching on whole tokens is what keeps "L" from
    matching "XL" or "W30 L30".
    """
    size = re.sub(r"\(.*?\)", " ", size.upper())
    return {t for t in re.findall(r"[A-Z0-9.]+", size) if t != "US"}


def _size_matches(wanted: str, listing_size: str) -> bool:
    wanted = re.sub(r"^(US|SIZE)\s+", "", wanted.strip().upper())
    if not wanted:
        return True
    tokens = _size_tokens(listing_size)
    if listing_size.upper().startswith("ONE SIZE"):
        return wanted in _LETTER_SIZES or wanted in {"ONE", "ONE SIZE"}
    return wanted in tokens


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    keywords = [w for w in _words(description or "") if w not in _STOPWORDS]
    if not keywords:
        return []

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue

        title = set(_words(listing["title"]))
        tags = set(_words(" ".join(
            listing["style_tags"] + listing["colors"] + [listing["category"]]
        )))
        body = set(_words(listing["description"]))

        score = 0
        for word in keywords:
            if word in title:
                score += 3
            elif word in tags:
                score += 2
            elif word in body:
                score += 1
        if score > 0:
            scored.append((score, listing))

    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item_text = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    system = (
        "You are a thrift-savvy stylist. Be concrete and brief. "
        "Plain text, no markdown headings."
    )

    if not items:
        prompt = (
            f"Someone is thinking about buying this thrifted item:\n{item_text}\n\n"
            "We don't know anything they already own. Give general styling "
            "advice: two short outfit ideas (2-3 sentences each) describing the "
            "kinds of pieces that would pair well with it. Do not claim they "
            "own anything."
        )
    else:
        wardrobe_text = "\n".join(
            f"- {w['name']} ({w['category']}; colors: {', '.join(w.get('colors', []))}; "
            f"style: {', '.join(w.get('style_tags', []))})"
            for w in items
        )
        prompt = (
            f"Someone is thinking about buying this thrifted item:\n{item_text}\n\n"
            f"Here is what they already own:\n{wardrobe_text}\n\n"
            "Suggest one or two outfits (2-3 sentences each) that pair the new "
            "item with pieces from their wardrobe. Name each wardrobe piece "
            "exactly as it's written above. Only use pieces from that list."
        )

    response = generate(prompt, system=system).strip()
    if not response:
        return (
            f"Style the {new_item.get('title', 'item')} with simple basics in "
            f"colors that echo its {', '.join(new_item.get('colors', [])) or 'palette'}."
        )
    return response


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            f"Can't write a fit card for {new_item.get('title', 'this item')}: "
            "no outfit suggestion was provided."
        )

    prompt = (
        f"Write a caption for a social post about this thrift find.\n\n"
        f"Item: {new_item.get('title')}\n"
        f"Price: ${new_item.get('price'):.0f}\n"
        f"Platform: {new_item.get('platform')}\n"
        f"Condition: {new_item.get('condition')}\n\n"
        f"How it's being styled:\n{outfit}\n\n"
        "Rules: 2 to 4 sentences. Sound like a real person posting, not a "
        "product listing. Mention the item, the price and the platform once "
        "each. Be specific about the vibe of the outfit. Up to 3 hashtags at "
        "the end are fine. Return only the caption."
    )
    return generate(prompt, system="You write short, natural outfit captions.").strip()


def _describe_item(item: dict) -> str:
    """One listing as prompt text. Brand is left out when it's None."""
    lines = [
        f"Title: {item.get('title')}",
        f"Category: {item.get('category')}",
        f"Colors: {', '.join(item.get('colors', []))}",
        f"Style: {', '.join(item.get('style_tags', []))}",
        f"Size: {item.get('size')}",
        f"Price: ${item.get('price')}",
        f"Description: {item.get('description')}",
    ]
    if item.get("brand"):
        lines.insert(1, f"Brand: {item['brand']}")
    return "\n".join(lines)
