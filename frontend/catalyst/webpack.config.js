module.exports = {

    module: {
        rules: [
            {
                test: /\.(woff|woff2)$/,
                type: 'asset/resource',
                generator: {
                    filename: 'assets/fonts/[name][ext]',
                }
            }
        ]
    },
    watch: true
}