// Exporte depuis la version de test (dev) les dirigeants régionaux et la composition
// des chambres vers data/regions_chambres.json, lu par update_regions.py pour
// remplir Supabase. À relancer après toute modification de ces données dans dev.
// Usage : node tools/export_regions_chambres.js chemin/vers/geolandar-dev/index.html
const fs = require('fs');
const h = fs.readFileSync(process.argv[2], 'utf8');
function ex(name) {
  const i = h.indexOf('var ' + name + '='); if (i < 0) throw new Error(name + ' introuvable');
  let j = h.indexOf('{', i), d = 0, k = j, str = null;
  for (; k < h.length; k++) {
    const c = h[k];
    if (str) { if (c === '\\') k++; else if (c === str) str = null; continue; }
    if (c === '"' || c === "'") { str = c; continue; }
    if (c === '/' && h[k + 1] === '*') { k = h.indexOf('*/', k) + 1; continue; }
    if (c === '{') d++; else if (c === '}' && --d === 0) break;
  }
  return (0, eval)('(' + h.slice(j, k + 1) + ')');
}
const L = ex('REGIONS_LEADERS'), C = ex('CHAMBRES_COMPOSITION');
const dirigeants = [], chambres = [];
for (const p in L) {
  const verif = ((L[p].disclaimer || '').match(/(?:vérifi\S*|à jour|situation)[^.]*?(\d{1,2}(?:er)? \S+ 20\d\d)/i) || [])[1] || '';
  for (const r in (L[p].liste || {})) {
    const x = L[p].liste[r];
    dirigeants.push(x.college ? { pays: p, region: r, college: x.college, verifie: verif }
      : { pays: p, region: r, nom: x.n || '', titre: x.t || '', parti: x.parti || '', pos: (x.pos === undefined ? null : x.pos), verifie: verif });
  }
}
for (const p in C) {
  let o = 0;
  for (const ch in (C[p].chambres || {})) {
    const x = C[p].chambres[ch];
    chambres.push({ pays: p, chambre: ch, total: x.total, groupes: x.groupes, perime: !!x.perime, verifie: C[p].verifie || '', ordre: o++ });
  }
}
fs.writeFileSync('data/regions_chambres.json', JSON.stringify({ dirigeants, chambres }));
console.log(dirigeants.length + ' dirigeants régionaux, ' + chambres.length + ' chambres');
