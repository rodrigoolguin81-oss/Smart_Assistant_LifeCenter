"""Source citations in a generated answer (R10 a, b). Pure — no I/O.

A citation is exactly the string `Fragment.cita` produces: `[ID | vigente desde dd/mm/aaaa]`.
Anything else in brackets that *looks* like a source reference ("[TAR-001]", "[fuente: …]",
another date format) is reported by `malformed_citations`, so validation can reject an answer
that cites a source in a way that cannot be checked against the retrieved fragments.
"""

import re

CITATION = re.compile(r"\[[^\s\[\]|]+ \| vigente desde \d{2}/\d{2}/\d{4}\]")
BRACKETED = re.compile(r"\[[^\[\]]*\]")
# Signs that a bracketed segment is meant as a source reference: a "|" separator, the words of
# the citation format, or a document-ID shape such as TAR-001.
SOURCE_REFERENCE_HINT = re.compile(r"\||vigente|desde|fuente|\b[A-Z]{2,}-\d+\b", re.IGNORECASE)


def extract_citations(text: str) -> list[str]:
    """Every well-formed citation in `text`, in order of appearance (duplicates kept)."""
    return CITATION.findall(text)


def malformed_citations(text: str) -> list[str]:
    """Bracketed source references in `text` that are not well-formed citations."""
    return [
        segment
        for segment in BRACKETED.findall(text)
        if not CITATION.fullmatch(segment) and SOURCE_REFERENCE_HINT.search(segment)
    ]
