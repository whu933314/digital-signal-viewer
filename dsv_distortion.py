# -*- coding: utf-8 -*-
"""失真量測（MATLAB Spectrum Analyzer 的 MEASUREMENTS › DISTORTION：諧波失真 THD／SNR／SINAD／SFDR、互調失真 TOI）——純 numpy，和 GUI 分開。

兩條路：
1. **scope_harmonic() / scope_intermod()**：Spectrum Analyzer 本體（spectrumAnalyzer scope）顯示的數字——DSV 頻譜視窗要顯示的是這一組。
   依據是 2026-10-24 開 MATLAB R2025a 的 spectrumAnalyzer 實測 20 個 capture 解出的規則（scope_capture/ANALYSIS.md §4、rules.json D1–D11；
   數據抽到 tests/matlab_ref/scope/distortion/scope_distortion.json：每個 capture 用的設定、scope 回的全部量測欄位、輸入訊號的檔名與倍率、顯示格
   的中介資料；顯示的頻譜不抄——selftest 從訊號用同一個頻譜模型重建）。scope 的演算法沒有公開，規則是用數字反推的；
   15 個諧波 capture 裡 14 個每一欄都到 1.3e-11 dB／1e-12 Hz，5 個互調 capture 到 1.2e-13 dB；對不上的（見「未定」）列成已知差異。
2. thd／snr／sinad／sfdr／toi 與 harmonic_distortion／intermod_distortion：Signal Processing Toolbox 函式的 'psd'／'power'／時域形式
   （可以用 MATLAB 位元級驗證，tests/matlab_ref/distortion/）。scope 的數字**不等於**這些函式（音的功率是峰值 bin 不是積分、諧波逐一清掉、
   Pnoise 公式不同），所以這一條是次要的、給想對 MATLAB 函式的人用。

Spectrum Analyzer 本體的規則（實測解出；D1–D11）：
- D1 輸入＝顯示的 trace 換成線性功率（W/bin），只用 f ≥ 0 的半邊：單邊顯示就是整條；兩邊（centered）顯示取 f ≥ 0 的 bin 照顯示值（不加倍、
  +fs/2 那個 bin 也算），所以絕對功率比單邊低 3.0103 dB、比值只差在沒加倍的 DC／Nyquist bin（dist_h_offbin_2s_N6：23.977307 vs 26.987607 dBm，
  SNR 76.08472 vs 76.08548）。power-density 顯示：trace 乘 RBW 當每 bin 功率去搜尋與算比值，但功率列報 dBm/Hz（峰值 bin 的密度值；D11）。
- D2 DC：從 bin 0 往右走、只要 P[i+1] ≤ P[i] 就繼續，[0, R0] 清成 0，W0＝(R0+1)·df。
- D3 基頻：t1＝剩下的最大 bin；從 t1 往左（P[L−1] ≤ P[L]）／往右（P[R+1] ≤ P[R]）走單調不升的裙邊得 [L, R]；Fe1＝這段的功率重心（只拿來瞄準）；
  **P1＝P[t1] 峰值 bin 的值**（不是積分：dist_h_noisy 的 25.832889 dBm＝0.5 W × Hann 在 0.45 bin 偏移的損失，積分會是 27.0）；W1＝(R−L+1)·df；
  清掉 [L, R]；報的頻率是 bin 中心 f[t1]（2531.7 Hz 的音報 2531.25）。
- D4 諧波 k＝2..N：目標 bin tb＝round(k·Fe1/df)；tb 超過最後一個 bin 就**停**，這列和之後的都不列（dist_h_alias：只有 2 列；dist_h_offbin_1s_N10：
  9 列，H10＝25317 Hz > 24000；不折回、不加寬度）；否則在 [tb−1, tb+1] 取工作頻譜的最大 bin（已經清成 0 的也算、同值取第一個），從它走裙邊
  （0 的區域也照走、寬度照算——dist_h_lowf 的 Wsum 要是 82 個 bin＝1+7+7+10+19+19+19），P_k＝那個 bin 的值（0 → 報 −Inf），清掉。
- D5 Pnoise＝(Σ剩餘 bin·df + 剩餘非 0 bin 的中位數·Wsum)/RBW，Wsum＝W0+W1+…+Wn（文件的公式照字面）。
- D6 THD＝10·log10(ΣP_k/P1)、THD%＝100·10^(THD/20)、SNR＝10·log10(P1/Pnoise)、SINAD＝10·log10(P1/(ΣP_k+Pnoise))、
  SFDR＝10·log10(P1/max(P_maxspur, max P_k))——max P_k 這項 14 個 capture 都證實，P_maxspur（剩餘最大 bin）這項沒有 capture 能證實（見「未定」）。
- D7 互調：清 DC；F1＝最強的音、F2＝次強（同 D3 的抓法、清掉）；三階積在 2·Fe1−Fe2（第 3 列）與 2·Fe2−Fe1（第 4 列），用重心瞄準、±1 bin 窗、
  峰值 bin 值（dist_toi_doc：音報 6000／5015.625，積卻在 6984.375／3984.375＝最接近 2·6000−5000／2·5000−6000 的 bin）；
  TOI_lower＝P_F1+(P_F2−P_2F1−F2)/2、TOI_upper＝P_F2+(P_F1−P_2F2−F1)/2、TOI＝平均（dBm）；積 < 0 Hz → 功率 −Inf、TOI +Inf。
- D8 量測範圍＝trace 的整個 Nyquist 範圍，和 scope 的 FrequencySpan 無關（span [0 6000] 與 [1000 24000] 的 capture 數字和 full 完全相同）。
- D9 Max-Hold 開著時用 normal trace（dist_h_maxhold_2calls 報第 2 幀 0.1·h_lowf 的 60 Hz／5.88 dBm）——呼叫端傳 normal trace。
- D10 複數訊號照算（兩邊顯示的正半邊；dist_cplx_obw_2s_harmonic_N6 到 4.3e-14 dB），不空白、不報錯。
- 頻譜模型（selftest 重建顯示用；ANALYSIS.md §1，fresh 的顯示到 4.8e-10 dB）：periodic Hann、NFFT＝max(1024, L)、power |X|²/(Σw)²、
  psd |X|²/(fs·Σw²)、單邊 DC／Nyquist 以外 ×2、兩邊 MATLAB centered（Nyquist 在 +fs/2）、RBW＝ENBW＝1.5·fs/L——就是 dsv_spectrum.design_window
  ('hann') 與 welch(..., noverlap 0, nfft, 'onesided'／'centered')。

函式路徑的做法（MATLAB 的 thd、snr、sinad、toi 與 bandpower 的 psd 積分，用自己的話描述）：
輸入一律是**單邊**頻譜：頻率格 F（F[0] 必須是 0、遞增）與同長度的 Pxx（'psd'：功率密度，單位²/Hz）或 Sxx（'power'：每個 bin 的
功率，單位²；要另外給 RBW＝視窗的解析頻寬，而且 RBW ≥ 平均 bin 寬）。DSV 的 dsv_spectrum.welch(..., 'onesided') 回傳的 power／psd／
rbw 就是這個形式；雙邊（centered／twosided）結果先用 fold_onesided() 折成單邊。
- 'power' 輸入先換成密度 Pxx＝Sxx/RBW，門檻值 rbw＝RBW；'psd' 輸入 rbw＝mean(diff(F))；時域輸入（thd(x,fs) 等）rbw＝Kaiser 視窗的 ENBW。
  所以同一筆資料用 'power' 和 'psd' 形式算出的數字可以差一點（rbw 只當門檻用，見下）。
- 抓一根音（tone）：沒給目標頻率就取整個 Pxx 的最大值那個 bin；給了目標頻率 f 就先找最接近 f 的 bin，再在它左右各一個 bin 裡取最大的
  （f 不在 [F[0], F[-1]] 裡 → 這根音不存在，功率、頻率都是 NaN）。接著從峰值往左走、只要 Pxx 不升就一直走，往右同理：單調下降的
  裙邊（leakage）全算這根音的一部分，得到 [left, right]（含兩端）。
  頻率＝這段的功率加權重心 Σ(F·Pxx)/ΣPxx；功率＝這段密度的矩形積分（bandpower：寬度是 diff(F) 再補一個「缺的」平均寬度——段從 0 Hz
  開始時補在尾端、否則補在前端）；段只有一個 bin 時用 Pxx·(F[t+1]−F[t−1])/2，在頭尾則用 Pxx·mean(diff(F))。
  保護：積出來的功率若小於 rbw·Pxx[峰]（鄰近的音侵入視窗主瓣時會這樣），就改成 rbw·Pxx[峰]、頻率改成峰值 bin 的頻率。
- DC：先把 Pxx[0] 加倍（＋3 dB），以 f＝0 抓一根音，把它的範圍清成 0。
- 基頻＝剩下的最大值那根音（P1、Fe1）。
- THD（thd）：第 k 個諧波在 k·Fe1 附近抓音（k＝2..N，N 預設 6、必須是 > 1 的整數），**不**把找到的諧波清掉再找下一個；
  THD＝10·log10(Σ找到的諧波功率 / P1)（dBc），harm_pow＝各諧波的 10·log10(功率)（dB，輸入單位²）、harm_freq＝重心頻率，超過
  Nyquist 的諧波是 NaN、不計入。'aliased'：目標頻率先折回 [0, fs/2]（g＝mod(k·Fe1, fs)，g > fs/2 → fs−g；fs 在 'psd'／'power' 形式假設
  是 2·F[-1]，時域形式用真正的取樣率）。
- SNR（snr）：DC、基頻、各諧波（k＝2..N）的範圍都清成 0；雜訊底估計＝剩下 > 0 的 bin 的中位數，填進清掉的 bin；再和原始 Pxx 逐 bin
  取小（填的值不能高過原本的；中位數是 NaN——全被清光——時取原值）；雜訊功率＝整個 F 的 bandpower 積分。SNR＝10·log10(P1/雜訊)，
  第二個輸出是 10·log10(雜訊)。
- SINAD（sinad）：和 SNR 一樣但只清 DC 和基頻（諧波留在雜訊裡）。
- SFDR（sfdr）：時域形式**不**去平均值（其他四個都先 x−mean(x)），Kaiser(N, 38) 週期圖 'psd'；清 DC、抓基頻並清掉它的範圍，再把
  |F−Fe1| < MSD 的 bin 清 0；最大的 spur＝剩下最大值的 bin 抓音（積分功率）。SFDR＝10·log10(P1/Pspur)。
  'power' 形式（sfdr(Sxx,F,'power')）用的是 bin 值不是積分：Sxx[0] 加倍、從頭清到第一次上升為止；基頻＝最大 bin；左界＝基頻左邊最後一個
  「往右會下降」的 bin、右界＝基頻右邊第一次上升前的那個 bin，再擴到 ±MSD（F ≤ Fe1−MSD 的最後一個、F > Fe1+MSD 的第一個）；清掉
  [左, 右] 後最大的 bin 就是 spur。Sxx 必須全為正。
- TOI（toi）：清 DC；第一根音＝最大值，暫時清掉後找第二根音，再把第一根放回；依頻率排好（F1 < F2）；三階互調 2F1−F2、2F2−F1
  附近各抓一根音（不在範圍內 → NaN；下方那根若重心頻率 ≤ DC 範圍右端的頻率也算 NaN）。全部換成 dB 後
  OIP3＝mean(基頻 dB) + (mean(基頻 dB) − mean(IM3 dB))/2；任一 IM3 是 NaN → OIP3 NaN。
  spectrumAnalyzer 文件的公式 TOI_lower＝P_F1 + (P_F2 − P_(2F1−F2))/2、TOI_upper＝P_F2 + (P_F1 − P_(2F2−F1))/2、TOI＝兩者平均，代數上
  就等於 OIP3（研究報告以 MATLAB 數字確認，差 < 4e-15）。
- 時域形式（thd(x,fs) 等）＝先 x−mean(x)（sfdr 除外）、kaiser(N, 38) 視窗、N 點單邊週期圖 'psd'（這裡用 dsv_spectrum.welch 一段算），
  rbw＝ENBW＝fs·Σw²/(Σw)²，再走上面的流程。

錯誤：MATLAB 會丟錯的輸入（N ≤ 1 或非整數、Fs／MSD ≤ 0、F[0] ≠ 0、RBW < 平均 bin 寬、不認得的選項、不是向量、空陣列…）對應成
DistortionError（identifier＝MATLAB 的錯誤識別碼、英文訊息照 MATLAB、另附繁中說明）。validateattributes 的屬性照 MATLAB 的順序檢查
（例如 F：real、finite、vector，snr 再 increasing、numel；sinad 再 numel、increasing），所以同時有幾個毛病時報的是 MATLAB 會先報的那個。

未定／自行決定（capture 解不出、沒有 capture 碰到、或 MATLAB 沒有對應的地方）：
- scope 路徑是 DSV 顯示用的主路徑（實測 20 個 capture 證實 scope 的數字**不是** thd／snr／sinad／sfdr 的 'power' 形式：音的功率是峰值 bin、諧波
  逐一清掉、Pnoise 公式不同，dist_h_noisy 的基頻差 1.17 dB）；thd／…／harmonic_distortion／intermod_distortion 留著當次要路徑（對 MATLAB 函式用）。
- SFDR 的 P_maxspur：14 個 capture 的 SFDR 都＝P1/max P_k（非諧波 spur 都比諧波小），只有 dist_h_alias_1s_N6 的 28.745379 dB 對不上——文件規則
  （清完剩下的最大 bin）給 35.470829，差 6.73 dB。能給 0.21 dB 的候選（每根音只清峰值 ±1 bin）把 4 個已驗證的 capture 弄壞 3.5–22 dB，不能用；
  其他候選（見 SCOPE_KNOWN）都對不上。這裡**照文件**用清完剩下的最大 bin；dist_h_alias 的 SFDR 列成已知差異（selftest 斷言兩邊的數字）。
  要解開要有「一根非諧波的 spur 比每個諧波都大」的 capture。
- 不存在的互調積（2·Fe2−Fe1 < 0）：scope 功率 −Inf、TOI +Inf（照做），頻率欄 scope 顯示 4171.875 Hz＝第 3 列的積往下一個 bin（f[t3−1]，也＝第 3 列
  搜尋窗的下緣 f[tb3−1]；裙邊左緣對不上）——看起來是殘留的中間值，一個 capture 分不出是哪個 → 這裡回 NaN（不重現沒意義的數字），列成已知差異。
  目標 ≥ 0 但 bin 超過最後一個（超過 Nyquist）的積沒有 capture，照 < 0 Hz 處理（不存在）。
- 文件的「leakage 佔頻寬超過 70 % 時 SNR／SINAD 顯示 –」：沒有 capture 觸發（最大 Wsum 佔比 h_noiseless 2156/24000），門檻怎麼算不確定；
  這裡算 leakage_fraction＝Wsum/（半邊頻寬＝bin 數·df）、回旗標 leakage_blank＝> 0.70，數字照算不清掉，GUI 自己決定要不要顯示「–」。
- 目標 bin 的 round：C／MATLAB 是半數離零，numpy 是半數取偶；用 floor(x+0.5)（沒有 capture 剛好落在 .5）。
- 沒有任何諧波（N＝2 而 H2 已超過 Nyquist）時 ΣP_k＝0 → THD −Inf、THD% 0、SFDR 看 P_maxspur；全被清光（P1＝0）→ 比值 NaN；都不印 numpy 警告。
  沒有 capture。
- power-density 顯示的互調：功率列用密度值（dBm/Hz）；TOI 也是用這些值算（＝power 的 TOI − 10·log10(RBW)，dBm/Hz）。只有諧波有 psd capture
  （D11：功率列 dBm/Hz、比值不變），互調的 psd 沒有 capture。
- 輸入排列：'onesided'、'centered'（取 f ≥ 0）、'twosided'（0..fs(1−1/N)：取前 N//2+1 個 bin＝0..fs/2）；mode＝None 時有負頻率就是 centered。
  F[0] ≠ 0（scope 的 FrequencyOffset）沒有 capture：DC 的走法照樣從第 1 個 bin 開始，目標 bin 用 (k·Fe1 − F[0])/df。
- scope 路徑的絕對功率一律是 10·log10(trace 的單位)；dBm＝+30（ReferenceLoad 1）、dBW／Vrms 的換算由 GUI 用和頻譜線一樣的方式做。
- dist_h_noiseless_1s_N6（沒加雜訊）第 4–6 個諧波（≈ −275 dBm，1e-31 W）與 Pnoise（1e-28 W）是 FFT 的捨入，MATLAB 與 numpy 的 FFT 不同
  （功率差 0.35 dB、SNR 差 6.5e-4 dB）；selftest 斷言兩邊都在 P1·1e-25 的底下、差 ≤ 1 dB／0.01 dB，前 3 列與 THD／SINAD／SFDR 照嚴格容差。
- DSV 自訂保護（scope 路徑）：trace 超過 2^24 個 bin 丟 tooManyBins（不配置、不搜尋）；少於 2 個 bin（f ≥ 0）丟 tooFewBins；trace 必須是非負的
  線性值（傳 dB 進來會被 expectedNonnegative 擋下）；Num Harmonics 要是 2..99 的整數（invalidNumHarmonics，文字同面板）。識別碼用 dsv:scope_*:…
  （scope 沒有 MATLAB 識別碼）。
- THD%＝100·10^(THD/20) 照 spectrumAnalyzer 文件（THDPercent 欄 capture 證實）。
- harmonic_distortion 的 n_harm 照 Spectrum Analyzer 的 Num Harmonics 欄位檢查 2..99（有限實數；錯誤文字照 MATLAB 介面顯示的訊息，
  簡體轉繁體），不合就丟 DistortionError 而不是讓 thd 去配置 N 個元素的陣列（N＝1e9 會把 GUI 卡死）；
  非整數（例如 3.5）MATLAB 介面的檢查放過，但 thd 本身照 MATLAB 丟 expectedInteger——這裡跟 thd。thd／snr 本身和 MATLAB 一樣不設上限。
- 雙邊 → 單邊只對**實數訊號**成立（負頻率是正頻率的鏡像，DC、Nyquist 以外 ×2）；複數（I/Q）訊號不支援——fold_onesided() 不會檢查
  訊號是不是複數，GUI 要自己擋。
- sfdr 的 'psd' 形式（sfdr(Pxx,F,'psd')）MATLAB 沒有公開，這裡提供的算法和 sfdr(x,fs) 在週期圖之後的結果一致；rbw 沒給時用 mean(diff(F))。
- thd／snr 的 'psd' 形式可以用 rbw、fs 參數覆寫門檻與折回取樣率（時域形式就是這樣用的）；MATLAB 的 'psd' 形式沒有這兩個參數。
- 空陣列：MATLAB 的 validateattributes 'vector' 對 0×0 的 [] 丟 expectedVector（1×0／0×1 沒驗過，MATLAB 可能放過再在後面出別的錯），
  這裡任何 size 0 的輸入一律丟 expectedVector（column 形式丟 expectedColumn），不讓 numpy 的 IndexError／ZeroDivisionError 漏出去
  （dsv_spectrum.welch 資料不夠一段時回傳空陣列，GUI 會走到這裡）。純量（0-d）照 MATLAB isvector(純量)＝true 當 1 個元素的向量；
  1 個樣本／1 個 bin 的結果照 MATLAB 是 NaN（mean(diff(F)) 是 NaN），不丟錯也不印 numpy 警告；'power' 形式則因 RBW ≥ NaN 不成立丟
  notGreaterEqual（訊息寫 >= NaN）。
- 型別：X／Pxx／Sxx／F 在 MATLAB 限 single／double、Fs／N／RBW／MSD 限 numeric；這裡整數 dtype 一律轉成 float 接受（MATLAB 會拒絕 int 類別），
  字串／物件／邏輯值丟 invalidType（MATLAB:<func>:invalidType，訊息照 validateattributes 的格式；參考資料沒有這一例，文字未對照）。
  F 不遞增時 snr／sinad 丟 expectedIncreasing（訊息「to be increasing.」未對照）；thd／toi／sfdr 在 MATLAB 也不檢查遞增，照樣不檢查。
- 錯誤訊息裡的數字（RBW ≥ 多少）用 %g 格式、NaN／Inf 照 MATLAB 寫法；參考資料只有 23.4375 一例可對。F 與 Pxx 長度不同一律丟 incorrectNumel
  （MATLAB 的 thd／toi 沒檢查，會在後面出維度錯誤）。non-integer 的 N 照 MATLAB 函式丟 expectedInteger（UI 的 2..99 範圍檢查屬 GUI 層）。
- tone() 是公開的低階函式，不檢查 finite：Pxx 裡有 NaN 時照 MATLAB 的語意——max 略過 NaN（MATLAB max 的公開語意；全是 NaN 才取第 0 個）；
  從峰值往兩側找裙邊時碰到 NaN 就停（NaN 不算「不升」）。thd／snr／sinad／sfdr／toi 本身要求 finite，走不到這裡。
- 絕對功率一律是 10·log10(輸入單位²)；換成 dBm／dBW／Vrms 由 GUI 用和頻譜線一樣的轉換。
- selftest 的容差（見 selftest 的常數）：餵 MATLAB 自己的頻譜（'psd'／'power'／Hann Welch）與時域形式一律 rtol 1e-12（這些值全部都過，
  研究報告的 4.9e-13 也支持）；面板路徑（x → dsv_spectrum.welch(對稱 hann) → harmonic_distortion／intermod_distortion）經過 numpy 的 Welch，
  rtol 1e-9、dB 值另加 1e-9 dB 絕對容差（h_noiseless 的 SNR 是 −4.28e-6 dB，接近 0 的 dB 值相對差沒有意義，觀測相對差 6.8e-10，
  其餘 ≤ 2.2e-11）；頻譜 bin |Δ| ≤ 1e-12·|ref| + 1e-14·峰值（numpy 與 MATLAB 的 FFT 捨入不同，觀測 |Δ|/峰值 ≤ 8.1e-16；底部的 bin
  相對差本來就 > 1e-12）；h_noiseless 時域形式裡低於基頻 250 dB 的值（第 4 個以後的諧波約 −305 dB、雜訊底 −280 dB，共 36 個）是 FFT 捨入底
  的不同實現（餵 MATLAB 自己的 Pxx 時這些值也位元級一致，所以不是演算法的問題），只檢查同為底（相差 ≤ 10 dB、頻率在 2 個 bin 內；
  觀測 ≤ 0.65 dB、1 bin），另外計數、不算進嚴格總數。
"""
from __future__ import annotations

