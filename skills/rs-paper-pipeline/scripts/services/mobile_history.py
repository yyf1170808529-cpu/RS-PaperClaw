"""Permanent published identities, rebuilt from archives and retained across repairs."""
import re
from urllib.parse import unquote
from services.maritime import read_json, write_json


def identity(value):
    value=unquote(str(value or '')).strip()
    value=re.sub(r'^https?://(?:www\.)?arxiv.org/(?:abs|pdf)/','',value,flags=re.I)
    value=re.sub(r'^arxiv:\s*','',value,flags=re.I)
    value=re.sub(r'^(?:https?://(?:dx\.)?doi.org/|doi:\s*)','',value,flags=re.I)
    if re.fullmatch(r'10\.\d{4,9}/\S+',value,re.I):return 'doi:'+value.lower()
    value=re.sub(r'\.pdf$','',value)
    if re.fullmatch(r'(?:\d{4}\.\d{4,5}|[a-zA-Z.-]+/\d{7})(?:v\d+)?',value):
        return 'arxiv:'+re.sub(r'v\d+$','',value).lower()
    return value


class PublishedHistory:
    def __init__(self,root,library):
        self.parent={};self.dates={}
        def link(values):
            values=[identity(v) for v in values if v]
            for v in values:self.parent.setdefault(v,v)
            for v in values[1:]:self.parent[self.find(v)]=self.find(values[0])
        for key,p in library['papers'].items():
            link([key,p.get('paper_id'),p.get('arxiv_id'),p.get('doi'),p.get('arxiv_url')])
        for old,new in library.get('aliases',{}).items():link([old,new])
        path=root/'docs/maritime-data/mobile/pushed-history.json'
        records=read_json(path,{'identities':{}})['identities']
        records={k:set(v) for k,v in records.items()}
        for archive in sorted(path.parent.glob('????-??-??.json')):
            saved=read_json(archive,{})
            if saved.get('publication_status') in ('partial','failed'):continue
            for p in saved.get('papers',[]):
                values=[p.get(f) for f in ('paper_id','arxiv_id','doi','arxiv_url') if p.get(f)]
                link(values)
                for v in values:records.setdefault(identity(v),set()).add(saved.get('date',archive.stem))
        for key,dates in records.items():
            canonical=self.find(identity(key))
            self.dates.setdefault(canonical,set()).update(dates)
        # Save every observed identifier, not just today's canonical ID, for later merges.
        write_json(path,{'schema_version':1,'identities':{k:sorted(self.dates[self.find(k)]) for k in sorted(set(self.parent)|set(records)) if self.dates.get(self.find(k))}})

    def find(self,key):
        self.parent.setdefault(key,key)
        if self.parent[key]!=key:self.parent[key]=self.find(self.parent[key])
        return self.parent[key]

    def canonical(self,paper):
        return self.find(identity(paper['paper_id']))

    def pushed_dates(self,paper):
        return self.dates.get(self.canonical(paper),set())

    def prior(self,paper,day):
        # Same-day rebuilds may retain valid picks, but never reuse an earlier day's paper.
        return bool(self.pushed_dates(paper)-{str(day)})
