# UC Cluster Glossary

Last updated: 2026-03-13

## Purpose

This note translates the UC atlas cluster labels into plain language.

Important caution:

- these are study-specific cluster names, not universal ontology labels
- some names describe a canonical cell type
- some names describe an activation state
- some names describe a proliferative state
- some names describe marker-defined stromal subtypes

So a label like `CD4+ Memory` is closer to a standard immune cell type, while a
label like `WNT2B+ Fos-hi` is a study-defined stromal subtype with a marker and
activity signature.

## How to read the names

Common naming patterns in this atlas:

- `CD4+`, `CD8+`, `NKs`, `Plasma`, `Macrophages`, `DC1`, `DC2`:
  immune lineages
- `Enterocytes`, `Goblet`, `Stem`, `TA`, `M cells`, `Tuft`:
  epithelial lineages
- `Fibroblasts`, `Myofibroblasts`, `Pericytes`, `Endothelial`, `Venules`,
  `Glia`:
  stromal, vascular, or support-cell lineages
- `Cycling`:
  proliferating cells
- `Fos-hi` / `Fos-lo`:
  immediate-early activation signature, often a cell-state distinction
- `PD1+`, `CD69+`, `IL17+`:
  activation or functional markers
- `Immature`, `Progenitors`, `Stem`, `TA`:
  differentiation stage
- `BEST4+`, `RSPO3+`, `WNT2B+`, `WNT5B+`:
  marker-defined subtypes named after characteristic genes
- `MT-hi`:
  mitochondrial-high or stressed-like state, often needing extra caution in
  interpretation

## Broad compartments

### Epithelial lineage

- `Best4+ Enterocytes`
- `Enterocyte Progenitors`
- `Enterocytes`
- `Enteroendocrine`
- `Goblet`
- `Immature Enterocytes 1`
- `Immature Enterocytes 2`
- `Immature Goblet`
- `M cells`
- `Secretory TA`
- `Stem`
- `TA 1`
- `TA 2`
- `Cycling TA`
- `Tuft`

### Immune lineage

- `CD4+ Activated Fos-hi`
- `CD4+ Activated Fos-lo`
- `CD4+ Memory`
- `CD4+ PD1+`
- `CD69+ Mast`
- `CD69- Mast`
- `CD8+ IELs`
- `CD8+ IL17+`
- `CD8+ LP`
- `Cycling B`
- `Cycling Monocytes`
- `Cycling T`
- `DC1`
- `DC2`
- `Follicular`
- `GC`
- `ILCs`
- `Inflammatory Monocytes`
- `Macrophages`
- `NKs`
- `Plasma`
- `Tregs`

### Stromal, vascular, and support lineage

- `Endothelial`
- `Glia`
- `Inflammatory Fibroblasts`
- `Microvascular`
- `Myofibroblasts`
- `Pericytes`
- `Post-capillary Venules`
- `RSPO3+`
- `WNT2B+ Fos-hi`
- `WNT2B+ Fos-lo 1`
- `WNT2B+ Fos-lo 2`
- `WNT5B+ 1`
- `WNT5B+ 2`

### Ambiguous or cautionary state

- `MT-hi`

## Cluster-by-cluster plain-language guide

