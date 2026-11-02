function finite_template()
% validateattributes 'finite' template (MATLAB:expectedFinite) with the spectrumAnalyzer property name
% FrequencyOffset, for the values the review probed on the scope (NaN, Inf, -Inf, [0 NaN]); plus the 'scalar'
% template for the same name. Function-level only. Writes finite_template.json next to this folder's other refs.
vals = {NaN, Inf, -Inf, [0 NaN], [0 10], 0};
rows = struct('value', {}, 'ok', {}, 'id', {}, 'msg', {});
for k = 1:numel(vals)
  try
    validateattributes(vals{k}, {'numeric'}, {'finite'}, '', 'FrequencyOffset');
    rows(k) = struct('value', mat2str(vals{k}), 'ok', true, 'id', '', 'msg', '');
  catch ME
    rows(k) = struct('value', mat2str(vals{k}), 'ok', false, 'id', ME.identifier, 'msg', ME.message);
  end
  fprintf('finite %s -> ok=%d %s | %s\n', rows(k).value, rows(k).ok, rows(k).id, rows(k).msg);
end
out = struct('matlab_version', version, 'cases', rows);
fid = fopen('finite_template.json', 'w'); fprintf(fid, '%s\n', jsonencode(out, 'PrettyPrint', true)); fclose(fid);
end
