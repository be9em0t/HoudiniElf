-- mac side --
192.168.1.28
81.244.26.127
79470363
VO7eB8oVA4CcXfWoDUK2McnHjHMaEClhvkO5SdC2pBA=

/Applications/RustDesk.app/Contents/MacOS/rustdesk --config "host=81.244.26.127,key=VO7eB8oVA4CcXfWoDUK2McnHjHMaEClhvkO5SdC2pBA=,relay=81.244.26.127:21117"

open -a RustDeck --args --config "host=81.244.26.127,key=VO7eB8oVA4CcXfWoDUK2McnHjHMaEClhvkO5SdC2pBA=,relay=81.244.26.127:21117"


---- windows ---
nssm install "RustDesk hbbs service" "c:\Ketarin\Tools\RustDesk_x86_64\hbbs.exe"
nssm install "RustDesk hbbr service" "c:\Ketarin\Tools\RustDesk_x86_64\hbbr.exe"

nssm edit "RustDesk hbbs service"
nssm edit "RustDesk hbbr service"

nssm start "RustDesk hbbs service"
nssm start "RustDesk hbbr service"

nssm stop "RustDesk hbbs service"
nssm stop "RustDesk hbbr service"

nssm restart "RustDesk hbbs service"
nssm restart "RustDesk hbbr service"


New-NetFirewallRule -DisplayName "RustDesk TCP 21114-21119" -Direction Inbound -Protocol TCP -LocalPort 21114-21119 -Action Allow

New-NetFirewallRule -DisplayName "RustDesk UDP 21116" -Direction Inbound -Protocol UDP -LocalPort 21116 -Action Allow

------

./hbbr.exe -k "VO7eB8oVA4CcXfWoDUK2McnHjHMaEClhvkO5SdC2pBA="

set ALWAYS_USE_RELAY=Y
./hbbs.exe --mask 192.168.0.0/16 -r 81.244.26.127:21117 -k "VO7eB8oVA4CcXfWoDUK2McnHjHMaEClhvkO5SdC2pBA="


--local-ip 81.244.26.127
Example NSSM change + restart:
nssm set "RustDesk-hbbs" AppParameters "-r 81.244.26.127:21117 -k "VO7eB8oVA4CcXfWoDUK2McnHjHMaEClhvkO5SdC2pBA=" --mask 192.168.0.0/16 --local-ip 81.244.26.127"