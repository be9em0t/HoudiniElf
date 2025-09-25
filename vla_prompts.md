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

