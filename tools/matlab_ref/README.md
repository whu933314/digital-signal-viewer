# MATLAB 參考值

`tests/matlab_ref/` 裡的測試訊號與 JSON 是用這裡的 .m 腳本在 MATLAB R2025a（Signal Processing Toolbox）算出來的，
`dsv_measure.selftest`、`dsv_spectrum.selftest`（`python signal_viewer.py --selftest` 會跑）拿 DSV 自己的實作逐筆比對：

| 腳本 | 產生 | 比對的 MATLAB 函式 |
|---|---|---|
| `bilevel_ref.m` | `bilevel_A..D.txt`、`peaks_input.txt`、`bilevel_ref.json` | statelevels、risetime、falltime、slewrate、overshoot、undershoot（含 'Region','Preshoot'）、settlingtime、midcross、findpeaks |
| `cycles_ref.m` | `bilevel_D01.txt`、`peaks_plateau.txt`、`cycles_ref.json` | pulsewidth、pulseperiod、dutycycle（正、負極性）、findpeaks（平頂、Threshold、MinPeakDistance） |
| `digital_ref.m` | `digital_ref.json` | 理想 0/1 階梯的 settlingtime、overshoot、undershoot、risetime、midcross |
| `spectrum_ref.m` | `spec_real.txt`、`spec_cplx.txt`、`spectrum_ref.json` | hann／hamming／flattopwin／blackmanharris（periodic）、chebwin、kaiser、enbw、pwelch（mean／maxhold／minhold、onesided／twosided／centered、power／psd、重疊、NFFT 折疊與補零）、spectrogram（power／psd、reassigned）、findpeaks（dB 頻譜） |

重新產生：在這個資料夾的上一層（`tools/`）開 MATLAB，`cd matlab_ref`，先 `mkdir ref` 再依序執行這些腳本，把 `ref/` 裡的檔案複製到 `tests/matlab_ref/`。
這些是 MATLAB 算出的數值，不含 MATLAB 的程式碼；DSV 的實作是照 MATLAB 文件的定義自己寫的。
