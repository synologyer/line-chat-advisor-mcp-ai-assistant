#!/usr/bin/env node
import { createServer } from '../src/line-readonly-mcp/server.mjs';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
if (process.argv.includes('--help')) {
  console.log('Claude LINE Readonly: local MCP on stdio.\nComplete the explicit setup in INSTALL.md before use. No automatic setup or key capture.');
} else {
  await createServer().connect(new StdioServerTransport());
}
