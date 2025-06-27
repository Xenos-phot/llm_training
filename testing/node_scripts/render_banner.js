const fs = require('fs');
const { createCanvas, registerFont } = require('canvas');
const { JSDOM } = require('jsdom');
const path = require('path');
const axios = require('axios');

// Function to display usage information
function showUsage() {
    console.log(`
Banner Renderer for Node.js

Usage:
  node utils/render_banner.js [input-file] [output-file] [format] [options]

Arguments:
  input-file         Path to the input JSON configuration file (default: input_config.json)
  output-file        Path to write the output JSON (default: updated_config.json)
  format             Export format: --png or --svg (optional)

Options:
  --force-download   Force download of remote assets even if cached locally

Examples:
  node utils/render_banner.js input.json output.json --svg
  node utils/render_banner.js input.json output.json --png --force-download
`);
    process.exit(0);
}

// Check for help flag
if (process.argv.includes('--help') || process.argv.includes('-h')) {
    showUsage();
}

// Setup JSDOM to create a browser-like environment
const dom = new JSDOM('<!DOCTYPE html><html><body><canvas id="canvas"></canvas></body></html>');
global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;
global.Image = dom.window.Image;
global.HTMLDocument = dom.window.HTMLDocument;
global.Document = dom.window.Document;
global.Element = dom.window.Element;

// Now require fabric.js after setting up JSDOM
const fabric = require('fabric').fabric;

// Get command line arguments for input and output files
const inputFile = process.argv[2] || 'temp.json';
const outputFile = process.argv[3] || 'updated_config.json';
const exportFormat = process.argv[4] || 'none'; // Can be 'png', 'svg', or '--png', '--svg'
const forceDownload = process.argv.includes('--force-download'); // Flag to force download of remote assets

// Log to verify what's being loaded
console.log(`Using input file: ${inputFile}, output file: ${outputFile}, export format: ${exportFormat}`);

// Setup canvas correctly for Node.js
const canvas = new fabric.Canvas(null, { width: 1080, height: 1080 });

// Function to load fonts
function loadFont(fontFamily, fontURL) {
    return new Promise((resolve, reject) => {
        try {
            // Extract the font file name from the URL
            const fontFileName = fontURL.split('/').pop();
            const fontPath = path.join('./tmp/fonts', fontFileName);
            
            // Create fonts directory if it doesn't exist
            if (!fs.existsSync('./tmp/fonts')) {
                fs.mkdirSync('./tmp/fonts', { recursive: true });
            }
            
            // Check if font already exists
            if (fs.existsSync(fontPath)) {
                console.log(`Font already exists: ${fontFamily}, using cached version`);
                registerFont(fontPath, { family: fontFamily });
                resolve();
                return;
            }
            
            // If we're here, font doesn't exist locally. 
            // In a real-world scenario, we'd download it, but for now we'll use a system font
            console.log(`Font not found: ${fontFamily}, using system fallback`);
            // Use a system font as fallback
            resolve();
            
        } catch (error) {
            console.error(`Error loading font ${fontFamily}:`, error);
            // Still resolve to not break rendering
            resolve();
        }
    });
}

