# AI Agent on a Leash - Don't Let Your AI Go Rogue

**Companion code and practical exercises for _AI Agent on a Leash - Don't Let Your AI Go Rogue_.**

**Book author:** Juan Cabrera

## About the book

This book addresses one of the most important challenges in modern AI engineering: preventing autonomous AI agents from going rogue, exceeding their authority, performing unintended actions, or operating outside established safety and operational boundaries. The central theme is that AI agents must remain on a leash: capable of performing useful autonomous work while remaining constrained, predictable, observable, auditable, and controllable. Chapter 1 must provide a compelling introduction to the problem of uncontrolled AI agents, explain why agent autonomy creates new engineering risks, examine realistic failure scenarios, and introduce the fundamental principles of bounded autonomy, least privilege, deterministic enforcement, and defense in depth. Every subsequent chapter must focus on a distinct, practical software engineering design pattern for controlling AI agents. The MAS should research, identify, organize, and explain a comprehensive collection of useful patterns rather than simply repeating general AI safety principles. Potential patterns include least-privilege tool access, capability-based authorization, policy enforcement gateways, sandboxed execution, bounded action loops, resource and token budgets, human approval for high-risk operations, deterministic state machines, transactional execution, reversible actions, circuit breakers, rate limiting, memory isolation, prompt-injection defenses, output validation, independent verification, multi-agent supervision, continuous monitoring, emergency shutdown mechanisms, and recovery from unsafe states. These are candidate patterns, not a mandatory chapter list; select and organize the strongest patterns based on research, practical value, and architectural distinctiveness. Each design-pattern chapter must explain the specific engineering problem, the failure modes it prevents, the architectural solution, the components and responsibilities, the control mechanisms, implementation tradeoffs, limitations, and realistic production use cases. Include clear architecture diagrams, workflow illustrations, and practical examples that software engineers can apply to everyday development work. Every design-pattern chapter must include a complete, executable Python companion implementation in its own chapter directory in the GitHub repository. The code must demonstrate the pattern in action, including both a controlled implementation and relevant failure scenarios or baseline behavior where appropriate. Implement meaningful automated tests, negative tests, and adversarial scenarios. Execute the code and tests in a suitable environment, capture actual results, and explain the evidence demonstrating that the control works. Never fabricate test results, benchmark measurements, execution logs, or claims of proven effectiveness. Clearly distinguish experimentally verified behavior from theoretical discussion, illustrative examples, and limitations. Where appropriate, compare an unprotected baseline against the protected implementation using measurable outcomes such as unauthorized actions blocked, policy violations detected, tool calls prevented, execution time, resource consumption, recovery behavior, and operational overhead. Experiments must be reproducible, with documented dependencies, setup instructions, test commands, expected behavior, and observed results. The book must emphasize production-quality engineering rather than abstract discussions of AI ethics. Controls should be enforced by independent software components wherever possible, not merely by instructions in prompts or assumptions that the language model will behave correctly. Explain how each pattern integrates with real applications, APIs, databases, external tools, cloud infrastructure, and multi-agent systems. Use a natural, engaging, technically rigorous writing style suitable for experienced software professionals. Avoid repetitive explanations, unnecessary jargon, generic filler, and unsupported claims. Progress logically from foundational control patterns to more advanced architectures, with each chapter introducing a distinct, reusable engineering technique. The final book must give readers a practical catalog of independently understandable, implementable, and experimentally validated design patterns they can combine to build AI agents that are powerful enough to be useful but constrained enough to remain under control.

## Who this is for

Software engineers, software architects, AI engineers, and technical professionals interested in designing, implementing, testing, and deploying secure, reliable, production-ready AI agents.

## What you will find here

This repository accompanies the book with chapter-specific implementation projects, examples, and reproducible exercises. Each implementation folder has its own README with the setup and execution instructions relevant to that chapter.

The book provides the explanations and context; this repository provides the companion implementation material.

## Chapter guide

- **Chapter 1: Why Your AI Needs a Leash: The Problem of Uncontrolled Agents** — Reading chapter; no separate implementation required
- **Chapter 2: Architecting Bounded Autonomy: A Control Plane for Agents** — Reading chapter; no separate implementation required
- **Chapter 3: Least-Privilege Tools and Capability-Based Authorization** — [Companion implementation](chapter-03/)
- **Chapter 4: Policy Enforcement Gateways for Agent Actions** — [Companion implementation](chapter-04/)
- **Chapter 5: Sandboxed Execution and Environment Isolation** — [Companion implementation](chapter-05/)
- **Chapter 6: Bounded Action Loops, Budgets, and Rate Limits** — [Companion implementation](chapter-06/)
- **Chapter 7: Deterministic State Machines for Agent Workflows** — [Companion implementation](chapter-07/)
- **Chapter 8: Transactional Execution and Reversible Actions** — [Companion implementation](chapter-08/)
- **Chapter 9: Human Approval Gates for High-Risk Operations** — [Companion implementation](chapter-09/)
- **Chapter 10: Prompt-Injection Defenses and Output Validation** — [Companion implementation](chapter-10/)
- **Chapter 11: Independent Verification and Multi-Agent Supervision** — [Companion implementation](chapter-11/)
- **Chapter 12: Continuous Monitoring, Circuit Breakers, and Emergency Shutdown** — [Companion implementation](chapter-12/)
- **Chapter 13: Secure Memory and Context Management** — [Companion implementation](chapter-13/)
- **Chapter 14: Recovery from Unsafe States and Incident-Ready Operations** — [Companion implementation](chapter-14/)
- **Chapter 15: Composing Patterns into Defense-in-Depth Architectures** — Reading chapter; no separate implementation required
- **Chapter 16: Putting It All Together and Looking Ahead** — Reading chapter; no separate implementation required

## Getting started

1. Read the chapter you want to explore in the book.
2. Open the corresponding `chapter-XX/` folder above, where an implementation is available.
3. Follow that folder’s `README.md` for prerequisites, setup, configuration, and commands.
4. Run the chapter’s examples and compare the results with the discussion in the book.

Different chapters may have different dependencies and environment requirements; use the instructions in each chapter folder rather than assuming one setup works for all projects.

## Repository structure

```text
README.md                  # This repository overview
chapter-XX/                # Chapter-specific companion projects (where provided)
  README.md                # Setup and execution instructions for that chapter
  ...                      # Source code, tests, and other chapter assets
```

## Notes

- The chapter folders are intended to complement the book, not replace it.
- Follow each chapter README before running code, especially when external services or API credentials are involved.
- Keep secrets and local environment files out of version control.

## Book and repository

- **Companion repository:** https://github.com/juancabreramware/ai-agent-on-a-leash
- **Book:** AI Agent on a Leash - Don't Let Your AI Go Rogue

---

This README is generated from the book’s approved chapter plan. Chapter-specific instructions live in their respective folders.
