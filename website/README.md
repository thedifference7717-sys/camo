# CAMO website

Static site built from the website design (https://claude.ai/artifact/QB6piNbZWjL9suC5Kvfirw).
Plain HTML/CSS/JS, no build step, no third-party requests (fonts are self-hosted, strict CSP), so
visitors' IPs are not leaked to Google Fonts, analytics or CDNs.

```
website/
  index.html   page
  styles.css   all styling (night-ops palette)
  main.js      launch countdown only
  assets/      logo, Ghillie icon, favicon, white paper PDF, fonts (SIL OFL, licenses alongside)
```

Preview locally: `python3 -m http.server -d website 8080` then open http://localhost:8080.

## Hosting (free)
The plan is a separate **public** repo (e.g. `thedifference7717-sys/camo-website`) so the site can go live
while the code repo is private. Copy this folder's contents to that repo's root, then either:
- **Cloudflare Pages**: connect the repo, framework "None", build command empty, output directory `/`.
- **GitHub Pages**: Settings → Pages → deploy from branch `main`, folder `/ (root)`.

## Before publishing
- Downloads (Dec 7), mining guide, block explorer and community links are shown as "soon"; replace them with
  real links when they exist.
- The GitHub link 404s until the repo is made public (planned Nov 10).
- Keep supply numbers, burn address and dates in sync with `CLAUDE.md`, `contrib/camo/ALLOCATION.md` and the
  white paper.
