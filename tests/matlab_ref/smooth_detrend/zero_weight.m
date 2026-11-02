% zero_weight.m -- MATLAB R2025a: what smoothdata's local regression returns in a window whose combined
% weights (tricube x robust x not-NaN) are all zero, and the error for an infinite robust window.
% Run from this folder: matlab -batch "zero_weight"  -> writes zero_weight.json here (relative path).
out = struct();
N = 200; n = (0:N-1)';
x = sin(n/7) + 0.1*cos(n/3) + 0.02*n;
x([37 120 171]) = x([37 120 171]) + [4; -5; 3.5];
out.x = x;
% (1) robust methods, outlier windows, three axes: samples (no SamplePoints), exactly uniform n/1024,
%     not exactly uniform 0.37+n/100 (sample-point path with the real time vector)
R = struct('method',{},'axis',{},'W',{},'y',{});
axs = {'none', []; 'fs1024', n/1024; 'fs100', 0.37 + n/100};
for a = 1:size(axs,1)
  for m = {'rlowess','rloess'}
    for ws = [4 4.5 5 7 8.5]
      t = axs{a,2};
      if isempty(t)
        if ws ~= fix(ws), continue; end
        y = smoothdata(x, m{1}, ws);
        W = ws;
      else
        W = ws*(t(2)-t(1));
        y = smoothdata(x, m{1}, W, 'SamplePoints', t);
      end
      R(end+1) = struct('method',m{1},'axis',axs{a,1},'W',W,'y',y'); %#ok<AGROW>
    end
  end
end
out.robust = R;
% (2) non-robust, NaN makes every nonzero tricube weight vanish (windows of 5 and 7 samples)
xr = cos(n(1:60)/7);
xr1 = xr; xr1(21:23) = NaN;         % window 5 around 1-based 22: only the two tricube-zero ends are not NaN
xr2 = xr; xr2(19:25) = NaN; xr2(18) = 2; xr2(26) = -1;   % window 9 around 22: ends 18/26 (tricube 0) not NaN
out.xr1 = xr1; out.xr2 = xr2;
NR = struct('method',{},'sig',{},'W',{},'sp',{},'y',{});
for m = {'lowess','loess','rlowess','rloess','sgolay'}
  for s = {'xr1', 5; 'xr1', 6; 'xr2', 9; 'xr2', 10}'
    xs = out.(s{1});
    y = smoothdata(xs, m{1}, s{2});
    NR(end+1) = struct('method',m{1},'sig',s{1},'W',s{2},'sp',0,'y',y'); %#ok<AGROW>
    y = smoothdata(xs, m{1}, s{2}/100, 'SamplePoints', 0.37 + (0:59)'/100);
    NR(end+1) = struct('method',m{1},'sig',s{1},'W',s{2}/100,'sp',1,'y',y'); %#ok<AGROW>
  end
end
out.nanwin = NR;
% (3) robust with a NaN next to the outlier
xq = x; xq(170) = NaN;   % 1-based 170 = 0-based 169, left neighbour of the outlier at 0-based 170
out.xq = xq;
Q = struct('method',{},'W',{},'y',{});
for m = {'rlowess','rloess'}
  for ws = [4 5 7 9]
    y = smoothdata(xq, m{1}, ws);
    Q(end+1) = struct('method',m{1},'W',ws,'y',y'); %#ok<AGROW>
  end
end
out.robust_nan = Q;
% (4) infinite robust window on an exactly-uniform axis (ws = 1e308/2^-10 overflows to Inf)
E = struct('method',{},'W',{},'id',{},'msg',{});
for m = {'rlowess','rloess','lowess','loess','sgolay','gaussian','movmean','movmedian'}
  for W = [1e308 realmax]
    id = ''; msg = '';
    try
      smoothdata(x, m{1}, W, 'SamplePoints', n/1024);
    catch ME
      id = ME.identifier; msg = ME.message;
    end
    E(end+1) = struct('method',m{1},'W',W,'id',id,'msg',msg); %#ok<AGROW>
  end
end
try, smoothdata(x, 'rlowess', Inf); catch ME, E(end+1) = struct('method','rlowess','W',Inf,'id',ME.identifier,'msg',ME.message); end
out.inf_window = E;
fid = fopen('zero_weight.json', 'w');
fprintf(fid, '%s', jsonencode(out));
fclose(fid);
for k = 1:numel(E), fprintf('%-9s W=%g id=%s msg=%s\n', E(k).method, E(k).W, E(k).id, E(k).msg); end
