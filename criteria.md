# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
On a matching query the parse and the search are plain code with no
randomness, so they don't fail. What can fail is the two model calls,
`suggest_outfit` and `create_fit_card`, and every try makes both of them with
caching off. One timeout or rate-limit error from the free-tier API fails the
whole try. `run_agent` doesn't catch `ModelUnavailable` yet (that's unit 4),
so I'm allowing one bad try in five for the network rather than for my code.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path never reaches a model. `parse_query` is regex, `search_listings` is
a filter, and the branch is an `if not session["search_results"]` check in
`agent.py::run_agent`. The same query gives the same result every time, so
there's no luck involved. One miss in five would mean the branch is wrong, so
a 4-of-5 target would hide a real bug.

---

## 3. The selected item is the item the later tools receive

On a matching query, the `id` of `session["selected_item"]` equals the `id` of
`search_results[0]`, and it is the same `id` the trace shows going into
`suggest_outfit` and into `create_fit_card`, in 5 of 5 tries.

**Why this target:**
No model decides which item moves on. `run_agent` writes the first result to
the session, and both later steps read it back out of the session. So the
hand-off should never vary, and 5 of 5 is the honest target. I'm comparing
`id`s instead of reading the outfit text because a model can write about the
right item in vague words, or the wrong one in convincing words. The trace
shows what actually went in.


---

## 4. The fit card is a postable caption with the facts in it

The fit card is 2 to 4 sentences, not counting a trailing line of hashtags. It
states the selected item's exact price as `$NN` and names its platform, in at
least 4 of 5 tries on the same query.

**Why this target:**
The price and platform are the facts a buyer needs, and a caption longer than
four sentences isn't something anyone would post. The prompt in
`tools.py::create_fit_card` asks for all of this, but nothing in the code
checks the reply, and `TEMPERATURE` is 0.9. So the model will sometimes write
a fifth sentence or leave out the platform. 5 of 5 would assume the model
always follows instructions, and it doesn't.


---

## 5. Search respects the price ceiling and the size

For `'vintage graphic tee under $30, size M'`, every listing in
`session["search_results"]` costs $30 or less and comes in a size that fits M
(`M`, `S/M`, `M/L` or `One Size`), and none is `L`, `XL` or a waist size, in
5 of 5 tries.

**Why this target:**
The size field mixes letter, waist and shoe sizes. In Milestone 1 I found that
a substring test is wrong (`"L" in "XL"` and `"L" in "W30 L30"` are both
True), so this is the bug I'd most expect to slip in. The filters are plain
code in `tools.py::search_listings` with no model involved. If one try lets in
the wrong size, every try will, so anything under 5 of 5 means the filter is
broken.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
