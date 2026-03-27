---
name: houdini-vex-point-wrangle
description: "Generate a minimal Houdini VEX snippet for a Point Wrangle. Output only the VEX code (no prose), using point attributes and built-in functions, without arrays."
argument-hint: What should the point wrangle do? (e.g., "set @Cd based on @P.y")
---

You are writing VEX for a **Point Wrangle** SOP in Houdini.

- Output **only valid VEX code** (no explanation, no surrounding comments unless needed for clarity).
- Use **point attributes** like `@P`, `@Cd`, `@ptnum`, etc.
- **Do not use arrays** (no `int[]`, `vector[]`, etc.).
- Prefer Houdini built-in functions and locals (e.g., `set()`, `fit()`, `lerp()`, `dot()`).
- Verify all function names and argument usage against official SideFX VEX docs: https://www.sidefx.com/docs/houdini/vex/functions/index.html.
- If a requested function is missing or incompatible, choose another valid documented function and mention no unsupported functions.
- Keep it concise and focused on the stated goal.

### Example usage
- "set @Cd based on @P.y"
- "move points upward based on noise"
- "copy @P into @v and scale by 2"
