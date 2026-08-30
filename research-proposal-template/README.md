# Research Proposal LaTeX Template

Overleaf-ready research proposal template based on the structure in
`Research Proposal Writing.docx`.

## Files

- `main.tex` - proposal template
- `references.bib` - sample bibliography database

## Overleaf Setup

1. Upload both files to a new Overleaf project.
2. Open `main.tex`.
3. Set the bibliography tool to `Biber`.
4. Compile.

## Citation Style

The template uses APA-style author-year citations through `biblatex`:

```latex
\textcite{sampleArticle}
\parencite{sampleBook}
```

The reference list is generated with:

```latex
\printbibliography
```

To add your own sources, replace the sample entries in `references.bib`.
