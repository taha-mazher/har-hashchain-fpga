# xsim batch: record switching activity of the implemented cascade_secure netlist over the whole test set
open_saif $::env(SPLIT_OUT)/$::env(SAIF_NAME).saif
log_saif [get_objects -r /tb_cascade_secure/dut/*]
run all
close_saif
quit
