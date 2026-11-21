import { expect, test } from '../../frontend/node_modules/@playwright/test';
import { readServerEvents } from '../../frontend/src/api/eventStream';

test('SSE preserves fragmented UTF-8, CRLF boundaries, and multiline data', async () => {
  const bytes = new TextEncoder().encode(': keepalive\r\n\r\nevent: progress\r\ndata: caf\u00e9\r\ndata: next line\r\n\r\nevent: result\ndata: {}\n\n');
  const body = new ReadableStream<Uint8Array>({ start(controller) {
    for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
    controller.close();
  }});
  const events = [];
  for await (const event of readServerEvents(body)) events.push(event);
  expect(events).toEqual([{kind: 'progress', data: 'caf\u00e9\nnext line'}, {kind: 'result', data: '{}'}]);
  expect(body.locked).toBe(false);
});

test('SSE releases the reader when the consumer stops early', async () => {
  let cancelled = false;
  const body = new ReadableStream<Uint8Array>({
    start(controller) { controller.enqueue(new TextEncoder().encode('event: error\ndata: failed\n\n')); },
    cancel() { cancelled = true; },
  });
  for await (const event of readServerEvents(body)) { expect(event.kind).toBe('error'); break; }
  expect(cancelled).toBe(true);
  expect(body.locked).toBe(false);
});
