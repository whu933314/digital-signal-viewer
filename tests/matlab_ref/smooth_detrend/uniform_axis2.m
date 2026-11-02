% uniform_axis2.m -- MATLAB R2025a reference numbers for DSV dsv_clean (smoothdata on exactly-uniform SamplePoints).
% Run from this folder:  matlab -batch "uniform_axis2"   -> writes uniform_axis2.json next to this file (relative path).
% Only plain functions are called (smoothdata, diff, num2hex, jsonencode); no app, figure or scope.
%
% Part 1 (axes): which time vectors DSV can build are "exactly uniform" (max(diff(t)) == min(diff(t)));
%   the results below show how smoothdata's output differs on such axes.
%   Forms:  t0 + (0:N-1)'/fs                    (dsv_clean.time_vector)
%           (offset/sps + (0:N-1)'/sps) / sr     (DSV symbol axis x0 + n/sps converted to seconds afterwards)
%   For each vector: the flag, hex of t(1), t(end), max(dt), min(dt), and two sums over the bit patterns
%   (low / high 32 bits) so a port can check it builds the identical vector.
% Part 2 (smooth): smoothdata(x, method, W, 'SamplePoints', t [, 'Degree', d]) on exactly-uniform axes, many
%   windows whose sample equivalent ws = W/(t(2)-t(1)) is fractional with an even floor, plus NaN, complex,
%   automatic windows, Savitzky-Golay degree limits, huge windows (1e30, 1e308) and N = 2 / 3 axes.

out = struct();

%% ---------------- Part 1: axis table ----------------
ax = {};
plain = { % N, fs, t0
  200, 100, 0.37;  200, 1, 0;  200, 2, 0;  200, 4, 0;  200, 4, 0.25;  200, 1024, 0;  200, 8, 0.375;
  1000, 1024, 0;  1000, 1000, 0;  1000, 1000, 0.37;  1000, 4, 0.25;  1000, 3, 0;
  65536, 8192, 0;  65536, 8e6, 0;  65536, 8e6, 2;  65536, 1e6, 0;  4096, 1e6, 0;  4096, 2^20, 0;
  2, 100, 0.37;  3, 100, 0.37;  3, 1e6, 0;  10, 10, 0;  10, 3, 0;  100, 0.5, -1;  200, 1/3, 100 };
for k = 1:size(plain,1)
  [N, fs, t0] = plain{k,:};
  ax(end+1,:) = {sprintf('plain N=%d fs=%.17g t0=%.17g', N, fs, t0), 'plain', N, fs, t0, NaN, NaN, NaN, t0 + (0:N-1)'/fs}; %#ok<AGROW>
end
for N = [1000 65536]
  for sps = [1 2 4 8 16 64 3 10]
    for offset = [0 3 0.5]
      for sr = [1e6 2e6 1]
        x0 = offset/sps;
        ta = x0/sr + (0:N-1)'/(sps*sr);           % time_vector(N, sps*sr, x0/sr)
        tb = (x0 + (0:N-1)'/sps)/sr;              % symbol axis divided by the symbol rate
        ax(end+1,:) = {sprintf('dsv_a N=%d sps=%g offset=%g sr=%g', N, sps, offset, sr), 'dsv_a', N, sps*sr, x0/sr, sps, offset, sr, ta}; %#ok<AGROW>
        ax(end+1,:) = {sprintf('dsv_b N=%d sps=%g offset=%g sr=%g', N, sps, offset, sr), 'dsv_b', N, sps*sr, x0/sr, sps, offset, sr, tb}; %#ok<AGROW>
      end
    end
  end
end
axes_ = struct('label',{},'form',{},'N',{},'fs',{},'t0',{},'sps',{},'offset',{},'sr',{},'uniform',{}, ...
               't1_hex',{},'tend_hex',{},'dtmax_hex',{},'dtmin_hex',{},'lo32_sum',{},'hi32_sum',{});
for k = 1:size(ax,1)
  t = ax{k,9};
  dt = diff(t);
  u = typecast(t, 'uint64');
  lo = sum(double(bitand(u, uint64(4294967295))));
  hi = sum(double(bitshift(u, -32)));
  axes_(end+1) = struct('label',ax{k,1},'form',ax{k,2},'N',ax{k,3},'fs',ax{k,4},'t0',ax{k,5},'sps',ax{k,6}, ...
      'offset',ax{k,7},'sr',ax{k,8},'uniform',double(max(dt)==min(dt)),'t1_hex',num2hex(t(1)),'tend_hex',num2hex(t(end)), ...
      'dtmax_hex',num2hex(max(dt)),'dtmin_hex',num2hex(min(dt)),'lo32_sum',lo,'hi32_sum',hi); %#ok<AGROW>
end
out.axes = axes_;
fprintf('axes: %d vectors, %d exactly uniform\n', numel(axes_), sum([axes_.uniform]));

%% ---------------- Part 2: smoothdata on exactly-uniform axes ----------------
N = 200; n = (0:N-1)';
x = sin(n/7) + 0.1*cos(n/3) + 0.02*n;
x([37 120 171]) = x([37 120 171]) + [4; -5; 3.5];      % outliers so the robust methods do something
xn = x; xn([11 101 151]) = NaN;                         % NaN (smoothdata default 'omitnan')
xc = x + 1i*cos(n/5);
out.x = x; out.xn = xn; out.xc_re = real(xc); out.xc_im = imag(xc);
T = struct();
T.fs1024 = n/1024;            % dt = 2^-10   (dsv_clean.time_vector(200, 1024, 0))
T.fs4_t025 = 0.25 + n/4;      % time_vector(200, 4, 0.25)
T.sym8_off3 = 0.375 + n/8;    % DSV symbol axis, sps 8, offset 3 samples
T.int3 = 100 + 3*n;           % exactly uniform with a non-dyadic step
T.fs100_t037 = 0.37 + n/100;  % NOT exactly uniform (reference A_time axis) -- sample-point path
T.samples = n;                % samples mode axis 0..N-1
out.axes_smooth = T;
methods_ = {'movmean','movmedian','gaussian','lowess','loess','rlowess','rloess','sgolay'};
SIG = struct('x', x, 'xn', xn, 'xc', xc);
cases = struct('group',{},'axis',{},'signal',{},'method',{},'W',{},'ws',{},'sf',{},'degree',{},'sp',{}, ...
               'y_re',{},'y_im',{},'winsz',{},'warn',{},'err',{},'uniform',{});
% 2a. many fractional windows on the dyadic axis (dt = 2^-10, so W = ws*dt is exact)
wsMain = [1.5 2.5 3.5 4.2 4.5 4.8 5.5 6.3 7 8 8.5 9.5 10.3 11.7 20.5 150.5 250.5 450.5];
for ws = wsMain
  for mi = 1:numel(methods_)
    cases(end+1) = run1(T, SIG, 'fraction', 'fs1024', 'x', methods_{mi}, ws/1024, [], [], true); %#ok<AGROW>
  end
end
% 2b. other exactly-uniform axes (W given in the axis' own units)
for an = {'fs4_t025','sym8_off3','int3'}
  t = T.(an{1}); dt = t(2) - t(1);
  for ws = [2.5 4.5 8 8.5 10.3 11.7]
    for mi = 1:numel(methods_)
      cases(end+1) = run1(T, SIG, 'other_axis', an{1}, 'x', methods_{mi}, ws*dt, [], [], true); %#ok<AGROW>
    end
  end
end
% 2c. NaN and complex on the dyadic axis
for ws = [4.5 8 8.5]
  for mi = 1:numel(methods_)
    cases(end+1) = run1(T, SIG, 'nan', 'fs1024', 'xn', methods_{mi}, ws/1024, [], [], true); %#ok<AGROW>
  end
end
for ws = [4.5 8.5]
  for mi = 1:numel(methods_)
    cases(end+1) = run1(T, SIG, 'complex', 'fs1024', 'xc', methods_{mi}, ws/1024, [], [], true); %#ok<AGROW>
  end
end
% 2d. automatic windows (default factor 0.25, and 0.1 / 0.6) on exactly-uniform time axes
for an = {'fs1024','int3'}
  for sf = {[], 0.1, 0.6}
    for mi = 1:numel(methods_)
      cases(end+1) = run1(T, SIG, 'auto', an{1}, 'x', methods_{mi}, [], sf{1}, [], true); %#ok<AGROW>
    end
  end
end
% 2e. Savitzky-Golay degree limits on the dyadic axis (the degree check counts the sample-point window wl,
%     the uniform fast path then fits fix(ws) points)
sg = {8.5, 8; 8.5, 9; 4.5, 3; 4.5, 4; 4.5, 5; 2.5, 1; 2.5, 2; 2.5, 3; 10.3, 6};
for k = 1:size(sg,1)
  cases(end+1) = run1(T, SIG, 'sgolay_degree', 'fs1024', 'x', 'sgolay', sg{k,1}/1024, [], sg{k,2}, true); %#ok<AGROW>
end
cases(end+1) = run1(T, SIG, 'sgolay_degree', 'fs1024', 'x', 'sgolay', [], [], 60, true);
cases(end+1) = run1(T, SIG, 'sgolay_degree', 'fs1024', 'x', 'sgolay', [], 0.05, 9, true);
% 2f. huge windows: 1e30 (samples without / with SamplePoints, dyadic axis, non-uniform axis) and 1e308
for mi = 1:numel(methods_)
  cases(end+1) = run1(T, SIG, 'huge', 'samples', 'x', methods_{mi}, 1e30, [], [], false); %#ok<AGROW>
  cases(end+1) = run1(T, SIG, 'huge', 'samples', 'x', methods_{mi}, 1e30, [], [], true); %#ok<AGROW>
  cases(end+1) = run1(T, SIG, 'huge', 'fs1024', 'x', methods_{mi}, 1e30, [], [], true); %#ok<AGROW>
  cases(end+1) = run1(T, SIG, 'huge', 'fs100_t037', 'x', methods_{mi}, 1e30, [], [], true); %#ok<AGROW>
  cases(end+1) = run1(T, SIG, 'huge', 'fs1024', 'x', methods_{mi}, 1e308, [], [], true); %#ok<AGROW>
end
out.cases = cases;

% 2g. N = 2 and N = 3 axes (N = 2 has a single difference, so it is always "exactly uniform")
small = struct('t',{},'x',{},'method',{},'W',{},'y',{},'winsz',{},'err',{},'uniform',{});
smallAxes = {[0.37; 0.38], [1; 3]; [0.37; 0.38; 0.39], [1; 3; 2]; [0; 0.25; 0.5], [1; 3; 2]};
for k = 1:size(smallAxes,1)
  t = smallAxes{k,1}; xx = smallAxes{k,2}; dt = t(2) - t(1);
  for ws = [1.5 2.5 3 4.5]
    for mi = 1:numel(methods_)
      y = []; w = []; e = '';
      try
        [y, w] = smoothdata(xx, methods_{mi}, ws*dt, 'SamplePoints', t);
      catch ME
        e = ME.identifier;
      end
      small(end+1) = struct('t',t','x',xx','method',methods_{mi},'W',ws*dt,'y',y(:)','winsz',w,'err',e, ...
                            'uniform',double(max(diff(t))==min(diff(t)))); %#ok<AGROW>
    end
  end
end
out.small = small;

fid = fopen('uniform_axis2.json', 'w');     % relative path: written next to this script
fprintf(fid, '%s', jsonencode(out));
fclose(fid);
fprintf('cases: %d, small: %d\n', numel(cases), numel(small));
fprintf('errors: %s\n', strjoin(unique({cases(~cellfun(@isempty,{cases.err})).err}), ', '));
fprintf('warnings: %s\n', strjoin(unique({cases(~cellfun(@isempty,{cases.warn})).warn}), ', '));

%% ---------------- local function ----------------
function c = run1(T, SIG, group, axname, signame, m, W, sf, deg, usesp)
    t = T.(axname);
    xx = SIG.(signame);
    args = {m};
    if ~isempty(W), args{end+1} = W; end
    if ~isempty(sf), args = [args {'SmoothingFactor', sf}]; end
    if usesp, args = [args {'SamplePoints', t}]; end
    if ~isempty(deg), args = [args {'Degree', deg}]; end
    lastwarn('', '');
    y = []; w = []; e = '';
    try
        [y, w] = smoothdata(xx, args{:});
    catch ME
        e = ME.identifier;
    end
    [~, wid] = lastwarn;
    dt = t(2) - t(1);
    ws = NaN; if ~isempty(W), ws = W/dt; end
    c = struct('group',group,'axis',axname,'signal',signame,'method',m,'W',W,'ws',ws,'sf',sf,'degree',deg,'sp',double(usesp), ...
               'y_re',real(y(:))','y_im',imag(y(:))','winsz',w,'warn',wid,'err',e,'uniform',double(max(diff(t))==min(diff(t))));
end
