# Build, gate-level bit-exact simulation (cascade + every hash) with activity capture, and power for one variant;
# then the same netlist held idle for IDLE cycles, for idle power. Usage (PowerShell):
#   .\run_secure.ps1 cascade_uci 1 0 0 sec_uci_lite_plain        (model lite keyed gate tag)
#   .\run_secure.ps1 cascade_uci 1 0 0 sec_uci_lite_plain -IdleOnly   (existing build: idle sim and power only)
param([string]$Name, [string]$Lite, [string]$Keyed, [string]$Gate, [string]$Tag, [switch]$IdleOnly)
$ErrorActionPreference = "Stop"
$bin = "C:\Xilinx\Vivado\2024.2\bin"
$Idle = 20000
Set-Location $PSScriptRoot
$out = "out_$Tag"

if (-not $IdleOnly) {
    & "$bin\vivado.bat" -mode batch -nojournal -log "build_$Tag.log" -source build_secure.tcl -tclargs $Name $Lite $Keyed $Gate $Tag | Out-Null
}
$n2 = (Get-Content "../rtl/mem/$Name/params.txt") -replace '^N2=(\d+).*', '$1'
$chain = "../out/chain_" + $Name.Substring(8) + ".mem"
& "$bin\xvlog.bat" -d NETLIST ../rtl/tb_cascade_secure.v "$out/netlist_funcsim.v" "C:/Xilinx/Vivado/2024.2/data/verilog/src/glbl.v" | Out-Null
& "$bin\xelab.bat" -debug typical -L unisims_ver -L secureip tb_cascade_secure glbl -s "tb_net_$Tag" | Out-Null
$env:SPLIT_OUT = $out
if (-not $IdleOnly) {
    $env:SAIF_NAME = "activity"
    Set-Content -Encoding ascii "xsim_opts_$Tag.txt" "-testplusarg TEST=../out/$Name.mem -testplusarg N2=$n2 -testplusarg CHAIN=$chain -testplusarg KEYED=$Keyed -tclbatch saif_secure.tcl -log xsim_$Tag.log"
    & "$bin\xsim.bat" "tb_net_$Tag" -f "xsim_opts_$Tag.txt" | Out-Null
    Select-String -Path "xsim_$Tag.log" -Pattern "windows=|RESULT" | ForEach-Object { $_.Line }
    & "$bin\vivado.bat" -mode batch -nojournal -log "power_$Tag.log" -source power_secure.tcl -tclargs $Tag tb_cascade_secure | Out-Null
}
$env:SAIF_NAME = "idle"
Set-Content -Encoding ascii "xsim_opts_idle_$Tag.txt" "-testplusarg IDLE=$Idle -testplusarg CHAIN=$chain -tclbatch saif_secure.tcl -log xsim_idle_$Tag.log"
& "$bin\xsim.bat" "tb_net_$Tag" -f "xsim_opts_idle_$Tag.txt" | Out-Null
Select-String -Path "xsim_idle_$Tag.log" -Pattern "idle cycles|RESULT" | ForEach-Object { $_.Line }
& "$bin\vivado.bat" -mode batch -nojournal -log "power_idle_$Tag.log" -source power_secure.tcl -tclargs $Tag tb_cascade_secure idle | Out-Null
