#!/bin/bash

# Wake machine on local LAN
# /opt/homebrew/bin/wakeonlan 60:CF:84:BC:9F:1B
/opt/homebrew/bin/wakeonlan -i 192.168.1.255 60:CF:84:BC:9F:1B

# Wake machine over internet through router
/opt/homebrew/bin/wakeonlan -i 81.244.26.127 -p 51820 60:CF:84:BC:9F:1B