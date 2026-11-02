function hann_periodic_ref()
% Round 7 (spectral_mask review): MATLAB's own hann(L,'periodic') doubles for the two WindowLengths of the analyzer
% captures (1000, 4000), so the window DSV uses (dsv_spectrum.design_window('hann', L)) can be compared with MATLAB's
% at the ulp level and the window part of the scope-vs-model residual can be quantified (exact_periodogram.py).
% Function-level MATLAB only (no scope, no figure). Run from tests/matlab_ref/spectral_mask; writes
% hann_periodic_{1000,4000}.txt (%.17g, one value per line) and hann_periodic_ref.json (sums, first values, version).
out = struct('matlab_version', version, 'windows', []);
rows = struct('L', {}, 'file', {}, 'sum', {}, 'first_values', {}, 'symmetric_w2_to_end', {});
for L = [1000 4000]
    w = hann(L, 'periodic');
    fn = sprintf('hann_periodic_%d.txt', L);
    fid = fopen(fn, 'w'); fprintf(fid, '%.17g\n', w); fclose(fid);
    rows(end+1) = struct('L', L, 'file', fn, 'sum', sum(w), 'first_values', w(1:4)', ...
        'symmetric_w2_to_end', isequal(w(2:end), flipud(w(2:end))));
    fprintf('hann(%d,''periodic''): sum=%.17g first=%s symmetric(2:end)=%d\n', L, sum(w), mat2str(w(1:4)', 17), rows(end).symmetric_w2_to_end);
end
out.windows = rows;
fid = fopen('hann_periodic_ref.json', 'w'); fprintf(fid, '%s\n', jsonencode(out, 'PrettyPrint', true)); fclose(fid);
end