// Function to create Fabric.js objects
function createFabricObject(objectData) {
    return new Promise(async (resolve, reject) => {
        try {
            console.log(`Creating object of type: ${objectData.type}, id: ${objectData.id}`);
            
            // Pre-process image URLs to local files if needed
            if (objectData.type.toLowerCase() === 'image' && objectData.src && objectData.src.startsWith('http')) {
                try {
                    // Extract filename from URL
                    const fileurl = objectData.src;
                    const fileName = objectData.src.split('/').pop();
                    const localPath = path.join('./tmp/images', fileName);
                    
                    // Create images directory if it doesn't exist
                    if (!fs.existsSync('./tmp/images')) {
                        fs.mkdirSync('./tmp/images', { recursive: true });
                        console.log('Created tmp/images directory for caching images');
                    }
                    
                    // Check if we already have this image locally and it's not empty, unless forced to download
                    if (forceDownload || !fs.existsSync(localPath) || fs.statSync(localPath).size === 0) {
                        if (forceDownload && fs.existsSync(localPath)) {
                            console.log(`Force download enabled. Re-downloading image from ${objectData.src}`);
                        } else {
                            console.log(`Image file not found locally or is empty. Downloading image from ${objectData.src}`);
                        }
                        
                        // Download the image
                        const response = await axios({
                            method: 'get',
                            url: objectData.src,
                            responseType: 'arraybuffer',
                            timeout: 20000 // 20 second timeout for download
                        });
                        
                        // Check if we received valid data
                        if (response.data && Buffer.from(response.data).length > 0) {
                            // Save the image locally
                            fs.writeFileSync(localPath, Buffer.from(response.data));
                            console.log(`Download complete. Saved image to ${localPath} (${Buffer.from(response.data).length} bytes)`);
                        } else {
                            console.error(`Downloaded empty file from ${objectData.src}`);
                            throw new Error('Downloaded file is empty');
                        }
                    } else {
                        // Get file stats to display file size
                        const stats = fs.statSync(localPath);
                        console.log(`Using cached image from ${localPath} (${stats.size} bytes)`);
                    }
                    
                    // Replace the remote URL with the local file path
                    objectData.src = localPath;
                } catch (error) {
                    console.error(`Failed to download/cache image: ${error.message}`);
                    // Continue with the original URL
                }
            }
            
            switch(objectData.type.toLowerCase()) {
                case 'text':
                case 'textbox':
                    // If fontURL is provided, load the font first
                    if (objectData.fontURL) {
                        try {
                            await loadFont(objectData.fontFamily, objectData.fontURL);
                        } catch (error) {
                            console.warn(`Failed to load font for ${objectData.fontFamily}, falling back to default`);
                        }
                    }
                    
                    const textObject = objectData.type.toLowerCase() === 'text' 
                        ? new fabric.Text(objectData.text, objectData)
                        : new fabric.Textbox(objectData.text, objectData);
                    // console.log(textObject)

                    let text_forced = new fabric.Text(objectData.text, objectData)
                    textObject.width = text_forced.width+2
                    resolve(textObject);
                    break;

                case 'image':
                    // Add timeout to prevent hanging
                    let imageLoaded = false; // Flag to track if image loaded successfully
                    
                    const imagePromise = new Promise((imgResolve) => {
                        // Check if the source is a local file
                        if (objectData.src && !objectData.src.startsWith('http') && fs.existsSync(objectData.src)) {
                            console.log(`Loading image from local file: ${objectData.src}`);
                            try {
                                // Use Node.js canvas to load the image
                                const { Image } = require('canvas');
                                const img = new Image();
                                
                                img.onload = () => {
                                    // Create a fabric.Image object from the loaded image
                                    const fabricImage = new fabric.Image(img, {
                                        ...objectData,
                                        scaleX: objectData.scaleX || 1,
                                        scaleY: objectData.scaleY || 1
                                    });
                                    
                                    console.log(`Successfully loaded image from file: ${objectData.src}`);
                                    console.log(`Image dimensions: ${img.width} x ${img.height}`);
                                    imageLoaded = true; // Set flag to true on successful load
                                    imgResolve(fabricImage);
                                };
                                
                                img.onerror = (err) => {
                                    console.error(`Error loading image from file: ${objectData.src}`, err);
                                    imgResolve(createFallbackRect(objectData));
                                };
                                
                                // Set the source to load the image
                                img.src = objectData.src;
                            } catch (err) {
                                console.error(`Error processing local image file: ${err.message}`);
                                imgResolve(createFallbackRect(objectData));
                            }
                        } else {
                            // Original remote URL handling
                            fabric.Image.fromURL(objectData.src, img => {
                                if (!img) {
                                    console.warn(`Failed to load image: ${objectData.src}`);
                                    imgResolve(createFallbackRect(objectData));
                                    return;
                                }
                                
                                // Apply properties individually
                                for (const key in objectData) {
                                    if (key !== 'type' && key !== 'src') {
                                        img.set(key, objectData[key]);
                                    }
                                }
                                
                                console.log(`Successfully loaded image: ${objectData.src}`);
                                imageLoaded = true; // Set flag to true on successful load
                                imgResolve(img);
                            }, { crossOrigin: 'anonymous' });
                        }
                    });
                    
                    // Add timeout to prevent hanging
                    const timeoutPromise = new Promise((timeoutResolve) => {
                        setTimeout(() => {
                            // Only show warning if image hasn't loaded already
                            if (!imageLoaded) {
                                console.warn(`Image loading timeout for: ${objectData.src}`);
                                timeoutResolve(createFallbackRect(objectData));
                            }
                        }, 10000); // Increased timeout to 10 seconds for better reliability
                    });
                    
                    resolve(Promise.race([imagePromise, timeoutPromise]));
                    break;

                case 'rect':
                    resolve(new fabric.Rect(objectData));
                    break;

                case 'circle':
                    resolve(new fabric.Circle(objectData));
                    break;

                case 'triangle':
                    resolve(new fabric.Triangle(objectData));
                    break;

                case 'line':
                    resolve(new fabric.Line([
                        objectData.x1 || 0,
                        objectData.y1 || 0,
                        objectData.x2 || 100,
                        objectData.y2 || 100
                    ], objectData));
                    break;

                case 'path':
                    resolve(new fabric.Path(objectData.path, objectData));
                    break;

                case 'polygon':
                    resolve(new fabric.Polygon(objectData.points, objectData));
                    break;

                case 'polyline':
                    resolve(new fabric.Polyline(objectData.points, objectData));
                    break;

                case 'ellipse':
                    resolve(new fabric.Ellipse(objectData));
                    break;

                case 'group':
                    // Handle groups of objects
                    Promise.all(objectData.objects.map(obj => createFabricObject(obj)))
                        .then(objects => {
                            const group = new fabric.Group(objects, objectData);
                            resolve(group);
                        })
                        .catch(reject);
                    break;

                case 'svg':
                    if (objectData.src.startsWith('http')) {
                        // Handle SVG URL
                        fabric.loadSVGFromURL(objectData.src, (objects, options) => {
                            const svgObject = fabric.util.groupSVGElements(objects, {
                                ...objectData,
                                ...options
                            });
                            svgObject.set({
                                left: objectData.left || 0,
                                top: objectData.top || 0,
                                scaleX: objectData.scaleX || 1,
                                scaleY: objectData.scaleY || 1
                            });
                            resolve(svgObject);
                        });
                    } else {
                        try {
                            // Handle SVG string
                            fabric.loadSVGFromString(objectData.src, (objects, options) => {
                                if (!objects || objects.length === 0) {
                                    console.warn('No SVG elements loaded from string');
                                    resolve(new fabric.Rect({
                                        width: objectData.width || 50,
                                        height: objectData.height || 50,
                                        left: objectData.left || 0,
                                        top: objectData.top || 0,
                                        fill: 'rgba(200,200,200,0.5)'
                                    }));
                                    return;
                                }
                                
                                const svgObject = fabric.util.groupSVGElements(objects, {
                                    ...objectData,
                                    ...options
                                });
                                
                                svgObject.set({
                                    left: objectData.left || 0,
                                    top: objectData.top || 0,
                                    scaleX: objectData.scaleX || 1,
                                    scaleY: objectData.scaleY || 1
                                });
                                resolve(svgObject);
                            });
                        } catch (svgError) {
                            console.error('Error processing SVG:', svgError);
                            resolve(new fabric.Rect({
                                width: objectData.width || 50,
                                height: objectData.height || 50,
                                left: objectData.left || 0,
                                top: objectData.top || 0,
                                fill: 'rgba(255,0,0,0.5)'
                            }));
                        }
                    }
                    break;

                case 'gradient':
                    const gradient = new fabric.Gradient(objectData);
                    resolve(gradient);
                    break;

                default:
                    console.warn(`Unsupported object type: ${objectData.type}`);
                    // Instead of rejecting, create a fallback rectangle
                    resolve(new fabric.Rect({
                        width: 50,
                        height: 50,
                        fill: 'red',
                        ...objectData
                    }));
            }
        } catch (error) {
            console.error('Error in createFabricObject:', error);
            reject(error);
        }
    });
}

