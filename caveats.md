# Caveats — Pathway Express Check

The analyses produced by Pathway Express Check rest on a number of methodological and
biological assumptions. The following caveats should be considered before drawing
conclusions or reporting results. See also `hypotheses.md` for guidance on what kinds
of hypotheses this tool can and cannot support.

---

## 1. Median Expression Conceals Intra-Tissue Heterogeneity

GTEx reports the **median** TPM across donors per tissue. Rare-cell-type expression,
outlier donors, sex/age stratification, and bimodal distributions are all collapsed into
a single value. A gene that is highly expressed in 5% of donors — for example, due to a
common variant or mosaic event — will appear lowly expressed in the median. Outlier
biology, exactly the kind that generates interesting hypotheses, is invisible to this
analysis.

## 2. GTEx v8 Reflects Healthy Adult Donors Only

The GTEx v8 dataset contains bulk RNA-seq from post-mortem tissue of adult donors with
no known major disease. Disease states, pediatric tissue, fetal tissue, and acutely
stressed tissue are not represented. Pathway co-expression patterns in cancer,
inflammation, or development may differ substantially from those observed here. Findings
should not be extrapolated to pathological contexts without independent validation in an
appropriate dataset.

## 3. Bulk RNA-seq Mixes Cell Types Within a Tissue

Each GTEx tissue sample is bulk RNA from a heterogeneous mixture of cell types. A
pathway active only in a minority cell type — for example, Purkinje cells within
cerebellum — will appear diluted relative to its true activity in that cell population.
Apparent low consistency scores may reflect cell-type dilution rather than a genuine
lack of co-regulation. Single-cell or single-nucleus RNA-seq data would be required to
resolve cell-type-specific co-expression.

## 4. Pearson r Detects Only Linear Co-expression

The pathway consistency score and pairwise correlation matrix are computed as Pearson r
on log₂(TPM+1) values across tissues. Non-monotonic or threshold-dependent
relationships — for example, a gene pair that is co-expressed only above a certain
expression level — will not be captured. Pearson r is also sensitive to outlier tissues.
Spearman r would be more robust to both concerns but is not currently computed.

## 5. Gene Set Membership Is Static and Curation-Dependent

MSigDB gene sets reflect the state of knowledge at the time of their curation. Newly
characterised pathway members, alternatively spliced isoforms with distinct functions,
and context-specific roles are absent. A high or low consistency score for a gene set
may partly reflect the quality and completeness of the curation rather than underlying
biology. Users working with rapidly evolving pathways should cross-check gene set
membership against current literature.

## 6. Correlation Does Not Imply Regulatory Relationship

Co-expression across tissues is consistent with — but does not prove — shared
transcriptional regulation, functional interaction, or causal relationship. Confounders
include shared housekeeping programs, correlated cell-type abundances across tissues,
and technical co-variation in library preparation or sequencing. A high consistency
score is a useful starting point for hypothesis generation; experimental validation
(e.g., ChIP-seq, perturbation assays, eQTL colocalisation) is required to move from
correlation to mechanism.
