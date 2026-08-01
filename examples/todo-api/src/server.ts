// Optional entrypoint for running the app standalone (not used by the test
// suite — tests drive createApp() directly via supertest).

import 'dotenv/config';
import { createApp } from './app';

const port = process.env.PORT ? Number(process.env.PORT) : 3000;
createApp().listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`todo-api listening on :${port}`);
});
