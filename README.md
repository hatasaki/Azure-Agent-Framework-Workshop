# Azure Agent Framework Workshop 

## 内容一覧
1. AI Foundry エージェントとのチャット
2. エージェントと MCP ツールの連携
3. [optional] マルチエージェント協調
4. [optional] 自作 MCP サーバを構築

---
## 事前準備 (インストール & アカウント)
| item | description |
|-------------|------------|
| Python 3.10+ | アプリ (Flask) 実行用 |
| Git / VS Code | コード入手と編集、実行確認 |
| Azure アカウント | Azure AI Foundry でエージェント利用 |
| Bing エージェント作成済み | 検索付きエージェントをすぐ試すため |
| Azure CLI で `az login` 済み | ローカルから安全に認証して API 呼び出し |
| [optional] VS Code Azure Tools 拡張 | Functions のデプロイを簡単操作 |

### 最小構成
```env
AZURE_AI_PROJECT_ENDPOINT=https://<your-project>.eastus.ai.azure.com
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4.1
CREATE_NEW_AGENT=true
USE_AZURE_CLI_CREDENTIAL=true

# 公式ドキュメント検索 MCP を使う例
MCP_FUNCTION_URL=https://learn.microsoft.com/api/mcp
```

### 自作 Azure Functions MCP を使う例
```env
MCP_FUNCTION_URL=https://<function_app>.azurewebsites.net/runtime/webhooks/mcp
MCP_FUNCTION_KEY=<your_function_key>
```

---
## ステップ1: AI Foundry エージェントとのチャット
AI Foundry上の Bing エージェントとのチャット(`app.py`)
目的: Microsoft Agent Frameworkを利用して AI Foundry 上のエージェントを実行

1. 取得 & 移動
	```bash
	git clone https://github.com/<your_org_or_user>/Azure-Agent-Framework-Workshop.git
	cd Azure-Agent-Framework-Workshop/Agent_framework
	```
2. ライブラリを入れる
	```bash
	pip install -r requirements.txt
	```
3. `.env` ファイルを作成し下記の内容を保存
```env
AZURE_AI_PROJECT_ENDPOINT=<your AI Foundry project endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<your model depolyment name>
USE_AZURE_CLI_CREDENTIAL=true
CREATE_NEW_AGENT=false
WORKSHOP_AGENT_ID=<your agent id>
```
4. 起動
	```bash
	python app.py
	```
5. ブラウザで http://localhost:5000 を開き、質問してみる (例: 「今日の天気を調べて」)。
6. [optional] `.env` の CREATE_NEW_AGENT=true に設定し、適宜コード内のAGENT_INSTRUCTIONSや環境変数WORKSHOP_AGENT_INSTRUCTIONSを書き換えて、新規エージェントの作成を実施

うまくいかないとき:
- エラーが「Required environment variable ... is not set」→ `.env` のスペル漏れ
- 何も返ってこない → ネットワーク制限やプロキシの可能性。再試行後も不可なら講師へ相談

---
## ステップ2: エージェントと MCP ツールの連携
エージェントから Microsoft 公式ドキュメント検索 MCP を使って情報を引き出す (`app_mcp.py`)
目的: エージェントが外部ツール (MCP) 経由で Microsoft 公式ドキュメントを検索し回答品質を上げる

1. `.env` に以下を追加
	```env
	MCP_FUNCTION_URL=https://learn.microsoft.com/api/mcp
	```
	認証情報(キー)は不要 (公開エンドポイント)
2. アプリを起動
	```bash
	python app_mcp.py
	```
3. ブラウザで http://localhost:5000 を開き、質問:
	- 「Azure Functions とは？」
	- 「Azure Container Apps と Functions の違いを簡単に」など
4. ツール結果が統合され、ドキュメントに基づいた説明を返答

仕組み簡単説明:
- `app_mcp.py` が `MCP_FUNCTION_URL` を読み取り MCP ツールを登録。
- エージェントは必要と判断したときに MCP 経由で検索しレスポンスへ組み込み

> もしツールが使われない場合: 質問を具体化 (「Azure Functions の価格モデルは？」など) すると呼び出されやすい

---
## ステップ3 [optional]: マルチエージェント協調
3つの役割 (調査/執筆/レビュー) で協調するマルチエージェントを構築 (`app_multiagent.py`)
目的: 複数エージェントが強調して複雑なタスクを実行

1. 起動
	```bash
	python app_multiagent.py
	```
