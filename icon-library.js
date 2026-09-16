/**
 * Icon lookup over the local noun-icons.json cache.
 *
 * This replaces the old Freepik API client. Nothing here talks to an API:
 * the 1,246 icons in noun-icons.json were resolved once in January 2026 and
 * the CDN still serves them (freepik.com now 301s to magnific.com), so a key,
 * a proxy and a subscription are all beside the point.
 *
 * The old client defaulted to a localhost proxy, which meant every visitor's
 * browser called their own machine and got nothing -- these pages have never
 * shown an icon to anyone but the author. Reading the cache fixes that.
 *
 *   const icons = new IconLibrary();
 *   const hit = await icons.searchAndGetIcon('butter', 128);
 *   if (hit) img.src = hit.pngUrl;
 */

/**
 * Hand-picked stand-ins for phrases the noun list does not hold.
 *
 * The cache is 1,246 Spanish *nouns*, so abstractions and compounds miss.
 * Only aliased where the substitute actually reads as the thing -- cinnamon,
 * oatmeal, vanilla and "shopping bag" are deliberately left to miss, because
 * the nearest cached icons (a tree, a bowl of soup, a dessert, a second
 * market) would say the wrong thing more loudly than an empty slot does.
 */
const ICON_ALIASES = {
    'speech bubble talk': 'message',
    'fist punch': 'boxing',
    'rocket fast': 'speed',
    'binoculars focus': 'glasses',
    'like thumb': 'hand',
    'feather soft': 'pillow',
    'hammer impact': 'tool',
    'worry anxious': 'sadness',   // not 'fear' -- the same page uses that at
                                  // the other end of the gradient
    'bench': 'seat',
    'children': 'girl',
};

class IconLibrary {
    constructor(src = '/noun-icons.json') {
        this.src = src;
        this.byTerm = null;
        this.loading = null;
    }

    /** Index English term -> icon. Loaded once, shared by every lookup. */
    async load() {
        if (this.byTerm) return this.byTerm;
        if (!this.loading) {
            this.loading = fetch(this.src)
                .then(r => r.json())
                .then(data => {
                    const byTerm = new Map();
                    for (const entry of Object.values(data)) {
                        const en = (entry.en || '').trim().toLowerCase();
                        if (en && entry.icon && entry.icon.url && !byTerm.has(en)) {
                            byTerm.set(en, entry.icon);
                        }
                    }
                    this.byTerm = byTerm;
                    return byTerm;
                })
                .catch(() => (this.byTerm = new Map()));
        }
        return this.loading;
    }

    /**
     * Resolve a search phrase to an icon, or null.
     *
     * Pages ask for things the noun list does not hold verbatim -- "salt
     * shaker", "coffee cup flat color", "heart love". So: try the whole
     * phrase, then each word in it, then a substring match either way.
     */
    async find(term) {
        const byTerm = await this.load();
        const phrase = (term || '')
            .toLowerCase()
            .replace(/\bflat color\b/g, '')
            .replace(/[^a-z0-9 ]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
        if (!phrase) return null;

        if (byTerm.has(phrase)) return byTerm.get(phrase);
        const alias = ICON_ALIASES[phrase];
        if (alias && byTerm.has(alias)) return byTerm.get(alias);
        for (const word of phrase.split(' ')) {
            if (byTerm.has(word)) return byTerm.get(word);
        }
        for (const [key, icon] of byTerm) {
            if (key.includes(phrase) || phrase.includes(key)) return icon;
        }
        return null;
    }

    /**
     * The one method the pages call. Same shape the old client returned, so
     * the call sites did not have to change: {pngUrl, id, name, ...} or null.
     *
     * The cached URLs are 128px; the CDN serves 256 and 512 from the same
     * path, so the size is a substitution rather than another lookup.
     */
    async searchAndGetIcon(term, size = 512) {
        const icon = await this.find(term);
        if (!icon) return null;
        return {
            ...icon,
            pngUrl: icon.url.replace(/\/(128|256|512)\//, `/${size}/`),
        };
    }

    /** How many terms the cache can answer -- handy from the console. */
    async count() {
        return (await this.load()).size;
    }
}