import math
from typing import Any, Dict, NamedTuple, Optional, Sequence, Tuple

import numpy as np

import dsv_spectrum

DEFAULT_NUM_HARMONICS = 6          # thd／snr 的 N 預設；Spectrum Analyzer 的 Num Harmonics 預設也是 6（含基頻）
MAX_PANEL_HARMONICS = 99           # Spectrum Analyzer 的 Num Harmonics 上限（文件：positive integer, at most 99；UI 檢查 2..99）
KAISER_BETA = 38.0                 # 時域形式用的 Kaiser 視窗 β
HARM_TYPES = ("omitaliases", "aliased")
KINDS = ("psd", "power")


class DistortionError(ValueError):
    """MATLAB thd／snr／sinad／sfdr／toi 丟出的輸入錯誤：identifier＝MATLAB 的錯誤識別碼、message＝MATLAB 英文訊息、zh＝繁中說明。"""

    def __init__(self, identifier: str, message: str, zh: str):
        super().__init__(message)
        self.identifier = identifier
        self.message = message
        self.zh = zh

    def __str__(self) -> str:
        return f"{self.message}（{self.zh}）"


class Tone(NamedTuple):
    """一根音：power＝積分功率（線性）、freq＝功率重心頻率、idx＝峰值 bin、left／right＝裙邊範圍（含）。不在範圍內時 idx 是 None。"""
    power: float
    freq: float
    idx: Optional[int]
    left: Optional[int]
    right: Optional[int]


# ----------------------------------------------------------------------------- 輸入檢查（照 MATLAB validateattributes 的訊息）
_ZH_NAME = {"X": "訊號 X", "Pxx": "功率密度 Pxx", "Sxx": "功率頻譜 Sxx", "F": "頻率 F", "Fs": "取樣率 Fs", "N": "諧波數 N",
            "RBW": "解析頻寬 RBW", "MSD": "最小 spur 距離 MSD"}
_MATLAB_CLASS = {"U": "char", "S": "char", "b": "logical", "O": "cell"}


def _num(x: float) -> str:
    """錯誤訊息裡的數字：%g，NaN／Inf 照 MATLAB 的寫法。"""
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Inf" if x > 0 else "-Inf"
    return f"{x:g}"


def _ident(func: str, key: str) -> str:
    """錯誤識別碼：func 自帶前綴（例如 'dsv:scope_harmonic'——scope 的這些量測沒有 MATLAB 識別碼）就直接接 key，否則是 MATLAB:<func>:<key>。"""
    return f"{func}:{key}" if ":" in func else f"MATLAB:{func}:{key}"


def _attr_error(func: str, key: str, k: int, name: str, tail_en: str, tail_zh: str) -> DistortionError:
    return DistortionError(_ident(func, key), f"Expected input number {k}, {name}, to be {tail_en}.",
                           f"第 {k} 個輸入 {_ZH_NAME.get(name, name)} {tail_zh}。")


def _numeric(func: str, a: np.ndarray, k: int, name: str, classes: str) -> None:
    """dtype 要是數值（int／uint／float／complex；complex 之後由 expectedReal 擋）。字串、物件、邏輯值 → invalidType（訊息格式照 validateattributes，未對照）。"""
    if a.dtype.kind not in "iufc":
        cls = _MATLAB_CLASS.get(a.dtype.kind, a.dtype.name)
        raise DistortionError(_ident(func, "invalidType"),
                              f"Expected input number {k}, {name}, to be one of these types:\n\n{classes}\n\nInstead its type was {cls}.",
                              f"第 {k} 個輸入 {_ZH_NAME.get(name, name)} 必須是數值（{classes}），不能是 {cls}。")


def _check_option(func: str, value: Any, allowed: Sequence[str]) -> str:
    v = str(value).strip().lower()
    if v not in allowed:
        raise DistortionError("signal:chknostropts:UnknownOption", f"Unknown option:  '{value}'", f"不認得的選項 '{value}'")
    return v


def _vector(func: str, a, k: int, name: str, column: bool = False, nonneg: bool = False, positive: bool = False) -> np.ndarray:
    """real、finite 的非空向量（column＝True 時還要是直的：MATLAB 'column'）→ 1-D float 陣列。純量當 1 個元素的向量（MATLAB isvector(純量)＝true）。"""
    arr = np.asarray(a)
    _numeric(func, arr, k, name, "single, double")
    if np.iscomplexobj(arr):
        raise _attr_error(func, "expectedReal", k, name, "real", "必須是實數")
    is_vec = arr.size > 0 and arr.ndim <= 2 and sum(d > 1 for d in arr.shape) <= 1
    is_col = is_vec and not (arr.ndim == 2 and arr.shape[0] == 1 and arr.size > 1)
    if column and not is_col:
        raise _attr_error(func, "expectedColumn", k, name, "a column vector", "必須是非空的直向量（column）")
    if not is_vec:
        raise _attr_error(func, "expectedVector", k, name, "a vector", "必須是非空的向量")
    v = np.ascontiguousarray(arr.reshape(-1), dtype=float)
    if not np.all(np.isfinite(v)):
        raise _attr_error(func, "expectedFinite", k, name, "finite", "必須是有限值")
    if positive and not np.all(v > 0):
        raise _attr_error(func, "expectedPositive", k, name, "positive", "必須是正數")
    if nonneg and not np.all(v >= 0):
        raise _attr_error(func, "expectedNonnegative", k, name, "nonnegative", "不能是負數")
    return v


def _scalar(func: str, v, k: int, name: str, positive: bool = True, ge: Optional[float] = None) -> float:
    a = np.asarray(v)
    _numeric(func, a, k, name, "numeric")
    if np.iscomplexobj(a):
        raise _attr_error(func, "expectedReal", k, name, "real", "必須是實數")
    if a.size != 1:
        raise _attr_error(func, "expectedScalar", k, name, "a scalar", "必須是純量")
    x = float(a.reshape(-1)[0])
    if not math.isfinite(x):
        raise _attr_error(func, "expectedFinite", k, name, "finite", "必須是有限值")
    if positive and not x > 0:
        raise _attr_error(func, "expectedPositive", k, name, "positive", "必須是正數")
    if ge is not None and not x >= ge:
        raise _attr_error(func, "notGreaterEqual", k, name, f"a scalar with value >= {_num(ge)}", f"必須 ≥ {_num(ge)}（平均 bin 寬）")
    return x


def _num_harm(func: str, n, k: int) -> int:
    """N：numeric、integer、finite、positive、scalar、> 1（validateattributes 的檢查順序）。"""
    a = np.asarray(n)
    _numeric(func, a, k, "N", "numeric")
    if np.iscomplexobj(a):
        raise _attr_error(func, "expectedInteger", k, "N", "integer-valued", "必須是整數")
    if a.size != 1:
        raise _attr_error(func, "expectedScalar", k, "N", "a scalar", "必須是純量")
    x = float(a.reshape(-1)[0])
    if not (math.isfinite(x) and x == math.floor(x)):
        raise _attr_error(func, "expectedInteger", k, "N", "integer-valued", "必須是整數")
    if not x > 0:
        raise _attr_error(func, "expectedPositive", k, "N", "positive", "必須是正數")
    if not x > 1:
        raise _attr_error(func, "notGreater", k, "N", "a scalar with value > 1", "必須大於 1")
    return int(x)


def _mean_df(F: np.ndarray) -> float:
    """MATLAB mean(diff(F))：少於 2 個 bin 是 NaN（不印 numpy 的警告）。"""
    return float(np.mean(np.diff(F))) if F.size > 1 else math.nan


_ONESIDED_MSG = {("thd", "psd"): ("signal:thd:MustBeOneSidedPxx", "Input Pxx must be a 'onesided' PSD"),
                 ("thd", "power"): ("signal:thd:MustBeOneSidedSxx", "Input Sxx must be a 'onesided' spectrum"),
                 ("snr", "psd"): ("signal:snr:MustBeOneSidedPxx", "Input Pxx must be a 'onesided' PSD."),
                 ("snr", "power"): ("signal:snr:MustBeOneSidedSxx", "Input Sxx must be a 'onesided' spectrum."),
                 ("sinad", "psd"): ("signal:sinad:MustBeOneSidedPxx", "Input Pxx must be a 'onesided' PSD"),
                 ("sinad", "power"): ("signal:sinad:MustBeOneSidedSxx", "Input Sxx must be a 'onesided' spectrum"),
                 ("toi", "psd"): ("signal:toi:MustBeOneSidedPxx", "Input Pxx must be a 'onesided' PSD"),
                 ("toi", "power"): ("signal:toi:MustBeOneSidedSxx", "Input Sxx must be a 'onesided' spectrum"),
                 ("sfdr", "psd"): ("signal:sfdr:MustBeOneSided", "Input Sxx must be a 'onesided' spectrum"),
                 ("sfdr", "power"): ("signal:sfdr:MustBeOneSided", "Input Sxx must be a 'onesided' spectrum")}


def _check_numel(func: str, F: np.ndarray, P: np.ndarray, name: str) -> None:
    if F.size != P.size:
        raise DistortionError(_ident(func, "incorrectNumel"),
                              f"Expected input number 2, F, to be an array with number of elements equal to {P.size}.",
                              f"第 2 個輸入 F 的元素數要和 {name} 一樣（{P.size}）")


def _check_increasing(func: str, F: np.ndarray) -> None:
    """validateattributes 'increasing'（snr、sinad 的 F）；訊息格式未對照 MATLAB。"""
    if F.size > 1 and not np.all(np.diff(F) > 0):
        raise _attr_error(func, "expectedIncreasing", 2, "F", "increasing", "必須嚴格遞增")


def _spectrum_inputs(func: str, pxx, f, kind, rbw, column: bool = False, positive: bool = False,
                     increasing: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray, float, str]:
    """共同的輸入檢查；回傳 (密度 Pxx, F, rbw 門檻, kind)。'power' 的 Sxx 會除以 RBW 變成密度。
    increasing＝'before'（snr：先 increasing 再 numel）／'after'（sinad：先 numel 再 increasing）／None（thd、toi、sfdr 不檢查）。"""
    kind = _check_option(func, kind, KINDS)
    name = "Pxx" if kind == "psd" else "Sxx"
    P = _vector(func, pxx, 1, name, column=column, nonneg=not positive, positive=positive)
    F = _vector(func, f, 2, "F")
    if increasing == "before":
        _check_increasing(func, F)
    _check_numel(func, F, P, name)
    if increasing == "after":
        _check_increasing(func, F)
    if not F[0] == 0:
        ident, msg = _ONESIDED_MSG[(func, kind)]
        raise DistortionError(ident, msg, f"輸入的 {name} 必須是單邊頻譜（F[0] 要是 0）")
    df = _mean_df(F)
    if kind == "power":
        if rbw is None:
            raise DistortionError("MATLAB:narginchk:notEnoughInputs", "Not enough input arguments.", "'power' 形式要給 RBW")
        r = _scalar(func, rbw, 3, "RBW", ge=df)
        return P / r, F, r, kind
    return P, F, (df if rbw is None else _scalar(func, rbw, 3, "RBW")), kind


# ----------------------------------------------------------------------------- 核心
def band_power(pxx, f) -> float:
    """MATLAB bandpower(Pxx, F, 'psd')（沒指定範圍）：矩形積分，寬度＝diff(F) 補一個平均寬度（F[0]＝0 補在尾端、否則補在前端）。單一 bin → NaN。"""
    P = np.asarray(pxx, dtype=float)
    F = np.asarray(f, dtype=float)
    m = F.size
    if m < 2:
        return math.nan
    d = np.diff(F)
    miss = (F[-1] - F[0]) / (m - 1)
    width = np.concatenate([d, [miss]]) if F[0] == 0 else np.concatenate([[miss], d])
    return float(width @ P)


def _argmax(P: np.ndarray) -> int:
    """MATLAB [~, i] = max(P)：第一個最大值，略過 NaN；全是 NaN 時是第 0 個。"""
    if np.isnan(P).any():
        return 0 if np.isnan(P).all() else int(np.nanargmax(P))
    return int(np.argmax(P))


def _skirt(P: np.ndarray, t: int) -> Tuple[int, int]:
    """從峰值 t 往左走（P[j] <= P[j+1] 就繼續）、往右走（P[j−1] >= P[j] 就繼續）的範圍 [L, R]（含）。
    分段向量化搜尋；停下來的條件寫成「比較不成立」，所以碰到 NaN 就停住。"""
    n = P.size
    L, step = 0, 32
    lo = t
    with np.errstate(invalid="ignore"):
        while lo > 0:
            a = max(0, lo - step)
            viol = np.nonzero(~(P[a:lo] <= P[a + 1:lo + 1]))[0]      # j 在 [a, lo−1]，不是 P[j] <= P[j+1]：往左的裙邊到此為止
            if viol.size:
                L = a + int(viol[-1]) + 1
                break
            lo, step = a, step * 2
        R, step = n - 1, 32
        hi = t + 1
        while hi < n:
            b = min(n, hi + step)
            viol = np.nonzero(~(P[hi - 1:b - 1] >= P[hi:b]))[0]      # j 在 [hi, b−1]，不是 P[j−1] >= P[j]：往右的裙邊到此為止
            if viol.size:
                R = hi + int(viol[0]) - 1
                break
            hi, step = b, step * 2
    return L, R


