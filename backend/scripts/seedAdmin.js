require('dotenv').config({ path: require('path').join(__dirname, '../.env') })
const mongoose = require('mongoose')
const bcrypt   = require('bcryptjs')

const User = require('../src/models/User')

async function seedAdmin() {
  if (mongoose.connection.readyState === 0) {
    await mongoose.connect(process.env.MONGODB_URI)
  }

  // ── Admin — use $set so refreshToken/session data is never wiped ──────────
  const adminHash = await bcrypt.hash('Admin@1234', 10)
  const admin = await User.findOneAndUpdate(
    { email: 'admin@estatemind.com' },
    {
      $set: {
        name:     'Administrateur',
        email:    'admin@estatemind.com',
        phone:    '+21600000000',
        password: adminHash,
        role:     'admin',
        isActive: true,
      },
    },
    { upsert: true, new: true }
  )
  console.log('✅ Admin créé/vérifié:', admin.email)

  // ── Investisseur de test ───────────────────────────────────────────────────
  const investorHash = await bcrypt.hash('Invest@1234', 10)
  const investor = await User.findOneAndUpdate(
    { email: 'investor@test.com' },
    {
      $set: {
        name:  'Test Investisseur',
        email: 'investor@test.com',
        phone: '+21611111111',
        password: investorHash,
        role:     'investor',
        isActive: true,
        subscription: {
          status:    'active',
          expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
        },
      },
    },
    { upsert: true, new: true }
  )
  console.log('✅ Investisseur test créé/vérifié:', investor.email)

  if (require.main === module) {
    await mongoose.disconnect()
  }
}

module.exports = { seedAdmin }

if (require.main === module) {
  seedAdmin().catch(err => {
    console.error('❌ Erreur seedAdmin:', err)
    process.exit(1)
  })
}
