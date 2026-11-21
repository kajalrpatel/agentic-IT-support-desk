# Frontend architecture

The frontend is an independently built React application. The backend remains the authority for identity, conversation ownership, ticket approval versions, and persisted messages. This refactor does not change the HTTP contracts or deployment images.

```text
src/
  App.tsx                       Composition root: connects hooks to components
  main.tsx                      React entry point
  app/
    components/                 Header, error boundary, and safe fallback
    styles/                     Workspace shell styles
  config/runtime.ts             Container-provided runtime configuration
  api/                          JSON transport, SSE decoding, generated contracts
  models/supportModels.ts       Shared typed conversation/ticket data contracts
  features/
    auth/services/              Demo/OIDC session initialization
    conversations/
      models/                   Conversation navigation view contract
      components/                    History, navigation, welcome, messages, composer
      hooks/                    Conversation workflow, composer state, and scrolling
      services/                 Conversation endpoints and message-stream protocol
      utils/                    Browser selection storage and error formatting
      styles/                   Conversation presentation
    tickets/
      components/                    TicketPreview and TicketCard
      hooks/                    useTicketDraft: local edit state and discard behavior
      styles/                   Ticket presentation
  styles/                       Base styles, feedback, ordered imports, responsive overrides
```

## Components and hooks

The frontend is organized by feature. **Models** define data contracts, **components** render data and emit actions, and **hooks** own state and coordinate workflows. `hooks/useConversations.ts` handles conversation state and service calls; smaller hooks handle composer state, scrolling, and ticket draft editing. Services handle external I/O; utilities contain narrowly scoped helpers.

The flow is `App -> hook -> service -> HTTP/backend`, followed by state updates and component rendering. Presentation components receive workflow callbacks instead of importing the workspace hook or making HTTP calls. Models do not import components or hooks. Shared contracts live in `models/supportModels.ts`; feature-only models stay inside the feature. Add folders only when they have a concrete responsibility.

All application components are functions. `AppErrorBoundary` composes [react-error-boundary](https://github.com/bvaughn/react-error-boundary), with a separate functional fallback component. React's error-catching lifecycle still uses a class inside that library; wrapping children in a function or try/catch alone cannot catch descendant rendering failures. The fallback does not expose exception details and reloads the workspace to recover.

## Ownership and dependencies

`App` composes features. UI components receive typed data and callbacks; they do not authenticate, fetch, or access browser storage. The conversation hook coordinates service calls and state; endpoint paths live in the service adapter. Transport and stream decoding do not import React or feature UI. The contract aliases depend on generated schemas. Ticket components can be used by a conversation without importing its state hook.

Keep state at its owner: unsent text belongs to the composer, unsaved ticket fields belong to the preview, and persisted conversation state belongs to the workspace hook. Do not introduce a global store for component-local state. Add a separate feature hook when introducing a new workflow rather than growing `App` or the conversation hook indefinitely.

Writes are single-flight to prevent duplicate submits before React rerenders. Conversation selection ignores stale responses. Initialization tolerates React StrictMode and checks that the saved conversation is present in the authenticated list. Blocked browser storage does not prevent chat. Errors are shown in the workspace; a rendering error has a reload fallback. Failed message streams are not automatically retried because the server may already have accepted the request.

Streaming uses a POST request and SSE records. The generic decoder handles fragmented UTF-8 and LF/CRLF records, and releases its reader on completion or failure. The chat adapter interprets progress, result, and error records. Ticket creation remains a separate explicit confirmation request with the server's draft version and a request ID.

Styles are split by ownership, preserving their original cascade through `styles/index.css`. Responsive overrides remain centralized because they coordinate the sidebar, chat, and ticket layouts. Generated contracts remain in their own file; regenerate them using `npm run generate:api` when the backend contract changes.

## Verification and deployment

- `npm run typecheck`: strict TypeScript checks.
- `npm run build`: TypeScript plus production Vite build.
- `npm test`: Playwright browser flows and stream-decoder checks. Starts a deterministic backend test server; does not create Jira tickets or call a paid LLM.

Runtime configuration still comes from `public/config.js` locally and the container entrypoint in deployments. No secrets belong in that configuration. Production authentication still requires a correctly configured OIDC provider; these local tests use demo authentication and do not certify provider renewal, TLS, or a production deployment. Browser state is not an authorization boundary.
