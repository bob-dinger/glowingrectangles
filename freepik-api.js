/**
 * Freepik API Utility for Glowing Gardens
 *
 * IMPORTANT: SVG downloads cost 150 credits each.
 * PNG thumbnails (128, 256, 512px) are free to use in searches.
 *
 * Usage:
 *   const freepik = new FreepikAPI('YOUR_API_KEY');
 *
 *   // Search for icons (returns PNG thumbnails)
 *   const icons = await freepik.searchIcons('cooking');
 *
 *   // Get icon PNG URL (free, no credits)
 *   const pngUrl = icons[0].thumbnails[2].url; // 512px
 *
 *   // Download SVG (costs 150 credits!)
 *   const svgUrl = await freepik.downloadIcon(iconId, 'svg');
 */

class FreepikAPI {
    constructor(apiKey, useProxy = true) {
        this.apiKey = apiKey;
        // Use local proxy to avoid CORS issues in browser
        this.baseUrl = useProxy ? 'http://localhost:3002' : 'https://api.freepik.com/v1';
        this.useProxy = useProxy;
        this.cache = new Map();
        this.cacheTimeout = 14 * 60 * 1000; // 14 minutes
    }

    /**
     * Make authenticated API request
     */
    async request(endpoint, options = {}) {
        const headers = {
            'Accept': 'application/json',
            ...options.headers
        };

        // Only add API key header when not using proxy (proxy handles it)
        if (!this.useProxy) {
            headers['x-freepik-api-key'] = this.apiKey;
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`API request failed: ${response.status} - ${error}`);
        }

        return response.json();
    }

    /**
     * Search for icons
     * @param {string} term - Search term
     * @param {object} options - { limit, page, style, family }
     * @returns {Promise<Array>} - Array of icon objects with thumbnails
     */
    async searchIcons(term, options = {}) {
        const {
            limit = 20,
            page = 1,
            style = null,      // style ID
            family = null      // family ID
        } = options;

        let endpoint = `/icons?term=${encodeURIComponent(term)}&limit=${limit}&page=${page}`;
        if (style) endpoint += `&filters[style]=${style}`;
        if (family) endpoint += `&filters[family]=${family}`;

        const result = await this.request(endpoint);
        return result.data || [];
    }

    /**
     * Get icon details
     * @param {number} iconId - Icon ID
     * @returns {Promise<object>} - Icon details with related icons
     */
    async getIcon(iconId) {
        const result = await this.request(`/icons/${iconId}`);
        return result.data;
    }

    /**
     * Download icon (costs credits for SVG!)
     * @param {number} iconId - Icon ID
     * @param {string} format - 'png' (free) or 'svg' (150 credits!)
     * @returns {Promise<string>} - Download URL
     */
    async downloadIcon(iconId, format = 'png') {
        const endpoint = format === 'svg'
            ? `/icons/${iconId}/download?format=svg`
            : `/icons/${iconId}/download`;

        const result = await this.request(endpoint);
        return result.data?.url || null;
    }

    /**
     * Search for general resources (photos, vectors, etc.)
     * @param {string} term - Search term
     * @param {object} options - { limit, page, type }
     * @returns {Promise<Array>} - Array of resources
     */
    async searchResources(term, options = {}) {
        const {
            limit = 20,
            page = 1,
            type = null  // 'vector', 'photo', 'psd'
        } = options;

        let endpoint = `/resources?term=${encodeURIComponent(term)}&limit=${limit}&page=${page}`;
        if (type) endpoint += `&filters[type]=${type}`;

        const result = await this.request(endpoint);
        return result.data || [];
    }

    /**
     * Get PNG thumbnail URL for an icon (no credits needed)
     * @param {object} icon - Icon object from search
     * @param {number} size - 128, 256, or 512
     * @returns {string} - PNG URL
     */
    getThumbnailUrl(icon, size = 512) {
        const thumbnail = icon.thumbnails?.find(t => t.width === size);
        return thumbnail?.url || icon.thumbnails?.[0]?.url;
    }

    /**
     * Search and get first matching icon with PNG URL
     * @param {string} term - Search term
     * @param {number} size - Thumbnail size (128, 256, 512)
     * @returns {Promise<{id, name, pngUrl, icon}>}
     */
    async searchAndGetIcon(term, size = 512) {
        const icons = await this.searchIcons(term, { limit: 1 });
        if (icons.length === 0) return null;

        const icon = icons[0];
        const pngUrl = this.getThumbnailUrl(icon, size);

        return { id: icon.id, name: icon.name, pngUrl, icon };
    }

    /**
     * Batch search for multiple terms
     * @param {Array<string>} terms - Array of search terms
     * @param {number} size - Thumbnail size
     * @returns {Promise<Map<string, object>>} - Map of term -> result
     */
    async batchSearch(terms, size = 512) {
        const results = new Map();

        // Process 5 at a time
        const batchSize = 5;
        for (let i = 0; i < terms.length; i += batchSize) {
            const batch = terms.slice(i, i + batchSize);
            const promises = batch.map(term => this.searchAndGetIcon(term, size));
            const batchResults = await Promise.all(promises);

            batch.forEach((term, idx) => {
                results.set(term, batchResults[idx]);
            });
        }

        return results;
    }

    /**
     * Get available icon styles
     * @returns {Promise<Array>} - Array of style objects
     */
    async getStyles() {
        const result = await this.request('/icons/styles');
        return result.data || [];
    }

    /**
     * Get icon families (icon packs)
     * @param {object} options - { limit, page, term }
     * @returns {Promise<Array>} - Array of family objects
     */
    async getFamilies(options = {}) {
        const { limit = 20, page = 1, term = null } = options;
        let endpoint = `/icons/families?limit=${limit}&page=${page}`;
        if (term) endpoint += `&term=${encodeURIComponent(term)}`;

        const result = await this.request(endpoint);
        return result.data || [];
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FreepikAPI;
}
