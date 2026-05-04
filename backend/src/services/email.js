const nodemailer = require('nodemailer')

const transporter = nodemailer.createTransport({
  host:   process.env.SMTP_HOST,
  port:   parseInt(process.env.SMTP_PORT || '587'),
  secure: false,
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,
  },
})

const APP_NAME = process.env.SMTP_APP_NAME || 'EstateMind'
const FROM     = `${APP_NAME} <${process.env.SMTP_USER}>`

async function sendEmail({ to, subject, html }) {
  await transporter.sendMail({ from: FROM, to, subject, html })
}

async function sendWelcomeEmail(user) {
  await sendEmail({
    to:      user.email,
    subject: `Bienvenue sur ${APP_NAME} 🏠`,
    html: `
      <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px">
        <h1 style="color:#00204a">Bienvenue ${user.name} !</h1>
        <p>Votre compte a été créé avec succès.</p>
        <p>Explorez les meilleures opportunités immobilières en Tunisie.</p>
        <a href="${process.env.FRONTEND_URL}" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#00204a;color:#fff;border-radius:8px;text-decoration:none">
          Accéder à la plateforme
        </a>
        <hr style="margin-top:32px;border:none;border-top:1px solid #e2e8f0">
        <p style="color:#94a3b8;font-size:12px">${APP_NAME} — Plateforme Immobilière Intelligente Tunisie</p>
      </div>
    `,
  })
}

async function sendSubscriptionConfirmEmail(user) {
  await sendEmail({
    to:      user.email,
    subject: '✅ Abonnement Investisseur Premium activé !',
    html: `
      <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px">
        <h1 style="color:#16a34a">Abonnement activé !</h1>
        <p>Bonjour ${user.name},</p>
        <p>Votre abonnement <strong>Investisseur Premium</strong> à 20 TND/mois est maintenant actif.</p>
        <p>Vous recevrez désormais des alertes pour chaque nouvelle annonce de vente.</p>
        <a href="${process.env.FRONTEND_URL}" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#16a34a;color:#fff;border-radius:8px;text-decoration:none">
          Accéder à votre espace
        </a>
      </div>
    `,
  })
}

async function sendContactNotificationEmail(seller, contact, listing) {
  await sendEmail({
    to:      seller.email,
    subject: `📩 Nouvelle demande sur votre annonce — ${listing.title}`,
    html: `
      <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px">
        <h2 style="color:#00204a">Nouvelle demande de contact</h2>
        <p>Quelqu'un est intéressé par votre annonce <strong>${listing.title}</strong>.</p>
        <p><strong>Message :</strong></p>
        <blockquote style="border-left:4px solid #00204a;padding:12px;background:#f0f9ff;border-radius:4px">
          ${contact.message}
        </blockquote>
        ${contact.phone ? `<p><strong>Téléphone :</strong> ${contact.phone}</p>` : ''}
        <a href="${process.env.FRONTEND_URL}/dashboard/contacts" style="display:inline-block;margin-top:16px;padding:12px 24px;background:#00204a;color:#fff;border-radius:8px;text-decoration:none">
          Voir les demandes
        </a>
      </div>
    `,
  })
}

module.exports = {
  sendEmail,
  sendWelcomeEmail,
  sendSubscriptionConfirmEmail,
  sendContactNotificationEmail,
}
