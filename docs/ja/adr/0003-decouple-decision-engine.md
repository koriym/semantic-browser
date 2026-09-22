# 3. Decouple Decision Engine

- Status: accepted
- Date: 2026-09-21

## Context

Semantic Browserのコア機能は、利用可能なaffordanceの中から次の行動を「選択」することです。この選択ロジックには、当初 `laya-mlx` を利用します。将来的に生成LLM（GPT-4, Claudeなど）や異なるアプローチのエンジンに差し替える可能性も考えられます。

ただしこれは上位互換への置き換えではありません。`laya-mlx` は文章を生成せず、提示した選択肢の確率を返します（[docs/laya-mlx.md](../laya-mlx.md)）。生成LLMに差し替えると、選択肢外の出力を防ぐ仕組み、返答のパース、理由文字列の扱いといった、`laya-mlx` には存在しない関心事が加わります。インターフェースの背後に隠せる差ではないため、差し替えの際は Trace の形式と Audit の前提も見直す必要があります。

意思決定のロジックが、HTTP通信やHALのパースといったコアロジックと密結合していると、エンジンの差し替えが困難になり、プロジェクトの柔軟性が損なわれます。

## Decision

意思決定エンジンを、Semantic Browserのコアロジックから **明確に分離** します。

具体的には、以下のような抽象インターフェース（ABC: Abstract Base Class）を定義します。

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class DecisionEngine(ABC):
    @abstractmethod
    def choose_next_action(
        self,
        current_representation: Dict[str, Any],
        available_links: List[Dict[str, Any]],
        alps_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        利用可能なリンクの中から、次に実行すべきアクションを1つ選択する。

        Returns:
            選択されたリンクの辞書。選択できない場合はNoneを返す。
        """
        pass
```

`LayaMlxDecisionEngine` のような具象クラスがこのインターフェースを実装します。コアロジックは、このインターフェースにのみ依存します。

## Consequences

- **Positive:**
  - **交換可能性:** 新しい意思決定エンジンを、コアロジックを変更することなく容易に追加・交換できる。
  - **テスト容易性:** テスト時には、意思決定エンジンをモックオブジェクトに置き換えることができ、コアロジックの単体テストが容易になる。
  - **関心の分離:** HTTP通信、ハイパーメディア解釈、意味的決定という関心事が分離され、コードの見通しが良くなる。
- **Negative:**
  - 小さなインターフェースと具象クラスを定義するための、わずかな初期コストが発生する。
