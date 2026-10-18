`timescale 1ns / 1ps
// Clock gate: a BUFGCE in synthesis; in RTL simulation the usual latch-and-AND model, which behaves the same
// (en is sampled while clk is low, so the gated clock never glitches).
module clk_gate (input wire clk, input wire en, output wire gclk);
`ifdef SYNTHESIS
    BUFGCE bg (.I(clk), .CE(en), .O(gclk));
`else
    reg l = 1'b0;
    always @(clk or en) if (!clk) l = en;
    assign gclk = clk & l;
`endif
endmodule
