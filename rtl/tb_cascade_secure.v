`timescale 1ns / 1ps
// tb_cascade for cascade_secure.v: also checks the chain head after every window against out/chain_<name>.mem
// (from chain.py: class sensor_en used_s2 plain_hash hmac_hash fs_hash), column chosen by KEYED (+KEYED=<0|1|2> in
// netlist sims). +IDLE=<cycles>: instead of the test set, hold the design idle after reset (for idle power).
module tb_cascade_secure;
    parameter N2 = 9, H2 = 8, FA = 12, FB = 12, KEEP_ALL = 1;
    parameter signed [32:0] TAU = 0, TAU_KEEP = 0;
    parameter [4:0] MASK = 5'b00110, MASK2 = 5'b00110;
    parameter MEM_DIR = "mem/cascade_uci/";
    parameter TEST_FILE = "../out/cascade_uci.mem";
    parameter CHAIN_FILE = "../out/chain_uci.mem";
    parameter KEYED = 0, LITE = 1, GATE = 0;

    reg clk = 1'b0, rst_n = 1'b0, start = 1'b0, x_valid = 1'b0;
    reg [16*14-1:0] x = 0;  // widest model; +N2=<n> sets how many features are used (netlist sims have no parameters)
    reg [15:0] x_in = 16'd0;
    wire [2:0] class_out;
    wire valid, busy, sensor_en, used_s2, hash_valid;
    reg [2:0] hash_sel = 3'd0;
    wire [31:0] hash_word;
    always #10 clk = ~clk;  // 50 MHz

`ifdef NETLIST
    cascade_secure dut (.clk(clk), .rst_n(rst_n), .x_in(x_in), .x_valid(x_valid), .start(start), .class_out(class_out), .valid(valid),
                 .busy(busy), .sensor_en(sensor_en), .used_s2(used_s2), .hash_sel(hash_sel), .hash_word(hash_word), .hash_valid(hash_valid));
`else
    cascade_secure #(.N2(N2), .H2(H2), .FA(FA), .FB(FB), .TAU(TAU), .TAU_KEEP(TAU_KEEP), .KEEP_ALL(KEEP_ALL),
              .MASK(MASK), .MASK2(MASK2), .W_FILE({MEM_DIR, "w.mem"}), .B_FILE({MEM_DIR, "b.mem"}), .KEYED(KEYED), .LITE(LITE), .GATE(GATE))
        dut (.clk(clk), .rst_n(rst_n), .x_in(x_in), .x_valid(x_valid), .start(start), .class_out(class_out), .valid(valid),
             .busy(busy), .sensor_en(sensor_en), .used_s2(used_s2), .hash_sel(hash_sel), .hash_word(hash_word), .hash_valid(hash_valid));
`endif

    integer n2, fd, r, j, total, bad, correct, scored, n_s2, n_en, cyc, cyc1, cyc2;
    integer fc, keyed, hbad, hcyc, idle;
    reg [3:0] c0, c1, c2;
    reg [255:0] hp, hk, hf, want, got;
    reg [8*256:1] cf;
    reg [15:0] v;
    reg [3:0] flag, py, pen, pused, label;
    reg [8*256:1] tf;
    initial begin
        total = 0; bad = 0; correct = 0; scored = 0; n_s2 = 0; n_en = 0; cyc1 = 0; cyc2 = 0;
        if (!$value$plusargs("TEST=%s", tf)) tf = TEST_FILE;
        if (!$value$plusargs("N2=%d", n2)) n2 = N2;
        if (!$value$plusargs("CHAIN=%s", cf)) cf = CHAIN_FILE;
        if (!$value$plusargs("KEYED=%d", keyed)) keyed = KEYED;
        hbad = 0; hcyc = 0;
        if ($value$plusargs("IDLE=%d", idle)) begin
            #200 rst_n <= 1'b1;
            repeat (idle) @(posedge clk);
            $display("idle cycles=%0d", idle); $display("RESULT: PASS (idle)");
            $finish;
        end
        fc = $fopen(cf, "r");
        if (fc == 0) begin $display("cannot open %0s", cf); $finish; end
        fd = $fopen(tf, "r");
        if (fd == 0) begin $display("cannot open %0s", tf); $finish; end
        #200;  // gate-level GSR
        while (!$feof(fd)) begin
            r = $fscanf(fd, "%h", flag);
            if (r == 1) begin
                for (j = 0; j < n2; j = j + 1) begin r = $fscanf(fd, "%h", v); x[16 * j +: 16] = v; end
                r = $fscanf(fd, "%h %h %h %h\n", py, pen, pused, label);
                if (flag[0]) begin
                    rst_n <= 1'b0; @(posedge clk); @(posedge clk); rst_n <= 1'b1; @(posedge clk);
                end
                for (j = 0; j < n2; j = j + 1) begin
                    x_in <= x[16 * j +: 16]; x_valid <= 1'b1; @(posedge clk);
                end
                x_valid <= 1'b0;
                start <= 1'b1; @(posedge clk); start <= 1'b0;
                cyc = 1;
                while (!valid) begin
                    @(posedge clk); cyc = cyc + 1;
                    if (cyc > 2000) begin $display("TIMEOUT at window %0d", total); $display("RESULT: FAIL"); $finish; end
                end
                if (used_s2) cyc2 = cyc; else cyc1 = cyc;
                if (class_out != py[2:0] || sensor_en != pen[0] || used_s2 != pused[0]) begin
                    bad = bad + 1;
                    if (bad <= 10) $display("MISMATCH window %0d: rtl %0d/%0d/%0d python %0d/%0d/%0d",
                                             total, class_out, sensor_en, used_s2, py, pen, pused);
                end
                if (label != 4'hf) begin scored = scored + 1; if (class_out == label[2:0]) correct = correct + 1; end
                cyc = 0;
                while (!hash_valid) begin
                    @(posedge clk); cyc = cyc + 1;
                    if (cyc > 1000) begin $display("HASH TIMEOUT at window %0d", total); $display("RESULT: FAIL"); $finish; end
                end
                if (cyc > hcyc) hcyc = cyc;
                @(negedge clk);
                for (j = 0; j < 8; j = j + 1) begin hash_sel = j; #1 got[255 - 32 * j -: 32] = hash_word; end
                r = $fscanf(fc, "%h %h %h %h %h %h\n", c0, c1, c2, hp, hk, hf);
                want = keyed == 2 ? hf : keyed ? hk : hp;
                if (got !== want) begin
                    hbad = hbad + 1;
                    if (hbad <= 5) $display("HASH MISMATCH window %0d: rtl %h want %h", total, got, want);
                end
                n_s2 = n_s2 + used_s2; n_en = n_en + sensor_en;
                total = total + 1;
                @(posedge clk);
            end
        end
        $fclose(fd);
        $display("%0s keyed=%0d: windows=%0d mismatches=%0d hash_mismatches=%0d accuracy=%0d/%0d stage2=%0d sensor_on=%0d cycles stage1=%0d stage2=%0d hash_after_valid=%0d",
                 tf, keyed, total, bad, hbad, correct, scored, n_s2, n_en, cyc1, cyc2, hcyc);
        if (total == 0 || bad != 0 || hbad != 0) $display("RESULT: FAIL"); else $display("RESULT: PASS (bit-exact)");
        $finish;
    end
endmodule
