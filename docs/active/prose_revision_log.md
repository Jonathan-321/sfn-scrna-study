# Prose Revision Log

Date: 2025-01
Files modified: `paper/main.tex`, `README.md`

---

## paper/main.tex

### Abstract

**Problem:** The original abstract was a single run-on paragraph. It used "non-trivial"
(forbidden phrase) and opened with a passive framing that buried the methodological
contribution. It also listed all three representations and both cohorts in a single
dense sentence.

**Changes:**
- Removed "non-trivial"; replaced with a direct statement of what the methodology
  actually requires ("requires strict donor-aware cross-validation").
- Split into two paragraphs: the first establishes the problem and the three
  representations/cohorts; the second delivers the quantitative results.
- Removed the run-on structure by using separate sentences for each result.
- Removed "These results establish that..." throat-clearing; the last sentence
  states the finding directly.

### Introduction

**Problem:**
1. The phrase "Several studies have demonstrated that cell type composition is
   indeed predictive" is hedgy and indirect ("indeed predictive" is a telltale
   hedging construction).
2. Two `---` em-dashes used as parenthetical delimiters in the first paragraph.
3. The five-classifier list used `---` dashes as parenthetical delimiters.

**Changes:**
- Rewrote the hedgy sentence to: "Cell type composition predicts IBD status at
  the donor level..." — direct, no hedge.
- Replaced the two `---` em-dash parentheticals with `\textemdash{}` in the
  first paragraph (used inline rather than converting to parentheses, to preserve
  the appositive structure).
- Replaced the classifier list `--- ... ---` with parentheses, which is cleaner
  and avoids dash abuse.

### Methods

**Problem:** Several passive voice chains in Feature Engineering and CLR
subsections. One `---` em-dash in the Future Work section.

**Changes:**
- "Raw composition tables were subject to two cleaning steps" → "We applied two
  cleaning steps to the raw composition tables" (active voice).
- "Any cell type present in fewer than 20% of donors... was removed. This
  eliminates types..." → "Cell types present in fewer than 20% of donors...
  were removed. These types are structurally absent..." (tightened; the subject
  of the second sentence was ambiguous).
- "Any cell type with standard deviation..." → "Cell types with standard
  deviation..." (parallel with the rare-type filter change).
- "inflate the effective dimensionality relative to $n$" — removed redundant "the".
- CLR section: "A pseudocount was added" → "We added a pseudocount" (active);
  "CLR was fit on training donors only... and applied separately" → "CLR parameters
  were fit on training donors only... and applied to test donors separately"
  (agent clarified).
- Future Work: "resolution --- a question" → "resolution, a question" (comma
  replaces em-dash; no structural meaning was carried by the dash).
- Subsubsection header: "SCP259 (Smillie et al. 2019 --- UC vs. Healthy)" →
  "SCP259 (Smillie et al. 2019: UC vs. Healthy)" (colon is the correct
  delimiter for a subtitle; em-dash was incorrect here).

### Discussion

**Problem:**
1. The opening paragraph used `---` dashes to list all three representations.
2. "The results reveal that no single representation dominates" is a weak opener
   that restates the abstract.
3. The CFN vs. linear paragraph used `---` dashes for parenthetical insertion
   of biological detail.
4. The edge stability paragraph used `---` after "0.026" as a shorthand for
   "meaning".

**Changes:**
- Rewrote the opening paragraph to state the benchmark framing directly without
  re-listing the representations in dash-delimited form. Replaced "The central
  aim of this study was to benchmark" with "This study benchmarks".
- CFN vs. linear: replaced `--- villous enterocyte depletion and goblet cell
  dropout ---` with parentheses. Removed "by contrast" as it was redundant given
  the explicit contrast in the preceding sentence.
- Edge stability: replaced `--- near-zero reproducibility` with a comma and the
  word "indicating"; the dash was used as an explanation marker, which a comma
  plus participle handles cleanly.
- Replaced "This is a consequence of" with "This contrast follows from" (avoids
  "this is" opener).
- Replaced "This finding has implications beyond this specific model" with "The
  implication extends beyond this specific model" (shorter, no throat-clearing).

### Conclusion

**Problem:**
1. "constitutes a strong and difficult-to-improve baseline" — "constitutes" is
   a forbidden phrase.
