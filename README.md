# Glowing Gardens - Distribution Visualizations

Beautiful, interactive visualizations of statistical distributions using D3.js force-directed graphs.

## Overview

This project makes complex statistical distributions intuitive and beautiful by visualizing them as animated bubble charts. Each bubble represents a data point, with size determined by the distribution type.

## Static Distributions

All static distributions feature 100 data points in a 600x600px canvas:

- **Power Law** (`d3-bubble-power-law.html`) - 5 huge bubbles dominate, most are tiny (wealth inequality, social media follows)
- **Normal Distribution** (`d3-bubble-normal.html`) - Classic bell curve with uniform sizes clustering in center
- **Uniform** (`d3-bubble-uniform.html`) - Perfect equality - all 100 bubbles identical
- **Diversity** (`d3-bubble-diversity.html`) - Every bubble unique in size and color (rainbow spectrum)
- **Uniform Random** (`d3-bubble-uniform-random.html`) - Truly random sizes with equal probability
- **Bimodal** (`d3-bubble-bimodal.html`) - Two distinct groups (like heights by gender)
- **Polarized** (`d3-bubble-polarized.html`) - Only extremes - very large or very small, no middle
- **Pareto (80/20)** (`d3-bubble-pareto.html`) - 20% of bubbles represent 80% of total size

## Animated Transformations

Watch distributions transform over time:

- **Middle Class Squeeze** (`d3-bubble-middle-class-squeeze.html`) - Uniform → Polarized transformation showing the disappearance of the middle class over 8 seconds

## Running Locally

1. Start a local server:
   ```bash
   python3 -m http.server 3001
   ```

2. Open any HTML file in your browser:
   ```
   http://localhost:3001/d3-bubble-power-law.html
   ```

## Features

- **Interactive physics** - Drag bubbles around, watch them bounce and settle
- **Consistent styling** - All visualizations use 600x600px canvas with uniform padding
- **Smooth animations** - D3 transitions make transformations mesmerizing
- **Educational** - See statistical concepts instantly instead of reading formulas

## Technology

- D3.js v7 for force simulations and animations
- Pure vanilla JavaScript
- No build process required

## Future Distributions

Coming soon:
- Exponential growth/decay
- Logistic growth
- Rich-get-richer dynamics
- Normal → Power Law (emergence of inequality)
- Power Law → Normal (redistribution)
- Market crash/revolution simulations

## License

MIT

## Credits

Created to make statistical distributions intuitive and beautiful.
