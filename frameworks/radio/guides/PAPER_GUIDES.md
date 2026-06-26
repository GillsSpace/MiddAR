# Paper Guides — combined editor checklist

*Condensed from three economics-writing guides so a draft can be checked against this one
file instead of the three source PDFs (`.misc/Harvard_Guide.pdf`, `IZA_Guide.pdf`,
`PP_Guide.pdf`). Sources: Harvard "Writing Economics"; Nikolov, "Writing Tips for
Economics Research Papers" (IZA DP 15057); Beatty & Shimshack, "Practical Tips for Writing
and Publishing Applied Economics Papers" (PP). Items marked **[ALL 3]** are where all three
agree — treat those as hard rules.*

This is the bar: **a paper that a top journal would publish.** The desk-reject screen reads
mainly the **abstract + introduction** and asks: is the question interesting, novel, and
important; is it of interest to this journal's readers; is it competently executed and
communicated. The two biggest rejection reasons are (a) **minimal or unclearly communicated
contribution** and (b) **poor writing**. Analysis is a small part of research — the paper
tells an economic *story* that answers an important, previously-unanswered question.

---

## 1. Structure (section order + the job of each)

Order: **Abstract → Introduction → Literature (or folded into intro) → Data → Identification
Strategy → Results (incl. robustness) → Conclusion → References → Appendices.** Not every
paper needs every section; a theory paper swaps in model/assumptions/propositions/proofs.

- **Abstract** — write it LAST. Concise, plain language; states the concrete contribution
  and the single headline result. Not "I found many interesting results."
- **Introduction** — the most important section (see §2). ≤ ~2 pages.
- **Literature** — ~2 pages. Two jobs: (a) situate relative to directly relevant prior work
  (same method/model/data), (b) state your contribution. **Synthesize into strands, do not
  summarize paper-by-paper.** [ALL 3] Mostly peer-reviewed *economics* journals. Avoid
  titling it bluntly "Literature Review" if it can fold into the intro.
- **Data** — name, source, period, unit of observation, N, central variables, panel/cross-
  section, and **limitations/proxies acknowledged**. Include a **summary-statistics table**
  (means, SDs), broken out by subgroup (treatment vs. control) where relevant. [ALL 3]
- **Identification Strategy** — ~2–3 pages. Write out the econometric equation; define every
  variable; **state which coefficient(s) are of interest**; state the testable hypothesis,
  the identifying assumptions, the naïve-OLS bias avoided, and the comparison groups.
  Explain why the design identifies the effect *in your specific context*, not in the
  abstract. [ALL 3]
- **Results** — ~3–5 pages. Main results + tables/figures + robustness. Secondary analyses →
  appendix (each with an in-text call).
- **Conclusion** — short, ~1 page / 5–6 paragraphs: summarize results, give the intuitive
  mechanism, state limitations, note policy implications and future research. Restate, do
  not re-derive. Conclusions must follow from the analysis. [ALL 3]
- **References** — complete; every relevant work cited (uncited relevant work angers
  referees and triggers rejection). One consistent style (AER / Chicago Author-Date).
- Workflow: write the intro first, **rewrite the intro after every other section**, then
  write the conclusion, then finalize the abstract, then **proofread last** (numbers make
  sense; every in-text citation appears in References and vice versa). [ALL 3]

## 2. The introduction (the recipe — all three give the same shape)

Lead with the punchline; this is not a mystery novel. **[ALL 3: state the main findings up
front, in the first few paragraphs — readers will not hunt for the punchline on page 10.]**
The "triangular" move: as soon as the specific question is posed, give the most important
finding, then backfill.

