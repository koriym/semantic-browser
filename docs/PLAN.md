# Semantic Browser: PoC Implementation Plan

このドキュメントは、Semantic Browserのコンセプトを検証するための、段階的な実装計画を定義します。

## 1. PoCのGoalとNon-Goal

### Goal
- HAL + ALPS + Laya-MLX + HTTP traversal + Semantic Traceという最小構成で、「意味に基づくナビゲーション」というコアコンセプトが技術的に成立することを証明する。
- 数日で完了する規模のPoCを通じて、プロジェクトの仮説を検証する。

### Non-Goal
- GUI、分散実行、高度なグラフDB、自律的なバグ修正、完全なAIエージェントフレームワークなどの構築。
- 本番環境での利用を想定した、堅牢な認証・認可システムの実装。
- 全てのハイパーメディアフォーマットへの対応。
- BEAR.Sundayや他の特定フレームワークへの深い依存。

## 2. 主要な設計判断 (ADRs)

- [ADR-0001: Record Architecture Decisions](./adr/0001-record-architecture-decisions.md)
- [ADR-0002: Python as Implementation Language](./adr/0002-python-as-implementation-language.md)
- [ADR-0003: Decouple Decision Engine](./adr/0003-decouple-decision-engine.md)

## 3. Milestones

### Milestone 1: 静的な世界での自律歩行 (Static World Walker)

- **何を実装するか:**
  - **Mock Server:** 用意済み。`http://127.0.0.1:8791/` で稼働する査読ジャーナルの編集システム（HAL + ALPS）。実装者はこのサーバーのソースを読まない。ALPS は実行時に `rel="profile"` から取得する。記述を書いた者と読む者を分けることが Milestone 3 の前提であり、ソースを読めば自己記述性の検査は自作自演になる。
  - **HTTP Walker:** `httpx` を使い、HALから遷移候補を抽出するクライアント。候補は 2 種類ある。`_links` の各 rel と、`_embedded` 配下の各リソースが持つ `_links.self`。後者は一覧から個別リソースへ進む唯一の手段である。`{id}` を含む templated link は M1 では候補から除外する（展開は Milestone 2）。
  - **Decision Engine Interface:** `choose(links, alps_doc, current_state)` のような、Laya-MLXを呼び出すための小さなインターフェースを定義する。選択肢には rel と `_embedded` の個別リソースが混在しうるので、両者を同じ形で扱えるようにする。
  - **Laya-MLX Connector:** 上記インターフェースの具象クラス。提示された `rel` を `choice` 質問の選択肢として渡し、返る確率分布から遷移を決める。Laya は文字列を生成しないのでパース処理は不要（[docs/laya-mlx.md](./laya-mlx.md)）。
  - **Traversal Loop:** `discover → choose → follow` のループを回すメインロジック。
  - **Semantic Trace (JSONL):** 各ステップの観測結果（現在のURI、利用可能なリンク、選択したリンク、確率分布）をJSONLファイルに記録する。Laya は理由の文章を返さないため、選択の根拠として残せるのは分布そのものである。

- **何が動けば完了か:**
  - CLIから `python main.py <entry_uri> --goal "<達成したいこと>"` を実行すると、Semantic Browserがサーバーを自律的に巡回し、終了条件（ゴール到達、最大ステップ数）を満たす。`choice` はゴールとの照合で選ぶため、ゴールなしでは決定が定義できない。
  - `trace.jsonl` というファイルが生成され、一連の遷移記録が保存されている。

- **そこで何を検証できるか:**
  - HALとALPSだけから、事前知識なしに次の遷移候補を発見できるか。
  - Laya-MLXが、意味情報に基づいて妥当な次の一手を選択できるか。
  - 一連の処理を繰り返すことで、ハイパーメディア空間を自律的に巡回できるか。

### Milestone 2: 副作用と文脈の導入 (Stateful Traversal)

- **何を実装するか:**
  - **Stateful Mock Server:** Mock Serverを拡張し、POST/PUT/DELETEでリソースの状態が変化するようにする（例: メモリ上の辞書でデータを管理）。
  - **Safety Governor:** `unsafe` な遷移をデフォルトでブロックし、`--allow-unsafe` のようなCLIフラグでのみ実行を許可する仕組み。
  - **Context-Aware Decision:** Laya-MLXへの入力に、直前のレスポンスボディを含め、パスパラメータ（例: `/users/{id}`）を動的に解決するロジック。

- **何が動けば完了か:**
  - Semantic Browserが、リソースの作成（POST）→参照（GET）→削除（DELETE）という一連のライフサイクルを、安全装置を介しつつ自律的に実行できる。
  - トレースに、unsafeな操作がスキップされた記録、または許可されて実行された記録が残る。

- **そこで何を検証できるか:**
  - safe/unsafe/idempotentの区別が、自律巡回において有効に機能するか。
  - 文脈（前の状態）を読み解き、動的なパラメータを解決できるか。

### Milestone 3: Semantic Auditの原型 (Proto-Audit)

- **何を実装するか:**
  - **Trace Analyzer:** 生成された `trace.jsonl` を読み込み、意味的な欠陥を検出する分析スクリプト。
  - **Audit Rules:**
    - 「ALPSに定義があるが、`_links` に存在しない遷移」を検出する。
    - 「`_links` に存在するが、ALPSに定義がない遷移」を検出する。
    - Layaが返す確率分布が拮抗していた遷移を「曖昧」としてリストアップする。[docs/laya-mlx.md](./laya-mlx.md) の観測どおり分布は候補集合に依存するので、何をもって曖昧とするかは実装者が定義し、その定義をレポートに明記すること。
  - **Audit Report:** 検出した欠陥を、人間が読める形式（Markdown）で出力する。

- **何が動けば完了か:**
  - `python analyze.py trace.jsonl` を実行すると、モックサーバーのHAL/ALPS定義に含まれる「意味的なギャップ」がレポートとして出力される。

- **そこで何を検証できるか:**
  - Semantic Traceが、単なるHTTPログよりも意味のある行動記録になっているか。
  - トレースを分析することで、アプリケーションの自己記述性の欠陥を発見できるか。

## 4. 技術的不確実性とSpike

- **state と question の設計:** Laya に渡す `state` と `choice` 質問をどう構成すれば、最も安定して「正しい `rel`」が選ばれるか。プロンプトではなく typed question の設計である（[docs/laya-mlx.md](./laya-mlx.md)）。**これは最初に検証すべき最も重要な Spike である。** 同ドキュメントの「観測（未解決）」に、state の書き方と候補集合が結果を動かした実測がある。結論は出ていない。
- **ALPSの対応付け:** ALPSドキュメント（XML/JSON）の descriptor を `choice` の `criteria`（`{ラベル: 説明}`）にどう対応させるか。自然言語への変換ではなく構造の対応付けである。context 上限は 512 トークン（英語チェックポイント）で、instructions・criteria・state のすべてを含む。ALPSプロファイル全体は入らない。
- **記述のない rel の扱い:** `_links` にあって ALPS に記述がない rel を `criteria` にどう載せるか。補完すれば Milestone 3 の検出対象が消える。
