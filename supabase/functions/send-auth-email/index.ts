/**
 * Supabase Auth Email Hook — sends all auth emails (OTP, recovery, etc.)
 * via MetaNet SMTP instead of Supabase's built-in mailer.
 *
 * Configured in Supabase Auth → Hooks → Send Email Hook
 * Must verify the webhook signature using SEND_EMAIL_HOOK_SECRET.
 */

import nodemailer from 'npm:nodemailer@6'

const HOOK_SECRET = Deno.env.get('SEND_EMAIL_HOOK_SECRET') ?? ''
const SITE_URL = Deno.env.get('APP_URL') ?? 'https://signalforgeai.predivo.ch'

// ── SMTP Transport ────────────────────────────────────────
let _transporter: ReturnType<typeof nodemailer.createTransport> | null = null

function getTransporter() {
  if (_transporter) return _transporter

  const host = Deno.env.get('SMTP_HOST')
  const port = parseInt(Deno.env.get('SMTP_PORT') ?? '587', 10)
  const user = Deno.env.get('SMTP_USER')
  const pass = Deno.env.get('SMTP_PASS')

  if (!host || !user || !pass) {
    throw new Error('Missing SMTP configuration (SMTP_HOST, SMTP_USER, SMTP_PASS)')
  }

  _transporter = nodemailer.createTransport({
    host,
    port,
    secure: port === 465,
    auth: { user, pass },
    tls: { rejectUnauthorized: false },
  })

  return _transporter
}

async function sendEmail(to: string, subject: string, html: string): Promise<void> {
  const from = Deno.env.get('SMTP_FROM') ?? Deno.env.get('SMTP_USER') ?? 'SignalForgeAI <noreply@signalforgeai.predivo.ch>'
  const transporter = getTransporter()
  await transporter.sendMail({
    from,
    to,
    subject,
    html,
    text: html.replace(/<[^>]*>/g, ''),
  })
}

// ── Payload types ─────────────────────────────────────────
interface AuthEmailPayload {
  user: {
    email: string
    user_metadata?: Record<string, unknown>
  }
  email_data: {
    token: string
    token_hash: string
    redirect_to: string
    email_action_type: string
    site_url: string
    token_new?: string
    token_hash_new?: string
  }
}

