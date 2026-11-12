"""Chunking rule (R2): one fragment per Markdown `##` section, titulo carried on each. Pure."""

from app.domain.retrieval.fragment import Fragment
from app.domain.retrieval.kb_document import SECTION_HEADING, KbDocument


def chunk_document(doc: KbDocument) -> list[Fragment]:
    starts = [m.start() for m in SECTION_HEADING.finditer(doc.body)]
    ends = starts[1:] + [len(doc.body)]
    sections = [doc.body[s:e].strip() for s, e in zip(starts, ends)]

    return [
        Fragment(
            text=f"{doc.titulo}\n\n{section}",
            titulo=doc.titulo,
            source_id=doc.id,
            tipo=doc.tipo,
            vigente_desde=doc.vigente_desde,
            ejemplo=doc.ejemplo,
        )
        for section in sections
    ]
