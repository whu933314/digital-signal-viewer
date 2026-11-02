#!/bin/bash
# 建立本機專用的 code signing 鑰匙圈與自簽憑證（.signing/，已在 .gitignore）。build_mac.sh 看到它就用固定簽章，
# 重新打包後 macOS 的隱私權限（例如「文件」）不會每次重問。全程不用登入密碼、不改登入鑰匙圈、不跳授權視窗。
# 已經有 .signing/ 就不動（換憑證＝macOS 會當成新 App 重問一次權限）。
set -e
cd "$(dirname "$0")/.."
D=.signing
if [ -f "$D/dsv-signing.keychain-db" ]; then echo "已存在 $D/dsv-signing.keychain-db，不重建"; exit 0; fi
mkdir -p "$D"; chmod 700 "$D"
openssl rand -hex 24 > "$D/kc.pass"; chmod 600 "$D/kc.pass"; KP=$(cat "$D/kc.pass")
cat > "$D/cert.cnf" <<'CNF'
[req]
distinguished_name = dn
x509_extensions = ext
prompt = no
[dn]
CN = DSV Local Code Signing
[ext]
basicConstraints = critical,CA:false
keyUsage = critical,digitalSignature
extendedKeyUsage = critical,codeSigning
subjectKeyIdentifier = hash
CNF
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$D/key.pem" -out "$D/cert.pem" -days 3650 -config "$D/cert.cnf" 2>/dev/null
openssl pkcs12 -export -legacy -inkey "$D/key.pem" -in "$D/cert.pem" -name "DSV Local Code Signing" -out "$D/sign.p12" -passout pass:"$KP" 2>/dev/null
security create-keychain -p "$KP" "$(pwd)/$D/dsv-signing.keychain-db"
security set-keychain-settings "$(pwd)/$D/dsv-signing.keychain-db"
security unlock-keychain -p "$KP" "$(pwd)/$D/dsv-signing.keychain-db"
security import "$D/sign.p12" -k "$(pwd)/$D/dsv-signing.keychain-db" -P "$KP" -T /usr/bin/codesign >/dev/null
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$KP" "$(pwd)/$D/dsv-signing.keychain-db" >/dev/null
rm -f "$D/key.pem" "$D/sign.p12"
echo "建好：$D/dsv-signing.keychain-db（憑證 $(openssl x509 -in "$D/cert.pem" -noout -fingerprint -sha1 | sed 's/.*=//')）"
