# Discord Read-only Integration

Solo Empire exposes a bounded metadata-only Discord boundary. It uses a bot
token to validate the bot identity and list the servers/guilds visible to that
bot.

## Supported boundary

- `GET /api/integrations/discord/guilds?limit=20` — authenticated, at most 100
  partial guild summaries (`id`, `name`, `icon`, `owner`, and feature names).
- `GET /api/integrations/health` — validates `GET /users/@me` without reading
  messages or member lists.
- `?offline=true` — deterministic credential-free verification path.

Messages, channels, members, DMs, slash-command registration, Gateway
connections, and all create/update/delete operations are intentionally out of
scope.

## Credential contract

- Environment name: `DISCORD_BOT_TOKEN`
- Secret folder: `/discord`
- Token is resolved by `infra/scripts/utils/secret_resolver.py`; values never
  belong in this repository or in logs.

The adapter follows Discord's bot-token authentication and current-user guild
listing endpoints documented in the [Discord developer documentation](https://docs.discord.com/developers/resources/user).