// Helper function to create a fallback rectangle
function createFallbackRect(objectData) {
    return new fabric.Rect({
        width: objectData.width || 100,
        height: objectData.height || 100,
        left: objectData.left || 0,
        top: objectData.top || 0,
        fill: 'rgba(200,200,200,0.5)'
    });
}

// Wrapper function with timeout for loadBannerConfig
async function loadBannerConfigWithTimeout(config, timeoutMs = 30000) {
    return Promise.race([
        loadBannerConfig(config),
        new Promise((_, reject) => {
            setTimeout(() => {
                reject(new Error(`Banner loading timed out after ${timeoutMs}ms`));
            }, timeoutMs);
        })
    ]);
}

// Function to load banner configuration
async function loadBannerConfig(config) {
    try {
        // Set canvas properties
        canvas.setWidth(config.width || 1080);
        canvas.setHeight(config.height || 1080);
        canvas.setBackgroundColor(config.backgroundColor || '#ffffff', canvas.renderAll.bind(canvas));
        
        // Clear existing objects
        canvas.clear();
        // Clear the font cache
        fabric.util.clearFabricFontCache();
        // Load new objects if they exist
        if (config.objects && Array.isArray(config.objects)) {
            for (const objectData of config.objects) {
                try {
                    const fabricObject = await createFabricObject(objectData);
                    if (fabricObject) {
                        canvas.add(fabricObject);
                    }
                } catch (error) {
                    console.error('Error creating object:', error);
                }
            }
        }
        
        canvas.renderAll();
        return canvas.toJSON(["fontURL", "src"]); // Return the updated config
    } catch (error) {
        console.error('Error in loadBannerConfig:', error);
        throw error;
    }
}

