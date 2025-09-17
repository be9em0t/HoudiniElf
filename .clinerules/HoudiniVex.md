# Houdini VEX Verification Rule

- All VEX code must be verified against the official Houdini 20.5 documentation at https://www.sidefx.com/docs/houdini20.5/
- Every function call and syntax usage must be explicitly found and confirmed in the official documentation.
- Any function or syntax not documented must be flagged as unverified and corrected or justified with authoritative sources.
- Verification should first consult the local VEX documentation stored in the project.
- If local documentation is missing or unclear, the live official documentation URL should be queried as a fallback.
- This rule ensures rigorous accuracy and prevents the use of undocumented or incorrect VEX functions or syntax.
- Automated tools should be used to enforce this rule by cross-referencing code against the local and live documentation.

# Implementation Notes

- A scraper will be developed to extract all VEX functions, arguments, and syntax from https://www.sidefx.com/docs/houdini20.5/vex/index.html
- The extracted data will be stored as a Cline Document for offline verification.
- Verification tools will prioritize local documentation and only query live docs when necessary.

# Purpose

VEX is a specialized language with complex syntax and many functions. This rule enforces strict adherence to official documentation to maintain code quality and correctness.
