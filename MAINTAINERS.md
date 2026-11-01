# Maintenance for the Claude fork

This fork is maintained at https://github.com/synologyer/line-chat-advisor-mcp-ai-assistant.
Keep runtime/data/vendor, real account paths, candidates, messages and keys out of commits and packages. Preserve the original MIT license and source attribution.

Before publishing: run `npm test`, `npm run check:package`, `git diff --check`, review all staged files, and test the MCP connection against the explicitly selected account only. Do not re-run real key capture just to publish a documentation change.

This package is private (`private: true`); GitHub updates do not publish to npm. Never execute `npm publish` as part of ordinary repository updates.

Source and transitive dependency pins have separate scopes: npm-shrinkwrap and Python hash locks are required; optional GUI vendor builds must remain reviewed. Default Claude operation is passive, without GUI wake-up.
