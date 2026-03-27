
---
agent: 'agent'
description: 'Edit QGIS dbXXX.py scripts'
name: 'qgis_edit_scripts'
model: Raptor mini (Preview)
---

This is my QGIS master script to generate proper SQL that I use via dBeaver to get data from our Databricks (spark) server.

Have a look at #file:Feature Overview.csv and pick appropriate features

Here is the documentation if you have any questions: https://specs.tomtomgroup.com/orbis/documentation/feature_spec/feature_spec_12.9-1.0/internal/specifications/feature_model/geometry/geometries.html

For optimisation of selections we have two approaches:
fProcessBuildingsWithParts() - optimised for ST_ selection polygon
and
fProcessBuildingsWithPartsH3() - optimised for approximate selection using H3 tiles.
