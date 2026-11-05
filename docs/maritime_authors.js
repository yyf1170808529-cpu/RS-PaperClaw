'use strict';
(function(root){
  function label(p){
    const authors=Array.isArray(p.authors)?p.authors:[],first=authors[0]||p.first_author||'待核实';
    const values=p.corresponding_author_verified&&p.corresponding_author_source&&Array.isArray(p.corresponding_authors)?p.corresponding_authors:[];
    const names=[...new Set(values.map(v=>typeof v==='string'?v:v?.name).filter(v=>authors.includes(v)))],others=names.filter(v=>v!==first);
    return first+(names.includes(first)?'（通讯作者）':'')+(others.length?' · Corresponding: '+others.slice(0,2).join('、')+(others.length>2?' 等':''):'');
  }
  if(typeof module!=='undefined')module.exports={label};else root.MaritimeAuthors={label};
})(globalThis);
