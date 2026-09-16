// Bundles src/main.js (+ three.js, tree-shaken) and inlines it into the page.
// Emits two files from one template:
//   index.html    — standalone, works over file:// and on GitHub Pages
//   artifact.html — body content only, for publishing as a hosted Artifact
import { build } from 'esbuild';
import { readFile, writeFile } from 'node:fs/promises';

const out = await build({
  entryPoints: ['src/main.js'],
  bundle: true,
  format: 'esm',
  target: 'es2020',
  minify: true,
  legalComments: 'none',
  write: false,
});

const js = out.outputFiles[0].text.replaceAll('</script', '<\\/script');
const tpl = await readFile('src/template.html', 'utf8');

const split = tpl.indexOf('<div id="stage">');
const head = tpl.slice(0, split).trim();
const body = tpl.slice(split).trim();
const script = `<script type="module">\n${js}\n</script>`;

await writeFile('artifact.html', `${head}\n\n${body}\n\n${script}\n`);
await writeFile('index.html',
  `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
${head}
</head>
<body>
${body}

${script}
</body>
</html>
`);

const kb = n => `${(n / 1024).toFixed(0)} KB`;
console.log(`bundle ${kb(js.length)} · index.html ${kb((await readFile('index.html')).length)}`);
