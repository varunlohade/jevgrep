# jevgrep

**Search code by meaning.** Ask "where do we retry failed payments?" and get `file:line` ranges in about 1–2 seconds, even when the code never uses the words in your question.

```
$ cd flutter/packages/flutter
$ jevgrep "When I turn on the slow-motion debug switch, all my app's animations crawl. Where does the app stretch out the clock each frame gets?" -k 3
  0.86  lib/src/scheduler/binding.dart:1108-1167  Duration _adjustForEpoch(Duration rawTimeStamp) {
  0.56  lib/src/scheduler/binding.dart:1086-1107  void resetEpoch() {
  0.49  lib/src/scheduler/binding.dart:40-82  set timeDilation(double value) {
  grep  lib/animation.dart:1-150  ...
```

One of the 20 benchmark questions, run on the Flutter framework (694 files). The question never says "time dilation" or "epoch", and the first pick is the function that scales each frame's timestamp. Not every question goes this well: see [Results](#results). Read the top few.

One Python file, standard library only. It uses TypeSafe's [**jev**](https://docs.typesafe.ai) choice model: it never generates text, it only picks the best option from a list.

## When to use it

| Use it for | Why |
|---|---|
| **Code you don't know yet**: new job, new repo, open source you want to patch | You don't know what the code calls things. Type the behaviour, not the name. |
| **Questions with no obvious keyword** ("where do we give up on a request that takes too long?") | It reads function names and every identifier inside, not just the words you typed. |
| **A 2-second first look before a grep hunt** | If the top 5 has it, you're done. If not, you've lost 2 seconds. |
| **Scripts and tools** | `--json` returns ranked hits with scores. |

| Don't use it for | Why |
|---|---|
| **Replacing grep in an AI coding agent** | In our tests, an agent with grep was right 20/20 every time (see below). |
| **Finding *every* place something happens** | It returns the top 5, not all matches. Use `grep -rn`. |
| **Code you may not share** | It sends code summaries (names, identifiers, short strings) to TypeSafe. |
| **Anything that must never miss** | Its confidence score does not tell you when it is wrong. Check the code it points to. |

## Install

```sh
curl -o ~/.local/bin/jevgrep https://raw.githubusercontent.com/varunlohade/jevgrep/main/jevgrep
chmod +x ~/.local/bin/jevgrep
export TYPESAFE_API_KEY=...        # or: echo <key> > ~/.config/jevgrep/key
```

## Use

```sh
jevgrep "<question>" [dir]          # default dir: current folder
jevgrep "<question>" [dir] -k 10    # more results
jevgrep "<question>" [dir] --json   # for scripts and agents
```

The first run in a repo reads and summarises every source file, then caches the result in `~/.cache/jevgrep`. After that, only changed files are read again.

## How it works

