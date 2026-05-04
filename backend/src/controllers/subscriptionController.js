const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY)
const { User } = require('../models')
const { sendSubscriptionConfirmEmail } = require('../services/email')
const { sendSubscriptionWhatsApp } = require('../services/sms')

async function createCheckout(req, res) {
  try {
    const user = await User.findById(req.user.id)
    if (!user) return res.status(404).json({ error: 'Utilisateur introuvable' })

    if (user.subscription && user.subscription.status === 'active') {
      const stillActive = !user.subscription.expiresAt || user.subscription.expiresAt > new Date()
      if (stillActive) return res.status(400).json({ error: 'Vous avez déjà un abonnement actif' })
    }

    let customerId = user.subscription?.stripeCustomerId || null
    if (!customerId) {
      const customer = await stripe.customers.create({
        email: user.email,
        name:  user.name,
        metadata: { userId: user.id },
      })
      customerId = customer.id
    }

    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      payment_method_types: ['card'],
      mode: 'subscription',
      line_items: [{
        price_data: {
          currency: 'eur',
          product_data: {
            name: 'Abonnement Investisseur Premium — EstateMind',
            description: 'Accès illimité aux agents IA + alertes nouvelles annonces',
          },
          unit_amount: 600,
          recurring: { interval: 'month' },
        },
        quantity: 1,
      }],
      success_url: `${process.env.FRONTEND_URL}/subscription/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url:  `${process.env.FRONTEND_URL}/subscription/cancel`,
      metadata: { userId: user.id },
    })

    await User.findByIdAndUpdate(user._id, {
      'subscription.stripeCustomerId': customerId,
      'subscription.stripeSessionId':  session.id,
      'subscription.status':           'pending',
      'subscription.plan':             'premium',
      'subscription.amount':           6,
    })

    return res.json({ url: session.url, sessionId: session.id })
  } catch (err) {
    console.error('[stripe.checkout]', err)
    return res.status(500).json({ error: 'Erreur Stripe : ' + err.message })
  }
}

async function getStatus(req, res) {
  try {
    const user = await User.findById(req.user.id).select('subscription')
    if (!user || !user.subscription) return res.json({ active: false, plan: null })

    const sub    = user.subscription
    const active = sub.status === 'active' &&
      (!sub.expiresAt || sub.expiresAt > new Date())

    return res.json({
      active,
      status:         sub.status,
      plan:           sub.plan,
      currentPeriodEnd: sub.expiresAt,
      amount:         sub.amount,
    })
  } catch (err) {
    return res.status(500).json({ error: 'Erreur serveur' })
  }
}

async function webhook(req, res) {
  const sig = req.headers['stripe-signature']
  let event
  try {
    event = stripe.webhooks.constructEvent(req.body, sig, process.env.STRIPE_WEBHOOK_SECRET)
  } catch (err) {
    console.error('[webhook] Signature invalide:', err.message)
    return res.status(400).send(`Webhook Error: ${err.message}`)
  }

  try {
    if (event.type === 'checkout.session.completed') {
      const session = event.data.object
      const userId  = session.metadata?.userId
      if (!userId) return res.json({ received: true })

      const expiresAt = session.expires_at
        ? new Date(session.expires_at * 1000)
        : new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)

      await User.findByIdAndUpdate(userId, {
        role: 'investor',
        'subscription.stripeSubscriptionId': session.subscription,
        'subscription.stripeCustomerId':     session.customer,
        'subscription.status':               'active',
        'subscription.expiresAt':            expiresAt,
      })

      const user = await User.findById(userId)
      if (user) {
        sendSubscriptionConfirmEmail(user).catch(e => console.warn('[Email]', e.message))
        if (user.phone) sendSubscriptionWhatsApp(user).catch(e => console.warn('[WhatsApp]', e.message))
      }
    }

    if (event.type === 'customer.subscription.deleted' ||
        event.type === 'customer.subscription.paused') {
      const subscription = event.data.object
      const user = await User.findOne({ 'subscription.stripeSubscriptionId': subscription.id })
      if (user) {
        await User.findByIdAndUpdate(user._id, {
          role: 'user',
          'subscription.status': 'cancelled',
        })
      }
    }

    if (event.type === 'invoice.payment_failed') {
      const invoice = event.data.object
      const user = await User.findOne({ 'subscription.stripeSubscriptionId': invoice.subscription })
      if (user) {
        await User.findByIdAndUpdate(user._id, { 'subscription.status': 'past_due' })
      }
    }

    return res.json({ received: true })
  } catch (err) {
    console.error('[webhook.handler]', err)
    return res.status(500).json({ error: 'Erreur webhook' })
  }
}

async function verifySession(req, res) {
  try {
    const { session_id } = req.query
    if (!session_id) return res.status(400).json({ error: 'session_id requis' })

    const session = await stripe.checkout.sessions.retrieve(session_id)
    if (session.payment_status === 'paid') {
      const userId = session.metadata?.userId
      if (userId) {
        await User.findByIdAndUpdate(userId, {
          role: 'investor',
          'subscription.stripeSubscriptionId': session.subscription,
          'subscription.stripeCustomerId':     session.customer,
          'subscription.status':               'active',
        })
      }
      return res.json({ success: true, status: 'active' })
    }
    return res.json({ success: false, status: session.payment_status })
  } catch (err) {
    return res.status(500).json({ error: err.message })
  }
}

module.exports = { createCheckout, getStatus, webhook, verifySession }
