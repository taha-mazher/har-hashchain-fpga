# All UCI variants of cascade_secure, plus the plain cascade's power in mW for the same comparison.
Set-Location $PSScriptRoot
foreach ($v in @(@("1","0","sec_uci_lite_plain"), @("1","1","sec_uci_lite_keyed"), @("0","0","sec_uci_iter_plain"), @("0","1","sec_uci_iter_keyed"))) {
    Write-Output "== $($v[2])"
    & .\run_secure.ps1 cascade_uci $v[0] $v[1] $v[2]
}
& "C:\Xilinx\Vivado\2024.2\bin\vivado.bat" -mode batch -nojournal -log power_fine_cascade_uci.log -source power_fine.tcl -tclargs cascade_uci tb_cascade | Out-Null
Write-Output "ALL DONE"
