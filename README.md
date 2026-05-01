# Support Triage Agent

## Overview
This is a terminal-based AI support triage agent that processes support tickets across HackerRank, Claude, and Visa ecosystems.

## Architecture
The system follows a pipeline:
1. Retrieval of relevant documents from the provided corpus
2. LLM-based response generation using Groq API
3. Validation layer to enforce safe escalation for high-risk issues (fraud, billing, security)

## Features
- Context-aware responses using provided support corpus
- Safe handling via escalation logic
- Structured CSV output generation
- Terminal-based evaluation logs

## Setup
1. Install dependencies:
   pip install groq

2. Set API key:
   set GROQ_API_KEY=your_key_here

3. Run:
   python main.py

## Notes
- Only the provided corpus is used (no external knowledge)
- High-risk issues are escalated to human support