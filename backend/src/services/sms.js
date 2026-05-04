const twilio = require('twilio')

let client = null
function getClient() {
  if (!client) {
    client = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN)
  }
  return client
}

const APP_NAME = process.env.SMTP_APP_NAME || 'EstateMind'

async function sendWelcomeWhatsApp(user) {
  if (!user.phone) return
  await getClient().messages.create({
    from: process.env.TWILIO_WHATSAPP_FROM,
    to:   `whatsapp:${user.phone}`,
    body: `Bienvenue sur ${APP_NAME} ${user.name} ! 🏠\nVotre compte est activé. Connectez-vous sur ${process.env.FRONTEND_URL}`,
  })
}

async function sendSubscriptionWhatsApp(user) {
  if (!user.phone) return
  await getClient().messages.create({
    from: process.env.TWILIO_WHATSAPP_FROM,
    to:   `whatsapp:${user.phone}`,
    body: `${APP_NAME} : Abonnement Investisseur Premium activé pour ${user.name} ! ✅\nVous recevrez des alertes pour les nouvelles annonces de vente.`,
  })
}

// Legacy SMS fallback (kept for compatibility)
async function sendWelcomeSMS(phone, name) {
  if (!phone) return
  try {
    await getClient().messages.create({
      from: process.env.TWILIO_WHATSAPP_FROM,
      to:   `whatsapp:${phone}`,
      body: `Bienvenue sur ${APP_NAME}, ${name} ! 🏠`,
    })
  } catch (err) {
    console.warn('[WhatsApp] sendWelcomeSMS:', err.message)
  }
}

async function sendSubscriptionSMS(phone, name) {
  if (!phone) return
  try {
    await getClient().messages.create({
      from: process.env.TWILIO_WHATSAPP_FROM,
      to:   `whatsapp:${phone}`,
      body: `${APP_NAME} : Abonnement Premium activé pour ${name} ! ✅`,
    })
  } catch (err) {
    console.warn('[WhatsApp] sendSubscriptionSMS:', err.message)
  }
}

module.exports = { sendWelcomeWhatsApp, sendSubscriptionWhatsApp, sendWelcomeSMS, sendSubscriptionSMS }
