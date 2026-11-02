function probe_r5_offset()
% Round-5 review: real spectrumAnalyzer FrequencyOffset validation messages (object only, never shown/stepped).
sa = spectrumAnalyzer('SampleRate', 1000);
vals = {NaN, Inf, -Inf, [0 NaN], [0 -Inf], 'abc', true, 1i, [1; 2], single(5), int32(5), [], [1 2 3], 1e308, -1e308};
rows = struct('value', {}, 'ok', {}, 'id', {}, 'msg', {});
for k = 1:numel(vals)
    v = vals{k};
    if ischar(v), vs = ['''' v '''']; else, vs = mat2str(v); end
    try
        sa.FrequencyOffset = v;
        rows(k) = struct('value', vs, 'ok', true, 'id', '', 'msg', mat2str(sa.FrequencyOffset));
        sa.FrequencyOffset = 0;
    catch ME
        rows(k) = struct('value', vs, 'ok', false, 'id', ME.identifier, 'msg', ME.message);
    end
    fprintf('FrequencyOffset %s -> ok=%d %s | %s\n', rows(k).value, rows(k).ok, rows(k).id, rows(k).msg);
end
delete(sa);
out = struct('matlab_version', version, 'cases', rows);
fid = fopen('probe_r5_offset.json', 'w'); fprintf(fid, '%s\n', jsonencode(out, 'PrettyPrint', true)); fclose(fid);
end
