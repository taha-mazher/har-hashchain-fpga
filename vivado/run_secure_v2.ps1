# Forward-secure and clock-gated variants (low-area core), plus idle power for the two earlier ungated builds.
Set-Location $PSScriptRoot
foreach ($v in @(@("0","0","sec_uci_lite_plain"), @("1","0","sec_uci_lite_keyed"))) {
    Write-Output "== $($v[2]) (idle only)"
    & .\run_secure.ps1 cascade_uci 1 $v[0] $v[1] $v[2] -IdleOnly
}
foreach ($v in @(@("2","0","sec_uci_lite_fs"), @("0","1","sec_uci_lite_plain_g"), @("1","1","sec_uci_lite_keyed_g"), @("2","1","sec_uci_lite_fs_g"))) {
    Write-Output "== $($v[2])"
    & .\run_secure.ps1 cascade_uci 1 $v[0] $v[1] $v[2]
}
Write-Output "ALL DONE"
