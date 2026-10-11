# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

You ask FitFindr for a thrift item in plain language, for example
`'vintage graphic tee under $30, size M'`. It pulls a description, a size and
a price ceiling out of the request and searches 40 secondhand listings from
Depop, thredUp and Poshmark. Then it suggests one or two outfits that pair the
best match with clothes you already own, and writes a short caption you could
post. If nothing matches, it stops before the styling steps and tells you
which part of the request to change: the price, the size, or the words.


---

## Notes from the data (Milestone 1)

- **40 listings**, each with: `id`, `title`, `description`, `category`,
  `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list),
  `brand` (str or None), `platform`.
- **Sizes aren't one system.** Letter sizes (`S`, `M`, `L/XL`, `S/M`,
  `XL (oversized)`), waist sizes (`W28`, `W30 L30`), shoe sizes (`US 8`,
  `US 8.5`) and `One Size ...` all live in the same field. A plain substring
  test is wrong: `"L" in "XL"` and `"L" in "W30 L30"` are both True.
- **Prices** run from $12 to $75. Nothing is under $12, so `under $5`
  can never match.
- **Categories:** tops 15, bottoms 10, outerwear 8, shoes 4, accessories 3.
  The silk slip dress (`lst_013`) is filed under `bottoms`.
- **`brand` is None on most listings**, so no prompt can assume it.
- **A wardrobe** is `{"items": [...]}`. Each item has `id`, `name`,
  `category`, `colors`, `style_tags`, `notes`. The empty wardrobe is
  `{"items": []}`, the same shape with an empty list.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters `data/listings.json` by price ceiling and size,
  then ranks what's left by keyword overlap with the description. No model call.
- **Inputs:**
  - `description` (str): free-text keywords, e.g. `"vintage graphic tee"`.
    Filler words ("a", "for", "looking") are dropped.
  - `size` (str | None): `None` skips the size filter. A size matches when it
    equals one whole size token in the listing, ignoring case and any
    parenthetical. `"M"` matches `M`, `S/M` and `M/L` but not `XL`. `"L"` does
    not match `XL` or `W30 L30`. `"8"` and `"US 8"` match `US 8` but not
    `US 8.5`. `"W30"` matches `W30 L30`. A `One Size` listing matches any
    letter size (XS–XXL).
  - `max_price` (float | None): inclusive ceiling. `None` skips the price filter.
- **Returns:** `list[dict]` of at most `config.SEARCH_RESULT_LIMIT` (10)
  listing dicts, best match first. Each dict is the unchanged listing record
  with `id`, `title`, `description`, `category`, `style_tags`, `size`,
  `condition`, `price`, `colors`, `brand`, `platform`. Scoring: each keyword
  scores 3 if it's in the title, 2 if it's in `style_tags`, `category` or
  `colors`, and 1 if it's only in `description`. Ties go to the lower price.
- **When it has nothing:** `[]`, an empty list. Never `None`, and it never
  raises. That covers no keyword hits, every hit filtered out by size or
  price, and an empty description.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the new
  item. When the wardrobe has items, each outfit names pieces from it.
- **Inputs:**
  - `new_item` (dict): one listing dict, the shape `search_listings` returns.
  - `wardrobe` (dict): `{"items": [ {id, name, category, colors, style_tags, notes}, ... ]}`.
    `items` may be empty.
- **Returns:** `str`, non-empty plain text. It has one or two short outfits.
  With a non-empty wardrobe, each outfit names at least one wardrobe item by
  its `name`.
- **When it has nothing:** With an empty wardrobe (`items == []`) it still
  returns a non-empty `str` of general styling advice: what kinds of pieces
  to pair the item with, and no claims about what the user owns. It never
  returns `""` and never raises for an empty wardrobe. If the model returns
  blank text, it returns a fixed fallback sentence naming the item.

### `create_fit_card`

- **What it does:** Asks the model for a short social-media caption about the
  find and the outfit.
- **Inputs:**
  - `outfit` (str): the text `suggest_outfit` returned.
  - `new_item` (dict): the same listing dict that went into `suggest_outfit`.
- **Returns:** `str`, a 2–4 sentence caption that names the item, its price
  (`$NN`) and its platform once each. It may use emoji and hashtags. Wording
  changes from run to run (`TEMPERATURE = 0.9`).
- **When it has nothing:** If `outfit` is empty or only whitespace, it skips
  the model call and returns
  `"Can't write a fit card for <title>: no outfit suggestion was provided."`
  It never raises.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message
in `session["error"]` saying which part of the query to change, then stop.
`suggest_outfit` and `create_fit_card` are not called, and
`session["fit_card"]` stays `None`. Otherwise, put the first result in
`session["selected_item"]` and go on to `suggest_outfit`, then
`create_fit_card`.

To make the message specific, the empty branch re-runs `search_listings` with
one filter dropped at a time:
- Matches exist when the price filter is dropped: say the cheapest one's price
  and suggest raising the max.
- Matches exist when the size filter is dropped: say which sizes do exist.
- Neither helps: say the keywords matched nothing and suggest broader words.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** regex, in `agent.py::parse_query`, with no model
call.
- `max_price`: `under $30`, `below 30`, `less than $30`, `max $30`, `$30 or less`.
- `size`: `size M`, `in size M`, `size 8`, `size W30`.
- Everything left over is the `description`.

**What moves through the session:**
1. `query`
2. `parsed` (`description`, `size`, `max_price`)
3. `search_results`
4. `selected_item` (read back out of the session for both later tools)
5. `outfit_suggestion` (read back out for the fit card)
6. `fit_card`
7. `error`, set only when the run stops early.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Vintage Band Tee — Faded Grey — $19.0 on depop

  Outfit:   Outfit 1: Grunge Streetwear
Pair the vintage band tee with your baggy straight-leg jeans and black combat boots for an effortless, classic look. Throw on the vintage black denim jacket and finish with the black crossbody bag for extra edge.

Outfit 2: High-Low Contrast
Tuck the band tee into your wide-leg khaki trousers and accent the waist using the brown leather belt. Step into your chunky white sneakers to bridge the gap between casual grunge and neutral minimalism.

  Fit card: Score this faded grey vintage band tee on Depop for just $19 and haven't stopped wearing it since. I love throwing it on with baggy denim and combat boots for a total grunge streetwear vibe, or dressing it down with tailored khakis and chunky sneakers. Such an easy, lived-in piece to style. 

#depop #vintagestyle #grungefashion

0 model calls this session, 2 served from cache
```