// Function to clean object properties
function cleanObjectProperties(obj) {
    // Only keep properties that the model returns
    const essentialProps = {
        id: true,
        // Basic properties
        type: true,
        left: true,
        top: true,
        width: true,
        height: true,
        
        // Style properties
        fill: true,
        stroke: true,
        strokeWidth: true,
        backgroundColor: true,
        
        // Transform properties
        scaleX: true,
        scaleY: true,
        angle: true,
        opacity: true,
        
        // Text-specific properties
        text: true,
        fontSize: true,
        fontFamily: true,
        fontWeight: true,
        fontStyle: true,
        textAlign: true,
        lineHeight: true,
        charSpacing: true,
        fontURL: true,  // Added fontURL property
        
        // Image-specific properties
        src: true,
        
        // Origin properties
        originX: true,
        originY: true,
        
        // SVG-specific properties
        src: true,

        // Circle-specific properties
        radius: true,
        
        // rect-specific properties
        rx: true,
        path: true,
        ry: true,
    };

    const cleaned = {};
    for (const [key, value] of Object.entries(obj)) {
        if (key == 'type' && value == 'image') {
            cleaned[key] = value;
        }
    }
    for (const [key, value] of Object.entries(obj)) {
        if (essentialProps[key] && value !== null && value !== undefined) {
            if (key == 'src') {
                if (value.startsWith('http')) {
                    cleaned[key] = value;
                }
                else {
                    cleaned[key] = `https://s3.us-east-2.wasabisys.com/ai-image-editor-webapp/test-images/${value.split('/').pop()}`;
                }
            }
            else {
                cleaned[key] = value;
            }
        }
    }
    
    return cleaned;
}

// Modified updateJSON function for Node.js environment
function updateJSON() {
    const currentState = canvas.toJSON(["fontURL", "src"]);
    const cleanedState = {
        backgroundColor: currentState.backgroundColor || "#ffffff",
        height: canvas.height,
        width: canvas.width,
        objects: currentState.objects.map(obj => {
            const cleaned = cleanObjectProperties(obj);
            // Preserve fontURL if it exists in the original object
            if (obj.fontURL) {
                cleaned.fontURL = obj.fontURL;
            }
            return cleaned;
        }),
        version: "5.3.0"
    };
    
    // Return the cleaned state instead of updating DOM element
    return cleanedState;
}

