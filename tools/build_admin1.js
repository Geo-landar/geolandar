// Outil ponctuel : transforme Natural Earth (admin-1) en data/admin1.json léger (une entrée par pays, régions simplifiées).
// Usage : node tools/build_admin1.js chemin/vers/ne_10m_admin_1_states_provinces.geojson
const fs = require('fs');
const { topology } = require('topojson-server');
const { presimplify, simplify, quantile } = require('topojson-simplify');
const src = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const by = {};
for (const f of src.features) {
  const iso = (f.properties.iso_a2 || '').toLowerCase();
  if (!iso || iso === '-99') continue;
  (by[iso] = by[iso] || []).push({ type: 'Feature', properties: { n: f.properties.name_fr || f.properties.name }, geometry: f.geometry });
}
const out = {};
for (const [iso, feats] of Object.entries(by)) {
  let t = topology({ r: { type: 'FeatureCollection', features: feats } }, 1e4);
  t = presimplify(t);
  const w = quantile(t, 0.93); // garde ~7 % des points les plus significatifs
  t = simplify(t, w);
  t.arcs = t.arcs.map(a => { const r = []; for (const p of a) { const q = [Math.round(p[0] * 100) / 100, Math.round(p[1] * 100) / 100]; const l = r[r.length - 1]; if (!l || l[0] !== q[0] || l[1] !== q[1]) r.push(q); } return r.length > 1 ? r : a.slice(0, 2).map(p => [Math.round(p[0] * 100) / 100, Math.round(p[1] * 100) / 100]); }); // retire le poids (z) ajouté par presimplify
  out[iso] = t;
}
fs.writeFileSync('data/admin1.json', JSON.stringify(out));
console.log(Object.keys(out).length, 'pays', (fs.statSync('data/admin1.json').size / 1e6).toFixed(1), 'Mo');
