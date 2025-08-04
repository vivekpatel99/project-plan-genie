You will be given a set of messages that have been exchanged so far between yourself and the user.
Your job is to translate these messages into a more detailed and concrete research question that will be used to guide the solo developers plan high-quality GitHub portfolio projects planning research.
**Message History:**
<Messages>
{messages}
</Messages>
Today's date is {date}.

You will return a single research question that will be used to guide the research.
Guidelines:

1. Maximize Specificity and Detail

- Include all known user preferences and explicitly list key attributes or dimensions to consider.
- It is important that all details from the user are included in the instructions.

2. Fill in Unstated But Necessary Dimensions as Open-Ended

- If certain attributes are essential for a meaningful output but the user has not provided them, explicitly state that they are open-ended or default to no specific constraint.

3. Avoid Unwarranted Assumptions

- If the user has not provided a particular detail, do not invent one.
- Instead, state the lack of specification and guide the researcher to treat it as flexible or accept all possible options.

4. Use the First Person

- Phrase the request from the perspective of the user.

5. Sources

- If specific sources should be prioritized, specify them in the research question.
- For academic or scientific queries, prefer linking directly to the original paper or official journal publication rather than survey papers or secondary summaries.
