"""Author presentation never infers correspondence from author position."""
def author_label(p):
    authors=p.get('authors') or []
    first=authors[0] if authors else p.get('first_author') or '待核实'
    values=p.get('corresponding_authors') or []
    verified=p.get('corresponding_author_verified') and p.get('corresponding_author_source')
    names=[]
    for value in values if verified and isinstance(values,list) else []:
        name=value.get('name','') if isinstance(value,dict) else value
        if isinstance(name,str) and name in authors and name not in names:names.append(name)
    others=[name for name in names if name!=first]
    return first+('（通讯作者）' if first in names else '')+(' · Corresponding: '+'、'.join(others[:2])+(' 等' if len(others)>2 else '') if others else '')