The same command on a query nothing can match, which takes the empty-search
branch:

```
$ python app.py ask 'designer ballgown size XXS under $5'

  No listings match the words in 'designer ballgown' even with the size and price filters removed. Try broader words, like an item type (accessories, bottoms, outerwear, shoes, tops) or a style such as 'vintage' or 'denim'.

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
[{'id': 'lst_006', 'title': 'Graphic Tee — 2003 Tour Bootleg Style', 'description': 'Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.', 'category': 'tops', 'style_tags': ['graphic tee', 'vintage', 'grunge', 'streetwear', 'band tee'], 'size': 'L', 'condition': 'good', 'price': 24.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_002', 'title': 'Y2K Baby Tee — Butterfly Print', 'description': 'Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small.', 'category': 'tops', 'style_tags': ['y2k', 'vintage', 'graphic tee', 'cottagecore'], 'size': 'S/M', 'condition': 'excellent', 'price': 18.0, 'colors': ['white', 'pink', 'purple'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_033', 'title': 'Vintage Band Tee — Faded Grey', 'description': 'Faded grey band-style tee with distressed graphic. Crew neck. Fits boxy. Well-loved but no holes or major damage.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'band tee', 'graphic tee', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 19.0, 'colors': ['grey', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_015', 'title': 'Vintage Graphic Hoodie — Faded Black', 'description': 'Faded black pullover hoodie with barely-visible vintage graphic on the chest. Cozy interior. Some pilling but adds to the worn-in look.', 'category': 'tops', 'style_tags': ['vintage', 'grunge', 'graphic', 'streetwear'], 'size': 'L', 'condition': 'fair', 'price': 26.0, 'colors': ['black', 'charcoal'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_017', 'title': 'Mesh Long-Sleeve Top — Black', 'description': 'Sheer black mesh long-sleeve. Great for layering under a graphic tee or over a bralette. Stretchy material, fits true to size.', 'category': 'tops', 'style_tags': ['y2k', 'grunge', 'goth', 'layering'], 'size': 'S/M', 'condition': 'excellent', 'price': 15.0, 'colors': ['black'], 'brand': None, 'platform': 'depop'}, {'id': 'lst_012', 'title': 'Oversized Crewneck Sweatshirt — Vintage Navy', 'description': 'Perfectly faded navy crewneck. Genuinely vintage — not manufactured distressed. Ribbed cuffs and hem. No graphics, clean.', 'category': 'tops', 'style_tags': ['vintage', 'basics', 'oversized', 'classic'], 'size': 'XL (fits oversized)', 'condition': 'good', 'price': 20.0, 'colors': ['navy'], 'brand': None, 'platform': 'thredUp'}, {'id': 'lst_011', 'title': 'Low-Rise Cargo Pants — Khaki', 'description': 'Y2K era low-rise cargo pants. Lots of pockets. Khaki color, slightly distressed at the hems. Great for layering with a long tee.', 'category': 'bottoms', 'style_tags': ['y2k', 'cargo', '2000s', 'streetwear'], 'size': 'W29', 'condition': 'fair', 'price': 27.0, 'colors': ['khaki', 'tan'], 'brand': None, 'platform': 'poshmark'}]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Outfit 1:
Pair the Vintage Levi's 501 Jeans with the White ribbed tank top tucked in, secured by the Brown leather belt. Throw on the Vintage black denim jacket and finish with the Chunky white sneakers for an effortless off-duty streetwear look.

Outfit 2:
Style the Vintage Levi's 501 Jeans with the Oversized grey crewneck sweatshirt worn slightly slouchy. Add the Black combat boots and the Black crossbody bag to give the classic denim an edgy, grunge-inspired finish.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Score these vintage Levi's 501 jeans for just $38 over on my Depop and they fit like an absolute dream. I kept it super casual today by pairing the medium wash denim with some fresh white sneakers for that effortless, everyday errand vibe. Snagged just in time for fall layering. 

#vintagedenim #levis501 #depopseller
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
