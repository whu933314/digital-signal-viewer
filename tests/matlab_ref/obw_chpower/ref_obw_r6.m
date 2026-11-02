% Round-6 reference numbers for dsv_chmeas (MATLAB R2025a, functions only: validateattributes, obw, powerbw, bandpower).
% A. half: which validateattributes attributes exist for half, and which obw/powerbw/bandpower arguments therefore
%    reject half with half:error:FunctionNotDefinedForHalf (FREQRANGE, R, bandpower's F and FREQRANGE) or accept it (P, RBW, Fs).
% B. The "Instead its type was <class>." line of invalidType: omitted for char and for EMPTY cells, printed otherwise.
%    Empty non-numeric FREQRANGE (cell / datetime / duration) is converted with double() and fails there.
% C. Numeric cases that pin one rule each: non-uniform grids (where the missing bin width goes), spectra that are all-zero
%    before the range start (the i==1 clamp of the inverse interpolation), PSD exactly 0 at the x-dB crossing (realmin floor),
%    powerbw ranges that contain the DC bin (the reference level uses the undoubled PSD).
% D. bandpower with a single, non-integer F: MATLAB computes in single (result 110 exactly); the same F widened to double.
% Run from this folder: reads in_x_real.txt, writes ref_obw_r6.json (relative paths only).
function ref_obw_r6()
xr = load('in_x_real.txt');
f5 = (0:4).' * 10;
p5 = [1; 2; 5; 2; 1];
fnu = [0; 5; 15; 30; 40];          % non-uniform, starts at 0 (missing width goes to the end)
fneg = [-7; -2; 3; 9; 20];         % non-uniform, negative start (missing width goes to the front)
q2 = [p5, [5; 1; 1; 1; 2]];        % two channels with different peaks
q = [4; 5; 1; 1; 1];               % DC bin becomes the peak only after doubling
fcen = [-20; -10; 0; 10; 20];
ffrac = [0.1; 10.1; 20.1; 30.1; 40.1];
c = {};
% --- A1. validateattributes attributes on half
c{end+1} = tc('va_half_nonzero',     @() validateattributes(half(3), {'numeric'}, {'nonzero'}), 0);
c{end+1} = tc('va_half_increasing',  @() validateattributes(half([10 30]), {'numeric'}, {'increasing'}), 0);
c{end+1} = tc('va_half_finite',      @() validateattributes(half([10 30]), {'numeric'}, {'finite'}), 0);
c{end+1} = tc('va_half_real',        @() validateattributes(half([10 30]), {'numeric'}, {'real'}), 0);
c{end+1} = tc('va_half_size',        @() validateattributes(half([10 30]), {'numeric'}, {'size', [1 2]}), 0);
c{end+1} = tc('va_half_vector',      @() validateattributes(half([10 30]), {'numeric'}, {'vector'}), 0);
c{end+1} = tc('va_half_scalar',      @() validateattributes(half(3), {'numeric'}, {'scalar'}), 0);
c{end+1} = tc('va_half_positive',    @() validateattributes(half(3), {'numeric'}, {'positive'}), 0);
c{end+1} = tc('va_half_nonempty',    @() validateattributes(half(3), {'numeric'}, {'nonempty'}), 0);
c{end+1} = tc('va_half_nonnegative', @() validateattributes(half(3), {'numeric'}, {'nonnegative'}), 0);
c{end+1} = tc('va_half_less',        @() validateattributes(half(3), {'numeric'}, {'<', 100}), 0);
c{end+1} = tc('va_half_ge',          @() validateattributes(half(3), {'numeric'}, {'>=', 1}), 0);
c{end+1} = tc('va_half_numel',       @() validateattributes(half([10 30]), {'numeric'}, {'numel', 2}), 0);
c{end+1} = tc('va_half_numeric',     @() validateattributes(half(3), {'numeric'}, {}), 0);
c{end+1} = tc('va_half_floatclass',  @() validateattributes(half(3), {'double', 'single'}, {}), 0);
c{end+1} = tc('va_half_scalar_increasing', @() validateattributes(half(3), {'numeric'}, {'increasing'}), 0);
c{end+1} = tc('va_half_2d',          @() validateattributes(half([10 30]), {'numeric'}, {'2d'}), 0);
% --- A2. half through obw / powerbw / bandpower: rejected (FREQRANGE, R, bandpower F / FREQRANGE)
c{end+1} = tc('h1_obw_range_half',        @() obw(p5, f5, half([10 30]), 99), 4);
c{end+1} = tc('h2_obw_range_half_frac',   @() obw(p5, f5, half([10.1 30.3]), 99), 4);
c{end+1} = tc('h3_obw_time_range_half',   @() obw(xr, 1e4, half([500 3000])), 4);
c{end+1} = tc('h4_pbw_range_half',        @() powerbw(p5, f5, half([10 30]), 3), 4);
c{end+1} = tc('h5_pbw_time_range_half',   @() powerbw(xr, 1e4, half([1000 1500]), 3), 4);
c{end+1} = tc('h6_pbw_R_half',            @() powerbw(p5, f5, [], half(3)), 4);
c{end+1} = tc('h7_pbw_R_half_frac',       @() powerbw(p5, f5, [], half(2.7)), 4);
c{end+1} = tc('h8_pbw_time_R_half',       @() powerbw(xr, 1e4, [], half(3)), 4);
c{end+1} = tc('h9_bp_f_half',             @() bandpower(p5, half(f5), 'psd'), 1);
c{end+1} = tc('h10_bp_range_half',        @() bandpower(p5, f5, half([5 35]), 'psd'), 1);
c{end+1} = tc('h11_bp_range_half_frac',   @() bandpower(p5, f5, half([5.3 35.7]), 'psd'), 1);
c{end+1} = tc('h12_obw_sxx_range_half',   @() obw(p5, f5, 10, half([10 30]), 99), 4);
c{end+1} = tc('h13_bp_f_half_with_range', @() bandpower(p5, half(f5), [5 35], 'psd'), 1);
c{end+1} = tc('h14_obw_single_pxx_range_half', @() obw(single(p5), f5, half([10 30]), 99), 4);
% --- A3. order: the checks before 'increasing' / 'nonzero' still fire first; the ones after it never do
c{end+1} = tc('o1_obw_time_range_half_inf',   @() obw(xr, 1e4, half([500 Inf])), 4);
c{end+1} = tc('o2_obw_range_half_decreasing', @() obw(p5, f5, half([30 10]), 99), 4);
c{end+1} = tc('o3_obw_range_half_1x3',        @() obw(p5, f5, half([10 30 50]), 99), 4);
c{end+1} = tc('o4_obw_range_half_out',        @() obw(p5, f5, half([10 60]), 99), 4);
c{end+1} = tc('o5_obw_time_range_half_scalar', @() obw(xr, 1e4, half(1000)), 4);
c{end+1} = tc('o6_obw_range_half_P_bad',      @() obw(p5, f5, half([10 30]), 100), 4);
c{end+1} = tc('o7_obw_int16_pxx_range_half',  @() obw(int16(p5), f5, half([10 30]), 99), 4);
c{end+1} = tc('o8_pbw_R_half_vec',            @() powerbw(p5, f5, [], half([3 4])), 4);
c{end+1} = tc('o9_pbw_R_half_nan',            @() powerbw(p5, f5, [], half(NaN)), 4);
c{end+1} = tc('o10_pbw_R_half_inf',           @() powerbw(p5, f5, [], half(Inf)), 4);
c{end+1} = tc('o11_pbw_R_half_empty',         @() powerbw(p5, f5, [], half([])), 4);
c{end+1} = tc('o12_pbw_R_half_zero',          @() powerbw(p5, f5, [], half(0)), 4);
c{end+1} = tc('o13_pbw_range_half_R_zero',    @() powerbw(p5, f5, half([10 30]), 0), 4);
c{end+1} = tc('o14_bp_range_half_1x3',        @() bandpower(p5, f5, half([5 35 40]), 'psd'), 1);
c{end+1} = tc('o15_bp_range_half_out',        @() bandpower(p5, f5, half([5 60]), 'psd'), 1);
c{end+1} = tc('o16_bp_range_half_decreasing', @() bandpower(p5, f5, half([35 5]), 'psd'), 1);
c{end+1} = tc('o17_bp_f_half_short',          @() bandpower(p5, half(f5(1:4)), 'psd'), 1);
c{end+1} = tc('o18_bp_f_half_inf',            @() bandpower(p5, half([0; 10; 20; 30; Inf]), 'psd'), 1);
c{end+1} = tc('o19_bp_f_half_matrix',         @() bandpower(p5, half([f5 f5]), 'psd'), 1);
c{end+1} = tc('o20_bp_f_half_decreasing',     @() bandpower(p5, half(flipud(f5)), 'psd'), 1);
% --- A4. half accepted: P, RBW, Fs (and an empty half FREQRANGE = not given)
c{end+1} = tc('a1_obw_rbw_half',       @() obw(p5, f5, half(10), [], 99), 4);
c{end+1} = tc('a2_obw_rbw_half_frac',  @() obw(p5, f5, half(10.3), [], 99), 4);
c{end+1} = tc('a3_obw_P_half',         @() obw(p5, f5, [], half(90)), 4);
c{end+1} = tc('a4_obw_P_half_frac',    @() obw(p5, f5, [], half(99.9)), 4);
c{end+1} = tc('a5_obw_fs_half',        @() obw(xr, half(1e4)), 4);
c{end+1} = tc('a6_obw_fs_half_frac',   @() obw(xr, half(3333.3)), 4);
c{end+1} = tc('a7_pbw_fs_half',        @() powerbw(xr, half(1e4)), 4);
c{end+1} = tc('a8_obw_range_half_empty', @() obw(p5, f5, half([]), 99), 4);
c{end+1} = tc('a9_obw_P_half_nan',     @() obw(p5, f5, [], half(NaN)), 4);
c{end+1} = tc('a10_obw_fs_half_zero',  @() obw(xr, half(0)), 4);
c{end+1} = tc('a11_obw_rbw_half_small', @() obw(p5, f5, half(5), [], 99), 4);
% --- B1. validateattributes: the "Instead its type was" line
c{end+1} = tc('v1_va_cell_empty',     @() validateattributes({}, {'numeric'}, {}), 0);
c{end+1} = tc('v2_va_cell_0x2',       @() validateattributes(cell(0, 2), {'numeric'}, {}), 0);
c{end+1} = tc('v3_va_cell_1x0',       @() validateattributes(cell(1, 0), {'numeric'}, {}), 0);
c{end+1} = tc('v4_va_cell_1elem',     @() validateattributes({[]}, {'numeric'}, {}), 0);
c{end+1} = tc('v5_va_cell_2elem',     @() validateattributes({1, 2}, {'numeric'}, {}), 0);
c{end+1} = tc('v6_va_int16_empty',    @() validateattributes(int16([]), {'double', 'single'}, {}), 0);
c{end+1} = tc('v7_va_logical_empty',  @() validateattributes(logical([]), {'double', 'single'}, {}), 0);
c{end+1} = tc('v8_va_half_empty',     @() validateattributes(half([]), {'double', 'single'}, {}), 0);
c{end+1} = tc('v9_va_struct_empty',   @() validateattributes(struct([]), {'numeric'}, {}), 0);
c{end+1} = tc('v10_va_datetime_empty', @() validateattributes(datetime.empty, {'numeric'}, {}), 0);
c{end+1} = tc('v11_va_duration_empty', @() validateattributes(duration.empty, {'numeric'}, {}), 0);
c{end+1} = tc('v12_va_char_empty',    @() validateattributes('', {'numeric'}, {}), 0);
c{end+1} = tc('v13_va_char_1',        @() validateattributes('a', {'numeric'}, {}), 0);
c{end+1} = tc('v14_va_string_empty',  @() validateattributes(strings(0), {'numeric'}, {}), 0);
c{end+1} = tc('v15_va_int16_0x2',     @() validateattributes(zeros(0, 2, 'int16'), {'double', 'single'}, {}), 0);
% --- B2. through obw / powerbw / bandpower
c{end+1} = tc('e1_obw_P_cell_empty',      @() obw(p5, f5, [], {}), 4);
c{end+1} = tc('e2_obw_P_cell_1',          @() obw(p5, f5, [], {1}), 4);
c{end+1} = tc('e3_obw_pxx_cell_empty',    @() obw({}, f5), 4);
c{end+1} = tc('e4_obw_pxx_cell_0x2',      @() obw(cell(0, 2), f5), 4);
c{end+1} = tc('e5_obw_pxx_cell_1x0',      @() obw(cell(1, 0), f5), 4);
c{end+1} = tc('e6_obw_pxx_cell_1',        @() obw({1}, f5), 4);
c{end+1} = tc('e7_obw_pxx_int16_empty',   @() obw(int16([]), f5), 4);
c{end+1} = tc('e8_obw_pxx_logical_empty', @() obw(logical([]), f5), 4);
c{end+1} = tc('e9_obw_pxx_half_empty',    @() obw(half([]), f5), 4);
c{end+1} = tc('e10_obw_pxx_int16_0x3',    @() obw(int16(zeros(0, 3)), f5), 4);
c{end+1} = tc('e11_obw_P_struct_empty',   @() obw(p5, f5, [], struct([])), 4);
c{end+1} = tc('e12_obw_P_datetime_empty', @() obw(p5, f5, [], datetime.empty), 4);
c{end+1} = tc('e13_obw_P_logical_empty',  @() obw(p5, f5, [], logical([])), 4);
c{end+1} = tc('e14_obw_P_char_empty',     @() obw(p5, f5, [], ''), 4);
c{end+1} = tc('e15_pbw_R_cell_empty',     @() powerbw(p5, f5, [], {}), 4);
c{end+1} = tc('e16_bp_range_cell_empty',  @() bandpower(p5, f5, {}, 'psd'), 1);
c{end+1} = tc('e17_bp_pxx_cell_empty',    @() bandpower({}, f5, 'psd'), 1);
c{end+1} = tc('e18_bp_f_cell_empty',      @() bandpower(p5, {}, 'psd'), 1);
c{end+1} = tc('e19_bp_x_cell_empty',      @() bandpower({}), 1);
c{end+1} = tc('e20_obw_x_cell_empty',     @() obw({}, 1e4), 4);
c{end+1} = tc('e21_pbw_time_range_cell_2', @() powerbw(xr, 1e4, {1, 2}, 3), 4);
c{end+1} = tc('e22_obw_sxx_cell_empty',   @() obw({}, f5, 10, [], 99), 4);
c{end+1} = tc('e23_bp_pxx_cell_1',        @() bandpower({1}, f5, 'psd'), 1);
% --- B3. empty non-numeric FREQRANGE: converted with double(), fails there (numeric / logical / char empties pass as "not given")
c{end+1} = tc('r1_obw_range_cell_empty',     @() obw(p5, f5, {}, 99), 4);
c{end+1} = tc('r2_obw_range_cell_0x2',       @() obw(p5, f5, cell(0, 2), 99), 4);
c{end+1} = tc('r3_obw_time_range_cell_empty', @() obw(xr, 1e4, {}), 4);
c{end+1} = tc('r4_pbw_range_cell_empty',     @() powerbw(p5, f5, {}, 3), 4);
c{end+1} = tc('r5_obw_range_datetime_empty', @() obw(p5, f5, datetime.empty, 99), 4);
c{end+1} = tc('r6_obw_range_duration_empty', @() obw(p5, f5, duration.empty, 99), 4);
c{end+1} = tc('r7_obw_range_int16_empty',    @() obw(p5, f5, int16([]), 99), 4);
c{end+1} = tc('r8_obw_range_logical_empty',  @() obw(p5, f5, logical([]), 99), 4);
c{end+1} = tc('r9_obw_range_int16_0x2',      @() obw(p5, f5, zeros(0, 2, 'int16'), 99), 4);
c{end+1} = tc('r10_obw_range_char_empty',    @() obw(p5, f5, '', 99), 4);
c{end+1} = tc('r11_pbw_time_range_cell_empty', @() powerbw(xr, 1e4, {}, 3), 4);
c{end+1} = tc('r12_obw_sxx_range_cell_empty', @() obw(p5, f5, 10, {}, 99), 4);
% --- C1. non-uniform grids (where the missing bin width goes)
c{end+1} = tc('u1_obw_nu',           @() obw(p5, fnu), 4);
c{end+1} = tc('u2_pbw_nu',           @() powerbw(p5, fnu), 4);
c{end+1} = tc('u3_bp_nu',            @() bandpower(p5, fnu, 'psd'), 1);
c{end+1} = tc('u4_bp_nu_range',      @() bandpower(p5, fnu, [5 30], 'psd'), 1);
c{end+1} = tc('u5_bp_nu_range_mid',  @() bandpower(p5, fnu, [7 33], 'psd'), 1);
c{end+1} = tc('u6_obw_nu_range',     @() obw(p5, fnu, [5 30], 99), 4);
c{end+1} = tc('u7_obw_nu_range_mid', @() obw(p5, fnu, [7 33], 90), 4);
c{end+1} = tc('u8_pbw_nu_range',     @() powerbw(p5, fnu, [5 30], 3), 4);
c{end+1} = tc('u9_pbw_nu_range_mid', @() powerbw(p5, fnu, [7 33], 3), 4);
c{end+1} = tc('u10_obw_nu_sxx',      @() obw(p5, fnu, 10, [], 99), 4);
c{end+1} = tc('u11_obw_neg',         @() obw(p5, fneg), 4);
c{end+1} = tc('u12_pbw_neg',         @() powerbw(p5, fneg), 4);
c{end+1} = tc('u13_bp_neg',          @() bandpower(p5, fneg, 'psd'), 1);
c{end+1} = tc('u14_obw_neg_range',   @() obw(p5, fneg, [-2 9], 99), 4);
c{end+1} = tc('u15_pbw_neg_range',   @() powerbw(p5, fneg, [-2 9], 3), 4);
c{end+1} = tc('u16_obw_nu_mat',      @() obw(q2, fnu), 4);
c{end+1} = tc('u17_pbw_nu_mat',      @() powerbw(q2, fnu), 4);
c{end+1} = tc('u18_bp_nu_mat',       @() bandpower(q2, fnu, 'psd'), 1);
% --- C2. spectrum all-zero before the range start (inverse interpolation index clamp)
c{end+1} = tc('c1_obw_zero_head_range_0_20',  @() obw([0; 0; 0; 0; 1], f5, [0 20], 99), 4);
c{end+1} = tc('c2_obw_zero_head_range_0_25',  @() obw([0; 0; 0; 0; 1], f5, [0 25], 99), 4);
c{end+1} = tc('c3_obw_zero_head_range_0_30',  @() obw([0; 0; 0; 0; 1], f5, [0 30], 99), 4);
c{end+1} = tc('c4_obw_zero_head_full',        @() obw([0; 0; 0; 0; 1], f5), 4);
c{end+1} = tc('c5_obw_zero_tail_range_20_40', @() obw([1; 0; 0; 0; 0], f5, [20 40], 99), 4);
c{end+1} = tc('c6_obw_zero_mid_range_10_30',  @() obw([1; 0; 0; 0; 1], f5, [10 30], 99), 4);
c{end+1} = tc('c7_pbw_zero_head_range_0_20',  @() powerbw([0; 0; 0; 0; 1], f5, [0 20], 3), 4);
c{end+1} = tc('c8_obw_zero_head_P50',         @() obw([0; 0; 0; 0; 1], f5, [0 20], 50), 4);
% --- C3. PSD exactly 0 (or denormal) at the x-dB crossing (realmin floor of the hit bin)
c{end+1} = tc('z1_pbw_zero_sides',       @() powerbw([0; 0; 5; 0; 0], f5), 4);
c{end+1} = tc('z2_pbw_zero_sides_R10',   @() powerbw([0; 1; 5; 1; 0], f5, [], 10), 4);
c{end+1} = tc('z3_pbw_zero_sides_range', @() powerbw([0; 0; 5; 0; 0], f5, [10 30], 3), 4);
c{end+1} = tc('z4_pbw_zero_range_mean',  @() powerbw([5; 0; 0; 0; 5], f5, [10 30], 3), 4);
c{end+1} = tc('z5_pbw_denormal_sides',   @() powerbw([1e-320; 0; 5; 0; 1e-320], f5), 4);
c{end+1} = tc('z6_obw_zero_sides',       @() obw([0; 0; 5; 0; 0], f5), 4);
% --- C4. DC-bin doubling: peak search uses the doubled PSD, the range reference level does not
c{end+1} = tc('d1_pbw_dc_peak_after_doubling', @() powerbw(q, f5), 4);
c{end+1} = tc('d2_pbw_no_dc_grid',       @() powerbw(q, f5 + 1), 4);
c{end+1} = tc('d3_pbw_centered_dc_mid',  @() powerbw([1; 1; 3; 5; 1], fcen), 4);
c{end+1} = tc('d4_pbw_centered_dc_mid2', @() powerbw([1; 4; 5; 1; 1], fcen), 4);
c{end+1} = tc('d5_pbw_dc_range_incl',    @() powerbw(q, f5, [0 20], 3), 4);
c{end+1} = tc('d6_pbw_dc_sxx',           @() powerbw(q, f5, 10, [], 3), 4);
c{end+1} = tc('d7_pbw_negative_start_grid', @() powerbw(q, f5 - 10), 4);
c{end+1} = tc('t9_pbw_range_lowend',     @() powerbw(p5, f5, [0 5], 3), 4);
c{end+1} = tc('t10_pbw_range_highend',   @() powerbw(p5, f5, [35 40], 3), 4);
% --- D. bandpower with single F (non-integer): single arithmetic vs the same F widened to double
c{end+1} = tc('s1_bp_f_single_frac',           @() bandpower(p5, single(ffrac), 'psd'), 1);
c{end+1} = tc('s2_bp_f_double_of_single_frac', @() bandpower(p5, double(single(ffrac)), 'psd'), 1);
c{end+1} = tc('s3_bp_f_single_int',            @() bandpower(p5, single(f5), 'psd'), 1);
c{end+1} = tc('s4_bp_range_single_frac',       @() bandpower(p5, f5, single([5.3 35.7]), 'psd'), 1);
c{end+1} = tc('s5_bp_range_double_of_single_frac', @() bandpower(p5, f5, double(single([5.3 35.7])), 'psd'), 1);
c{end+1} = tc('s6_bp_f_double_frac',           @() bandpower(p5, ffrac, 'psd'), 1);
R = struct('version', version, 'cases', {c});
fid = fopen('ref_obw_r6.json', 'w');
fprintf(fid, '%s', jsonencode(R));
fclose(fid);
end

function s = tc(name, fn, nout)
% Call fn and keep either its outputs (class, size, %.17g text of the value widened to double) or the error.
s = struct('name', name, 'ok', true, 'id', '', 'message', '', 'vals', {{}}, 'sizes', {{}}, 'classes', {{}});
out = cell(1, nout);
try
    if nout == 0
        fn();
    else
        [out{:}] = fn();
    end
catch e
    s.ok = false;
    s.id = e.identifier;
    s.message = e.message;
    return
end
for k = 1:nout
    s.classes{k} = class(out{k});
    v = double(out{k});
    s.sizes{k} = size(v);
    s.vals{k} = arrayfun(@(t) sprintf('%.17g', t), v(:).', 'UniformOutput', false);
end
end
