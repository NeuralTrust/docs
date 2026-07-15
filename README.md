# Mintlify StarterKit

Click on `Use this template` to copy the Mintlify starter kit. The starter kit contains examples including

- Guide pages
- Navigation
- Customizations
- API Reference pages
- Use of popular components

### Development

**Node.js:** Use **Node 20 or 22 LTS** (see `.nvmrc`; Mintlify does not support **Node 25+**). Pick one approach:

- **Homebrew (macOS, no version manager):** `brew install node@22`, then put that Node first on your `PATH` for this shell or permanently, for example:
  `export PATH="$(brew --prefix)/opt/node@22/bin:$PATH"`  
  Confirm with `node -v` (should be `v22.x`).
- **[fnm](https://github.com/Schniz/fnm):** `brew install fnm`, follow the shell hook in `fnm`'s install output, then in this repo run `fnm install` and `fnm use`.
- **[nvm](https://github.com/nvm-sh/nvm):** Not installed by default. Install it from their README, restart the terminal, then here run `nvm install` and `nvm use` (reads `.nvmrc`).

Install the [Mintlify CLI](https://www.npmjs.com/package/mintlify) to preview the documentation changes locally. To install, use the following command

```
npm i -g mintlify@latest
```

Run the following command at the root of your documentation (where `docs.json` is)

```
mintlify dev
```

### Publishing Changes

Install our Github App to auto propagate changes from your repo to your deployment. Changes will be deployed to production automatically after pushing to the default branch. Find the link to install on your dashboard. 

#### Troubleshooting

- **Node 25+ / “not supported on node versions 25+”** — Use Node **20 or 22** (Homebrew `node@22`, fnm, or nvm after you install it). Check `node -v` before `mintlify dev`.
- **Invalid theme `luma`** — Upgrade the CLI: `npm i -g mintlify@latest`, and ensure `which mintlify` points at that install (not an old copy under another prefix).
- Mintlify dev isn't running — Run `mintlify install` to re-install dependencies.
- Page loads as a 404 — Make sure you are running in a folder with `docs.json`.
