# Anthropic API Pricing

**Last Updated:** 2025-12-13
**Plan:** MAX-5X with Extended Context (1M input / 64K output)
**Source:** Anthropic API Pricing (as of December 2025)

---

## Base Model Pricing

### Claude Opus 4.5 (`claude-opus-4-5-20251101`)

| Token Type | Cost per Million Tokens |
|------------|-------------------------|
| Input      | $5.00                   |
| Output     | $25.00                  |

**Use Cases:**
- Deep code review
- QMS compliance verification
- Narrative generation
- Adversarial review
- Critical decision support

---

### Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)

| Token Type | Cost per Million Tokens |
|------------|-------------------------|
| Input      | $1.00                   |
| Output     | $5.00                   |

**Use Cases:**
- Primary development work
- Implementation
- Standard analysis
- Code generation
- General reasoning tasks

---

### Claude Haiku 4.5 (`claude-haiku-4-5-20250507`)

| Token Type | Cost per Million Tokens |
|------------|-------------------------|
| Input      | $0.25                   |
| Output     | $1.25                   |

**Use Cases:**
- Simple edits
- Quick tasks
- Repetitive operations
- Template rendering
- Lightweight automation

---

## Prompt Caching Costs

**What is Prompt Caching?**

Prompt caching allows you to cache portions of your prompt context to reduce costs on repeated API calls. When you mark content as cacheable, Anthropic stores it for 5 minutes. Subsequent requests that include the same cached content pay reduced rates.

**Cache Lifetime:** 5 minutes (cache refreshed on each use)

**When to Use:**
- Repeatedly accessing the same large context (e.g., CLAUDE.md, agent files)
- Session-based workflows where context is reused
- Long documents analyzed multiple times

### Opus 4.5 Caching Costs

| Token Type        | Cost per Million Tokens | vs. Base Input |
|-------------------|-------------------------|----------------|
| Cache Write       | $6.25                   | 1.25× higher   |
| Cache Read        | $0.50                   | 10× cheaper    |
| Regular Input     | $5.00                   | baseline       |
| Output            | $25.00                  | unchanged      |

**Break-even Analysis:**
- Cache write costs 1.25× more than regular input
- Cache read costs 0.1× of regular input
- Break-even: Read cache 2+ times to recover write cost
- Session work: Typically 5-10+ cache reads → significant savings

**Example Session:**
```
Initial call:
- Cache write (CLAUDE.md, 10K tokens): $0.0625
- Regular input (user message, 500 tokens): $0.0025
Total: $0.065

Subsequent 9 calls in session:
- Cache read (10K tokens × 9): 9 × $0.005 = $0.045
- Regular input (500 tokens × 9): 9 × $0.0025 = $0.0225
Total: $0.0675

Session total: $0.1325
Without caching: $0.0525 × 10 = $0.525
Savings: $0.3925 (75% reduction)
```

---

### Sonnet 4.5 Caching Costs

| Token Type        | Cost per Million Tokens | vs. Base Input |
|-------------------|-------------------------|----------------|
| Cache Write       | $1.25                   | 1.25× higher   |
| Cache Read        | $0.10                   | 10× cheaper    |
| Regular Input     | $1.00                   | baseline       |
| Output            | $5.00                   | unchanged      |

---

### Haiku 4.5 Caching Costs

| Token Type        | Cost per Million Tokens | vs. Base Input |
|-------------------|-------------------------|----------------|
| Cache Write       | $0.30                   | 1.2× higher    |
| Cache Read        | $0.03                   | 8.3× cheaper   |
| Regular Input     | $0.25                   | baseline       |
| Output            | $1.25                   | unchanged      |

---

## Cost Optimization Strategies

### 1. Model Selection

**Use the right model for the task:**
- Haiku for simple, repetitive tasks (5× cheaper than Sonnet)
- Sonnet for standard development work (5× cheaper than Opus)
- Opus only when deep reasoning required (e.g., QMS review, narrative generation)

**Example Savings:**
- Simple edit (1K input, 500 output):
  - Opus: $0.0175
  - Sonnet: $0.0035 (5× cheaper)
  - Haiku: $0.000875 (20× cheaper)

---

### 2. Prompt Caching

