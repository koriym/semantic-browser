# 2. Python as Implementation Language

- Status: accepted
- Date: 2026-09-21

## Context

Semantic BrowserのPoCを実装するための言語を選択する必要があります。候補としては、Python, TypeScript (Node.js), Goなどが考えられます。

## Decision

PoCの実装言語として **Python** を選択します。

理由は以下の通りです。

1.  **Decision Engineとの親和性:** 当初の意思決定エンジン候補である `laya-mlx` がPythonライブラリであり、MLXフレームワークもPythonエコシステムの一部です。これにより、エンジンの統合が最もスムーズに行えます。
2.  **HTTPとデータ処理:** `httpx` や `pydantic` といった成熟したライブラリがあり、非同期HTTP通信や構造化データの扱いが容易です。
3.  **迅速なプロトタイピング:** 動的型付けと豊富な標準ライブラリにより、PoCのような小規模で変化の速い開発に適しています。

## Consequences

- **Positive:**
  - `laya-mlx` との統合が容易になり、PoCの中心的な課題に集中できる。
  - 開発速度が向上し、短期間での仮説検証が可能になる。
- **Negative:**
  - 静的型付け言語（TypeScriptやGo）に比べて、大規模化した際の保守性やパフォーマンスで不利になる可能性がある。ただし、PoCの段階ではこのリスクは限定的であると判断します。
