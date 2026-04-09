<p align="center">
  <img src="icon.png" width="128" alt="AirQRT logo">
</p>

<h1 align="center">AirQRT</h1>

<p align="center">
  <b>QRコードだけで Windows PC 間のファイルを完全オフライン転送</b><br>
  ネットワーク不要。ケーブル不要。USBメモリ不要。画面とカメラだけ。
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">中文</a> · <b>日本語</b> · <a href="README.ru.md">Русский</a>
</p>

---

## 仕組み

1台のPCが**送信側**として、画面にQRコードを高速表示します。  
もう1台のPCが**受信側**として、カメラで画面を読み取ります。

データは圧縮・分割され、**Reed-Solomon FEC（前方誤り訂正）** で保護されます。カメラが一部のフレームを読み落としても、ファイルは完全に復元できます。

## ダウンロード

**すぐ使いたい方へ** — ビルド済み `.exe` をダウンロード（Python不要）：

> **[⬇ AirQRT をダウンロード (Windows .exe)](../../releases/latest)**

解凍してダブルクリックするだけです。

## 機能

- **完全オフライン** — Wi-Fi、Bluetooth、インターネット接続不要
- **ワンクリックGUI** — ダークターミナル風インターフェース、ドラッグ＆ドロップ対応
- **FECエラー回復** — GF(256)上のReed-Solomonコーディングによるフレーム欠損耐性
- **ブロック間インターリーブ** — 連続フレーム欠損を分散し回復力を向上
- **FPS調整可能** — カメラの読取速度に合わせて動的に調整
- **ブロック指定再送** — 欠損ブロックをクリックして再送信
- **多言語UI** — English、中文、Русский、日本語

## クイックスタート（ソースから実行）

### 前提条件

- Python 3.9+
- 受信側にWebカメラが必要

### インストール

```bash
git clone https://github.com/YOUR_USERNAME/AirQRT.git
cd AirQRT
pip install -r requirements.txt
```

### 実行

```bash
python app.py
```

GUIが開き、**送信**と**受信**の2つのタブが表示されます。

#### 送信

1. **送信**タブに切り替え
2. **ファイル追加**をクリック（またはドラッグ＆ドロップ）
3. 必要に応じてFPSを調整
4. **[ 送信開始 ]** をクリック

#### 受信

1. **受信**タブに切り替え
2. カメラを送信側の画面に向ける
3. **[ 受信開始 ]** をクリック
4. 転送完了後、ファイルは `received_files/` に保存されます

## 実行ファイルのビルド

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "AirQRT" --icon=icon.ico --hidden-import=windnd app.py
```

`.exe` は `dist/` フォルダに生成されます。

## FECエラー回復

Reed-Solomonコードに基づくブロックレベルFECを使用：

| パラメータ | デフォルト値 |
|-----------|------------|
| ブロックあたりデータフレーム数 | 50 |
| 冗長率 | 30% |
| QRコード誤り訂正レベル | M (15%) |

**例：** 50データフレームのブロックから15の冗長フレームが生成されます（合計65フレーム）。  
そのうち**任意の** 50フレームを読み取れば、全データが復元できます。

## パフォーマンスガイド

| ファイルサイズ | 所要時間（目安） |
|-------------|--------------|
| 10 KB | 約30秒 |
| 50 KB | 約2分 |
| 100 KB | 約4分 |

小さなファイル（500 KB未満）に最適です。大きなファイルは圧縮してから転送してください。

## パラメータ調整

`sender.py` で以下のパラメータを変更できます：

```python
CHUNK_SIZE = 300            # データシャードあたりのバイト数（小さいほど読取りやすい）
FRAME_FPS = 20              # デフォルトFPS
FEC_DATA_SHARDS = 50        # FECブロックあたりのデータフレーム数
FEC_REDUNDANCY_RATIO = 0.30 # 30%の冗長オーバーヘッド
QR_ERROR_LEVEL = 'M'        # L / M / Q / H
```

## トラブルシューティング

| 問題 | 解決方法 |
|------|---------|
| カメラが開かない | `receiver_camera.py` の `CAMERA_INDEX` を `1` または `2` に変更 |
| 読取率が低い | `CHUNK_SIZE` を減らす、FPSを下げる、`FEC_REDUNDANCY_RATIO` を上げる |
| 大きなファイルが遅い | ファイルを先に圧縮（zip/7z）してから転送 |

## プロジェクト構成

```
├── app.py               # GUIアプリケーション (Tkinter)
├── sender.py            # ファイル圧縮、QRエンコード、FECフレーミング
├── receiver_camera.py   # カメラスキャン、QRデコード、FEC回復
├── fec_utils.py         # GF(256)上のReed-Solomonコーデック
├── icon.png             # アプリアイコン
├── build_exe.bat        # ワンクリックEXEビルドスクリプト
├── requirements.txt     # Python依存関係
└── received_files/      # 受信ファイル出力ディレクトリ
```

## ライセンス

本プロジェクトはオープンソースです。詳細は [LICENSE](LICENSE) をご覧ください。

---

<p align="center"><i>USBメモリが見つからない、そんな時のために。</i></p>
