VS Code (including chat extensions) uses its own icon font called Codicons.

🎯 The actual thing
Font: Codicon (a.k.a. @vscode/codicons)
Maintained by: Microsoft
Format: icon font + SVG set
Usage: everywhere in VS Code UI and extensions

👉 It’s the default “product icon theme” in VS Code

🧩 How it shows up in extensions (including chat UIs)

If you’ve seen stuff like:

$(sparkle)
$(comment)
$(send)

That’s not emoji magic, that’s Codicons.

Syntax: $(iconName)
Rendered via: Codicon font glyph mapping
🧠 Mental model (useful for your UI tinkering)

Think of it like this:

Codicons = VS Code’s internal “UI language”
not decorative, but semantic tokens for actions
$(play) → run
$(gear) → settings
$(sparkle) → AI-ish stuff (chat, suggestions)
$(comment-discussion) → chat bubbles
⚠️ Important nuance (you’ll care about this)

There are actually two layers:

Codicons (product icons) → what chat extensions use
File icon themes → different system (Material Icons, etc.)

So if you’re mimicking VS Code chat UI, you want Codicons, not Font Awesome / Material.

🛠️ If you want to steal the look (you probably do 😄)

Install:

npm i @vscode/codicons

Use in HTML:

<span class="codicon codicon-sparkle"></span>

Or SVG sprite if you’re feeling fancy.

🎨 Design flavor (why it feels “VS Code”)

Codicons are:

monochrome
16px grid
slightly geometric / utilitarian
optimized for dense UI + low cognitive load

Basically: “icons that don’t get in your way while you’re thinking”