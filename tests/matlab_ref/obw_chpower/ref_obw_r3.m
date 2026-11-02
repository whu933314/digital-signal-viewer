% Round-3 reference numbers for dsv_chmeas (obw / powerbw / bandpower edge cases).
% Numeric functions only (obw, powerbw, bandpower); no figures, no scopes.
% Run from this folder: reads in_x_real.txt, writes ref_obw_r3.json (both relative paths).
function ref_obw_r3()
xr = load('in_x_real.txt');
fs = 1e4;
f5 = (0:4).' * 10;
p5 = [1; 2; 5; 2; 1];
pn = [1; NaN; 5; 2; 1];
c = {};
% --- 1-sample and tiny time-domain inputs
c{end+1} = tc('obw_1sample_vec',     @() obw([1.0], 1e4), 4);
c{end+1} = tc('obw_1sample_scalar',  @() obw(3.0, 1e4), 4);
c{end+1} = tc('obw_1sample_nofs',    @() obw(3.0), 4);
c{end+1} = tc('powerbw_1sample',     @() powerbw(3.0, 1e4), 4);
c{end+1} = tc('powerbw_1sample_vec', @() powerbw([1.0], 1e4), 4);
c{end+1} = tc('obw_1sample_badrange', @() obw(3.0, 1e4, [0 6000]), 4);
c{end+1} = tc('obw_2sample_col',     @() obw([1; 2], 1e4), 4);
c{end+1} = tc('obw_2sample_row',     @() obw([1 2], 1e4), 4);
c{end+1} = tc('powerbw_2sample_col', @() powerbw([1; 2], 1e4), 4);
c{end+1} = tc('obw_3sample_row',     @() obw([1 3 2], 1e4), 4);
c{end+1} = tc('obw_3sample_col',     @() obw([1; 3; 2], 1e4), 4);
% --- empty time-domain inputs
c{end+1} = tc('obw_empty_00',  @() obw([], 1e4), 4);
c{end+1} = tc('obw_empty_01',  @() obw(zeros(0,1), 1e4), 4);
c{end+1} = tc('obw_empty_10',  @() obw(zeros(1,0), 1e4), 4);
c{end+1} = tc('obw_empty_50',  @() obw(zeros(5,0), 1e4), 4);
c{end+1} = tc('powerbw_empty_00', @() powerbw([], 1e4), 4);
c{end+1} = tc('powerbw_empty_50', @() powerbw(zeros(5,0), 1e4), 4);
% --- P = NaN and friends
c{end+1} = tc('obw_P_nan',      @() obw(p5, f5, [], NaN), 4);
c{end+1} = tc('obw_P_nan2',     @() obw(p5, f5, [], [NaN NaN]), 4);
c{end+1} = tc('obw_P_inf',      @() obw(p5, f5, [], Inf), 4);
c{end+1} = tc('powerbw_R_nan',  @() powerbw(p5, f5, [], NaN), 4);
c{end+1} = tc('powerbw_R_zero', @() powerbw(p5, f5, [], 0), 4);
% --- NaN / Inf inside the spectrum
c{end+1} = tc('obw_pxx_nan',          @() obw(pn, f5), 4);
c{end+1} = tc('powerbw_pxx_nan',      @() powerbw(pn, f5), 4);
c{end+1} = tc('obw_pxx_nan_range',    @() obw(pn, f5, [10 30]), 4);
c{end+1} = tc('powerbw_pxx_nan_range',@() powerbw(pn, f5, [10 30]), 4);
c{end+1} = tc('powerbw_pxx_allnan',   @() powerbw([NaN; NaN; NaN], [0; 10; 20]), 4);
c{end+1} = tc('powerbw_pxx_nanpeak',  @() powerbw([1; 2; NaN; 2; 1], f5), 4);
c{end+1} = tc('powerbw_pxx_nan_twocol', @() powerbw([pn, p5], f5), 4);
c{end+1} = tc('obw_pxx_inf',          @() obw([1; Inf; 5; 2; 1], f5), 4);
c{end+1} = tc('powerbw_pxx_inf',      @() powerbw([1; Inf; 5; 2; 1], f5), 4);
c{end+1} = tc('obw_sxx_nan_rbw',      @() obw(pn, f5, 10, [], 99), 4);
c{end+1} = tc('powerbw_huge_R1e4',    @() powerbw(1e308*ones(5,1), f5, [], 1e4), 4);
c{end+1} = tc('powerbw_time_huge_R1e4', @() powerbw((0:4).'*1e300, 3.0, [], 1e4), 4);
c{end+1} = tc('bandpower_pxx_nan',    @() bandpower(pn, f5, 'psd'), 1);
% --- invalidType texts
c{end+1} = tc('obw_P_char',        @() obw(p5, f5, [], '99'), 4);
c{end+1} = tc('obw_P_cell',        @() obw(p5, f5, [], {99, 1}), 4);
c{end+1} = tc('obw_range_cell',    @() obw(p5, f5, {0, 1}, 99), 4);
c{end+1} = tc('obw_F_char',        @() obw(p5, 'abc'), 4);
c{end+1} = tc('obw_F_logical',     @() obw(p5, true(5,1)), 4);
c{end+1} = tc('obw_X_char',        @() obw('abc', 1e4), 4);
c{end+1} = tc('powerbw_Fs_char1',  @() powerbw(xr, 'a'), 4);
c{end+1} = tc('powerbw_Fs_logical1', @() powerbw(xr, true), 4);
c{end+1} = tc('powerbw_time_range_cell', @() powerbw(xr, fs, {0, 1}, 3), 4);
c{end+1} = tc('obw_time_range_scalar', @() obw(xr, fs, 1000, 99), 4);
c{end+1} = tc('obw_power_range_scalar', @() obw(p5, f5, 10, 1000, 99), 4);
c{end+1} = tc('obw_rbw_complex',   @() obw(p5, f5, 20+1i, [], 99), 4);
c{end+1} = tc('obw_Fs_complex',    @() obw(xr, 1e4+1i), 4);
c{end+1} = tc('powerbw_Fs_neg',    @() powerbw(xr, -1), 4);
c{end+1} = tc('bandpower_F_cell',  @() bandpower(p5, {0, [1 2]}, 'psd'), 1);
c{end+1} = tc('bandpower_X_logical', @() bandpower(true(3,1)), 1);
c{end+1} = tc('bandpower_range_cell', @() bandpower(p5, f5, {0, 10}, 'psd'), 1);
% --- dispatch: second argument non-scalar / empty
c{end+1} = tc('obw_fs_vector',     @() obw(xr, [1e4 2e4]), 4);
c{end+1} = tc('powerbw_fs_char3',  @() powerbw(xr, 'abc'), 4);
c{end+1} = tc('obw_fs_cell2',      @() obw(xr, {1, [2]}), 4);
c{end+1} = tc('obw_pxx_F_empty',   @() obw(p5, []), 4);
c{end+1} = tc('obw_pxx_F_scalar',  @() obw(p5, 0), 4);
c{end+1} = tc('obw_rbw_vector',    @() obw(p5, f5, [20 30], 99), 4);
c{end+1} = tc('obw_rbw_empty',     @() obw(p5, f5, [], 99), 4);
c{end+1} = tc('obw_range_scalar_psd', @() obw(p5, f5, 1000, 99), 4);
% --- empty fs cast rules
c{end+1} = tc('obw_fs_double_empty',  @() obw(xr, []), 4);
c{end+1} = tc('obw_fs_logical_empty', @() obw(xr, logical([])), 4);
c{end+1} = tc('obw_fs_char_empty',    @() obw(xr, ''), 4);
c{end+1} = tc('obw_fs_single_empty',  @() obw(xr, single([])), 4);
c{end+1} = tc('obw_fs_int8_empty',    @() obw(xr, int8([])), 4);
c{end+1} = tc('obw_fs_uint16_empty',  @() obw(xr, uint16([])), 4);
c{end+1} = tc('obw_fs_complex_empty', @() obw(xr, complex([])), 4);
c{end+1} = tc('obw_fs_cell_empty',    @() obw(xr, {}), 4);
c{end+1} = tc('obw_fs_6',             @() obw(xr, 6), 4);
c{end+1} = tc('obw_fs_1',             @() obw(xr, 1), 4);
c{end+1} = tc('obw_fs_single2pi',     @() obw(xr, double(single(2*pi))), 4);
c{end+1} = tc('powerbw_fs_logical_empty', @() powerbw(xr, logical([])), 4);
c{end+1} = tc('powerbw_fs_char_empty',    @() powerbw(xr, ''), 4);
try
    h = obw(xr, half([]));  %#ok<NASGU>
    c{end+1} = tc('obw_fs_half_empty', @() obw(xr, half([])), 4);
catch e
    c{end+1} = struct('name', 'obw_fs_half_empty', 'ok', false, 'id', e.identifier, 'message', e.message);
end
% --- bandpower strings and empties
c{end+1} = tc('bandpower_char',      @() bandpower('abc'), 1);
c{end+1} = tc('bandpower_char_psd',  @() bandpower('psd'), 1);
c{end+1} = tc('bandpower_char_PSD',  @() bandpower('PSD'), 1);
c{end+1} = tc('bandpower_char_empty', @() bandpower(''), 1);
c{end+1} = tc('bandpower_pxx_char',  @() bandpower('abc', f5, 'psd'), 1);
c{end+1} = tc('bandpower_F_char',    @() bandpower(p5, 'abc', 'psd'), 1);
c{end+1} = tc('bandpower_range_char', @() bandpower(p5, f5, 'abc', 'psd'), 1);
c{end+1} = tc('bandpower_F_psd',     @() bandpower(p5, 'psd', 'psd'), 1);
c{end+1} = tc('bandpower_pxx_psd',   @() bandpower('psd', f5, 'psd'), 1);
c{end+1} = tc('bandpower_range_psd', @() bandpower(p5, f5, 'psd', 'psd'), 1);
c{end+1} = tc('bandpower_empty_00',  @() bandpower([]), 1);
c{end+1} = tc('bandpower_empty_10',  @() bandpower(zeros(1,0)), 1);
c{end+1} = tc('bandpower_empty_01',  @() bandpower(zeros(0,1)), 1);
c{end+1} = tc('bandpower_empty_02',  @() bandpower(zeros(0,2)), 1);
c{end+1} = tc('bandpower_empty_30',  @() bandpower(zeros(3,0)), 1);
c{end+1} = tc('bandpower_scalar',    @() bandpower(3), 1);
% --- class names printed by invalidType (char prints no 'Instead its type was' line)
c{end+1} = tc('obw_P_string',   @() obw(p5, f5, [], "99"), 4);
c{end+1} = tc('obw_P_logical',  @() obw(p5, f5, [], true), 4);
c{end+1} = tc('obw_P_datetime', @() obw(p5, f5, [], datetime(2026,1,1)), 4);
c{end+1} = tc('obw_P_duration', @() obw(p5, f5, [], seconds(1)), 4);
c{end+1} = tc('obw_P_struct',   @() obw(p5, f5, [], struct('a', 1)), 4);
c{end+1} = tc('obw_P_char1',    @() obw(p5, f5, [], 'a'), 4);
c{end+1} = tc('obw_P_char_empty', @() obw(p5, f5, [], ''), 4);
c{end+1} = tc('obw_power_F_char', @() obw(p5, 'abc', 10, [], 99), 4);
c{end+1} = tc('obw_pxx_F_char1',  @() obw(p5, 'a'), 4);
c{end+1} = tc('obw_pxx_char',     @() obw('1 2 3', [0; 10; 20]), 4);
c{end+1} = tc('obw_range_char_empty', @() obw(p5, f5, '', 99), 4);
% --- number format of the RBW '>=' message (%g) and a NaN comparison value
dfs = [1/3, 1e5/3, 1e-7/3, 1e20/3, 123456789.123, 0.1, 2/3*1e-3];
for k = 1:numel(dfs)
    d = dfs(k);
    c{end+1} = tc(sprintf('obw_rbw_fmt_%d', k), @() obw([1; 2; 1], (0:2).' * d, d/2, [], 99), 4); %#ok<AGROW>
end
c{end+1} = tc('obw_rbw_fmt_inf', @() obw([1; 2; 1], [-1e308; 0; 1e308], 1, [], 99), 4);
c{end+1} = tc('obw_rbw_nan_df',  @() obw([1; 2; 1], [1e308; -1e308; 1e308], 1, [], 99), 4);
% --- bandpower empty F / FREQRANGE
c{end+1} = tc('bandpower_F_empty',     @() bandpower(p5, [], 'psd'), 1);
c{end+1} = tc('bandpower_range_empty', @() bandpower(p5, f5, [], 'psd'), 1);
% --- empty fs of classes cast() cannot target, and single complex
c{end+1} = tc('obw_fs_datetime_empty', @() obw(xr, datetime.empty), 4);
c{end+1} = tc('obw_fs_duration_empty', @() obw(xr, duration.empty), 4);
c{end+1} = tc('obw_fs_string_empty',   @() obw(xr, strings(0)), 4);
c{end+1} = tc('obw_fs_struct_empty',   @() obw(xr, struct([])), 4);
c{end+1} = tc('obw_fs_csingle_empty',  @() obw(xr, complex(single([]))), 4);
c{end+1} = tc('obw_fs_uint8_empty',    @() obw(xr, uint8([])), 4);
% --- scalar RBW that fails finite / positive, single-bin bandpower, degenerate and 1e308-scale spectra
c{end+1} = tc('obw_rbw_inf',   @() obw(p5, f5, Inf, [], 99), 4);
c{end+1} = tc('obw_rbw_neg',   @() obw(p5, f5, -1, [], 99), 4);
c{end+1} = tc('obw_rbw_nan',   @() obw(p5, f5, NaN, [], 99), 4);
c{end+1} = tc('bandpower_one_bin', @() bandpower(1, 0, 'psd'), 1);
c{end+1} = tc('obw_zero_psd',      @() obw(zeros(5,1), f5), 4);
c{end+1} = tc('powerbw_zero_psd',  @() powerbw(zeros(5,1), f5), 4);
c{end+1} = tc('powerbw_zero_col',  @() powerbw([p5, zeros(5,1)], f5), 4);
c{end+1} = tc('powerbw_zero_in_range', @() powerbw([1; 0; 0; 0; 1], f5, [10 30]), 4);
c{end+1} = tc('obw_huge_psd',      @() obw(1e308*ones(5,1), f5), 4);
c{end+1} = tc('powerbw_huge_psd',  @() powerbw(1e308*ones(5,1), f5), 4);
c{end+1} = tc('bandpower_huge_psd', @() bandpower(1e308*ones(5,1), f5, 'psd'), 1);
c{end+1} = tc('bandpower_huge_time', @() bandpower([1e308 1e308]), 1);
fh = [-1e308; -5e307; 0; 5e307; 1e308];
c{end+1} = tc('obw_huge_grid',       @() obw(p5, fh), 4);
c{end+1} = tc('powerbw_huge_grid',   @() powerbw(p5, fh), 4);
c{end+1} = tc('bandpower_huge_grid', @() bandpower(p5, fh, 'psd'), 1);
c{end+1} = tc('obw_huge_grid_range', @() obw(p5, fh, [-5e307 5e307], 99), 4);
% --- the remaining validateattributes / error messages the module asserts
c{end+1} = tc('obw_P_vector',    @() obw(p5, f5, [], [90 99]), 4);
c{end+1} = tc('obw_P_empty',     @() obw(p5, f5, [], []), 4);
c{end+1} = tc('obw_range_3',     @() obw(p5, f5, [0 10 20], 99), 4);
c{end+1} = tc('obw_range_nan',   @() obw(p5, f5, [NaN 1], 99), 4);
c{end+1} = tc('obw_F_short',     @() obw(p5, f5(1:4)), 4);
c{end+1} = tc('obw_F_matrix',    @() obw(p5, zeros(5,2)), 4);
c{end+1} = tc('powerbw_F_char',  @() powerbw(p5, 'abc'), 4);
c{end+1} = tc('powerbw_X_char',  @() powerbw('abc', 1e4), 4);
c{end+1} = tc('powerbw_X_inf',   @() powerbw([1 Inf], 1e4), 4);
c{end+1} = tc('bandpower_X_inf', @() bandpower([1 Inf]), 1);
c{end+1} = tc('bandpower_X_3d',  @() bandpower(zeros(2,2,2)), 1);
c{end+1} = tc('obw_F_cell',      @() obw(p5, {0, [1 2]}), 4);
c{end+1} = tc('obw_pxx_cell',    @() obw({1, [2 3]}, f5), 4);
c{end+1} = tc('obw_X_cell',      @() obw({1, [2]}, 1e4), 4);
c{end+1} = tc('powerbw_range_cell', @() powerbw(p5, f5, {0, 1}, 3), 4);
c{end+1} = tc('bandpower_X_cell', @() bandpower({1, [2]}), 1);
c{end+1} = tc('obw_pxx_3d',      @() obw(zeros(4,2,2), f5(1:4)), 4);
c{end+1} = tc('obw_pxx_complex', @() obw(complex(p5), f5), 4);
c{end+1} = tc('powerbw_R_vector', @() powerbw(p5, f5, [], [3 6]), 4);
c{end+1} = tc('powerbw_extra',   @() powerbw(p5, f5, [], 3, 1), 4);
c{end+1} = tc('powerbw_time_extra', @() powerbw(xr, fs, [], 3, 1), 4);
c{end+1} = tc('bandpower_range_out', @() bandpower(p5, f5, [0 60], 'psd'), 1);
c{end+1} = tc('bandpower_pxx_inf', @() bandpower([1; 2; Inf; 2; 1], f5, 'psd'), 1);
c{end+1} = tc('bandpower_pxx_complex', @() bandpower(complex(p5), f5, 'psd'), 1);
c{end+1} = tc('bandpower_F_decreasing', @() bandpower(p5, flipud(f5), 'psd'), 1);
c{end+1} = tc('bandpower_F_short', @() bandpower(p5, f5(1:4), 'psd'), 1);
c{end+1} = tc('bandpower_range_3', @() bandpower(p5, f5, [0 10 20], 'psd'), 1);
c{end+1} = tc('bandpower_range_equal', @() bandpower(p5, f5, [10 10], 'psd'), 1);
c{end+1} = tc('obw_Fs_cell1',    @() obw(xr, {[]}), 4);
c{end+1} = tc('bandpower_neg_psd', @() bandpower(-p5, f5, 'psd'), 1);
c{end+1} = tc('bandpower_pos_psd', @() bandpower(p5, f5, 'psd'), 1);
R = struct('version', version, 'cases', {c});
fid = fopen('ref_obw_r3.json', 'w');
fprintf(fid, '%s', jsonencode(R, 'PrettyPrint', true));
fclose(fid);
end

function s = tc(name, fn, nout)
% Run fn; record outputs (%.17g strings keep NaN/Inf/sizes) or the error id/message.
s = struct('name', name, 'ok', true, 'id', '', 'message', '', 'vals', {{}}, 'sizes', {{}});
out = cell(1, nout);
try
    [out{:}] = fn();
catch e
    s.ok = false; s.id = e.identifier; s.message = e.message;
    return
end
for k = 1:nout
    v = double(out{k});
    s.sizes{k} = size(v);
    s.vals{k} = arrayfun(@(t) sprintf('%.17g', t), v(:).', 'UniformOutput', false);
end
end
