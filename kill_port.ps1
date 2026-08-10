$targetPort = 3000
$conn = Get-NetTCPConnection -LocalPort $targetPort -ErrorAction SilentlyContinue
if ($conn) {
    $procId = $conn.OwningProcess
    Stop-Process -Id $procId -Force
    Write-Host ("Port " + $targetPort + " freed (PID " + $procId + " killed)")
} else {
    Write-Host ("Port " + $targetPort + " is already free")
}
