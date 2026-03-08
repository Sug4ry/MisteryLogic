# Mystery Logic Analyzer - デプロイガイド

このアプリケーションをGitHub経由でStreamlit Community Cloudにデプロイし、データをGoogle Sheetsに保存・同期するための手順です。

## 1. Google Cloud Platform (GCP) の準備

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセスし、新しいプロジェクトを作成します。
2. **「APIとサービス」 > 「ライブラリ」** から以下のAPIを有効化します。
   - Google Sheets API
   - Google Drive API
3. **「APIとサービス」 > 「認証情報」** を開き、「認証情報を作成」から「**サービスアカウント**」を作成します。
4. 作成したサービスアカウントの「キー」タブから、「新しいキーを作成」 > 「**JSON**」を選択し、ダウンロードします。（このJSONファイルの内容は後で使います）

## 2. Google Spreadsheetの準備

1. Google Driveで新しいスプレッドシートを作成します。
2. スプレッドシートの**共有設定**を開力し、先ほど作成した**サービスアカウントのメールアドレス（xxx@yyy.iam.gserviceaccount.com）に「編集者」権限を付与**します。
3. スプレッドシートのURLから**スプレッドシートキー**（`/d/`と`/edit`の間の英数字）をコピーします。

## 3. GitHubへのプッシュ

このプロジェクトフォルダ内のすべてのファイル（`main.py`, `analyzer.py`, `visualizer.py`, `models.py`, `sheets_db.py`, `requirements.txt`, `DEPLOYMENT.md`）をあなたのGitHubリポジトリにプッシュします。

※ `state.json` や `.streamlit/secrets.toml` 等のファイルはGitに含めないように注意してください。

## 4. Streamlit Community Cloud へのデプロイ

1. [Streamlit Community Cloud](https://share.streamlit.io/) にログインし、「New app」をクリックします。
2. プッシュしたGitHubリポジトリ、ブランチ、メインのファイルパス（`main.py`）を選択します。
3. デプロイ前に、**「Advanced settings」**を開力します。
4. **Secrets** のテキストエリアに、以下の形式で設定を記述します。

```toml
# GEMINI_API_KEYはここで設定するか、アプリ起動後のサイドバーで入力できます
GEMINI_API_KEY = "あなたのGemini APIキー"

# スプレッドシートキー
[gsheets]
spreadsheet_key = "手順2-3でコピーしたスプレッドシートキー"

# サービスアカウントJSONの内容
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
universe_domain = "googleapis.com"
```

※ `[gcp_service_account]` の下には、ダウンロードしたサービスアカウントのJSONファイルの中身をそのまま（ただしTOML形式に合わせて変数化して）貼り付けます。

5. 「Deploy」をクリックします。

これで、モバイル環境や別PCからアクセスしても、データがGoogle Sheetsに保存されるクラウド対応のアプリケーションが完成です！
