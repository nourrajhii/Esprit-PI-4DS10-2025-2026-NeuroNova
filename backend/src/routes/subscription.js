const router = require('express').Router()
const ctrl = require('../controllers/subscriptionController')
const { authenticate } = require('../middlewares/auth')
const express = require('express')

// Stripe webhook needs raw body — registered separately in server.js
// POST /subscription/webhook is registered in server.js BEFORE json middleware

router.post('/subscribe',       authenticate, ctrl.createCheckout)
router.get('/status',           authenticate, ctrl.getStatus)
router.get('/verify',           authenticate, ctrl.verifySession)

module.exports = router
