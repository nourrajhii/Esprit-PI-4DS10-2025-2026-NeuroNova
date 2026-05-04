const mongoose = require('mongoose')

const UserSchema = new mongoose.Schema({
  name:     { type: String, required: true },
  email:    { type: String, required: true, unique: true, lowercase: true, trim: true },
  phone:    { type: String },
  password: { type: String, required: true },
  role:     { type: String, enum: ['admin', 'seller', 'investor', 'user'], default: 'user' },
  refreshToken: { type: String },
  subscription: {
    status:               { type: String, enum: ['active', 'inactive', 'cancelled', 'pending', 'past_due'], default: 'inactive' },
    stripeCustomerId:     { type: String },
    stripeSubscriptionId: { type: String },
    stripeSessionId:      { type: String },
    plan:                 { type: String, default: 'premium' },
    amount:               { type: Number, default: 20 },
    expiresAt:            { type: Date },
  },
  isActive:  { type: Boolean, default: true },
  createdAt: { type: Date, default: Date.now },
})

module.exports = mongoose.model('User', UserSchema)
