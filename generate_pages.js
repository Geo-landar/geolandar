#!/usr/bin/env node
/* ═══════════════════════════════════════════════════════════════
   GEOLANDAR — Générateur des pages pays (référencement)
   Lit les données directement dans index.html (PAYS, INFO, LEADERS, E, SRC)
   et produit une page HTML statique par pays dans pages/<slug>/index.html,
   une page d'index /pays/ et, avec --sitemap, le sitemap.xml complet.

   Usage :
     node generate_pages.js --only France,Vietnam,Espagne   (pages d'essai)
     node generate_pages.js --all --sitemap                  (tout)
   Ne modifie JAMAIS index.html, CNAME ni les scripts de mise à jour.
   ═══════════════════════════════════════════════════════════════ */
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const SITE = 'https://geolandar.fr';
const OUT = path.join(ROOT, 'pays');           // → https://geolandar.fr/pays/<slug>/
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

/* ── Extraction d'un littéral JS (tableau/objet) de index.html ── */
function extract(name) {
  let s = html.indexOf('\nvar ' + name + '=');
  if (s < 0) s = html.indexOf('\nvar ' + name + ' =');
  if (s < 0) throw new Error('Données introuvables dans index.html : ' + name);
  const eq = html.indexOf('=', s);
  let open = eq + 1;
  while (html[open] !== '[' && html[open] !== '{') open++;
  const o = html[open], c = o === '[' ? ']' : '}';
  let d = 0, q = null, k;
  for (k = open; k < html.length; k++) {
    const ch = html[k];
    if (q) { if (ch === '\\') k++; else if (ch === q) q = null; continue; }
    if (ch === '"' || ch === "'" || ch === '`') { q = ch; continue; }
    if (ch === '/' && html[k + 1] === '*') { k = html.indexOf('*/', k) + 1; continue; }
    if (ch === '/' && html[k + 1] === '/') { k = html.indexOf('\n', k); continue; }
    if (ch === o) d++;
    if (ch === c && --d === 0) break;
  }
  return (0, eval)('(' + html.slice(open, k + 1) + ')');
}
const PAYS = extract('PAYS'), INFO = extract('INFO'), LEADERS = extract('LEADERS');
const E = extract('E'), SRC = extract('SRC');
if (!PAYS.length || !E.length || !Object.keys(LEADERS).length) throw new Error('Structure de index.html inattendue');

/* ── Utilitaires ── */
const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const slug = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
const ACCENTS = { 'Bresil': 'Brésil', 'Thailande': 'Thaïlande', 'Tchequie': 'Tchéquie', 'Armenie': 'Arménie', 'Georgie': 'Géorgie',
  'Benin': 'Bénin', 'Egypte': 'Égypte', 'Equateur': 'Équateur', 'Erythree': 'Érythrée', 'Ethiopie': 'Éthiopie',
  'Emirats arabes': 'Émirats arabes unis', 'Etats-Unis': 'États-Unis', 'Coree du Sud': 'Corée du Sud', 'Coree du Nord': 'Corée du Nord',
  'Cote d\'Ivoire': 'Côte d\'Ivoire', 'Bahrein': 'Bahreïn', 'Koweit': 'Koweït', 'Haiti': 'Haïti', 'Indonesie': 'Indonésie',
  'Jamaique': 'Jamaïque', 'Micronesie': 'Micronésie', 'Mozambique': 'Mozambique', 'Algerie': 'Algérie', 'Guinee': 'Guinée',
  'Guinee equatoriale': 'Guinée équatoriale', 'Guinee-Bissau': 'Guinée-Bissau', 'Rep. dominicaine': 'République dominicaine',
  'Rep. du Congo': 'République du Congo', 'RD Congo': 'RD Congo', 'Centrafrique': 'Centrafrique', 'Mauritanie': 'Mauritanie' };
const nom = p => ACCENTS[p] || p;
const REGION = { EU: 'Europe', AM: 'Amériques', AF: 'Afrique', AS: 'Asie', OC: 'Océanie' };
const TYPE = { p: 'présidentielle', l: 'législative', s: 'sénatoriale', m: 'municipale ou régionale', r: 'référendum' };
const TYPEF = { p: 'Élection présidentielle', l: 'Élections législatives', s: 'Élections sénatoriales', m: 'Élections municipales ou régionales', r: 'Référendum' };
const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
const today = new Date(); today.setHours(0, 0, 0, 0);
function fmtDate(d, cert) {
  if (!d || cert === 3) return 'date à confirmer';
  const [y, m, j] = d.split('-').map(Number);
  if (!m || !j || cert === 2) return m ? MOIS[m - 1] + ' ' + y : String(y);
  return j + (j === 1 ? 'er ' : ' ') + MOIS[m - 1] + ' ' + y;
}
const isoOk = d => d && /^\d{4}-\d\d-\d\d$/.test(d) && !d.endsWith('-00');
const isPast = e => isoOk(e.d) && new Date(e.d + 'T00:00:00') < today;
const IND = [['pib', 'PIB'], ['cho', 'Chômage'], ['edu', 'Éducation'], ['san', 'Santé'], ['dem', 'Démocratie'], ['cor', 'Anti-corruption']];
const col = s => s >= 75 ? '#10b981' : s >= 50 ? '#eab308' : s >= 30 ? '#f97316' : '#ef4444';

