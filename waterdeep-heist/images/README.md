# Illustrated recap images

Drop each session's images into its folder and they show up automatically in the
**Illustrated Recap** carousel at the top of that session's tab. No code changes needed.

```
waterdeep-heist/images/session-01/
waterdeep-heist/images/session-02/
...
waterdeep-heist/images/session-06/
```

- Supported: `.png .jpg .jpeg .webp .gif .avif`
- Order is by filename (natural sort), so number them: `01-the-heist-begins.png`, `02-...`
- The caption is the filename without the number prefix, extension, and with dashes/underscores turned into spaces
- Easiest way: open the folder on github.com, then **Add file → Upload files**, drag the images in, and commit to `main`
- New images appear on the site within a minute or two (after GitHub Pages redeploys)
- Keep images under ~2 MB each if you can (WebP or JPG at ~1600px wide is plenty) so mobile loads fast
