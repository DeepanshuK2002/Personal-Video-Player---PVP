const sveltePreprocess = require('svelte-preprocess');

const createSveltePreprocessor = () =>
    sveltePreprocess({
        tsconfigFile: './tsconfig.json',
        sourceMap: false
    });

module.exports = {
    preprocess: createSveltePreprocessor(),
    createSveltePreprocessor
};