| Cluster | Plain meaning | Notes |
|---|---|---|
| `Best4+ Enterocytes` | absorptive epithelial cells with `BEST4`-like marker program | Often a specialized colon enterocyte subtype. |
| `CD4+ Activated Fos-hi` | activated CD4 T cells with strong immediate-early gene response | `Fos-hi` means high `FOS`-family activation signal. |
| `CD4+ Activated Fos-lo` | activated CD4 T cells with weaker immediate-early response | Same broad lineage as above, different activity state. |
| `CD4+ Memory` | memory CD4 T cells | Adaptive immune compartment. |
| `CD4+ PD1+` | PD-1 positive CD4 T cells | Often activated or exhausted-like state. |
| `CD69+ Mast` | activated tissue mast cells | `CD69` is an activation or tissue-residency marker. |
| `CD69- Mast` | mast cells without the `CD69` activation signature | Broadly the same lineage, different state. |
| `CD8+ IELs` | intraepithelial CD8 T cells | `IEL` = intraepithelial lymphocyte. |
| `CD8+ IL17+` | IL-17 expressing CD8 T cells | Pro-inflammatory cytotoxic T-cell-like state. |
| `CD8+ LP` | lamina propria CD8 T cells | `LP` = lamina propria. |
| `Cycling B` | proliferating B cells | Cell-cycle state, not just lineage. |
| `Cycling Monocytes` | proliferating monocytes | Cell-cycle state. |
| `Cycling T` | proliferating T cells | Cell-cycle state. |
| `Cycling TA` | proliferating transit-amplifying epithelial cells | Rapidly dividing epithelial progenitors. |
| `DC1` | dendritic cell type 1 | Antigen-presenting immune lineage. |
| `DC2` | dendritic cell type 2 | Antigen-presenting immune lineage. |
| `Endothelial` | vascular endothelial cells | Blood-vessel lining cells. |
| `Enterocyte Progenitors` | early absorptive epithelial precursors | Upstream of mature enterocytes. |
| `Enterocytes` | mature absorptive epithelial cells | Major intestinal epithelial lineage. |
| `Enteroendocrine` | hormone-producing epithelial cells | Rare secretory epithelial lineage. |
| `Follicular` | likely follicular B cells | B-cell compartment associated with lymphoid follicles. |
| `GC` | likely germinal-center B cells | `GC` usually means germinal center. |
| `Glia` | enteric glial support cells | Nervous-system support cells in the gut. |
| `Goblet` | mucus-producing epithelial cells | Secretory epithelial lineage. |
| `ILCs` | innate lymphoid cells | Innate immune lymphoid lineage. |
| `Immature Enterocytes 1` | immature absorptive epithelial cells | Developmental state before mature enterocytes. |
| `Immature Enterocytes 2` | second immature enterocyte state | Study-specific subdivision of immature enterocytes. |
| `Immature Goblet` | immature goblet cells | Developing mucus-producing cells. |
| `Inflammatory Fibroblasts` | fibroblasts with inflammatory program | Often expanded in inflamed tissue. |
| `Inflammatory Monocytes` | monocytes with inflammatory gene program | Immune inflammatory state. |
| `M cells` | antigen-sampling epithelial cells | Specialized epithelial lineage involved in immune sampling. |
| `MT-hi` | mitochondrial-high cells | Often stressed, dying, or technically unusual; interpret cautiously. |
| `Macrophages` | tissue macrophages | Myeloid immune lineage. |
| `Microvascular` | small-vessel vascular cells | Likely microvascular endothelial or closely related vascular subset. |
| `Myofibroblasts` | contractile stromal fibroblast-like cells | Tissue-remodeling stromal lineage. |
| `NKs` | natural killer cells | Innate cytotoxic lymphoid lineage. |
| `Pericytes` | vessel-associated support cells | Support vascular integrity. |
| `Plasma` | plasma cells | Antibody-secreting B-cell lineage. |
| `Post-capillary Venules` | venule-associated vascular cells | Specialized vascular segment. |
| `RSPO3+` | `RSPO3`-positive stromal cells | Often niche-supporting fibroblast/stromal population. |
| `Secretory TA` | transit-amplifying epithelial cells biased toward secretory fate | Intermediate progenitor state. |
| `Stem` | epithelial stem cells | Intestinal crypt stem compartment. |
| `TA 1` | transit-amplifying epithelial state 1 | Rapidly dividing epithelial progenitor state. |
| `TA 2` | transit-amplifying epithelial state 2 | Another TA subdivision. |
| `Tregs` | regulatory T cells | Immunosuppressive CD4 T-cell lineage. |
| `Tuft` | tuft cells | Rare chemosensory epithelial lineage. |
| `WNT2B+ Fos-hi` | `WNT2B`-positive stromal cells with high activation signature | Marker-defined stromal subtype. |
| `WNT2B+ Fos-lo 1` | `WNT2B`-positive stromal cells with lower activation signature, subtype 1 | Study-specific stromal subdivision. |
| `WNT2B+ Fos-lo 2` | `WNT2B`-positive stromal cells with lower activation signature, subtype 2 | Study-specific stromal subdivision. |
| `WNT5B+ 1` | `WNT5B`-positive stromal subtype 1 | Marker-defined fibroblast/stromal population. |
| `WNT5B+ 2` | `WNT5B`-positive stromal subtype 2 | Marker-defined fibroblast/stromal population. |

## Practical interpretation rules

### 1. Not all labels are equally “cell-type-like”

Closer to canonical cell types:

- `Macrophages`
- `Plasma`
- `NKs`
- `Goblet`
- `Enterocytes`
- `Tregs`

Closer to study-specific states or subclusters:

- `CD4+ Activated Fos-hi`
- `WNT2B+ Fos-lo 1`
- `WNT5B+ 2`
- `MT-hi`
- `Cycling T`

This matters because broad biological conclusions should usually be drawn first
at the coarse-family level, not from every fine subcluster.

### 2. Some of the strongest UC shifts are biologically interpretable

From the local UC donor summaries:

- immune-associated clusters such as `Follicular`, `CD4+ Memory`, and `Tregs`
  are higher in UC
- inflammatory stromal populations such as `Inflammatory Fibroblasts` are
  higher in UC
- absorptive epithelial maturation states such as `Immature Enterocytes 1` and
  `Enterocyte Progenitors` are lower in UC

That pattern is coherent with inflamed tissue containing more immune and
reactive stromal content and relatively less normal epithelial composition.

### 3. `Fos-hi`, `Cycling`, and `MT-hi` should be treated carefully

These can reflect real biology, but they can also be disproportionately
sensitive to:

- acute stimulation
- proliferation
- stress
- technical handling effects

So they are useful, but they should not be over-interpreted in isolation.

## Best next use of this glossary

Use this glossary to build a coarse mapping next:
- epithelial
- immune
- stromal / vascular / neural
- cautionary state

That coarse mapping will make the composition results easier to reason about and
will likely be more stable than working only at the 51-cluster level.