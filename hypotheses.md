# Hypotheses for Pathway Express Check

Pathway Express Check produces several quantitative outputs — pathway consistency score (mean pairwise Pearson r on log₂TPM+1 across GTEx v8 tissues), expression heatmaps, a pairwise correlation matrix, PCA of the gene × tissue matrix, per-gene summary statistics (CV, max tissue, mean/median TPM), and ranked correlated gene pairs. The following hypotheses are directly testable using these outputs.

---

## 1. Pathway Coherence vs. Curation Specificity

**Statement:** Hallmark gene sets will have higher pathway consistency scores than comparably sized GO Biological Process gene sets covering the same broad function.

**Rationale:** Hallmark sets (MSigDB H collection) are constructed by expert curation and iterative refinement to remove peripheral or indirectly associated genes. GO terms include all annotated members regardless of expression relevance, introducing noise that should lower mean pairwise correlations.

**Metrics to examine:** Consistency score for matched Hallmark vs. GO_BP gene sets (e.g., `HALLMARK_OXIDATIVE_PHOSPHORYLATION` vs. `GOBP_OXIDATIVE_PHOSPHORYLATION`).

**Predicted outcome:** Hallmark gene sets will show systematically higher consistency scores (mean pairwise r) than their GO counterparts, with reduced variance in the correlation matrix.

---

## 2. Tissue Relevance Predicts Local Coherence

**Statement:** The pathway consistency score for a metabolic or signalling pathway will be highest when the analysis is restricted to the tissue in which that pathway is physiologically dominant.

**Rationale:** Co-expression is driven by shared transcriptional programs. Genes in a liver-specific pathway (e.g., fatty acid metabolism) should be co-regulated in liver but uncorrelated in tissues where the pathway is largely inactive. The `max_tissue` field in per-gene summary stats identifies where each gene peaks.

**Metrics to examine:** Consistency score computed across all GTEx tissues vs. within a tissue subset selected by the `tissue_ids` parameter; `max_tissue` distribution for pathway members.

**Predicted outcome:** Restricting to the physiologically dominant tissue (e.g., liver for `HALLMARK_FATTY_ACID_METABOLISM`, brain subregions for `HALLMARK_NEUROGENESIS`) will increase the consistency score relative to the all-tissue score.

---

## 3. High-CV Genes as Tissue-Specific Pathway Drivers

**Statement:** Within a curated pathway, the genes with the highest coefficient of variation (CV = std / (mean + ε) across tissues) will correspond to known tissue-specific isoforms, rate-limiting enzymes, or pathway entry points rather than constitutively expressed housekeeping members.

**Rationale:** A high CV indicates that a gene's expression is strongly modulated across tissues, making it a candidate "driver" of where and when the pathway is activated. Constitutively expressed members (low CV) contribute to the pathway in all contexts but do not determine its tissue specificity.

**Metrics to examine:** `cv` column in the summary statistics table; cross-reference top-CV genes against literature or UniProt tissue expression annotations.

**Predicted outcome:** Top-CV genes will be enriched for tissue-restricted paralogs, regulated isoforms, or rate-limiting enzymes; low-CV genes will be enriched for shared scaffolding or structural subunits.

---

## 4. Anti-correlated Pairs Reveal Regulatory Feedback Within Pathways

**Statement:** Even within tightly curated gene sets, a detectable subset of gene pairs will be negatively correlated across GTEx tissues, reflecting mutual inhibition, reciprocal expression programs, or opposing arms of a regulatory network.

**Rationale:** Canonical pathways often contain both activators and inhibitors (e.g., pro- and anti-apoptotic BCL2 family members in apoptosis gene sets, or competing metabolic branches). If these are expressed in complementary tissue patterns, they will appear as negative Pearson r values in the correlation matrix despite co-membership in the same pathway.

**Metrics to examine:** Minimum values and bottom-ranked pairs in the correlation matrix; bottom of the sorted pairwise correlation table in the Excel export.

**Predicted outcome:** Apoptosis, cell cycle, and immune signalling gene sets will show more anti-correlated pairs than metabolic or structural gene sets, where members are generally co-induced.

---

## 5. PC1 Recapitulates Organ-System Boundaries Rather Than Pathway Structure

**Statement:** The first principal component of the gene × tissue expression matrix will separate GTEx tissues by major organ system (CNS, cardiovascular, GI, immune, reproductive) rather than by any pathway-internal gene grouping.

**Rationale:** GTEx tissue-to-tissue variance in bulk RNA-seq is large and dominated by cell-type composition. For a small gene set (typically 20–200 genes), the between-tissue variance will exceed the between-gene variance within a single pathway, so PC1 will load predominantly on tissue identity rather than gene modules within the pathway.

**Metrics to examine:** PCA scatter plot (tissue labels), PC1 loadings; compare tissue clustering in PC space across gene sets with different tissue-specificity profiles.

**Predicted outcome:** PC1 will broadly separate CNS tissues from peripheral tissues regardless of pathway; PC2 or later components are more likely to reflect within-pathway gene sub-modules or tissue sub-specialisation.

---

## 6. Consistency Score as a Druggability Proxy

**Statement:** Pathways with high consistency scores across all GTEx tissues (globally co-expressed) will be enriched for targets of approved systemic therapies, while pathways with high scores only in a single tissue will be enriched for tissue-selective or orphan therapeutic targets.

**Rationale:** A globally co-expressed pathway is active — and thus potentially essential — in many tissues, meaning that pharmacological intervention is likely to produce broad, on-target effects throughout the body. A pathway with strong tissue-restricted co-expression is a candidate for selective targeting with lower risk of systemic toxicity.

**Metrics to examine:** Consistency score (all tissues) vs. consistency score restricted to the top `max_tissue`; cross-reference against DGIdb or ChEMBL target–indication mappings.

**Predicted outcome:** High all-tissue consistency score will correlate with targets of chemotherapy, metabolic drugs, and broad-spectrum anti-inflammatories; tissue-selective high consistency will correlate with CNS, cardiac, or endocrine drug targets.
