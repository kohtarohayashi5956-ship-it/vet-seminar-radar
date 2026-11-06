# Vet Seminar Radar — 獣医系セミナー情報レーダー

[Vet Lit Radar](https://kohtarohayashi5956-ship-it.github.io/vet-lit-radar/) と同じ方式で動く、独立した学会・セミナー収集プロジェクトです。

**公開範囲に注意**: GitHub Pages を使うと一覧HTMLはインターネットから閲覧可能です。公開するのはセミナー名、日付、主催者、開催地、料金、公式URLなどの事実情報のみです。サイト本文、画像、AI抽出用キャッシュ、個人情報、参加者データを公開しないでください。選択したセミナーはブラウザ内のローカルストレージで保存され、サーバーには送信されません。

## 実装済み

- 初期ソース: JAHA / Life&Tail / 学際企画 / VETS TECH の4種のアダプター
- robots.txt、サイト拒否、3秒以上の巡回間隔を守るHTTPクライアント
- **無料ルール抽出（既定）**：JAHA、Life&Tail、学際企画、VETS TECHの公開ページをサイト別に解析。開催日が不明な場合は推測せず未入力にします。
- **任意の有料AI補助**：無料抽出0件のページのみ、明示的な設定があればClaude APIを使用
- JSONの蓄積、同じ講座の重複排除、古い講座の削除
- 月別・分野・職種・地域・料金別の一覧、複数選択、Lark用の告知文の編集・コピー
- 収集先別の巡回件数と失敗理由の記録（`data/run_status.json`）
- GitHub Actionsによる週2回の巡回（月・木 06:00 JST）とGitHub Pages更新
- `python -m unittest discover -s tests` によるオフライン自動テスト

**未確認**: GitHub Actions実環境から各公式サイトへの取得成功率・robots.txtへの適合性、Anthropic API実課金・実抽出結果、実データの網羅性は、実行ログで確認してください。元ZIPの24件はモックテストで、実サイト巡回の保証ではありません。

## GitHubでの初回導入（1回だけ）

1. GitHubで **新規の空リポジトリ `vet-seminar-radar` をPublicで作成** します（既存の `vet-lit-radar` は変更しません）。READMEなどの初期化ファイルは作らないでください。
2. 本ZIP内のファイルとフォルダをすべて、リポジトリのトップへアップロードします。`seminar-radar/` という親フォルダを残さず、`.github/workflows/seminar-radar.yml` がトップから参照されるようにします。隠しファイル `.nojekyll` と `.gitignore` もアップロードしてください。
3. **Settings → Secrets and variables → Actions → New repository secret** で、`ANTHROPIC_API_KEY` は**無料モードでは不要**です。別途、`SEMINAR_RADAR_CONTACT` に自身が外部サイトへ連絡先として示してよいメールアドレスを登録します。鍵をGitHubのファイルに直接書かないでください。
4. **Settings → Pages** で **Deploy from a branch / main / /(root)** を選択して保存します。公開URLは `https://kohtarohayashi5956-ship-it.github.io/vet-seminar-radar/` になる想定です。公開はPagesの設定と成功を確認してからです。
5. **Actions → Vet Seminar Radar → Run workflow** を手動実行し、結果のログと `data/run_status.json` をチェックします。GitHub Pagesの反映も確認します。
6. 巡回設定・モデル名・頻度は `config.py` と `.github/workflows/seminar-radar.yml` を編集します。サイトの利用規約・robots.txtを再確認してから有効化してください。

> 重要：無料モードはAPIキーなしで動きます。Claude APIを使用する場合のみ `ANTHROPIC_API_KEY` (Secrets) と `SEMINAR_RADAR_USE_AI=1` (Variables) を設定してください。キーの登録だけでは利用しません。

## ローカルでの確認

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -q
python run.py --demo --out demo.html   # 架空データのUI確認（公開しない）
python run.py --offline                # 保存データから index.html を再生成
python run.py                         # 無料で実サイトを巡回（APIキー不要）
python run.py --ai                    # 必要時だけ有料AI補助を許可（キー必須）
python validate_public.py             # 公開HTMLの基本安全・形式検証
```

`--only jaha,gakusai` による巡回先制限、`--months 2`、`--debug` も利用可能です。**`--debug` はページ本文を `cache/` に記録します。公開・配布しないでください。**

## 運用と品質上の注意

- 収集サイトは独自HTMLのため、URL変更・サイト改修・アクセス制限で抽出失敗が起こり得ます。失敗時はエラーログに記録し、拒否は回避しません。
- `verified` はタイトルや抜粋と取得本文との機械的照合であって、開催日・料金・締切の人手確認済みという意味ではありません。告知前に主催者ページを必ず確認してください。
- 新着・更新の検知は現在 `data/events.json` の蓄積で実現しています。申込取消・変更・延期等の検出は取得サイトの情報に依存します。
- `data/extract_cache.json` はGitHub Actionsの非公開キャッシュに保存してAPI使用量を抑えます。Gitリポジトリには含めません。
- ローカルの `manual_events.csv` に書いた情報は、公開リポジトリにコミットすると公開されます。個人情報を入れないでください。
- 初期URLと取得対象はユーザー提供のソースリストを基準に設定しています。39件の候補は `docs/source_candidates.md` に記録しています。このうちコード化済みなのは4巡回先です。未実装の候補を完了とみなさないでください。
- GitHub Actionsでの実行スケジュールはベストエフォートです。定刻からずれる場合があります。

## 構成

- `run.py` — 実行と監査ログ
- `config.py` — 対象サイト、期間、APIモデル、アクセス間隔
- `sources.py` — 公式サイトごとのページ構造アダプター
- `fetcher.py` — robots.txt・間隔・拒否処理
- `free_extract.py` — 無料のサイト別ルール抽出
- `extract.py` — 明示的に有効化したときだけ有料AI補助
- `merge.py` — 重複除去と蓄積
- `template.html`, `render.py` — 単一HTML UI生成
- `validate_public.py` — 公開前の形式安全チェック
- `data/events.json` — 公開可能な事実データ
- `data/run_status.json` — 公開可能な収集状態
- `data/manual_events.csv` — 手動登録のテンプレート（公開情報のみ）
- `.github/workflows/seminar-radar.yml` — 定期実行

参照先: [JAHA](https://www.jaha.or.jp/seminar-calendar/)、[Life&Tail](https://life-tail.com/)、[学際企画](https://www.gakusai.co.jp/doubutu/seminar-comingup/)、[VETS TECH](https://vets-tech.jp/)。
