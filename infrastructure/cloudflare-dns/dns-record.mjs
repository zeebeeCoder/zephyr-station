import { isIP } from 'node:net';

import * as cloudflare from '@pulumi/cloudflare';
import * as pulumi from '@pulumi/pulumi';

export const ZEPHYR_API_DNS_LABEL = 'zephyr';
export const ZEPHYR_API_DNS_RESOURCE_NAME = 'zephyr-api-a';
export const ZEPHYR_API_DNS_TTL_SECONDS = 300;

const zoneIdPattern = /^[a-f0-9]{32}$/i;
const hostnamePattern = /^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i;

function requireNonEmpty(value, key) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`Pulumi config "${key}" must be a non-empty string`);
  }

  return value.trim();
}

export function validateZephyrApiDnsConfig(values) {
  const cloudflareZoneId = requireNonEmpty(values.cloudflareZoneId, 'cloudflareZoneId');
  const apiHostname = requireNonEmpty(values.apiHostname, 'apiHostname').toLowerCase();
  const originIpv4 = requireNonEmpty(values.originIpv4, 'originIpv4');

  if (!zoneIdPattern.test(cloudflareZoneId)) {
    throw new Error('Pulumi config "cloudflareZoneId" must be a 32-character Cloudflare zone ID');
  }

  if (!hostnamePattern.test(apiHostname)) {
    throw new Error('Pulumi config "apiHostname" must be a fully qualified DNS hostname without a scheme or path');
  }

  if (!apiHostname.startsWith(`${ZEPHYR_API_DNS_LABEL}.`)) {
    throw new Error(`Pulumi config "apiHostname" must use the approved "${ZEPHYR_API_DNS_LABEL}" label`);
  }

  if (isIP(originIpv4) !== 4) {
    throw new Error('Pulumi config "originIpv4" must be an IPv4 address');
  }

  return { cloudflareZoneId, apiHostname, originIpv4 };
}

export function readZephyrApiDnsConfig(config = new pulumi.Config()) {
  return validateZephyrApiDnsConfig({
    cloudflareZoneId: config.require('cloudflareZoneId'),
    apiHostname: config.require('apiHostname'),
    originIpv4: config.require('originIpv4'),
  });
}

export function requireCloudflareApiToken(env = process.env) {
  if (typeof env.CLOUDFLARE_API_TOKEN !== 'string' || env.CLOUDFLARE_API_TOKEN.trim() === '') {
    throw new Error('CLOUDFLARE_API_TOKEN must be set for Cloudflare provider authentication');
  }
}

export function createZephyrApiDnsRecord(values, options = {}) {
  const config = validateZephyrApiDnsConfig(values);

  return new cloudflare.DnsRecord(ZEPHYR_API_DNS_RESOURCE_NAME, {
    zoneId: config.cloudflareZoneId,
    name: config.apiHostname,
    type: 'A',
    content: config.originIpv4,
    proxied: false,
    ttl: ZEPHYR_API_DNS_TTL_SECONDS,
    comment: 'Zephyr backend API; managed by Pulumi',
  }, options);
}

export function configureZephyrApiDns({ config = new pulumi.Config(), env = process.env } = {}) {
  const values = readZephyrApiDnsConfig(config);
  requireCloudflareApiToken(env);
  return createZephyrApiDnsRecord(values);
}