def tone(pxx, f, rbw: float, target: Optional[float] = None) -> Tone:
    """抓一根音（照 MATLAB thd／snr／sinad／sfdr 找音調的規則）：target＝None 取全域最大，否則在最接近 target 的 bin ±1 取最大；
    裙邊單調下降的 bin 全算進去；功率＝bandpower 積分（低於 rbw·峰值時改用 rbw·峰值、頻率改用峰值 bin）。
    Pxx 可以有 NaN（語意照 MATLAB：max 略過 NaN、裙邊碰到 NaN 停）；空陣列或長度不同丟 DistortionError。"""
    P = np.asarray(pxx, dtype=float).reshape(-1)
    F = np.asarray(f, dtype=float).reshape(-1)
    n = P.size
    if n == 0 or F.size != n:
        raise DistortionError("dsv:tone:EmptyInput", f"Input Pxx must be a nonempty vector with the same number of elements as F ({F.size}).",
                              f"Pxx 必須是非空向量、元素數和 F 一樣（{F.size}）")
    if target is None:
        t = _argmax(P)
    elif F[0] <= target <= F[-1]:
        t = int(np.argmin(np.abs(F - target)))
        lo, hi = max(0, t - 1), min(t + 1, n - 1)
        t = lo + _argmax(P[lo:hi + 1])
    else:
        return Tone(math.nan, math.nan, None, None, None)
    L, R = _skirt(P, t)
    S = P[L:R + 1]
    tot = float(np.sum(S))
    with np.errstate(invalid="ignore", divide="ignore"):
        freq = float(F[L:R + 1] @ S) / tot if tot != 0 else math.nan
        if L < R:
            power = band_power(S, F[L:R + 1])
        elif 0 < R < n - 1:
            power = float(P[R] * (F[R + 1] - F[R - 1]) / 2.0)
        else:
            power = float(P[R] * _mean_df(F))
        if power < rbw * P[t]:
            power = float(rbw * P[t])
            freq = float(F[t])
    return Tone(power, freq, t, L, R)


def _remove_dc(P: np.ndarray, F: np.ndarray, rbw: float) -> Tone:
    """DC 加 3 dB、以 f＝0 抓音並清成 0（就地改 P）；回傳那根音（要它的 right）。
    0 不在 [F[0], F[-1]] 裡（F 遞減時會這樣；thd／toi／sfdr 不檢查遞增）就沒有 DC 範圍可清——照 MATLAB 的 isempty 守衛跳過。"""
    P[0] *= 2.0
    dc = tone(P, F, rbw, 0.0)
    if dc.left is not None:
        P[dc.left:dc.right + 1] = 0.0
    return dc


def _alias(freq: float, fs: float) -> float:
    g = freq % fs
    return fs - g if g > fs / 2.0 else g


def _db(v) -> Any:
    with np.errstate(divide="ignore", invalid="ignore"):
        return 10.0 * np.log10(v)


def _db_ratio(a: float, b: float) -> float:
    """10·log10(a/b)，0/0 → NaN、x/0 → ±Inf（和 MATLAB 一樣，不丟 ZeroDivisionError）。"""
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(10.0 * np.log10(np.float64(a) / np.float64(b)))


def _noise_power(P: np.ndarray, orig: np.ndarray, F: np.ndarray) -> float:
    """清掉的 bin 填上剩餘 > 0 bin 的中位數、和原始值取小（NaN 中位數＝取原值），整段積分。"""
    pos = P[P > 0]
    med = float(np.median(pos)) if pos.size else math.nan
    P = P.copy()
    P[P == 0] = med
    P = np.fmin(P, orig)
    return band_power(P, F)


def _harmonic_targets(fund_freq: float, F: np.ndarray, n_harm: int, alias_fs: Optional[float]):
    """k＝2..N 的目標頻率。沒有 'aliased' 時 k·Fe1 一超過 F[-1] 之後的諧波全是 NaN（tone 會回 NaN），就不用再找了——結果相同、省時間。"""
    for k in range(2, n_harm + 1):
        tf = k * fund_freq
        if alias_fs is not None:
            yield _alias(tf, alias_fs)
        elif tf > F[-1]:
            return
        else:
            yield tf


def _thd_core(P: np.ndarray, F: np.ndarray, rbw: float, n_harm: int, alias_fs: Optional[float]) -> Tuple[float, np.ndarray, np.ndarray]:
    P = P.copy()
    _remove_dc(P, F, rbw)
    fund = tone(P, F, rbw)
    hp = np.full(n_harm, np.nan)
    hf = np.full(n_harm, np.nan)
    hp[0], hf[0] = fund.power, fund.freq
    total = 0.0
    for k, tf in enumerate(_harmonic_targets(fund.freq, F, n_harm, alias_fs), start=2):
        h = tone(P, F, rbw, tf)
        hp[k - 1], hf[k - 1] = h.power, h.freq
        if not math.isnan(h.power):
            total += h.power
    return _db_ratio(total, hp[0]), _db(hp), hf


def _snr_core(P: np.ndarray, F: np.ndarray, rbw: float, n_harm: int, alias_fs: Optional[float], harmonics: bool) -> Tuple[float, float]:
    orig = P.copy()
    P = P.copy()
    _remove_dc(P, F, rbw)
    fund = tone(P, F, rbw)
    P[fund.left:fund.right + 1] = 0.0
    if harmonics:
        for tf in _harmonic_targets(fund.freq, F, n_harm, alias_fs):
            h = tone(P, F, rbw, tf)
            if not math.isnan(h.power) and h.left is not None:
                P[h.left:h.right + 1] = 0.0
    noise = _noise_power(P, orig, F)
    return _db_ratio(fund.power, noise), float(_db(noise))


# ----------------------------------------------------------------------------- 公開：頻譜形式（照 MATLAB 的 'psd'／'power'）
def thd(pxx, f, kind: str = "psd", rbw: Optional[float] = None, n_harm: int = DEFAULT_NUM_HARMONICS,
        harm_type: str = "omitaliases", fs: Optional[float] = None) -> Tuple[float, np.ndarray, np.ndarray]:
    """MATLAB thd(Pxx,F,N,'psd'[,'aliased'])／thd(Sxx,F,RBW,N,'power'[,'aliased'])。回傳 (THD dBc, harm_pow dB[N], harm_freq[N])；
    第 0 個是基頻。fs＝'aliased' 折回用的取樣率（None → 2·F[-1]）。"""
    ht = _check_option("thd", harm_type, HARM_TYPES)
    P, F, r, kind = _spectrum_inputs("thd", pxx, f, kind, rbw)
    n = _num_harm("thd", n_harm, 4 if kind == "power" else 3)
    alias_fs = (2.0 * float(F[-1]) if fs is None else float(fs)) if ht == "aliased" else None
    return _thd_core(P, F, r, n, alias_fs)


def snr(pxx, f, kind: str = "psd", rbw: Optional[float] = None, n_harm: int = DEFAULT_NUM_HARMONICS,
        harm_type: str = "omitaliases", fs: Optional[float] = None) -> Tuple[float, float]:
    """MATLAB snr(Pxx,F,N,'psd'[,'aliased'])／snr(Sxx,F,RBW,N,'power'[,'aliased'])（F 要遞增）。回傳 (SNR dB, 雜訊功率 dB)。"""
    ht = _check_option("snr", harm_type, HARM_TYPES)
    P, F, r, kind = _spectrum_inputs("snr", pxx, f, kind, rbw, increasing="before")
    n = _num_harm("snr", n_harm, 4 if kind == "power" else 3)
    alias_fs = (2.0 * float(F[-1]) if fs is None else float(fs)) if ht == "aliased" else None
    return _snr_core(P, F, r, n, alias_fs, True)


def sinad(pxx, f, kind: str = "psd", rbw: Optional[float] = None) -> Tuple[float, float]:
    """MATLAB sinad(Pxx,F,'psd')／sinad(Sxx,F,RBW,'power')（輸入要是直的向量、F 要遞增）。回傳 (SINAD dB, 雜訊＋失真功率 dB)。"""
    P, F, r, _ = _spectrum_inputs("sinad", pxx, f, kind, rbw, column=True, increasing="after")
    return _snr_core(P, F, r, 0, None, False)


def sfdr(sxx, f, kind: str = "power", msd: Optional[float] = None, rbw: Optional[float] = None) -> Tuple[float, float, float]:
    """MATLAB sfdr(Sxx,F[,MSD],'power')（bin 值，Sxx 必須全為正）；kind＝'psd' 的算法和 sfdr(x,fs) 在週期圖之後的結果一致（積分功率，MATLAB 沒有
    公開這個形式；rbw 沒給用 mean(diff(F))）。回傳 (SFDR dB, spur 功率 dB, spur 頻率)。"""
    k = _check_option("sfdr", kind, KINDS)
    if k == "power":
        S = _vector("sfdr", sxx, 1, "Sxx", positive=True)
        F = _vector("sfdr", f, 2, "F")
        _check_numel("sfdr", F, S, "Sxx")
        if not F[0] == 0:
            ident, msg = _ONESIDED_MSG[("sfdr", "power")]
            raise DistortionError(ident, msg, "輸入的 Sxx 必須是單邊頻譜（F[0] 要是 0）")
        m = 0.0 if msd is None else _scalar("sfdr", msd, 3, "MSD")
        return _sfdr_power(S, F, m)
    P, F, r, _ = _spectrum_inputs("sfdr", sxx, f, k, rbw)
    m = 0.0 if msd is None else _scalar("sfdr", msd, 3, "MSD")
    return _sfdr_psd(P, F, r, m)


def _sfdr_psd(P: np.ndarray, F: np.ndarray, rbw: float, msd: float) -> Tuple[float, float, float]:
    P = P.copy()
    _remove_dc(P, F, rbw)
    fund = tone(P, F, rbw)
    P[fund.left:fund.right + 1] = 0.0
    with np.errstate(invalid="ignore"):
        P[np.abs(F - fund.freq) < msd] = 0.0
    sb = int(np.argmax(P))
    spur = tone(P, F, rbw, float(F[sb]))
    return _db_ratio(fund.power, spur.power), float(_db(spur.power)), spur.freq


def _sfdr_power(S: np.ndarray, F: np.ndarray, msd: float) -> Tuple[float, float, float]:
    S = S.copy()
    n = S.size
    S[0] *= 2.0
    rise = np.nonzero(S[:-1] < S[1:])[0]
    if rise.size:
        S[:int(rise[0]) + 1] = 0.0                                  # DC 單調下降的部分
    fb = int(np.argmax(S))
    fpow = float(S[fb])
    ff = float(F[fb])
    down = np.nonzero(S[1:fb + 1] < S[:fb])[0]                      # 左邊最後一個往右會下降的 bin
    left = int(down[-1]) if down.size else 0
    up = np.nonzero(S[fb + 1:] > S[fb:-1])[0]                       # 右邊第一次上升之前的 bin
    right = fb + int(up[0]) if up.size else n - 1
    lg = np.nonzero(F <= ff - msd)[0]
    rg = np.nonzero(ff + msd < F)[0]
    if lg.size and lg[-1] < left:
        left = int(lg[-1])
    if rg.size and rg[0] > right:
        right = int(rg[0])
    S[left:right + 1] = 0.0
    sb = int(np.argmax(S))
    spow = float(S[sb])
    return _db_ratio(fpow, spow), float(_db(spow)), float(F[sb])


def toi(pxx, f, kind: str = "psd", rbw: Optional[float] = None) -> Tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """MATLAB toi(Pxx,F,'psd')／toi(Sxx,F,RBW,'power')。回傳 (OIP3 dB, fund_pow dB[2], fund_freq[2], imod_pow dB[2], imod_freq[2])，
    順序 F1 < F2、IM3 依 2F1−F2、2F2−F1。"""
    P, F, r, _ = _spectrum_inputs("toi", pxx, f, kind, rbw)
    return _toi_core(P, F, r)


def _toi_core(P: np.ndarray, F: np.ndarray, rbw: float) -> Tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    P = P.copy()
    dc = _remove_dc(P, F, rbw)
    t1 = tone(P, F, rbw)
    saved = P[t1.left:t1.right + 1].copy()
    P[t1.left:t1.right + 1] = 0.0
    t2 = tone(P, F, rbw)
    P[t1.left:t1.right + 1] = saved
    if t2.freq < t1.freq:
        t1, t2 = t2, t1
    fp = np.array([t1.power, t2.power])
    ff = np.array([t1.freq, t2.freq])
    lo = tone(P, F, rbw, 2.0 * ff[0] - ff[1])
    hi = tone(P, F, rbw, 2.0 * ff[1] - ff[0])
    ip = np.array([lo.power, hi.power])
    fi = np.array([lo.freq, hi.freq])
    if dc.right is not None and (math.isnan(fi[0]) or fi[0] <= F[dc.right]):   # 下方 IM3 落在 DC 範圍裡（F2 是 F1 的二次諧波）；MATLAB 只在找到 DC 範圍時檢查
        ip[0] = fi[0] = math.nan
    fpd = _db(fp)
    ipd = _db(ip)
    carrier = (fpd[0] + fpd[1]) / 2.0
    oip3 = carrier + (carrier - (ipd[0] + ipd[1]) / 2.0) / 2.0
    return float(oip3), fpd, ff, ipd, fi


# ----------------------------------------------------------------------------- 公開：時域形式（和 MATLAB 一樣先做 Kaiser(N,38) 週期圖）
def _time_inputs(func: str, x, fs) -> Tuple[np.ndarray, float]:
    """時域形式的 X、Fs 檢查（照 MATLAB 的順序：X 在 Fs 前、N 在它們後面——由呼叫端在這之後檢查 N）。"""
    return _vector(func, x, 1, "X"), _scalar(func, fs, 2, "Fs")


def _kaiser38(v: np.ndarray, fsv: float, remove_mean: bool) -> Tuple[np.ndarray, np.ndarray, float]:
    if remove_mean:
        v = v - v.mean()
    w = np.kaiser(v.size, KAISER_BETA)
    r = dsv_spectrum.welch(v, fsv, w, 0, v.size, "onesided")
    return r["psd"], r["f"], float(r["rbw"])


def kaiser38_psd(x, fs: float = 1.0, remove_mean: bool = True, func: str = "thd") -> Tuple[np.ndarray, np.ndarray, float]:
    """thd／snr／sinad／toi（去平均值）與 sfdr（不去）時域形式用的週期圖：kaiser(N, 38)、N 點單邊 'psd'（dsv_spectrum.welch 一段）。
    回傳 (Pxx, F, rbw＝ENBW)。"""
    v, fsv = _time_inputs(func, x, fs)
    return _kaiser38(v, fsv, remove_mean)


def thd_time(x, fs: float = 1.0, n_harm: int = DEFAULT_NUM_HARMONICS, harm_type: str = "omitaliases") -> Tuple[float, np.ndarray, np.ndarray]:
    """MATLAB thd(x,Fs[,N][,'aliased'])。"""
    ht = _check_option("thd", harm_type, HARM_TYPES)
    v, fsv = _time_inputs("thd", x, fs)
    n = _num_harm("thd", n_harm, 3)
    P, F, rbw = _kaiser38(v, fsv, True)
    return _thd_core(P, F, rbw, n, fsv if ht == "aliased" else None)


def snr_time(x, fs: float = 1.0, n_harm: int = DEFAULT_NUM_HARMONICS, harm_type: str = "omitaliases") -> Tuple[float, float]:
    """MATLAB snr(x,Fs[,N][,'aliased'])。"""
    ht = _check_option("snr", harm_type, HARM_TYPES)
    v, fsv = _time_inputs("snr", x, fs)
    n = _num_harm("snr", n_harm, 3)
    P, F, rbw = _kaiser38(v, fsv, True)
    return _snr_core(P, F, rbw, n, fsv if ht == "aliased" else None, True)


def sinad_time(x, fs: float = 1.0) -> Tuple[float, float]:
    """MATLAB sinad(x,Fs)。"""
    P, F, rbw = kaiser38_psd(x, fs, True, "sinad")
    return _snr_core(P, F, rbw, 0, None, False)


def sfdr_time(x, fs: float = 1.0, msd: Optional[float] = None) -> Tuple[float, float, float]:
    """MATLAB sfdr(x,Fs[,MSD])（不去平均值）。"""
    v, fsv = _time_inputs("sfdr", x, fs)
    m = 0.0 if msd is None else _scalar("sfdr", msd, 3, "MSD")
    P, F, rbw = _kaiser38(v, fsv, False)
    return _sfdr_psd(P, F, rbw, m)


