fs = 1000; out = struct();
for nm = {'A', 'B', 'C', 'D'}
    y = readmatrix(fullfile('ref', ['bilevel_' nm{1} '.txt']));
    r = struct();
    [w, ic, fc] = pulsewidth(y, fs); r.wpos = w; r.wpos_ic = ic; r.wpos_fc = fc;
    [w, ic, fc] = pulsewidth(y, fs, 'Polarity', 'negative'); r.wneg = w; r.wneg_ic = ic;
    [p, ic, fc] = pulseperiod(y, fs); r.ppos = p; r.ppos_ic = ic;
    [p] = pulseperiod(y, fs, 'Polarity', 'negative'); r.pneg = p;
    [d] = dutycycle(y, fs); r.dpos = d;
    [d] = dutycycle(y, fs, 'Polarity', 'negative'); r.dneg = d;
    out.(nm{1}) = r;
end
x01 = [0 0 0 1 1 1 0 0 1 1 1 0 0 0 1 1 0 0 0 0 1 1 1 1 1 0];
r = struct(); r.wpos = pulsewidth(x01); r.ppos = pulseperiod(x01); r.dpos = dutycycle(x01);
r.wneg = pulsewidth(x01, 'Polarity', 'negative'); r.pneg = pulseperiod(x01, 'Polarity', 'negative'); r.dneg = dutycycle(x01, 'Polarity', 'negative');
r.mid = midcross(x01); r.levels = statelevels(x01);
out.D01 = r; writematrix(x01(:), fullfile('ref', 'bilevel_D01.txt'));
% 峰值
yp = readmatrix(fullfile('ref', 'peaks_input.txt'));
pk = struct();
[v, l] = findpeaks(yp, 'NPeaks', 3, 'SortStr', 'descend'); pk.default3 = struct('v', v, 'l', l);
[v, l] = findpeaks(yp, 'NPeaks', 5, 'SortStr', 'descend', 'MinPeakDistance', 50); pk.dist50 = struct('v', v, 'l', l);
[v, l] = findpeaks(yp, 'NPeaks', 5, 'SortStr', 'descend', 'Threshold', 0.05); pk.thr005 = struct('v', v, 'l', l);
[v, l] = findpeaks(yp, 'NPeaks', 99, 'SortStr', 'descend', 'MinPeakHeight', 1.05); pk.minh105 = struct('v', v, 'l', l);
[v, l] = findpeaks(yp, 'NPeaks', 4, 'SortStr', 'descend', 'MinPeakHeight', 0.5, 'MinPeakDistance', 100, 'Threshold', 0.01); pk.combo = struct('v', v, 'l', l);
pl = [0 1 3 3 3 1 0 2 2 0 5 1 5 0 4 4 4 4 2 7];
[v, l] = findpeaks(pl); pk.plateau = struct('v', v, 'l', l);
[v, l] = findpeaks(pl, 'Threshold', 1); pk.plateau_thr1 = struct('v', v, 'l', l);
[v, l] = findpeaks(pl, 'MinPeakDistance', 3, 'SortStr', 'descend'); pk.plateau_d3 = struct('v', v, 'l', l);
writematrix(pl(:), fullfile('ref', 'peaks_plateau.txt'));
out.peaks = pk;
fid = fopen(fullfile('ref', 'cycles_ref.json'), 'w'); fprintf(fid, '%s', jsonencode(out)); fclose(fid);
s = out.A; fprintf('A wpos %s ppos %s dpos %s\n', mat2str(s.wpos', 5), mat2str(s.ppos', 5), mat2str(s.dpos', 5));
s = out.D01; fprintf('D01 wpos %s ppos %s dpos %s wneg %s pneg %s dneg %s mid %s\n', mat2str(s.wpos'), mat2str(s.ppos'), mat2str(s.dpos', 4), mat2str(s.wneg'), mat2str(s.pneg'), mat2str(s.dneg', 4), mat2str(s.mid'));
fprintf('plateau peaks %s at %s ; thr1 %s at %s ; d3 %s at %s\n', mat2str(pk.plateau.v), mat2str(pk.plateau.l), mat2str(pk.plateau_thr1.v), mat2str(pk.plateau_thr1.l), mat2str(pk.plateau_d3.v), mat2str(pk.plateau_d3.l));