/* ── Sélection des pays à générer ── */
const args = process.argv.slice(2);
const only = args.includes('--only') ? args[args.indexOf('--only') + 1].split(',').map(s => s.trim()) : null;
let list = PAYS.map(c => c.p);
if (only) {
  const miss = only.filter(n => !list.includes(n));
  if (miss.length) throw new Error('Pays inconnu(s) : ' + miss.join(', '));
  list = only;
} else if (!args.includes('--all')) { throw new Error('Précisez --all ou --only Pays1,Pays2'); }
const wanted = new Set(list);

/* ── Génération d'une page ── */
function page(c) {
  const p = c.p, n = nom(p), L = LEADERS[p], I = INFO[p] || {}, region = REGION[c.r] || '';
  const els = E.filter(e => e.p === p).sort((a, b) => (a.d || '').localeCompare(b.d || ''));
  const next = els.filter(e => !e.done && !isPast(e));
  const passed = els.filter(e => e.done || isPast(e));
  const nextYear = next.length ? (next[0].d || '').slice(0, 4) : '';
  const first = next[0];

  const title = (first
    ? `${n} : ${TYPE[first.t] ? TYPE[first.t][0].toUpperCase() + TYPE[first.t].slice(1) : 'élection'} ${nextYear}, dirigeant et indicateurs | Geolandar`
    : `${n} : dirigeant, régime politique et indicateurs | Geolandar`);
  const descParts = [];
  if (L) descParts.push(`${L.n}, ${L.t.charAt(0).toLowerCase() + L.t.slice(1)}`);
  if (first) descParts.push(`prochaine élection : ${TYPE[first.t] || 'scrutin'} ${fmtDate(first.d, first.cert)}`);
  descParts.push('indicateurs économiques, santé, éducation et démocratie');
  let desc = `${n} : ` + descParts.join(' ; ') + '.';
  if (desc.length > 158) desc = desc.slice(0, 155).replace(/[ ,;:]+\S*$/, '') + '…';

  const regime = (c.s || '').replace(/^Rép\./, 'République').replace(/Monarchie const\./, 'Monarchie constitutionnelle');

  let body = '';
  /* Présentation */
  body += `<section><h2>Présentation</h2><p>${esc(n)}${region ? ' — ' + esc(region) : ''}. Régime : <strong>${esc(regime || 'non précisé')}</strong>${c.pop ? ` · Population : <strong>${esc(c.pop)}</strong>` : ''}${I.capital ? ` · Capitale : <strong>${esc(I.capital)}</strong>` : ''}.</p>`;
  const rows = [['Capitale', I.capital], ['Langue(s)', I.langue], ['Monnaie', I.monnaie], ['Superficie', I.superficie]].filter(r => r[1]);
  if (rows.length) body += '<dl class="info">' + rows.map(r => `<div><dt>${r[0]}</dt><dd>${esc(r[1])}</dd></div>`).join('') + '</dl>';
  body += '</section>';
  /* Dirigeant */
  if (L) body += `<section><h2>${esc(n)} — dirigeant actuel</h2><div class="card"><div class="lname">${esc(L.n)}</div><div class="ltitle">${esc(L.t)}${L.p ? ' · ' + esc(L.p) : ''}</div>${L.d ? `<p>${esc(L.d)}</p>` : ''}</div></section>`;
  /* Élections à venir */
  if (next.length) {
    body += `<section><h2>${esc(n)} — prochaines élections</h2>`;
    next.forEach(e => {
      body += `<div class="card"><div class="ehead"><span class="badge">${esc(TYPEF[e.t] || 'Scrutin')}</span><span class="edate">${esc(fmtDate(e.d, e.cert))}</span></div>`;
      if (e.ctx) body += `<p>${esc(e.ctx)}</p>`;
      if (e.enjeux && e.enjeux.length) body += '<ul class="enj">' + e.enjeux.map(x => `<li><strong>${esc(x.t)}</strong> — ${esc(x.d)}</li>`).join('') + '</ul>';
      body += '</div>';
    });
    body += '</section>';
  }
  if (passed.length) {
    body += `<section><h2>${esc(n)} — dernières élections</h2>`;
    passed.slice(-2).reverse().forEach(e => {
      body += `<div class="card"><div class="ehead"><span class="badge">${esc(TYPEF[e.t] || 'Scrutin')}</span><span class="edate">${esc(fmtDate(e.d, e.cert))}</span></div>`;
      if (!e.done) body += `<p>Scrutin tenu. Les résultats sont en cours de consolidation : consultez la <a href="/">carte interactive</a> pour la mise à jour.</p>`;
      if (e.done && e.ctx) body += `<p>${esc(e.ctx)}</p>`;
      if (e.done && e.fiabilite && e.fiabilite.txt) body += `<p class="fiab"><strong>Fiabilité du scrutin :</strong> ${esc(e.fiabilite.txt)}${e.fiabilite.src ? ' <em>(sources : ' + esc(e.fiabilite.src) + ')</em>' : ''}</p>`;
      body += '</div>';
    });
    body += '</section>';
  }
  if (!els.length) body += `<section><h2>Élections</h2><p>Aucune élection nationale n’est actuellement référencée pour ce pays dans le calendrier 2026-2028. Le calendrier est mis à jour chaque nuit.</p></section>`;
  /* Indicateurs */
  if (c.i) body += `<section><h2>${esc(n)} — indicateurs clés</h2><div class="grid">` + IND.map(([k, lab]) => {
    const v = c.i[k]; return v ? `<div class="ind"><div class="il">${lab}</div><div class="iv" style="color:${col(v.s)}">${esc(v.v)}</div></div>` : '';
  }).join('') + '</div></section>';
  /* Sources */
  if (SRC[p]) body += `<section><h2>Source officielle</h2><p><a href="${esc(SRC[p].url)}" rel="noopener" target="_blank">${esc(SRC[p].n)}</a></p></section>`;
  /* Maillage interne */
  const voisins = PAYS.filter(x => x.r === c.r && x.p !== p && wanted.has(x.p)).slice(0, 12);
  if (voisins.length) body += `<section><h2>Autres pays : ${esc(region)}</h2><p class="chips">` + voisins.map(x => `<a href="/pays/${slug(x.p)}/">${esc(nom(x.p))}</a>`).join('') + '</p></section>';

  const url = `${SITE}/pays/${slug(p)}/`;
  const ld = [{ '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: [
    { '@type': 'ListItem', position: 1, name: 'Geolandar', item: SITE + '/' },
    { '@type': 'ListItem', position: 2, name: 'Pays', item: SITE + '/pays/' },
    { '@type': 'ListItem', position: 3, name: n, item: url }] }];
  return `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${url}">
<link rel="icon" type="image/png" href="/favicon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Geolandar">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${SITE}/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="${SITE}/og-image.png">
<script type="application/ld+json">${JSON.stringify(ld)}</script>
<style>${CSS}</style>
</head>
<body>
<header><a class="brand" href="/"><img src="/favicon.png" alt="" width="28" height="28"> Geolandar</a>
<nav><a href="/">Carte et calendrier</a><a href="/pays/">Tous les pays</a></nav></header>
<main>
<nav class="crumb" aria-label="Fil d’Ariane"><a href="/">Geolandar</a> › <a href="/pays/">Pays</a> › ${esc(n)}</nav>
<h1>${esc(n)} : ${first ? 'élections, ' : ''}dirigeant et indicateurs</h1>
${body}
<section class="cta"><h2>Explorer ${esc(n)} sur la carte interactive</h2><p>Globe, calendrier mondial des élections, résultats et fiabilité des scrutins dans 196 pays.</p><a class="btn" href="/">Ouvrir Geolandar</a></section>
</main>
<footer>Geolandar — Dans un monde de plus en plus complexe et interconnecté, comprendre ailleurs est essentiel. · <a href="/">geolandar.fr</a></footer>
</body>
</html>
`;
}

