# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**VibeMatch 1.0**

It matches you to songs that fit your vibe: your favorite genre, your mood, and
how much energy you want.

---

## 2. Intended Use  

VibeMatch takes a short taste profile and returns the top 5 songs from a small
catalog. Each pick comes with a plain-English reason, like "genre match" or
"energy fit 90%."

It assumes the user can name a favorite genre, a mood, and roughly how much
energy they want. It assumes their taste is stable and can be summed up in a few
numbers.

This is for classroom exploration, not real users. It is a simulation built to
learn how recommender scoring works, not a product.

**Non-intended use.** Do not use it to recommend music to real listeners, to
judge songs or artists, or to make any real decision. The catalog is tiny and
hand-made, so it does not reflect real listening data.

---

## 3. How the Model Works  

Think of it as a judge that gives each song points. The song with the most
points wins.

Every song has a genre, a mood, and five dials: energy, tempo, valence (how
happy it sounds), danceability, and acousticness. The user gives their favorite
genre, favorite mood, and a target for each dial.

Points come in two ways:

- **Genre and mood are all-or-nothing.** If the song's genre matches, it gets a
  flat bonus (+2.0). Same for mood (+1.0). No match means no points.
- **The dials reward closeness.** For each dial, the closer the song is to what
  the user wants, the more points it earns. A perfect match earns the full
  weight. The further off, the fewer points.

I add up all the points and rank the songs from highest to lowest. Not every
dial matters the same. Energy is weighted heaviest (2.0), then acousticness
(1.5), and the rest count less.

**What I changed from the starter.** The starter just handed back the first 5
songs in the file. I wrote the real scoring math, added a reason string for
every pick so you can see where the points came from, and normalized tempo (it
is stored in BPM but the other dials run 0 to 1). I also built a set of test
profiles to stress the system.

---

## 4. Data  

The catalog is a single CSV file with **20 songs**. Each song has a title,
artist, genre, mood, and five numeric features: energy, tempo (BPM), valence,
danceability, and acousticness.

The genres are spread thin. There are **17 genres across 20 songs**. Only lofi
(3 songs) and pop (2 songs) have more than one. Everything else — classical,
folk, reggae, blues, metal, jazz, and more — has exactly one song. Moods are
just as scattered.

I used the starter dataset as-is. I did not add or remove songs.

**What is missing.** A lot. There is no year, no language, no lyrics, and no
real listening history. Whole styles of music are absent. With only one song
per genre, a niche listener basically has one true match and nothing else. Real
taste is far richer than 20 rows can hold.

---

## 5. Strengths  

VibeMatch works best for clear, mainstream tastes that live in the catalog.

- **Chill Lofi** and **High-Energy Pop** got clean, sensible lists. These
  genres have more than one song, so the picks felt coherent and matched my gut.
- **The energy dial really works.** Chill Lofi got quiet, slow songs. High-Energy
  Pop and Deep Intense Rock got loud, fast ones. The two calm and loud lists had
  no overlap, which is exactly right.
- **Same energy, different mood is captured.** Pop and Rock both want high
  energy and share some songs, but their #1 picks differ: Pop lands on a happy
  song, Rock on a dark one. The mood and valence points pull them apart.
- **The reasons are honest.** Every pick shows where its points came from, so
  it is easy to see why a song ranked where it did.

---

## 6. Limitations and Bias 

The clearest weakness I found is a **genre filter bubble driven by catalog imbalance**. Of the
20 songs, 15 of the 17 genres are represented by a single track (only lofi has three and pop
has two), so a lofi or pop listener gets a tight, coherent top of the list while a classical,
folk, reggae, or blues fan has just one true match and is force-fed cross-genre songs at ranks
2–5. This is made worse by the scoring math: the flat +2.0 genre bonus plus energy being the
heaviest numeric weight (2.0) means the "energy gap" quietly dominates the ranking, so listeners
who care most about mood or acousticness are still ranked mainly on how close their energy is.
My weight-shift experiment confirmed the sensitivity — doubling energy and halving genre flipped
the adversarial "sad + high-energy" profile so a loud `metal / angry` track outranked the true
`blues / somber` match. In short, the system serves well-represented, energy-defined mainstream
tastes far better than niche or mood-driven users, and it never signals when it is padding the
list with songs the user did not actually ask for.

