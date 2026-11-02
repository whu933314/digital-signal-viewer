% Reviewer probe: exactly-uniform SamplePoints (dyadic fs) with a window whose sample-equivalent is non-integer.
n = (0:199)';
x = sin(n/7) + 0.1*cos(n/3) + 0.02*n;
out = struct();
cases = {
  't_fs2',  n/2,     4.25;   % dt=0.5 exactly -> 8.5 samples
  't_fs2b', n/2,     3.75;   % 7.5 samples
  't_fs1',  n,       8.5;    % dt=1 -> 8.5 samples
  't_fs1b', n,       7.5;
  't_fs4',  n/4,     2.125;  % dt=0.25 -> 8.5 samples
  't_fs100',0.37+n/100, 0.085; % NOT exactly uniform (reference-style) -> 8.5 samples by sample-point rule
};
methods = {'movmean','movmedian','gaussian','lowess','loess','rlowess','rloess','sgolay'};
for c = 1:size(cases,1)
  t = cases{c,2}; W = cases{c,3};
  fprintf('CASE %s W=%.17g uniform(max==min diff)=%d\n', cases{c,1}, W, max(diff(t))==min(diff(t)));
  for m = 1:numel(methods)
    [y, w] = smoothdata(x, methods{m}, W, 'SamplePoints', t);
    out.(cases{c,1}).(methods{m}) = y;
  end
  out.(cases{c,1}).t = t; out.(cases{c,1}).W = W;
end
out.x = x;
fid = fopen('uniform_axis.json','w');   % 在這個資料夾執行：輸出到同資料夾
fprintf(fid, '%s', jsonencode(out)); fclose(fid);
% Also: window size in samples that MATLAB's uniform path effectively uses -- count the nonzero taps via an impulse
imp = zeros(200,1); imp(100) = 1;
for c = 1:size(cases,1)
  t = cases{c,2}; W = cases{c,3};
  y = smoothdata(imp, 'movmean', W, 'SamplePoints', t);
  k = find(y ~= 0) - 100;
  fprintf('IMPULSE %s movmean taps offsets: %s\n', cases{c,1}, mat2str(k'));
  y = smoothdata(imp, 'sgolay', W, 'SamplePoints', t);
  k = find(abs(y) > 1e-14) - 100;
  fprintf('IMPULSE %s sgolay taps offsets: %s\n', cases{c,1}, mat2str(k'));
  y = smoothdata(imp, 'gaussian', W, 'SamplePoints', t);
  k = find(abs(y) > 1e-14) - 100;
  fprintf('IMPULSE %s gaussian taps offsets: %s\n', cases{c,1}, mat2str(k'));
  y = smoothdata(imp, 'lowess', W, 'SamplePoints', t);
  k = find(abs(y) > 1e-14) - 100;
  fprintf('IMPULSE %s lowess taps offsets: %s\n', cases{c,1}, mat2str(k'));
end
