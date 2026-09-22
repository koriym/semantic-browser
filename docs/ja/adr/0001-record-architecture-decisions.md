# 1. Record Architecture Decisions

- Status: accepted
- Date: 2026-09-21

## Context

このプロジェクトは、新しい概念を検証するPoCであり、将来にわたって多くの技術的選択が行われることが予想されます。設計上の重要な決定がなされた背景や理由を記録しておかないと、後から「なぜこうなっているのか？」を追跡するのが困難になり、一貫性のない変更が加えられるリスクがあります。

## Decision

私たちは、重要なアーキテクチャ上の決定を、軽量なADR（Architecture Decision Records）として `/docs/adr` ディレクトリに記録することにします。

フォーマットは、Michael Nygard氏の提案するシンプルな形式（Title, Status, Context, Decision, Consequences）に従います。

## Consequences

- **Positive:**
  - 設計の意図が明確になり、将来の開発者（または未来の自分）がコードを理解しやすくなる。
  - 新しいメンバーがプロジェクトの経緯を学ぶための貴重な資料となる。
  - 場当たり的な変更を防ぎ、一貫したアーキテクチャを維持しやすくなる。
- **Negative:**
  - 決定のたびにドキュメントを作成するという、わずかなオーバーヘッドが発生する。
