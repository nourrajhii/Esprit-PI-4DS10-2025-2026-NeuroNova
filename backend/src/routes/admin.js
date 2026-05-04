const router = require('express').Router()
const ctrl = require('../controllers/adminController')
const { authenticate, authorize } = require('../middlewares/auth')

router.use(authenticate, authorize('admin'))

router.get('/stats',              ctrl.stats)
router.get('/users',              ctrl.listUsers)
router.patch('/users/:id/role',   ctrl.updateUserRole)
router.patch('/users/:id/deactivate', ctrl.deactivateUser)

module.exports = router
