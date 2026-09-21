# Laya-MLX

意思決定エンジンとして使うライブラリの事実。設計判断はここに書かない。

https://github.com/mizorewww/laya-mlx · Apache-2.0 · `pip install laya-mlx`

## 何であって、何でないか

**生成モデルではない。** bidirectional encoder が state と typed question を
同時に符号化し、decision head が確率を返す。

```
state + typed question → bidirectional encoder → decision heads → probabilities
```

- **出力トークンは 0。** 文章も JSON も生成されない
- したがって**パースする文字列がない**。返るのは Python の dict
- したがって**理由（reason）は得られない**。得られるのは確率分布
- したがって**プロンプト設計ではない**。設計対象は state の書き方と question の定義

`temperature`、`max_tokens`、文法制約、ストリーミングといった概念は存在しない。

## API

```python
import laya_mlx as laya

agent = laya.load("aac6fef/laya-mlx", dtype="float16")
result = agent.predict(state, questions)
```

`state` はテキスト、dict、または会話リスト。
`questions` は `{名前: 質問定義}`。質問は独立に、バッチで評価される。

### 質問の型は 3 つ

| type | 指定するもの | 返るもの |
| --- | --- | --- |
| `choice` | `criteria`: `{ラベル: 説明}` または ラベルのリスト | 各ラベルの確率と選択 |
| `score` | `criteria`: 低→高に並べたレベルのリスト | 期待レベル（0 始まり）と確率 |
| `noul` | なし | P(true) |

`choice` は**提示したラベル以外を返さない**。候補外の選択肢は構造上ありえない。

### 実際の戻り値

```python
result = agent.predict(
    "Goal: list all books.",
    {"rel": {"type": "choice",
             "instructions": "Which link should I follow next?",
             "criteria": {"books": "The complete collection of books.",
                          "authors": "Every author with at least one book.",
                          "index": "The entry page of the API."}},
     "done": {"type": "noul", "instructions": "Has the goal already been reached?"}},
)
```

```python
{'model': 'laya-rl-agent',
 'answers': {
   'rel':  {'type': 'choice', 'choice': 'books', 'confidence': 0.4822,
            'probabilities': {'books': 0.808, 'index': 0.154, 'authors': 0.038},
            'action': {'act_probability': 1.0}},
   'done': {'type': 'noul', 'noul': 0.1029, 'confidence': 0.8971,
            'action': {'act_probability': 1.0}}},
 'usage': {'input_tokens': 126, 'output_tokens': 0}}
```

`confidence` は温度較正済み。`usage.input_tokens` で context 消費を確認できる。

## チェックポイントと制限

| モデル | encoder | パラメータ | context | 用途 |
| --- | --- | ---: | ---: | --- |
| `aac6fef/laya-mlx` | ModernBERT-large | 421M | **512** | 英語 |
| `aac6fef/laya-multilingual-mlx` | mmBERT-base | 322M | **1024** | 多言語 |
| `aac6fef/laya-typed-decisions-mlx` | ModernBERT-large | 421M | **1024** | typed-decisions |

**context には instructions・criteria・state のすべてが含まれる。**
ALPS プロファイル全体を渡す設計は 512 トークンに収まらない。

Apple Silicon、Python 3.11+、macOS 14+。初回 `load` で重みを取得する。

## 速度とメモリ

M3 Max 実測（英語 421M、FP16、モデルロードを除く）。

| | |
| --- | --- |
| 1 問（短文）P50 | 13.4 ms |
| 2 問同時（本プロジェクトの `rel` + `done`） | 約 51 ms |
| ピーク MLX 割り当て | 944 MiB |

生成 LLM と違い、decode 速度・prefill 速度という律速は存在しない。

## 観測（未解決）

`docs/PLAN.md` の Spike に対応する測定。**結論ではなく観測**。
再現コードを付す。判断は実装者が下すこと。

### state に URI を含めると選択が変わる

ゴールも候補も同一で、state 先頭の `At /index.` の有無だけを変えた。

| state | 1 位 |
| --- | --- |
| `At /index. Goal: list all books.` | `index` 0.912 |
| `Goal: list all books.` | `books` 0.943 |

`index` の説明文を書き換えても順位は変わらない（`index` 0.906）。
ラベルを `option_1` 等に置き換えると 0.873 → 0.422 まで下がるが順位は変わらない。

### 候補集合を変えると勝者が変わる

ゴール「Norwegian Wood を書いたのは誰か」、state に URI を含めない。

| 候補 | 1 位 |
| --- | --- |
| books / authors / index | `books` 0.627 |
| books / authors | `authors` 0.601 |

無関係に見える候補を外すと順位が入れ替わる。

### 多段の遷移は安定している

本を開いた後の state で `author` を選ぶ確率。

| state に "author" の語 | rubric | 結果 |
| --- | --- | --- |
| あり | `"author"`（ALPS 未記述時の代替） | 0.966 |
| なし | `"author"` | 0.919 |
| あり | 記述あり | 0.989 |
| なし | 記述あり | 0.963 |

```python
import laya_mlx as laya
a = laya.load("aac6fef/laya-mlx")
crit = {"books": "The complete collection of books in the library.",
        "authors": "Every author who has written at least one book.",
        "index": "The entry page of the API."}
for s in ["At /index. Goal: list all books.", "Goal: list all books."]:
    r = a.predict(s, {"q": {"type": "choice",
                            "instructions": "Which link should I follow next?",
                            "criteria": crit}})
    print(s, r["answers"]["q"]["probabilities"])
```

## 上流との関係

`convaiinnovations/laya` の独立した MLX 移植。重み・質問形式・温度較正・
出力スキーマは上流のまま。学習とファインチューニングは上流の範囲。
