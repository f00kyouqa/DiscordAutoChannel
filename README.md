# Discord Auto Channel Bot

Discord サーバーのチャンネルを Ollama LLM を使用して自動で作成・整理する Bot です。

## 🌟 機能

- **チャンネル作成提案**: 会話の文脈から必要なチャンネルを AI が自動提案
- **チャンネル整理分析**: 非アクティブなチャンネルを検出し、整理を提案
- **自動サーバー整理**: カテゴリ分類による自動整理
- **管理者向けコマンド**: チャンネルの細かい制御が可能

## 📋 セットアップ

### 前提条件

- Python 3.8以上
- Ollama がインストール・実行中 ([https://ollama.ai](https://ollama.ai))
- Discord Bot Token

### インストール手順

1. **リポジトリをクローン**
```bash
git clone https://github.com/f00kyouqa/DiscordAutoChannel.git
cd DiscordAutoChannel
```

2. **依存パッケージをインストール**
```bash
pip install -r requirements.txt
```

3. **環境設定ファイルを作成**
```bash
cp .env.example .env
```

4. **.env ファイルを編集して、認証情報を設定**

#### Discord Bot Token の取得

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. "New Application" をクリック
3. アプリケーション名を入力して作成
4. 左側メニューの "Bot" をクリック
5. "Add Bot" をクリック
6. "TOKEN" セクションで "Copy" をクリックしてトークンをコピー
7. `.env` ファイルの `DISCORD_TOKEN` に貼り付け

#### Bot の権限設定

1. Developer Portal の "OAuth2" → "URL Generator" に移動
2. 以下のスコープを選択：
   - `bot`
3. 以下の権限を選択：
   - `Manage Channels`
   - `Send Messages`
   - `Read Message History`
   - `Administrator` (推奨)
4. 生成された URL をコピーしてブラウザで開き、サーバーに追加

#### Ollama の設定

1. Ollama をインストール: https://ollama.ai
2. Ollama を起動:
```bash
ollama serve
```

3. モデルをダウンロード (別のターミナルで):
```bash
# Mistral (推奨、軽量で高速)
ollama pull mistral

# または他のモデル
ollama pull neural-chat
ollama pull orca-mini
```

4. `.env` ファイルの `OLLAMA_API_URL` と `OLLAMA_MODEL` を確認

### Bot の起動

```bash
python main.py
```

## 🎮 使用方法

### コマンド一覧

#### `!suggest_channels <context>`
チャンネル作成を提案します。
```
!suggest_channels We need better organization for our development team
```

**詳細:**
- AI が会話の文脈を分析
- 既存チャンネルとの重複を避けて提案
- ボタンで提案されたチャンネルを一括作成可能

#### `!cleanup_analysis`
チャンネル整理の分析を実行します。
```
!cleanup_analysis
```

**詳細:**
- 非アクティブなチャンネルを検出
- 重複するチャンネルを特定
- アーカイブ/削除の推奨を提案

#### `!create_channel <channel_name> [description]`
手動でチャンネルを作成します。
```
!create_channel projects "Project management channel"
```

#### `!auto_organize`
サーバーを自動整理（カテゴリ分類）します。
```
!auto_organize
```

## ⚙️ カスタマイズ

### Ollama モデルの変更

`.env` ファイルの `OLLAMA_MODEL` を変更：

| モデル | サイズ | 速度 | 推奨用途 |
|--------|--------|------|---------|
| mistral | 7B | 高速 | 汎用（推奨） |
| neural-chat | 7B | 高速 | 会話型 |
| llama2 | 7B/13B | 中速 | 複雑な分析 |
| orca-mini | 3B | 最速 | 軽量環境 |

### プロンプトの調整

`main.py` の `OllamaManager` クラス内のプロンプトテンプレートを編集して、AI の提案をカスタマイズできます。

## 🔍 トラブルシューティング

### Ollama に接続できない
```
Ollama API error: Cannot connect to server
```

**解決策:**
```bash
# Ollama が実行中か確認
ollama serve

# ポートが正しいか確認（デフォルト: 11434）
curl http://localhost:11434/api/tags
```

### Bot がオンラインにならない
```
Error: DISCORD_TOKEN が設定されていません
```

**解決策:**
1. `.env` ファイルが存在するか確認
2. `DISCORD_TOKEN` が正しい値か確認
3. Bot のトークンが有効か確認（Discord Developer Portal）

### チャンネル作成権限がない
```
❌ チャンネル作成の権限がありません
```

**解決策:**
1. サーバーでの Bot の権限を確認
2. "Manage Channels" 権限を付与
3. Bot のロールがサーバー管理者より上位か確認

## 📁 プロジェクト構造

```
DiscordAutoChannel/
├── main.py              # メイン Bot スクリプト
├── requirements.txt     # 依存パッケージ
├── .env.example         # 環境変数テンプレート
├── .env                 # 環境変数（.gitignore済み）
└── README.md            # このファイル
```

## 🚀 拡張機能の提案

- [ ] チャンネル使用状況の統計情報
- [ ] 定期的な自動整理スケジューリング
- [ ] スレッド管理機能
- [ ] カテゴリ自動分類
- [ ] メッセージアーカイブ機能
- [ ] ロール連携機能

## 📝 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 🤝 貢献

プルリクエストや Issue は大歓迎です！

## 📞 サポート

問題が発生した場合は、GitHub の Issues セクションで報告してください。
