---
name: ui-pr
description: Capture and attach UI evidence for pull requests. Use when Codex opens, updates, prepares, or reviews a PR with user-visible UI changes and needs screenshots, video, or Playwright trace evidence; when a user asks to add PR screenshots/video; or when a PR body lacks visual evidence for UI work.
---

# UI PR

## Core Rule

For every PR with user-visible UI changes, ensure the PR has current visual evidence before finishing. If relevant screenshots, videos, or traces already exist in the PR body or comments, verify they still match the current changes. If not, capture new evidence and attach it to the PR.

Prefer screenshots for static visual states. Use video for multi-step flows, animations, drag/drop, navigation guards, modal sequences, or any behavior that cannot be understood from one still image.

Do not commit screenshots or videos to the feature branch unless the user explicitly asks for tracked assets. PR evidence should live in GitHub PR attachments or on a dedicated evidence branch that is not part of the PR diff.

## Check Existing Evidence

1. Identify the PR:

```bash
gh pr view --json number,url,body,comments,files,headRefName,headRepository,headRepositoryOwner
```

2. Inspect the body and comments for Markdown images, videos, trace links, or filenames matching the changed UI.
3. Inspect the file list for committed evidence folders such as `.pr-screenshots`, `screenshots`, `artifacts`, `.playwright`, `test-results`, or media extensions. Remove these from the feature branch unless they are intentional product assets.
4. If evidence exists but points at an old branch path, stale state, or a removed file, replace it.

## Capture With Playwright MCP

Use Playwright MCP to reproduce the changed UI in a real browser. Use `browser_snapshot` for interaction refs and assertions; use screenshots only for visual evidence.

Useful setup calls:

```text
browser_resize { "width": 1440, "height": 1000 }
browser_navigate { "url": "http://localhost:5173/path-under-test" }
browser_wait_for { "text": "Expected stable text" }
browser_snapshot {}
```

Viewport screenshot:

```text
browser_take_screenshot {
  "filename": "ui-pr/01-settings-empty-state.png",
  "type": "png"
}
```

Full-page screenshot:

```text
browser_take_screenshot {
  "filename": "ui-pr/02-connectors-list.png",
  "type": "png",
  "fullPage": true
}
```

Element screenshot after obtaining a target from `browser_snapshot`:

```text
browser_take_screenshot {
  "target": "e42",
  "element": "Dirty navigation confirmation modal",
  "filename": "ui-pr/03-dirty-nav-modal.png",
  "type": "png"
}
```

Video recording requires Playwright MCP `devtools` capability. Start before the interaction, optionally add chapters, and stop after the final state is visible:

```text
browser_start_video {
  "filename": "ui-pr/dirty-nav-flow.webm",
  "size": { "width": 1440, "height": 1000 }
}
browser_video_chapter {
  "title": "Unsaved connector edit",
  "description": "Change a connector field so Save changes is enabled"
}
browser_click { "target": "e15", "element": "Navigate to another connector" }
browser_video_chapter {
  "title": "Dirty navigation guard",
  "description": "Modal blocks navigation and offers save, discard, or keep editing"
}
browser_stop_video {}
```

Trace recording also requires `devtools` capability and is useful when reviewers need a timeline with DOM snapshots, screenshots, network, and console:

```text
browser_start_tracing {}
browser_navigate { "url": "http://localhost:5173/path-under-test" }
browser_click { "target": "e15", "element": "Primary interaction" }
browser_stop_tracing {}
```

Keep captures focused. Name files with a stable order and the behavior or ticket they demonstrate. Avoid secrets, personal data, tokens, private customer data, and unrelated browser chrome.

## Upload To GitHub

Prefer GitHub PR/issue attachments when a browser session is authenticated. GitHub supports PNG, GIF, JPEG, SVG, MP4, MOV, and WEBM attachments in PR comments and descriptions. GitHub uploads inserted in the editor become GitHub-hosted URLs.

### Preferred: PR Attachment Upload

Use Playwright MCP against the GitHub PR page:

```text
browser_navigate { "url": "https://github.com/OWNER/REPO/pull/123" }
browser_snapshot {}
```

Open a PR comment editor or edit the PR description, trigger the Attach files control or file chooser, then upload local evidence files:

```text
browser_click { "target": "e77", "element": "Add a comment text area" }
browser_click { "target": "e88", "element": "Attach files" }
browser_file_upload {
  "paths": [
    "/absolute/path/to/ui-pr/01-settings-empty-state.png",
    "/absolute/path/to/ui-pr/dirty-nav-flow.webm"
  ]
}
browser_wait_for { "textGone": "Uploading your files" }
browser_snapshot {}
```

After upload completes, GitHub inserts Markdown URLs into the editor. Submit the comment or copy the generated Markdown into the PR body and update it with:

```bash
gh pr edit 123 --body-file /tmp/pr-body.md
```

Use a PR comment for supplemental evidence. Use the PR body when screenshots are central to review.

### CLI Fallback: Dedicated Evidence Branch

`gh` can edit PR text and create comments, but it does not provide a supported binary attachment upload command. Do not claim that `gh gist create` uploads binary screenshots; it may reject binary files.

If the browser is not authenticated, create a dedicated GitHub-hosted evidence branch that is not the PR branch. This keeps media out of the PR diff while still using GitHub URLs.

```bash
PR_NUMBER=123
EVIDENCE_DIR=/absolute/path/to/ui-pr
ASSET_BRANCH="pr-${PR_NUMBER}-ui-evidence"
entries_file=$(mktemp)

for file in "$EVIDENCE_DIR"/*.{png,jpg,jpeg,gif,svg,webm,mp4,mov}; do
  [ -e "$file" ] || continue
  oid=$(git hash-object -w "$file")
  printf '100644 blob %s\t%s\n' "$oid" "$(basename "$file")" >> "$entries_file"
done

tree=$(git mktree < "$entries_file")
rm "$entries_file"
commit=$(printf 'PR #%s UI evidence\n' "$PR_NUMBER" | git commit-tree "$tree")
git update-ref "refs/heads/$ASSET_BRANCH" "$commit"
git push origin "refs/heads/$ASSET_BRANCH:refs/heads/$ASSET_BRANCH"
```

Link assets from the PR body or a PR comment:

```markdown
![Settings empty state](https://github.com/OWNER/REPO/raw/pr-123-ui-evidence/01-settings-empty-state.png)

https://github.com/OWNER/REPO/raw/pr-123-ui-evidence/dirty-nav-flow.webm
```

Prefer lowercase hyphenated filenames without spaces so raw URLs work without escaping. For private repositories, verify the links render for users who have repository access.

## Update The PR

Build a concise evidence section:

```markdown
## Screenshots

Captured against a local dev stack after the UI changes in this PR.

![Settings empty state](...)

## Video

Dirty navigation flow: ...
```

Apply it with one of:

```bash
gh pr edit 123 --body-file /tmp/pr-body.md
gh pr comment 123 --body-file /tmp/pr-evidence-comment.md
```

When replacing committed screenshot links, remove any text saying screenshots are committed to the branch.

## Validate

Before finishing:

1. Run `gh pr view 123 --json body,comments,files` and confirm the PR includes current evidence.
2. Confirm the PR file list does not include temporary screenshots, videos, traces, or evidence folders unless intentionally tracked.
3. Open or fetch every image/video URL and confirm it returns content, not a 404 or local `file://` path.
4. If a dedicated evidence branch was used, confirm it contains only evidence files and is not opened as a separate PR.
5. Mention in the final response how evidence was attached and whether any browser-authenticated upload was unavailable.
