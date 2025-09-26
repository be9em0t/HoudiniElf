Good. we have a MVP of Unity ShaderGraph scrape mode.

The problem I see on a full run is that a lot of nodes got double or triple accounted.

Don't do a de-duplicating algorhitm, that is easy, but we want to solve the root cause.

And the root cause is that you have a slightly too wide a net for scaping the nodes.

The correct capture routine is this:
1. On the initial URL look at the frame containing the page, not the sidebar. There is a table that lists all and only pages leading to node pages. The table groups them by Topic, which may or may not be a Category.
2. Step two: define categories -  follow through each Topic in sequence, there you will find more tables containing the actual elements (Nodes).  As you go through the Topic pages some of them have a single table - for example Topic Channel Nodes -> contains only table Channel Nodes. In this case the category name is "Channel". In other cases  the topic page contains multiple tables, for example topic Artistic contains tables like "Adjustment", "Blend", "Filter etc. Each of these tables represent separate Cathegory, and so the topic in this case is not a category.
3. Scrape the Node information. Now that you understand the structure and having the URLs for the nodes of each category you can scrape the necessary info from those node URLs. As an extra check, each Node page has a title that states the name of the node, for example "Custom Function Node" or "Channel Mixer Node". Notice how the type of the element (node) is part of the title. If there are nodes that seem not to conform to this, please list them also in the JSON file, in key "problems" after the "capture_date" key.
4. Finally, to make control easier, please build a node tree with only names of categories and nodes. This will serve as a kind of "contents tree" for easy visualization and verification. Include it at  the start of the JSON in as visual way as practical, under key "contents_tree", after the "root_url" key, before "categories". If you think the tree is not useful or is hard to represent in a JSON file, please tell me and we're adjust this action.

Pleae concentrate on these actions and don't stray to non-directly related changes of code. #file:README.md and #file:scrape_dog.md provide overview of the scape_dog module.

-
complete fail, it just runs in a loop. obviousl, what you run as test and what I run with python -m scrape_dog are completely different things.

To try and untangle ourselves, disable the actual element url scraping, concentrate only on building the element tree. Remember, the root url will give you the Topics, each topic will give you the Cathegories. White down only the Element names with correct categories to the tree. DO NOT SCRAPE the element URLS! 
----


we are working on the Unity ShaderGrpaph scraper adapter.
Read the #file:README.md and #file:scrape_dog.md documents to familiarize with the scrape_dog project.

at the current point we have partial success scraping he Shadergraph nodes, but problems remain

---
First I want to do some refactoring. The script has become a bit messy becaue of me asking for more features.

1. We need to makeour data model universal. It now serves functions, api classes and node for three different languages (vex, python and unity shading language)
a. document level
- software: str
- version: str 
- capture_date
- root url: str
b. category level
- category: str
c. element level
- <function | class | node> name: str
- description: str
- branch url: str
- usage: List[str]
2. We need to split the script with the goal of loading less code into the prompt. We'll have a master script (scrape_dog.py) and child scripts organized by topic (vex, houdini noded, python docs, unity nodes). 
3. We need to sort out testing process, seems like our setup requres tweaking every time we edit the script
4. We'll revisit the top comment in the master script to reflect these updates

Please, proceed with these steps in an optimal way. Do not overcomplicate the script for edge cases, simplicity is easier to maintain.

--------

yes, do

Implement success autosave using exact filename format <software>_<version>.json (replace spaces with underscores). Also include timestamp or incrementing suffix if file already exists? (I'll add timestamp to avoid clobbering by default.)
Implement _autosave_result helper to centralize writing to capture_results/ and call it both in success and cancel flows.
Optionally add a small visible status in the GUI indicating the autosave path when done.

---------

its's not super intuitive running it like this:
python scrape_dog.py <adapter> [url] [--max N]

i would prefer the master script to open a window similar to the one we had before, that would allow us to:
- select capture mode
- assign root URL
- assign manually, if necessary, version and software name
- set Max Results (0 means no limit)
- have a text field to view the results of the run, as before.If this add compliction we can pipe that information to the command line

Aslo, part of the job of the master module is to read settings from the ini file and save them back to reflect user changes (mode, url, software name, version)
-----
we contiue work on scrape_dog documentation scraping toolkit.

check the open documents, then we can continue with restoring the proper GUI.
1. We should read and write the settings to scrape_settings.ini

