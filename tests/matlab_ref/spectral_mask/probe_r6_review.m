function probe_r6_review()
% Round-6 adversarial review: extra FrequencyOffset shapes/types on a spectrumAnalyzer object (never shown or stepped),
% plus MATLAB's own hann(L,'periodic') doubles so the window used by exact_periodogram.py can be compared bit-for-bit.
sa = spectrumAnalyzer('SampleRate', 1000);
vals = {[1 2; 3 4], [true false], zeros(1,0), zeros(0,1), "abc", {5}, uint8(3), single([1 2]), [1 2]', 1, -0, 0.5, [NaN NaN]};
names = {'[1 2;3 4]', '[true false]', 'zeros(1,0)', 'zeros(0,1)', '"abc"', '{5}', 'uint8(3)', 'single([1 2])', '[1 2]''', '1', '-0', '0.5', '[NaN NaN]'};
rows = struct('value', {}, 'ok', {}, 'id', {}, 'msg', {});
for k = 1:numel(vals)
    v = vals{k};
    try
        sa.FrequencyOffset = v;
        rows(k) = struct('value', names{k}, 'ok', true, 'id', '', 'msg', mat2str(sa.FrequencyOffset));
        sa.FrequencyOffset = 0;
    catch ME
        rows(k) = struct('value', names{k}, 'ok', false, 'id', ME.identifier, 'msg', ME.message);
    end
    fprintf('FrequencyOffset %s -> ok=%d %s | %s\n', rows(k).value, rows(k).ok, rows(k).id, strrep(rows(k).msg, newline, '\n'));
end
delete(sa);
out = struct('matlab_version', version, 'cases', rows);
fid = fopen('probe_r6_review.json', 'w'); fprintf(fid, '%s\n', jsonencode(out, 'PrettyPrint', true)); fclose(fid);
for L = [1000 4000]
    w = hann(L, 'periodic');
    fid = fopen(sprintf('hann_periodic_%d.txt', L), 'w'); fprintf(fid, '%.17g\n', w); fclose(fid);
    fprintf('hann(%d,periodic): sum=%.17g\n', L, sum(w));
end
end
