> Legacy workspace/laboratory guide. Current ticket-pilot controls and trust boundaries are described in [pilot security](PILOT_SECURITY.md) and [the reviewer guide](REVIEW_GUIDE.md).

# Authority and evidence operations

## Signed authority bundles

The `AuthoritySource` contract separates grant issuance from the mechanism that supplies upstream authority. The bundled reference source verifies an HMAC-signed JSON document containing:

- schema and key identifier;
- initiator principal;
- exact action-resource permissions; and
- issued and expiration timestamps.

The HMAC key is read only from `SCOPEDACT_AUTHORITY_KEY`; it is never written into the bundle. Use a distinct, randomly generated secret and protect it outside the project directory. A verified bundle proves possession of that shared key, not a person's identity.

## Event anchors

`anchor-events` first verifies the database's internal event chain. It then writes the chain head, event count, anchor time, schema, and HMAC to a separate file. Retain that file away from the database. `verify-anchor` checks both its signature and exact correspondence to current lifecycle state.

This closes one limitation of an unanchored chain: removing the final event changes the count/head relative to the retained anchor. It does not provide a trusted timestamp, public verifiability, hardware key protection, remote immutability, or key rotation.

Use different keys for authority bundles and evidence anchors. Never commit either key or real authority data.
