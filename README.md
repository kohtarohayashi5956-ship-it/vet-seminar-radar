# Vet Seminar Radar — 獣医系セミナー情報レーダー

[Vet Lit Radar](https://kohtarohayashi5956-ship-it.github.io/vet-lit-radar/) と同じ方式で動く、独立した学会・セミナー収集プロジェクトです。

**公開範囲に注意**: GitHub Pages を使うと一覧HTMLはインターネットから閲覧可能です。公開するのはセミナー名、日付、主催者、開催地、料金、公式URLなどの事実情報のみです。サイト本文、画像、AI抽出用キャッシュ、個人情報、参加者データを公開しないでください。選択したセミナーはブラウザ内のローカルストレージで保存され、サーバーには送信されません。

## 実装済み

- 初期ソース: JAHA / Life&Tail / 学際企画 / VETS TECH の4種のアダプター
- VETS ACADEMY公式セミナー一覧の講習カード単位抽出（開催日／オンデマンド配信期間、LIVE・会場型・対象職種、公式個別リンク）。詳細ページの料金・申込締切補完は別工程。アクセス制限時は巡回せずログに記録。
- robots.txt、サイト拒否、3秒以上の巡回間隔を守るHTTPクライアント
- **無料モード（既定）**：JAHAの月別カレンダー、学際企画の年間予定、VETS TECHのRSS記事、Life&Tailの一覧をソース別ルールで抽出。年や開催日の不明な情報は補いません。
- **任意のAI補助**：明示的に有効化した場合のみ、無料抽出0件のページにClaude APIを使用（原文照合あり、有料）。APIキーの登録だけではAIを使用しません。
- JSONの蓄積、同じ講座の重複排除、古い講座の削除
- 月別・分野・職種・地域・料金別の一覧、複数選択、Lark用の告知文の編集・コピー
- 収集先別の巡回件数と失敗理由の記録（`data/run_status.json`）
- 日本獣医麻酔外科学会の地区講習会は、開催日一致を確認できる公式個別ページから開催時刻・受講料区分・事前申込締切を補完（最大6詳細ページ）。学術集会の録画配信期限やキャンセル期限は申込締切として扱いません。
- 開催日・時刻・料金・締切・分野・対象職種・公式URLの記載率を `data/run_status.json` の `data_quality` に保存（正確性の検証率ではありません）
- GitHub Actionsによる週2回の巡回（月・木 06:00 JST）とGitHub Pages更新
- `python -m unittest discover -s tests` によるオフライン自動テスト（日時誤認の回帰テストを追加）

**未確認**: GitHub Actions実環境から各公式サイトへの取得成功率・robots.txtへの適合性、個々の取得データの正確性・網羅性は、実行ログと主催者ページで確認してください。テストはオフラインの模擬HTMLを使用しており、実サイト巡回を保証しません。

## 2026-11-09 巡回許可の実測確認

- 2026-11-09 12:08 JSTの GitHub Actions 巡回で PEPPY・EDUWARD Press・VETS ACADEMY の公式一覧はいずれも共通 Fetcher の robots.txt 判定で取得不可となり、各0件でした。
- これら3サイトを定期巡回対象から無効化しました。個別の解析コードと単体テストは保持しますが、許諾または正規の配信手段が確認できるまで使用しません。
- **有効な自動巡回先は13サイトです。** 設定上の追加によって収集可能サイトが16に増えたわけではありません。既存の82件についても、フィールド記載率と個別の事実確認率は異なります。
- SEMINAR_RADAR_CONTACT が未設定のため、相手サイトへ公開してよい連絡用アドレスを GitHub Actions の secret に設定することを推奨します（ソースに直書きしない）。

## GitHubでの初回導入（v1.1以降）

リポジトリ `kohtarohayashi5956-ship-it/vet-seminar-radar` は作成済みです。

1. **Settings → Pages** で `Deploy from a branch` / `main` / `/(root)` を選択し、公開を有効化します。
2. **Actions → Vet Seminar Radar → Run workflow** で一度手動実行します。APIキー不要で、無料抽出が動きます。
3. 実行ログと `data/run_status.json` を確認し、抽出件数・アクセス不可サイトを確認します。
4. `SEMINAR_RADAR_CONTACT` には、巡回先へ示してよいメールアドレスを GitHub **Settings → Secrets and variables → Actions** から任意で登録できます（推奨）。連絡先は公開ソースに記述しないでください。

**無料利用には `ANTHROPIC_API_KEY` の作成・登録・決済設定は不要です。** GitHub Actionsで実行するだけで無料ルール抽出を行います。

有料のAI補助は、無料抽出が0件だったページに限定されます。利用したい場合のみ、`ANTHROPIC_API_KEY` をGitHub ActionsのSecretsに登録し、`SEMINAR_RADAR_USE_AI` をGitHub ActionsのVariablesで `1` に設定します。料金が発生する可能性があるため、キーの設定だけでは有効化されません。ローカルでは `python run.py --ai` でも指定できます。

GitHub Pagesの公開URL（Pages設定後）：`https://kohtarohayashi5956-ship-it.github.io/vet-seminar-radar/`

## ローカルでの確認

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -q
python run.py --demo --out demo.html   # 架空データのUI確認（公開しない）
python run.py --offline                # 保存データから index.html を再生成
python run.py                         # 実サイトを無料ルールで巡回（APIキー不要）
python run.py --ai                    # 必要なときのみAI補助を許可（キー必須・従量課金）
python validate_public.py             # 公開HTMLの基本安全・形式検証
```

`--only jaha,gakusai` による巡回先制限、`--months 2`、`--debug` も利用可能です。**`--debug` はページ本文を `cache/` に記録します。公開・配布しないでください。**

## VETS ACADEMYのアクセス制限（2026-11-07）

GitHub Actionsの実巡回で公式一覧 `https://academy.eduone.jp/seminar` は robots.txt で不許可と判定され、0件でした。講習カードの専用抽出コードとオフラインテストは保持しますが、定期巡回は無効化しています。制限の回避を行わず、正式な許可または利用可能な公式RSS・API等が確認できるまで再有効化しません。

## PEPPYのアクセス制限（2026-11-07）

PEPPYの公式セミナー一覧は GitHub Actions の共通 Fetcher により robots.txt で取得不可と判定されました。収集コードとテストは残しますが、定期巡回は無効化しています。アクセス制限の回避は行いません。公式の許可、API、RSS等の別経路が確認されるまでは再有効化しません。

## 今回の品質拡張

- JAHAの複数日開催講義では、本文に西暦付きで全日程が列記され、同じ年・同じ月日を含む個別「パート」「講義」等の時間範囲が一意の場合のみ、日程別の時刻を補完します。受付時間・キャンセル情報・別年度の情報は除外します。
- `data/run_status.json` の `quality_by_source` に、公開済みイベントを主たる収集先ごとに集計した記載件数と割合を出力します。未掲載項目を優先して改善するための指標で、独立した事実確認ではありません。

## 運用と品質上の注意

- 収集サイトは独自HTMLのため、URL変更・サイト改修・アクセス制限で抽出失敗が起こり得ます。失敗時はエラーログに記録し、拒否は回避しません。
- `verified` はタイトルや抜粋と取得本文との機械的照合であって、開催日・料金・締切の人手確認済みという意味ではありません。告知前に主催者ページを必ず確認してください。
- 新着・更新の検知は現在 `data/events.json` の蓄積で実現しています。申込取消・変更・延期等の検出は取得サイトの情報に依存します。
- `data/extract_cache.json` は任意AIモード専用です。GitHub Actionsのキャッシュに保存して再抽出を減らし、Gitリポジトリには含めません。
- ローカルの `manual_events.csv` に書いた情報は、公開リポジトリにコミットすると公開されます。個人情報を入れないでください。
- 初期URLと取得対象はユーザー提供のソースリストを基準に設定しています。39件の候補は `docs/source_candidates.md` に記録しています。このうちコード化済みなのは4巡回先です。未実装の候補を完了とみなさないでください。
- GitHub Actionsでの実行スケジュールはベストエフォートです。定刻からずれる場合があります。

## 構成

- `run.py` — 実行と監査ログ
- `config.py` — 対象サイト、期間、APIモデル、アクセス間隔
- `sources.py` — 公式サイトごとのページ構造アダプター
- `fetcher.py` — robots.txt・間隔・拒否処理
- `free_extract.py` — **無料**のソース別ルール抽出
- `extract.py` — 任意の有料AI補助と原文照合、非公開キャッシュ
- `merge.py` — 重複除去と蓄積
- `template.html`, `render.py` — 単一HTML UI生成
- `validate_public.py` — 公開前の形式安全チェック
- `data/events.json` — 公開可能な事実データ
- `data/run_status.json` — 公開可能な収集状態
- `data/manual_events.csv` — 手動登録のテンプレート（公開情報のみ）
- `.github/workflows/seminar-radar.yml` — 定期実行

参照先: [JAHA](https://www.jaha.or.jp/seminar-calendar/)、[Life&Tail](https://life-tail.com/)、[学際企画](https://www.gakusai.co.jp/doubutu/seminar-comingup/)、[VETS TECH](https://vets-tech.jp/)。

## 2026-11-06 日時抽出の品質修正

- **Life&Tail**: 一覧の個々の講座カードにある `2026.12.01 20:00〜21:30` 等の日時を、同じカードからのみ抽出します。前後の講座の日時が混入する問題を修正しました。
- **JAHA**: 日付とセミナーをカレンダーの同じ表行で関連付ける処理を追加しました。サイト側の表示形式によっては抽出0件になる場合があるため、巡回ログを確認します。
- **VETS TECH**: 記事URLと公開日、申込締切を開催日と混同しないように変更し、RSSが省略版なら公的な詳細記事本文も取得します（robots.txtに従います）。
- **既存の誤データ**: サイトの巡回が成功してイベントを抽出できた場合に限り、同じ収集元の古いレコードを今回の結果と置き換えます。失敗・0件の場合は既存データを保護します。
- **表示**: 当月に予定が見つからなくても、次の開催月へ移動できるボタンを設けました。
- **品質確認**: テスト実行は `python -m unittest discover -s tests -q`。実サイトの最新情報に関してはGitHub Actionsの `data/run_status.json` と掲載元URLの照合が必要です。
