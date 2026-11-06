# GitHub導入：最短手順

1. GitHubにログインし、右上の `+` → **New repository** を選びます。
2. Repository name: **`vet-seminar-radar`**、Visibility: **Public** を選択します。README、`.gitignore`、Licenseの自動追加はすべて **なし** にします。
3. **Create repository** を押します。
4. 新しいリポジトリのURLをChatGPTに知らせてください。GitHub連携が書き込みを認めていれば、この完成パッケージのファイル登録を進められます。
5. ファイル登録後に GitHub **Settings → Secrets and variables → Actions** から `ANTHROPIC_API_KEY` と `SEMINAR_RADAR_CONTACT` を設定します。APIキーの値をチャットや公開ファイルに貼らないでください。
6. **Settings → Pages** から Branch: `main`、Folder: `/(root)` を選んで保存します。
7. **Actions → Vet Seminar Radar → Run workflow** で初回収集を起動します。
8. Actionsログ、`data/run_status.json`、公開Webページを確認します。

**現在の限界**：このChatGPTのGitHub連携は既存リポジトリへのファイル作成・更新はできますが、リポジトリそのものを新設する操作はありません。したがって、1〜3だけGitHub上で実施いただく必要があります。

**セキュリティ**：Pagesは公開サイトです。主催者が公開したイベントの事実データとリンクのみを載せます。スクレイピングした本文やサイト画像、個人情報は登録しません。各サイトの取得可否は初回GitHub Actionsログで検証が必要です。