---

## 7. Evaluation  

**Profiles I tested.** I ran five listeners through the system. Three were realistic:
**High-Energy Pop** (loud, fast, danceable), **Chill Lofi** (calm, slow, acoustic), and
**Deep Intense Rock** (loud, fast, heavy). Two were tricky edge cases: **The Contradiction**
(wants sad music, but high energy) and **The Blank Slate** (no preferences at all). For each
one I checked the top 5 songs, their scores, and the reasons.

**What surprised me.** The same loud songs kept showing up for very different people. Also, the
Blank Slate still gave five "recommendations" even though every score was 0.00. It just listed
songs in the order they appear in the file. That is not a real recommendation.

**Comparing the profiles (what changed, and why it makes sense):**

- **High-Energy Pop vs. Chill Lofi.** Total opposites. Pop gets loud, fast songs. Lofi gets quiet,
  slow, acoustic songs. This shows the energy dial really works.

- **High-Energy Pop vs. Deep Intense Rock.** Both want high energy. So they share some songs (like
  Gym Hero). But the #1 pick is different. Pop picks a happy song. Rock picks a dark, heavy song.
  Same energy, different mood.

- **Chill Lofi vs. Deep Intense Rock.** The biggest contrast. One list is all calm. The other is
  all loud. No overlap. That makes sense — they sit at opposite ends of the energy dial.

- **Deep Intense Rock vs. The Contradiction.** These lists look alike. Both show rock and metal.
  But the Contradiction asked for sad, quiet blues. The high-energy request took over. The loud
  songs almost win. Only the genre and mood bonus lets the one true blues song reach #1.

- **Any real profile vs. The Blank Slate.** A real profile gives clear scores, about 6 to 9. The
  Blank Slate gives five songs all tied at 0.00. This shows the system has no "I don't know you
  yet" fallback. It just lists whatever comes first.

---

## 8. Future Work  

If I kept building this, I would:

1. **Add a "we don't know you yet" fallback.** Right now the Blank Slate gets 5
   songs all tied at 0.00, just in file order. That is not a real recommendation.
   I would detect an empty profile and return popular or diverse picks instead,
   and say so.
2. **Push for variety in the top 5.** The same loud songs keep showing up for
   different people. I would add a rule that nudges the list to cover more than
   one genre or mood, so a niche listener is not force-fed cross-genre filler.
3. **Grow the catalog and let energy stop dominating.** With more songs per genre
   and adjustable weights, the ranking would not lean so hard on the energy gap,
   and mood-driven listeners would be served better.

---

## 9. Personal Reflection  

I learned that a recommender is really just ranking. Score everything, sort it,
show the top few. The hard part is not the sorting. It is choosing the weights,
because those choices quietly decide who the system serves well and who it
ignores.

The thing that surprised me most was the Blank Slate. It still gave five
"recommendations" with every score at 0.00. That taught me a system can look
confident while knowing nothing. Now when I use a real music app, I wonder how
much of what I see is a true match versus just filler dressed up as a
recommendation.

---

## 10. Reflection and Ethics (VibeMatch 2.0)

_This section covers the reliability layer added in **VibeMatch 2.0**
(`src/reliability.py`, `eval/`, `tests/`) — the confidence scoring, filler
flagging, blank-slate guardrail, and the offline evaluation harness that gates
them._

### What are the limitations or biases in your system?

The core bias is a **genre filter bubble driven by catalog imbalance**, and the
reliability layer exposes it rather than removing it. With 15 of 17 genres
represented by a single song, a lofi or pop listener gets a coherent list while
a classical, folk, or blues fan gets one true match and cross-genre filler at
ranks 2–5. The evaluation report makes this measurable: The Contradiction case
carries **4 of 5 filler picks** and is the only profile with non-zero rank churn
(**20%** under the weight nudge), because energy is the heaviest numeric weight
(2.0) and quietly dominates the ranking for anyone who cares more about mood.

