#!/usr/bin/env python3
"""
Census NLQ — Command Line Interface
=====================================
Usage:
    # Mock mode (no API keys needed)
    python cli.py --mock

    # With a real LLM
    export LLM_PROVIDER=anthropic   # or openai
    export LLM_API_KEY=your_key_here
    python cli.py

    # With real Census data too
    export CENSUS_API_KEY=your_census_key
    python cli.py

Example questions to try:
    What is the population of California?
    Which state has the highest median income?
    Compare poverty rates in Mississippi, West Virginia, and Louisiana.
    What is the unemployment rate in Texas?
    How does Colorado's income compare nationally?
    Tell me about Utah's demographics.
"""

import sys
import os
import argparse

# Make sure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="Census NLQ — Ask questions about US Census data")
    parser.add_argument("--mock", action="store_true",
                        help="Run in mock mode (no API keys required)")
    parser.add_argument("--debug", action="store_true",
                        help="Show tool calls and debug info")
    parser.add_argument("--question", "-q", type=str,
                        help="Ask a single question and exit (non-interactive mode)")
    args = parser.parse_args()

    if args.mock:
        os.environ["MOCK_MODE"] = "true"

    # Late import so env vars are set before config loads
    from nlq.pipeline import answer

    # ── Banner ────────────────────────────────────────────────────────────────
    mock_label = " [MOCK MODE]" if args.mock else ""
    print(f"\n{'='*60}")
    print(f"  Census NLQ{mock_label}")
    print(f"  Ask questions about US Census data (ACS 2022)")
    print(f"{'='*60}")

    if not args.mock:
        from config import LLM_API_KEY, LLM_PROVIDER
        if not LLM_API_KEY:
            print(f"\n⚠  No LLM_API_KEY set. Running in mock mode.")
            print(f"   Set LLM_PROVIDER=anthropic and LLM_API_KEY=sk-ant-...")
            print(f"   or run with --mock for offline demo.\n")
            os.environ["MOCK_MODE"] = "true"
        else:
            print(f"\n  Provider: {LLM_PROVIDER}")

    print(f"\n  Try: 'What is the population of California?'")
    print(f"       'Which state has the highest income?'")
    print(f"       'Compare poverty in Texas, Mississippi, and Ohio'")
    print(f"\n  Type 'quit' or press Ctrl+C to exit.\n")

    # ── Single question mode ──────────────────────────────────────────────────
    if args.question:
        result = answer(args.question)
        print(f"\n{result['answer']}\n")
        if args.debug:
            print(f"[confidence: {result['confidence']:.2f} | "
                  f"flagged: {result['flagged']} | "
                  f"tools: {[t['tool'] for t in result['tool_calls']]}]")
        return

    # ── Interactive loop ──────────────────────────────────────────────────────
    history = []

    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nBye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q", "bye"):
            print("Bye!")
            break

        print()
        result = answer(question, history=history)

        print(f"Assistant: {result['answer']}")

        if result['sources']:
            unique_sources = list(dict.fromkeys(
                s for s in result['sources']
                if not s.startswith("Geography:")
            ))
            if unique_sources:
                print(f"\n  Source: {unique_sources[0]}")

        if args.debug:
            print(f"\n  [confidence: {result['confidence']:.2f} | "
                  f"flagged: {result['flagged']} | "
                  f"tools called: {[t['tool'] for t in result['tool_calls']]}]")

        print()

        # Update conversation history for multi-turn
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": result["answer"]})


if __name__ == "__main__":
    main()
