# Project presentation review — November 12, 2026

## Findings and decisions

The previous README mixed onboarding with dated development evidence and superseded interface descriptions. The only hosted release was v0.2.0 while source/builds were 0.5.2. The portable packager copied Markdown but had no provision for graphics or separate notices. Owner-private notes contained stale relative links and current/historical dictation descriptions mixed together.

The revision makes the GitHub repository the program page: illustrated introduction, useful badges, prominent version-specific download/setup/help links, feature table, expandable explanations and a Mermaid architecture diagram. GitHub does not run arbitrary JavaScript in README content; interactive elements use supported native rendering. The graphic is explicitly an illustration with synthetic text, not a screenshot or a fabricated performance result. No upstream artwork was copied.

Setup, maintenance and acceptance detail live on dedicated pages. Community policies, issue forms, a PR template, license notices and a changelog make participation and support discoverable. A Windows ZIP and checksum accompany the release. This is a 0.5.2 release, not a claim of v1.0 acceptance.

## Primary sources reviewed

| Source | Pattern applied |
| --- | --- |
| [GitHub: About READMEs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) | Purpose, usefulness, getting started, help and maintainers first; relative links for repository content |
| [GitHub: Community profiles](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories) | License, contribution guidance, conduct and issue templates |
| [Open Source Guides: Starting a project](https://opensource.guide/starting-a-project/) | Audience, branding, expectations and pre-launch preparation |
| [Handy](https://github.com/cjpais/Handy) | Speech-tool presentation, visible identity, installation and community routes |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | Technical quick start, diagrams/media and detailed platform documentation |

These are structural references, not claims that SimpleWhisper shares their feature set, offline acceptance, scale or support capacity.
