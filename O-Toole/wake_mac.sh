#!/bin/bash

# Wake machine on local LAN
/opt/homebrew/bin/wakeonlan/wakeonlan 60:CF:84:BC:9F:1B

# Wake machine over internet through router
/opt/homebrew/bin/wakeonlan/wakeonlan -i 81.244.26.127 -p 51820 60:CF:84:BC:9F:1B