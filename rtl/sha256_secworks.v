`timescale 1ns/1ps
// Baseline: the open secworks SHA-256 core (third_party/secworks_sha256, BSD) behind the same ports as
// sha256_iter. It always starts from the SHA-256 IV (its init mode), so h_in is ignored: enough for the plain
// chain, where every window is one block from the IV. done pulses when the digest becomes valid.
module sha256_secworks (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,
    input  wire [255:0] h_in,
    input  wire [511:0] block,
    output wire [255:0] h_out,
    output reg          done,
    output wire         busy
);
    wire ready, valid;
    reg  started;
    assign busy = started | !ready;
    sha256_core core (.clk(clk), .reset_n(rst_n), .init(start & !busy), .next(1'b0), .mode(1'b1),
                      .block(block), .ready(ready), .digest(h_out), .digest_valid(valid));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin started <= 1'b0; done <= 1'b0; end
        else begin
            done <= started & ready & valid;
            if (start & !busy) started <= 1'b1;
            else if (ready & valid) started <= 1'b0;
        end
endmodule
