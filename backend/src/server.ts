import fs from 'node:fs'
import { createApp } from './app.js'
import express from 'express'
import dotenv from 'dotenv'

dotenv.config()

const uploadDir = process.env.UPLOAD_DIR ?? './uploads'
const port = Number(process.env.PORT ?? 4000)

if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true })

const app = createApp()
app.use('/static', express.static(uploadDir))

app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`REAL backend listening on http://localhost:${port}`)
})

