#!/usr/bin/env python3
"""
DnD Beyond → Character Sheet HTML Generator

Fetches your character from DnD Beyond and generates a self-contained HTML file
matching the format used in this project.

Usage:
  python3 generate_sheet.py 165996399
  python3 generate_sheet.py 165996399 --output character-sheet/mychar/index.html
  python3 generate_sheet.py 165996399 --cookie "CobaltSession=abc123"  # private chars

Requires Python 3.7+, no external dependencies.
"""

import sys
import json
import math
import re
import os
import argparse
import urllib.request
import urllib.error

# ── DnD constants ──────────────────────────────────────────────────────────────

ALIGNMENTS = {
    1: "Lawful Good", 2: "Neutral Good", 3: "Chaotic Good",
    4: "Lawful Neutral", 5: "True Neutral", 6: "Chaotic Neutral",
    7: "Lawful Evil", 8: "Neutral Evil", 9: "Chaotic Evil",
}

ABILITY_IDS = {1: "STR", 2: "DEX", 3: "CON", 4: "INT", 5: "WIS", 6: "CHA"}

SKILLS = [
    ("Acrobatics", 2), ("Animal Handling", 5), ("Arcana", 4),
    ("Athletics", 1), ("Deception", 6), ("History", 4),
    ("Insight", 5), ("Intimidation", 6), ("Investigation", 4),
    ("Medicine", 5), ("Nature", 4), ("Perception", 5),
    ("Performance", 6), ("Persuasion", 6), ("Religion", 4),
    ("Sleight of Hand", 2), ("Stealth", 2), ("Survival", 5),
]

SKILL_SUBTYPE_MAP = {
    "acrobatics": "Acrobatics", "animal-handling": "Animal Handling",
    "arcana": "Arcana", "athletics": "Athletics", "deception": "Deception",
    "history": "History", "insight": "Insight", "intimidation": "Intimidation",
    "investigation": "Investigation", "medicine": "Medicine", "nature": "Nature",
    "perception": "Perception", "performance": "Performance", "persuasion": "Persuasion",
    "religion": "Religion", "sleight-of-hand": "Sleight of Hand",
    "stealth": "Stealth", "survival": "Survival",
}

SAVE_SUBTYPE_MAP = {
    "strength-saving-throws": "STR", "dexterity-saving-throws": "DEX",
    "constitution-saving-throws": "CON", "intelligence-saving-throws": "INT",
    "wisdom-saving-throws": "WIS", "charisma-saving-throws": "CHA",
}

FULL_CASTER_SLOTS = {
    1:[2,0,0,0,0,0,0,0,0], 2:[3,0,0,0,0,0,0,0,0], 3:[4,2,0,0,0,0,0,0,0],
    4:[4,3,0,0,0,0,0,0,0], 5:[4,3,2,0,0,0,0,0,0], 6:[4,3,3,0,0,0,0,0,0],
    7:[4,3,3,1,0,0,0,0,0], 8:[4,3,3,2,0,0,0,0,0], 9:[4,3,3,3,1,0,0,0,0],
    10:[4,3,3,3,2,0,0,0,0], 11:[4,3,3,3,2,1,0,0,0], 12:[4,3,3,3,2,1,0,0,0],
    13:[4,3,3,3,2,1,1,0,0], 14:[4,3,3,3,2,1,1,0,0], 15:[4,3,3,3,2,1,1,1,0],
    16:[4,3,3,3,2,1,1,1,0], 17:[4,3,3,3,2,1,1,1,1], 18:[4,3,3,3,3,1,1,1,1],
    19:[4,3,3,3,3,2,1,1,1], 20:[4,3,3,3,3,2,2,1,1],
}

HALF_CASTER_SLOTS = {
    1:[0,0,0,0,0,0,0,0,0], 2:[2,0,0,0,0,0,0,0,0], 3:[3,0,0,0,0,0,0,0,0],
    4:[3,0,0,0,0,0,0,0,0], 5:[4,2,0,0,0,0,0,0,0], 6:[4,2,0,0,0,0,0,0,0],
    7:[4,3,0,0,0,0,0,0,0], 8:[4,3,0,0,0,0,0,0,0], 9:[4,3,2,0,0,0,0,0,0],
    10:[4,3,2,0,0,0,0,0,0], 11:[4,3,3,0,0,0,0,0,0], 12:[4,3,3,0,0,0,0,0,0],
    13:[4,3,3,1,0,0,0,0,0], 14:[4,3,3,1,0,0,0,0,0], 15:[4,3,3,2,0,0,0,0,0],
    16:[4,3,3,2,0,0,0,0,0], 17:[4,3,3,3,1,0,0,0,0], 18:[4,3,3,3,1,0,0,0,0],
    19:[4,3,3,3,2,0,0,0,0], 20:[4,3,3,3,2,0,0,0,0],
}

WARLOCK_SLOTS = {
    1:1, 2:2, 3:2, 4:2, 5:3, 6:3, 7:4, 8:4,
    9:4, 10:4, 11:3, 12:3, 13:3, 14:3, 15:3,
    16:3, 17:4, 18:4, 19:4, 20:4,
}
WARLOCK_SLOT_LEVEL = {
    1:1, 2:1, 3:2, 4:2, 5:3, 6:3, 7:4, 8:4, 9:5, 10:5,
    11:5, 12:5, 13:5, 14:5, 15:5, 16:5, 17:5, 18:5, 19:5, 20:5,
}

FULL_CASTER_CLASSES = {"Bard", "Cleric", "Druid", "Sorcerer", "Wizard"}
HALF_CASTER_CLASSES = {"Paladin", "Ranger"}
WARLOCK_CLASSES = {"Warlock"}

SPELLCASTING_ABILITY = {
    "Bard": "CHA", "Cleric": "WIS", "Druid": "WIS",
    "Paladin": "CHA", "Ranger": "WIS", "Sorcerer": "CHA",
    "Warlock": "CHA", "Wizard": "INT", "Artificer": "INT",
}

ORDINALS = ["1st","2nd","3rd","4th","5th","6th","7th","8th","9th"]

