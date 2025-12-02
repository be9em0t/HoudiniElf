# Wake machine over internet using PowerShell
$MacAddress = "60:CF:84:BC:9F:1B"
$PublicIP = "81.244.26.127"
$Port = 51820

$MacBytes = $MacAddress -split '[:-]' | ForEach-Object { [byte]('0x' + $_) }
$MagicPacket = (,0xFF * 6) + ($MacBytes * 16)
$UdpClient = New-Object System.Net.Sockets.UdpClient
$UdpClient.Connect($PublicIP, $Port)
[void]$UdpClient.Send($MagicPacket, $MagicPacket.Length)
$UdpClient.Close()
Write-Host "Magic packet sent to $MacAddress via $PublicIP`:$Port"