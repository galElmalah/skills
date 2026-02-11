# Reply Comment Formats

## Reply Templates by Decision

### Accepted Proposed Fix

```
Addressed - {summary_of_what_was_done}
```

Example:
```
Addressed - Replaced md5 with bcrypt for password hashing and updated verifyPassword() accordingly.
```

### Fixed with Custom Instructions

```
Addressed - {summary_of_what_was_done}
```

Example:
```
Addressed - Switched to argon2id instead of bcrypt as it provides better resistance to GPU attacks for our use case.
```

### Won't Fix

```
Won't fix - {reason}
```

Example:
```
Won't fix - This is intentional. The function uses early returns for readability as established in our style guide.
```

### Skip for Now

No reply is posted. The comment remains unaddressed.

## Posting Replies

### Replying to Review Comments (Inline)

Review comments support threading. Reply directly to the comment:

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments \
  --method POST \
  -f body="Addressed - Replaced md5 with bcrypt for password hashing." \
  -F in_reply_to={comment_id}
```

The `in_reply_to` field threads the reply under the original comment.

### Replying to Issue Comments (General)

Issue comments don't support threading. Post a new comment that quotes the original:

```bash
gh api repos/{owner}/{repo}/issues/{number}/comments \
  --method POST \
  -f body="> {first_line_of_original_comment}

Addressed - {summary_of_what_was_done}"
```

Quote the first line (or a distinctive part) of the original comment so reviewers can identify which comment is being addressed.

## Formatting Guidelines

- Keep replies concise (1-2 sentences)
- Start with the action: "Addressed", "Won't fix"
- Include what was done, not what was asked
- For "Won't fix", always include the reason
- Do not use markdown headers or bullet points in replies - keep them flat
- Do not include code blocks in replies unless the change is very small and showing it adds clarity

## Batch Posting

When multiple comments are addressed, post replies sequentially (not in parallel) to avoid rate limiting and ensure proper threading. A small delay between posts is fine.