def toi_time(x, fs: float = 1.0) -> Tuple[float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """MATLAB toi(x,Fs)。"""
    P, F, rbw = kaiser38_psd(x, fs, True, "toi")
    return _toi_core(P, F, rbw)


# ----------------------------------------------------------------------------- 公開：DSV 用的包裝
def fold_onesided(f, s, mode: str = "centered") -> Tuple[np.ndarray, np.ndarray]:
    """dsv_spectrum.welch 的 centered／twosided **實數訊號**頻譜（power 或 psd 都可）→ 單邊：取 0..fs/2，DC 與 Nyquist（偶數 NFFT 才有）
    以外 ×2，和 welch(..., 'onesided') 一樣。mode＝'onesided' 原樣回傳。複數（I/Q）訊號的負頻率不是鏡像，不能這樣折——不支援，呼叫端要自己擋。"""
    F = np.asarray(f, dtype=float)
    S = np.asarray(s, dtype=float)
    n = F.size
    if mode == "onesided" or n == 0:
        return F, S
    if mode == "centered":
        k0 = n // 2 - 1 if n % 2 == 0 else (n - 1) // 2               # dsv_spectrum.freq_grid 的 DC 位置
        if F[k0] != 0:
            raise DistortionError("dsv:fold_onesided:NoDC", "Centered spectrum has no 0 Hz bin.", "置中頻譜裡找不到 0 Hz 的 bin")
        F1, S1 = F[k0:].copy(), S[..., k0:].copy()
    elif mode == "twosided":
        h = n // 2 + 1
        F1, S1 = F[:h].copy(), S[..., :h].copy()
    else:
        raise DistortionError("dsv:fold_onesided:UnknownMode", f"Unknown mode: '{mode}'", f"不認得的 mode '{mode}'")
    h = F1.size
    hi = h - 1 if n % 2 == 0 else h
    S1[..., 1:hi] *= 2.0
    return F1, S1


def _panel_num_harm(n) -> Any:
    """Spectrum Analyzer 的 Num Harmonics 欄位檢查（MATLAB 工具列欄位：取開頭的數字，看不懂、< 2、> 99 都是錯；非整數放過、由 thd 擋）。"""
    a = np.asarray(n)
    ok = a.dtype.kind in "iuf" and a.size == 1
    if ok:
        v = float(a.reshape(-1)[0])
        ok = math.isfinite(v) and 2 <= v <= MAX_PANEL_HARMONICS
    if not ok:
        raise DistortionError("dsv:harmonic_distortion:invalidNumHarmonics",
                              f"Enter number of harmonics as a finite positive real scalar between 2 and {MAX_PANEL_HARMONICS}.",
                              f"以 2 到 {MAX_PANEL_HARMONICS} 之間的有限正實數純量形式輸入諧波的數目。")
    return n


def harmonic_distortion(sxx, f, rbw: float, n_harm: int = DEFAULT_NUM_HARMONICS, aliased: bool = False) -> Dict[str, Any]:
    """諧波失真面板：單邊功率頻譜（welch 的 power、f、rbw）→ thd／snr／sinad／sfdr 的 'power' 形式。n_harm 限 2..99（Spectrum Analyzer 的
    Num Harmonics 檢查）。回傳 dict：thd（dBc）、thd_pct（%）、snr、sinad、sfdr（dB）、noise_pow、spur_pow（dB）、spur_freq、
    harm_freq[N]、harm_pow[N]（dB，輸入單位²）、harm_rel[N]（dBc，H1＝0）。輸入不合（例如空頻譜、有 0 的 bin：sfdr 要全為正）會丟 DistortionError。"""
    ht = "aliased" if aliased else "omitaliases"
    n_harm = _panel_num_harm(n_harm)
    r_thd, hp, hf = thd(sxx, f, "power", rbw, n_harm, ht)
    r_snr, npow = snr(sxx, f, "power", rbw, n_harm, ht)
    r_sinad, _ = sinad(sxx, f, "power", rbw)
    r_sfdr, spow, sfreq = sfdr(sxx, f, "power")
    with np.errstate(invalid="ignore"):                             # 基頻功率 0（hp[0]＝−Inf）時 −Inf−(−Inf) 是 NaN，不印警告
        rel = hp - hp[0]
    return {"thd": r_thd, "thd_pct": 100.0 * 10.0 ** (r_thd / 20.0), "snr": r_snr, "sinad": r_sinad, "sfdr": r_sfdr,
            "noise_pow": npow, "spur_pow": spow, "spur_freq": sfreq, "harm_freq": hf, "harm_pow": hp, "harm_rel": rel}


def intermod_distortion(sxx, f, rbw: float) -> Dict[str, Any]:
    """互調失真面板：單邊功率頻譜 → toi 的 'power' 形式。回傳 dict：f1、f2、p1、p2（dB）、im_freq[2]（2F1−F2、2F2−F1）、im_pow[2]（dB）、
    im_rel[2]（dBc：相對 F1、F2）、toi（OIP3 dB）、toi_lower／toi_upper（spectrumAnalyzer 文件的兩個 TOI，平均＝toi）。"""
    oip3, fp, ff, ip, fi = toi(sxx, f, "power", rbw)
    lower = fp[0] + (fp[1] - ip[0]) / 2.0
    upper = fp[1] + (fp[0] - ip[1]) / 2.0
    return {"f1": float(ff[0]), "f2": float(ff[1]), "p1": float(fp[0]), "p2": float(fp[1]), "im_freq": fi, "im_pow": ip,
            "im_rel": ip - fp, "toi": oip3, "toi_lower": float(lower), "toi_upper": float(upper)}


# ----------------------------------------------------------------------------- 公開：Spectrum Analyzer 本體（scope）的失真演算法
# 2026-10-24 開 MATLAB R2025a 的 spectrumAnalyzer 實測 20 個 capture 解出的規則（scope_capture/ANALYSIS.md §4、rules.json D1–D11；
# 數據在 tests/matlab_ref/scope/distortion/）。DSV 頻譜視窗顯示的失真數字走這一組；上面的 thd／snr／sinad／sfdr／toi 函式路徑是次要的。
# 做法（用自己的話；工作頻譜 P＝f ≥ 0 半邊的每 bin 功率，W）：
#   DC   從 bin 0 往右走、只要不升就繼續，走到的 [0, R0] 清成 0，W0＝(R0+1)·df。
#   基頻 t1＝剩下的最大 bin；從 t1 往左／往右走單調不升的裙邊得 [L, R]；Fe1＝這段的功率重心（只拿來瞄準）；P1＝P[t1]（峰值 bin 值，不是
#        積分）；W1＝(R−L+1)·df；清掉 [L, R]；報的頻率是 bin 中心 f[t1]。
#   諧波 k＝2..N：目標 bin＝round(k·Fe1/df)，超過最後一個 bin 就停（這列和之後的都不列、不折回、不加寬度）；否則在目標 ±1 bin 裡取最大的
#        bin（已經清成 0 的也算），從它走裙邊（0 的區域也照走、寬度照算），P_k＝那個 bin 的值（0 → −Inf dB），清掉。
#   剩下 P_rem＝Σ剩餘 bin、P_maxspur＝剩餘最大 bin、P_est＝剩餘非 0 bin 的中位數；Wsum＝W0+W1+…+Wn；
#   Pnoise＝(P_rem·df + P_est·Wsum)/RBW；THD＝ΣP_k/P1、THD%＝100·10^(THD/20)、SNR＝P1/Pnoise、SINAD＝P1/(ΣP_k+Pnoise)、
#   SFDR＝P1/max(P_maxspur, max P_k)。
#   互調 清 DC；F1＝最強的音、F2＝次強（同上抓法、清掉）；三階積在 2·Fe1−Fe2（第 3 列）與 2·Fe2−Fe1（第 4 列），±1 bin 窗、峰值 bin 值；
#        TOI_lower＝P_F1+(P_F2−P_2F1−F2)/2、TOI_upper＝P_F2+(P_F1−P_2F2−F1)/2、TOI＝平均（dB）；積 < 0 Hz → 功率 0（−Inf）、TOI +Inf。
SCOPE_HALF_WINDOW = 1            # 諧波／互調積的搜尋窗：目標 bin ±1（D4、D7）
SCOPE_LEAKAGE_LIMIT = 0.70       # 文件：leakage 佔頻寬超過 70 % 時 SNR／SINAD 顯示「–」；沒有 capture 觸發過 → 只回旗標 leakage_blank
SCOPE_MAX_BINS = 1 << 24         # DSV 自訂保護：trace 超過 2^24 個 bin 直接丟錯（不配置、不搜尋）
SCOPE_MODES = ("onesided", "centered", "twosided")
SCOPE_IMOD_LABELS = ("F1", "F2", "2F1-F2", "2F2-F1")


def _round_half_up(x: float) -> int:
    """0.5 進位的四捨五入（C／MATLAB 的 round 是半數離零；numpy 的 round 是半數取偶，不一樣）。目標 bin 是正的，floor(x+0.5) 就是。"""
    return int(math.floor(x + 0.5))


def _scope_mode(func: str, F: np.ndarray, mode: Optional[str]) -> str:
    """頻譜排列：None → 有負頻率就是 centered、否則 onesided；指定的要是 SCOPE_MODES 之一。"""
    if mode is None:
        return "centered" if bool(np.any(F < 0)) else "onesided"
    m = str(mode).strip().lower()
    if m not in SCOPE_MODES:
        raise DistortionError(_ident(func, "unknownMode"), f"Unknown spectrum mode '{mode}'. Expected onesided, centered or twosided.",
                              f"不認得的頻譜排列 '{mode}'（要是 onesided、centered 或 twosided）")
    return m


def _scope_inputs(func: str, trace, f, rbw, kind, mode) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, float, str, str]:
    """scope 量測共同的輸入檢查與前處理：trace（顯示的線性值：'power' W/bin、'psd' W/Hz；不能是 dB）、F、RBW → 取 f ≥ 0 的半邊（照顯示值，
    不加倍：D1），'psd' 乘 RBW 變成每 bin 功率當工作頻譜。回傳 (T 顯示值, P 工作用功率, F, df, rbw, kind, mode)。"""
    kind = _check_option(func, kind, KINDS)
    name = "Pxx" if kind == "psd" else "Sxx"
    nbins = np.asarray(trace).size
    if nbins > SCOPE_MAX_BINS:                                      # 先擋大小，之後才會複製／檢查整個陣列
        raise DistortionError(_ident(func, "tooManyBins"), f"Spectrum has {nbins} bins; at most {SCOPE_MAX_BINS} are supported.",
                              f"頻譜有 {nbins} 個 bin，超過上限 {SCOPE_MAX_BINS}（DSV 的保護）")
    T = _vector(func, trace, 1, name, nonneg=True)
    F = _vector(func, f, 2, "F")
    _check_numel(func, F, T, name)
    r = _scalar(func, rbw, 3, "RBW")
    mode = _scope_mode(func, F, mode)
    if mode == "centered":
        keep = F >= 0
        T, F = T[keep], F[keep]
    elif mode == "twosided":                                        # 0..fs(1−1/N)：前 N//2+1 個 bin 就是 0..fs/2（奇數 N 到 (N−1)/2）
        h = F.size // 2 + 1
        T, F = T[:h], F[:h]
    if F.size < 2:
        raise DistortionError(_ident(func, "tooFewBins"), "Spectrum must have at least 2 bins at f >= 0.", "頻譜在 f ≥ 0 至少要有 2 個 bin")
    if not np.all(np.diff(F) > 0):
        raise _attr_error(func, "expectedIncreasing", 2, "F", "increasing", "必須嚴格遞增")
    df = float((F[-1] - F[0]) / (F.size - 1))
    P = T * r if kind == "psd" else T.copy()
    return T, P, F, df, r, kind, mode


def _scope_num_harm(func: str, n) -> int:
    """Num Harmonics（含基頻）：有限整數 2..99（Spectrum Analyzer 欄位的範圍；DistortionMeasurementsConfiguration 要 positive integer，非整數也拒絕）。"""
    a = np.asarray(n)
    ok = a.dtype.kind in "iuf" and a.size == 1
    if ok:
        v = float(a.reshape(-1)[0])
        ok = math.isfinite(v) and v == math.floor(v) and 2 <= v <= MAX_PANEL_HARMONICS
    if not ok:
        raise DistortionError(_ident(func, "invalidNumHarmonics"),
                              f"Enter number of harmonics as a finite positive real scalar between 2 and {MAX_PANEL_HARMONICS}.",
                              f"以 2 到 {MAX_PANEL_HARMONICS} 之間的有限正實數純量形式輸入諧波的數目。")
    return int(float(a.reshape(-1)[0]))


def _scope_clear_dc(P: np.ndarray, df: float) -> Tuple[float, int]:
    """D2：從 bin 0 往右走、只要不升就繼續，[0, R0] 清成 0（就地改 P）；回傳 (W0＝(R0+1)·df, R0)。"""
    r0 = _skirt(P, 0)[1]
    P[:r0 + 1] = 0.0
    return (r0 + 1) * df, r0


def _scope_centroid(P: np.ndarray, F: np.ndarray, L: int, R: int, t: int) -> float:
    """功率加權的重心頻率 Σ(F·P)/ΣP（只拿來瞄準諧波／互調積）；整段是 0 時退回峰值 bin 的頻率。"""
    seg = P[L:R + 1]
    s = float(seg.sum())
    return float(F[L:R + 1] @ seg) / s if s > 0 else float(F[t])


def _scope_take(P: np.ndarray, F: np.ndarray, df: float, t: int) -> Dict[str, Any]:
    """以 t 為峰值抓一根音（D3／D4）：單調不升的裙邊 [L, R]、重心、峰值 bin 值、寬度；把 [L, R] 清成 0（就地改 P）。"""
    L, R = _skirt(P, t)
    tone = {"idx": t, "freq": float(F[t]), "centroid": _scope_centroid(P, F, L, R, t), "peak": float(P[t]),
            "width": (R - L + 1) * df, "left": L, "right": R}
    P[L:R + 1] = 0.0
    return tone


def _scope_search(P: np.ndarray, F: np.ndarray, df: float, target: float) -> Optional[Dict[str, Any]]:
    """在 round(target/df) ± SCOPE_HALF_WINDOW 的窗裡取最大的 bin（清成 0 的也算；同值取第一個），再從它抓音。
    目標 bin 超過最後一個 bin、或 target 低於第一個 bin（互調積 < 0 Hz）→ None（這一列不存在）。"""
    n = P.size
    tb = _round_half_up((target - F[0]) / df)
    if target < F[0] or tb > n - 1 or tb < 0:
        return None
    lo, hi = max(tb - SCOPE_HALF_WINDOW, 0), min(tb + SCOPE_HALF_WINDOW, n - 1)
    return _scope_take(P, F, df, lo + int(np.argmax(P[lo:hi + 1])))


def _scope_values(T: np.ndarray, rows: Sequence[Dict[str, Any]]) -> np.ndarray:
    """報表的功率列＝峰值 bin 的顯示值（'power' W/bin、'psd' W/Hz：D11）；清成 0 的 bin（或不存在的列）是 0。"""
    return np.array([float(T[h["idx"]]) if h["idx"] is not None and h["peak"] > 0 else 0.0 for h in rows])


def scope_harmonic(trace, f, rbw: float, n_harm: int = DEFAULT_NUM_HARMONICS, kind: str = "power", mode: Optional[str] = None) -> Dict[str, Any]:
    """Spectrum Analyzer 本體的 Harmonic Distortion（規則 D1–D6、D8–D11）。
    trace＝顯示的線性頻譜：dsv_spectrum.welch 的 power（kind='power'，W/bin）或 psd（kind='psd'，W/Hz），單邊、或 centered 兩邊
    （取 f ≥ 0 的半邊照顯示值用，所以兩邊顯示的絕對功率比單邊低 3.01 dB——和 scope 一樣；複數訊號照算）；f＝頻率格；rbw＝視窗的 RBW（ENBW）；
    n_harm＝Num Harmonics（含基頻，2..99）；mode＝None 自動（有負頻率＝centered）或 'onesided'／'centered'／'twosided'。Max-Hold 開著時
    scope 用的是 normal trace（D9），呼叫端傳 normal trace。
    回傳 dict：harmonic_number[m]、freq[m]（峰值 bin 的中心頻率）、power[m]（峰值 bin 的顯示值；清掉的 bin 是 0）、power_db[m]（10·log10，
    0 → −Inf；dBm＝+30）、rel_db[m]（dBc，H1＝0）、thd、snr、sinad、sfdr（dB）、thd_pct（%）、noise_power（Pnoise，W）、spur_power／spur_freq
    （清完剩下的最大 bin）、fund_centroid（Fe1）、widths[m+1]（W0、W1..Wm，Hz）、wsum、leakage_fraction（Wsum/半邊頻寬）、leakage_blank
    （> 70 %：文件說 SNR／SINAD 要顯示「–」）、n_requested、n_found（m；超過 Nyquist 的諧波不列）、df、rbw、kind、mode。"""
    func = "dsv:scope_harmonic"
    n = _scope_num_harm(func, n_harm)
    T, P, F, df, r, kind, mode = _scope_inputs(func, trace, f, rbw, kind, mode)
    nb = P.size
    w0, _ = _scope_clear_dc(P, df)
    fund = _scope_take(P, F, df, int(np.argmax(P)))
    rows = [fund]
    for k in range(2, n + 1):
        h = _scope_search(P, F, df, k * fund["centroid"])
        if h is None:
            break
        rows.append(h)
    p1 = fund["peak"]
    pk = np.array([h["peak"] for h in rows[1:]])
    p_harm = float(pk.sum())
    nz = P[P > 0]
    p_est = float(np.median(nz)) if nz.size else 0.0
    spur_idx = int(np.argmax(P))
    p_spur = float(P[spur_idx])
    widths = np.array([w0] + [h["width"] for h in rows])
    wsum = float(widths.sum())
    p_noise = (float(P.sum()) * df + p_est * wsum) / r
    thd = _db_ratio(p_harm, p1)
    vals = _scope_values(T, rows)
    pdb = _db(vals)
    with np.errstate(invalid="ignore"):
        rel = pdb - pdb[0]
    frac = wsum / (nb * df)
    return {"harmonic_number": np.arange(1, len(rows) + 1), "freq": np.array([h["freq"] for h in rows]), "power": vals, "power_db": pdb,
            "rel_db": rel, "thd": thd, "thd_pct": 100.0 * 10.0 ** (thd / 20.0), "snr": _db_ratio(p1, p_noise),
            "sinad": _db_ratio(p1, p_harm + p_noise), "sfdr": _db_ratio(p1, max(p_spur, float(pk.max()) if pk.size else 0.0)),
            "noise_power": p_noise, "spur_power": p_spur, "spur_freq": float(F[spur_idx]), "fund_centroid": fund["centroid"],
            "widths": widths, "wsum": wsum, "leakage_fraction": frac, "leakage_blank": bool(frac > SCOPE_LEAKAGE_LIMIT),
            "n_requested": n, "n_found": len(rows), "df": df, "rbw": r, "kind": kind, "mode": mode}


