% 第二批頻譜工具的 MATLAB 參考值：視窗函數、ENBW、pwelch（平均／max-hold／min-hold、單邊／置中、power／psd、
% overlap、NFFT 比視窗短（wrap）或長（補零））、spectrogram（power／psd、單邊／置中、reassigned）。
% 輸入訊號先用 %.17g 寫成文字再讀回來算，DSV 讀同一份檔案，兩邊用的是完全相同的 double。
out = struct();
fs = 1000; N = 5000; t = (0:N-1)'/fs;
rng(7);
xr = sin(2*pi*50*t) + 0.01*sin(2*pi*123.4*t + 0.3) + 0.2 + 0.001*randn(N, 1);
fid = fopen(fullfile('ref', 'spec_real.txt'), 'w'); fprintf(fid, '%.17g\n', xr); fclose(fid);
xr = readmatrix(fullfile('ref', 'spec_real.txt'));
fs2 = 2e6; N2 = 4096; t2 = (0:N2-1)'/fs2;
rng(11);
xc = exp(1j*2*pi*150e3*t2) + 0.1*exp(-1j*2*pi*400e3*t2 + 1j*0.7) + 0.003*(randn(N2, 1) + 1j*randn(N2, 1));
fid = fopen(fullfile('ref', 'spec_cplx.txt'), 'w'); fprintf(fid, '%.17g %.17g\n', [real(xc) imag(xc)].'); fclose(fid);
m = readmatrix(fullfile('ref', 'spec_cplx.txt')); xc = complex(m(:, 1), m(:, 2));
kb = @(a) (a > 50) * 0.1102*(a - 8.7) + (a >= 21 && a <= 50) * (0.5842*(a - 21)^0.4 + 0.07886*(a - 21));
% 1) 視窗
W = struct();
for L = [8 9 64]
    s = struct();
    s.rect = ones(L, 1); s.hann = hann(L, 'periodic'); s.hamming = hamming(L, 'periodic');
    s.flattop = flattopwin(L, 'periodic'); s.bh = blackmanharris(L, 'periodic');
    s.cheb45 = chebwin(L, 45); s.cheb60 = chebwin(L, 60); s.cheb100 = chebwin(L, 100);
    s.kaiser45 = kaiser(L, kb(45)); s.kaiser60 = kaiser(L, kb(60)); s.kaiser100 = kaiser(L, kb(100));
    W.(sprintf('L%d', L)) = s;
end
out.windows = W;
E = struct();
for L = [1000 1001]
    s = struct();
    s.rect = enbw(ones(L, 1)); s.hann = enbw(hann(L, 'periodic')); s.hamming = enbw(hamming(L, 'periodic'));
    s.flattop = enbw(flattopwin(L, 'periodic')); s.bh = enbw(blackmanharris(L, 'periodic'));
    s.cheb60 = enbw(chebwin(L, 60)); s.kaiser60 = enbw(kaiser(L, kb(60))); s.kaiser100 = enbw(kaiser(L, kb(100)));
    E.(sprintf('L%d', L)) = s;
