% error_ids.m -- MATLAB R2025a: the error identifiers smoothdata raises for invalid window / factor / degree /
% sample-point inputs (DSV's CleanError identifiers are checked against these).
% Run from this folder: matlab -batch "error_ids"  -> writes error_ids.json here (relative path).
x = sin((0:19)'/3);
t = (0:19)'/10;
C = {
 'window 0',            @() smoothdata(x, 'movmean', 0)
 'window -1',           @() smoothdata(x, 'movmean', -1)
 'window NaN',          @() smoothdata(x, 'movmean', NaN)
 'window Inf',          @() smoothdata(x, 'movmean', Inf)
 'window Inf rlowess',  @() smoothdata(x, 'rlowess', Inf)
 'window 1e30',         @() smoothdata(x, 'movmean', 1e30)
 'window complex',      @() smoothdata(x, 'movmean', 3+1i)
 'window [3 4 5]',      @() smoothdata(x, 'movmean', [3 4 5])
 'window true',         @() smoothdata(x, 'movmean', true)
 'window 2.5 samples',  @() smoothdata(x, 'movmean', 2.5)
 'factor 1.5',          @() smoothdata(x, 'movmean', 'SmoothingFactor', 1.5)
 'factor -0.1',         @() smoothdata(x, 'movmean', 'SmoothingFactor', -0.1)
 'factor NaN',          @() smoothdata(x, 'movmean', 'SmoothingFactor', NaN)
 'factor complex',      @() smoothdata(x, 'movmean', 'SmoothingFactor', 0.5i)
 'degree -1',           @() smoothdata(x, 'sgolay', 5, 'Degree', -1)
 'degree 2.5',          @() smoothdata(x, 'sgolay', 5, 'Degree', 2.5)
 'degree NaN',          @() smoothdata(x, 'sgolay', 5, 'Degree', NaN)
 'degree Inf',          @() smoothdata(x, 'sgolay', 5, 'Degree', Inf)
 'degree complex',      @() smoothdata(x, 'sgolay', 5, 'Degree', 2i)
 'degree with movmean', @() smoothdata(x, 'movmean', 5, 'Degree', 2)
 'degree with loess',   @() smoothdata(x, 'loess', 5, 'Degree', 2)
 'degree 6 window 5',   @() smoothdata(x, 'sgolay', 5, 'Degree', 6)
 'method foo',          @() smoothdata(x, 'foo')
 'sp length',           @() smoothdata(x, 'movmean', 0.3, 'SamplePoints', t(1:5))
 'sp NaN',              @() smoothdata(x, 'movmean', 0.3, 'SamplePoints', [t(1:19); NaN])
 'sp Inf',              @() smoothdata(x, 'movmean', 0.3, 'SamplePoints', [t(1:19); Inf])
 'sp decreasing',       @() smoothdata(x, 'movmean', 0.3, 'SamplePoints', flipud(t))
 'sp duplicate',        @() smoothdata(x, 'movmean', 0.3, 'SamplePoints', [t(1:19); t(19)])
 'sp complex',          @() smoothdata(x, 'movmean', 0.3, 'SamplePoints', t + 1i)
 'x string',            @() smoothdata(["a";"b";"c"], 'movmean', 3)
 'x Inf movmean',       @() smoothdata([1; Inf; 3], 'movmean', 3)
 'window false',        @() smoothdata(x, 'movmean', false)
 'factor true',         @() smoothdata(x, 'movmean', 'SmoothingFactor', true)
 'factor [0.1 0.2]',    @() smoothdata(x, 'movmean', 'SmoothingFactor', [0.1 0.2])
 'factor string',       @() smoothdata(x, 'movmean', 'SmoothingFactor', "a")
 'degree true',         @() smoothdata(x, 'sgolay', 5, 'Degree', true)
 'degree [1 2]',        @() smoothdata(x, 'sgolay', 5, 'Degree', [1 2])
 'window string',       @() smoothdata(x, 'movmean', "abc")
 'sp string',           @() smoothdata(x, 'movmean', 0.3, 'SamplePoints', string(t))
 'sp matrix',           @() smoothdata(x, 'movmean', 0.3, 'SamplePoints', [t t])
 'x matrix',            @() smoothdata([x x], 'movmean', 3)
 'detrend x string',    @() detrend(["a";"b";"c"])
 'detrend x cell',      @() detrend({1,2,3})
};
E = struct('case',{},'id',{},'msg',{});
for k = 1:size(C,1)
  id = ''; msg = '';
  try
    C{k,2}();
  catch ME
    id = ME.identifier; msg = ME.message;
  end
  E(end+1) = struct('case',C{k,1},'id',id,'msg',msg); %#ok<AGROW>
  fprintf('%-20s %-45s %s\n', C{k,1}, id, msg);
end
fid = fopen('error_ids.json', 'w');
fprintf(fid, '%s', jsonencode(E));
fclose(fid);
