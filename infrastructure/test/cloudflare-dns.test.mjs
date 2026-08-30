import assert from 'node:assert/strict';
import test from 'node:test';

import * as pulumi from '@pulumi/pulumi';

import {
  createZephyrApiDnsRecord,
  readZephyrApiDnsConfig,
  requireCloudflareApiToken,
  ZEPHYR_API_DNS_RESOURCE_NAME,
  ZEPHYR_API_DNS_TTL_SECONDS,
} from '../cloudflare-dns.mjs';

const resources = [];

pulumi.runtime.setMocks({
  newResource: (args) => {
    resources.push(args);
    return {
      id: `${args.name}-id`,
      state: args.inputs,
    };
  },
  call: (args) => args.inputs,
});

function stubConfig(values) {
  return {
    require(key) {
      if (!(key in values)) {
        throw new Error(`missing required configuration key "${key}"`);
      }
      return values[key];
    },
  };
}

const validConfig = {
  cloudflareZoneId: '0123456789abcdef0123456789abcdef',
  apiHostname: 'api.example.test',
  originIpv4: '192.0.2.10',
};

test('Cloudflare DNS config fails when a required input is absent', () => {
  assert.throws(
    () => readZephyrApiDnsConfig(stubConfig({ cloudflareZoneId: validConfig.cloudflareZoneId })),
    /apiHostname/,
  );
});

test('Cloudflare provider auth requires CLOUDFLARE_API_TOKEN', () => {
  assert.throws(() => requireCloudflareApiToken({}), /CLOUDFLARE_API_TOKEN/);
  assert.doesNotThrow(() => requireCloudflareApiToken({ CLOUDFLARE_API_TOKEN: 'present-but-not-inspected' }));
});

test('creates exactly one DNS-only Zephyr A record with a low TTL', async () => {
  resources.length = 0;

  await pulumi.runtime.runInPulumiStack(async () => {
    const record = createZephyrApiDnsRecord(validConfig);
    await record.id.promise();
  });

  const cloudflareResources = resources.filter((resource) => resource.type.startsWith('cloudflare:'));
  assert.deepEqual(
    cloudflareResources.map((resource) => resource.type),
    ['cloudflare:index/dnsRecord:DnsRecord'],
    'the module must not manage a Cloudflare zone or any unrelated resources',
  );

  const dnsRecords = cloudflareResources;
  assert.equal(dnsRecords[0].name, ZEPHYR_API_DNS_RESOURCE_NAME);
  assert.deepEqual(dnsRecords[0].inputs, {
    comment: 'Zephyr backend API; managed by Pulumi',
    content: validConfig.originIpv4,
    name: validConfig.apiHostname,
    proxied: false,
    ttl: ZEPHYR_API_DNS_TTL_SECONDS,
    type: 'A',
    zoneId: validConfig.cloudflareZoneId,
  });
});