2. The conclusion was largely a restatement of the abstract with the same
   sentence ordering and some identical phrasing.
3. Passive voice: "scVI latent embeddings match linear composition performance
   when compartment structure is preserved" is acceptable but the paragraph felt
   like a list of abstract bullet points restated.

**Changes:**
- Rewrote the opening sentence to lead with the finding rather than the method:
  "Compartment-stratified cell type composition with CLR transformation and
  linear classifiers provides a strong, difficult-to-improve baseline..." —
  removes "constitutes", active construction.
- Split into two paragraphs. The first covers CFN vs. linear models (the action
  finding). The second covers the geometry insight, scVI, and transfer.
- Added a sentence connecting compartment-stratified scVI to the interpretation:
  "suggesting that the primary discriminative signal lies in compartment-level
  cellular makeup rather than cell-intrinsic transcriptional state."
- Changed the final sentence from "establish a methodologically sound baseline
  and identify CFN on compartment composition as the most promising direction"
  to a direct statement: "CFN on compartment composition is the most promising
  direction for further development in structured IBD patient stratification."

---

## Figure captions

### Figure 1

**Problem:** The caption described what was in the figure but did not orient the
reader to the most important comparison or give a reading guide. Used "shows" and
italics for panel direction labels.

**Changes:**
- Opens with a sentence naming what the figure is and what the key takeaway is
  (the colon/TI reversal).
- Added a "Reading guide" sentence directing readers to scan left to right across
  panels.
- Removed italics for "Left panel" / "Right three panels" — written out plainly.
- Removed the word "shows" from the lead sentence (moved to reading guide).

### Figure 2

**Problem:** Caption described the figure components without emphasizing the
global-vs-compartment contrast that is the entire point of the figure. Used
"shows" in the final sentence.

**Changes:**
- Opens by naming the figure as a contrast between global and compartment
  formulations.
- The second sentence immediately calls out the critical comparison (first vs.
  second panel) with the quantitative stability numbers.
- Added reading guide instructing readers to compare the two SCP259 panels first,
  then move to the Kong colon panel.
- Replaced "shows substantially more structured and reproducible patterns" with
  "has sharply defined block structure" (specific, not abstract).

### Figure 3

**Problem:** Caption used `\textit{Left}` and `\textit{Right}` for panel labels
(italics for direction labels, which the task prohibits). The quantitative result
was buried in the middle of the caption rather than stated upfront.

**Changes:**
- Opens with the figure name and the key finding (directional asymmetry) in one
  sentence.
- Second sentence states the quantitative asymmetry immediately.
- Third sentence describes the layout (bar chart left, heatmap right) using
  plain prose without italics.
- Reading guide directs the reader to the heatmap's CD→UC row.

---

## Figures at a glance (new section)

Added after `\tableofcontents\newpage` and before `\section{Introduction}` as
`\section*{Figures at a glance}`. Three paragraphs, each led by `\textbf{Figure N}`.
Each paragraph previews what the figure contains and what the reader should look
for. Written to orient a reader who wants to look at figures before reading the
full paper, and to give context not just description.

---

## README.md

**Problem:** The existing README was an in-progress planning document reflecting
an earlier stage of the project. It referenced old figure paths and old claims
("an honest benchmark paper story, not yet a stable-mechanism or CFN beats all
baselines story"). It opened with the generic "This repo..." construction and
used long bullet-point lists.

**Changes:**
- Replaced entirely with a clean, current README.
- Opens with a one-paragraph third-person summary of the project and its main
  finding (no hype, no "This is a fascinating study").
- "Results in brief" section: clean markdown table of the six top results pulled
  directly from the paper's tables.
- "Repository layout" section: reflects the actual current structure
  (`paper/`, `scripts/`, `results/`, `data/`, `docs/active/`), not the old
  structure.
- "How to reproduce" section: concrete script ordering using the actual script
  names from `scripts/`.
- "Figures" section: embeds the three publication figures at their actual paths
  under `results/figures/`.
- "Paper" section: points to `paper/main.pdf` and the GitHub URL.
- Correct affiliation throughout: Oklahoma Christian University,
  jonathan.muhire@eagles.oc.edu.
- No "Feel free to...", no "This repository contains...", no eight-item bullet
  lists with identical lead words.
