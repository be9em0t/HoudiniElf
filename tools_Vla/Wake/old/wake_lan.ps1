# Wake machine on local LAN using PowerShell
$MacAddress = "60:CF:84:BC:9F:1B"
$MacBytes = $MacAddress -split '[:-]' | ForEach-Object { [byte]('0x' + $_) }
$MagicPacket = (,0xFF * 6) + ($MacBytes * 16)
$UdpClient = New-Object System.Net.Sockets.UdpClient
$UdpClient.Connect(([System.Net.IPAddress]::Broadcast), 9)
[void]$UdpClient.Send($MagicPacket, $MagicPacket.Length)
$UdpClient.Close()
Write-Host "Magic packet sent to $MacAddress"