# Agent-readable site

A site can look finished and still disappear when you strip away the design. The main claim may live inside an image. The title may say Home. The structured data may never make it into the page.

I built this toolkit to inspect what is actually there. It has three parts: a linter, an llms.txt draft generator, and six JSON-LD templates. It names the gaps it can prove and stops where the evidence stops.

**Conformance is measurable. Outcomes are not.**

## Who this is for

I made this for site owners, developers, content teams, and technical SEO practitioners who need a concrete inventory before they change a site. It is useful when a page looks clear to a person but its claims, identity, or navigation are difficult to recover from HTML and metadata.

## What it checks

The linter reads one page and the root metadata around it. It checks:

- whether `/llms.txt` exists and follows the documented llms.txt v2 structure;
- whether JSON-LD exists, parses, and declares schema.org types;
- whether an Organization or Person entity includes `name`, `url`, and `description`;
- whether primary claims exist as visible text or appear trapped in an image;
- whether H1 and H2 headings describe content and follow a usable order;
- whether the title and meta description are substantive;
- whether a canonical URL is declared; and
- what `robots.txt` says about a maintained list of AI-related user-agent tokens.

Crawler access is a fact, not a defect. Blocking can be deliberate, and the score does not reward or punish that decision.

## The llms.txt caveat

llms.txt is an emerging convention with uneven adoption. The current proposal defines a small Markdown file with one required H1, optional summary and context, and optional H2 sections containing link lists. This tool reports conformance to that documented structure. It does not claim that any AI system will rank, cite, favor, or even read a conforming site.

The generator only describes pages it successfully reads. If a page has no title or meta description, the draft does not invent one. The human edits the draft before publishing it.

## Install it

I target Python 3.11 or newer. Runtime code uses only the Python standard library.

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e .
```

Install the test dependency when you are working on the toolkit:

```bash
.venv/bin/pip install -e '.[test]'
```

## Run it

Inspect a page:

```bash
agent-readable-site lint https://example.com
```

Return JSON for another tool:

```bash
agent-readable-site lint https://example.com --json
```

Draft llms.txt from pages the generator can read:

```bash
agent-readable-site generate \
  https://example.com \
  https://example.com/services \
  https://example.com/about \
  --output llms.txt
```

The generator stops if any supplied page cannot be fetched or parsed. It never fills a missing description from model memory or a guess.

## Read the report

A clean fixture produces this shape:

```text
Agent-readable site report
URL: file:///tmp/example-site/index.html
Score: 100/100
Schema types: Organization

Defects:
- none

Crawler access facts:
- OAI-SearchBot: allowed
- GPTBot: allowed
```

The complete report lists every maintained user-agent token. The short example keeps the focus on the score and defect format.

That 100/100 is a purpose-built fixture, not a normal target. In a calibration pass, measured real sites landed between 20 and 65. The top of that band was the site that publishes the llms.txt convention itself. I'm keeping this as a band so individual site scores do not go stale.

## How the score works

I need to be straight about the score. I chose these weights. They are useful because every point maps to an observable condition, but they are not a study of ranking or citation outcomes.

| Check | Points | Why it carries that weight |
|---|---:|---|
| llms.txt presence and conformance | 20 | This is a bet, not a measured outcome. llms.txt is the only artifact here authored specifically for machine consumption. If you think the convention will not stick, subtract 20 and read the remaining 80. Presence earns 8 points. Valid structure earns the remaining 12. |
| Parseable JSON-LD | 15 | Structured data gives machines explicit entities and types, but it cannot replace readable page text. |
| Complete Organization or Person entity | 15 | This is worth more than canonical because it records who the page represents with a name, URL, and description. It is worth less than llms.txt because it is not the dedicated machine-consumption artifact this score is betting on. |
| Primary claims in visible text | 15 | A claim trapped in pixels is harder to inspect, quote, and verify from HTML. |
| Descriptive heading structure | 10 | This is worth more than canonical because H1 and H2 text maps the page's content. It is worth less than llms.txt because headings are one layer of page clarity, not an artifact written specifically for machines. |
| Substantive title | 10 | The title is the shortest stable label for the page. The check requires at least 12 characters and two words. |
| Substantive meta description | 10 | The description supplies a concise page summary. The check requires at least 50 characters and eight words. |
| Canonical URL | 5 | Canonical identity matters, but it should not outweigh readable claims or entity data. |

The maximum is 100. robots.txt is deliberately outside the score.

## Fail loud

Silence is not a pass. If the linter cannot fetch the page, decode it, or parse recognizable HTML, it prints the exact failure, exits non-zero, and produces no score. If a root resource is definitively absent, such as a 404 for llms.txt, that absence becomes a named defect. If the resource fails for an ambiguous reason, the inspection stops instead of calling the site healthy.

Malformed JSON-LD and malformed llms.txt are named defects and produce a non-zero result. A page the tool never read never receives a number.

## Use the templates

The `templates/` directory contains filled-in JSON-LD examples for Organization, Person, Service, Course, Article, and FAQPage. Every name and URL belongs to an obviously fictional example. Replace the values, validate the result, and publish only facts you can support.

## Check the convention

I implemented the llms.txt structure from [the llms.txt v2 proposal](https://llmstxt.org/). The crawler-token list is grounded in current documentation from [OpenAI](https://developers.openai.com/api/docs/bots), [Anthropic](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler), [Google](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers), and [Perplexity](https://docs.perplexity.ai/docs/resources/perplexity-crawlers). Those providers can change their tokens and policies. Treat this list as inspectable code, not permanent truth.

## License

I release this toolkit under the MIT License. See `LICENSE`.
