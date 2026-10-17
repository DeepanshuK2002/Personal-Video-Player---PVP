import { describe, expect, it } from 'vitest';
import { queryString } from './api';

// `queryString` builds every outgoing request URL (including the OAuth
// redirects for Google Drive / OneDrive) and is also used in reverse to read a
// parameter back out of a redirect URL.

describe('queryString reading a parameter out of a URL', () => {
    it('returns the value of the requested parameter', () => {
        expect(queryString('code', 'https://example.com/callback?code=abc123&state=xyz')).toBe('abc123');
    });

    it('reads a parameter that is not the first one', () => {
        expect(queryString('state', 'https://example.com/callback?code=abc123&state=xyz')).toBe('xyz');
    });

    it('returns undefined when the parameter is absent', () => {
        expect(queryString('missing', 'https://example.com/callback?code=abc123')).toBeUndefined();
    });

    it('returns an empty string for a valueless parameter', () => {
        expect(queryString('code', 'https://example.com/callback?code=&state=xyz')).toBe('');
    });
});

describe('queryString building a URL from an object', () => {
    it('appends parameters to a bare url', () => {
        expect(queryString({ a: '1' }, 'https://example.com/api')).toBe('https://example.com/api?a=1');
    });

    it('joins several parameters with &', () => {
        const result = queryString({ a: '1', b: '2' }, 'https://example.com/api');
        expect(result).toBe('https://example.com/api?a=1&b=2');
    });

    it('keeps parameters already present on the url', () => {
        const result = queryString({ b: '2' }, 'https://example.com/api?a=1');
        expect(result).toBe('https://example.com/api?a=1&b=2');
    });

    it('percent-encodes values so tokens and redirect urls survive', () => {
        const result = queryString({ redirect: 'https://example.com/cb?x=1' }, 'https://example.com/auth');
        expect(result).toContain('redirect=https%3A%2F%2Fexample.com%2Fcb%3Fx%3D1');
    });

    it('percent-encodes spaces and "+" rather than passing them through', () => {
        const result = queryString({ scope: 'read write' }, 'https://example.com/auth');
        expect(result).toBe('https://example.com/auth?scope=read%20write');
    });

    it('serialises object values as encoded JSON', () => {
        const result = queryString({ filter: { id: 1 } }, 'https://example.com/api');
        expect(result).toBe(`https://example.com/api?filter=${encodeURIComponent(JSON.stringify({ id: 1 }))}`);
    });

    it('serialises a boolean as an explicit true/false value', () => {
        // Note: values are encoded before the bare-flag check, so a `true`
        // value is emitted as `pretty=true` rather than as a bare `pretty`.
        expect(queryString({ pretty: true }, 'https://example.com/api')).toBe('https://example.com/api?pretty=true');
        expect(queryString({ pretty: false }, 'https://example.com/api')).toBe('https://example.com/api?pretty=false');
    });

    it('skips undefined values instead of sending "undefined"', () => {
        const result = queryString({ a: '1', b: undefined }, 'https://example.com/api');
        expect(result).toBe('https://example.com/api?a=1');
    });

    it('returns the url untouched for an empty parameter object', () => {
        expect(queryString({}, 'https://example.com/api')).toBe('https://example.com/api');
    });
});

describe('queryString building a URL from an array', () => {
    it('appends raw string entries', () => {
        expect(queryString(['a=1'], 'https://example.com/api')).toBe('https://example.com/api?a=1');
    });

    it('appends key/value pair entries', () => {
        expect(queryString([['a', '1']], 'https://example.com/api')).toBe('https://example.com/api?a=1');
    });
});
