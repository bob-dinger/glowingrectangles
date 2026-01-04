/**
 * Fetch Freepik icon URLs for all Spanish nouns
 *
 * Usage: node fetch-noun-icons.js
 *
 * This script:
 * 1. Reads all nouns from posts/spanish-nouns.html
 * 2. Searches Freepik API for each English translation
 * 3. Saves 512px PNG URLs to noun-icons.json
 */

const fs = require('fs');
const https = require('https');

const API_KEY = 'FPSX98b5430c546d73ef259e47ed0df6eabd';
const BATCH_SIZE = 5;
const DELAY_BETWEEN_BATCHES = 500; // ms

// Extract nouns from the HTML file
function extractNouns() {
    const html = fs.readFileSync('posts/spanish-nouns.html', 'utf8');
    const regex = /\{\s*es:\s*"([^"]+)",\s*en:\s*"([^"]+)"\s*\}/g;
    const nouns = [];
    let match;

    while ((match = regex.exec(html)) !== null) {
        nouns.push({
            es: match[1],
            en: match[2]
        });
    }

    return nouns;
}

// Make API request
function apiRequest(endpoint) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: 'api.freepik.com',
            path: `/v1${endpoint}`,
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'x-freepik-api-key': API_KEY
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    reject(new Error(`Parse error: ${data}`));
                }
            });
        });

        req.on('error', reject);
        req.end();
    });
}

// Search for an icon and get 512px PNG URL
async function searchIcon(term) {
    try {
        // Use first English word (before comma)
        const searchTerm = term.split(',')[0].trim();
        const endpoint = `/icons?term=${encodeURIComponent(searchTerm)}&limit=1`;
        const result = await apiRequest(endpoint);

        if (result.data && result.data.length > 0) {
            const icon = result.data[0];
            const thumbnail = icon.thumbnails?.find(t => t.width === 512)
                           || icon.thumbnails?.find(t => t.width === 256)
                           || icon.thumbnails?.[0];

            return {
                id: icon.id,
                name: icon.name,
                style: icon.style?.name || null,
                url: thumbnail?.url || null
            };
        }
        return null;
    } catch (error) {
        console.error(`  Error searching "${term}": ${error.message}`);
        return null;
    }
}

// Sleep helper
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Main function
async function main() {
    console.log('Extracting nouns from spanish-nouns.html...');
    const nouns = extractNouns();
    console.log(`Found ${nouns.length} nouns\n`);

    // Load existing results if any (to resume)
    let results = {};
    const outputFile = 'noun-icons.json';

    if (fs.existsSync(outputFile)) {
        try {
            results = JSON.parse(fs.readFileSync(outputFile, 'utf8'));
            console.log(`Loaded ${Object.keys(results).length} existing results\n`);
        } catch (e) {
            console.log('Starting fresh...\n');
        }
    }

    // Filter out already-fetched nouns (retry ones with null icon)
    const remaining = nouns.filter(n => !results[n.es] || !results[n.es].icon?.url);
    console.log(`${remaining.length} nouns to fetch\n`);

    if (remaining.length === 0) {
        console.log('All nouns already fetched!');
        return;
    }

    let successCount = 0;
    let failCount = 0;

    // Process in batches
    for (let i = 0; i < remaining.length; i += BATCH_SIZE) {
        const batch = remaining.slice(i, i + BATCH_SIZE);
        const batchNum = Math.floor(i / BATCH_SIZE) + 1;
        const totalBatches = Math.ceil(remaining.length / BATCH_SIZE);

        console.log(`Batch ${batchNum}/${totalBatches}: ${batch.map(n => n.en.split(',')[0]).join(', ')}`);

        // Process batch in parallel
        const promises = batch.map(async (noun) => {
            const icon = await searchIcon(noun.en);
            if (icon && icon.url) {
                results[noun.es] = {
                    en: noun.en,
                    icon: icon
                };
                successCount++;
                return true;
            } else {
                results[noun.es] = {
                    en: noun.en,
                    icon: null
                };
                failCount++;
                return false;
            }
        });

        await Promise.all(promises);

        // Save progress after each batch
        fs.writeFileSync(outputFile, JSON.stringify(results, null, 2));

        // Progress update
        const progress = ((i + batch.length) / remaining.length * 100).toFixed(1);
        console.log(`  Progress: ${progress}% | Success: ${successCount} | Failed: ${failCount}\n`);

        // Rate limiting delay
        if (i + BATCH_SIZE < remaining.length) {
            await sleep(DELAY_BETWEEN_BATCHES);
        }
    }

    // Final summary
    console.log('\n========== COMPLETE ==========');
    console.log(`Total nouns: ${nouns.length}`);
    console.log(`Icons found: ${successCount}`);
    console.log(`Not found: ${failCount}`);
    console.log(`Results saved to: ${outputFile}`);

    // Show coverage
    const withIcons = Object.values(results).filter(r => r.icon?.url).length;
    console.log(`\nCoverage: ${withIcons}/${nouns.length} (${(withIcons/nouns.length*100).toFixed(1)}%)`);
}

main().catch(console.error);
