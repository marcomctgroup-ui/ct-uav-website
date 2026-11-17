"""Render explicit chapter references to canonical specifications, without maths."""
import re
import cms_generate as legacy


def referenced_value(reference, row, language):
    value = legacy.specification_value(row, language)
    part = reference.get('render_part', 'display')
    if part in {'no_load', 'full_load'}:
        match = re.fullmatch(r'(?:No load|Không tải):\s*(.+?);\s*(?:Full load|Đầy tải|Tải đầy):\s*(.+)', value)
        if not match:
            raise ValueError('Conditional specification needs its explicit load labels')
        value = match[1 if part == 'no_load' else 2]
    elif part != 'display':
        qualifier = ''
        prefix = re.match(r'^(Tối đa|Maximum)\s+', value)
        if prefix:
            qualifier = prefix[1]; value = value[prefix.end():]
        match = re.fullmatch(r'(.*?)\s+(kg|km|ha|minutes|phút|min|m/s)(?:\s+(.*))?', value)
        if not match:
            raise ValueError('Specification cannot be split into literal value and unit')
        if part == 'numeric': value = match[1]
        elif part == 'unit':
            value = match[2]
            if reference.get('unit_style') == 'short' and value in {'minutes','phút'}: value = 'min'
        elif part == 'qualifier': value = match[3] or qualifier
        else: raise ValueError('Unknown specification render part')
    if not value.strip():
        raise ValueError('A specification reference cannot produce blank text')
    edges = []
    for key in ('prefix', 'suffix'):
        text = reference.get(key if language == 'en' else key + '__i18n__' + language, '')
        if not isinstance(text, str) or (reference.get(key) and language != 'en' and not text):
            raise ValueError('Specification context needs an explicit translation')
        edges.append(text)
    return edges[0] + value + edges[1]


def chapter_values(chapter, rows, language):
    values = legacy.chapter_body(chapter, language)
    used = set()
    for ref in chapter.get('specification_keys', []):
        index = ref.get('paragraph_index')
        if isinstance(index, str) and re.fullmatch(r'0|[1-9][0-9]*', index): index = int(index)
        if isinstance(index, bool) or not isinstance(index, int) or index < 0 or index >= len(values) or index in used:
            raise ValueError('Chapter specification target must be a unique paragraph index')
        if ref.get('spec_key') not in rows:
            raise ValueError('Chapter specification key does not exist')
        values[index] = referenced_value(ref, rows[ref['spec_key']], language)
        used.add(index)
    return values
