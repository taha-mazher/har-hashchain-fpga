# Synthesise and implement cascade_secure.v (cascade + hash chain) at 50 MHz.
# Usage: vivado -mode batch -source build_secure.tcl -tclargs <model> <lite 0|1> <keyed 0|1|2> <gate 0|1> <tag>
lassign $argv name lite keyed gate tag
cd [file dirname [file normalize [info script]]]
file mkdir out_$tag
foreach f {w b} { file copy -force ../rtl/mem/$name/$f.mem $f.mem }
set fp [open ../rtl/mem/$name/params.txt]; set gen "[string trim [read $fp]] LITE=$lite KEYED=$keyed GATE=$gate"; close $fp

foreach f {cascade_secure cascade sha256_lite sha256_iter clk_gate} { read_verilog ../rtl/$f.v }
read_xdc clock.xdc
synth_design -top cascade_secure -part xc7a35ticsg324-1L -generic $gen
opt_design
place_design
phys_opt_design
route_design
write_checkpoint -force out_$tag/routed.dcp
report_utilization          -file out_$tag/utilization_routed.rpt
report_utilization -hierarchical -file out_$tag/utilization_hier.rpt
report_timing_summary       -file out_$tag/timing_routed.rpt
write_verilog -mode funcsim -force out_$tag/netlist_funcsim.v
