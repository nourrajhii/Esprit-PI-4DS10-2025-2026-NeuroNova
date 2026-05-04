const mongoose = require('mongoose')

let scrapedConn = null

async function connectScrapedDB() {
  if (!process.env.SCRAPED_DB_URI) return null
  try {
    scrapedConn = await mongoose.createConnection(process.env.SCRAPED_DB_URI).asPromise()
    console.log('✅ Scraped MongoDB connecté (dcrawl)')
    return scrapedConn
  } catch (err) {
    console.warn('⚠️  Scraped MongoDB indisponible:', err.message)
    return null
  }
}

function getScrapedConn() { return scrapedConn }

module.exports = { connectScrapedDB, getScrapedConn }
