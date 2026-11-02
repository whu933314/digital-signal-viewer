% zero_weight2.m -- MATLAB R2025a follow-up: (a) is the tricube distance scale dmax taken over the whole window or
% only over the non-NaN points; (b) do the time-axis mismatches move when the time vector changes by rounding only.
% Run from this folder: matlab -batch "zero_weight2"  -> writes zero_weight2.json here (relative path).
out = struct();
N = 60; n = (0:N-1)';
xa = cos(n/7) + 0.05*n;
A = struct('case',{},'method',{},'W',{},'x',{},'y',{});
nanSets = {'end4', 5; 'endN5', N-4; 'int_m3', [27 31]};     % 1-based NaN positions
for s = 1:size(nanSets,1)
  xs = xa; xs(nanSets{s,2}) = NaN;
  for m = {'lowess','loess','rlowess','rloess','sgolay'}
    for W = [5 6 7]
      y = smoothdata(xs, m{1}, W);
      A(end+1) = struct('case',nanSets{s,1},'method',m{1},'W',W,'x',xs','y',y'); %#ok<AGROW>
    end
  end
end
out.dmax = A;
% (b) same data on two roundings of "0.37 s + n/100"
N = 200; n = (0:N-1)';
x = sin(n/7) + 0.1*cos(n/3) + 0.02*n;
x([37 120 171]) = x([37 120 171]) + [4; -5; 3.5];
out.x = x;
t1 = 0.37 + n/100;
t2 = (37 + n)/100;
out.t2 = t2;
B = struct('axis',{},'method',{},'W',{},'y',{});
for ax = {'t1','t2'}
  if strcmp(ax{1}, 't1'), t = t1; else, t = t2; end
  for m = {'rloess','rlowess','loess','lowess'}
    for W = [0.045 0.07 0.075]
      y = smoothdata(x, m{1}, W, 'SamplePoints', t);
      B(end+1) = struct('axis',ax{1},'method',m{1},'W',W,'y',y'); %#ok<AGROW>
    end
  end
end
out.rounding = B;
fid = fopen('zero_weight2.json', 'w');
fprintf(fid, '%s', jsonencode(out));
fclose(fid);
fprintf('t1==t2 everywhere: %d, max|t1-t2| = %g, uniform t1/t2: %d/%d\n', isequal(t1,t2), max(abs(t1-t2)), ...
        max(diff(t1))==min(diff(t1)), max(diff(t2))==min(diff(t2)));