const CSS = `:root{--bg:#0a0e1a;--cd:#121828;--bd:#232c45;--tx:#eceff6;--mu:#8e98b3;--a:#f97316;--a1:#3b82f6}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--a1)}header{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 20px;border-bottom:1px solid var(--bd);flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:8px;font-weight:800;font-size:1.15rem;color:var(--a);text-decoration:none}
header nav a{margin-left:16px;color:var(--tx);text-decoration:none;font-size:.92rem}main{max-width:860px;margin:0 auto;padding:20px 16px 48px}
.crumb{font-size:.85rem;color:var(--mu);margin-bottom:8px}.crumb a{color:var(--mu)}
h1{font-size:1.9rem;line-height:1.2;margin:.2em 0 .6em}h2{font-size:1.2rem;margin:1.8em 0 .6em;color:var(--a)}
.card{background:var(--cd);border:1px solid var(--bd);border-radius:12px;padding:14px 16px;margin-bottom:12px}.card p{margin:.5em 0}
.lname{font-size:1.25rem;font-weight:700}.ltitle{color:var(--mu);font-size:.95rem}
.ehead{display:flex;justify-content:space-between;gap:8px;align-items:center;flex-wrap:wrap}.badge{background:#1e2a47;color:var(--a1);border-radius:999px;padding:2px 10px;font-size:.8rem;font-weight:600}.edate{color:var(--mu);font-size:.9rem}
.enj{padding-left:18px;margin:.4em 0}.enj li{margin:.4em 0}.fiab{color:var(--mu);font-size:.92rem}
.info{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:12px 0 0}.info div{background:var(--cd);border:1px solid var(--bd);border-radius:10px;padding:10px 12px}
dt{color:var(--mu);font-size:.8rem}dd{margin:2px 0 0;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}.ind{background:var(--cd);border:1px solid var(--bd);border-radius:10px;padding:10px 12px;text-align:center}
.il{color:var(--mu);font-size:.8rem}.iv{font-size:1.2rem;font-weight:800;margin-top:2px}
.chips{display:flex;flex-wrap:wrap;gap:8px}.chips a{background:var(--cd);border:1px solid var(--bd);border-radius:999px;padding:4px 12px;text-decoration:none;color:var(--tx);font-size:.9rem}
.cta{text-align:center;background:linear-gradient(135deg,#1a1f33,#14233f);border:1px solid var(--bd);border-radius:14px;padding:8px 16px 20px;margin-top:2em}
.btn{display:inline-block;background:var(--a);color:#fff;padding:10px 22px;border-radius:999px;text-decoration:none;font-weight:700}
footer{border-top:1px solid var(--bd);color:var(--mu);font-size:.85rem;text-align:center;padding:18px 16px}
@media (max-width:600px){h1{font-size:1.5rem}}`;

