# Microsoft Agent Framework Workshop 

## 内容一覧
1. AI Foundry エージェントとのチャット
2. エージェントと MCP ツールの連携
3. マルチエージェント協調
4. 自作 MCP サーバを構築

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

---
## ステップ1: AI Foundry エージェントとのチャット
AI Foundry上の Bing エージェントとのチャット(`app.py`)
- 目的: [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)を利用して AI Foundry 上のエージェントを実行

1. 取得 & 移動
	```bash
	git clone https://github.com/hatasaki/Microsoft-Agent-Framework-Workshop.git
	cd Azure-Agent-Framework-Workshop/Agent_framework
	```
2. ライブラリを入れる
	```bash
	pip install -r requirements.txt
	```
3. VS Code で Agent_framework フォルダーの下に`.env` ファイルを作成し下記の内容を保存。
   各プレースフォルダーの```AI Foundry project endpoint```および```your model deployment name```はAI Foundryポータルから確認。```your agent id```にはBingエージェントのAgent IDを登録

	```env
	AZURE_AI_PROJECT_ENDPOINT=<your AI Foundry project endpoint>
	AZURE_AI_MODEL_DEPLOYMENT_NAME=<your model deployment name>
	USE_AZURE_CLI_CREDENTIAL=true
	CREATE_NEW_AGENT=false
	WORKSHOP_AGENT_ID=<your agent id>
	```
4. Azure にログイン (Azure AI Foundryへの接続に必要)
   下記の Azure CLI コマンドを実行して Azure にログイン
   ブラウザーが利用できない環境ではデバイスコードによる認証を実施
	```bash
	az login
	```   
5. 起動
	```bash
	python app.py
	```
6. ブラウザで http://localhost:5000 を開き、質問してみる (例: 「今日の天気を調べて」)。
7. [optional] `.env` の CREATE_NEW_AGENT=true に設定し、適宜コード内のAGENT_INSTRUCTIONSや環境変数WORKSHOP_AGENT_INSTRUCTIONSを書き換えて、新規エージェントの作成を実施

うまくいかないとき:
- エラーが「Required environment variable ... is not set」→ `.env` のスペル漏れ
- 何も返ってこない → ネットワーク制限やプロキシの可能性。再試行後も不可なら講師へ相談

---
## ステップ2: エージェントと MCP ツールの連携
エージェントから [Microsoft 公式ドキュメント検索 MCP サーバ](https://learn.microsoft.com/en-us/training/support/mcp) を使って情報を引き出す (`app_mcp.py`)
- 目的: エージェントが外部ツール (MCP) 経由で Microsoft 公式ドキュメントを検索し回答品質を上げる

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

> もしツールが使われない場合: 質問を具体化 (「Microsoft Agent FrameworkのドキュメントのMCPサンプルコードを取得して、そのURLも教えて」など) すると呼び出されやすい

---
## ステップ3 : マルチエージェント協調
3つの役割 (調査/執筆/レビュー) で協調するマルチエージェントを構築 (`app_multiagent.py`)
- 目的: 複数エージェントが強調して複雑なタスクを実行

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
## ステップ4: 自作 MCP サーバを構築
自作 MCP ツールを [Azure Functions の MCP トリガー](https://learn.microsoft.com/ja-jp/azure/azure-functions/functions-bindings-mcp-trigger?tabs=attribute&pivots=programming-language-python)で公開し、エージェントから利用する (`MCP_function`の MCP サーバアプリをデプロイして `app_mcp.py` で接続)
- 目的: 自分専用の社内API/ユーティリティを MCP 化してエージェントから安全に活用

1. VS CodeにAzure Tools拡張機能をインストール（未インストールの場合）
2. VS Code 左側の Azure アイコンをクリック(サインインを未実施の場合はサインインを実施)
3. VS Code の terminal を開き、下記のコマンドを実行して Function App 用の VS Code ウインドウを開く(カレントディレクトリが```Agent_framework```であることを確認)
	```bash
	code ../MCP_function
	```
4. オープンしたウインドウで、Azure拡張機能の Functions を右クリックして```Create Azure Function App in Azure...(Advanced)``` オプションを選択し、下記の構成で Functions アプリを作成:
   - Functionの名前: 一意の名前例: `mcp-time-tools-<自分の名前>-<ランダムな4桁の数字>`
   - プラン: Flex Consumption
   - location: Japan East
   - Runtime: python 3.10
   - Memory: 512
   - instance count: デフォルト値のまま
   - リソースグループ: 自分のリソースグループを指定
   - authentication type: Secrets
   - storage account: create new storage account
   - name of the new storage account: デフォルト値のまま
   - application insights: Create new Application Insights
   - name of the new Application Insights: デフォルト値のまま
6. MCP サーバアプリのデプロイ: 作成された Function Apps に右クリックして```Deploy to Function App...```を実行（確認ウインドウが表示されたら```Deploy```をクリック)
7. デプロイ完了後は Azure Portal で該当する Function App をオープン。MCP サーバの URL は下記のフォーマット（Azure Portal 等で確認できる Function Apps のURLにパス ```/runtime/webhooks/mcp```が追加必要な点に注意 
	```
	https://<your Function app name>.azurewebsites.net/runtime/webhooks/mcp
	```
8. Azure Portal の Function App の左メニューの 関数 → アプリキー を選択し、mcp_extension の右側のキーをコピー
9. 元の VS Code のウインドウ（Micoroft-Agent-Framework-Workshop フォルダがルートとなっているもの)に移動
10. キーを`.env` へ追記:
	```env
	MCP_FUNCTION_URL=https://<your Function app name>.azurewebsites.net/runtime/webhooks/mcp
	MCP_FUNCTION_KEY=<コピーしたキー>
	```
11. アプリの起動:
	```bash
	python app_mcp.py
	```
12. ブラウザーでテスト質問: 「シアトルの現在時刻を教えて」など

おすすめ
- Application Insights 有効化 (監視/例外収集)すると、デバッグ等が容易

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
## 参考リンク
- Azure AI Foundry: https://learn.microsoft.com/azure/ai-studio/
- Microsoft Agent Framework: https://github.com/microsoft/agent-framework
- Azure Functions MCP: https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-mcp?pivots=programming-language-python

---
## Contributing
This project has adopted the Microsoft Open Source Code of Conduct. For more information see the Code of Conduct FAQ or contact opencode@microsoft.com with any additional questions or comments.