2. ブラウザで http://localhost:5000 を開き、質問 例: 「最新AI動向をまとめて」
3. Researcher → Writer → Reviewer → Writer → Reviewer → Writer の順でエージェントを実行し返答（数十秒応答に時間を要する）
4. Azure AI Foundry ポータルに移動しエージェント画面でBingエージェントのスレッドログをクリック
5. 最新のスレッドログを開くと複数エージェントの対話履歴が確認可能(プレイグラウンドに移動すると会話形式で表示)
6. [optional] エージェントの実行順序を変更


---
## ステップ4: [optional] 自作 MCP サーバを構築
自作 MCP ツールを Azure Functions に公開し、エージェントから利用する (`MCP_function/` をデプロイして `app_mcp.py` で接続)
目的: 自分専用の社内API/ユーティリティを MCP 化してエージェントから安全に活用

1. VS CodeにAzure Tools拡張機能をインストール（未インストールの場合）
2. VS Code 左側の Azure アイコンをクリック(サインインを未実施の場合はサインインを実施)
3. Azure拡張機能の Functions を右クリックし Deploy を選択
4. Advanced オプションを選択し、下記の構成で Functions アプリを作成:
   プラン: Flex Consumption / OS: Linux / リソースグループ: 自分のリソースグループ
   Functionの名前: 一意の名前例: `mcp-time-tools-<自分の名前>-<任意の4桁の数字>`
5. デプロイ完了後 URL 例:
	```
	https://mcp-time-tools-XXXX.azurewebsites.net/runtime/webhooks/mcp
	```
6. 「App Keys」から Function Key をコピー
7. `.env` へ追記:
	```env
	MCP_FUNCTION_URL=https://mcp-time-tools-XXXX.azurewebsites.net/runtime/webhooks/mcp
	MCP_FUNCTION_KEY=<コピーしたキー>
	```
8. アプリの起動:
	```bash
	python app_mcp.py
	```
9. ブラウザーでテスト質問: 「シアトルの現在時刻を教えて」など

おすすめ
- Application Insights 有効化 (監視/例外収集)すると、デバッグ等が容易


---
## うまく行かないときのチェックリスト
| 問題 | 原因例 | 対処 |
|------|--------|------|
| 環境変数未設定エラー | `.env` のスペル/配置ミス | ファイル名が `.env` か再確認、再起動 |
| 認証失敗 | `az login` 未実行 | ターミナルで `az login` |
| MCP が反応しない | URL が間違い / 質問が曖昧 | URL再確認, 具体的な質問に変更 |
| Functions 接続 401 | キー未設定 | `.env` の KEY 記述 & 再起動 |
| タイムゾーンエラー | `Asia/Tokyo` のような IANA 名でない | 正しい IANA 名へ修正 |
| 公式 Docs 検索弱い | 質問が短すぎる | 何を知りたいか具体化 (例: 「料金計算の仕組みは？」) |

---
## 次にできる発展
- 社内 REST API を MCP ラッパー化
- Bicep / Terraform で IaC 化し再現性を確保
- GitHub Actions で自動デプロイ
- Key Vault で機密値管理 / Private Endpoint で閉域化

---
## 環境変数

| 変数名 | 必須 | 説明 |
|--------|-------|---------------|
| `AZURE_AI_PROJECT_ENDPOINT` | ◎ | Azure AI Foundry プロジェクトの URL (ポータルで確認) |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | ◎ | 利用するモデルのデプロイ名 (例: gpt-4o-mini) |
| `CREATE_NEW_AGENT` | 任意 | 毎回新しく作るなら `true` / 既存再利用なら `false` |
| `WORKSHOP_AGENT_ID` | 条件 | 既存を再利用する時に Azure 画面からコピーして記入 |
| `USE_AZURE_CLI_CREDENTIAL` | 任意 | `true` なら `az login` 済み資格情報を使う |
| `MCP_FUNCTION_URL` | Step2以降 | MCP ツールのURL (公式Docsか自作Functions) |
| `MCP_FUNCTION_KEY` | 自作Functions時 | Functions のキー。公式Docs検索には不要 |
| `WORKSHOP_AGENT_NAME` | 任意 | 表示用名前。未指定なら既定値 |
| `WORKSHOP_AGENT_INSTRUCTIONS` | 任意 | エージェントへ最初に与える「性格/役割」説明文 |
| (option) Writer/Reviewer 系 | Step3 | マルチエージェント時の追加設定 |

.envファイルに環境変数を保存

---
## 参考リンク
- Azure AI Foundry: https://learn.microsoft.com/azure/ai-studio/
- MCP 仕様: https://learn.microsoft.com/api/mcp
- Azure Functions Flex Consumption サンプル: https://github.com/Azure-Samples/functions-quickstart-javascript-azd/

---
## Contributing
This project has adopted the Microsoft Open Source Code of Conduct. For more information see the Code of Conduct FAQ or contact opencode@microsoft.com with any additional questions or comments.

