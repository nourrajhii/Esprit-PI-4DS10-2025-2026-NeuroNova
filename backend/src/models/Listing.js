const mongoose = require('mongoose')

const ListingSchema = new mongoose.Schema({
  title:       { type: String, required: true },
  description: { type: String },
  type:        { type: String, enum: ['vente', 'location'], required: true },
  price:       { type: Number, required: true },
  surface:     { type: Number },
  rooms:       { type: Number },
  city:        { type: String, required: true },
  address:     { type: String },
  location: {
    type:        { type: String, default: 'Point' },
    coordinates: { type: [Number], default: [0, 0] },
  },
  images:      [String],
  status:      { type: String, enum: ['active', 'pending', 'sold', 'rented'], default: 'active' },
  source:      { type: String, default: 'internal' },
  externalUrl: { type: String },
  seller:      { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  createdAt:   { type: Date, default: Date.now },
})

ListingSchema.index({ location: '2dsphere' })
ListingSchema.index({ title: 'text', city: 'text', address: 'text', description: 'text' })

module.exports = mongoose.model('Listing', ListingSchema)
