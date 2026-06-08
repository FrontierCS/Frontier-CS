# Generals.io Bot Arena

Work in `/app/generals_agent`, then run:

```bash
bash /app/make_submission.sh
bash /app/submit.sh
```

Submit the baseline skeleton once before running long local experiments, then
submit every meaningful improvement. Local simulations are useful only for tiny
sanity checks; the black-box judge is the scoring feedback for this task, and
submissions run asynchronously while you keep improving.

Submission is asynchronous. Use:

```bash
bash /app/submissions.sh
bash /app/wait_submission.sh <submission_uuid>
```

to inspect judge results while continuing to improve the bot.
