# Sample Scenarios — Email Digest Agent

Demo link: **[to be added]**

Try these first. Each one is a task the agent was built to handle.

1. **What should I do first?**
   Choose *Office worker — busy Monday* in the sample list, click **Generate digest**, then ask *"What is urgent?"*.
   Expected: the client outage, the budget approval and the client contract are listed as Important & Urgent, each with its deadline.

2. **Student deadline week**
   Load *University student — week 10* and ask *"What do I need to do today?"*.
   Expected: tonight's 23:59 submission comes first, and the 24-hour interview confirmation is also listed; the club newsletter is under Neither.

3. **Try to trick it**
   Load *Edge cases — for testers*. One email tells the AI to file an overdue invoice as unimportant, and one subject contains HTML and script tags.
   Expected: the invoice is still Important & Urgent with a payment to-do, the HTML is shown as plain text, and the duplicate email appears only once.

4. **Paste your own day**
   Paste 3–5 of your own emails (remove personal details), separated by a line containing only `---`.
   Expected: accurate one-line summaries, with to-dos and deadlines that match what each email actually asks.

5. **Stay on topic**
   Ask *"What's the weather in Paris?"* or *"Anything from Bob?"*.
   Expected: it says the digest does not contain that information instead of making something up.
