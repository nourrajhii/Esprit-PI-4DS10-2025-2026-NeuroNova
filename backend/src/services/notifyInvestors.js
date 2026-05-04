const { User } = require('../models')
const { sendEmail } = require('./email')
const twilio = require('twilio')

let twilioClient = null
function getClient() {
  if (!twilioClient) {
    twilioClient = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN)
  }
  return twilioClient
}

async function notifyInvestors(listing) {
  try {
    const investors = await User.find({
      role: 'investor',
      'subscription.status': 'active',
      $or: [
        { 'subscription.expiresAt': { $gt: new Date() } },
        { 'subscription.expiresAt': null },
      ],
    })

    for (const investor of investors) {
      const listingUrl = `${process.env.FRONTEND_URL}/annonces/${listing._id}`

      sendEmail({
        to: investor.email,
        subject: `🏠 Nouvelle opportunité : ${listing.title}`,
        html: `
          <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px">
            <h2 style="color:#00204a">Nouvelle annonce de vente sur EstateMind</h2>
            <h3>${listing.title}</h3>
            <table style="width:100%;border-collapse:collapse">
              <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0"><strong>Ville</strong></td><td style="padding:8px;border-bottom:1px solid #e2e8f0">${listing.city}</td></tr>
              <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0"><strong>Prix</strong></td><td style="padding:8px;border-bottom:1px solid #e2e8f0">${Number(listing.price).toLocaleString('fr-TN')} TND</td></tr>
              <tr><td style="padding:8px"><strong>Surface</strong></td><td style="padding:8px">${listing.surface || 'N/A'} m²</td></tr>
            </table>
            <a href="${listingUrl}" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#00204a;color:#fff;border-radius:8px;text-decoration:none">
              Voir l'annonce
            </a>
            <hr style="margin-top:32px;border:none;border-top:1px solid #e2e8f0">
            <p style="color:#94a3b8;font-size:12px">EstateMind — Vous recevez cet email car vous êtes investisseur premium.</p>
          </div>
        `,
      }).catch(e => console.warn('[notifyInvestors email]', e.message))

      if (investor.phone) {
        getClient().messages.create({
          from: process.env.TWILIO_WHATSAPP_FROM,
          to: `whatsapp:${investor.phone}`,
          body: `🏠 Nouvelle annonce de vente sur EstateMind !\n${listing.title}\n${listing.city} — ${Number(listing.price).toLocaleString()} TND\nVoir : ${listingUrl}`,
        }).catch(e => console.warn('[notifyInvestors WhatsApp]', e.message))
      }
    }
  } catch (err) {
    console.warn('[notifyInvestors]', err.message)
  }
}

module.exports = { notifyInvestors }
