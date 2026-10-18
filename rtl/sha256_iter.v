`timescale 1ns/1ps
// SHA-256 compression, one round per clock (FIPS 180-4). Matches sha256_ref.compress.
// start loads block and the working state from h_in; 64 rounds follow; done pulses one cycle after the last
// round with h_out = h_in + state. h_in must be held for the whole operation (the caller keeps it in a register
// or ties it to a constant), so the core does not copy it: 256 flip-flops saved.
// Message schedule computed on the fly in a 16-word shift register. Latency: 66 cycles from the start cycle to done.
module sha256_iter (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,
    input  wire [255:0] h_in,
    input  wire [511:0] block,
    output reg  [255:0] h_out,
    output reg          done,
    output wire         busy
);
    reg [31:0] a, b, c, d, e, f, g, h;
    reg [511:0] w;              // w[511:480] = W[t]
    reg [5:0] t;
    reg run, fin;
    assign busy = run | fin;

    function [31:0] k;
        input [5:0] i;
        case (i)
        0: k = 32'h428a2f98;
        1: k = 32'h71374491;
        2: k = 32'hb5c0fbcf;
        3: k = 32'he9b5dba5;
        4: k = 32'h3956c25b;
        5: k = 32'h59f111f1;
        6: k = 32'h923f82a4;
        7: k = 32'hab1c5ed5;
        8: k = 32'hd807aa98;
        9: k = 32'h12835b01;
        10: k = 32'h243185be;
        11: k = 32'h550c7dc3;
        12: k = 32'h72be5d74;
        13: k = 32'h80deb1fe;
        14: k = 32'h9bdc06a7;
        15: k = 32'hc19bf174;
        16: k = 32'he49b69c1;
        17: k = 32'hefbe4786;
        18: k = 32'h0fc19dc6;
        19: k = 32'h240ca1cc;
        20: k = 32'h2de92c6f;
        21: k = 32'h4a7484aa;
        22: k = 32'h5cb0a9dc;
        23: k = 32'h76f988da;
        24: k = 32'h983e5152;
        25: k = 32'ha831c66d;
        26: k = 32'hb00327c8;
        27: k = 32'hbf597fc7;
        28: k = 32'hc6e00bf3;
        29: k = 32'hd5a79147;
        30: k = 32'h06ca6351;
        31: k = 32'h14292967;
        32: k = 32'h27b70a85;
        33: k = 32'h2e1b2138;
        34: k = 32'h4d2c6dfc;
        35: k = 32'h53380d13;
        36: k = 32'h650a7354;
        37: k = 32'h766a0abb;
        38: k = 32'h81c2c92e;
        39: k = 32'h92722c85;
        40: k = 32'ha2bfe8a1;
        41: k = 32'ha81a664b;
        42: k = 32'hc24b8b70;
        43: k = 32'hc76c51a3;
        44: k = 32'hd192e819;
        45: k = 32'hd6990624;
        46: k = 32'hf40e3585;
        47: k = 32'h106aa070;
        48: k = 32'h19a4c116;
        49: k = 32'h1e376c08;
        50: k = 32'h2748774c;
        51: k = 32'h34b0bcb5;
        52: k = 32'h391c0cb3;
        53: k = 32'h4ed8aa4a;
        54: k = 32'h5b9cca4f;
        55: k = 32'h682e6ff3;
        56: k = 32'h748f82ee;
        57: k = 32'h78a5636f;
        58: k = 32'h84c87814;
        59: k = 32'h8cc70208;
        60: k = 32'h90befffa;
        61: k = 32'ha4506ceb;
        62: k = 32'hbef9a3f7;
        63: k = 32'hc67178f2;
        endcase
    endfunction

    function [31:0] rotr;
        input [31:0] x;
        input [4:0] n;
        rotr = (x >> n) | (x << (6'd32 - n));
    endfunction

    wire [31:0] wt = w[511:480];
    wire [31:0] w1 = w[479:448], w9 = w[223:192], w14 = w[63:32];
    wire [31:0] s0 = rotr(w1, 7) ^ rotr(w1, 18) ^ (w1 >> 3);
    wire [31:0] s1 = rotr(w14, 17) ^ rotr(w14, 19) ^ (w14 >> 10);
    wire [31:0] t1 = h + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + k(t) + wt;
    wire [31:0] t2 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 1'b0; fin <= 1'b0; done <= 1'b0; t <= 6'd0;
        end else begin
            done <= 1'b0;
            if (start && !busy) begin
                {a, b, c, d, e, f, g, h} <= h_in;
                w <= block; t <= 6'd0; run <= 1'b1;
            end else if (run) begin
                {a, b, c, d, e, f, g, h} <= {t1 + t2, a, b, c, d + t1, e, f, g};
                w <= {w[479:0], wt + s0 + w9 + s1};
                t <= t + 6'd1;
                if (t == 6'd63) begin run <= 1'b0; fin <= 1'b1; end
            end else if (fin) begin
                h_out <= {h_in[255:224] + a, h_in[223:192] + b, h_in[191:160] + c, h_in[159:128] + d,
                          h_in[127:96] + e, h_in[95:64] + f, h_in[63:32] + g, h_in[31:0] + h};
                fin <= 1'b0; done <= 1'b1;
            end
        end
    end
endmodule