// Function to determine if we should export an image
function shouldExportImage() {
    return exportFormat === 'png' || exportFormat === '--png' || 
           exportFormat === 'svg' || exportFormat === '--svg';
}

// Function to get export format
function getExportFormat() {
    if (exportFormat === 'png' || exportFormat === '--png') return 'png';
    if (exportFormat === 'svg' || exportFormat === '--svg') return 'svg';
    return 'none';
}

// Function to get output image path
function getOutputImagePath(format) {
    return outputFile.replace(/\.json$/, `.${format}`);
}

// Function to save canvas as image
function saveCanvasAsImage(fabricCanvas, filePath, format) {
    return new Promise((resolve, reject) => {
        try {
            if (format === 'svg') {
                // Export as SVG
                const svgData = fabricCanvas.toSVG();
                fs.writeFileSync(filePath, svgData);
                console.log(`Successfully saved SVG to ${filePath}`);
                resolve();
            } else {
                // Try to export as PNG using node-canvas
                console.log('Attempting to export as PNG, but this might not work in all Node.js environments');
                
                try {
                    // Use a simple approach - just try to get the buffer from canvas
                    const dataURL = fabricCanvas.toDataURL({ format: 'png' });
                    const data = dataURL.replace(/^data:image\/\w+;base64,/, '');
                    const buffer = Buffer.from(data, 'base64');
                    fs.writeFileSync(filePath, buffer);
                    console.log(`Successfully saved PNG to ${filePath}`);
                    resolve();
                } catch (innerError) {
                    console.error('Error converting to PNG:', innerError);
                    
                    // Fallback to SVG if PNG fails
                    console.log('Falling back to SVG export...');
                    const svgFilePath = filePath.replace(/\.png$/, '.svg');
                    const svgData = fabricCanvas.toSVG();
                    fs.writeFileSync(svgFilePath, svgData);
                    console.log(`Fallback: Successfully saved SVG to ${svgFilePath}`);
                    resolve();
                }
            }
        } catch (error) {
            console.error(`Error saving canvas as ${format}:`, error);
            reject(error);
        }
    });
}

;(async () => {
    // Read banner config from input file
    let banner_config;
    try {
        const configData = fs.readFileSync(inputFile, 'utf8');
        banner_config = JSON.parse(configData);
        
        // Await the loading of banner config with timeout
        try {
            if (exportFormat === 'png' || exportFormat === '--png') {
                const updatedConfig = await loadBannerConfigWithTimeout(banner_config);
            } else {
                const updatedConfig = await loadBannerConfig(banner_config);
            }
            // Call updateJSON to get the cleaned state
            const cleanedConfig = updateJSON();
            // Save to file using Node.js fs module and log success
            fs.writeFileSync(outputFile, JSON.stringify(cleanedConfig, null, 2));
            
            // If export flag is set, save the canvas as image
            if (shouldExportImage()) {
                const format = getExportFormat();
                const outputPath = getOutputImagePath(format);
                try {
                    await saveCanvasAsImage(canvas, outputPath, format);
                } catch (imageError) {
                    console.error(`Error saving ${format.toUpperCase()}:`, imageError);
                }
            }
            
            // Force exit the process after successful completion
            process.exit(0);
        } catch (loadError) {
            console.error('Error loading banner config:', loadError);
            // Still try to save whatever we have in the canvas
            const cleanedConfig = updateJSON();
            fs.writeFileSync(outputFile, JSON.stringify(cleanedConfig, null, 2));
            
            // If export flag is set, try to save image even if there was an error
            if (shouldExportImage()) {
                const format = getExportFormat();
                const outputPath = getOutputImagePath(format);
                try {
                    await saveCanvasAsImage(canvas, outputPath, format);
                } catch (imageError) {
                    console.error(`Error saving partial ${format.toUpperCase()}:`, imageError);
                }
            }
            
            // Force exit the process even after error
            process.exit(1);
        }
    } catch (error) {
        console.error(`Error processing banner:`, error);
        process.exit(1);
    }
})().catch(error => {
    console.error('Unhandled error in main process:', error);
    process.exit(1);
});