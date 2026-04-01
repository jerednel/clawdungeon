# 🍌 Nano Banana Pro - Image Generation Guide

**What it is:** Nano Banana Pro is an OpenClaw skill that uses Google's Gemini 3 Pro Image model to generate and edit high-quality images.

**Perfect for:** CLAWDUNGEON avatars, game art, marketing materials, and more.

---

## Setup

### Prerequisites

1. **Install `uv`** (Python package manager):
```bash
brew install uv
```

2. **Get a Gemini API Key:**
   - Go to https://ai.google.dev/
   - Sign in with Google
   - Create an API key
   - Copy the key

3. **Configure OpenClaw:**

Option A - Environment variable:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

Option B - OpenClaw config file (`~/.openclaw/openclaw.json`):
```json
{
  "skills": {
    "nano-banana-pro": {
      "apiKey": "your-api-key-here"
    }
  }
}
```

---

## Usage

### Basic Image Generation

```bash
uv run /Users/jeremy/.nvm/versions/node/v24.12.0/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "a dark fantasy warrior in ornate armor standing in a torchlit dungeon" \
  --filename "warrior-avatar.png" \
  --resolution 2K
```

### Edit an Existing Image

```bash
uv run /Users/jeremy/.nvm/versions/node/v24.12.0/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "add a glowing magical aura around the warrior" \
  --filename "warrior-magic.png" \
  --input "/path/to/warrior-avatar.png" \
  --resolution 2K
```

### Multi-Image Composition (up to 14 images)

```bash
uv run /Users/jeremy/.nvm/versions/node/v24.12.0/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "combine these characters into a party portrait, epic fantasy style" \
  --filename "party-composition.png" \
  --input warrior.png \
  --input mage.png \
  --input rogue.png \
  --resolution 2K
```

---

## Command Reference

| Flag | Description | Required |
|------|-------------|----------|
| `--prompt` | Image description or edit instructions | ✅ Yes |
| `--filename` | Output filename (use timestamps!) | ✅ Yes |
| `--resolution` | Image size: `1K`, `2K`, or `4K` | ❌ No (default: 1K) |
| `-i`, `--input` | Input image(s) for editing/composition | ❌ No |

---

## Resolutions

| Resolution | Dimensions | Best For |
|------------|------------|----------|
| `1K` | ~1024x1024 | Quick drafts, icons, thumbnails |
| `2K` | ~2048x2048 | Game art, avatars, web assets |
| `4K` | ~4096x4096 | Print quality, high-res marketing |

---

## Prompt Engineering Tips

### For CLAWDUNGEON Game Art

**Character Prompts:**
```
"a fierce orc warrior with green skin, wearing spiked armor, holding a massive battle axe, dark fantasy style, dramatic lighting, detailed"
```

**Environment Prompts:**
```
"an ancient underground dungeon with glowing crystals, stone pillars, torches casting shadows, atmospheric fog, epic fantasy landscape"
```

**Item/Weapon Prompts:**
```
"a legendary glowing sword with runic engravings, magical fire aura, ornate golden hilt, game item icon, centered composition"
```

### Style Keywords That Work Well

- `dark fantasy` - Perfect for CLAWDUNGEON aesthetic
- `epic lighting` - Dramatic shadows and highlights
- `highly detailed` - More intricate textures
- `concept art` - Professional game art style
- `dramatic composition` - Dynamic poses and framing
- `atmospheric` - Mood and environment depth

### Avoid

- Vague descriptions ("a cool warrior")
- Conflicting styles ("realistic cartoon")
- Too many subjects in one prompt

---

## CLAWDUNGEON Avatar Ideas

### Character Classes

**Warrior:**
```bash
--prompt "a mighty warrior in plate armor, holding a massive sword, shield on back, battle scars, determined expression, dark fantasy, dramatic lighting, epic portrait"
```

**Mage:**
```bash
--prompt "a wise mage in flowing robes, glowing staff, magical particles, spellbook, arcane energy swirling, dark fantasy, mysterious atmosphere"
```

**Rogue:**
```bash
--prompt "a stealthy rogue in leather armor, dual daggers, hooded cloak, shadowy background, cunning expression, dark fantasy, assassin's creed style"
```

**Cleric:**
```bash
--prompt "a holy cleric in white and gold vestments, divine light aura, holy symbol, healing magic, peaceful expression, dark fantasy, heavenly lighting"
```

### Boss Monsters

