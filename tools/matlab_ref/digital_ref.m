x01 = readmatrix(fullfile('ref', 'bilevel_D01.txt'))';
r = struct();
[s, sl, si] = settlingtime(x01, 1, 2); r.settle_d2 = s; r.settle_inst = si;
[s] = settlingtime(x01, 1, 1); r.settle_d1 = s;
[os, ~, oi] = overshoot(x01, 1); r.over = os; r.over_inst = oi;
[us, ~, ui] = undershoot(x01, 1); r.under = us;
r.pre_over = overshoot(x01, 1, 'Region', 'Preshoot'); r.pre_under = undershoot(x01, 1, 'Region', 'Preshoot');
[rt, lt, ut] = risetime(x01, 1); r.rise = rt; r.rise_lt = lt; r.rise_ut = ut;
r.fall = falltime(x01, 1); r.slew = slewrate(x01, 1);
r.mid = midcross(x01, 1);
fid = fopen(fullfile('ref', 'digital_ref.json'), 'w'); fprintf(fid, '%s', jsonencode(r)); fclose(fid);
fprintf('settle d2 %s inst %s\nsettle d1 %s\nover %s under %s pre_over %s pre_under %s\nrise %s lt %s ut %s\nfall %s slew %s mid %s\n', ...
  mat2str(r.settle_d2', 5), mat2str(r.settle_inst', 5), mat2str(r.settle_d1', 5), mat2str(r.over', 4), mat2str(r.under', 4), ...
  mat2str(r.pre_over', 4), mat2str(r.pre_under', 4), mat2str(r.rise', 4), mat2str(r.rise_lt', 5), mat2str(r.rise_ut', 5), mat2str(r.fall', 4), mat2str(r.slew', 4), mat2str(r.mid'));
