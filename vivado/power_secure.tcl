# Activity-based power in mW, with the per-instance split (cascade vs hash core).
# Usage: -tclargs <tag> <tb> [saif name, default activity] -> out_<tag>/power_<saif>_mw.rpt
lassign $argv tag tb saif
if {$saif eq ""} { set saif activity }
cd [file dirname [file normalize [info script]]]
open_checkpoint out_$tag/routed.dcp
read_saif out_$tag/$saif.saif -strip_path $tb/dut
set_units -power mW
# Vivado takes clock-net activity from the clock constraints and ignores both the SAIF and the BUFGCE enable, so a
# gated clock would be costed at 50 MHz even while it is stopped. While idle the gate is off (the simulation shows
# zero toggles on gclk), so declare that: the clock after the gate runs at 50 MHz / 10^6, i.e. effectively stopped.
if {$saif eq "idle" && [llength [get_cells -quiet cg/bg]]} {
    create_generated_clock -name gclk_off -source [get_pins cg/bg/I0] -divide_by 1000000 [get_pins cg/bg/O]
}
report_power -hierarchical_depth 2 -file [expr {$saif eq "activity" ? "out_$tag/power_saif_mw.rpt" : "out_$tag/power_${saif}_mw.rpt"}]
