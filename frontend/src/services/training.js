/**
 * Training API Service
 * Handles all training-related API calls
 */

const API_BASE = '/api/training'

export const trainingService = {
    /**
     * Start training for a specific bot
     */
    async startTraining(symbol, timeframe, botName, options = {}) {
        const response = await fetch(`${API_BASE}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol,
                timeframe,
                bot_name: botName,
                epochs: options.epochs || 50,
                batch_size: options.batchSize || 200,
                fetch_latest_data: options.fetchLatestData !== false
            })
        })

        if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Failed to start training')
        }

        return response.json()
    },

    /**
     * Stop/cancel a training session
     */
    async stopTraining(trainingId, reason = 'user_requested') {
        const response = await fetch(`${API_BASE}/stop/${trainingId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason })
        })

        if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Failed to stop training')
        }

        return response.json()
    },

    /**
     * Get status of a specific training session
     */
    async getTrainingStatus(trainingId) {
        const response = await fetch(`${API_BASE}/status/${trainingId}`)

        if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Failed to get training status')
        }

        return response.json()
    },

    /**
     * Get training history with optional filters
     */
    async getTrainingHistory(filters = {}) {
        const params = new URLSearchParams()

        if (filters.symbol) params.append('symbol', filters.symbol)
        if (filters.timeframe) params.append('timeframe', filters.timeframe)
        if (filters.botName) params.append('bot_name', filters.botName)
        if (filters.status) params.append('status', filters.status)
        if (filters.limit) params.append('limit', filters.limit)

        const response = await fetch(`${API_BASE}/history?${params}`)

        if (!response.ok) {
            throw new Error('Failed to fetch training history')
        }

        return response.json()
    },

    /**
     * Get status of all models for a symbol/timeframe
     */
    async getModelsStatus(symbol, timeframe = '5m') {
        const params = new URLSearchParams({ symbol, timeframe })
        const response = await fetch(`${API_BASE}/models/status?${params}`)

        if (!response.ok) {
            throw new Error('Failed to fetch models status')
        }

        return response.json()
    },

    /**
     * Get all active training sessions
     */
    async getActiveTrainings() {
        const response = await fetch(`${API_BASE}/active`)

        if (!response.ok) {
            throw new Error('Failed to fetch active trainings')
        }

        return response.json()
    },

    /**
     * Train a bot using the existing prediction/train endpoint
     */
    async trainBot(symbol, timeframe, botName, epochs = 50, batchSize = 200) {
        const response = await fetch('/api/prediction/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol,
                timeframe,
                bot_name: botName,
                epochs,
                batch_size: batchSize
            })
        })

        if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Failed to train bot')
        }

        return response.json()
    }
}
