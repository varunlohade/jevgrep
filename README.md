# jevgrep

**Search code by meaning.** Ask "where do we retry failed payments?" and get `file:line` ranges in about 1–2 seconds, even when the code never uses the words in your question.

```
$ cd dio && jevgrep "Where does a request get rejected because the response status is not acceptable?"
  0.24  lib/src/options.dart:697-758  bool _defaultValidateStatus(int? status) {
  0.20  lib/src/dio_exception.dart:13-45  enum DioExceptionType {
  0.11  lib/src/interceptor.dart:348-373  void onResponse(
  0.06  lib/src/dio_mixin.dart:591-656  Future<Response<dynamic>> _dispatchRequest<T>(RequestOptions reqOpt) async {
  0.06  lib/src/interceptor.dart:515-535  Object? _handleResponse(
  grep  test/pinning_test.dart:9-158  void main() {
  grep  lib/src/dio/dio_for_native.dart:26-126  Future<Response> download(
```

A real run on the public `dio` package, in 1 s. #1 is the rule that decides which statuses pass. #4 is where the request actually gets rejected (`validateStatus` on line 622). The question never says "validate". The scores are not a guarantee, so read the top few.

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

1. **Chunk.** Every source file is split into whole declarations (functions, classes). Doc comments stay attached, and tiny header pieces merge into the next one.
2. **Summarise.** Each chunk becomes its signature plus every identifier and short string used inside. That is how a question about a "not acceptable status" can find code that only says `validateStatus`.
3. **Grep lane (free, local).** Question words are matched against identifier parts (`imageSharpness` → image, sharpness). The best 8 chunks always go into the candidate list.
4. **Jev lane.**
   - In big repos, jev first picks folders. It picks top-level groups first when there are more than 200, because jev takes about 250 options at most.
   - Then it picks files, then the final chunks.
5. **Answer.** It prints jev's top 5 plus grep's best 2, so a miss by one lane can still be caught by the other.

## Results

Each test used an answer key of "where is X?" questions written by one agent. Some had an obvious keyword; the rest were phrased by behaviour, with words that don't appear in the code. A separate agent that never saw the key answered with grep, timed. All scores come from **held-out** questions that were never used for tuning.

**Small repo:** a 27-file, 10k-line Swift app, 20 questions.

| | AI agent + grep | jevgrep | [jegrep](https://github.com/can1357/jegrep) |
|---|---|---|---|
| Found | 20/20 | **20/20** | 16/20 |
| First pick right | 20/20 | 17/20 | 16/20 |
| Lines to read (median) | – | **35** | 162 |
| Time | 7.9 s | **~1 s** | 1.2 s |

**Big repo:** a 1,967-file, 362k-line Flutter app, 20 questions. Measured before the fix that made jevgrep see Dart/Java/Kotlin methods, so jevgrep's numbers here are a floor.

| | AI agent + grep | jevgrep | jegrep |
|---|---|---|---|
| Found | **20/20** | 16/20 | 12/20 |
| First pick right | **20/20** | 10/20 | 12/20 |
| Keyword questions found | 8/8 | 8/8 | 8/8 (all first pick) |
| Behaviour questions found | 12/12 | **8/12** | 4/12 |
| Time | 9.7 s | 2.2 s | 1.5 s |

**What this means:**
- jevgrep beats jegrep on behaviour questions and points at tighter ranges. jegrep is better at keyword questions.
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

MIT. Built on TypeSafe's jev model. The benchmark method came from [fastBrowserTool](https://github.com/varunlohade/fastBrowserTool).
