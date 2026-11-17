"""Prepare chapter reference additions only. No network, writes, or publication."""
import copy
import uuid
from cms_spec_refs import chapter_values
import cms_generate as legacy


# Placement, not product data: each paragraph reads the containing product row.
BINDINGS = {
    'decarb54': {
        0:[(1,'spec-001','numeric'),(2,'spec-001','unit')],
        1:[(1,'spec-004','numeric'),(2,'spec-004','unit'),(4,'spec-005','display'),(6,'spec-006','display')],
        2:[(1,'spec-002','numeric'),(2,'spec-002','unit'),(4,'spec-000','display'),(6,'spec-007','display')],
    },
    'ct-pegas-230': {
        0:[(1,'spec-002','numeric'),(2,'spec-002','unit'),(3,'spec-002','qualifier')],
        1:[(1,'spec-001','numeric'),(2,'spec-001','unit'),(4,'spec-006','display'),(6,'spec-000','display')],
        2:[(1,'spec-003','numeric'),(2,'spec-003','unit'),(5,'spec-004','no_load'),(7,'spec-004','full_load'),(9,'spec-005','display')],
    },
}


def prepare(snapshot):
    result=copy.deepcopy(snapshot)
    for story in result['stories']:
        c=story['content']; key=c.get('content_id')
        if key not in BINDINGS: continue
        rows={r['spec_key']:r for r in c['specifications']}
        for chapter_index,slots in BINDINGS[key].items():
            ch=c['story_sections'][chapter_index]
            refs=[]
            for index,spec,part in slots:
                ref={'component':'spec_reference','spec_key':spec,'paragraph_index':str(index),'render_part':part,'unit_style':'short' if part=='unit' else 'source',
                     '_uid':str(uuid.uuid5(uuid.NAMESPACE_URL,f'{key}:{chapter_index}:{index}:{spec}:{part}'))}
                refs.append(ref)
            if ch.get('specification_keys') and ch['specification_keys']!=refs:
                raise ValueError('Existing editor specification bindings differ; preserve and review them')
            ch['specification_keys']=refs
            # No number, unit, qualifier, or translation may change during import.
            for lang in ('en','vi'):
                if chapter_values(ch,rows,lang)!=legacy.chapter_body(ch,lang):
                    raise ValueError('Source chapter and canonical specifications disagree: '+key+':'+str(chapter_index)+':'+lang)
    return result


def prepare_to_file(snapshot_path, output, base=None, current=None, report=None):
    """Prepare from a snapshot file. Recommended: give base and current for the editor guard."""
    import json
    from pathlib import Path
    from cms_refresh_guard import run_guarded, summary, warn_not_editor_safe
    if (base is None) != (current is None):
        raise ValueError('Give both base and current, or neither')
    load=lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
    candidate=prepare(load(snapshot_path))
    if base is None:
        warn_not_editor_safe()
        Path(output).write_text(json.dumps(candidate,ensure_ascii=False,indent=2),encoding='utf-8')
        return {'stories':len(candidate['stories'])}
    output=Path(output)
    guard_report=run_guarded(load(base),load(current),candidate,output,report or output.with_name(output.stem+'-guard-report.json'))
    return {'stories':len(candidate['stories']),'guard':summary(guard_report)}


if __name__=='__main__':
    import argparse, json, sys
    parser=argparse.ArgumentParser(description='Prepare chapter specification_keys; no network or Storyblok writes.')
    parser.add_argument('snapshot'); parser.add_argument('--output',required=True)
    parser.add_argument('--base',help='last complete read-back snapshot (recommended)')
    parser.add_argument('--current',help='fresh complete Storyblok read just before the write (recommended)')
    parser.add_argument('--report',help='guard report path; default: <output>-guard-report.json')
    parser.add_argument('--unguarded',action='store_true',help='local analysis only; output must never be written to Storyblok')
    args=parser.parse_args()
    if args.base is None and args.current is None and not args.unguarded:
        parser.error('give --base and --current (editor guard), or --unguarded for local analysis only')
    result=prepare_to_file(args.snapshot,args.output,args.base,args.current,args.report)
    print(json.dumps(result,ensure_ascii=True))
    if 'guard' in result and not result['guard']['ok']:
        print('STOP: guard found conflicts or stops; no output was written. Read the report.',file=sys.stderr)
        sys.exit(1)