CAST_UNIT_MAP = {1:"Action", 2:"Bonus Action", 3:"Reaction", 4:"Minute", 5:"Hour", 6:"Special"}
RANGE_TYPE_MAP = {1:"Self", 2:"Touch", 4:"Sight", 5:"Unlimited", 6:"Special"}
DUR_TYPE_MAP = {1:"Instantaneous", 3:"Special", 4:"Until Dispelled"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def prof_bonus(level):
    return math.ceil(level / 4) + 1

def score_mod(score):
    return math.floor((score - 10) / 2)

def fmt_mod(m):
    return f"+{m}" if m >= 0 else str(m)

def strip_html(s):
    s = re.sub(r'<[^>]+>', '', s or '')
    return re.sub(r'\s+', ' ', s).strip()

def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def slug(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower())


# ── Character parser ──────────────────────────────────────────────────────────

class Character:
    def __init__(self, raw):
        # DDB wraps data in {"data": {...}} at the top level
        self.d = raw.get("data", raw)
        self._build()

    def _build(self):
        d = self.d
        self.name = d.get("name", "Unknown")
        self.char_id = d.get("id", 0)

        # Collect all modifiers up front
        self.all_mods = []
        for src in (d.get("modifiers") or {}).values():
            self.all_mods.extend(src or [])

        self._parse_classes()
        self._parse_race()
        self._parse_background()
        self.alignment = ALIGNMENTS.get(d.get("alignmentId"), "Unknown")
        self._parse_ability_scores()
        self._parse_proficiencies()
        self._parse_speed()
        self._parse_initiative()
        self._parse_hp()
        self._parse_senses()
        self._parse_resistances()
        self._parse_languages()
        self._parse_armor()
        self._parse_weapons()
        self._parse_spells()
        self._parse_features()
        self._parse_inventory()

    def _parse_classes(self):
        self.classes = []
        for cls in (self.d.get("classes") or []):
            cls_def = cls.get("definition") or {}
            sub_def = cls.get("subclassDefinition")
            self.classes.append({
                "name": cls_def.get("name", "Unknown"),
                "level": cls.get("level", 1),
                "subclass": (sub_def or {}).get("name"),
                "hitDice": cls_def.get("hitDice", 8),
            })
        self.total_level = sum(c["level"] for c in self.classes)
        self.prof = prof_bonus(self.total_level)

    def _parse_race(self):
        race = self.d.get("race") or {}
        self.race_name = race.get("fullName") or race.get("baseName", "Unknown")

    def _parse_background(self):
        bg = (self.d.get("background") or {})
        bg_def = (bg.get("definition") or {})
        self.background = bg_def.get("name", "Unknown")

    def _parse_ability_scores(self):
        base = {s["id"]: s.get("value") or 10 for s in (self.d.get("stats") or [])}
        bonus = {s["id"]: s.get("value") or 0 for s in (self.d.get("bonusStats") or [])}
        override = {s["id"]: s.get("value") for s in (self.d.get("overrideStats") or [])}

        racial_bonus = {}
        stat_subtype = {
            "strength-score": 1, "dexterity-score": 2, "constitution-score": 3,
            "intelligence-score": 4, "wisdom-score": 5, "charisma-score": 6,
        }
        for m in self.all_mods:
            sub = m.get("subType", "")
            if m.get("type") == "bonus" and sub in stat_subtype:
                aid = stat_subtype[sub]
                racial_bonus[aid] = racial_bonus.get(aid, 0) + (m.get("fixedValue") or m.get("value") or 0)

        self.ability_scores = {}
        for aid, aname in ABILITY_IDS.items():
            if override.get(aid) is not None:
                score = override[aid]
            else:
                score = base.get(aid, 10) + bonus.get(aid, 0) + racial_bonus.get(aid, 0)
            self.ability_scores[aname] = score

    def _parse_proficiencies(self):
        self.skill_profs = {}
        for m in self.all_mods:
            sub = m.get("subType", "")
            typ = m.get("type", "")
            if sub in SKILL_SUBTYPE_MAP:
                skill = SKILL_SUBTYPE_MAP[sub]
                if typ == "expertise":
                    self.skill_profs[skill] = "expertise"
                elif typ == "proficiency" and self.skill_profs.get(skill) != "expertise":
                    self.skill_profs[skill] = "proficiency"
                elif typ == "half-proficiency-rounded-down" and skill not in self.skill_profs:
                    self.skill_profs[skill] = "half"

        self.save_profs = set()
        for m in self.all_mods:
            sub = m.get("subType", "")
            if m.get("type") == "proficiency" and sub in SAVE_SUBTYPE_MAP:
                self.save_profs.add(SAVE_SUBTYPE_MAP[sub])

        self.armor_profs, self.weapon_profs, self.tool_profs = [], [], []
        for m in self.all_mods:
            if m.get("type") != "proficiency":
                continue
            sub = m.get("subType", "")
            name = m.get("friendlySubtypeName") or sub.replace("-", " ").title()
            if not name:
                continue
            if any(x in sub.lower() for x in ["armor", "shield"]):
                if name not in self.armor_profs:
                    self.armor_profs.append(name)
            elif any(x in sub.lower() for x in ["weapon", "martial", "simple", "firearms"]):
                if name not in self.weapon_profs:
                    self.weapon_profs.append(name)
            elif m.get("entityTypeId") and "saving" not in sub and sub not in SKILL_SUBTYPE_MAP:
                if name not in self.tool_profs:
                    self.tool_profs.append(name)

    def _parse_speed(self):
        race = self.d.get("race") or {}
        speeds = (race.get("weightSpeeds") or {}).get("normal") or {}
        self.speed = speeds.get("walk", 30)
        for m in self.all_mods:
            if m.get("type") == "bonus" and m.get("subType") == "speed":
                self.speed += (m.get("fixedValue") or m.get("value") or 0)

    def _parse_initiative(self):
        self.initiative = score_mod(self.ability_scores.get("DEX", 10))
        for m in self.all_mods:
            if m.get("type") in ("bonus",) and m.get("subType") == "initiative":
                self.initiative += (m.get("fixedValue") or m.get("value") or 0)

    def _parse_hp(self):
        hp_info = self.d.get("hitPointInfo") or {}
        if hp_info.get("override"):
            self.max_hp = hp_info["override"]
        else:
            self.max_hp = self._calc_max_hp()
        removed = self.d.get("removedHitPoints") or 0
        self.current_hp = self.max_hp - removed

    def _calc_max_hp(self):
        con_bonus = score_mod(self.ability_scores.get("CON", 10))
        total = 0
        for cls in self.classes:
            hd = cls["hitDice"]
            lvl = cls["level"]
            total += hd + con_bonus
            avg = math.floor(hd / 2) + 1
            total += (lvl - 1) * (avg + con_bonus)
        for m in self.all_mods:
            if m.get("type") == "bonus":
                sub = m.get("subType", "")
                if sub == "hit-points-per-level":
                    total += (m.get("fixedValue") or m.get("value") or 0) * self.total_level
                elif sub == "hit-points":
                    total += (m.get("fixedValue") or m.get("value") or 0)
        return max(1, total)

    def _parse_senses(self):
        self.darkvision = 0
        for m in self.all_mods:
            sub = m.get("subType", "")
            typ = m.get("type", "")
            if "darkvision" in sub:
                val = m.get("fixedValue") or m.get("value") or 60
                self.darkvision = max(self.darkvision, val)

    def _parse_resistances(self):
        self.resistances, self.immunities, self.vulnerabilities = [], [], []
        for m in self.all_mods:
            typ = m.get("type", "")
            name = (m.get("friendlySubtypeName") or m.get("subType", "")).replace("-", " ").title()
            if not name:
                continue
            if typ == "resistance" and name not in self.resistances:
                self.resistances.append(name)
            elif typ == "immunity" and name not in self.immunities:
                self.immunities.append(name)
            elif typ == "vulnerability" and name not in self.vulnerabilities:
                self.vulnerabilities.append(name)

    def _parse_languages(self):
        self.languages = []
        for m in self.all_mods:
            if m.get("type") == "language":
                name = (m.get("friendlySubtypeName") or m.get("subType", "")).title()
                if name and name not in self.languages:
                    self.languages.append(name)

    def _parse_armor(self):
        self.armor_pieces = []
        dex = score_mod(self.ability_scores.get("DEX", 10))

        # Check for Unarmored Defense ability bonuses
        unarmored_add = 0
        for m in self.all_mods:
            if m.get("subType") == "unarmored-armor-class":
                aid = m.get("statId")
                if aid and aid in ABILITY_IDS:
                    unarmored_add += score_mod(self.ability_scores.get(ABILITY_IDS[aid], 10))

        for item in (self.d.get("inventory") or []):
            defn = item.get("definition") or {}
            if not item.get("equipped"):
                continue
            ftype = defn.get("filterType", "")
            itype = defn.get("type", "")
            if ftype != "Armor" and itype != "Armor":
                continue

            name = defn.get("name", "Unknown")
            base_ac = defn.get("armorClass") or 0
            armor_type = defn.get("armorTypeId") or 0
            magic_bonus = defn.get("magicBonus") or 0

            is_shield = armor_type == 4 or "shield" in name.lower()
            piece_id = slug(name) or "armor"

            if is_shield:
                self.armor_pieces.append({
                    "id": "shield", "name": name,
                    "ac": base_ac + magic_bonus,
                    "type": "shield", "equipped": True,
                })
            else:
                if armor_type == 1:    # Light — full DEX
                    dex_add = dex
                elif armor_type == 2:  # Medium — max +2 DEX
                    dex_add = min(2, dex)
                else:                  # Heavy — no DEX
                    dex_add = 0
                self.armor_pieces.append({
                    "id": piece_id, "name": name,
                    "ac": base_ac + magic_bonus + dex_add,
                    "type": "armor", "equipped": True,
                })

        base_armor = [a for a in self.armor_pieces if a["type"] == "armor"]
        shield = next((a for a in self.armor_pieces if a["type"] == "shield"), None)
        if base_armor:
            self.ac = base_armor[0]["ac"] + (shield["ac"] if shield else 0)
        else:
            self.ac = 10 + dex + unarmored_add + (shield["ac"] if shield else 0)

    def _parse_weapons(self):
        self.weapons = []
        for item in (self.d.get("inventory") or []):
            defn = item.get("definition") or {}
            if not item.get("equipped"):
                continue
            if defn.get("filterType") != "Weapon" and defn.get("type") != "Weapon":
                continue

            name = defn.get("name", "Unknown")
            props = [p.get("name", "") for p in (defn.get("properties") or [])]
            is_ranged = defn.get("attackType") == 2
            is_finesse = "Finesse" in props

            if is_finesse:
                str_m = score_mod(self.ability_scores.get("STR", 10))
                dex_m = score_mod(self.ability_scores.get("DEX", 10))
                ability = "STR" if str_m >= dex_m else "DEX"
            elif is_ranged:
                ability = "DEX"
            else:
                ability = "STR"

            ab_mod = score_mod(self.ability_scores.get(ability, 10))
            magic = defn.get("magicBonus") or 0
            hit = ab_mod + self.prof + magic

            dmg = defn.get("damage") or {}
            dc = dmg.get("diceCount", 1)
            dv = dmg.get("diceValue", 4)
            dtype = (dmg.get("damageType") or {}).get("name", "")
            db = ab_mod + magic

            notes = []
            if "Versatile" in props:
                vd = defn.get("versatileDamage") or {}
                if vd:
                    notes.append(f"Versatile {vd.get('diceCount',1)}d{vd.get('diceValue',8)}+{ab_mod}")
            if is_ranged:
                nr = defn.get("range", 20)
                lr = defn.get("longRange", 60)
                notes.append(f"Range {nr}/{lr}")
            if "Loading" in props:
                notes.append("Loading")

            self.weapons.append({
                "name": name, "hit": hit,
                "damage": f"{dc}d{dv}+{db}" if db >= 0 else f"{dc}d{dv}{db}",
                "damage_type": dtype,
                "notes": ", ".join(notes),
            })

    def _parse_spells(self):
        self.spell_slots = [0] * 9
        self.cantrips = []
        self.spells_by_level = {i: [] for i in range(1, 10)}

        # Calculate spell slots
        is_warlock = False
        warlock_level = 0
        for cls in self.classes:
            cname = cls["name"]
            lvl = cls["level"]
            if cname in FULL_CASTER_CLASSES:
                for i, s in enumerate(FULL_CASTER_SLOTS.get(lvl, [0]*9)):
                    self.spell_slots[i] = max(self.spell_slots[i], s)
            elif cname in HALF_CASTER_CLASSES:
                for i, s in enumerate(HALF_CASTER_SLOTS.get(lvl, [0]*9)):
                    self.spell_slots[i] = max(self.spell_slots[i], s)
            elif cname in WARLOCK_CLASSES:
                is_warlock = True
                warlock_level = lvl

        if is_warlock and warlock_level:
            slot_count = WARLOCK_SLOTS.get(warlock_level, 2)
            slot_level = WARLOCK_SLOT_LEVEL.get(warlock_level, 1)
            self.spell_slots[slot_level - 1] = max(self.spell_slots[slot_level - 1], slot_count)

        # Collect always-prepared domain spell IDs
        domain_ids = set()
        for cls in (self.d.get("classes") or []):
            sub = cls.get("subclassDefinition") or {}
            for feat in (sub.get("classFeatures") or []):
                for s in (feat.get("spells") or []):
                    sid = (s.get("definition") or {}).get("id") or s.get("id")
                    if sid:
                        domain_ids.add(sid)

        # Gather all spells from all sources
        seen_ids = set()
        all_spells = []
        for cs in (self.d.get("classSpells") or []):
            for s in (cs.get("spells") or []):
                all_spells.append((s, False))
        for src_key, src_list in (self.d.get("spells") or {}).items():
            for s in (src_list or []):
                defn = s.get("definition") or {}
                is_domain = defn.get("id") in domain_ids
                all_spells.append((s, is_domain))

        for spell, is_domain in all_spells:
            defn = spell.get("definition") or {}
            sid = defn.get("id")
            if not sid or sid in seen_ids:
                continue
            seen_ids.add(sid)

            level = defn.get("level", 0)
            name = defn.get("name", "Unknown")
            school = (defn.get("school") or "").capitalize()

            activation = defn.get("activation") or {}
            cast_count = activation.get("activationTime", 1)
            cast_type = activation.get("activationType", 1)
            cast_unit = CAST_UNIT_MAP.get(cast_type, "Action")
            casting_time = f"{cast_count} {cast_unit}" if cast_count != 1 else cast_unit

            range_info = defn.get("range") or {}
            range_type = range_info.get("rangeType", 0)
            range_dist = range_info.get("rangeValue", 0)
            if range_type in RANGE_TYPE_MAP:
                range_str = RANGE_TYPE_MAP[range_type]
            else:
                range_str = f"{range_dist}ft"

            dur = defn.get("duration") or {}
            dur_type = dur.get("durationType", 1)
            dur_val = dur.get("durationInterval", 0)
            dur_unit = dur.get("durationUnit", "")
            conc = bool(defn.get("requiresConcentration"))
            ritual = bool(defn.get("ritual"))

            if conc:
                dur_str = f"Conc {dur_val} {dur_unit}".strip() if dur_val else "Conc 1 min"
            elif dur_type in DUR_TYPE_MAP:
                dur_str = DUR_TYPE_MAP[dur_type]
            else:
                dur_str = f"{dur_val} {dur_unit}".strip() if dur_val else "1 Round"

            tags = []
            if conc:
                tags.append("Conc")
            if ritual:
                tags.append("Ritual")

            desc = strip_html(defn.get("description", "") or "")
            if len(desc) > 600:
                desc = desc[:600] + "…"

            higher = (defn.get("atHigherLevels") or {}).get("higherLevelDefinitions") or []
            if higher:
                higher_text = strip_html(higher[0].get("details", "") or "")
                if higher_text:
                    desc += f" At Higher Levels: {higher_text}"

            always_prep = is_domain or spell.get("alwaysPrepared", False)

            components = defn.get("components") or []
            comp_str = ("V" if 1 in components else "") + ("S" if 2 in components else "") + ("M" if 3 in components else "")

            info = {
                "id": sid, "name": name, "level": level, "school": school,
                "casting_time": casting_time, "range": range_str, "duration": dur_str,
                "concentration": conc, "ritual": ritual, "components": comp_str,
                "tags": tags, "description": desc, "always_prepared": always_prep,
            }

            if level == 0:
                self.cantrips.append(info)
            elif 1 <= level <= 9:
                self.spells_by_level[level].append(info)

        self.cantrips.sort(key=lambda s: s["name"])
        for lvl in range(1, 10):
            self.spells_by_level[lvl].sort(key=lambda s: (not s["always_prepared"], s["name"]))

    def _parse_features(self):
        self.racial_traits = []
        self.class_features = []
        self.feats = []

        race = self.d.get("race") or {}
        for trait in (race.get("racialTraits") or []):
            defn = trait.get("definition") or {}
            desc = strip_html(defn.get("description", "") or "")
            if len(desc) > 400: desc = desc[:400] + "…"
            self.racial_traits.append({"name": defn.get("name", "?"), "description": desc})

        for cls_data in (self.d.get("classes") or []):
            cls_def = cls_data.get("definition") or {}
            sub_def = cls_data.get("subclassDefinition") or {}
            cls_level = cls_data.get("level", 1)
            all_feats = list(cls_def.get("classFeatures") or []) + list(sub_def.get("classFeatures") or [])
            for feat in all_feats:
                if feat.get("requiredLevel", 1) > cls_level:
                    continue
                desc = strip_html(feat.get("description", "") or "")
                if len(desc) > 500: desc = desc[:500] + "…"
                name = feat.get("name", "?")
                if not any(f["name"] == name for f in self.class_features):
                    self.class_features.append({"name": name, "description": desc})

        for feat_data in (self.d.get("feats") or []):
            defn = feat_data.get("definition") or {}
            desc = strip_html(defn.get("description", "") or "")
            if len(desc) > 500: desc = desc[:500] + "…"
            self.feats.append({"name": defn.get("name", "?"), "description": desc})

    def _parse_inventory(self):
        self.gear_items = []
        currencies = self.d.get("currencies") or {}
        self.currency = {
            "gp": currencies.get("gp", 0),
            "sp": currencies.get("sp", 0),
            "cp": currencies.get("cp", 0),
            "pp": currencies.get("pp", 0),
            "ep": currencies.get("ep", 0),
        }
        for item in (self.d.get("inventory") or []):
            defn = item.get("definition") or {}
            ftype = defn.get("filterType", "")
            if ftype in ("Weapon", "Armor"):
                continue
            name = defn.get("name", "")
            qty = item.get("quantity", 1)
            if name:
                self.gear_items.append({"name": name, "qty": qty})

    def get_skill_bonus(self, skill_name, ability_id):
        ability = ABILITY_IDS[ability_id]
        base = score_mod(self.ability_scores.get(ability, 10))
        prof_type = self.skill_profs.get(skill_name)
        if prof_type == "expertise":
            return base + self.prof * 2
        elif prof_type == "proficiency":
            return base + self.prof
        elif prof_type == "half":
            return base + math.floor(self.prof / 2)
        return base

    def get_save_bonus(self, ability):
        base = score_mod(self.ability_scores.get(ability, 10))
        return base + (self.prof if ability in self.save_profs else 0)

    def is_caster(self):
        return any(self.spell_slots) or bool(self.cantrips)

    def get_spell_ability(self):
        for cls in self.classes:
            if cls["name"] in SPELLCASTING_ABILITY:
                return SPELLCASTING_ABILITY[cls["name"]]
        return None

    def get_spell_attack_bonus(self):
        ab = self.get_spell_ability()
        return score_mod(self.ability_scores.get(ab, 10)) + self.prof if ab else 0

    def get_spell_save_dc(self):
        ab = self.get_spell_ability()
        return 8 + score_mod(self.ability_scores.get(ab, 10)) + self.prof if ab else 8


# ── HTML generation ───────────────────────────────────────────────────────────

CSS = """\
:root{--gold:#8B6914;--gold-l:#c9a84c;--gold-p:#f5e9c8;--bg:#faf8f3;--card:#fff;--sec:#f5f2ea;--ink:#1a1a18;--ink2:#6b6860;--bd:rgba(0,0,0,0.12);--r:8px;--green:#1D9E75;--purple:#534AB7;--red:#D85A30;--amber:#BA7517;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--ink);font-size:14px;}
.sheet{max-width:960px;margin:0 auto;padding:16px;}
.hdr{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:start;margin-bottom:12px;padding-bottom:12px;border-bottom:2px solid var(--gold-l);}
.cname{font-size:22px;font-weight:700;}
.meta{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px;}
.pill{font-size:11px;background:var(--sec);border:0.5px solid var(--bd);border-radius:20px;padding:2px 9px;color:var(--ink2);}
.pill b{font-weight:700;color:var(--ink);}
.hdr-r{display:flex;flex-direction:column;gap:7px;align-items:flex-end;}
.srow{display:flex;gap:7px;}
.sb{text-align:center;background:var(--card);border:0.5px solid var(--bd);border-radius:var(--r);padding:6px 12px;min-width:58px;}
.sb .v{font-size:18px;font-weight:700;}.sb .l{font-size:9px;color:var(--ink2);text-transform:uppercase;letter-spacing:.5px;margin-top:1px;}
.hp-box{background:var(--card);border:0.5px solid var(--bd);border-radius:var(--r);padding:10px 14px;margin-bottom:12px;}
.hp-top{display:flex;align-items:center;gap:12px;margin-bottom:8px;}
.hp-nums{display:flex;align-items:baseline;gap:3px;}
.hp-cur{font-size:30px;font-weight:700;min-width:38px;text-align:center;}
.hp-sep{font-size:20px;color:var(--ink2);}.hp-max{font-size:20px;color:var(--ink2);}
.hp-lbl{font-size:9px;color:var(--ink2);text-transform:uppercase;letter-spacing:.4px;}
.hp-bar-wrap{flex:1;background:var(--sec);border-radius:4px;height:7px;overflow:hidden;}
.hp-bar{height:7px;border-radius:4px;background:var(--green);transition:width .25s,background .25s;}
.hp-pct{font-size:11px;color:var(--ink2);min-width:34px;text-align:right;}
.hp-controls{display:flex;gap:6px;align-items:center;flex-wrap:wrap;}
.hp-controls input{width:70px;padding:5px 7px;font-size:13px;border:0.5px solid var(--bd);border-radius:var(--r);background:var(--card);color:var(--ink);font-family:inherit;}
.btn{font-size:12px;padding:5px 11px;border:0.5px solid var(--bd);border-radius:var(--r);cursor:pointer;background:transparent;color:var(--ink);font-family:inherit;}
.btn:hover{background:var(--sec);}
.btn-dmg{border-color:var(--red);color:var(--red);}
.btn-heal{border-color:var(--green);color:var(--green);}
.btn-sr{border-color:var(--amber);color:var(--amber);}
.btn-sm{font-size:11px;padding:4px 8px;color:var(--ink2);}
.tabs{display:flex;gap:4px;margin-bottom:12px;flex-wrap:wrap;}
.tab{font-size:12px;padding:5px 13px;border:0.5px solid var(--bd);border-radius:20px;cursor:pointer;background:transparent;color:var(--ink2);font-family:inherit;}
.tab.active,.tab:hover{background:var(--gold);color:#fff;border-color:var(--gold);}
.panel{display:none;}.panel.active{display:block;animation:panelIn .18s ease;}
@keyframes panelIn{from{opacity:0;transform:translateX(12px)}to{opacity:1;transform:translateX(0)}}
.grid2{display:grid;grid-template-columns:minmax(0,200px) minmax(0,1fr);gap:10px;}
.grid2x{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px;}
.col{display:flex;flex-direction:column;gap:8px;}
.sec{background:var(--card);border:0.5px solid var(--bd);border-radius:var(--r);padding:9px;}
.sec-t{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.9px;color:var(--gold);margin-bottom:7px;border-bottom:.5px solid var(--bd);padding-bottom:4px;}
.ab6{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;}
.ab{background:var(--sec);border-radius:6px;padding:5px 3px;text-align:center;}
.abm{font-size:15px;font-weight:700;}.abs{font-size:11px;color:var(--ink2);margin-top:1px;}.abn{font-size:9px;color:var(--ink2);text-transform:uppercase;letter-spacing:.3px;margin-top:1px;}
.pos{color:var(--green);}.neg{color:var(--red);}
.sg{background:var(--sec);border-radius:6px;padding:6px 7px;margin-bottom:4px;}
.sg-h{font-size:10px;font-weight:700;color:var(--gold);margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px;}
.sk{display:flex;align-items:center;gap:5px;font-size:12px;padding:1px 0;}
.dot{width:7px;height:7px;border-radius:50%;border:1.5px solid var(--bd);flex-shrink:0;}
.dot.p{background:var(--gold);border-color:var(--gold);}
.skn{flex:1;color:var(--ink2);}.skv{font-weight:700;color:var(--ink);}
.sk-note{font-size:10px;color:var(--purple);font-style:italic;}
.sk-bonus{font-size:10px;color:var(--gold);margin-left:3px;}
.sk.hi .skn{color:var(--green);font-weight:700;}.sk.hi .skv{color:var(--green);}
.prow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;}
.pbox{background:var(--sec);border-radius:6px;padding:5px;text-align:center;}
.pv{font-size:16px;font-weight:700;}.pl{font-size:9px;color:var(--ink2);text-transform:uppercase;}
.ut{background:var(--sec);border-radius:6px;padding:7px 9px;margin-bottom:5px;}
.ut-top{display:flex;align-items:center;gap:7px;margin-bottom:4px;}
.ut-name{font-size:12px;font-weight:700;flex:1;}
.badge{font-size:10px;padding:1px 7px;border-radius:3px;font-weight:600;}
.b-lr{background:#EEEDFE;color:var(--purple);}
.b-sr{background:#E1F5EE;color:#0F6E56;}
.b-free{background:#EAF3DE;color:#3B6D11;}
.udots{display:flex;gap:5px;flex-wrap:wrap;}
.udot{width:13px;height:13px;border-radius:50%;background:var(--gold-l);cursor:pointer;border:none;transition:opacity .15s;flex-shrink:0;}
.udot.used{opacity:.18;background:var(--ink2);}
.ut-desc{font-size:11px;color:var(--ink2);line-height:1.5;}
.wtb{width:100%;border-collapse:collapse;font-size:12px;}
.wtb th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--ink2);padding:4px 6px;border-bottom:.5px solid var(--bd);font-weight:700;}
.wtb td{padding:5px 6px;border-bottom:.5px solid rgba(0,0,0,.05);}
.hbadge{background:var(--sec);border:.5px solid var(--bd);border-radius:4px;padding:2px 6px;font-weight:700;}
.slot-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-bottom:10px;}
.slot-box{text-align:center;background:var(--sec);border-radius:6px;padding:7px;}
.slot-lbl{font-size:10px;color:var(--ink2);text-transform:uppercase;}
.slot-n{font-size:14px;font-weight:700;}
.sdots{display:flex;justify-content:center;gap:4px;margin-top:5px;}
.sdot{width:11px;height:11px;border-radius:50%;background:var(--gold-l);cursor:pointer;border:none;transition:opacity .15s;}
.sdot.used{opacity:.18;background:var(--ink2);}
.sl-lbl{font-size:11px;font-weight:700;color:var(--ink2);padding:5px 0 3px;}
.sr{display:flex;align-items:center;gap:7px;font-size:12px;padding:5px 7px;border-radius:5px;background:var(--sec);margin-bottom:3px;cursor:pointer;transition:background .1s;user-select:none;}
.sr:hover,.sr.open{background:var(--gold-p);}
.sr.open{border-radius:5px 5px 0 0;margin-bottom:0;}
.sr.aw{border-left:2px solid var(--gold);}
.slvl{font-size:10px;background:var(--card);border:.5px solid var(--bd);border-radius:3px;padding:1px 5px;min-width:20px;text-align:center;color:var(--ink2);}
.sn{flex:1;font-weight:600;}.stag{font-size:10px;color:var(--ink2);}
.sarr{font-size:10px;color:var(--ink2);margin-left:3px;transition:transform .15s;}
.sr.open .sarr{transform:rotate(90deg);}
.sd{display:none;font-size:11px;color:var(--ink2);line-height:1.6;padding:7px 9px;background:var(--gold-p);border-radius:0 0 5px 5px;margin-bottom:3px;border-left:2px solid var(--gold-l);}
.sd.open{display:block;}
.sdm{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:5px;}
.sdm span{font-size:10px;background:rgba(139,105,20,.12);border-radius:3px;padding:2px 6px;color:var(--gold);font-weight:700;}
.ft{padding:7px 9px;background:var(--sec);border-radius:6px;margin-bottom:5px;}
.ftn{font-size:12px;font-weight:700;}.ftd{font-size:11px;color:var(--ink2);margin-top:3px;line-height:1.55;}
.util-card{background:var(--card);border:.5px solid var(--bd);border-radius:var(--r);padding:9px;margin-bottom:8px;}
.util-hdr{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--gold);margin-bottom:7px;padding-bottom:4px;border-bottom:.5px solid var(--bd);}
.utool{padding:5px 7px;border-radius:5px;margin-bottom:3px;cursor:pointer;border:.5px solid transparent;}
.utool:hover,.utool.open{background:var(--sec);border-color:var(--bd);}
.utool-hdr{display:flex;align-items:center;gap:6px;}
.utool-name{font-size:12px;font-weight:700;flex:1;}
.utool-arr{font-size:10px;color:var(--ink2);transition:transform .15s;}
.utool.open .utool-arr{transform:rotate(90deg);}
.utool-desc{display:none;font-size:11px;color:var(--ink2);line-height:1.55;margin-top:5px;padding-top:5px;border-top:.5px solid var(--bd);}
.utool.open .utool-desc{display:block;}
.armor-slot{cursor:pointer;background:var(--sec);border:2px solid var(--gold);border-radius:var(--r);padding:9px;text-align:center;}
@media(max-width:600px){.grid2,.grid2x{grid-template-columns:1fr;}.hdr{grid-template-columns:1fr;}.ab6{grid-template-columns:repeat(3,1fr);}.slot-grid{grid-template-columns:1fr 1fr 1fr;}}
body.dark{--bg:#1b1917;--card:#242220;--sec:#2d2b28;--ink:#e8e4da;--ink2:#9b9890;--bd:rgba(255,255,255,0.1);--gold:#c9a84c;--gold-l:#4a3808;--gold-p:#2a2008;--green:#18a06b;--purple:#7c73d4;--red:#d96040;--amber:#c98a20;}
body.dark .hp-bar{background:#18a06b;}
body.dark .hbadge{background:var(--sec);}
body.dark .sr:hover,body.dark .sr.open{background:var(--gold-p);}
body.dark .sd,body.dark .sr.open{border-color:var(--gold-l);}
body.dark .utool:hover,body.dark .utool.open{background:var(--gold-p);}
.sr.conc-spell{border-left:2px solid var(--purple);}
.conc-cast{font-size:10px;padding:2px 6px;border-radius:3px;border:1px solid var(--purple);color:var(--purple);background:transparent;cursor:pointer;margin-right:4px;white-space:nowrap;flex-shrink:0;}
.conc-cast:hover{background:rgba(83,74,183,0.12);}
.stag .ci{color:var(--purple);font-weight:700;}
.dark-btn{font-size:18px;background:none;border:none;cursor:pointer;padding:2px 4px;line-height:1;border-radius:4px;}
.dark-btn:hover{background:var(--sec);}
.tmp-badge{display:none;font-size:13px;font-weight:700;color:var(--purple);background:rgba(83,74,183,0.12);border:1.5px solid var(--purple);border-radius:6px;padding:2px 8px;margin-left:6px;align-items:baseline;gap:3px;}
.tmp-badge.visible{display:inline-flex;}
.conc-box{background:var(--card);border:0.5px solid var(--bd);border-radius:var(--r);padding:8px 12px;margin-bottom:10px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.conc-label{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--purple);flex-shrink:0;}
.conc-input{flex:1;min-width:120px;font-size:13px;border:none;background:transparent;color:var(--ink);font-family:inherit;outline:none;}
.conc-input::placeholder{color:var(--ink2);}
.conc-clear{font-size:11px;color:var(--ink2);background:none;border:none;cursor:pointer;padding:2px 5px;}
.ds-box{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:8px;padding-top:8px;border-top:.5px solid var(--bd);}
.ds-label{font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:var(--ink2);flex-shrink:0;}
.ds-group{display:flex;gap:5px;align-items:center;}
.ds-dot{width:14px;height:14px;border-radius:50%;border:1.5px solid var(--bd);background:transparent;cursor:pointer;flex-shrink:0;}
.ds-dot.suc{background:var(--green);border-color:var(--green);}
.ds-dot.fail{background:var(--red);border-color:var(--red);}
.insp-pip{width:16px;height:16px;border-radius:50%;background:transparent;border:2px solid var(--gold-l);cursor:pointer;transition:background .15s;flex-shrink:0;}
.insp-pip.active{background:var(--gold-l);}
.char-notes{width:100%;min-height:90px;font-size:11px;line-height:1.6;border:.5px solid var(--bd);border-radius:6px;background:var(--sec);color:var(--ink);font-family:inherit;padding:7px 9px;resize:vertical;outline:none;}
.char-notes::placeholder{color:var(--ink2);}
.char-notes:focus{border-color:var(--gold);}
.cond-box{background:var(--card);border:0.5px solid var(--bd);border-radius:var(--r);padding:8px 12px;margin-bottom:10px;}
.cond-row{display:flex;flex-wrap:wrap;gap:5px;align-items:center;}
.cond-lbl{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--ink2);flex-shrink:0;margin-right:3px;}
.cond{font-size:10px;padding:2px 9px;border-radius:20px;border:1px solid var(--bd);color:var(--ink2);cursor:pointer;user-select:none;transition:all .15s;background:transparent;}
.cond.active{background:var(--red);border-color:var(--red);color:#fff;font-weight:700;}
.res-pill{font-size:10px;padding:2px 9px;border-radius:20px;background:rgba(29,158,117,0.12);border:1px solid var(--green);color:var(--green);}
.imm-pill{font-size:10px;padding:2px 9px;border-radius:20px;background:rgba(83,74,183,0.12);border:1px solid var(--purple);color:var(--purple);}
"""

JS_ENGINE = """\
function getState(){try{return JSON.parse(localStorage.getItem(STORE_KEY))||{};}catch(e){return {};}}
function renderRes(res){
  const rem=resRem[res];const groups=new Map();
  document.querySelectorAll('.udot[data-res="'+res+'"]').forEach(dot=>{
    const c=dot.closest('.udots');if(!groups.has(c))groups.set(c,[]);groups.get(c).push(dot);
  });
  groups.forEach(dots=>dots.forEach((d,i)=>d.classList.toggle('used',i>=rem)));
}
function renderAllRes(){ALL_RES.forEach(r=>renderRes(r));}
function toggleCond(el){el.classList.toggle('active');saveState();}
function saveState(){
  const s=getState();const res={};ALL_RES.forEach(r=>res[r]=resRem[r]);s.res=res;
  const sdots={};document.querySelectorAll('.sdot').forEach((d,i)=>sdots['s'+i]=d.classList.contains('used'));s.sdots=sdots;
  const conds={};document.querySelectorAll('.cond').forEach((c,i)=>conds['c'+i]=c.classList.contains('active'));s.conds=conds;
  s.hp=hp;s.tmp=tmp;s.ds=dsState;localStorage.setItem(STORE_KEY,JSON.stringify(s));
}
function loadState(){
  const s=getState();
  if(s.res)ALL_RES.forEach(r=>{if(s.res[r]!==undefined)resRem[r]=s.res[r];});
  renderAllRes();
  if(s.sdots)document.querySelectorAll('.sdot').forEach((d,i)=>{if(s.sdots['s'+i]!==undefined)d.classList.toggle('used',s.sdots['s'+i]);});
  if(s.conds)document.querySelectorAll('.cond').forEach((c,i)=>{if(s.conds['c'+i])c.classList.add('active');});
  if(s.hp!==undefined)hp=s.hp;if(s.tmp!==undefined)tmp=s.tmp;
}
window.addEventListener('storage',e=>{if(e.key===STORE_KEY){loadState();upd();}});
function toggleDot(el){
  const res=el.dataset.res;
  if(res){
    const rem=resRem[res];const max=RES_MAX[res];
    const dots=Array.from(el.closest('.udots').querySelectorAll('.udot[data-res="'+res+'"]'));
    const pipIdx=dots.indexOf(el);
    resRem[res]=pipIdx<rem?Math.max(0,rem-1):Math.min(max,rem+1);renderRes(res);
  }else{el.classList.toggle('used');}
  saveState();
}
function toggleDark(){
  const dark=document.body.classList.toggle('dark');
  document.getElementById('darkBtn').textContent=dark?'\\u2600\\uFE0F':'\\uD83C\\uDF19';
  const s=getState();s.dark=dark;localStorage.setItem(STORE_KEY,JSON.stringify(s));
}
function toggleArmor(id){
  armor[id].equipped=!armor[id].equipped;
  const slot=document.getElementById('slot-'+id);const eq=armor[id].equipped;
  slot.style.borderColor=eq?'var(--gold)':'transparent';
  slot.querySelector('[data-eq]').textContent=eq?'Equipped':'Not equipped';
  slot.querySelector('[data-eq]').style.color=eq?'var(--green)':'var(--ink2)';
  updateAC();
}
function updateAC(){
  let base=10,parts=[];
  const keys=Object.keys(armor);
  const baseArmor=keys.filter(k=>k!=='shield'&&armor[k].equipped);
  if(baseArmor.length){const k=baseArmor[0];base=armor[k].ac;parts.push(armor[k].name+' ('+base+')');}
  else parts.push('Unarmored ('+base+')');
  let shieldAC=0;
  if(armor.shield&&armor.shield.equipped){shieldAC=armor.shield.ac;parts.push('Shield (+'+shieldAC+')');}
  const total=base+shieldAC;
  document.getElementById('acDisplay').textContent=total;
  document.getElementById('acHeader').textContent=total;
  document.getElementById('acNoShield').textContent=base;
  document.getElementById('acBreakdown').innerHTML=parts.join(' + ')+' = <b style="color:var(--ink);">'+total+'</b>';
}
function upd(){
  const c=Math.max(0,Math.min(maxHp,hp));
  document.getElementById('hpCur').textContent=c;
  const pct=maxHp>0?Math.round((c/maxHp)*100):0;
  document.getElementById('hpPct').textContent=pct+'%';
  const bar=document.getElementById('hpBar');
  bar.style.width=pct+'%';bar.style.background=pct>50?'#1D9E75':pct>25?'#BA7517':'#D85A30';
  const badge=document.getElementById('tmpBadge');
  if(tmp>0){badge.classList.add('visible');document.getElementById('tmpVal').textContent=tmp;}
  else badge.classList.remove('visible');
  document.getElementById('deathSaves').style.display=c===0?'flex':'none';
}
function getAmt(){return Math.abs(parseInt(document.getElementById('hpAmt').value)||0);}
function clearAmt(){document.getElementById('hpAmt').value='';}
function applyDmg(){const a=getAmt();if(!a)return;let r=a;if(tmp>0){const ab=Math.min(tmp,r);tmp-=ab;r-=ab;}hp=Math.max(0,hp-r);clearAmt();upd();saveState();}
function applyHeal(){const a=getAmt();if(!a)return;hp=Math.min(maxHp,hp+a);clearAmt();upd();saveState();}
function setTmp(){const v=parseInt(prompt('Set Temp HP (current: '+tmp+'):','0'));if(!isNaN(v))tmp=Math.max(0,v);upd();saveState();}
function resetLR(){
  hp=maxHp;tmp=0;ALL_RES.forEach(r=>{resRem[r]=RES_MAX[r];});renderAllRes();
  document.querySelectorAll('.sdot').forEach(d=>d.classList.remove('used'));
  clearDS();clearConc();upd();saveState();
}
function shortRest(){
  // Add short-rest resource recharges here if needed
  renderAllRes();saveState();
}
function castConc(name){document.getElementById('concSpell').value=name;saveConc();}
function saveConc(){const s=getState();s.conc=document.getElementById('concSpell').value;localStorage.setItem(STORE_KEY,JSON.stringify(s));}
function clearConc(){document.getElementById('concSpell').value='';saveConc();}
function saveNotes(){const s=getState();s.notes=document.getElementById('charNotes').value;localStorage.setItem(STORE_KEY,JSON.stringify(s));}
const dsState={s:[false,false,false],f:[false,false,false]};
function toggleDS(type,idx){
  dsState[type][idx]=!dsState[type][idx];
  const el=document.getElementById('ds-'+type+idx);
  el.classList.toggle(type==='s'?'suc':'fail',dsState[type][idx]);saveState();
}
function clearDS(){
  ['s','f'].forEach(t=>[0,1,2].forEach(i=>{dsState[t][i]=false;const el=document.getElementById('ds-'+t+i);if(el)el.classList.remove('suc','fail');}));saveState();
}
let inspired=false;
function toggleInspiration(){
  inspired=!inspired;document.getElementById('inspPip').classList.toggle('active',inspired);
  const s=getState();s.inspired=inspired;localStorage.setItem(STORE_KEY,JSON.stringify(s));
}
function showTab(id,btn){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById(id).classList.add('active');btn.classList.add('active');
}
function ts(row){
  const desc=row.nextElementSibling;const was=row.classList.contains('open');
  document.querySelectorAll('.sr.open').forEach(r=>{r.classList.remove('open');if(r.nextElementSibling)r.nextElementSibling.classList.remove('open');});
  if(!was){row.classList.add('open');desc.classList.add('open');}
}
(function init(){
  const s=getState();
  if(s.dark){document.body.classList.add('dark');document.getElementById('darkBtn').textContent='\\u2600\\uFE0F';}
  loadState();
  if(s.conc)document.getElementById('concSpell').value=s.conc;
  if(s.notes)document.getElementById('charNotes').value=s.notes;
  if(s.inspired){inspired=true;document.getElementById('inspPip').classList.add('active');}
  if(s.ds){['s','f'].forEach(t=>[0,1,2].forEach(i=>{if(s.ds[t]&&s.ds[t][i]){dsState[t][i]=true;const el=document.getElementById('ds-'+t+i);if(el)el.classList.add(t==='s'?'suc':'fail');}}));}
  document.querySelectorAll('.sr').forEach(row=>{
    const stag=row.querySelector('.stag');if(!stag)return;
    const txt=stag.textContent;if(!/\\bConc\\b/.test(txt)||/\\bno Conc\\b/.test(txt))return;
    row.classList.add('conc-spell');
    stag.innerHTML=stag.innerHTML.replace(/Conc/g,'<span class="ci">Conc</span>');
    const nameEl=row.querySelector('.sn');if(!nameEl)return;
    const spellName=nameEl.textContent.trim();
    const btn=document.createElement('button');btn.className='conc-cast';btn.textContent='Cast';
    btn.onclick=function(e){e.stopPropagation();castConc(spellName);};
    nameEl.insertBefore(btn,nameEl.firstChild);
  });
  upd();updateAC();
})();
"""


def generate_html(char: Character) -> str:
    name = char.name
    char_id = char.char_id
    char_slug = slug(name)
    store_key = f"dnd-{char_slug}-{char_id}"

    # ── Header pills ──────────────────────────────────────────────────────────
    class_pills = []
    for cls in char.classes:
        class_pills.append(f'<span class="pill">{esc(cls["name"])} <b>{cls["level"]}</b></span>')
        if cls.get("subclass"):
            class_pills.append(f'<span class="pill">{esc(cls["subclass"])}</span>')
    meta_pills = "".join(class_pills)
    meta_pills += f'<span class="pill">{esc(char.race_name)}</span>'
    meta_pills += f'<span class="pill">{esc(char.background)}</span>'
    meta_pills += f'<span class="pill">{esc(char.alignment)}</span>'
    meta_pills += f'<span class="pill">Prof <b>+{char.prof}</b></span>'
    if char.is_caster():
        meta_pills += f'<span class="pill">Save DC <b>{char.get_spell_save_dc()}</b></span>'
        meta_pills += f'<span class="pill">Spell Atk <b>{fmt_mod(char.get_spell_attack_bonus())}</b></span>'

    # ── Ability scores ────────────────────────────────────────────────────────
    display_order = ["STR", "DEX", "CHA", "INT", "WIS", "CON"]
    ability_html = ""
    for aname in display_order:
        score = char.ability_scores.get(aname, 10)
        m = score_mod(score)
        cls_attr = ' class="abm pos"' if m > 0 else ' class="abm neg"' if m < 0 else ' class="abm"'
        ability_html += (
            f'<div class="ab"><div{cls_attr}>{fmt_mod(m)}</div>'
            f'<div class="abs">{score}</div><div class="abn">{aname}</div></div>\n          '
        )

    # ── Saving throws ─────────────────────────────────────────────────────────
    saves_html = ""
    for aname in display_order:
        bonus = char.get_save_bonus(aname)
        is_prof = aname in char.save_profs
        m_str = fmt_mod(bonus).replace("-", "−")
        if is_prof:
            saves_html += (
                f'<div class="pbox" style="border:1.5px solid var(--purple);">'
                f'<div class="pv" style="color:var(--purple);">{m_str} ✦</div>'
                f'<div class="pl">{aname}</div></div>\n          '
            )
        else:
            saves_html += (
                f'<div class="pbox"><div class="pv">{m_str}</div>'
                f'<div class="pl">{aname}</div></div>\n          '
            )

    # ── Passives ──────────────────────────────────────────────────────────────
    passive_percep = 10 + char.get_skill_bonus("Perception", 5)
    passive_insight = 10 + char.get_skill_bonus("Insight", 5)
    passive_invest = 10 + char.get_skill_bonus("Investigation", 4)

    # ── Proficiencies text ────────────────────────────────────────────────────
    prof_lines = ""
    prof_lines += f'<div><b style="color:var(--ink);">Armor:</b> {esc(", ".join(char.armor_profs) or "None")}</div>\n'
    prof_lines += f'<div><b style="color:var(--ink);">Weapons:</b> {esc(", ".join(char.weapon_profs) or "None")}</div>\n'
    prof_lines += f'<div><b style="color:var(--ink);">Tools:</b> {esc(", ".join(char.tool_profs) or "None")}</div>\n'
    prof_lines += f'<div><b style="color:var(--ink);">Languages:</b> {esc(", ".join(char.languages) or "Common")}</div>\n'
    if char.darkvision:
        prof_lines += f'<div><b style="color:var(--ink);">Darkvision:</b> {char.darkvision}ft</div>\n'
    if char.resistances:
        prof_lines += f'<div><b style="color:var(--ink);">Resistances:</b> {esc(", ".join(char.resistances))}</div>\n'

    # ── Skills ────────────────────────────────────────────────────────────────
    def skill_row(skill_name, ability_id):
        bonus = char.get_skill_bonus(skill_name, ability_id)
        prof_type = char.skill_profs.get(skill_name)
        dot_cls = "dot p" if prof_type in ("proficiency", "expertise") else "dot"
        hi_cls = " hi" if prof_type == "expertise" else ""
        extra = '<span class="sk-bonus">Expert</span>' if prof_type == "expertise" else ""
        return (
            f'<div class="sk{hi_cls}"><div class="{dot_cls}"></div>'
            f'<span class="skn">{esc(skill_name)}</span>'
            f'<span class="skv">{fmt_mod(bonus)}</span>{extra}</div>\n'
        )

    def mod_str(aname):
        return fmt_mod(score_mod(char.ability_scores.get(aname, 10)))

    # ── Weapons ───────────────────────────────────────────────────────────────
    weapon_rows = ""
    for w in char.weapons:
        weapon_rows += (
            f'<tr><td><b>{esc(w["name"])}</b></td>'
            f'<td><span class="hbadge">{fmt_mod(w["hit"])}</span></td>'
            f'<td>{esc(w["damage"])} {esc(w["damage_type"])}</td>'
            f'<td style="color:var(--ink2);">{esc(w["notes"])}</td></tr>\n'
        )
    if not weapon_rows:
        weapon_rows = '<tr><td colspan="4" style="color:var(--ink2);">No equipped weapons found</td></tr>\n'

    # ── Combat spell slots ────────────────────────────────────────────────────
    combat_slots_html = ""
    spell_slots_panel_html = ""
    res_max_parts = []

    for i, count in enumerate(char.spell_slots):
        if count == 0:
            continue
        lvl = i + 1
        key = f"slot{lvl}"
        res_max_parts.append(f"  '{key}':{count}")
        # Spells tab dots (sdot style, saved as sdots)
        sdots = "".join(f'<button class="sdot" onclick="toggleDot(this)"></button>' for _ in range(count))
        spell_slots_panel_html += (
            f'<div class="slot-box"><div class="slot-lbl">{ORDINALS[i]}</div>'
            f'<div class="slot-n">{count} slot{"s" if count>1 else ""}</div>'
            f'<div class="sdots">{sdots}</div></div>\n      '
        )
        # Combat tab dots (udot style, synced by data-res)
        udots = "".join(
            f'<button class="udot" data-res="{key}" onclick="toggleDot(this)"></button>'
            for _ in range(count)
        )
        combat_slots_html += (
            f'<div style="text-align:center;">'
            f'<div style="font-size:10px;color:var(--ink2);margin-bottom:5px;">{ORDINALS[i]} Level ({count})</div>'
            f'<div class="udots" style="justify-content:center;">{udots}</div>'
            f'</div>\n        '
        )

    combat_slots_section = ""
    if combat_slots_html:
        combat_slots_section = (
            '<div class="sec"><div class="sec-t">Spell Slots — click to spend · synced with Spells tab</div>'
            f'<div style="display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start;">\n        '
            f'{combat_slots_html}</div></div>\n'
        )

    # ── Spell rows ────────────────────────────────────────────────────────────
    def spell_row_pair(spell):
        tag_str = " · ".join(spell["tags"])
        lvl = spell["level"]
        ord_sfx = "st" if lvl == 1 else "nd" if lvl == 2 else "rd" if lvl == 3 else "th"
        meta = f'{lvl}{ord_sfx} {esc(spell["school"])}'
        aw = " aw" if spell["always_prepared"] else ""
        slvl = "★" if spell["always_prepared"] else ("C" if lvl == 0 else str(lvl))
        row = (
            f'<div class="sr{aw}" onclick="ts(this)">'
            f'<span class="slvl">{slvl}</span>'
            f'<span class="sn">{esc(spell["name"])}</span>'
            f'<span class="stag">{esc(tag_str)}</span>'
            f'<span class="sarr">▶</span></div>\n'
        )
        row += (
            f'<div class="sd"><div class="sdm">'
            f'<span>{meta}</span>'
            f'<span>{esc(spell["casting_time"])}</span>'
            f'<span>{esc(spell["range"])}</span>'
            f'<span>{esc(spell["duration"])}</span>'
            f'</div>{esc(spell["description"])}</div>\n'
        )
        return row

    spells_content = ""
    if char.cantrips:
        spells_content += '<div class="sl-lbl">Cantrips</div>\n'
        for s in char.cantrips:
            spells_content += spell_row_pair(s)
    for lvl in range(1, 10):
        spells = char.spells_by_level.get(lvl, [])
        if not spells:
            continue
        count = char.spell_slots[lvl - 1]
        spells_content += f'<div class="sl-lbl">{ORDINALS[lvl-1]} Level ({count} slot{"s" if count>1 else ""})</div>\n'
        for s in spells:
            spells_content += spell_row_pair(s)

    spells_tab_btn = ""
    spells_panel = ""
    if char.is_caster():
        spells_tab_btn = '<button class="tab" onclick="showTab(\'spells\',this)">Spells</button>'
        spells_panel = (
            '<div id="spells" class="panel">\n'
            '  <div style="display:flex;flex-direction:column;gap:9px;">\n'
            '    <div class="sec"><div class="sec-t">Spell Slots — click dots to track</div>\n'
            '      <div class="slot-grid">\n      '
            f'{spell_slots_panel_html}'
            '      </div></div>\n'
            '    <div class="sec"><div class="sec-t">Prepared Spells — click to expand · ★ = always prepared</div>\n'
            f'{spells_content}'
            '    </div>\n  </div>\n</div>\n'
        )

    # ── Armor ─────────────────────────────────────────────────────────────────
    armor_slots_html = ""
    armor_js_parts = []
    for ap in char.armor_pieces:
        aid = ap["id"]
        aname_esc = esc(ap["name"])
        armor_type_lbl = "Shield" if ap["type"] == "shield" else "Armor"
        armor_slots_html += (
            f'<div class="armor-slot" id="slot-{esc(aid)}" onclick="toggleArmor(\'{esc(aid)}\')">'
            f'<div style="font-size:11px;font-weight:700;">{aname_esc}</div>'
            f'<div style="font-size:10px;color:var(--ink2);">{armor_type_lbl}</div>'
            f'<div style="font-size:18px;font-weight:700;margin-top:3px;">AC {ap["ac"]}</div>'
            f'<div data-eq style="font-size:10px;color:var(--green);margin-top:3px;">Equipped</div>'
            f'</div>\n'
        )
        armor_js_parts.append(f"  {aid}:{{ac:{ap['ac']},equipped:true,name:{json.dumps(ap['name'])}}}")

    if not armor_slots_html:
        armor_slots_html = (
            f'<div class="armor-slot" id="slot-unarmored">'
            f'<div style="font-size:11px;font-weight:700;">Unarmored</div>'
            f'<div style="font-size:10px;color:var(--ink2);">Defense</div>'
            f'<div style="font-size:18px;font-weight:700;margin-top:3px;">AC {char.ac}</div>'
            f'<div data-eq style="font-size:10px;color:var(--green);margin-top:3px;">Equipped</div>'
            f'</div>\n'
        )
        armor_js_parts.append(f"  unarmored:{{ac:{char.ac},equipped:true,name:'Unarmored'}}")

    armor_js = "{\n" + ",\n".join(armor_js_parts) + "\n}"

    # ── Gear ──────────────────────────────────────────────────────────────────
    gear_html = ""
    items = [f'{esc(g["name"])}{"×"+str(g["qty"]) if g["qty"]>1 else ""}' for g in char.gear_items]
    currency_parts = []
    for code, label in [("pp","PP"),("gp","GP"),("sp","SP"),("cp","CP"),("ep","EP")]:
        if char.currency.get(code):
            currency_parts.append(f'{char.currency[code]} {label}')
    items.append("Currency: " + (", ".join(currency_parts) or "0 GP"))
    for i in range(0, len(items), 2):
        left = items[i]
        right = items[i+1] if i+1 < len(items) else ""
        gear_html += (
            f'<div style="font-size:12px;padding:3px 0;border-bottom:0.5px solid rgba(0,0,0,.05);">'
            f'<span style="color:var(--ink2);">{left}</span></div>\n'
            f'<div style="font-size:12px;padding:3px 0;border-bottom:0.5px solid rgba(0,0,0,.05);">'
            f'<span style="color:var(--ink2);">{right}</span></div>\n'
        )

    # ── Features ──────────────────────────────────────────────────────────────
    def feature_blocks(feats, limit=12):
        html = ""
        for f in feats[:limit]:
            html += (
                f'<div class="ft"><div class="ftn">{esc(f["name"])}</div>'
                f'<div class="ftd">{esc(f["description"])}</div></div>\n'
            )
        return html or '<div class="ft"><div class="ftn">—</div></div>\n'

    racial_features_html = feature_blocks(char.racial_traits, 10)
    class_features_html = feature_blocks(char.class_features, 20)
    feats_html = feature_blocks(char.feats) if char.feats else '<div class="ft"><div class="ftn">No feats</div></div>\n'

    # ── Resistances ───────────────────────────────────────────────────────────
    resist_html = '<span class="cond-lbl">Resist</span>'
    resist_html += " ".join(f'<span class="res-pill">{esc(r)}</span>' for r in char.resistances)
    if char.immunities:
        resist_html += '<span class="cond-lbl" style="margin-left:6px;">Immune</span>'
        resist_html += " ".join(f'<span class="imm-pill">{esc(r)}</span>' for r in char.immunities)

    # ── JS config ─────────────────────────────────────────────────────────────
    res_max_js = "{\n" + ",\n".join(res_max_parts) + "\n}" if res_max_parts else "{}"
    title_cls = char.classes[0]["name"] if char.classes else "Adventurer"

    # ── Assemble HTML ─────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(name)} — {esc(title_cls)} {char.total_level}</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="sheet">

<!-- HEADER -->
<div class="hdr">
  <div>
    <div class="cname">{esc(name)}</div>
    <div class="meta">{meta_pills}</div>
  </div>
  <div class="hdr-r">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;justify-content:flex-end;">
      <span style="font-size:10px;color:var(--ink2);">Inspiration</span>
      <div class="insp-pip" id="inspPip" onclick="toggleInspiration()" title="Heroic Inspiration"></div>
      <button class="dark-btn" onclick="toggleDark()" title="Toggle dark mode" id="darkBtn">🌙</button>
    </div>
    <div class="srow">
      <div class="sb"><div class="v" id="acHeader">{char.ac}</div><div class="l">AC</div></div>
      <div class="sb"><div class="v">{fmt_mod(char.initiative)}</div><div class="l">Init</div></div>
      <div class="sb"><div class="v">{char.speed}ft</div><div class="l">Speed</div></div>
    </div>
  </div>
</div>

<!-- CONCENTRATION TRACKER -->
<div class="conc-box">
  <span class="conc-label">Concentrating on</span>
  <input class="conc-input" id="concSpell" placeholder="— nothing —" oninput="saveConc()">
  <button class="conc-clear" onclick="clearConc()">✕ drop</button>
</div>

<!-- HP TRACKER -->
<div class="hp-box">
  <div class="hp-top">
    <div>
      <div class="hp-lbl">Hit Points</div>
      <div style="display:flex;align-items:baseline;gap:4px;flex-wrap:wrap;">
        <div class="hp-nums">
          <div class="hp-cur" id="hpCur">{char.max_hp}</div>
          <div class="hp-sep">/</div>
          <div class="hp-max">{char.max_hp}</div>
        </div>
        <span class="tmp-badge" id="tmpBadge">+<span id="tmpVal">0</span>&nbsp;tmp</span>
      </div>
    </div>
    <div class="hp-bar-wrap"><div class="hp-bar" id="hpBar" style="width:100%"></div></div>
    <div class="hp-pct" id="hpPct">100%</div>
  </div>
  <div class="hp-controls">
    <input type="number" id="hpAmt" placeholder="Amount" min="0">
    <button class="btn btn-dmg" onclick="applyDmg()">Take Damage</button>
    <button class="btn btn-heal" onclick="applyHeal()">Heal</button>
    <button class="btn btn-sm" onclick="setTmp()">Set Temp HP</button>
    <button class="btn btn-sm" onclick="resetLR()">Long Rest</button>
    <button class="btn btn-sr" onclick="shortRest()">Short Rest</button>
  </div>
  <div class="ds-box" id="deathSaves" style="display:none;">
    <span class="ds-label">Death Saves</span>
    <div class="ds-group">
      <span style="font-size:10px;color:var(--green);margin-right:3px;">Success</span>
      <div class="ds-dot" id="ds-s0" onclick="toggleDS('s',0)"></div>
      <div class="ds-dot" id="ds-s1" onclick="toggleDS('s',1)"></div>
      <div class="ds-dot" id="ds-s2" onclick="toggleDS('s',2)"></div>
    </div>
    <div class="ds-group">
      <span style="font-size:10px;color:var(--red);margin-right:3px;">Failure</span>
      <div class="ds-dot" id="ds-f0" onclick="toggleDS('f',0)"></div>
      <div class="ds-dot" id="ds-f1" onclick="toggleDS('f',1)"></div>
      <div class="ds-dot" id="ds-f2" onclick="toggleDS('f',2)"></div>
    </div>
    <button class="btn btn-sm" onclick="clearDS()">Clear</button>
  </div>
</div>

<!-- CONDITIONS + RESISTANCES -->
<div class="cond-box">
  <div class="cond-row">
    <span class="cond-lbl">Conditions</span>
    <span class="cond" onclick="toggleCond(this)">Blinded</span>
    <span class="cond" onclick="toggleCond(this)">Charmed</span>
    <span class="cond" onclick="toggleCond(this)">Deafened</span>
    <span class="cond" onclick="toggleCond(this)">Exhausted</span>
    <span class="cond" onclick="toggleCond(this)">Frightened</span>
    <span class="cond" onclick="toggleCond(this)">Grappled</span>
    <span class="cond" onclick="toggleCond(this)">Incapacitated</span>
    <span class="cond" onclick="toggleCond(this)">Paralyzed</span>
    <span class="cond" onclick="toggleCond(this)">Poisoned</span>
    <span class="cond" onclick="toggleCond(this)">Prone</span>
    <span class="cond" onclick="toggleCond(this)">Restrained</span>
    <span class="cond" onclick="toggleCond(this)">Stunned</span>
  </div>
  <div class="cond-row" style="margin-top:6px;padding-top:6px;border-top:0.5px solid var(--bd);">
    {resist_html}
  </div>
</div>

<!-- TABS -->
<div class="tabs">
  <button class="tab active" onclick="showTab('stats',this)">Stats &amp; Roleplay</button>
  <button class="tab" onclick="showTab('combat',this)">Combat</button>
  {spells_tab_btn}
  <button class="tab" onclick="showTab('features',this)">Features &amp; Traits</button>
  <button class="tab" onclick="showTab('equipment',this)">Equipment</button>
</div>

<!-- ═══ STATS & ROLEPLAY ═══ -->
<div id="stats" class="panel active">
  <div class="grid2">
    <div class="col">
      <div class="sec">
        <div class="sec-t">Ability Scores</div>
        <div class="ab6">
          {ability_html}
        </div>
      </div>
      <div class="sec">
        <div class="sec-t">Saving Throws — ✦ proficient</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-bottom:5px;">
          {saves_html}
        </div>
      </div>
      <div class="sec">
        <div class="sec-t">Passives</div>
        <div class="prow">
          <div class="pbox"><div class="pv">{passive_percep}</div><div class="pl">Percep.</div></div>
          <div class="pbox"><div class="pv">{passive_insight}</div><div class="pl">Insight</div></div>
          <div class="pbox"><div class="pv">{passive_invest}</div><div class="pl">Investig.</div></div>
        </div>
      </div>
      <div class="sec">
        <div class="sec-t">Proficiencies</div>
        <div style="font-size:11px;color:var(--ink2);line-height:1.8;">{prof_lines}</div>
      </div>
      <div class="sec">
        <div class="sec-t">Background &amp; Notes</div>
        <textarea class="char-notes" id="charNotes" placeholder="Backstory, personality traits, bonds, flaws, session notes, NPC names..." oninput="saveNotes()"></textarea>
      </div>
    </div>
    <div class="col">
      <div class="sec">
        <div class="sec-t">Skills by Ability — filled dot = proficient</div>
        <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:6px;">
          <div>
            <div class="sg"><div class="sg-h">STR {mod_str("STR")}</div>
              {skill_row("Athletics", 1)}
            </div>
            <div class="sg" style="margin-top:5px;"><div class="sg-h">DEX {mod_str("DEX")}</div>
              {skill_row("Acrobatics", 2)}{skill_row("Sleight of Hand", 2)}{skill_row("Stealth", 2)}
            </div>
            <div class="sg" style="margin-top:5px;"><div class="sg-h">CHA {mod_str("CHA")}</div>
              {skill_row("Deception", 6)}{skill_row("Intimidation", 6)}{skill_row("Performance", 6)}{skill_row("Persuasion", 6)}
            </div>
          </div>
          <div>
            <div class="sg"><div class="sg-h">INT {mod_str("INT")}</div>
              {skill_row("Arcana", 4)}{skill_row("History", 4)}{skill_row("Investigation", 4)}{skill_row("Nature", 4)}{skill_row("Religion", 4)}
            </div>
            <div class="sg" style="margin-top:5px;"><div class="sg-h">WIS {mod_str("WIS")}</div>
              {skill_row("Animal Handling", 5)}{skill_row("Insight", 5)}{skill_row("Medicine", 5)}{skill_row("Perception", 5)}{skill_row("Survival", 5)}
            </div>
            <div class="sg" style="margin-top:5px;"><div class="sg-h">CON {mod_str("CON")}</div>
              <div class="sk"><span class="sk-note">No CON skills</span></div>
            </div>
          </div>
        </div>
      </div>
      <div style="margin-top:4px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.9px;color:var(--gold);padding-bottom:4px;border-bottom:.5px solid var(--bd);">Roleplay &amp; Exploration Cheat Sheet</div>
      <div class="util-card" style="margin-top:6px;">
        <div class="util-hdr">Key abilities to remember</div>
        <div class="utool" onclick="this.classList.toggle('open')">
          <div class="utool-hdr"><span class="utool-name">Edit this file to add tips</span><span class="utool-arr">▶</span></div>
          <div class="utool-desc">Add expandable ability reminders, smart plays, and skill tips here. See deb/index.html for examples.</div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ COMBAT ═══ -->
<div id="combat" class="panel">
  <div style="display:flex;flex-direction:column;gap:9px;">
    <div class="sec">
      <div class="sec-t">Weapons</div>
      <table class="wtb">
        <tr><th>Weapon</th><th>Hit</th><th>Damage</th><th>Notes</th></tr>
        {weapon_rows}
      </table>
    </div>
    {combat_slots_section}
    <div class="sec">
      <div class="sec-t">Key Advantages &amp; Notes</div>
      <div style="font-size:12px;color:var(--ink2);line-height:1.8;">
        <div><b style="color:var(--ink);">Edit this section</b> to add combat notes, passive bonuses, and reminders.</div>
      </div>
    </div>
  </div>
</div>

{spells_panel}

<!-- ═══ FEATURES & TRAITS ═══ -->
<div id="features" class="panel">
  <div class="grid2x">
    <div class="col">
      <div class="sec">
        <div class="sec-t">Racial Traits — {esc(char.race_name)}</div>
        {racial_features_html}
      </div>
      <div class="sec">
        <div class="sec-t">Feats</div>
        {feats_html}
      </div>
    </div>
    <div class="col">
      <div class="sec">
        <div class="sec-t">Class Features</div>
        {class_features_html}
      </div>
    </div>
  </div>
</div>

<!-- ═══ EQUIPMENT ═══ -->
<div id="equipment" class="panel">
  <div style="display:flex;flex-direction:column;gap:9px;">
    <div class="sec">
      <div class="sec-t">Armor &amp; AC Tracker — click to equip/unequip</div>
      <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-bottom:10px;">
        {armor_slots_html}
      </div>
      <div style="display:flex;align-items:center;gap:12px;background:var(--sec);border-radius:var(--r);padding:10px 14px;">
        <div>
          <div style="font-size:10px;color:var(--ink2);text-transform:uppercase;letter-spacing:.4px;">Current AC</div>
          <div style="font-size:32px;font-weight:700;" id="acDisplay">{char.ac}</div>
        </div>
        <div style="flex:1;font-size:11px;color:var(--ink2);line-height:1.7;" id="acBreakdown">Equipped armor</div>
        <div style="text-align:right;">
          <div style="font-size:10px;color:var(--ink2);">Without shield</div>
          <div style="font-size:16px;font-weight:700;" id="acNoShield">{char.ac}</div>
        </div>
      </div>
    </div>
    <div class="sec">
      <div class="sec-t">Weapons &amp; Combat Gear</div>
      <table class="wtb">
        <tr><th>Item</th><th>Hit</th><th>Damage</th><th>Notes</th></tr>
        {weapon_rows}
      </table>
    </div>
    <div class="sec">
      <div class="sec-t">Adventuring Gear</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
        {gear_html}
      </div>
    </div>
  </div>
</div>

</div>

<script>
const STORE_KEY='{store_key}';
const RES_MAX={res_max_js};
const resRem={{...RES_MAX}};
const ALL_RES=Object.keys(RES_MAX);
let hp={char.max_hp},maxHp={char.max_hp},tmp=0;
const armor={armor_js};
{JS_ENGINE}
</script>
</body>
</html>"""

    return html


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch a DnD Beyond character and generate a self-contained HTML sheet."
    )
    parser.add_argument("character_id", help="DnD Beyond character ID (the number in the URL)")
    parser.add_argument("--output", "-o", help="Output path (default: character-sheet/<slug>/index.html)")
    parser.add_argument("--cookie", help="Auth cookie for private characters, e.g. 'CobaltSession=abc123'")
    args = parser.parse_args()

    url = f"https://www.dndbeyond.com/character/{args.character_id}/json"
    print(f"Fetching https://www.dndbeyond.com/character/{args.character_id}/json ...")

    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    req.add_header("Accept", "application/json, text/plain, */*")
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    if args.cookie:
        req.add_header("Cookie", args.cookie)

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("Error: Character is private. Pass your DDB cookie with --cookie 'CobaltSession=...'")
            print("Get it from browser DevTools → Application → Cookies → dndbeyond.com")
        else:
            print(f"HTTP {e.code}: {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Parsing character data...")
    char = Character(raw)
    print(f"  Name:    {char.name}")
    print(f"  Classes: {', '.join(f'{c[\"name\"]} {c[\"level\"]}' for c in char.classes)}")
    print(f"  Race:    {char.race_name} ({char.background})")
    print(f"  HP:      {char.max_hp}  AC: {char.ac}  Speed: {char.speed}ft")
    print(f"  Spells:  {sum(1 for s in char.cantrips)} cantrips, {sum(len(v) for v in char.spells_by_level.values())} leveled")
    print(f"  Armor:   {[a['name'] for a in char.armor_pieces] or ['none equipped']}")

    print("Generating HTML...")
    html = generate_html(char)

    if args.output:
        out_path = args.output
    else:
        char_slug = slug(char.name)
        out_path = f"character-sheet/{char_slug}/index.html"

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\nDone! Written to: {out_path}")
    print(f"Open in a browser to preview, then: git add {out_path} && git commit -m 'Add {char.name} character sheet'")


if __name__ == "__main__":
    main()
