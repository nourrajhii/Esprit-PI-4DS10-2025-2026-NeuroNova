const mongoose = require('mongoose')

const ContactSchema = new mongoose.Schema({
  listing: { type: mongoose.Schema.Types.ObjectId, ref: 'Listing', required: true },
  sender:  { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  seller:  { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  message: { type: String, required: true },
  phone:   { type: String },
  status:  { type: String, enum: ['pending', 'read', 'replied'], default: 'pending' },
  createdAt: { type: Date, default: Date.now },
})

module.exports = mongoose.model('Contact', ContactSchema)
