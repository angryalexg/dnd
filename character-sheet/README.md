# D&D Character Sheets

Interactive HTML character sheets hosted on GitHub Pages.

Live URL: `https://angryalexg.github.io/dnd/character-sheet/<character>/`

---

## Characters

| Character | Class | Sheet |
|-----------|-------|-------|
| Deb (Deborah U. Taunt) | Cleric 6 (War Domain, Aasimar) | [deb/index.html](deb/index.html) |

---

## Creating a New Character Sheet

### 1. Get the character data from D&D Beyond

Use the DDB MCP tools in Claude Code:
```
ddb_list_characters       → find your character's ID
ddb_get_character         → pull raw stat data
ddb_navigate              → scrape the full rendered sheet if needed
```

Key stats to collect:
- Ability scores and modifiers
- HP (max), AC breakdown (armor + shield), speed
- Saving throw proficiencies
- Skill proficiencies and expertise
- Spell slots per level
- Features, traits, limited-use resources (including recharge type: SR/LR)
- Spells known/prepared — note which require Concentration

### 2. Copy Deb's sheet as your starting point

```bash
cp -r deb <character-name>
```

Edit `<character-name>/index.html`:

**Required updates:**
- `<title>` — character name and class
- `.cname` div — character name
- `.pill` divs in `.meta` — class, level, race, background, alignment
- Header stat boxes (`.sb`) — Proficiency Bonus, Initiative, Speed, AC
- Ability scores — update all 6 scores and their modifiers in the Stats tab
- HP variables at top of `<script>`: `let hp=X,maxHp=X`
- `RES_MAX` object — update resource names and max charges for your character's features
- `resRem` object — must match `RES_MAX` exactly
- `ALL_RES` — auto-generated from `RES_MAX` keys, no change needed
- `armor` object — update with your character's actual armor pieces and AC values
- Saving throw proficiencies — mark with `sp` class
- Skills — add `sp` class for proficient, `se` class for expertise
- Spells tab — rebuild spell rows for your character's spell list
- Features tab — rebuild feature rows for your character's class features
- `STORE_KEY` — change to a unique string: `'dnd-<name>-<ddb-id>'`

### 3. Resource tracker setup

Each limited-use resource needs pip dots with a matching `data-res` attribute.

In HTML, a 3-pip tracker looks like:
```html
<div class="udots">
  <div class="udot" data-res="resource-name" onclick="toggleDot(this)"></div>
  <div class="udot" data-res="resource-name" onclick="toggleDot(this)"></div>
  <div class="udot" data-res="resource-name" onclick="toggleDot(this)"></div>
</div>
```

In the `<script>`, register it:
```javascript
const RES_MAX = {
  'resource-name': 3,   // max charges
  // add more...
};
const resRem = { ...same keys, same values... };
```

If a resource appears in **multiple tabs** (e.g., Combat and Features), give all its dots the same `data-res` value — they'll stay in sync automatically.

**Recharge rules** — update `shortRest()` and `resetLR()`:
- Long rest only: just include in `resetLR` loop (default behavior)
- Short rest recharge: add `resRem['resource-name'] = RES_MAX['resource-name'];` in `shortRest()`
- Short rest partial (like Channel Divinity): `resRem['cd'] = Math.min(RES_MAX['cd'], resRem['cd'] + 1);`

### 4. Concentration spells

No manual work needed. On page load, the init function automatically:
- Scans all `.sr` rows for "Conc" in the `.stag` span (excluding "no Conc")
- Adds a purple left border to those rows
- Highlights the word "Conc" in purple/bold within the tag
- Adds a "Cast" button that populates the concentration tracker at the top

Just make sure concentration spells have `Conc` somewhere in their `.stag` text.

### 5. Deploy

```bash
cd /home/deck/claude/dnd
git add character-sheet/<character-name>/
git commit -m "Add <character-name> character sheet"
git push
```

GitHub Pages serves from the `main` branch. The sheet will be live at:
`https://angryalexg.github.io/dnd/character-sheet/<character-name>/`

---

## Sheet Features

- **HP tracker** — damage/heal buttons, temp HP badge, bar with color-coded health
- **AC tracker** — toggle armor/shield pieces; header updates live
- **Concentration tracker** — shows active spell; populated via "Cast" buttons or manual entry
- **Resource pips** — click to spend/restore; synced across all tabs and browser tabs
- **Short rest / Long rest** — reset appropriate resources
- **Death saves** — appear automatically at 0 HP
- **Inspiration pip** — toggle in header
- **Dark mode** — toggle in header; preference persists
- **Spell slots** — pip dots per level; click to expend
- **Cross-tab sync** — all state persists in `localStorage` and syncs across open tabs in real time