1. **Chunk.** Every source file is split into whole declarations (functions, classes, and methods in Dart/Java/Kotlin). Doc comments stay attached, and tiny header pieces merge into the next one.
2. **Summarise.** Each chunk becomes its signature plus every identifier and short string used inside. That is how a question about a "not acceptable status" can find code that only says `validateStatus`.
3. **Grep lane (free, local).** Question words are matched against identifier parts (`imageSharpness` → image, sharpness). The best 8 chunks always join the candidates.
4. **Folders, then files: one yes/no per entry.** jev gives each folder (big repos) and each file its own probability, and jevgrep keeps *everything* above a threshold instead of betting on a top few. Requests run in parallel.
5. **Pick.** jev picks the likeliest chunks from the summaries.
6. **Check on real code.** The top 8 candidates (plus grep's best 2) are judged again on their actual, line-numbered code: "does this passage really do what the search describes?" That yes/no probability sets the final order.

Steps 4 and 6 are adapted from [jegrep](https://github.com/can1357/jegrep) by Can Bölük (MIT): absolute yes/no judgments, keep-above-threshold, parallel batches, and verifying on real content. jevgrep checks whole functions instead of fixed line blocks, which is why its ranges are tighter.

## Results

Each test used an answer key of "where is X?" questions written by one agent. Some had an obvious keyword; the rest were phrased by behaviour, with words that don't appear in the code. A separate agent that never saw the key answered with grep, timed. All scores come from **held-out** questions that were never used for tuning.

**Big public repo: the Flutter framework** (`packages/flutter`, 694 files, 566k lines), 20 held-out questions: 6 keyword, 7 behaviour, 7 vague. The questions and answers are in [`bench/questions_flutter.json`](bench/questions_flutter.json), so you can rerun this yourself.

| | jevgrep v4 (current) | jevgrep v3 | [jegrep](https://github.com/can1357/jegrep) 0.1.3 |
|---|---|---|---|
| Found | **18/20** | 17/20 | 16/20 |
| First pick right | 14/20 | 10/20 | **15/20** |
| Vague questions, first pick | **4/7** | 1/7 | **4/7** |
| Lines to read to reach the hit (median) | **77** | 103 | 395 |
| Time per question | 4.1 s | 3.0 s | **1.8 s** |

v4 finds the most answers and points at the tightest ranges. jegrep is right on the first pick one more time out of 20, and it is about 2× faster.

Earlier tests used v3:

**Small repo:** a 27-file, 10k-line Swift app, 20 questions.

| | AI agent + grep | jevgrep v3 | jegrep |
|---|---|---|---|
| Found | 20/20 | **20/20** | 16/20 |
| First pick right | 20/20 | 17/20 | 16/20 |
| Lines to read (median) | – | **35** | 162 |
| Time | 7.9 s | **~1 s** | 1.2 s |

**Big repo:** a 1,967-file, 362k-line Flutter app, 20 questions. Measured before the fix that made jevgrep see Dart/Java/Kotlin methods, so jevgrep's numbers here are a floor.

| | AI agent + grep | jevgrep v3 | jegrep |
|---|---|---|---|
| Found | **20/20** | 16/20 | 12/20 |
| First pick right | **20/20** | 10/20 | 12/20 |
| Keyword questions found | 8/8 | 8/8 | 8/8 (all first pick) |
| Behaviour questions found | 12/12 | **8/12** | 4/12 |
| Time | 9.7 s | 2.2 s | 1.5 s |

**What this means:**
- v3 beat jegrep on behaviour questions and pointed at tighter ranges. jegrep was better at keyword questions, which is what v4's yes/no and real-code steps took from it.
- Against an AI agent with grep, both lose on accuracy. An agent needs only about 2 grep calls to find a single-answer question.
- The case jevgrep is built for is untested: **a person** new to a codebase, hunting by hand. That comparison is next.

**Does it make an AI coding agent faster?** We gave one fresh agent grep only. We gave another the rule "grep when you know the name, jevgrep when you're guessing". Both answered the same questions on the small repo (2026-09-28). The vague questions were phrased like a user who has never seen the code.

| | Agent, grep only | Agent, grep + jevgrep |
|---|---|---|
| 20 specific questions | 20/20 · median **8.1 s** | 19/20 · median 10.8 s |
| 14 vague questions | 13/14 · median 13.1 s | **14/14** · median **9.9 s** |

- **No measurable speed-up.** The combined agent was just as fast on vague questions when it used plain grep (9.7 s). It had already explored the code on the first 20 questions, so the gap comes from that head start, not from jevgrep.
- **Where it called jevgrep on specific questions, it was slower** (10.3 s against 8.2 s). The extra tool call costs more than jevgrep saves.
- **An agent's turn costs about 4 s per tool call, and grep usually finds the answer in about 2 calls.** jevgrep can save one call at most.
- **Verdict:** jevgrep is a tool for **people** hunting in unfamiliar code (alone: 12/15 vague questions right on the first pick, ~1 s). It is not an agent speed-up.

**Can it run locally with Laya?** [Laya](https://huggingface.co/convaiinnovations/laya) is an open-weights, 421M-parameter model with the same question format, and it runs on your laptop, so no code would leave it. We tested it as a local backend on 2026-09-28:

| | jevgrep (hosted jev) | Laya 0.3.21, local |
|---|---|---|
| Small repo: found | **20/20** | 7/20 (all via the grep lane) |
| Behaviour questions: found | **12/12** | 0/12 |
| Time per question (M-series Mac) | **~1 s** | ~5 s |

- A choice question is capped at 192 tokens for all its options together. That is too small for a list of code summaries.
- Scoring each function yes/no works mechanically (80 checks in 2.2 s). But when every one of the 371 functions was scored directly, the right one ranked 117th.
- Laya is built for tickets, emails and short text, not code. **Not usable for code search today.**

Rerun it on your own repo: write an answer key and run `python3 bench/score.py <repo> <questions.json>`.

## Limits

- Source files only. Generated Dart and protobuf files, `node_modules`, `build` and `Pods` are skipped.
- The first index of a huge tree is slow: about 60 s for 56k files. It is cached after that.
- It does not see prose docs, configs or assets.

## License

MIT. Built on TypeSafe's jev model. Search ideas adapted from jegrep, © 2026 Can Bölük, MIT (see [NOTICE](NOTICE)). The benchmark method came from [fastBrowserTool](https://github.com/varunlohade/fastBrowserTool).
