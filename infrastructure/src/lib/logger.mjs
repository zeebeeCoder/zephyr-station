// Simple logger - demonstrates class export

import { config } from './config.mjs';

export class Logger {
  constructor(context = 'handler') {
    this.context = context;
  }

  #format(level, message, meta = {}) {
    return JSON.stringify({
      timestamp: new Date().toISOString(),
      level,
      service: config.serviceName,
      context: this.context,
      message,
      ...meta,
    });
  }

  info(message, meta) {
    console.log(this.#format('INFO', message, meta));
  }

  error(message, meta) {
    console.error(this.#format('ERROR', message, meta));
  }
}
