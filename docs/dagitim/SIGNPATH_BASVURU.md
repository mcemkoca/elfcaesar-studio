# SignPath Foundation — ücretsiz açık kaynak kod imzalama başvurusu

Başvuru: https://signpath.org/apply (form; e-posta ile dönüş yapılır). Koşullar: OSI onaylı lisans (MIT ✓), herkese açık depo ✓,
GitHub Actions ile depodan derleme (✓ `.github/workflows/windows-installer.yml`), kötü amaçlı/PUA içermeme, proje sahibinin
2FA'lı GitHub hesabı. Onaylanırsa sertifika "SignPath Foundation" adına düzenlenir ve imzalama GitHub Actions içinde yapılır.

## Formda istenebilecek alanlar — hazır yanıtlar
- Project name: ElfCaesar Studio
- Repository: https://github.com/mcemkoca/elfcaesar-studio
- Homepage: https://mcemkoca.github.io/elfcaesar-studio/
- License: MIT
- Maintainer: Dante (GitHub: mcemkoca)
- Build system: GitHub Actions (windows-latest), PyInstaller + Inno Setup
- Artifacts to sign: ElfCaesarStudio.exe, ElfCaesarNativeHost.exe, ElfCaesarStudio-<version>-Setup.exe
- Short description (EN): ElfCaesar Studio is a free, open-source, fully offline Windows application for file and folder
  encryption, end-to-end encrypted messages, Ed25519 digital signatures, a password manager with a browser extension, and
  local detection of personal data (Turkish KVKK / GDPR). It has no servers, accounts or telemetry. We currently sign releases
  with a self-issued certificate and an Ed25519 release manifest; users see SmartScreen warnings, which is the main obstacle
  for a security tool. A trusted signature would let users verify that the installer was built from this public repository.
- Why should users trust it: public source, automated tests (pytest on Windows/Linux), CodeQL, Bandit, pip-audit, gitleaks and
  OpenSSF Scorecard in CI, private vulnerability reporting enabled, signed SHA256SUMS on every release.

## Onay sonrası (ben yaparım)
`windows-installer.yml` iş akışına `signpath/github-action-submit-signing-request` adımı eklenir; imzalı Setup sürüm sayfasına konur.
