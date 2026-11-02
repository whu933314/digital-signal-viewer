function w4000_fft_ref()
% Round 5 (spectral_mask review): the two WindowLength-4000 captures (mask_A_doc_upper_W4000_*, N = 1, one
% Hann-periodic periodogram per call) rebuilt with MATLAB's own fft, so the DSV-vs-scope residual can be split into
% "scope vs MATLAB fft" and "DSV (numpy pocketfft) vs MATLAB fft". Function-level MATLAB only (no scope).
% Run from tests/matlab_ref/spectral_mask (all paths relative to that folder); writes w4000_fft_call{k}.txt
% (%.17g, one row per bin, one column per channel) and w4000_fft_ref.json.
d = fullfile('..', 'scope', 'spectral_mask');
L = 4000; w = hann(L, 'periodic');
out = struct('matlab_version', version, 'window', 'hann periodic 4000', 'nfft', L, 'model', ...
    '10*log10(|fft(w.*x)|^2/sum(w)^2 * (2 for interior one-sided bins)) + 30', 'calls', []);
calls = struct('k', {}, 'signal_file', {}, 'scope_spectrum_file', {}, 'fft_file', {}, 'max_abs_diff_dB', {}, ...
    'argmax_bin', {}, 'argmax_channel', {}, 'bit_identical_bins', {}, 'numel', {});
for k = 1:4
  sigf = sprintf('mask_A_update%d_ch1_ch2.txt', k);
  scf = sprintf('mask_A_doc_upper_W4000_call%d_S.txt', k);
  x = load(fullfile(d, 'signals', sigf));
  S = load(fullfile(d, 'spectra', scf));
  X = fft(w .* x, L);
  P = abs(X).^2 / sum(w)^2;
  P = P(1:L/2+1, :); P(2:end-1, :) = 2 * P(2:end-1, :);
  D = 10*log10(P) + 30;
  [m, i] = max(abs(D(:) - S(:)));
  [ib, ic] = ind2sub(size(S), i);
  fftf = sprintf('w4000_fft_call%d.txt', k);
  fid = fopen(fftf, 'w'); fprintf(fid, '%.17g %.17g\n', D.'); fclose(fid);
  calls(k) = struct('k', k, 'signal_file', sigf, 'scope_spectrum_file', scf, 'fft_file', fftf, ...
      'max_abs_diff_dB', m, 'argmax_bin', ib - 1, 'argmax_channel', ic, 'bit_identical_bins', nnz(D(:) == S(:)), 'numel', numel(S));
  fprintf('call %d: max|MATLAB fft model - scope| = %.17g dB at bin %d ch %d; bit-identical %d of %d\n', k, m, ib - 1, ic, nnz(D(:) == S(:)), numel(S));
end
out.calls = calls;
fid = fopen('w4000_fft_ref.json', 'w'); fprintf(fid, '%s\n', jsonencode(out, 'PrettyPrint', true)); fclose(fid);
end
