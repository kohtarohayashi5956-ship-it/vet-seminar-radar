# Vet Seminar Radar 無料モード初期設定

- リポジトリは作成済みです。Vet Lit Reader は変更しません。
- **Claude APIキーは不要**。無料モードはAPI呼び出しを行いません。
- [Pages設定](https://github.com/kohtarohayashi5956-ship-it/vet-seminar-radar/settings/pages) から main / /(root) でGitHub Pagesを有効化してください。
- [Actions](https://github.com/kohtarohayashi5956-ship-it/vet-seminar-radar/actions) の Vet Seminar Radar → Run workflow を実行し、抽出状況と data/run_status.json を確認します。
- 連絡先は Secrets の SEMINAR_RADAR_CONTACT に登録（任意、ただし推奨）。
- 有料AIを明示的に使う場合のみ Secret ANTHROPIC_API_KEY と Variable SEMINAR_RADAR_USE_AI=1 を設定してください。キーだけではAIを呼びません。

模擬HTML上のテストに合格しても、実サイトでの取得・収集精度はまだ未検証です。掲載内容は必ず主催者サイトで確認してください。
