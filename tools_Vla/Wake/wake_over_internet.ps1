$mac = "60:CF:84:BC:9F:1B"
$target = [System.Net.NetworkInformation.PhysicalAddress]::Parse(($mac.ToUpper() -replace '[^0-9A-F]',''))
$packet = [byte[]](,0xFF * 102 + ($target.GetAddressBytes() * 16))
$udp = New-Object System.Net.Sockets.UdpClient
$udp.Connect("81.244.26.127", 51820)
$udp.Send($packet, $packet.Length)
$udp.Close()