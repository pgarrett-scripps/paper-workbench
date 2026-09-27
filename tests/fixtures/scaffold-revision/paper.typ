#set page(paper: "us-letter", margin: 1in)
#set text(size: 11pt)
#import "config.typ": *
#align(center)[#text(size: 18pt, weight: "bold", paper-title)]
= Abstract
#paper-abstract
#set heading(numbering: "1.")

// >>> BODY START
= Introduction

We studied root bending in 12 seedlings in order to assess an association with treatment. The observations may support a role for the pathway.

= Methods

Seedlings were  imaged at 6 hours. We did not measure protein activity directly.

#include "results.typ"

= Interpretation

The observations are associative. Additional experiments could distinguish the proposed mechanism from an indirect effect.

The reference @doe provides background. Inline notation $x^2$ remains protected.
// <<< BODY END
#bibliography("references.bib", title: "References")
