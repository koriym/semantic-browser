# Semantic Browser

> A browser that follows meaning, not routes.

Semantic Browserは、ハイパーメディアアプリケーションを自律的にナビゲートするための、新しい種類のマシンクライアントです。

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

## 現状 (Status)

現在、このプロジェクトは **Proof of Concept (PoC) - Stage 1** にあります。

Stage 1の目標は、Pythonで実装された静的なモックHAL APIサーバーを対象に、以下のコアループが機能することを証明することです。

`discover → understand → choose → follow → record`

詳細な実装計画については、[docs/PLAN.md](./docs/PLAN.md)を参照してください。

## 将来のビジョン: Semantic Audit

このプロジェクトの最終的な目標は、単なる「ブラウザ」を作ることではありません。Semantic Browserが収集した「Semantic Trace」を分析し、アプリケーションの自己記述性（Self-descriptiveness）を検証する **「Semantic Audit」** ツールとしての価値を提供することです。

Semantic Auditは、以下のような問いに答えます。

- **Completeness:** ALPSに記述されているすべての遷移が、実際にHALの `_links` として提供されているか？
- **Clarity:** 各遷移の `rel` やALPSの記述は、機械が一意に解釈できるほど明確か？
- **Consistency:** ALPSの記述と、実際のHTTPメソッドやレスポンスは一致しているか？
- **Validity of Semantic Variables:** パスパラメータやリクエストボディのフィールドは、ALPSで意味的に定義され、HALで実際に提供されているか？

これにより、Semantic Browserは「意味的に不自然なstate transition」や「ALPSの宣言と実際のresponseの不整合」を検出し、API設計者に具体的なフィードバックを提供する、ハイパーメディアAPIの品質保証ツールへと進化します。
