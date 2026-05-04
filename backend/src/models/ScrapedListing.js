const { getScrapedConn } = require('../config/scrapedDatabase')

const schema = new (require('mongoose').Schema)({
  title:            String,
  price:            Number,
  currency:         String,
  city:             String,
  zone:             String,
  property_type:    String,
  transaction_type: String,
  surface_m2:       Number,
  rooms:            Number,
  bathrooms:        Number,
  description:      String,
  agency_owner:     String,
  phone:            String,
  listing_url:      String,
  image_urls:       [String],
  published_date:   Date,
  scraped_at:       Date,
}, { collection: 'listings', strict: false })

function getModel() {
  const conn = getScrapedConn()
  if (!conn) return null
  if (conn.models['ScrapedListing']) return conn.models['ScrapedListing']
  return conn.model('ScrapedListing', schema)
}

module.exports = { getModel }