A 6-beat intro (Keith Head's formula, compatible with all three):
1. **Hook + why the general subject is important** — a puzzle, a hard-to-explain fact, or a
   strong claim; why someone outside the subfield should care.
2. **State the specific question + what the paper does** — literally "This paper explores…"
   / "This paper addresses the question of…". State it by the **3rd paragraph** at the
   latest. Ideally a **yes/no question in < 25 words**.
3. **Contribution (~3 points) relative to prior work** — what is new, and *why it matters
   for knowledge*. State that it is a contribution **and how** it is one.
4. **What the paper does** — key research strategy + key data in 1–2 short sentences; if a
   reader anticipates an obvious problem (endogeneity), signal how you handle it.
5. **Results** — the single most important finding; restate why it is novel/important.
6. **Roadmap** — specific enough that it couldn't apply to any other paper.

The reader must leave the first two paragraphs knowing the key independent variable, the
outcome, and the embedded testable hypothesis.

## 3. Writing style (concrete do / don't)

- **Clarity over eloquence.** [ALL 3] It is technical writing; the goal is to be understood,
  not clever. "Clear writing is easy to read but hard to write."
- **Active voice; not passive.** [ALL 3] "This paper studies X" / "I collected data," not
  "the effect was studied" / "data was collected."
- **Present tense throughout.** [ALL 3] "Mullainathan (2000) finds…"; "This study shows…"
- **Cut ruthlessly; omit needless words.** [ALL 3] "to" not "in order to"; "whether" not
  "whether or not"; "equals" not "is equal to"; drop "very."
- **Short words and short sentences beat long ones.** Monosyllables are fine.
- **Avoid jargon** — "any word you don't read in a newspaper is suspect"; only for
  unavoidable technical concepts.
- **Avoid "of course / clearly / obviously"** and dramatic adjectives/verbs; adverbs sparingly.
- **Positive form** ("ignored the warnings," not "did not pay attention to").
- **Prefer positive (evidence-based) statements over normative ("should/ought").** [ALL 3]
  Let the analysis speak; avoid unsupported value judgments and policy advocacy. Keep
  political/social commentary to the intro's first paragraphs and the conclusion.
- **"I" for what you did, "we" for what any reader would grant.** Personal pronouns are OK.
- **Footnote** minor digressions; keep the body self-contained.
- **In-text citations**: "Crawford (1998)" (author in sentence) or "(Crawford and Sobel,
  1982; Crawford, 1998)" (parenthetical, multiple ordered by date, semicolon-separated).
  Quotes need a page number; "et al." for 3+ authors.

## 4. Tables & figures (must stand alone)

- **Each table/figure is self-contained** — an intelligent reader who hasn't read the text
  understands it from title + legend + notes. [ALL 3]
- **Report only the coefficient(s) of interest**, not every control. [ALL 3] No "kitchen
  sink."
- **Name variables in plain English**, never raw Stata/SAS names (YEDUCT2011). [ALL 3]
- **The cardinal sin:** reporting estimates as bare "a"/"b" or code names without saying
  what they mean. Always identify the dependent variable.
- **State whether parentheses hold standard errors or t-statistics — SEs preferred.** [ALL 3]
- **No false precision** — 2–3 significant digits. SE-benchmark rule: round the SE to its
  first significant digit and the coefficient to the same place; uniform decimals down a
  column; rescale to avoid strings of zeros.
- **Figures**: label axes; define every symbol; sensible units (percentages good); legible
  in black-and-white (no invisible dotted lines); reduce clutter, gray-out non-focal series,
  and highlight only the points that carry the story; integrate text so the story transfers.
- **Describing results in text**: the paragraph's **topic sentence** states the table's main
  point; first and last sentences are big-picture, tied to the paper's story; walk the
  reader through the numbers in order.

## 5. The contribution / "top journal" bar

- The question must be **important, and novel** — it should complete "I wonder if…" / "It is
  interesting that…"; it matters if many (or important subpopulations) are better/worse off,
  it is puzzling/controversial, it tests an important theoretical prediction, or it involves
  large social-resource outlays. [ALL 3 frame the contribution as the gate to publication.]
- **Provide NEW evidence**, and **document *why* a result holds — the economic mechanism +
  evidence for it** — not merely that an empirical regularity exists.
- **Do not define the contribution by technique/model/skill** ("what if I apply method M to
  X?" / "what if I change an assumption in Model X?") unless you are a pure theorist/
  econometrician.
- **Communicate the contribution explicitly** — "having a contribution is not the same as
  communicating it." Restating the research question is not a contribution.
- **Identification, identification, identification** (applied micro): a credible causal claim
  via exogenous variation / IV / DiD / RDD / RCT, with assumptions defended *in context*.
- Position against the closest existing papers, give priority credit, be generous with
  citations, and don't be gratuitously critical of work whose authors may referee you.
- **Honesty bar**: no empirical paper is perfect; inconclusive results are fine if you say
  why; acknowledge limitations rather than overclaim. [ALL 3] Report **economic magnitude,
  not just statistical significance** (everything is "significant" in a large panel).

## 6. Red flags (auto-fail checklist for the final editor)

- Punchline/question buried; reads like a mystery novel; question stated after ¶3. [ALL 3]
- Contribution minimal, vague, defined by technique, or merely a restated question. [ALL 3]
- "Kitchen sink" results dumping; false precision; ambiguous parentheses (SE vs t). [ALL 3]
- Coefficients reported as "a"/"b" or raw code names; dependent variable unlabeled.
- Tables/figures not self-contained; figures illegible in B&W.
- Passive voice; mixed tenses; jargon; "very/clearly/obviously"; filler; negative-form.
- Statistical significance reported without economic magnitude; missing standard errors.
- Lit review that summarizes paper-by-paper, cites everything, or is overly critical.
- Unsupported value judgments / policy advocacy; political commentary in the body.
- Conclusions not supported by the analysis; limitations hidden rather than acknowledged.
- Relevant work uncited (referee anger); citation/style inconsistent; references incomplete.
- Not proofread: numbers that don't reconcile, citations missing from References.