def scope_intermod(trace, f, rbw: float, kind: str = "power", mode: Optional[str] = None) -> Dict[str, Any]:
    """Spectrum Analyzer 本體的 Intermodulation Distortion（規則 D1、D2、D7）：清 DC；F1＝最強的音、F2＝次強（各自裙邊、重心、峰值 bin 值、
    清掉）；三階積在 2·Fe1−Fe2（第 3 列）與 2·Fe2−Fe1（第 4 列），用重心瞄準、±1 bin 窗、峰值 bin 值。
    TOI_lower＝P_F1+(P_F2−P_2F1−F2)/2、TOI_upper＝P_F2+(P_F1−P_2F2−F1)/2、TOI＝兩者平均（dB）。積 < 0 Hz（或超過 Nyquist）→ 不存在：
    power 0（−Inf dB）、freq NaN、TOI +Inf。輸入和 scope_harmonic 一樣。
    回傳 dict：labels、freq[4]、power[4]、power_db[4]、rel_db[4]（相對 F1）、toi、toi_lower、toi_upper（dB，trace 單位；dBm＝+30）、toi_linear、
    centroid[2]（Fe1、Fe2）、targets[2]（2Fe1−Fe2、2Fe2−Fe1）、df、rbw、kind、mode。"""
    func = "dsv:scope_intermod"
    T, P, F, df, r, kind, mode = _scope_inputs(func, trace, f, rbw, kind, mode)
    _scope_clear_dc(P, df)
    a = _scope_take(P, F, df, int(np.argmax(P)))
    b = _scope_take(P, F, df, int(np.argmax(P)))
    targets = (2.0 * a["centroid"] - b["centroid"], 2.0 * b["centroid"] - a["centroid"])
    rows = [a, b]
    for tg in targets:
        h = _scope_search(P, F, df, tg)
        rows.append(h if h is not None else {"idx": None, "freq": math.nan, "peak": 0.0})
    vals = _scope_values(T, rows)
    pdb = _db(vals)
    with np.errstate(invalid="ignore"):
        lower = float(pdb[0] + (pdb[1] - pdb[2]) / 2.0)
        upper = float(pdb[1] + (pdb[0] - pdb[3]) / 2.0)
        toi = (lower + upper) / 2.0
        rel = pdb - pdb[0]
    return {"labels": SCOPE_IMOD_LABELS, "freq": np.array([h["freq"] for h in rows]), "power": vals, "power_db": pdb, "rel_db": rel,
            "toi": toi, "toi_lower": lower, "toi_upper": upper, "toi_linear": float(10.0 ** (toi / 10.0)),
            "centroid": np.array([a["centroid"], b["centroid"]]), "targets": np.array(targets), "df": df, "rbw": r, "kind": kind, "mode": mode}


