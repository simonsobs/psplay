var path = require('path');
var version = require('./package.json').version;

var rules = [
    {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
    },
    {
        test: /\.(jpg|png|gif|svg)$/,
        use: [
            {
                loader: 'file-loader',
                options: {
                    esModule: false,
                }
            }
        ],
    }
];

module.exports = [
    {// Notebook extension
        entry: './src/extension.js',
        output: {
            filename: 'extension.js',
            path: path.resolve(__dirname, '..', 'psplay', 'static'),
            libraryTarget: 'amd'
        }
    },
    {// jupyter-leaflet-car bundle for the classic notebook
        entry: './src/notebook.js',
        output: {
            filename: 'index.js',
            path: path.resolve(__dirname, '..', 'psplay', 'static'),
            libraryTarget: 'amd'
        },
        devtool: 'source-map',
        module: {
            rules: rules
        },
        externals: ['@jupyter-widgets/base', 'jupyter-leaflet']
    },
    {// jupyter-leaflet-car bundle for unpkg
        entry: './src/embed.js',
        output: {
            filename: 'index.js',
            path: path.resolve(__dirname, 'dist'),
            libraryTarget: 'amd',
            publicPath: 'https://unpkg.com/jupyter-leaflet-car@' + version + '/dist/'
        },
        devtool: 'source-map',
        module: {
            rules: rules
        },
        externals: ['@jupyter-widgets/base', 'jupyter-leaflet']
    }
];
