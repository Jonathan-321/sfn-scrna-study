# UC Recurring CFN Edge Annotation Starter

- Minimum support: `2`
- Level: `raw`

| run                      | edge_label                                      | support_count | biological_theme                          | plausibility_seed | rationale_seed                                                                                           |
|--------------------------|-------------------------------------------------|---------------|-------------------------------------------|-------------------|----------------------------------------------------------------------------------------------------------|
| compartment_composition  | Epi__CD8+ IL17+->Epi__Tuft                      | 2             | epithelial-immune crosstalk               | plausible         | Cross-lineage epithelial and immune interaction is plausible in inflamed mucosa.                         |
| compartment_composition  | Epi__MT-hi->Epi__Endothelial                    | 2             | stress-associated / caution               | caution           | Contains a stress-associated state; interpret cautiously.                                                |
| compartment_composition  | Epi__MT-hi->Epi__Plasma                         | 2             | stress-associated / caution               | caution           | Contains a stress-associated state; interpret cautiously.                                                |
| compartment_composition  | Epi__Plasma->Epi__Endothelial                   | 2             | immune-stromal interaction                | plausible         | Needs manual biological review.                                                                          |
| compartment_composition  | LP__Enterocyte Progenitors->Epi__Myofibroblasts | 2             | epithelial-stromal remodeling             | highly_plausible  | Matches epithelial-stromal niche remodeling around crypt injury and repair.                              |
| compartment_composition  | LP__Tregs->LP__WNT2B+ Fos-hi                    | 2             | immune-stromal interaction                | plausible         | Needs manual biological review.                                                                          |
| donor_global_composition | Enterocyte Progenitors->ILCs                    | 2             | epithelial-immune crosstalk               | highly_plausible  | Links epithelial progenitor stress with innate lymphoid response in mucosal inflammation.                |
| donor_global_composition | Enterocyte Progenitors->Myofibroblasts          | 2             | epithelial-stromal remodeling             | highly_plausible  | Matches epithelial-stromal niche remodeling around crypt injury and repair.                              |
| donor_global_composition | RSPO3+->CD8+ IELs                               | 2             | immune-stromal interaction                | plausible         | Stromal niche support paired with intraepithelial immune dysregulation is biologically suggestive in UC. |
| donor_global_composition | Stem->Immature Enterocytes 2                    | 2             | epithelial regeneration / differentiation | highly_plausible  | Direct epithelial stem-to-immature enterocyte axis; consistent with regeneration/remodeling.             |
| donor_global_composition | Tuft->TA 2                                      | 2             | epithelial regeneration / differentiation | plausible         | Both are epithelial-state terms; may reflect remodeling of differentiation programs after injury.        |
