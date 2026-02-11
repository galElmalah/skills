# GitHub CLI Commands Reference

## Detecting the Current PR

Auto-detect PR from current branch:

```bash
gh pr view --json number,url,title,headRefName,baseRefName
```

If this fails (no PR for current branch), fall back to asking the user.

To get the repo owner/name:

```bash
gh repo view --json nameWithOwner --jq '.nameWithOwner'
```

## Getting the Current User

```bash
gh api user --jq '.login'
```

Use this to filter out the user's own comments.

## Fetching Review Comments (Inline Code Comments)

These are comments left on specific lines of code during a review:

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments --paginate
```

Each comment includes:
- `id` - Comment ID (for replying)
- `body` - Comment text
- `path` - File path the comment is on
- `line` or `original_line` - Line number
- `diff_hunk` - Code context
- `user.login` - Author
- `created_at` - Timestamp
- `in_reply_to_id` - If this is a reply to another comment

### Filtering Review Comments

To get only top-level comments (not replies):

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments --paginate \
  --jq '[.[] | select(.in_reply_to_id == null)]'
```

To check if a comment already has a reply from the current user:

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments --paginate \
  --jq '[.[] | select(.in_reply_to_id != null and .user.login == "CURRENT_USER")]'
```

Cross-reference: if any reply's `in_reply_to_id` matches a top-level comment's `id`, that comment has been replied to.

## Fetching Issue Comments (General PR Comments)

These are general conversation comments on the PR (not on specific code):

```bash
gh api repos/{owner}/{repo}/issues/{number}/comments --paginate
```

Each comment includes:
- `id` - Comment ID
- `body` - Comment text
- `user.login` - Author
- `created_at` - Timestamp

## Replying to Comments

For reply API calls and comment templates, see `references/reply-formats.md`.

## Pagination

All list endpoints support `--paginate` to automatically follow pagination. Always use it to ensure all comments are fetched.

## Rate Limiting

For PRs with many comments, the parallel subagent approach may hit rate limits. If a `gh api` call returns a 403 with rate limit headers, wait and retry. In practice, PRs rarely have enough comments to trigger this.