```bash
--prompt "a massive red dragon with scarred scales, burning eyes, wings spread, volcanic background, dark fantasy, epic scale, intimidating presence"
```

### City/Faction Art

```bash
--prompt "a medieval fortress city with stone walls and towers, Iron Vanguard banners, gray and gold color scheme, dark fantasy, epic landscape"
```

---

## Workflow Integration

### Via OpenClaw Agent

Just ask your agent:
```
Generate a dark fantasy mage avatar for my CLAWDUNGEON character
```

The agent will:
1. Call the nano-banana-pro skill
2. Generate the image
3. Save it to your workspace
4. Report the file path

### Automated Generation

Create a script to batch-generate avatars:

```bash
#!/bin/bash
# generate-avatars.sh

CLASSES=("warrior" "mage" "rogue" "cleric")
SKILL_PATH="/Users/jeremy/.nvm/versions/node/v24.12.0/lib/node_modules/openclaw/skills/nano-banana-pro/scripts/generate_image.py"

for class in "${CLASSES[@]}"; do
  uv run "$SKILL_PATH" \
    --prompt "a dark fantasy ${class} character portrait, epic lighting, detailed, game avatar" \
    --filename "avatar-${class}-$(date +%Y-%m-%d).png" \
    --resolution 2K
done
```

---

## Best Practices

1. **Use timestamps in filenames** to avoid overwriting:
   ```bash
   --filename "2026-03-31-warrior-avatar.png"
   ```

2. **Start with 1K** for drafts, upscale to 2K/4K for finals

3. **Save prompts** in a text file for consistency:
   ```bash
   echo "your prompt" > prompts/warrior.txt
   ```

4. **Iterate on edits** rather than regenerating from scratch:
   ```bash
   # Generate base
   --prompt "a warrior" --filename "base.png"
   
   # Edit specific details
   --prompt "add a horned helmet" --input "base.png" --filename "helmet.png"
   ```

5. **Use consistent style keywords** across your game's art:
   - Always include `dark fantasy`
   - Pick a lighting style and stick with it
   - Use consistent color palettes per faction

---

## Troubleshooting

### "API key not found"
- Verify `GEMINI_API_KEY` is set
- Check `~/.openclaw/openclaw.json` syntax
- Restart your terminal session

### "uv not found"
```bash
brew install uv
```

### "Resolution not supported"
- Use only `1K`, `2K`, or `4K`
- No other values work

### Images look generic
- Add more specific details to prompts
- Include style keywords
- Use the edit feature to refine

---

## Cost Considerations

- Gemini 3 Pro Image has usage limits on free tier
- Monitor your API usage at https://ai.google.dev/
- Consider rate limiting for batch generation

---

## Example: Complete CLAWDUNGEON Art Suite

```bash
# Create output directory
mkdir -p clawdungeon-art

# Generate class avatars
uv run $SKILL --prompt "dark fantasy warrior portrait, plate armor, sword, epic" --filename "clawdungeon-art/warrior.png" --resolution 2K
uv run $SKILL --prompt "dark fantasy mage portrait, robes, staff, magical aura" --filename "clawdungeon-art/mage.png" --resolution 2K
uv run $SKILL --prompt "dark fantasy rogue portrait, hood, daggers, shadows" --filename "clawdungeon-art/rogue.png" --resolution 2K
uv run $SKILL --prompt "dark fantasy cleric portrait, holy light, robes, divine" --filename "clawdungeon-art/cleric.png" --resolution 2K

# Generate boss
uv run $SKILL --prompt "massive red dragon boss, scarred scales, burning eyes, volcanic background, dark fantasy epic" --filename "clawdungeon-art/dragon-boss.png" --resolution 2K

# Generate environment
uv run $SKILL --prompt "underground dungeon entrance, stone archway, torches, atmospheric fog, dark fantasy landscape" --filename "clawdungeon-art/dungeon.png" --resolution 2K
```

---

## Quick Reference Card

```bash
# Generate
uv run $SKILL --prompt "DESCRIPTION" --filename "NAME.png" --resolution 2K

# Edit
uv run $SKILL --prompt "EDIT INSTRUCTIONS" --input "INPUT.png" --filename "OUTPUT.png"

# Compose
uv run $SKILL --prompt "COMBINE INSTRUCTIONS" -i img1.png -i img2.png --filename "OUTPUT.png"
```

Where `$SKILL` = full path to `generate_image.py`

---

*Happy generating! 🍌*
