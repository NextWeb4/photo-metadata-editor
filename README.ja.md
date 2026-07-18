<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/English-0969da?style=flat-square" alt="English"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-c8102e?style=flat-square" alt="简体中文"></a>
  <a href="README.ja.md"><img src="https://img.shields.io/badge/%E6%97%A5%E6%9C%AC%E8%AA%9E-8250df?style=flat-square" alt="日本語"></a>
</p>

# Photo Metadata Editor

同梱 ExifTool を利用して EXIF、XMP、IPTC、QuickTime メタデータを編集する、Windows 向けオフラインデスクトップアプリです。

[![最終コミット](https://img.shields.io/github/last-commit/NextWeb4/photo-metadata-editor?style=flat-square)](https://github.com/NextWeb4/photo-metadata-editor/commits/main)
[![リポジトリサイズ](https://img.shields.io/github/repo-size/NextWeb4/photo-metadata-editor?style=flat-square)](https://github.com/NextWeb4/photo-metadata-editor)
[![GitHub Stars](https://img.shields.io/github/stars/NextWeb4/photo-metadata-editor?style=flat-square)](https://github.com/NextWeb4/photo-metadata-editor)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
[![MIT ライセンス](https://img.shields.io/github/license/NextWeb4/photo-metadata-editor?style=flat-square)](LICENSE)

## 機能

- JPG、PNG、TIFF、HEIC、HEIF、WEBP、MOV、MP4 などの一般的な形式を開きます。
- タイトル、説明、キーワード、作成者、著作権、撮影日時、カメラ、ソフトウェア、GPS、場所を編集します。
- 形式、寸法、画素数、レンズ、ISO、焦点距離、絞り、シャッター速度などを読み取り専用で表示します。
- カメラ/GPS プリセット、ダークテーマ、ローカル OCR の日付検出、ファイル日時同期を提供します。
- 中国語/英語 UI を切り替え、設定を `%APPDATA%\PhotoMetadataEditor\settings.json` に保存します。
- 既定で ExifTool の `_original` バックアップを保持し、復元前に検証済み `_before_restore` コピーを作ります。
- ExifTool の書き込み概要と重要フィールドの再読み込みを検証し、終了コードだけで成功と判断しません。
- ファイルはローカルで処理し、画像やメタデータをアップロードせず、実行時に OCR モデルを取得しません。

## 動作要件と互換性

- **OS:** 同梱 ExifTool ランタイム、ドラッグ＆ドロップ対応デスクトップアプリ、パッケージスクリプト、MSI は Windows 向けです。
- **Python:** `pyproject.toml` は Python 3.11 以上を要求し、デスクトップ依存として `tkinterdnd2` を宣言しています。
- **ExifTool:** ソース実行とパッケージ版は `vendor/exiftool/` に格納された Windows ランタイムを使用します。パッケージ版では `PATH` 上の実行ファイルへ差し替えません。
- **任意の OCR:** 利用可否はローカルの Windows OCR 言語、Tesseract、またはインストール済み PaddleOCR リソースに依存します。クラウドへのフォールバックや実行時のモデル取得はありません。
- **メディアへの書き込み:** 読み取れる形式でも、すべてのタグを書き込めるとは限りません。コンテナー、ファイル権限、ExifTool のタグ表に依存します。

## リリース版のインストール

[GitHub Releases](https://github.com/NextWeb4/photo-metadata-editor/releases) から次を取得します。

- `PhotoMetadataEditor-0.1.2-win64.msi`: Windows インストーラー。
- `PhotoMetaEditor-portable.zip`: ポータブル版。すべて展開して `PhotoMetaEditor.exe` を実行します。
- `SHA256SUMS.txt`: リリースファイルのチェックサム。

`PhotoMetaEditor.exe` だけを取得しないでください。ZIP 内の隣接する `_internal` と `exiftool` が必要です。信頼されたコード署名証明書を設定しない公開ビルドは未署名のため、Windows が不明な発行元として警告する場合があります。実行前に SHA-256 チェックサムを照合してください。

## ソースから実行

`pyproject.toml` は Python 3.11 以上を指定しています。デスクトップ依存は `tkinterdnd2` で、ExifTool Windows ランタイムは `vendor/exiftool/` に含まれます。

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
$env:PYTHONPATH = "src"
.venv\Scripts\python -m photo_meta_editor
```

OCR は任意機能です。利用可能なローカルバックエンドは、ソース環境の Windows OCR、Tesseract、PaddleOCR リソースに依存します。モデルの自動取得やクラウド OCR への画像送信は禁止されています。

## エディターの使い方

1. ファイルを選択するか、画像/動画をウィンドウへドロップします。
2. 左側で対応フィールドを編集し、右側で生メタデータを確認、絞り込みます。
3. 必要に応じてカメラ/GPS プリセット、ローカル OCR、ファイル日時同期を使います。
4. **Save changes** を選びます。初回書き込みでは既定で `_original` を保持します。
5. 元に戻す場合は確認内容を読んでから **Restore backup** を使います。

対応コンテナーでも、実際の書き込み可否はファイル、権限、ExifTool の能力に依存します。概要と再読み込みの検証を通過した場合だけ成功として報告します。

## 書き込みと復元の安全性

- 通常の書き込みでは、利用者が明示的に変更しない限り ExifTool の `_original` バックアップを保持します。
- 復元前に `_before_restore` コピーを作成して検証し、同時に変更されたファイルを検出し、検証失敗時はロールバックします。
- GPS の緯度と経度は一組の値です。片方だけ更新された位置情報を残さず、両方を同時に書き込むか消去します。
- ExifTool の引数は構造化入力として渡します。Unicode パス、空白、バックスラッシュ、複数行の値をコマンド構文として解釈させません。
- ExifTool が `0 image files updated` と報告した場合、終了コードが 0 でも成功ではありません。概要を確認し、重要フィールドを再読み込みします。

## プロジェクト構成

| パス | 役割 |
| --- | --- |
| `src/photo_meta_editor/app.py` | Tkinter UI とアプリ調整 |
| `src/photo_meta_editor/exiftool.py` | ExifTool の安全な起動と読み書き |
| `src/photo_meta_editor/fields.py` | フィールド/タグの対応、正規化、検証 |
| `src/photo_meta_editor/ocr.py` | ローカル OCR 検出と日付解析 |
| `src/photo_meta_editor/presets.py` | カメラ/GPS プリセット |
| `src/photo_meta_editor/i18n.py` | 中国語/英語 UI 文言 |
| `src/photo_meta_editor/settings.py` | ローカル設定 |
| `vendor/exiftool/` | 同梱 ExifTool Windows ランタイム |
| `scripts/` | パッケージ、署名、ライセンス収集、プライバシー、パス安全性 |
| `tests/` | 標準 `unittest` の回帰テスト |

## テスト

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

## ビルド

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

リリースビルドはコンパイル確認、単体テスト、EXE/MSI/ZIP 作成、第三者ライセンス確認、プライバシースキャンを実行します。確認済み出力は次のとおりです。

- `dist\PhotoMetaEditor\PhotoMetaEditor.exe`
- `dist\PhotoMetadataEditor-0.1.2-win64.msi`
- `dist\PhotoMetaEditor-portable.zip`

信頼された証明書を持つ発行者は `PHOTO_META_EDITOR_SIGNING_CERT_THUMBPRINT` を設定できます。未設定時は未署名のままとし、信頼済み署名を装う自己署名証明書は作りません。

## プライバシーと配布

- バックグラウンドアップロード、テレメトリー、クラウド OCR、実行時モデル取得を追加しないでください。
- パッケージ化された EXE/MSI は同梱 ExifTool だけを使い、`PATH` や `PHOTO_META_EDITOR_EXIFTOOL` で置換しません。
- 配布物には収集済みのプロジェクトおよび第三者通知を含めます。
- プライバシースキャンはローカルパスなどを確認しますが、ライセンス完全性確認の代わりではありません。

依存関係の詳細は [`docs/THIRD_PARTY.md`](docs/THIRD_PARTY.md) と [`docs/OPEN_SOURCE_AUDIT.md`](docs/OPEN_SOURCE_AUDIT.md) を参照してください。

## プロジェクトの状態と制限

- バージョン 0.1.2 の MSI とポータブルリリース成果物が文書化された、公開中の Windows アプリです。
- OCR は任意のローカル機能です。バックエンドが利用できない場合は、ネットワークサービスへ密かに切り替えず、利用不可として扱います。
- 静止画像と QuickTime コンテナーでは読み書きできる範囲が異なり、特に GPS と日付タグは形式に依存します。
- 信頼された証明書が未設定なら公開成果物は未署名です。SHA-256 は内容の完全性を確認しますが、発行者の身元までは証明しません。
- リポジトリには第三者の ExifTool ランタイムが含まれます。プロジェクトの MIT License は、同梱コンポーネントの通知やライセンスを置き換えません。

## コントリビューション

Tkinter の調整は `app.py`、プロセス起動は `exiftool.py`、フィールド規則は `fields.py`、OCR 検出は `ocr.py`、パッケージ処理は `scripts/` に保ってください。タグ、日時、GPS、QuickTime、バックアップ、引数処理を変更した場合は実ファイルを使う回帰テストを追加し、全 `unittest` を実行します。パッケージ変更ではパス安全性、プライバシー、ランタイム削減、ライセンス収集の検査を維持します。現在リント/フォーマットコマンドは定義されていません。

## 作者

- [HaoXiang Huang](https://nextweb4.github.io/)
- [didadida1688@gmail.com](mailto:didadida1688@gmail.com)

## ライセンス

プロジェクトのソースは [MIT License](LICENSE) です。ExifTool と Windows ランタイムを含む同梱コンポーネントには各自のライセンスが適用されます。再配布時は通知を保持してください。
