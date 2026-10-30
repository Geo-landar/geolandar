// Outil ponctuel (lecture seule du dépôt dev) : copie les 3 jeux de données régionales dans data/regions.json
// Usage : node tools/extract_regions_from_dev.js chemin/vers/index.html
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
    if (c === '/' && h[k + 1] === '/') { k = h.indexOf('\n', k); continue; }
    if (c === '{') d++; else if (c === '}' && --d === 0) break;
  }
  return (0, eval)('(' + h.slice(j, k + 1) + ')');
}
const out = { geo: ex('REGIONS_GEOJSON_EMBEDDED'), source: ex('REGIONS_SOURCE'), leaders: ex('REGIONS_LEADERS') };
fs.writeFileSync('data/regions.json', JSON.stringify(out));
console.log('pays carte:', Object.keys(out.geo).length, '| source:', Object.keys(out.source).length, '| dirigeants régionaux:', Object.keys(out.leaders).length, '|', (fs.statSync('data/regions.json').size / 1e6).toFixed(1), 'Mo');
console.log(Object.keys(out.geo).join(', '));