The confidence metric has its own limitation, and it is honest about it in the
design docs but still worth naming: **confidence measures only the top pick**
(`top_score / max_possible_score`), so it can read **HIGH (75%) while 4 of 5
picks are filler**. It answers "is the #1 result a good fit?" not "is this whole
list any good?" There is also no notion of real-world accuracy — with no
listening history, confidence is a fit-to-stated-profile proxy, not a claim that
the user will like the songs. Finally, every metric is measured against
**human-authored expectations** in `eval/cases.yaml`; the system is only as
unbiased as the five cases and thresholds a person chose to write.

### Could your AI be misused, and how would you prevent that?

The realistic misuse is **misrepresenting confidence as endorsement** — shipping
a "98% confidence" banner as if it were a quality guarantee, when it only means
the top song closely matches the numbers the user typed. Downstream, that could
be used to justify decisions the system was never built for (curating a public
playlist, ranking artists, A/B-testing listeners) on a 20-song hand-made catalog.
A filler pick presented without its label could also mislead someone into
thinking a padded recommendation was a real match.

Prevention is built into the system rather than left to a disclaimer:
- **Filler is always labelled** and the blank-slate guardrail refuses to fake a
  match, so low-quality output cannot silently pose as a real recommendation.
- **The confidence string states its own basis** ("top pick scored X of Y
  possible") instead of a bare percentage, so it can't be quoted as a general
  quality score without the caveat travelling with it.
- **Every run is logged** to `vibematch.log` (profile, guardrails fired,
  confidence, filler count), giving an audit trail if outputs are ever disputed.
- **The model card scopes intended use** to classroom exploration and explicitly
  lists non-intended uses (real listeners, judging artists, real decisions).

The strongest structural guard is that a **human authors the expectations and
reviews the report** — the evaluation harness is a checkpoint, not an autopilot.

### What surprised me while testing my AI's reliability?

Two things. First, that **the honest signals disagree with each other** on the
adversarial case: the confidence bucket says HIGH while the filler count says
"4 of 5 of this list is padding." I expected a reliability layer to give one
clean verdict; instead it taught me that "trustworthy" is several separate
questions, and a single number hides that.

Second, the **stability probe reproduced a manual finding automatically**. In
VibeMatch 1.0 I discovered the energy-vs-genre weight sensitivity by hand. In 2.0
the harness re-derived it with no manual poking: nudging weights (energy ×1.25,
genre ×0.75) leaves the three core profiles at **0% churn** but moves **20%** of
The Contradiction's list. Watching a metric surface the exact fragile case on its
own — turning a one-off observation into a repeatable regression check — was the
moment the "reliability engineering" idea clicked.

### Collaboration with AI during this project

I used an AI assistant to think through the reliability architecture and the
evaluation design, then implemented and verified against the real output myself.

**A helpful suggestion.** When I described wanting to add trust features without
breaking the working recommender, the AI suggested treating reliability as a
**wrapper around the existing scoring core** rather than rewriting it —
`recommend_with_guardrails()` calls the original `recommend_songs()`. The
downstream payoff was one I hadn't anticipated: because the guardrails wrap the
real path, the evaluation harness can exercise the **exact code the app runs**
(`eval/evaluate.py` imports `recommend_with_guardrails`), so the tests measure
shipping behavior instead of a copy. That kept the AI logic and the trust logic
cleanly separable and made the whole thing testable.

**A flawed suggestion.** The AI's first proposal for the confidence score was to
average the scores of all five recommendations. That sounded reasonable but was
wrong for this system: a profile with lots of filler would average *down* and
report low confidence even when the **#1 pick was excellent**, conflating
"is the best match good?" with "is the list padded?" — two questions the design
deliberately keeps separate (filler count already answers the second). I rejected
it and used **top score ÷ best-possible score** instead. Testing then revealed
the residual limitation I documented above (HIGH confidence can still coexist
with heavy filler), which confirmed that top-pick and whole-list quality really
are distinct signals that should not be collapsed into one average.