# ----------------------------------------------------------------------------- selftest
def selftest(check, ref_dir: str) -> None:
    """拿 MATLAB R2025a 算的參考值逐筆比對（tests/matlab_ref/distortion/distortion_ref.json 與 inputs；研究用的 distortion_ref.m 產生）。
    容差見下面的常數與模組 docstring 的「selftest 的容差」。"""
    import json
    import os
    import time as _time
    import warnings
    d = os.path.join(ref_dir, "distortion")
    path = os.path.join(d, "distortion_ref.json")
    if not os.path.isfile(path):
        check(True, "（沒有 tests/matlab_ref/distortion：略過 MATLAB 失真量測比對）")
        return
    with open(path, encoding="utf-8") as fh:
        R = json.load(fh)
    RTOL_ALG = 1e-12    # 餵 MATLAB 自己的頻譜（純演算法）與時域形式（經 numpy FFT，仍到 1e-12）：全部 1379 個非捨入底的值都過
    RTOL_FFT = 1e-9     # 面板路徑 x → dsv_spectrum.welch → harmonic_distortion／intermod_distortion（numpy 的 Welch；觀測最大相對差 6.8e-10）
    ATOL_DB = 1e-9      # 面板路徑的 dB 值另加 1e-9 dB：h_noiseless 的 SNR 是 −4.28e-6 dB（絕對差 2.9e-15 dB），接近 0 的 dB 值相對差沒意義
    BIN_ATOL = 1e-14    # 頻譜 bin：|Δ| ≤ RTOL_ALG·|ref| + 1e-14·峰值（FFT 捨入：觀測 |Δ|/峰值 ≤ 8.1e-16；底部的 bin 相對差本來就 > 1e-12）
    ABS_FLOOR = 1e-12   # 所有比對再加的絕對底：接近 0 的 dB 值（h_noiseless 的 SNR −4.28e-6 dB）相對差沒意義——numpy 2.4 絕對差 2.9e-15、
    #                     numpy 1.26（pocketfft）1.9e-15 dB，相對卻到 4.5e-10；dB／Hz 的參考值都 ≫ 1e-12，所以這個底對其他值沒有影響
    ROFF_DBC = -250.0   # 低於基頻 250 dB 的值是 FFT 捨入底（h_noiseless 第 4 個以後的諧波 −305 dB、雜訊底 −280 dB）：MATLAB 與 numpy 的 FFT 捨入不同
    ROFF_DB_TOL = 10.0  # 捨入底的 dB 值只檢查同為底：相差 ≤ 10 dB（觀測 ≤ 0.65 dB）
    ROFF_BINS = 2.0     # 捨入底諧波的重心頻率：相差 ≤ 2 個 bin（觀測 ≤ 1 bin：在 ±1 bin 的搜尋窗裡選到不同的捨入峰）
    stats = {"n": 0, "ok": 0, "roff": 0, "roff_ok": 0}

    def vec(rel: str) -> np.ndarray:
        return np.loadtxt(os.path.join(d, os.path.basename(rel)))

    def arr(v) -> np.ndarray:
        v = v if isinstance(v, list) else [v]
        return np.asarray([np.nan if x is None else x for x in v], dtype=float)

    def cmp(bad: list, label: str, got, ref, rtol: float = RTOL_ALG, atol: float = 0.0, count: bool = True, roff=None) -> None:
        """每個值 |我−MATLAB| ≤ rtol·|MATLAB| + atol（NaN 要同位置、±Inf 要相等）。roff＝(mask, 'db'|'freq', df)：mask 為 True 的值是
        FFT 捨入底，改成寬鬆檢查（dB 相差 ≤ ROFF_DB_TOL、頻率相差 ≤ ROFF_BINS·df）並另外計數。count＝False 是診斷用的重複比對，不計入。"""
        g = np.atleast_1d(np.asarray(got, dtype=float)).reshape(-1)
        r = arr(ref).reshape(-1)
        if g.size != r.size:
            if count:
                stats["n"] += r.size
            bad.append(f"{label}: 長度 {g.size} ≠ {r.size}")
            return
        mask = np.zeros(r.size, dtype=bool) if roff is None else np.asarray(roff[0], dtype=bool).reshape(-1)
        nan_ok = np.isnan(g) == np.isnan(r)
        both = ~np.isnan(g) & ~np.isnan(r)
        with np.errstate(invalid="ignore"):
            fin = both & np.isfinite(r)
            ok = nan_ok & (~both | (np.isinf(r) & (g == r)) | (fin & (np.abs(g - r) <= rtol * np.abs(r) + max(atol, ABS_FLOOR))))
            if mask.any():
                lim = ROFF_DB_TOL if roff[1] == "db" else ROFF_BINS * roff[2]
                ok = np.where(mask, nan_ok & (~both | (np.abs(g - r) <= lim)), ok)
        if count:
            stats["n"] += int((~mask).sum())
            stats["ok"] += int((ok & ~mask).sum())
            stats["roff"] += int(mask.sum())
            stats["roff_ok"] += int((ok & mask).sum())
        if not ok.all():
            i = int(np.nonzero(~ok)[0][0])
            with np.errstate(invalid="ignore", divide="ignore"):
                rel = abs(g[i] - r[i]) / abs(r[i]) if r[i] != 0 else math.inf
            bad.append(f"{label}[{i}] 我={float(g[i])!r} MATLAB={float(r[i])!r} rel={rel:.2e}（{int((~ok).sum())} 個不合）")

    def bins_ok(got: np.ndarray, ref: np.ndarray) -> Tuple[bool, str]:
        """頻譜 bin 逐個比：|Δ| ≤ RTOL_ALG·|ref| + BIN_ATOL·峰值。回傳 (ok, 說明)。"""
        if got.size != ref.size:
            return False, f"長度 {got.size} ≠ {ref.size}"
        dv = np.abs(got - ref)
        peak = float(ref.max())
        ok = dv <= RTOL_ALG * np.abs(ref) + BIN_ATOL * peak
        worst = float(dv.max() / peak)
        if ok.all():
            return True, f"最大 |Δ|/峰值 {worst:.1e}"
        i = int(np.nonzero(~ok)[0][0])
        return False, f"{int((~ok).sum())} 個 bin 超過，第一個 [{i}] 我={float(got[i])!r} MATLAB={float(ref[i])!r}，最大 |Δ|/峰值 {worst:.1e}"

    def same(a, b) -> bool:
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        return a.shape == b.shape and bool(np.all((a == b) | (np.isnan(a) & np.isnan(b))))

    def report(bad: list, msg: str) -> None:
        check(not bad, msg + (f"（不一致：{'; '.join(bad[:4])}{'…' if len(bad) > 4 else ''}）" if bad else ""))

    # ---------------- 諧波案例 ----------------
    for s in R["harmonic"]:
        nm, fs, f0 = s["name"], float(s["fs"]), float(s["f0"])
        x = vec(s["x_file"])
        N = x.size
        Pm, Fm, Sm = vec(s["Pxx_file"]), vec(s["F_file"]), vec(s["Sxx_file"])
        rb = float(s["kaiser_enbw_rbw"])
        df_m = float(np.mean(np.diff(Fm)))
        floor_db = float(s["thd_time_default"]["harmPow"][0]) + ROFF_DBC           # 基頻（MATLAB）往下 250 dB：以下是 FFT 捨入底
        # (a) 週期圖重現：kaiser 視窗、ENBW、F、Pxx（全部 bin）
        wm = vec(f"inputs/{nm}_kaiser38_w.txt")
        P, F, rbw = kaiser38_psd(x, fs)
        Pw, _, _ = kaiser38_psd(x, fs, remove_mean=False)
        okb, info = bins_ok(P, Pm)
        okw = np.allclose(np.kaiser(N, KAISER_BETA), wm, rtol=1e-12, atol=0) and math.isclose(rbw, rb, rel_tol=1e-12) and np.array_equal(F, Fm)
        check(okw and okb, f"週期圖 vs MATLAB periodogram（{nm}：N＝{N}、kaiser(N,38) rtol 1e-12、ENBW、F 全等、Pxx 全部 {P.size} 個 bin "
                           f"|Δ| ≤ 1e-12·|ref| + 1e-14·峰值；{info}）")
        # (b) 時域形式（用 dsv_spectrum 算的週期圖）；h_noiseless 低於基頻 250 dB 的諧波／雜訊底是 FFT 捨入底，寬鬆檢查、另外計數
        bad: list = []
        n_roff = 0
        for tag, nh, ht in (("thd_time_default", 6, "omitaliases"), ("thd_time_N2", 2, "omitaliases"), ("thd_time_N6", 6, "omitaliases"),
                            ("thd_time_N10", 10, "omitaliases"), ("thd_time_aliased", 6, "aliased")):
            r, hp, hf = thd_time(x, fs, nh, ht)
            with np.errstate(invalid="ignore"):
                m = arr(s[tag]["harmPow"]) < floor_db
            n_roff += 2 * int(m.sum())                                          # harmPow 與 harmFreq 各一個
            cmp(bad, tag + ".r", r, s[tag]["r"])
            cmp(bad, tag + ".harmPow", hp, s[tag]["harmPow"], roff=(m, "db", df_m))
            cmp(bad, tag + ".harmFreq", hf, s[tag]["harmFreq"], roff=(m, "freq", df_m))
        for tag, nh, ht in (("snr_time_N2", 2, "omitaliases"), ("snr_time_N6", 6, "omitaliases"), ("snr_time_N10", 10, "omitaliases"),
                            ("snr_time_aliased", 6, "aliased"), ("snr_time_default", 6, "omitaliases")):
            m = np.array([s[tag]["noisePow"] < floor_db] * 2)
            n_roff += int(m.sum())
            cmp(bad, tag, snr_time(x, fs, nh, ht), [s[tag]["r"], s[tag]["noisePow"]], roff=(m, "db", df_m))
        cmp(bad, "sinad_time", sinad_time(x, fs), [s["sinad_time"]["r"], s["sinad_time"]["totDistPow"]])
        cmp(bad, "sfdr_time", sfdr_time(x, fs), [s["sfdr_time"]["r"], s["sfdr_time"]["spurPow"], s["sfdr_time"]["spurFreq"]])
        cmp(bad, "sfdr_time_msd", sfdr_time(x, fs, s["sfdr_time_msd"]["msd"]),
            [s["sfdr_time_msd"]["r"], s["sfdr_time_msd"]["spurPow"], s["sfdr_time_msd"]["spurFreq"]])
        report(bad, f"時域形式 vs MATLAB（{nm}，用 dsv_spectrum 的週期圖）：thd 預設／N＝2、6、10／aliased 的 THD、harmPow、harmFreq，"
                    f"snr N＝2、6、10／aliased／預設，sinad，sfdr 無／有 MSD 逐值 rtol 1e-12 一致"
                    + (f"；其中 {n_roff} 個值在 FFT 捨入底（< 基頻 −250 dB）只檢查同為底（±10 dB、2 bin）" if n_roff else ""))
        # (c) 同樣的演算法餵 MATLAB 自己的 Pxx（排除 FFT 差異、單純驗演算法）
        bad = []
        for tag, nh, ht in (("thd_time_default", 6, None), ("thd_time_N2", 2, None), ("thd_time_N6", 6, None), ("thd_time_N10", 10, None),
                            ("thd_time_aliased", 6, "aliased")):
            r, hp, hf = thd(Pm, Fm, "psd", rbw=rb, n_harm=nh, harm_type=ht or "omitaliases", fs=fs)
            cmp(bad, tag + ".r", r, s[tag]["r"], count=False)
            cmp(bad, tag + ".harmPow", hp, s[tag]["harmPow"], count=False)
            cmp(bad, tag + ".harmFreq", hf, s[tag]["harmFreq"], count=False)
        for tag, nh, ht in (("snr_time_N2", 2, None), ("snr_time_N6", 6, None), ("snr_time_N10", 10, None), ("snr_time_aliased", 6, "aliased"),
                            ("snr_time_default", 6, None)):
            cmp(bad, tag, snr(Pm, Fm, "psd", rbw=rb, n_harm=nh, harm_type=ht or "omitaliases", fs=fs), [s[tag]["r"], s[tag]["noisePow"]], count=False)
        cmp(bad, "sinad_time", sinad(Pm, Fm, "psd", rbw=rb), [s["sinad_time"]["r"], s["sinad_time"]["totDistPow"]], count=False)
        cmp(bad, "sfdr_time", sfdr(Pw, F, "psd", rbw=rbw), [s["sfdr_time"]["r"], s["sfdr_time"]["spurPow"], s["sfdr_time"]["spurFreq"]], count=False)
        report(bad, f"時域演算法 vs MATLAB（{nm}，餵 MATLAB 自己的 Pxx 與 ENBW；診斷用、不計入總數）：同上各組逐值 rtol 1e-12 一致"
                    f"（含 h_noiseless 的捨入底諧波——演算法本身位元級一致；sfdr 不去平均值的週期圖用 dsv_spectrum）")
        # (d) 'psd' 形式
        bad = []
        for tag, kw in (("thd_psd", {}), ("thd_psd_N3", {"n_harm": 3}), ("thd_psd_aliased", {"harm_type": "aliased"})):
            r, hp, hf = thd(Pm, Fm, "psd", **kw)
            cmp(bad, tag + ".r", r, s[tag]["r"])
            cmp(bad, tag + ".harmPow", hp, s[tag]["harmPow"])
            cmp(bad, tag + ".harmFreq", hf, s[tag]["harmFreq"])
        cmp(bad, "snr_psd", snr(Pm, Fm, "psd"), [s["snr_psd"]["r"], s["snr_psd"]["noisePow"]])
        cmp(bad, "snr_psd_N3", snr(Pm, Fm, "psd", n_harm=3), [s["snr_psd_N3"]["r"], s["snr_psd_N3"]["noisePow"]])
        cmp(bad, "sinad_psd", sinad(Pm, Fm, "psd"), [s["sinad_psd"]["r"], s["sinad_psd"]["totDistPow"]])
        report(bad, f"'psd' 形式 vs MATLAB（{nm}）：thd 預設／N＝3／aliased（fs＝2·F[-1]）、snr 預設／N＝3、sinad 逐值 rtol 1e-12 一致")
        # (e) 'power' 形式
        bad = []
        for tag, kw in (("thd_power", {}), ("thd_power_N3", {"n_harm": 3})):
            r, hp, hf = thd(Sm, Fm, "power", rb, **kw)
            cmp(bad, tag + ".r", r, s[tag]["r"])
            cmp(bad, tag + ".harmPow", hp, s[tag]["harmPow"])
            cmp(bad, tag + ".harmFreq", hf, s[tag]["harmFreq"])
        cmp(bad, "snr_power", snr(Sm, Fm, "power", rb), [s["snr_power"]["r"], s["snr_power"]["noisePow"]])
        cmp(bad, "snr_power_N3", snr(Sm, Fm, "power", rb, n_harm=3), [s["snr_power_N3"]["r"], s["snr_power_N3"]["noisePow"]])
        cmp(bad, "sinad_power", sinad(Sm, Fm, "power", rb), [s["sinad_power"]["r"], s["sinad_power"]["totDistPow"]])
        cmp(bad, "sfdr_power", sfdr(Sm, Fm, "power"), [s["sfdr_power"]["r"], s["sfdr_power"]["spurPow"], s["sfdr_power"]["spurFreq"]])
        cmp(bad, "sfdr_power_msd", sfdr(Sm, Fm, "power", msd=3 * f0 / 2),
            [s["sfdr_power_msd"]["r"], s["sfdr_power_msd"]["spurPow"], s["sfdr_power_msd"]["spurFreq"]])
        report(bad, f"'power' 形式 vs MATLAB（{nm}）：thd 預設／N＝3、snr 預設／N＝3、sinad、sfdr 無／有 MSD（bin 值演算法）逐值 rtol 1e-12 一致")
        # (f) Hann Welch（scope 式的有 leakage 頻譜）：餵 MATLAB 的 pwelch 結果
        h = s["hannwelch"]
        Sw, Fw, rh = vec(h["Sxx_file"]), vec(h["F_file"]), float(h["rbw"])
        bad = []
        r, hp, hf = thd(Sw, Fw, "power", rh)
        cmp(bad, "thd.r", r, h["thd"]["r"])
        cmp(bad, "thd.harmPow", hp, h["thd"]["harmPow"])
        cmp(bad, "thd.harmFreq", hf, h["thd"]["harmFreq"])
        cmp(bad, "snr", snr(Sw, Fw, "power", rh), [h["snr"]["r"], h["snr"]["noisePow"]])
        cmp(bad, "sinad", sinad(Sw, Fw, "power", rh), [h["sinad"]["r"], h["sinad"]["totDistPow"]])
        cmp(bad, "sfdr", sfdr(Sw, Fw, "power"), [h["sfdr"]["r"], h["sfdr"]["spurPow"], h["sfdr"]["spurFreq"]])
        hd = harmonic_distortion(Sw, Fw, rh)
        okp = (same(hd["thd"], r) and same(hd["harm_pow"], hp) and same(hd["harm_freq"], hf) and math.isclose(hd["thd_pct"], 100 * 10 ** (r / 20))
               and hd["harm_rel"][0] == 0.0)
        if not okp:
            bad.append("harmonic_distortion 包裝與 thd 不同")
        report(bad, f"Hann Welch 'power' 頻譜 vs MATLAB（{nm}，L＝{h['L']}、50% 重疊，餵 MATLAB 的 pwelch）：thd、snr、sinad、sfdr 逐值 rtol 1e-12 一致；"
                    f"harmonic_distortion 包裝一致")
        # (g) 面板真正走的路：x → dsv_spectrum.welch(hann(L) 對稱、L/2 重疊、NFFT L、單邊) → harmonic_distortion
        L = int(h["L"])
        res = dsv_spectrum.welch(x, fs, np.hanning(L), L // 2, L, "onesided")     # MATLAB hann(L) 預設 'symmetric' ＝ np.hanning(L)
        okb, info = bins_ok(res["power"], Sw)
        bad = []
        if not (okb and np.array_equal(res["f"], Fw) and math.isclose(res["rbw"], rh, rel_tol=1e-12)):
            bad.append(f"welch power／f／rbw 與 pwelch 不同（{info}）")
        hd = harmonic_distortion(res["power"], res["f"], res["rbw"])
        cmp(bad, "panel.thd", hd["thd"], h["thd"]["r"], RTOL_FFT, ATOL_DB)
        cmp(bad, "panel.harm_pow", hd["harm_pow"], h["thd"]["harmPow"], RTOL_FFT, ATOL_DB)
        cmp(bad, "panel.harm_freq", hd["harm_freq"], h["thd"]["harmFreq"], RTOL_FFT)
        cmp(bad, "panel.snr", [hd["snr"], hd["noise_pow"]], [h["snr"]["r"], h["snr"]["noisePow"]], RTOL_FFT, ATOL_DB)
        cmp(bad, "panel.sinad", hd["sinad"], h["sinad"]["r"], RTOL_FFT, ATOL_DB)
        cmp(bad, "panel.sfdr", [hd["sfdr"], hd["spur_pow"]], [h["sfdr"]["r"], h["sfdr"]["spurPow"]], RTOL_FFT, ATOL_DB)
        cmp(bad, "panel.spur_freq", hd["spur_freq"], h["sfdr"]["spurFreq"], RTOL_FFT)
        report(bad, f"面板路徑 vs MATLAB（{nm}：x → dsv_spectrum.welch(hann {L}, {L // 2}, {L}, 'onesided') → harmonic_distortion）："
                    f"welch power 全部 {res['power'].size} 個 bin 與 pwelch |Δ| ≤ 1e-12·|ref| + 1e-14·峰值（{info}）；"
                    f"thd／harmPow／harmFreq／snr／sinad／sfdr 逐值 rtol 1e-9（dB 值另 ±1e-9 dB）一致")

    # ---------------- 兩音（TOI）案例 ----------------
    for s in R["toi"]:
        nm, fs = s["name"], float(s["fs"])
        x = vec(s["x_file"])
        N = x.size
        Pm, Fm, Sm = vec(s["Pxx_file"]), vec(s["F_file"]), vec(s["Sxx_file"])
        rb = float(s["kaiser_enbw_rbw"])
        P, F, rbw = kaiser38_psd(x, fs)
        okb, info = bins_ok(P, Pm)
        check(okb and math.isclose(rbw, rb, rel_tol=1e-12) and np.array_equal(F, Fm),
              f"週期圖 vs MATLAB periodogram（{nm}：N＝{N}、ENBW、F 全等、Pxx 全部 {P.size} 個 bin |Δ| ≤ 1e-12·|ref| + 1e-14·峰值；{info}）")
        keys = ("oip3", "fundPow", "fundFreq", "imodPow", "imodFreq")
        for tag, got, label, count in (("toi_time", toi_time(x, fs), "時域形式（dsv_spectrum 週期圖）", True),
                                       ("toi_time", toi(Pm, Fm, "psd", rbw=rb), "時域演算法（餵 MATLAB 的 Pxx 與 ENBW；診斷用、不計入總數）", False),
                                       ("toi_psd", toi(Pm, Fm, "psd"), "'psd' 形式", True),
                                       ("toi_power", toi(Sm, Fm, "power", rb), "'power' 形式", True)):
            bad = []
            for k, v in zip(keys, got):
                cmp(bad, f"{tag}.{k}", v, s[tag][k], count=count)
            if tag == "toi_time":
                t = s["toi_time"]
                fp, ip = got[1], got[3]
                cmp(bad, "doc_TOI_lower", fp[0] + (fp[1] - ip[0]) / 2, t["doc_TOI_lower"], count=count)
                cmp(bad, "doc_TOI_upper", fp[1] + (fp[0] - ip[1]) / 2, t["doc_TOI_upper"], count=count)
                cmp(bad, "doc_TOI_avg", (fp[0] + (fp[1] - ip[0]) / 2 + fp[1] + (fp[0] - ip[1]) / 2) / 2, t["doc_TOI_avg"], count=count)
            report(bad, f"toi {label} vs MATLAB（{nm}）：OIP3、基頻功率／頻率、IM3 功率／頻率"
                        f"{'（含 spectrumAnalyzer 文件的 TOI_lower／upper／avg）' if tag == 'toi_time' else ''} 逐值 rtol 1e-12 一致")
        h = s["hannwelch"]
        Sw, Fw, rh = vec(h["Sxx_file"]), vec(h["F_file"]), float(h["rbw"])
        bad = []
        got = toi(Sw, Fw, "power", rh)
        for k, v in zip(keys, got):
            cmp(bad, f"hann.{k}", v, h["toi"][k])
        im = intermod_distortion(Sw, Fw, rh)
        if not (same(im["toi"], got[0]) and same([im["f1"], im["f2"]], got[2]) and same(im["im_pow"], got[3]) and same(im["im_freq"], got[4])
                and same(im["im_rel"], got[3] - got[1])
                and (math.isnan(im["toi"]) or math.isclose((im["toi_lower"] + im["toi_upper"]) / 2, im["toi"], rel_tol=1e-12))):
            bad.append("intermod_distortion 包裝與 toi 不同")
        report(bad, f"Hann Welch 'power' toi vs MATLAB（{nm}，L＝{h['L']}，餵 MATLAB 的 pwelch）：5 個輸出逐值 rtol 1e-12 一致；"
                    f"intermod_distortion 包裝一致、TOI_lower／upper 平均＝OIP3" + ("（下方 IM3 落在 DC 範圍 → NaN）" if math.isnan(got[0]) else ""))
        # 面板路徑：x → dsv_spectrum.welch(hann(L)) → intermod_distortion
        L = int(h["L"])
        res = dsv_spectrum.welch(x, fs, np.hanning(L), L // 2, L, "onesided")
        okb, info = bins_ok(res["power"], Sw)
        bad = []
        if not (okb and np.array_equal(res["f"], Fw) and math.isclose(res["rbw"], rh, rel_tol=1e-12)):
            bad.append(f"welch power／f／rbw 與 pwelch 不同（{info}）")
        im = intermod_distortion(res["power"], res["f"], res["rbw"])
        cmp(bad, "panel.toi", im["toi"], h["toi"]["oip3"], RTOL_FFT, ATOL_DB)
        cmp(bad, "panel.p", [im["p1"], im["p2"]], h["toi"]["fundPow"], RTOL_FFT, ATOL_DB)
        cmp(bad, "panel.f", [im["f1"], im["f2"]], h["toi"]["fundFreq"], RTOL_FFT)
        cmp(bad, "panel.im_pow", im["im_pow"], h["toi"]["imodPow"], RTOL_FFT, ATOL_DB)
        cmp(bad, "panel.im_freq", im["im_freq"], h["toi"]["imodFreq"], RTOL_FFT)
        report(bad, f"面板路徑 vs MATLAB（{nm}：x → dsv_spectrum.welch(hann {L}, {L // 2}, {L}, 'onesided') → intermod_distortion）："
                    f"welch power 全部 bin 與 pwelch |Δ| ≤ 1e-12·|ref| + 1e-14·峰值（{info}）；TOI、F1／F2 功率與頻率、IM3 功率與頻率 "
                    f"逐值 rtol 1e-9（dB 值另 ±1e-9 dB）一致")

    # ---------------- 錯誤訊息 ----------------
    s0 = R["harmonic"][0]
    x = vec(s0["x_file"])
    fs = float(s0["fs"])
    Pm, Fm, Sm = vec(s0["Pxx_file"]), vec(s0["F_file"]), vec(s0["Sxx_file"])
    rb0 = float(s0["kaiser_enbw_rbw"])
    df = float(np.mean(np.diff(Fm)))
    calls = {"thd(x,fs,1)": lambda: thd_time(x, fs, 1), "thd(x,fs,2.5)": lambda: thd_time(x, fs, 2.5), "thd(x,-1)": lambda: thd_time(x, -1),
             "thd(Pxx(2:end),F(2:end),'psd')": lambda: thd(Pm[1:], Fm[1:], "psd"), "thd(Sxx,F,df/2,'power')": lambda: thd(Sm, Fm, "power", df / 2),
             "thd(x,fs,'foo')": lambda: thd_time(x, fs, harm_type="foo"), "thd([x x],fs)": lambda: thd_time(np.column_stack([x, x]), fs),
             "snr(x,fs,1)": lambda: snr_time(x, fs, 1), "snr(Pxx(2:end),F(2:end),'psd')": lambda: snr(Pm[1:], Fm[1:], "psd"),
             "sinad(Pxx.',F,'psd') (row)": lambda: sinad(Pm[None, :], Fm, "psd"), "sinad(Sxx,F,df/2,'power')": lambda: sinad(Sm, Fm, "power", df / 2),
             "sfdr(x,fs,-1)": lambda: sfdr_time(x, fs, -1), "sfdr(Sxx(2:end),F(2:end),'power')": lambda: sfdr(Sm[1:], Fm[1:], "power"),
             "sfdr(Sxx*0,F,'power') (not positive)": lambda: sfdr(Sm * 0, Fm, "power"),
             "toi(Pxx(2:end),F(2:end),'psd')": lambda: toi(Pm[1:], Fm[1:], "psd"), "toi(Sxx,F,df/2,'power')": lambda: toi(Sm, Fm, "power", df / 2)}
    bad = []
    n_err = 0
    for e in R["errors"]:
        fn = calls.get(e["call"])
        if fn is None:
            bad.append(f"{e['call']}：selftest 沒有對應的呼叫")
            continue
        n_err += 1
        stats["n"] += 2
        try:
            fn()
            bad.append(f"{e['call']}：沒有丟錯（MATLAB：{e['identifier']}）")
        except DistortionError as ex:
            okid, okmsg = ex.identifier == e["identifier"], ex.message == e["message"]
            stats["ok"] += int(okid) + int(okmsg)
            if not (okid and okmsg):
                bad.append(f"{e['call']}：{ex.identifier} / {ex.message!r} ≠ {e['identifier']} / {e['message']!r}")
        except Exception as ex:                                     # noqa: BLE001
            bad.append(f"{e['call']}：丟了 {type(ex).__name__}: {ex}")
    report(bad, f"錯誤 vs MATLAB（{n_err} 個：N ≤ 1／非整數、Fs ≤ 0、F[0] ≠ 0、RBW < bin 寬、不認得的選項、不是向量／直向量、MSD ≤ 0、Sxx 非正）："
                f"DistortionError 的 identifier 與英文訊息逐字一致")

    # ---------------- 輸入保護（DSV 自訂、參考資料沒有的情況；不計入 MATLAB 總數） ----------------
    bad = []

    def expect(label: str, fn, ident: str) -> None:
        try:
            fn()
            bad.append(f"{label}：沒有丟錯（要 {ident}）")
        except DistortionError as ex:
            if ex.identifier != ident:
                bad.append(f"{label}：{ex.identifier} ≠ {ident}")
        except Exception as ex:                                     # noqa: BLE001
            bad.append(f"{label}：丟了 {type(ex).__name__}: {ex}")

    e0 = np.zeros(0)
    expect("thd([],[],'psd')", lambda: thd(e0, e0, "psd"), "MATLAB:thd:expectedVector")
    expect("snr([],[],'psd')", lambda: snr(e0, e0, "psd"), "MATLAB:snr:expectedVector")
    expect("sinad([],[],'psd')", lambda: sinad(e0, e0, "psd"), "MATLAB:sinad:expectedColumn")
    expect("sfdr([],[],'power')", lambda: sfdr(e0, e0, "power"), "MATLAB:sfdr:expectedVector")
    expect("toi([],[],'psd')", lambda: toi(e0, e0, "psd"), "MATLAB:toi:expectedVector")
    expect("thd_time([])", lambda: thd_time(e0, fs), "MATLAB:thd:expectedVector")
    expect("snr_time([])", lambda: snr_time(e0, fs), "MATLAB:snr:expectedVector")
    expect("sinad_time([])", lambda: sinad_time(e0, fs), "MATLAB:sinad:expectedVector")
    expect("sfdr_time([])", lambda: sfdr_time(e0, fs), "MATLAB:sfdr:expectedVector")
    expect("toi_time([])", lambda: toi_time(e0, fs), "MATLAB:toi:expectedVector")
    expect("tone([],[],1)", lambda: tone(e0, e0, 1.0), "dsv:tone:EmptyInput")
    emp = dsv_spectrum.welch(x[:100], fs, np.hanning(1024), 512, 1024, "onesided")        # 資料不夠一段 → 空陣列（GUI 會碰到）
    expect("harmonic_distortion(welch 空結果)", lambda: harmonic_distortion(emp["power"], emp["f"], emp["rbw"]), "MATLAB:thd:expectedVector")
    expect("intermod_distortion(welch 空結果)", lambda: intermod_distortion(emp["power"], emp["f"], emp["rbw"]), "MATLAB:toi:expectedVector")
    expect("harmonic_distortion(n_harm=1e9)", lambda: harmonic_distortion(Sm, Fm, rb0, n_harm=10 ** 9), "dsv:harmonic_distortion:invalidNumHarmonics")
    expect("harmonic_distortion(n_harm=100)", lambda: harmonic_distortion(Sm, Fm, rb0, n_harm=100), "dsv:harmonic_distortion:invalidNumHarmonics")
    expect("harmonic_distortion(n_harm=1)", lambda: harmonic_distortion(Sm, Fm, rb0, n_harm=1), "dsv:harmonic_distortion:invalidNumHarmonics")
    expect("harmonic_distortion(n_harm='6')", lambda: harmonic_distortion(Sm, Fm, rb0, n_harm="6"), "dsv:harmonic_distortion:invalidNumHarmonics")
    expect("harmonic_distortion(n_harm=3.5)", lambda: harmonic_distortion(Sm, Fm, rb0, n_harm=3.5), "MATLAB:thd:expectedInteger")
    expect("thd(Pxx,F,'psd',n_harm='6')", lambda: thd(Pm, Fm, "psd", n_harm="6"), "MATLAB:thd:invalidType")
    expect("thd_time(x,'48000')", lambda: thd_time(x, "48000"), "MATLAB:thd:invalidType")
    expect("thd_time(['a','b'],fs)", lambda: thd_time(np.array(["a", "b"]), fs), "MATLAB:thd:invalidType")
    expect("sinad(Pxx,F 遞減,'psd')", lambda: sinad(Pm, Fm[::-1], "psd"), "MATLAB:sinad:expectedIncreasing")
    expect("snr(Pxx,F 遞減,'psd')", lambda: snr(Pm, Fm[::-1], "psd"), "MATLAB:snr:expectedIncreasing")
    expect("snr(Pxx,F(1:end-1) 遞減,'psd')", lambda: snr(Pm, -Fm[:-1], "psd"), "MATLAB:snr:expectedIncreasing")      # snr：increasing 在 numel 前
    expect("sinad(Pxx,F(1:end-1) 遞減,'psd')", lambda: sinad(Pm, -Fm[:-1], "psd"), "MATLAB:sinad:incorrectNumel")   # sinad：numel 在 increasing 前
    try:
        if not math.isclose(thd(Pm, Fm[::-1] * 0 + Fm, "psd")[0], thd(Pm, Fm, "psd")[0]):
            bad.append("thd 多餘的檢查")
        thd(Pm, Fm.astype(np.int64) if np.all(Fm == np.round(Fm)) else Fm, "psd")                  # 整數 dtype 接受
        s_hp = thd(np.array(1.0), np.array(0.0), "psd")                                              # 純量當 1 個元素的向量
        if not (math.isnan(s_hp[0]) and s_hp[1].size == DEFAULT_NUM_HARMONICS):
            bad.append("純量輸入沒當 1 bin 處理")
    except Exception as ex:                                         # noqa: BLE001
        bad.append(f"整數 dtype／純量：丟了 {type(ex).__name__}: {ex}")
    n1 = 0
    with warnings.catch_warnings(record=True) as wl:               # 1 個樣本／1 個 bin：照 MATLAB 是 NaN，不印 numpy 警告
        warnings.simplefilter("always")
        one, f1 = np.array([1.0]), np.array([0.0])
        vals = [thd_time(one, fs)[0], snr_time(one, fs)[0], sinad_time(one, fs)[0], sfdr_time(one, fs)[0], toi_time(one, fs)[0],
                thd(one, f1, "psd")[0], snr(one, f1, "psd")[0], sinad(one, f1, "psd")[0], toi(one, f1, "psd")[0], tone(one, f1, 1.0).power]
        n1 = len(vals)
        if not all(math.isnan(v) for v in vals):
            bad.append(f"單樣本／單 bin 的結果不是全 NaN：{vals}")
        try:
            harmonic_distortion(one, f1, 10.0)
            bad.append("harmonic_distortion 單 bin 沒丟錯")
        except DistortionError as ex:
            if ">= NaN" not in ex.message:
                bad.append(f"harmonic_distortion 單 bin 的訊息：{ex.message!r}")
    if wl:
        bad.append(f"單樣本輸入有 {len(wl)} 個警告：{wl[0].category.__name__}: {wl[0].message}")
    # tone() 的 NaN 語意照 MATLAB：max 略過 NaN、裙邊碰到 NaN 停
    t = tone(np.array([np.nan, np.nan, np.nan]), np.arange(3.0), 1.0)
    if (t.idx, t.left, t.right) != (0, 0, 0) or not (math.isnan(t.power) and math.isnan(t.freq)):
        bad.append(f"tone 全 NaN：idx/left/right={t.idx}/{t.left}/{t.right}（MATLAB 0/0/0）")
    t = tone(np.array([1.0, 3.0, np.nan, 2.0, 1.0]), np.arange(5.0), 1.0)
    if (t.idx, t.left, t.right) != (1, 0, 1):
        bad.append(f"tone 中間 NaN：idx/left/right={t.idx}/{t.left}/{t.right}（MATLAB 1/0/1）")
    t = tone(np.array([0.1, 0.2, 0.3, 5.0, 0.4, np.nan, 0.2]), np.arange(7.0), 1.0, 3.0)
    if (t.idx, t.left, t.right) != (3, 0, 4):
        bad.append(f"tone 右側 NaN：idx/left/right={t.idx}/{t.left}/{t.right}（MATLAB 3/0/4）")
    report(bad, f"輸入保護（DSV 自訂、參考資料沒有的情況）：空陣列（含 welch 資料不夠一段的空結果）→ expectedVector／expectedColumn、"
                f"面板 n_harm 限 2..99（1e9／100／1／'6' → invalidNumHarmonics、3.5 → thd 的 expectedInteger）、字串 → invalidType、"
                f"F 不遞增 → snr／sinad 的 expectedIncreasing（檢查順序照 MATLAB）、整數 dtype 與純量接受、{n1} 個單樣本／單 bin 結果是 NaN 且無 numpy 警告、"
                f"tone() 的 NaN 語意照 MATLAB（max 略過 NaN、裙邊碰到 NaN 停）")

    # ---------------- 雙邊 → 單邊折疊 ----------------
    bad = []
    for s in (R["harmonic"][0], R["harmonic"][2]):                  # 偶數 N（2048）與奇數 N（1999）
        x = vec(s["x_file"])
        fs = float(s["fs"])
        w = np.kaiser(x.size, KAISER_BETA)
        one = dsv_spectrum.welch(x, fs, w, 0, x.size, "onesided")
        for mode in ("centered", "twosided"):
            two = dsv_spectrum.welch(x, fs, w, 0, x.size, mode)
            for key in ("power", "psd"):
                f1, s1 = fold_onesided(two["f"], two[key], mode)
                # 折疊規則本身是精確的；位元差只來自 numpy 版本的 FFT 捨入（numpy 2.4 位元一致，1.26 的 pocketfft 對實數輸入在
                # onesided／centered 兩條路徑的最後幾位不同）→ 用 bin 容差 RTOL_ALG·|ref| + BIN_ATOL·峰值
                if not (np.array_equal(f1, one["f"]) and bins_ok(s1, one[key])[0]):
                    bad.append(f"{s['name']} {mode} {key}")
        f1, s1 = fold_onesided(one["f"], one["power"], "onesided")
        if not (np.array_equal(s1, one["power"])):
            bad.append(f"{s['name']} onesided 原樣")
        hd1 = harmonic_distortion(one["power"], one["f"], one["rbw"])
        f2, s2 = fold_onesided(*(lambda r: (r["f"], r["power"]))(dsv_spectrum.welch(x, fs, w, 0, x.size, "centered")), "centered")
        hd2 = harmonic_distortion(s2, f2, one["rbw"])
        if not all(abs(hd1[k] - hd2[k]) <= RTOL_ALG * abs(hd1[k]) + ABS_FLOOR for k in ("thd", "snr", "sinad", "sfdr")):
            bad.append(f"{s['name']} 折疊後的失真數字不同")
    report(bad, "雙邊 → 單邊折疊（fold_onesided）：centered／twosided 的 power 與 psd 折起來和 welch 'onesided' 一致到 FFT 捨入（偶數、奇數 NFFT；"
                "numpy 2.4 位元一致、1.26 差最後幾位），harmonic_distortion 結果一致（rtol 1e-12）")

    # ---------------- Spectrum Analyzer 本體（scope）實測的 20 個 capture（2026-10-24；tests/matlab_ref/scope/distortion/） ----------------
    _scope_selftest(check, ref_dir)

    # ---------------- 速度：1e6 點 ----------------
    fs6 = 1e6
    n6 = 1_000_000
    tt = np.arange(n6) / fs6
    rng = np.random.default_rng(0)
    x6 = np.cos(2 * np.pi * 10e3 * tt) + 1e-3 * np.cos(2 * np.pi * 20e3 * tt) + 3e-4 * np.cos(2 * np.pi * 30e3 * tt) + 1e-4 * rng.standard_normal(n6)
    x6 += 0.3 * np.cos(2 * np.pi * 12e3 * tt)
    t0 = _time.time()
    P6, F6, rbw6 = kaiser38_psd(x6, fs6)
    t_pg = _time.time() - t0
    S6 = P6 * rbw6
    t0 = _time.time()
    hd = harmonic_distortion(S6, F6, rbw6)
    im = intermod_distortion(S6, F6, rbw6)
    t_hd = _time.time() - t0
    t0 = _time.time()
    hd99 = harmonic_distortion(S6, F6, rbw6, n_harm=MAX_PANEL_HARMONICS)
    t_99 = _time.time() - t0
    # 1e6 個 bin 的頻譜（寬裙邊：確認裙邊搜尋不是逐 bin 的 Python 迴圈）。底是平滑起伏的（隨機底會讓裙邊在峰附近就停：高斯峰頂每 bin 只差 5e-16）
    F7 = np.arange(1_000_000) * 1.0
    S7 = 1e-12 * (1.0 + 0.01 * np.sin(F7 / 500.0))
    for c, a in ((300_000, 1.0), (600_000, 1e-8), (900_000, 1e-10)):          # 諧波 −80、−100 dBc，裙邊各寬約 2×4σ＝24000 bins
        k = np.arange(-20_000, 20_001)
        S7[c + k] += a * np.exp(-0.5 * (k / 3000.0) ** 2)
    S7[:1000] += 0.01 * np.exp(-np.arange(1000) / 100.0)
    t0 = _time.time()
    hd7 = harmonic_distortion(S7, F7, 1.5)
    t_7 = _time.time() - t0
    thd_exp = 10 * math.log10(1e-6 + 9e-8)
    ok = (abs(hd["harm_freq"][0] - 10e3) < 1 and abs(hd["thd"] - thd_exp) < 0.1 and abs(im["f1"] - 10e3) < 1 and abs(im["f2"] - 12e3) < 1
          and abs(hd7["harm_freq"][0] - 300_000) < 1 and abs(hd7["thd"] - 10 * math.log10(1.01e-8)) < 0.5 and t_pg + t_hd < 3.0 and t_7 < 3.0
          and t_99 < 3.0 and hd99["harm_pow"].size == MAX_PANEL_HARMONICS and np.isnan(hd99["harm_pow"][50:]).all()
          and np.array_equal(hd99["harm_pow"][:6], hd["harm_pow"], equal_nan=True))
    check(ok, f"速度：1e6 點訊號 → Kaiser 週期圖 {t_pg:.2f}s、harmonic_distortion＋intermod_distortion（500001 bins）{t_hd:.2f}s、"
              f"N＝99 {t_99:.2f}s（第 51 個起超過 Nyquist 全是 NaN、前 6 個和 N＝6 相同）；1e6 bins 寬裙邊頻譜 harmonic_distortion {t_7:.2f}s；"
              f"THD {hd['thd']:.2f} dBc（理論 {thd_exp:.2f}）、F1/F2 {im['f1']:.0f}/{im['f2']:.0f} Hz；寬裙邊 THD {hd7['thd']:.2f} dBc"
              f"（理論 {10 * math.log10(1.01e-8):.2f}）")
    check(stats["ok"] == stats["n"] and stats["roff_ok"] == stats["roff"],
          f"MATLAB 參考值總計：比對 {stats['n']} 個值，{stats['ok']} 個在容差內一致（演算法與時域形式 rtol 1e-12、面板路徑 rtol 1e-9＋dB 值 1e-9 dB、"
          f"錯誤 identifier／訊息逐字）；另 {stats['roff']} 個是 FFT 捨入底（< 基頻 −250 dB）的值，{stats['roff_ok']} 個同為底（±10 dB／2 bin）")


# 容差（scope 實測比對；scope_capture/ANALYSIS.md §4.1 報的殘差：諧波 14/15 個 capture ≤ 1.3e-11 dB／9e-13 Hz，互調 5/5 個 ≤ 1.2e-13 dB）
SCOPE_TOL_DB = 1e-10         # 功率（dBm）、THD、THD%、SNR、SINAD、SFDR——純捨入的上界加餘裕：實測最大殘差 numpy 2.4 1.6e-11、numpy 1.26 1.65e-11 dB，
#                              scope 自己的 fft 捨入 3.9e-12（60 位精度 DFT 對照）；1e-10 dB＝相對功率 2.3e-11，離任何規則錯誤仍差 5 個數量級以上
SCOPE_TOL_HZ = 1e-12         # 頻率（bin 中心；h_odd 的 df＝48000/1999 不是二進位小數，殘差 9.1e-13）
SCOPE_TOL_TOI_DB = 1e-12     # 互調：功率與 TOI（實測最大 7.1e-14 dB；留 10 倍餘裕給其他 FFT 實作）
SCOPE_ROFF_REL = 1e-25       # 捨入底：低於 P1·1e-25（−250 dBc）的值是 FFT 捨入（h_noiseless 第 4–6 列 ≈ 1e-31 W、Pnoise ≈ 1e-28 W），兩種 FFT 不同
SCOPE_ROFF_DB = 1.0          # 捨入底的功率列 dBm 值兩種 FFT 相差 ≤ 1 dB（觀測 0.35 dB）
SCOPE_ROFF_SNR_DB = 0.01     # 捨入底的 SNR 相差 ≤ 0.01 dB（觀測 6.5e-4 dB）
# 已知差異（capture 解不出的規則；數字是 scope 的與我們的，selftest 斷言兩邊都還是這些數字，差異保持看得見）
SCOPE_KNOWN = {
    "dist_h_alias_1s_N6": {"SFDR": {"scope": 28.745379327536668, "ours": 35.47082906366433,
                                    "note": "scope 的 SFDR 隱含 spur −1.9116 dBm（6.439e-4 W）；文件規則（清完 DC、基頻、諧波後剩下的最大 bin＝20688 Hz，"
                                            "H3 的 alias，−14.435 dBm；max P_k＝H2 −8.637 dBm）給 35.4708 dB，差 6.73 dB。候選規則「每根音只清峰值 ±1 bin」"
                                            "會留下基頻主瓣的 bin 381（9144 Hz，−1.700 dBm）給 28.534 dB（差 0.21 dB），但它把 4 個已驗證的 capture 弄壞"
                                            "（h_noisy −3.50、h_lowf −22.34、h_odd −12.22、maxhold −22.34 dB），不能採用；單一 bin、×0.5／×2／×df/RBW／"
                                            "×RBW/df、任兩個 bin 的和或幾何平均、連續 2–6 個 bin 的和、對稱 Hann 的頻譜、別的 capture 殘留的數字都對不上"
                                            "（work2/distortion/sfdr_hypotheses.py）→ P_maxspur 的定義未解；其他 14 個 capture 的 SFDR 都＝P1/max P_k，"
                                            "只有非諧波的 spur 比每個諧波都大時才會有差"}},
    "dist_toi_lowimd_dc_1s": {"Frequency[3]": {"scope": 4171.875, "ours": math.nan,
                                               "note": "2·Fe2−Fe1≈ −600 Hz（重心 1000.0／2600.0 Hz；bin 中心算是 −586）不存在：scope 功率 −Inf、TOI +Inf（一致），"
                                                       "頻率欄卻顯示 4171.875 Hz＝第 3 列的積（bin 179，4195.3125 Hz）往下一個 bin＝f[t3−1]，也等於第 3 列搜尋窗的下緣"
                                                       "f[tb3−1]（tb3＝179）；第 3 列裙邊左緣 f[165]＝3867.1875 對不上。一個 capture 分不出是哪個殘留變數，"
                                                       "這裡回 NaN（不重現一個沒意義的數字）"}},
}
SCOPE_ROUNDOFF = {"dist_h_noiseless_1s_N6": {"rows": (3, 4, 5), "snr": True,
                                              "note": "沒有加雜訊：第 4–6 個諧波（−278／−273／−276 dBm ≈ 1e-31 W）與 Pnoise（≈ 1e-28 W）是 FFT 的捨入，"
                                                      "MATLAB 與 numpy 的 FFT 捨入不同；THD、SINAD、SFDR、前 3 列照嚴格容差"}}


def _scope_selftest(check, ref_dir: str) -> None:
    """20 個 spectrumAnalyzer capture（tests/matlab_ref/scope/distortion/scope_distortion.json）：從訊號重建 scope 顯示的頻譜
    （dsv_spectrum.design_window('hann') periodic、NFFT＝max(1024, L)、power |X|²/(Σw)²、psd |X|²/(fs·Σw²)、兩邊 centered、單邊 ×2，
    SpectralAverages 1 所以沒有平均；Max-Hold 的 capture 用最後一次呼叫的 normal trace），餵 scope_harmonic／scope_intermod，和 scope 的數字逐欄比對。"""
    import json
    import os
    sdir = os.path.join(ref_dir, "scope", "distortion")
    spath = os.path.join(sdir, "scope_distortion.json")
    if not os.path.isfile(spath):
        check(True, "（沒有 tests/matlab_ref/scope/distortion：略過 spectrumAnalyzer 實測比對）")
        return
    with open(spath, encoding="utf-8") as fh:
        SC = json.load(fh)
    st = {"caps": 0, "caps_ok": 0, "n": 0, "ok": 0, "worst_db": 0.0, "worst_hz": 0.0, "worst_toi": 0.0, "known": 0, "known_ok": 0}

    def one(g: float, r: float, tol: float, bad: list, label: str, kind: str) -> None:
        """一個數字：scope 是 ±Inf 要相等、NaN 要同為 NaN，否則 |我−scope| ≤ tol；記最大殘差。"""
        st["n"] += 1
        if math.isnan(r) or math.isinf(r):
            ok = (math.isnan(g) and math.isnan(r)) or g == r
        else:
            d = abs(g - r)
            ok = d <= tol
            st["worst_" + kind] = max(st["worst_" + kind], d)
        st["ok"] += int(ok)
        if not ok:
            bad.append(f"{label} 我={g!r} scope={r!r}")

    def many(g, r, tol: float, bad: list, label: str, kind: str, skip=()) -> None:
        g = np.atleast_1d(np.asarray(g, dtype=float)).reshape(-1)
        r = np.atleast_1d(np.asarray(r, dtype=float)).reshape(-1)
        if g.size != r.size:
            st["n"] += r.size
            bad.append(f"{label}：列數 {g.size} ≠ {r.size}")
            return
        for i in range(r.size):
            if i not in skip:
                one(float(g[i]), float(r[i]), tol, bad, f"{label}[{i}]", kind)

    def known_check(ok: bool, msg: str) -> None:
        st["known"] += 1
        st["known_ok"] += int(ok)
        check(ok, msg)

    for cap in SC["captures"]:
        nm, cfg, sig, sc = cap["name"], cap["config"], cap["signal"], cap["scope"]
        xs = []
        for c in sig["calls"]:                                      # 多次呼叫（Max-Hold capture）：scope 量的是最後一幀的 normal trace
            if "file_re" in c:
                x = np.loadtxt(os.path.join(ref_dir, c["file_re"])) + 1j * np.loadtxt(os.path.join(ref_dir, c["file_im"]))
            else:
                x = np.loadtxt(os.path.join(ref_dir, c["file"]))
            xs.append(x * c["scale"])
        x = xs[-1]
        fs = float(sig["fs"])
        L = int(cfg["window_length"])
        nfft = max(getattr(dsv_spectrum, "MIN_AUTO_NFFT", 1024), L)
        two = bool(cfg["two_sided"])
        psd = cfg["spectrum_type"] == "power-density"
        res = dsv_spectrum.welch(x, fs, dsv_spectrum.design_window("hann", L), 0, nfft, "centered" if two else "onesided")
        tr, fg, rb, kind = (res["psd"] if psd else res["power"]), res["f"], float(res["rbw"]), ("psd" if psd else "power")
        bad: list = []
        disp = cap["display"]
        if disp["fresh"] and not (fg.size == disp["nbins"] and math.isclose(fg[1] - fg[0], disp["df_Hz"], rel_tol=1e-12)
                                  and math.isclose(fg[0], disp["f_first_Hz"], abs_tol=1e-9) and math.isclose(fg[-1], disp["f_last_Hz"], abs_tol=1e-9)):
            bad.append(f"頻率格 {fg.size} bins {fg[0]}..{fg[-1]} ≠ 顯示的 {disp['nbins']} bins {disp['f_first_Hz']}..{disp['f_last_Hz']}")
        known = SCOPE_KNOWN.get(nm, {})
        roff = SCOPE_ROUNDOFF.get(nm)
        head = (f"scope capture {nm}（{cap['type']}，{'兩邊' if two else '單邊'}{'、複數' if sig['complex'] else ''}，{cfg['spectrum_type']}，"
                f"L＝{L}、NFFT＝{nfft}、df＝{fg[1] - fg[0]:g} Hz、RBW＝{rb:.6g} Hz{'、顯示 fresh（格一致）' if disp['fresh'] else '、顯示 stale（用模型頻譜）'}"
                f"{'、第 2 次呼叫 0.1·h_lowf' if len(xs) > 1 else ''}）：")
        st["caps"] += 1
        if cap["type"] == "harmonic":
            r = scope_harmonic(tr, fg, rb, cap["num_harmonics"], kind)
            if list(r["harmonic_number"]) != list(sc["HarmonicNumber"]):
                bad.append(f"HarmonicNumber {list(r['harmonic_number'])} ≠ {sc['HarmonicNumber']}")
            skip = set(roff["rows"]) if roff else set()
            many(r["freq"], sc["Frequency"], SCOPE_TOL_HZ, bad, "Frequency", "hz", skip)
            many(r["power_db"] + 30.0, sc["Power"], SCOPE_TOL_DB, bad, "Power", "db", skip)
            for key, mine in (("THD", r["thd"]), ("THDPercent", r["thd_pct"]), ("SNR", r["snr"]), ("SINAD", r["sinad"]), ("SFDR", r["sfdr"])):
                if key in known or (roff and roff["snr"] and key == "SNR"):
                    continue
                one(float(mine), float(sc[key]), SCOPE_TOL_DB, bad, key, "db")
            st["caps_ok"] += int(not bad)
            check(not bad, head + f"NumHarmonics {cap['num_harmonics']} → {r['n_found']} 列（超過 Nyquist 的不列）；頻率（±{SCOPE_TOL_HZ:g} Hz）、功率 dBm"
                             f"（±{SCOPE_TOL_DB:g} dB）、THD／THD%／SNR／SINAD／SFDR（±{SCOPE_TOL_DB:g}）和 scope 一致"
                             + (f"（{'、'.join(known)} 另列已知差異）" if known else "") + ("（第 4–6 列與 SNR 另列捨入底）" if roff else "")
                             + (f"（不一致：{'; '.join(bad[:4])}）" if bad else ""))
            if "SFDR" in known:
                kd = known["SFDR"]
                ours = kd["ours"]
                ok = (math.isclose(float(sc["SFDR"]), kd["scope"], abs_tol=1e-9) and ours is not None and abs(r["sfdr"] - ours) <= 1e-9
                      and math.isclose(r["sfdr"], float(sc["SFDR"]) + (ours - kd["scope"]), abs_tol=1e-9))
                known_check(ok, f"已知差異 {nm} SFDR：scope {float(sc['SFDR']):.12f} dB、我們 {r['sfdr']:.12f} dB（差 {r['sfdr'] - float(sc['SFDR']):+.4f} dB；"
                                f"記錄的我們值 {ours}；spur_freq {r['spur_freq']:.4f} Hz、spur {_db(r['spur_power']) + 30:.4f} dBm）——{kd['note']}")
            if roff:
                rows = list(roff["rows"])
                p1 = float(r["power"][0])
                floor = p1 * SCOPE_ROFF_REL
                sp_w = 10.0 ** ((np.asarray(sc["Power"], dtype=float)[rows] - 30.0) / 10.0)
                ours_w = r["power"][rows]
                d_db = np.abs(r["power_db"][rows] + 30.0 - np.asarray(sc["Power"], dtype=float)[rows])
                k = np.asarray(rows) + 1
                d_f = np.abs(r["freq"][rows] - k * r["fund_centroid"])
                sc_noise = p1 / 10.0 ** (float(sc["SNR"]) / 10.0)
                d_snr = abs(r["snr"] - float(sc["SNR"]))
                ok = (bool(np.all(sp_w < floor)) and bool(np.all(ours_w < floor)) and bool(np.all(d_db <= SCOPE_ROFF_DB))
                      and bool(np.all(d_f <= (SCOPE_HALF_WINDOW + 0.5) * r["df"])) and sc_noise < floor and r["noise_power"] < floor
                      and d_snr <= SCOPE_ROFF_SNR_DB)
                known_check(ok, f"已知差異（捨入底）{nm}：第 {k.tolist()} 列功率 scope {np.round(np.asarray(sc['Power'])[rows], 4).tolist()} dBm、"
                                f"我們 {np.round(r['power_db'][rows] + 30.0, 4).tolist()} dBm（差 ≤ {d_db.max():.4f} dB；兩邊都 < P1·1e-25＝{floor:.1e} W）；"
                                f"頻率 scope {np.asarray(sc['Frequency'])[rows].tolist()}、我們 {r['freq'][rows].tolist()} Hz（都在 k·Fe1 ±1.5 bin 的搜尋窗裡）；"
                                f"SNR scope {float(sc['SNR']):.9f}、我們 {r['snr']:.9f} dB（差 {d_snr:.2e} dB；Pnoise {sc_noise:.2e} 與 {r['noise_power']:.2e} W 都是捨入底）"
                                f"——{roff['note']}")
        else:
            r = scope_intermod(tr, fg, rb, kind)
            skip = {3} if "Frequency[3]" in known else set()
            many(r["freq"], sc["Frequency"], SCOPE_TOL_HZ, bad, "Frequency", "hz", skip)
            many(r["power_db"] + 30.0, sc["Power"], SCOPE_TOL_TOI_DB, bad, "Power", "toi")
            one(float(r["toi"]) + 30.0, float(sc["TOI"]), SCOPE_TOL_TOI_DB, bad, "TOI", "toi")
            st["caps_ok"] += int(not bad)
            check(not bad, head + f"F1／F2／2F1−F2／2F2−F1 的頻率（±{SCOPE_TOL_HZ:g} Hz）、功率 dBm 與 TOI（±{SCOPE_TOL_TOI_DB:g} dB）和 scope 一致"
                             f"（TOI_lower {r['toi_lower'] + 30:.6f}、TOI_upper {r['toi_upper'] + 30:.6f} dBm）"
                             + (f"（{'、'.join(known)} 另列已知差異）" if known else "") + (f"（不一致：{'; '.join(bad[:4])}）" if bad else ""))
            if "Frequency[3]" in known:
                kd = known["Frequency[3]"]
                ok = (math.isnan(r["freq"][3]) and float(sc["Frequency"][3]) == kd["scope"] and r["power"][3] == 0.0 and math.isinf(r["toi"])
                      and float(sc["Power"][3]) == -math.inf and float(sc["TOI"]) == math.inf)
                known_check(ok, f"已知差異 {nm} 第 4 列（2F2−F1＝{r['targets'][1]:.1f} Hz < 0）頻率：scope {kd['scope']} Hz、我們 NaN；功率 −Inf 與 TOI +Inf 兩邊一致"
                                f"——{kd['note']}")

    # 輸入保護（DSV 自訂）：dB 值、複數、2-D、太大、太少、長度不同、F 不遞增、N 不合、kind／mode 不認得 → DistortionError；全 0 不印警告；排列等價
    bad = []
    n0 = 1025
    f0 = np.arange(n0) * 23.4375
    s0 = 1e-6 * (1.0 + 0.1 * np.cos(f0 / 700.0))
    s0[108] = 0.5
    s0[216] = 5e-5
    s0[0] = 0.09

    def expect(label: str, fn, ident: str) -> None:
        try:
            fn()
            bad.append(f"{label}：沒有丟錯（要 {ident}）")
        except DistortionError as ex:
            if ex.identifier != ident:
                bad.append(f"{label}：{ex.identifier} ≠ {ident}")
        except Exception as ex:                                     # noqa: BLE001
            bad.append(f"{label}：丟了 {type(ex).__name__}: {ex}")

    expect("dB 值（負）", lambda: scope_harmonic(10 * np.log10(s0), f0, 35.15625), "dsv:scope_harmonic:expectedNonnegative")
    expect("複數 trace", lambda: scope_harmonic(s0 * (1 + 0j), f0, 35.15625), "dsv:scope_harmonic:expectedReal")
    expect("2-D trace", lambda: scope_harmonic(np.tile(s0, (2, 1)), f0, 35.15625), "dsv:scope_harmonic:expectedVector")
    expect("字串 trace", lambda: scope_intermod(np.array(["a", "b"]), f0[:2], 35.15625), "dsv:scope_intermod:invalidType")
    expect("空 trace", lambda: scope_harmonic(np.zeros(0), np.zeros(0), 35.15625), "dsv:scope_harmonic:expectedVector")
    expect("1 個 bin", lambda: scope_harmonic(np.array([1.0]), np.array([0.0]), 35.15625), "dsv:scope_harmonic:tooFewBins")
    expect("長度不同", lambda: scope_harmonic(s0, f0[:-1], 35.15625), "dsv:scope_harmonic:incorrectNumel")
    expect("F 不遞增", lambda: scope_harmonic(s0, f0[::-1] * 0 + np.r_[f0[1:], f0[0]], 35.15625), "dsv:scope_harmonic:expectedIncreasing")
    expect("RBW 0", lambda: scope_harmonic(s0, f0, 0.0), "dsv:scope_harmonic:expectedPositive")
    expect("RBW NaN", lambda: scope_intermod(s0, f0, math.nan), "dsv:scope_intermod:expectedFinite")
    expect("N＝1", lambda: scope_harmonic(s0, f0, 35.15625, 1), "dsv:scope_harmonic:invalidNumHarmonics")
    expect("N＝100", lambda: scope_harmonic(s0, f0, 35.15625, 100), "dsv:scope_harmonic:invalidNumHarmonics")
    expect("N＝3.5", lambda: scope_harmonic(s0, f0, 35.15625, 3.5), "dsv:scope_harmonic:invalidNumHarmonics")
    expect("N＝'6'", lambda: scope_harmonic(s0, f0, 35.15625, "6"), "dsv:scope_harmonic:invalidNumHarmonics")
    expect("kind 不認得", lambda: scope_harmonic(s0, f0, 35.15625, 6, "dbm"), "signal:chknostropts:UnknownOption")
    expect("mode 不認得", lambda: scope_harmonic(s0, f0, 35.15625, 6, "power", "folded"), "dsv:scope_harmonic:unknownMode")
    big = np.broadcast_to(np.float64(1.0), (SCOPE_MAX_BINS + 1,))                  # 不佔記憶體的 2^24+1 個 bin
    expect("2^24+1 bins", lambda: scope_harmonic(big, big, 1.0), "dsv:scope_harmonic:tooManyBins")
    expect("2^24+1 bins（互調）", lambda: scope_intermod(big, big, 1.0), "dsv:scope_intermod:tooManyBins")
    import warnings
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        z = scope_harmonic(np.zeros(n0), f0, 35.15625)                             # 全 0：全部清光 → NaN／−Inf，不印警告
        zi = scope_intermod(np.zeros(n0), f0, 35.15625)
        dconly = scope_harmonic(np.r_[1.0, np.zeros(n0 - 1)], f0, 35.15625, 2)      # 只有 DC
    if wl:
        bad.append(f"全 0／只有 DC 的輸入有 {len(wl)} 個警告：{wl[0].category.__name__}: {wl[0].message}")
    if not (math.isnan(z["thd"]) and math.isnan(z["snr"]) and all(v == 0 for v in z["power"]) and math.isnan(zi["toi"])
            and math.isnan(dconly["thd"]) and dconly["n_found"] == 2):
        bad.append(f"全 0／只有 DC 的結果：thd={z['thd']} snr={z['snr']} toi={zi['toi']} dconly={dconly['thd']}/{dconly['n_found']}")
    # 排列等價：實數訊號的 centered 與 twosided 兩邊頻譜取正半邊 → 和 scope 一樣的數字（絕對功率比單邊低 3.01 dB、THD／SFDR 相同）
    rng = np.random.default_rng(3)
    xt = np.cos(2 * np.pi * 2531.7 * np.arange(2048) / 48000) + 0.01 * np.cos(2 * np.pi * 5063.4 * np.arange(2048) / 48000) + 1e-4 * rng.standard_normal(2048)
    w = dsv_spectrum.design_window("hann", 2048)
    r1 = dsv_spectrum.welch(xt, 48000, w, 0, 2048, "onesided")
    rc = dsv_spectrum.welch(xt, 48000, w, 0, 2048, "centered")
    rt = dsv_spectrum.welch(xt, 48000, w, 0, 2048, "twosided")
    h1 = scope_harmonic(r1["power"], r1["f"], r1["rbw"])
    hc = scope_harmonic(rc["power"], rc["f"], rc["rbw"])
    ht = scope_harmonic(rt["power"], rt["f"], rt["rbw"], mode="twosided")
    hp = scope_harmonic(r1["psd"], r1["f"], r1["rbw"], kind="psd")
    hm = scope_harmonic(rc["power"], rc["f"], rc["rbw"], mode="centered")
    if not (np.array_equal(hc["power"], ht["power"]) and hc["thd"] == ht["thd"] and hc["sfdr"] == ht["sfdr"] and hc["snr"] == ht["snr"]
            and hm["thd"] == hc["thd"] and hc["mode"] == "centered" and ht["mode"] == "twosided"):
        bad.append("centered 與 twosided 取正半邊的結果不同")
    if not (abs((h1["power_db"][0] - hc["power_db"][0]) - 10 * math.log10(2)) < 1e-9 and abs(h1["thd"] - hc["thd"]) < 1e-9 and abs(h1["sfdr"] - hc["sfdr"]) < 1e-9):
        bad.append(f"單邊 vs 兩邊：功率差 {h1['power_db'][0] - hc['power_db'][0]:.6f} dB（要 3.0103）、THD 差 {h1['thd'] - hc['thd']:.2e}")
    if not (abs(hp["thd"] - h1["thd"]) < 1e-9 and abs(hp["snr"] - h1["snr"]) < 1e-9 and abs(hp["sfdr"] - h1["sfdr"]) < 1e-9
            and abs((h1["power_db"][0] - hp["power_db"][0]) - 10 * math.log10(r1["rbw"])) < 1e-9):
        bad.append(f"psd 形式：比值要相同、功率列差 10·log10(RBW)＝{10 * math.log10(r1['rbw']):.4f} dB（得 {h1['power_db'][0] - hp['power_db'][0]:.4f}）")
    xc = np.exp(2j * np.pi * 900 * np.arange(2048) / 10000) * (1 + 0.1 * rng.standard_normal(2048))
    rcx = dsv_spectrum.welch(xc, 10000, w, 0, 2048, "onesided")                     # 複數 → welch 自動 centered → 照算（D10）
    hx = scope_harmonic(rcx["power"], rcx["f"], rcx["rbw"])
    if not (hx["mode"] == "centered" and abs(hx["freq"][0] - 900) <= rcx["f"][1] - rcx["f"][0] and math.isfinite(hx["thd"])):
        bad.append(f"複數訊號：mode={hx['mode']} f1={hx['freq'][0]} thd={hx['thd']}")
    check(not bad, "scope 函式的輸入保護（DSV 自訂）：dB 值／複數／2-D／字串／空／1 bin／長度不同／F 不遞增／RBW 0 或 NaN／N 1、100、3.5、'6'／kind、mode 不認得"
                   f"／2^24+1 個 bin（broadcast 不佔記憶體）→ DistortionError（dsv:scope_*:…）；全 0 與只有 DC 的輸入是 NaN、不印警告；"
                   f"實數訊號 centered＝twosided 取正半邊、兩邊比單邊低 3.0103 dB 而 THD／SFDR 相同、psd 形式比值相同且功率列差 10·log10(RBW)；"
                   f"複數訊號照算（基頻 {hx['freq'][0]:.1f} Hz）" + (f"（不合：{'; '.join(bad[:4])}）" if bad else ""))
    check(st["ok"] == st["n"] and st["caps_ok"] == st["caps"] and st["known_ok"] == st["known"],
          f"scope 實測總計：{st['caps']} 個 capture（15 諧波、5 互調）{st['caps_ok']} 個一致，{st['n']} 個數字 {st['ok']} 個在容差內"
          f"（頻率 ±{SCOPE_TOL_HZ:g} Hz、諧波功率／比值 ±{SCOPE_TOL_DB:g} dB、互調 ±{SCOPE_TOL_TOI_DB:g} dB；最大殘差 {st['worst_hz']:.1e} Hz、"
          f"{st['worst_db']:.1e} dB、互調 {st['worst_toi']:.1e} dB）；另 {st['known']} 項已知差異／捨入底，{st['known_ok']} 項和記錄的數字一致")