// ── Branded HTML wrapper ──────────────────────────────────
function emailWrapper(title: string, body: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"/><meta name="viewport" content="width=device-width"/></head>
<body style="margin:0;padding:0;background:#0B0B14;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0B0B14;">
<tr><td align="center" style="padding:40px 20px;">
  <table width="560" cellpadding="0" cellspacing="0" style="background:#141420;border-radius:12px;overflow:hidden;">
    <tr><td style="background:#1A1A2E;padding:24px 32px;">
      <span style="color:#7B61FF;font-size:20px;font-weight:700;">SignalForgeAI</span>
    </td></tr>
    <tr><td style="padding:32px;color:#F0F0F5;font-size:15px;line-height:1.6;">
      <h2 style="color:#F0F0F5;margin:0 0 16px;font-size:22px;">${title}</h2>
      ${body}
    </td></tr>
    <tr><td style="padding:20px 32px;border-top:1px solid #2A2A3E;color:#888;font-size:12px;text-align:center;">
      &copy; ${new Date().getFullYear()} SignalForgeAI by Predivo GmbH. All rights reserved.<br/>
      Swiss-made
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>`
}

function otpBlock(token: string): string {
  return `<div style="margin:20px 0;padding:20px;background:#1A1A2E;border:1px solid #7B61FF44;border-radius:8px;text-align:center;">
  <p style="color:#888;margin:0 0 8px;font-size:13px;">Your verification code</p>
  <p style="font-size:32px;font-weight:700;letter-spacing:8px;color:#7B61FF;margin:0;font-family:'Courier New',monospace;">${token}</p>
  <p style="color:#666;margin:8px 0 0;font-size:12px;">Valid for 10 minutes</p>
</div>`
}

function buttonBlock(text: string, url: string): string {
  return `<div style="margin:24px 0;">
  <a href="${url}" style="display:inline-block;background:#7B61FF;color:#ffffff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">${text}</a>
</div>`
}

// ── Build action URL ──────────────────────────────────────
function buildActionUrl(payload: AuthEmailPayload): string {
  const { token_hash, email_action_type, redirect_to } = payload.email_data
  const type = email_action_type === 'signup' ? 'signup' :
               email_action_type === 'recovery' ? 'recovery' :
               email_action_type === 'invite' ? 'invite' :
               email_action_type === 'magiclink' ? 'magiclink' :
               email_action_type === 'email_change' ? 'email_change' :
               email_action_type
  const redirectTo = redirect_to || `${SITE_URL}/auth/callback`
  // Never use site_url — GoTrue's site_url includes '/auth/v1' causing doubled paths
  const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? ''
  return `${supabaseUrl}/auth/v1/verify?token=${token_hash}&type=${type}&redirect_to=${encodeURIComponent(redirectTo)}`
}

// ── Email content per type ────────────────────────────────
function getEmailContent(payload: AuthEmailPayload): { subject: string; html: string } {
  const { email_action_type, token } = payload.email_data
  const actionUrl = buildActionUrl(payload)
  const verifyUrl = `${SITE_URL}/auth/verify?token=${token}&email=${encodeURIComponent(payload.user.email)}&type=${email_action_type === 'signup' ? 'signup' : 'login'}`

  switch (email_action_type) {
    case 'signup':
      return {
        subject: 'SignalForgeAI \u2013 Your verification code: ' + token,
        html: emailWrapper('Verify your email', `
          <p style="color:#C0C0D0;">Enter this code on the signup page to verify your email and create your account:</p>
          ${otpBlock(token)}
          <p style="color:#666;font-size:13px;">If you didn't create an account, you can safely ignore this email.</p>
        `),
      }

    case 'magiclink':
      return {
        subject: 'Your SignalForgeAI login code: ' + token,
        html: emailWrapper('Sign in to SignalForgeAI', `
          <p style="color:#C0C0D0;">Enter this code on the login page to sign in to your account:</p>
          ${otpBlock(token)}
          <p style="color:#666;font-size:13px;">If you didn't request this, you can safely ignore this email.</p>
        `),
      }

    case 'recovery':
      return {
        subject: 'Reset your SignalForgeAI password',
        html: emailWrapper('Reset your password', `
          <p style="color:#C0C0D0;">We received a request to reset the password for your SignalForgeAI account. Click the button below to set a new password.</p>
          ${buttonBlock('Reset Password', actionUrl)}
          <p style="color:#666;font-size:13px;">If you didn't request this, you can safely ignore this email. Your password will not be changed.</p>
        `),
      }

    case 'email_change':
      return {
        subject: 'Confirm your email change',
        html: emailWrapper('Confirm Email Change', `
          <p style="color:#C0C0D0;">You requested to change the email address on your SignalForgeAI account. Click the button below to confirm.</p>
          ${buttonBlock('Confirm Email Change', actionUrl)}
          <p style="color:#666;font-size:13px;">If you didn't make this change, please secure your account immediately.</p>
        `),
      }

    case 'invite':
      return {
        subject: "You've been invited to SignalForgeAI",
        html: emailWrapper('You\'ve been invited', `
          <p style="color:#C0C0D0;">You've been invited to join SignalForgeAI. Click the button below to accept the invitation and set up your account.</p>
          ${buttonBlock('Accept Invitation', actionUrl)}
        `),
      }

    default:
      return {
        subject: 'SignalForgeAI: Action required',
        html: emailWrapper('Action Required', `
          <p style="color:#C0C0D0;">Your verification code is:</p>
          ${otpBlock(token)}
          ${buttonBlock('Continue', actionUrl)}
        `),
      }
  }
}

// ── Webhook signature verification ────────────────────────
async function verifySignature(payload: string, signature: string): Promise<boolean> {
  if (!HOOK_SECRET) {
    console.error('SEND_EMAIL_HOOK_SECRET not configured — skipping verification')
    // Allow request through if no secret configured (dev mode)
    return true
  }

  try {
    // Decode base64 secret
    const secretBytes = Uint8Array.from(atob(HOOK_SECRET), c => c.charCodeAt(0))

    const key = await crypto.subtle.importKey(
      'raw',
      secretBytes,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    )

    const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payload))
    const expected = Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('')
    const provided = signature.replace('v1,', '')
    return expected === provided
  } catch (err) {
    console.error('Signature verification error:', (err as Error).message)
    return false
  }
}

// ── Handler ───────────────────────────────────────────────
Deno.serve(async (req) => {
  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'POST only' }), { status: 405 })
  }

  const body = await req.text()

  // Verify webhook signature
  const signature = req.headers.get('x-supabase-webhook-signature') ?? ''
  if (signature && !(await verifySignature(body, signature))) {
    console.error('Invalid webhook signature')
    return new Response(JSON.stringify({ error: 'Invalid signature' }), { status: 401 })
  }

  let payload: AuthEmailPayload
  try {
    payload = JSON.parse(body)
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), { status: 400 })
  }

  const email = payload.user?.email
  if (!email) {
    return new Response(JSON.stringify({ error: 'No email in payload' }), { status: 400 })
  }

  try {
    const { subject, html } = getEmailContent(payload)
    await sendEmail(email, subject, html)
    console.log(`Auth email sent: ${payload.email_data.email_action_type} → ${email}`)
    return new Response(JSON.stringify({}), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (err) {
    console.error(`Failed to send auth email to ${email}:`, (err as Error).message)
    return new Response(
      JSON.stringify({ error: 'Failed to send email' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})
