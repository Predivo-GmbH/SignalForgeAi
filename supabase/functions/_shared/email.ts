/**
 * Email client using denomailer for Metanet SMTP.
 */

import { SMTPClient } from 'https://deno.land/x/denomailer@1.6.0/mod.ts'

let _client: SMTPClient | null = null

function getClient(): SMTPClient {
  if (_client) return _client

  const hostname = Deno.env.get('SMTP_HOST')
  const username = Deno.env.get('SMTP_USER')
  const password = Deno.env.get('SMTP_PASS')
  if (!hostname || !username || !password) {
    throw new Error('Missing SMTP_HOST, SMTP_USER, or SMTP_PASS')
  }

  _client = new SMTPClient({
    connection: {
      hostname,
      port: Number(Deno.env.get('SMTP_PORT') || '587'),
      tls: true,
      auth: { username, password },
    },
  })
  return _client
}

const FROM = Deno.env.get('SMTP_FROM') || 'noreply@signalforgeai.predivo.ch'

interface EmailOptions {
  to: string
  subject: string
  html: string
}

export async function sendEmail({ to, subject, html }: EmailOptions): Promise<void> {
  const client = getClient()
  await client.send({
    from: FROM,
    to,
    subject,
    content: 'auto',
    html,
  })
}

/** Wrap email body in branded layout */
export function emailLayout(title: string, body: string): string {
  return `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:#0B0B14;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0B0B14;">
<tr><td align="center" style="padding:40px 20px;">
  <table width="560" cellpadding="0" cellspacing="0" style="background:#141420;border-radius:12px;overflow:hidden;">
    <tr><td style="background:#1A1A2E;padding:24px 32px;">
      <span style="color:#7B61FF;font-size:20px;font-weight:700;">SignalForgeAI</span>
    </td></tr>
    <tr><td style="padding:32px;color:#F0F0F5;font-size:15px;line-height:1.6;">
      <h2 style="color:#F0F0F5;margin:0 0 16px;">${title}</h2>
      ${body}
    </td></tr>
    <tr><td style="padding:20px 32px;border-top:1px solid #2A2A3E;color:#888;font-size:12px;text-align:center;">
      &copy; ${new Date().getFullYear()} SignalForgeAI. All rights reserved.
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>`
}
