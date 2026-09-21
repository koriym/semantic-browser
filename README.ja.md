# Semantic Browser

> A browser that follows meaning, not routes.

[English](./README.md) | 日本語

Semantic Browser は、ハイパーリンクを意味によってブラウズします。

ハイパーメディアアプリケーションを自律的にナビゲートするための、新しい種類のマシンクライアントです。

従来のWebブラウザが「人間がrepresentationを読み、linkを選んで次へ進む」のに対し、Semantic Browserは「機械がrepresentationとその意味（semantics）を解釈し、提示されたaffordanceの中から次のactionを選択する」ことを目指します。

## コアコンセプト

このプロジェクトの中核は、AI Agentのように自由な推論でactionを「発明（invent）」するのではなく、サーバーから提示されたhypermedia controlsの中から意味に基づいて「選択（choose）」するという、制約駆動型のアプローチにあります。

```
representation
    +
hypermedia controls
    +
semantic description (ALPS)
    ↓
semantic decision
    ↓
choose transition
    ↓
next representation
```

## 基本原則

- **Discovery over Configuration:** Semantic Browserは単一のエントリーURIから始まり、HAL (`_links`) やALPS (`rel="profile"`) といった標準的なハイパーメディア情報を通じて、アプリケーションの構造を自己発見します。事前のルートテーブルやAPI定義は不要です。
- **Server-Driven Affordances:** クライアントはURLやactionを発明しません。常にサーバーが提供する選択肢の中から、現在の状態と目的に最も適したものを選択します。
- **Safety First:** デフォルトでは `unsafe` なHTTPメソッド（POST, PUT, DELETEなど）を実行しません。`safe` および `idempotent` な遷移を優先します。

## 意思決定エンジン

`semantic decision` の実装には [Laya-MLX](https://github.com/mizorewww/laya-mlx) を使います。

これは文章を生成するモデルではありません。state と選択肢を受け取り、**各選択肢の確率を返すエンコーダ**です。出力トークンは 0。したがって「選択肢以外を答える」ことが構造上できません。

基本原則の *Server-Driven Affordances* — クライアントはactionを発明しない — が、規約ではなくモデルの形として実装されます。

API・制限・実測は [docs/laya-mlx.md](./docs/laya-mlx.md) を参照してください。

## 現状 (Status)

**Proof of Concept — Stage 1 完了。**

`discover → understand → choose → follow → record` のループは成立しました。
一方で Semantic Audit にはもう一つ前提が要ることが分かっています。

- ブラウザは HAL と ALPS だけで、事前知識なしに巡回できる
- 監査のうち**決定的な検査**（記述の欠落、到達可能性）はそのまま使える
- **意味に基づく判定は、計器そのものの校正が先に要る**

測定と経緯は [docs/M1-RESULT.md](./docs/M1-RESULT.md)、
実装計画は [docs/PLAN.md](./docs/PLAN.md) を参照してください。

## 将来のビジョン: Semantic Audit

このプロジェクトの最終的な目標は、単なる「ブラウザ」を作ることではありません。Semantic Browserが収集した「Semantic Trace」を分析し、アプリケーションの自己記述性（Self-descriptiveness）を検証する **「Semantic Audit」** ツールとしての価値を提供することです。

Semantic Auditは、以下のような問いに答えます。

- **Completeness:** ALPSに記述されているすべての遷移が、実際にHALの `_links` として提供されているか？
- **Clarity:** 各遷移の `rel` やALPSの記述は、機械が一意に解釈できるほど明確か？
- **Consistency:** ALPSの記述と、実際のHTTPメソッドやレスポンスは一致しているか？
- **Validity of Semantic Variables:** パスパラメータやリクエストボディのフィールドは、ALPSで意味的に定義され、HALで実際に提供されているか？

これにより、Semantic Browserは「意味的に不自然なstate transition」や「ALPSの宣言と実際のresponseの不整合」を検出し、API設計者に具体的なフィードバックを提供する、ハイパーメディアAPIの品質保証ツールへと進化します。
