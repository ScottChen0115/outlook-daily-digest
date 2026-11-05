# Test Log — Email Digest Agent

Our prototype sorts a day's emails into the Eisenhower matrix, extracts to-dos and deadlines, and answers questions about the inbox (DeepSeek, `deepseek-flash`).

**What we tested**

1. **Labelled set (24 emails):** work, study, newsletters, a prompt-injection attempt, Chinese text and an empty subject, each with a fixed expected quadrant and action flag. Result: quadrant 23/24, action flag 24/24. The one miss was a client contract due Friday that was rated urgent rather than important-not-urgent.
2. **Three sample inboxes**, checked against written pass criteria: 18/18.
3. **Prompt injection:** an overdue invoice telling the AI to file it as unimportant, run three times. It was rated Important & Urgent, with a payment to-do, every time.
4. **Chat:** questions with known answers, each asked three times, plus off-topic and absent-sender questions.
5. **27 automated tests** covering input parsing, malformed model replies, API errors and HTML in emails.

**Found broken and fixed**

- "What is urgent?" listed only one of three urgent emails. We rewrote the prompt to require every matching email; afterwards all six runs were complete.
- Chat answers showed raw Markdown asterisks; they are now plain text.
- A model reply of `"false"` (a string) created fake to-dos.
- Emails the model skipped landed silently in the "ignore" quadrant; they are now flagged "needs manual check".
- Duplicate emails were listed twice; they are now merged.
- Oversized input dropped the connection instead of showing a "too large" message.

**Chose not to fix**

- The Friday contract: either quadrant is defensible, and over-warning on a client deadline is the safer error.
- Old chat messages stay on screen after a new digest is generated; this is cosmetic.
- Our test emails are synthetic and few. Real inboxes (long threads, forwarded chains) are untested, so reviewers' own emails are the most useful test.

**Method:** the expected labels were drafted with AI assistance, then reviewed and adopted by the team. Every check compares the output against these fixed labels or written criteria, never against the model's own judgement.