/* ── Écriture ── */
fs.mkdirSync(OUT, { recursive: true });
const done = [];
for (const c of PAYS.filter(x => wanted.has(x.p))) {
  const dir = path.join(OUT, slug(c.p));
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'index.html'), page(c));
  done.push(c);
}
/* Page d'index /pays/ */
const byRegion = {};
done.forEach(c => (byRegion[c.r] = byRegion[c.r] || []).push(c));
let hub = `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tous les pays : dirigeants, élections et indicateurs | Geolandar</title>
<meta name="description" content="Liste des pays du monde avec leur dirigeant, leur prochaine élection et leurs indicateurs clés : Europe, Amériques, Afrique, Asie, Océanie.">
<link rel="canonical" href="${SITE}/pays/"><link rel="icon" type="image/png" href="/favicon.png"><meta property="og:image" content="${SITE}/og-image.png"><style>${CSS}</style></head><body>
<header><a class="brand" href="/"><img src="/favicon.png" alt="" width="28" height="28"> Geolandar</a><nav><a href="/">Carte et calendrier</a><a href="/pays/">Tous les pays</a></nav></header>
<main><h1>Tous les pays : dirigeants, élections et indicateurs</h1>`;
Object.keys(REGION).forEach(r => {
  if (!byRegion[r]) return;
  hub += `<section><h2>${REGION[r]}</h2><p class="chips">` + byRegion[r].map(c => `<a href="/pays/${slug(c.p)}/">${esc(nom(c.p))}</a>`).join('') + '</p></section>';
});
hub += `</main><footer>Geolandar · <a href="/">geolandar.fr</a></footer></body></html>\n`;
fs.writeFileSync(path.join(OUT, 'index.html'), hub);

/* Sitemap (uniquement avec --sitemap) */
if (args.includes('--sitemap')) {
  const iso = today.toISOString().slice(0, 10);
  const urls = [[SITE + '/', '1.0', 'daily'], [SITE + '/pays/', '0.8', 'daily'], ...done.map(c => [`${SITE}/pays/${slug(c.p)}/`, '0.7', 'weekly'])];
  fs.writeFileSync(path.join(ROOT, 'sitemap.xml'), '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    urls.map(([u, pr, f]) => `  <url>\n    <loc>${u}</loc>\n    <lastmod>${iso}</lastmod>\n    <changefreq>${f}</changefreq>\n    <priority>${pr}</priority>\n  </url>`).join('\n') + '\n</urlset>\n');
}
console.log(`${done.length} page(s) générée(s) dans pays/ : ${done.map(c => slug(c.p)).join(', ')}`);
