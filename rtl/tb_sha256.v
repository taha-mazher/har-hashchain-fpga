// Checks rtl/sha256_core.v against out/sha256_vectors.mem (from sha256_ref.py): h_in block h_out per line.
`timescale 1ns/1ps
`ifndef DUT
`define DUT sha256_iter
`endif
module tb_sha256;
    parameter TEST_FILE = "../out/sha256_vectors.mem";
    reg clk = 1'b0, rst_n = 1'b0, start = 1'b0;
    reg [255:0] h_in, want;
    reg [511:0] block;
    wire [255:0] h_out;
    wire done, busy;
    integer fd, n, bad, cyc, worst;
    always #10 clk = ~clk;   // 50 MHz
    `DUT dut (.clk(clk), .rst_n(rst_n), .start(start), .h_in(h_in), .block(block), .h_out(h_out), .done(done), .busy(busy));
    initial begin
        fd = $fopen(TEST_FILE, "r");
        if (fd == 0) begin $display("RESULT FAIL cannot open %0s", TEST_FILE); $finish; end
        n = 0; bad = 0; worst = 0;
        repeat (3) @(posedge clk); rst_n = 1'b1;
        while ($fscanf(fd, "%h %h %h\n", h_in, block, want) == 3) begin
            @(negedge clk) start = 1'b1;
            @(negedge clk) start = 1'b0;
            cyc = 1;
            while (!done) begin @(negedge clk); cyc = cyc + 1; end
            if (cyc > worst) worst = cyc;
            if (h_out !== want) begin
                bad = bad + 1;
                if (bad <= 3) $display("MISMATCH vector %0d: got %h want %h", n, h_out, want);
            end
            n = n + 1;
        end
        $display("vectors=%0d errors=%0d cycles_start_to_done=%0d", n, bad, worst);
        $display("RESULT %0s", (bad == 0 && n > 0) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