**Cache large static context:**
- CLAUDE.md (~10K tokens)
- Agent files (.claude/agents/*.md)
- Analysis results (results/*.toml)
- Large reference documents

**Don't cache:**
- User messages (always changing)
- Short contexts (<1K tokens - overhead not worth it)
- Content used only once

---

### 3. Context Management

**Minimize redundant context:**
- Use Task tool with specialized agents instead of repeating instructions
- Reference files by path rather than including content when possible
- Summarize when full context not needed

**Example:**
- Bad: Include full 50K token analysis in every call
- Good: Cache 50K analysis, reference specific sections in calls

---

### 4. Output Token Management

**Output tokens cost 5× more than input:**
- Request concise responses when appropriate
- Use structured outputs (JSON) to reduce verbosity
- Don't request explanations when only result needed

**Example Savings:**
- Analysis script output:
  - Verbose (5K tokens): $0.025 (Sonnet)
  - Concise JSON (1K tokens): $0.005 (5× cheaper)

---

## Project-Specific Cost Estimates

### Checkpoint Overhead

**Pilot measurement (Issue #35):**
- 3 checkpoints: ~750 tokens
- Total session: ~110,000 tokens
- Overhead: 0.7%

**With complete checkpoints (projected):**
- 6 checkpoints: ~1,500 tokens
- Overhead: 1.4%

**Cost impact at scale:**
- Sonnet session (110K input, 10K output): $0.16
- Checkpoint overhead (1.5K output): $0.0075
- **Percentage increase: 4.7%**

**Assessment:** Negligible cost for significant quality improvement.

---

### Opus Narrative Generation

**Per issue:**
- Load narrative-generator agent: ~5K tokens (cache write: $0.03125)
- Load checkpoint files: ~3K tokens (input: $0.015)
- Generate narrative: ~2K tokens (output: $0.05)
- **Total: $0.096 per issue**

**With reuse in session (5 issues):**
- Initial: $0.096
- Subsequent 4: Cache read (5K) + input (3K) + output (2K) = $0.0875
- **Average per issue: $0.0877**

**ROI Assessment:**
- Cost: <$0.10 per issue
- Benefit: Objective review, consistent quality, bias elimination
- **Verdict: High value, negligible cost**

---

### Full QMS Review Process

**Example: Issue #83 pilot review**

**Agent work (Sonnet):**
- Development: ~110K input, ~10K output = $0.16

**QMS review agent (Haiku for user guidance):**
- 8 prompts: ~8K input, ~4K output = $0.007

**Opus narrative generation:**
- Checkpoint review: ~8K input, ~2K output = $0.09

**Total QMS overhead: $0.097**
**Work overhead percentage: 60%**

**Assessment:**
- Significant percentage but absolute cost is low (<$0.10)
- Quality improvement likely worth 60% overhead
- Consider Haiku for more of the review workflow to reduce cost

---

## Recommendations

### 1. Instrumentation

**Implement token tracking:**
- Log tokens per checkpoint
- Track cumulative session tokens
- Calculate overhead percentage
- Monitor cache hit rates

**Why:** Current cost estimates are rough. Real measurements needed for optimization.

---

### 2. Cache Strategy

**Immediate:**
- Enable caching for CLAUDE.md
- Enable caching for agent files
- Cache large analysis results when reused

**Future:**
- Measure cache hit rates
- Optimize cache boundaries
- Consider cache warming for common patterns

---

### 3. Model Selection Guidelines

**Decision tree:**
1. Is this creative/strategic/critical? → Opus
2. Is this standard development work? → Sonnet
3. Is this simple/repetitive/mechanical? → Haiku

**Examples:**
- "Generate narrative from checkpoints" → Opus (critical quality)
- "Implement OffsetManager class" → Sonnet (standard dev)
- "Fix typo in README" → Haiku (simple edit)

---

### 4. Output Optimization

**Target conciseness:**
- Checkpoints: <500 tokens (brief, structured)
- Code reviews: Focus on issues, not repetition
- Reports: Executive summary + details structure

**Avoid:**
- Verbose explanations when not needed
- Repeating context in output
- Long apologetic preambles

---

## Related Issues

- Issue #84: [Ideation] Applying token cost information to process and decision making
- Issue #85: [Ideation] Custom agents as foundational design pattern

---

## References

- [Anthropic API Pricing](https://www.anthropic.com/pricing)
- [Prompt Caching Documentation](https://docs.anthropic.com/en/docs/prompt-caching)
- MAX-5X Plan Details (internal)
