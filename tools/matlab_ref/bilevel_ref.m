% 產生雙位準測試訊號並用 Signal Processing Toolbox 算每個轉態的量測，寫成 JSON（DSV 的實作拿來逐筆比對）
out = struct();
fs = 1000; t = (0:1999)'/fs;
sq = double(mod(t, 0.4) < 0.2);
% A：二階 Butterworth（有一點過衝）＋雜訊
[b, a] = butter(2, 0.12); yA = filter(b, a, sq); rng(3); yA = yA + 0.002*randn(size(yA));
% B：FIR 低通（前後都有振鈴 → preshoot／overshoot／undershoot）
h = fir1(60, 0.08); yB = conv(sq, h, 'same');
% C：有一個沒到頂的 runt 脈波、雜訊大一點
yC = filter(b, a, sq); yC(900:960) = 0.45 * (1 - exp(-(0:60)'/8)) .* exp(-(0:60)'/40) + yC(900:960); rng(5); yC = yC + 0.01*randn(size(yC));
% D：從高位準開始（先下降）、二階欠阻尼（大振鈴）
sqD = 1 - sq; [bD, aD] = deal([0.0391 0.0782 0.0391], [1 -1.5 0.656]); yD = filter(bD, aD, sqD) * 2 + 0.5;
cases = {'A', yA; 'B', yB; 'C', yC; 'D', yD};
for k = 1:size(cases, 1)
    nm = cases{k, 1}; y = cases{k, 2};
    writematrix(y, fullfile('ref', ['bilevel_' nm '.txt']));
    r = struct();
    r.levels = statelevels(y);
    [rt, lt, ut, ll, ul] = risetime(y, fs); r.rise = rt; r.rise_lt = lt; r.rise_ut = ut; r.reflo = ll; r.refhi = ul;
    [ft, flt, fut] = falltime(y, fs); r.fall = ft; r.fall_lt = flt; r.fall_ut = fut;
    r.slew = slewrate(y, fs);
    [os, oslev, osinst] = overshoot(y, fs); r.over = os; r.over_inst = osinst;
    [us, uslev, usinst] = undershoot(y, fs); r.under = us; r.under_inst = usinst;
    [pso, ~, psoi] = overshoot(y, fs, 'Region', 'Preshoot'); r.pre_over = pso; r.pre_over_inst = psoi;
    [psu, ~, psui] = undershoot(y, fs, 'Region', 'Preshoot'); r.pre_under = psu; r.pre_under_inst = psui;
    [st, slev, sinst] = settlingtime(y, fs, 0.02); r.settle = st; r.settle_inst = sinst;
    r.midcross = midcross(y, fs);
    out.(nm) = r;
end
% 峰值：findpeaks 幾種參數
yp = yB; rng(7); yp = yp + 0.05*randn(size(yp));
writematrix(yp, fullfile('ref', 'peaks_input.txt'));
pk = struct();
[v, l] = findpeaks(yp, 'NPeaks', 3, 'SortStr', 'descend'); pk.default3 = struct('v', v, 'l', l);
[v, l] = findpeaks(yp, 'NPeaks', 5, 'SortStr', 'descend', 'MinPeakDistance', 50); pk.dist50 = struct('v', v, 'l', l);
[v, l] = findpeaks(yp, 'NPeaks', 5, 'SortStr', 'descend', 'Threshold', 0.05); pk.thr005 = struct('v', v, 'l', l);
[v, l] = findpeaks(yp, 'NPeaks', 99, 'SortStr', 'descend', 'MinPeakHeight', 1.05); pk.minh105 = struct('v', v, 'l', l);
[v, l] = findpeaks(yp, 'NPeaks', 4, 'SortStr', 'descend', 'MinPeakHeight', 0.5, 'MinPeakDistance', 100, 'Threshold', 0.01); pk.combo = struct('v', v, 'l', l);
out.peaks = pk;
fid = fopen(fullfile('ref', 'bilevel_ref.json'), 'w'); fprintf(fid, '%s', jsonencode(out)); fclose(fid);
disp('done');
s = out.A; fprintf('A: levels %s rise %s fall %s\n', mat2str(s.levels, 6), mat2str(s.rise', 5), mat2str(s.fall', 5));
fprintf('A over %s under %s settle %s\n', mat2str(s.over', 4), mat2str(s.under', 4), mat2str(s.settle', 4));
s = out.B; fprintf('B: preU %s preO %s over %s under %s\n', mat2str(s.pre_under', 4), mat2str(s.pre_over', 4), mat2str(s.over', 4), mat2str(s.under', 4));
s = out.C; fprintf('C: rise n=%d fall n=%d over %s\n', numel(s.rise), numel(s.fall), mat2str(s.over', 4));
s = out.D; fprintf('D: levels %s rise %s fall %s over %s under %s settle %s\n', mat2str(s.levels, 5), mat2str(s.rise', 4), mat2str(s.fall', 4), mat2str(s.over', 4), mat2str(s.under', 4), mat2str(s.settle', 4));
