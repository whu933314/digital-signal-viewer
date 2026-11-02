% Round-5 reference numbers for dsv_chmeas: the class check of Pxx / Sxx / F / X (double or single only).
% Which class names validateattributes prints, and that the class check comes before every other check.
% Numeric functions only (obw, powerbw, bandpower); no figures, no scopes.
% Run from this folder: reads in_x_real.txt, writes ref_obw_r5.json (relative paths only).
function ref_obw_r5()
xr = load('in_x_real.txt');
f5 = (0:4).' * 10;
p5 = [1; 2; 5; 2; 1];
xi = round(1000 * xr);
c = {};
% --- the remaining integer classes and half, on Pxx / Sxx / F / X
c{end+1} = tc('i_obw_pxx_int32',  @() obw(int32(p5), f5), 4);
c{end+1} = tc('i_obw_pxx_int64',  @() obw(int64(p5), f5), 4);
c{end+1} = tc('i_obw_pxx_uint16', @() obw(uint16(p5), f5), 4);
c{end+1} = tc('i_obw_pxx_uint32', @() obw(uint32(p5), f5), 4);
c{end+1} = tc('i_obw_pxx_uint64', @() obw(uint64(p5), f5), 4);
c{end+1} = tc('i_obw_sxx_int16',  @() obw(int16(p5), f5, 10, [], 99), 4);
c{end+1} = tc('i_obw_f_int64',    @() obw(p5, int64(f5)), 4);
c{end+1} = tc('i_obw_f_uint8',    @() obw(p5, uint8(f5)), 4);
c{end+1} = tc('i_obw_sxx_f_int32', @() obw(p5, int32(f5), 10, [], 99), 4);
c{end+1} = tc('h_obw_f_half',     @() obw(p5, half(f5)), 4);
c{end+1} = tc('h_obw_x_half',     @() obw(half(xr), 1e4), 4);
c{end+1} = tc('h_pbw_pxx_half',   @() powerbw(half(p5), f5), 4);
c{end+1} = tc('h_pbw_x_half',     @() powerbw(half(xr), 1e4), 4);
c{end+1} = tc('h_bp_pxx_half',    @() bandpower(half(p5), f5, 'psd'), 1);
c{end+1} = tc('h_bp_x_half',      @() bandpower(half(xr)), 1);
c{end+1} = tc('i_bp_x_uint8',     @() bandpower(uint8(p5)), 1);
c{end+1} = tc('i_bp_pxx_int64_range', @() bandpower(int64(p5), f5, [5 35], 'psd'), 1);
c{end+1} = tc('i_obw_x_int64_nofs', @() obw(int64(xi)), 4);
c{end+1} = tc('i_pbw_x_uint16_fs_int16', @() powerbw(uint16(xi + 5000), int16(10000)), 4);
c{end+1} = tc('l_obw_pxx_logical', @() obw(p5 > 0, f5), 4);
c{end+1} = tc('l_obw_x_logical',   @() obw(xr > 0, 1e4), 4);
c{end+1} = tc('l_pbw_x_logical',   @() powerbw(xr > 0, 1e4), 4);
c{end+1} = tc('l_bp_x_logical',    @() bandpower(xr > 0), 1);
c{end+1} = tc('l_bp_pxx_logical',  @() bandpower(p5 > 0, f5, 'psd'), 1);
% --- order: the class check of Pxx comes before F, before the attribute checks, before the other arguments
c{end+1} = tc('o_obw_both_int16',       @() obw(int16(p5), int16(f5)), 4);
c{end+1} = tc('o_obw_single_pxx_int16_f', @() obw(single(p5), int16(f5)), 4);
c{end+1} = tc('o_obw_int16_pxx_short_f', @() obw(int16(p5), f5(1:4)), 4);
c{end+1} = tc('o_obw_int16_pxx_neg',    @() obw(int16(-p5), f5), 4);
c{end+1} = tc('o_obw_int16_pxx_3d',     @() obw(int16(zeros(4, 2, 2)), f5(1:4)), 4);
c{end+1} = tc('o_obw_int16_pxx_bad_P',  @() obw(int16(p5), f5, [], 100), 4);
c{end+1} = tc('o_obw_int16_pxx_P_int16', @() obw(int16(p5), f5, [], int16(90)), 4);
c{end+1} = tc('o_obw_int16_f_nan_pxx',  @() obw([1; NaN; 5; 2; 1], int16(f5)), 4);
c{end+1} = tc('o_pbw_int16_f_bad_R',    @() powerbw(p5, int16(f5), [], 0), 4);
c{end+1} = tc('o_obw_x_int32_bad_fs',   @() obw(int32(xi), -1), 4);
c{end+1} = tc('o_obw_x_int32_1sample',  @() obw(int32(3), 1e4), 4);
c{end+1} = tc('o_obw_x_int32_empty',    @() obw(int32([]), 1e4), 4);
c{end+1} = tc('o_bp_int16_pxx_bad_f',   @() bandpower(int16(p5), flipud(f5), 'psd'), 1);
c{end+1} = tc('o_bp_x_int16_inf_shape', @() bandpower(int16(zeros(2, 2, 2))), 1);
% --- mixed concatenation (MATLAB: double with int16 gives int16) and integer-valued doubles
c{end+1} = tc('m_obw_mat_double_int16', @() obw([p5 int16(p5)], f5), 4);
c{end+1} = tc('m_obw_pxx_double_of_int16', @() obw(double(int16(p5)), f5), 4);
c{end+1} = tc('m_obw_literal',          @() obw([1; 2; 5; 2; 1], [0; 10; 20; 30; 40]), 4);
c{end+1} = tc('m_obw_x_int32_as_double', @() obw(double(int32(xi)), 1e4), 4);
R = struct('version', version, 'class_of_literal', class([1; 2; 5; 2; 1]), 'class_of_mixed_concat', class([p5 int16(p5)]), ...
           'class_of_logical_literal', class(p5 > 0), 'cases', {c});
fid = fopen('ref_obw_r5.json', 'w');
fprintf(fid, '%s', jsonencode(R));
fclose(fid);
end

function s = tc(name, fn, nout)
% Call fn and keep either its outputs (class, size, %.17g text of the value widened to double) or the error.
s = struct('name', name, 'ok', true, 'id', '', 'message', '', 'vals', {{}}, 'sizes', {{}}, 'classes', {{}});
out = cell(1, nout);
try
    [out{:}] = fn();
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