end
out.enbw = E;
out.kaiser_beta = struct('a20', kb(20), 'a21', kb(21), 'a30', kb(30), 'a50', kb(50), 'a51', kb(51), 'a60', kb(60), 'a100', kb(100));
% 2) pwelch
P = struct();
w = hann(256, 'periodic');
[p, f] = pwelch(xr, w, 0, 256, fs, 'onesided', 'power'); P.a_mean = struct('f', f, 'p', p);
p = pwelch(xr, w, 0, 256, fs, 'onesided', 'power', 'maxhold'); P.a_max = p;
p = pwelch(xr, w, 0, 256, fs, 'onesided', 'power', 'minhold'); P.a_min = p;
[p, f] = pwelch(xr, w, 0, 256, fs, 'onesided', 'psd'); P.a_psd = struct('f', f, 'p', p);
[p, f] = pwelch(xr, w, 128, 512, fs, 'centered', 'power'); P.b = struct('f', f, 'p', p);
[p, f] = pwelch(xr, w, 128, 512, fs, 'twosided', 'power'); P.b2 = struct('f', f, 'p', p);
wk = kaiser(300, kb(60));
[p, f] = pwelch(xc, wk, 99, 128, fs2, 'centered', 'psd'); P.c = struct('f', f, 'p', p);
wc = chebwin(200, 80);
[p, f] = pwelch(xc, wc, 0, 200, fs2, 'centered', 'power'); P.d = struct('f', f, 'p', p);
p = pwelch(xc, wc, 0, 200, fs2, 'centered', 'power', 'maxhold'); P.d_max = p;
p = pwelch(xc, wc, 0, 200, fs2, 'centered', 'power', 'minhold'); P.d_min = p;
wf = flattopwin(511, 'periodic');
[p, f] = pwelch(xr, wf, 255, 511, fs, 'onesided', 'power'); P.e = struct('f', f, 'p', p);
[p, f] = pwelch(xr, wf, 255, 511, fs, 'centered', 'power'); P.e_c = struct('f', f, 'p', p);
[p, f] = pwelch(xr, blackmanharris(1000, 'periodic'), 0, 1000, fs, 'onesided', 'power'); P.f_bh = struct('f', f, 'p', p);
[p, f] = pwelch(xr, ones(100, 1), 50, 100, fs, 'onesided', 'psd'); P.f_rect = struct('f', f, 'p', p);
[p, f] = pwelch(xr, w, 0, 100, fs, 'onesided', 'power'); P.g_wrap = struct('f', f, 'p', p);
out.pwelch = P;
% 3) spectrogram
S = struct();
[~, f, tt, ps] = spectrogram(xr, hann(128, 'periodic'), 64, 128, fs, 'power', 'onesided'); S.g = struct('f', f, 't', tt, 'ps', ps);
[~, f, tt, ps] = spectrogram(xr, hann(128, 'periodic'), 64, 128, fs, 'psd', 'onesided'); S.g_psd = struct('f', f, 't', tt, 'ps', ps);
[~, f, tt, ps] = spectrogram(xc, kaiser(100, kb(60)), 50, 256, fs2, 'centered', 'psd'); S.h = struct('f', f, 't', tt, 'ps', ps);
[~, f, tt, ps] = spectrogram(xr, hann(120, 'periodic'), 0, 120, fs, 'power', 'centered'); S.h2 = struct('f', f, 't', tt, 'ps', ps);
[~, f, tt, ps, fc, tc] = spectrogram(xr(1:1000), hann(128, 'periodic'), 96, 128, fs, 'reassigned', 'power', 'onesided');
S.r = struct('f', f, 't', tt, 'ps', ps, 'fc', fc, 'tc', tc);
[~, f, tt, ps, fc, tc] = spectrogram(xc(1:1024), kaiser(64, kb(60)), 48, 64, fs2, 'reassigned', 'psd', 'centered');
S.rc = struct('f', f, 't', tt, 'ps', ps, 'fc', fc, 'tc', tc);
out.spectrogram = S;
% 4) 頻譜峰值（findpeaks 在 dB 頻譜上）
db = 10*log10(P.a_mean.p);
[v, l] = findpeaks(db, 'NPeaks', 3, 'SortStr', 'descend'); out.peaks = struct('v', v, 'l', l);
[v, l] = findpeaks(db, 'NPeaks', 5, 'SortStr', 'descend', 'MinPeakHeight', -60, 'MinPeakDistance', 5, 'Threshold', 0.5); out.peaks2 = struct('v', v, 'l', l);
fid = fopen(fullfile('ref', 'spectrum_ref.json'), 'w'); fprintf(fid, '%s', jsonencode(out)); fclose(fid);
disp('spectrum_ref done');
