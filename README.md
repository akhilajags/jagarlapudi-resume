# Mario Resume — Akhila Jagarlapudi

A one-page, side-scrolling résumé where the content behaves like a Mario-style platformer. Move a pixel-Mario left and right to read through each section, jump straight to a section from the top nav, or download the full résumé as a PDF.

Live site: [jagarlapudi.com](https://jagarlapudi.com)

## Features

- **Side-scrolling movement** — walk Mario across the page with the arrow keys (desktop) or the on-screen arrow buttons (mobile).
- **Jump-to-section nav** — a bar at the top lists every section (Hello, About, Skills, …). Click one and Mario warps directly there; left/right still works from that point.
- **Download résumé** — a button in the nav downloads the résumé PDF in one click.
- **Retro styling** — VT323 pixel font, a Mario sprite sheet, and a classic blue-sky background.
- **Background music** — starts on first interaction (click, key press, or button tap).

## Project structure

```
jagarlapudi-resume/
├── index.html          # Main page (content lives here)
├── 404.html            # Served on bad URLs; kept identical to index.html
├── CNAME               # Custom domain for GitHub Pages
├── README.md
├── favicon.ico
└── public/
    ├── game.js         # Movement, music, and jump-to-section logic
    ├── main.css        # Styling
    ├── music.mp3       # Background track
    ├── resume.pdf      # The downloadable résumé
    └── img/
        ├── background.png
        ├── blank.png
        ├── floor.png
        ├── mario.png
        └── social.png  # Social preview image
```

## Run locally

Open `index.html` in a browser (Chrome works well). No build step or server needed — it's plain HTML, CSS, and JavaScript with jQuery loaded from a CDN.

## Deploy (GitHub Pages)

1. Push everything to the repository, keeping the structure above.
2. Go to **Settings → Pages** and deploy from the `main` branch, root folder.
3. Add your custom domain under **Pages → Custom domain** and enable **Enforce HTTPS**. The `CNAME` file should contain your domain (e.g. `jagarlapudi.com`).

## Updating the content

**Edit a section's text** — open `index.html` and find the matching `<div class="box">`. Each box starts with a `<b>` heading (e.g. `<b>ABOUT</b>`) followed by its text. Edit the text directly.

**Add or remove a section** — add or remove a `<div class="box">…</div>` inside `#scroll`. The page width adjusts automatically, so movement keeps working. If you want the new section in the top nav, add a matching link in the `#nav` bar and give it the correct `data-index` (sections are numbered from 0, in order).

**Swap the downloadable résumé** — replace `public/resume.pdf` with your new file, keeping the same name. The download button picks it up automatically; no code change needed.

**Force a refresh after changes** — `index.html` loads the CSS and JS with a version tag (e.g. `main.css?v=3`). Bump that number when you change those files so browsers load the new version instead of a cached one.

## Built with

HTML, CSS, JavaScript, and [jQuery](https://jquery.com/). Font: [VT323](https://fonts.google.com/specimen/VT323).

## Credits

Inspired by the classic Mario-style side-scroller résumé concept. Sprites and tiles are pixel-art recreations of that era's look.
