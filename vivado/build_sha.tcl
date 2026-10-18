# Area and timing of one SHA-256 core, out of context (its ~1,030 ports would not fit the package's pins).
# Usage: vivado -mode batch -source build_sha.tcl -tclargs <module> <tag> [extra sources...]
set args $argv
lassign $args module tag
cd [file dirname [file normalize [info script]]]
file mkdir out_$tag
read_verilog ../rtl/$module.v
foreach f [lrange $args 2 end] { read_verilog $f }
read_xdc clock.xdc
synth_design -top $module -part xc7a35ticsg324-1L -mode out_of_context
opt_design
place_design
route_design
report_utilization    -file out_$tag/utilization_routed.rpt
report_timing_summary -file out_$tag/timing_routed.rpt
