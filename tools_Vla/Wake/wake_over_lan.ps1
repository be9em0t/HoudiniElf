$mac = "60:CF:84:BC:9F:1B"
$target = [System.Net.NetworkInformation.PhysicalAddress]::Parse(($mac.ToUpper() -replace '[^0-9A-F]',''))
$packet = [byte[]](,0xFF * 102 + ($target.GetAddressBytes() * 16))
$udp = New-Object System.Net.Sockets.UdpClient
$udp.Connect(([System.Net.IPAddress]::Broadcast), 9)
$udp.Send($packet, $packet.Length)
$udp.Close()