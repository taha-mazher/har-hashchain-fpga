`timescale 1ns / 1ps
// Cascade plus a tamper-evident log: every window's result is folded into a SHA-256 hash chain, bit-exact
// with hw_fix/chain.py.
//   record  = prev hash (32 B) | window number (4 B) | {3'b0, class, sensor_en, used_s2}   (37 B, one block)
//   plain   : prev <= SHA256(record)                                     1 compression from the IV
//   KEYED=1 : prev <= HMAC-SHA256(key, record)                           2 compressions from the key's midstates
//             inner = compress(MID_I, record block); prev <= compress(MID_O, inner block). The inner hash is
//             parked in the prev register, which pass 1 no longer needs, so HMAC adds no 256-bit register.
//             The key exists only as its two midstates (MID_I, MID_O), baked in at build time.
//   KEYED=2 : forward secure. prev <= HMAC-SHA256(k, record), then k <= SHA256(k), overwriting the old key, so a key
//             read out of a stolen device cannot re-sign earlier windows. 5 compressions: ipad midstate -> r,
//             inner -> prev, opad midstate -> r, outer -> prev, SHA256(k) -> k. Adds k and r (512 flip-flops).
//             k starts at KEY0 on reset so each recording replays chain.py; a device would keep k in
//             non-volatile memory instead. Defaults are chain.KEY's.
// GATE=1  : one BUFGCE stops the clock to the whole design between windows; it runs only while features load,
//           the cascade or the hash is busy, or a one-cycle flag has to clear.
// The chain and window number restart at reset (one recording). The hash is read 32 bits at a time
// (hash_sel 0 = most significant word) so the design fits the package's pins.
// ponytail: one record in flight; a window finishing while the previous hash runs is dropped. At one window per 1.28 s
// against ~7 us of hashing that cannot happen; add a one-entry queue if windows ever come back to back.
module cascade_secure #(
    parameter N2 = 9, H2 = 8, FA = 12, FB = 12,
    parameter signed [32:0] TAU = 0,
    parameter signed [32:0] TAU_KEEP = 0,
    parameter KEEP_ALL = 1,
    parameter [4:0] MASK  = 5'b00110,
    parameter [4:0] MASK2 = 5'b00110,
    parameter W_FILE = "w.mem",
    parameter B_FILE = "b.mem",
    parameter KEYED = 0,            // 0: plain SHA-256 chain, 1: HMAC-SHA256 chain, 2: forward-secure HMAC chain
    parameter GATE  = 0,            // 1: clock gated off between windows
    parameter LITE  = 1,            // 1: sha256_lite, 0: sha256_iter
    parameter [255:0] MID_I = 256'h82a26513761c632fbc26416e638933010a68c71d1fe0fa8dae920cf900f3f280,
    parameter [255:0] MID_O = 256'h2367d3671fd96f8babce4f4dfcaef265bc99abd9c4550ac474cb6365b8eef166,
    parameter [255:0] KEY0  = 256'h000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [15:0] x_in,
    input  wire        x_valid,
    input  wire        start,
    output wire [2:0]  class_out,
    output wire        valid,
    output wire        busy,
    output wire        sensor_en,
    output wire        used_s2,
    input  wire [2:0]  hash_sel,
    output wire [31:0] hash_word,
    output reg         hash_valid   // pulses when the chain head includes the latest window
);
    localparam [255:0] IV = 256'h6a09e667bb67ae853c6ef372a54ff53a510e527f9b05688c1f83d9ab5be0cd19;
    localparam [255:0] IPAD = {32{8'h36}}, OPAD = {32{8'h5c}};
    localparam [2:0] LAST = KEYED == 2 ? 3'd4 : KEYED == 1 ? 3'd1 : 3'd0;

    wire gclk, cbusy, hbusy, hdone;
    reg  go;
    wire en = x_valid | start | cbusy | valid | go | hbusy | hdone | hash_valid;
    generate if (GATE) clk_gate cg (.clk(clk), .en(en), .gclk(gclk)); else assign gclk = clk; endgenerate

    cascade #(.N2(N2), .H2(H2), .FA(FA), .FB(FB), .TAU(TAU), .TAU_KEEP(TAU_KEEP), .KEEP_ALL(KEEP_ALL),
              .MASK(MASK), .MASK2(MASK2), .W_FILE(W_FILE), .B_FILE(B_FILE))
        net (.clk(gclk), .rst_n(rst_n), .x_in(x_in), .x_valid(x_valid), .start(start), .class_out(class_out),
             .valid(valid), .busy(cbusy), .sensor_en(sensor_en), .used_s2(used_s2));

    reg [255:0] prev;           // chain head (and the inner hash between the two HMAC passes)
    reg [255:0] k, r;           // KEYED=2 only: current key, and the midstate in use
    reg [31:0]  n;              // window number of the record being hashed
    reg [7:0]   rec;
    reg [2:0]   p;              // pass within the window, 0..LAST
    wire [255:0] h_out;
    assign busy = cbusy | go | hbusy;
    assign hash_word = prev[(3'd7 - hash_sel) * 32 +: 32];

    // padding: 0x80, zeros, then the message length in bits (+512 for the key block when keyed)
    wire [511:0] blk1 = {prev, n, rec, 8'h80, 144'd0, KEYED ? 64'd808 : 64'd296};
    wire [511:0] blk2 = {prev, 8'h80, 184'd0, 64'd768};
    reg  [511:0] block;
    reg  [255:0] h_in;
    always @* begin
        block = blk1; h_in = IV;
        if (KEYED == 1) begin block = p[0] ? blk2 : blk1; h_in = p[0] ? MID_O : MID_I; end
        if (KEYED == 2) begin
            h_in = p[0] ? r : IV;
            case (p)
                3'd0: block = {k ^ IPAD, IPAD};
                3'd1: block = blk1;
                3'd2: block = {k ^ OPAD, OPAD};
                3'd3: block = blk2;
                default: block = {k, 8'h80, 184'd0, 64'd256};
            endcase
        end
    end

    generate if (LITE)
        sha256_lite core (.clk(gclk), .rst_n(rst_n), .start(go), .h_in(h_in), .block(block), .h_out(h_out),
                          .done(hdone), .busy(hbusy));
    else
        sha256_iter core (.clk(gclk), .rst_n(rst_n), .start(go), .h_in(h_in), .block(block), .h_out(h_out),
                          .done(hdone), .busy(hbusy));
    endgenerate

    always @(posedge gclk or negedge rst_n) begin
        if (!rst_n) begin
            prev <= 256'd0; n <= 32'd0; rec <= 8'd0; go <= 1'b0; p <= 3'd0; hash_valid <= 1'b0;
            k <= KEY0; r <= 256'd0;
        end else begin
            go <= 1'b0; hash_valid <= 1'b0;
            if (valid && !hbusy && !go) begin
                rec <= {3'b000, class_out, sensor_en, used_s2};
                go <= 1'b1;
            end
            if (hdone) begin
                if (KEYED == 2 && p == 3'd4) k <= h_out;
                else if (KEYED == 2 && !p[0]) r <= h_out;
                else prev <= h_out;
                if (p != LAST) begin p <= p + 3'd1; go <= 1'b1; end
                else begin p <= 3'd0; n <= n + 32'd1; hash_valid <= 1'b1; end
            end
        end
    end
endmodule
