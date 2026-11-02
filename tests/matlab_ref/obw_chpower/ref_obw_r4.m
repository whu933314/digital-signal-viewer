% Round-4 reference numbers for dsv_chmeas: single-precision inputs and integer-class inputs.
% Numeric functions only (obw, powerbw, bandpower); no figures, no scopes.
% Run from this folder: reads in_x_real.txt / in_x_cplx_re.txt / in_x_cplx_im.txt,
% writes ref_obw_r4.json (all relative paths).
function ref_obw_r4()
xr = load('in_x_real.txt');
xc = load('in_x_cplx_re.txt') + 1j * load('in_x_cplx_im.txt');
f5 = (0:4).' * 10;
p5 = [1; 2; 5; 2; 1];
xs = single(xr);            % the samples a float32 caller hands over
xcs = single(xc);
c = {};
% --- single precision: what MATLAB returns, and MATLAB on the same data widened to double
c{end+1} = tc('s_obw_psd',        @() obw(single(p5), single(f5)), 4);
c{end+1} = tc('s_obw_psd_pxxonly', @() obw(single(p5), f5), 4);
c{end+1} = tc('s_obw_psd_fonly',  @() obw(p5, single(f5)), 4);
c{end+1} = tc('d_obw_psd',        @() obw(p5, f5), 4);
c{end+1} = tc('s_obw_P',          @() obw(p5, f5, [], single(90)), 4);
c{end+1} = tc('d_obw_P',          @() obw(p5, f5, [], 90), 4);
c{end+1} = tc('s_obw_range',      @() obw(p5, f5, single([10 30]), 99), 4);
c{end+1} = tc('d_obw_range',      @() obw(p5, f5, [10 30], 99), 4);
c{end+1} = tc('s_obw_rbw',        @() obw(p5, f5, single(10), [], 99), 4);
c{end+1} = tc('d_obw_rbw',        @() obw(p5, f5, 10, [], 99), 4);
c{end+1} = tc('s_obw_mat',        @() obw(single([p5 2*p5+1]), single(f5)), 4);
c{end+1} = tc('d_obw_mat',        @() obw([p5 2*p5+1], f5), 4);
c{end+1} = tc('s_obw_time',       @() obw(xs, 1e4), 4);
c{end+1} = tc('d_obw_time',       @() obw(double(xs), 1e4), 4);
c{end+1} = tc('s_obw_time_fs',    @() obw(xr, single(1e4)), 4);
c{end+1} = tc('d_obw_time_fs',    @() obw(xr, 1e4), 4);
c{end+1} = tc('s_obw_time_cplx',  @() obw(xcs, 1e4), 4);
c{end+1} = tc('d_obw_time_cplx',  @() obw(double(xcs), 1e4), 4);
c{end+1} = tc('s_pbw_psd',        @() powerbw(single(p5), single(f5)), 4);
c{end+1} = tc('d_pbw_psd',        @() powerbw(p5, f5), 4);
c{end+1} = tc('s_pbw_time',       @() powerbw(xs, 1e4), 4);
c{end+1} = tc('d_pbw_time',       @() powerbw(double(xs), 1e4), 4);
c{end+1} = tc('s_pbw_R',          @() powerbw(p5, f5, [], single(3)), 4);
c{end+1} = tc('d_pbw_R',          @() powerbw(p5, f5, [], 3), 4);
% single scalar arguments whose value is not a double literal: MATLAB widens them (results are double)
c{end+1} = tc('s_obw_P_frac',     @() obw(p5, f5, [], single(99.9)), 4);
c{end+1} = tc('d_obw_P_frac',     @() obw(p5, f5, [], double(single(99.9))), 4);
c{end+1} = tc('s_obw_range_frac', @() obw(p5, f5, single([10.1 30.3]), 99), 4);
c{end+1} = tc('d_obw_range_frac', @() obw(p5, f5, double(single([10.1 30.3])), 99), 4);
c{end+1} = tc('s_obw_fs_frac',    @() obw(xr, single(1e4/3)), 4);
c{end+1} = tc('d_obw_fs_frac',    @() obw(xr, double(single(1e4/3))), 4);
c{end+1} = tc('s_pbw_R_frac',     @() powerbw(p5, f5, [], single(2.7)), 4);
c{end+1} = tc('d_pbw_R_frac',     @() powerbw(p5, f5, [], double(single(2.7))), 4);
c{end+1} = tc('s_obw_rbw_frac',   @() obw(p5, f5, single(10.3), [], 99), 4);
c{end+1} = tc('d_obw_rbw_frac',   @() obw(p5, f5, double(single(10.3)), [], 99), 4);
c{end+1} = tc('s_bp_psd',         @() bandpower(single(p5), single(f5), 'psd'), 1);
c{end+1} = tc('d_bp_psd',         @() bandpower(p5, f5, 'psd'), 1);
c{end+1} = tc('s_bp_psd_range',   @() bandpower(single(p5), single(f5), [5 35], 'psd'), 1);
c{end+1} = tc('d_bp_psd_range',   @() bandpower(p5, f5, [5 35], 'psd'), 1);
c{end+1} = tc('s_bp_time',        @() bandpower(xs), 1);
c{end+1} = tc('d_bp_time',        @() bandpower(double(xs)), 1);
c{end+1} = tc('s_bp_time_cplx',   @() bandpower(xcs), 1);
c{end+1} = tc('d_bp_time_cplx',   @() bandpower(double(xcs)), 1);
% --- integer classes and half where MATLAB only takes double/single (Pxx, F, X)
c{end+1} = tc('i_obw_pxx_int16',  @() obw(int16(p5), f5), 4);
c{end+1} = tc('i_obw_pxx_uint8',  @() obw(uint8(p5), f5), 4);
c{end+1} = tc('i_obw_f_int16',    @() obw(p5, int16(f5)), 4);
c{end+1} = tc('i_obw_x_int32',    @() obw(int32(round(1000 * xr)), 1e4), 4);
c{end+1} = tc('i_pbw_pxx_int8',   @() powerbw(int8(p5), f5), 4);
c{end+1} = tc('i_pbw_f_uint16',   @() powerbw(p5, uint16(f5)), 4);
c{end+1} = tc('i_pbw_x_int16',    @() powerbw(int16(round(1000 * xr)), 1e4), 4);
c{end+1} = tc('i_bp_pxx_int16',   @() bandpower(int16(p5), f5, 'psd'), 1);
c{end+1} = tc('i_bp_x_int16',     @() bandpower(int16(round(1000 * xr))), 1);
c{end+1} = tc('h_obw_pxx_half',   @() obw(half(p5), f5), 4);
% --- integer classes where MATLAB takes any numeric class
c{end+1} = tc('h_obw_P_half',     @() obw(p5, f5, [], half(90)), 4);
c{end+1} = tc('h_obw_fs_half',    @() obw(xr, half(1e4)), 4);
c{end+1} = tc('i_bp_f_int16',     @() bandpower(p5, int16(f5), 'psd'), 1);
c{end+1} = tc('i_bp_range_int16', @() bandpower(p5, f5, int16([5 35]), 'psd'), 1);
c{end+1} = tc('i_obw_P_int8',     @() obw(p5, f5, [], int8(90)), 4);
c{end+1} = tc('i_obw_range_int16', @() obw(p5, f5, int16([10 30]), 99), 4);
c{end+1} = tc('i_obw_rbw_int16',  @() obw(p5, f5, int16(10), [], 99), 4);
c{end+1} = tc('i_obw_fs_int16',   @() obw(xr, int16(10000)), 4);
c{end+1} = tc('i_pbw_fs_int32',   @() powerbw(xr, int32(10000)), 4);
c{end+1} = tc('i_pbw_R_int8',     @() powerbw(p5, f5, [], int8(3)), 4);
c{end+1} = tc('i_pbw_range_int16', @() powerbw(p5, f5, int16([10 30]), 3), 4);
R = struct('version', version, 'cases', {c});
fid = fopen('ref_obw_r4.json', 'w');
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
