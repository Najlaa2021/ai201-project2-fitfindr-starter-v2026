"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import suggest_outfit, create_fit_card
from mcp_client import call_tool
from generate import ModelUnavailable
from utils.data_loader import load_listings


# ── search, through MCP ───────────────────────────────────────────────────────

def _search(description: str, size: str | None, max_price: float | None) -> list[dict]:
    """search_listings, called through the MCP server in mcp_server.py."""
    return call_tool("search_listings", {
        "description": description,
        "size": size,
        "max_price": max_price,
    })


# ── query parsing ─────────────────────────────────────────────────────────────

_PRICE_PATTERNS = [
    r"\b(?:under|below|less than|max|up to|at most)\s*\$?\s*(\d+(?:\.\d+)?)",
    r"\$\s*(\d+(?:\.\d+)?)\s*(?:or less|or under|max)\b",
]
_SIZE_PATTERN = r"\b(?:in\s+)?(?:size|sz)\s+((?:us\s+)?[a-z]*\d+(?:\.\d+)?|xxs|xs|s|m|l|xl|xxl)\b"


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max_price out of plain language, by regex.

    "vintage graphic tee under $30, size M"
        -> {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
    """
    text = query
    max_price = None
    for pattern in _PRICE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            max_price = float(match.group(1))
            text = text[: match.start()] + " " + text[match.end():]
            break

    size = None
    match = re.search(_SIZE_PATTERN, text, re.IGNORECASE)
    if match:
        size = match.group(1).upper()
        text = text[: match.start()] + " " + text[match.end():]

    description = re.sub(r"[,\s]+", " ", text).strip(" ,.")
    return {"description": description, "size": size, "max_price": max_price}


def _empty_search_message(parsed: dict) -> str:
    """
    Say which part of the query to change, by re-running the search with one
    filter dropped at a time.
    """
    desc, size, max_price = parsed["description"], parsed["size"], parsed["max_price"]
    what = f"'{desc}'" if desc else "your search"

    if max_price is not None:
        without_price = _search(desc, size, None)
        if without_price:
            cheapest = min(item["price"] for item in without_price)
            return (
                f"Nothing matching {what}{f' in size {size}' if size else ''} "
                f"is under ${max_price:.0f}. The cheapest match is "
                f"${cheapest:.0f}. Try raising your max price to ${cheapest:.0f} or more."
            )

    if size:
        without_size = _search(desc, None, max_price)
        if without_size:
            sizes = sorted({item["size"] for item in without_size})
            return (
                f"Nothing matching {what} comes in size {size}. "
                f"Sizes that do match: {', '.join(sizes)}. "
                "Try one of those, or leave the size out."
            )

    examples = sorted({item["category"] for item in load_listings()})
    return (
        f"No listings match the words in {what}"
        f"{' even with the size and price filters removed' if size or max_price is not None else ''}. "
        f"Try broader words, like an item type ({', '.join(examples)}) "
        "or a style such as 'vintage' or 'denim'."
    )


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    # Each pass runs one step and picks the next one from what came back.
    step = "parse"
    count = 0
    while step != "done":
        count += 1
        trace.check_iterations(count)

        if step == "parse":
            session["parsed"] = parse_query(session["query"])
            step = "search"

        elif step == "search":
            parsed = session["parsed"]
            session["search_results"] = _search(
                parsed["description"], parsed["size"], parsed["max_price"]
            )
            # THE BRANCH: nothing found -> say what to change and stop.
            if not session["search_results"]:
                session["error"] = _empty_search_message(parsed)
                step = "done"
            else:
                step = "select"

        elif step == "select":
            session["selected_item"] = session["search_results"][0]
            step = "outfit"

        elif step == "outfit":
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"], session["wardrobe"]
            )
            step = "fit_card"

        elif step == "fit_card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"]
            )
            step = "done"

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
