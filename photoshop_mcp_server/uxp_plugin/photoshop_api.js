/**
 * Photoshop MCP UXP Plugin
 * photoshop_api.js - Photoshop API操作の実装
 */

const { app, core, action, constants } = require('photoshop');
const { batchPlay } = require('photoshop').action;
const { executeAsModal } = require('photoshop').core;

// Photoshop APIの初期化
async function initPhotoshopAPI() {
    try {
        // アクティブなドキュメントがあるか確認
        const hasOpenDocuments = app.documents.length > 0;
        console.log(`Photoshop API初期化: ドキュメント数=${app.documents.length}`);
        
        return {
            success: true,
            hasOpenDocuments: hasOpenDocuments
        };
    } catch (error) {
        console.error('Photoshop API初期化エラー:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Photoshopアクションを実行
 * @param {Object} params - アクションパラメータ
 * @returns {Object} - 実行結果
 */
async function executePhotoshopAction(params) {
    try {
        // アクションの種類に基づいて処理を分岐
        switch (params.actionType) {
            case 'batchPlay':
                return await executeBatchPlay(params.commands);
                
            case 'createLayer':
                return await createLayer(params.name, params.type);
                
            case 'exportDocument':
                return await exportDocument(params.format, params.path, params.options);
                
            case 'applyFilter':
                return await applyFilter(params.filterType, params.options);
                
            case 'executeJSX':
                return await executeJSXScript(params.script);
                
            default:
                throw new Error(`未サポートのアクション: ${params.actionType}`);
        }
    } catch (error) {
        console.error('アクション実行エラー:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * batchPlayコマンドを実行
 * @param {Array} commands - batchPlayコマンド配列
 * @returns {Object} - 実行結果
 */
async function executeBatchPlay(commands) {
    try {
        // モーダルコンテキストで実行
        const result = await executeAsModal(async () => {
            return await batchPlay(commands, {
                synchronousExecution: true,
                modalBehavior: 'execute'
            });
        }, { commandName: 'MCPバッチプレイ実行' });
        
        return {
            success: true,
            result: result
        };
    } catch (error) {
        console.error('batchPlay実行エラー:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * 新規レイヤーを作成
 * @param {string} name - レイヤー名
 * @param {string} type - レイヤータイプ ('pixel', 'adjustment', 'text', 'shape')
 * @returns {Object} - 実行結果
 */
async function createLayer(name, type = 'pixel') {
    try {
        // アクティブなドキュメントがあるか確認
        if (app.documents.length === 0) {
            throw new Error('開いているドキュメントがありません');
        }
        
        const doc = app.activeDocument;
        let layer;
        
        // モーダルコンテキストで実行
        await executeAsModal(async () => {
            // レイヤータイプに基づいて処理を分岐
            switch (type) {
                case 'pixel':
                    // 通常のピクセルレイヤー
                    layer = await doc.createLayer({ name });
                    break;
                    
                case 'text':
                    // テキストレイヤー
                    layer = await doc.createTextLayer({ name });
                    break;
                    
                case 'adjustment':
                    // 調整レイヤー (例: レベル補正)
                    const result = await batchPlay([{
                        _obj: "make",
                        _target: [{ _ref: "adjustmentLayer" }],
                        using: { _obj: "levels", _target: [{ _ref: "adjustmentLayer" }] }
                    }], {
                        synchronousExecution: true,
                        modalBehavior: 'execute'
                    });
                    
                    // 作成された調整レイヤーの名前を変更
                    const currentLayer = doc.activeLayers[0];
                    await currentLayer.rename(name);
                    layer = currentLayer;
                    break;
                    
                case 'shape':
                    // シェイプレイヤー (例: 長方形)
                    const shapeResult = await batchPlay([{
                        _obj: "make",
                        _target: [{ _ref: "contentLayer" }],
                        using: {
                            _obj: "contentLayer",
                            type: {
                                _obj: "solidColorLayer",
                                color: { _obj: "RGBColor", red: 255, green: 0, blue: 0 }
                            },
                            shape: {
                                _obj: "rectangle",
                                top: 100,
                                left: 100,
                                bottom: 300,
                                right: 300
                            }
                        }
                    }], {
                        synchronousExecution: true,
                        modalBehavior: 'execute'
                    });
                    
                    // 作成されたシェイプレイヤーの名前を変更
                    const shapeLayer = doc.activeLayers[0];
                    await shapeLayer.rename(name);
                    layer = shapeLayer;
                    break;
                    
                default:
                    throw new Error(`未サポートのレイヤータイプ: ${type}`);
            }
        }, { commandName: 'MCPレイヤー作成' });
        
        return {
            success: true,
            layerId: layer.id,
            layerName: layer.name
        };
    } catch (error) {
        console.error('レイヤー作成エラー:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * ドキュメントをエクスポート
 * @param {string} format - エクスポート形式 ('jpg', 'png', 'psd')
 * @param {string} path - 保存先パス
 * @param {Object} options - エクスポートオプション
 * @returns {Object} - 実行結果
 */
async function exportDocument(format, path, options = {}) {
    try {
        // アクティブなドキュメントがあるか確認
        if (app.documents.length === 0) {
            throw new Error('開いているドキュメントがありません');
        }
        
        const doc = app.activeDocument;
        
        // モーダルコンテキストで実行
        await executeAsModal(async () => {
            // エクスポート形式に基づいて処理を分岐
            switch (format.toLowerCase()) {
                case 'jpg':
                case 'jpeg':
                    await doc.saveAs.jpg(path, {
                        quality: options.quality || 90,
                        embedColorProfile: options.embedColorProfile !== false
                    });
                    break;
                    
                case 'png':
                    await doc.saveAs.png(path, {
                        compression: options.compression || 6,
                        embedColorProfile: options.embedColorProfile !== false
                    });
                    break;
                    
                case 'psd':
                    await doc.saveAs.psd(path, {
                        embedColorProfile: options.embedColorProfile !== false,
                        maximizeCompatibility: options.maximizeCompatibility !== false
                    });
                    break;
                    
                default:
                    throw new Error(`未サポートのエクスポート形式: ${format}`);
            }
        }, { commandName: 'MCPドキュメントエクスポート' });
        
        return {
            success: true,
            path: path,
            format: format
        };
    } catch (error) {
        console.error('ドキュメントエクスポートエラー:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * フィルターを適用
 * @param {string} filterType - フィルタータイプ
 * @param {Object} options - フィルターオプション
 * @returns {Object} - 実行結果
 */
async function applyFilter(filterType, options = {}) {
    try {
        // アクティブなドキュメントがあるか確認
        if (app.documents.length === 0) {
            throw new Error('開いているドキュメントがありません');
        }
        
        // モーダルコンテキストで実行
        await executeAsModal(async () => {
            // フィルタータイプに基づいて処理を分岐
            switch (filterType) {
                case 'gaussianBlur':
                    await batchPlay([{
                        _obj: "gaussianBlur",
                        radius: options.radius || 10
                    }], {
                        synchronousExecution: true,
                        modalBehavior: 'execute'
                    });
                    break;
                    
                case 'sharpen':
                    await batchPlay([{
                        _obj: "unsharpMask",
                        amount: options.amount || 50,
                        radius: options.radius || 1,
                        threshold: options.threshold || 0
                    }], {
                        synchronousExecution: true,
                        modalBehavior: 'execute'
                    });
                    break;
                    
                case 'invert':
                    await batchPlay([{
                        _obj: "invert"
                    }], {
                        synchronousExecution: true,
                        modalBehavior: 'execute'
                    });
                    break;
                    
                default:
                    throw new Error(`未サポートのフィルター: ${filterType}`);
            }
        }, { commandName: 'MCPフィルター適用' });
        
        return {
            success: true,
            filterType: filterType
        };
    } catch (error) {
        console.error('フィルター適用エラー:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * JSXスクリプトを実行
 * @param {string} script - 実行するJSXスクリプト
 * @returns {Object} - 実行結果
 */
async function executeJSXScript(script) {
    try {
        // モーダルコンテキストで実行
        const result = await executeAsModal(async () => {
            return await core.executeJSX(script);
        }, { commandName: 'MCPスクリプト実行' });
        
        return {
            success: true,
            result: result
        };
    } catch (error) {
        console.error('JSXスクリプト実行エラー:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * ドキュメント情報を取得
 * @returns {Object} - ドキュメント情報
 */
async function getDocumentInfo() {
    try {
        // アクティブなドキュメントがあるか確認
        if (app.documents.length === 0) {
            return {
                success: false,
                error: '開いているドキュメントがありません'
            };
        }
        
        const doc = app.activeDocument;
        
        // ドキュメント情報を収集
        const info = {
            id: doc.id,
            name: doc.name,
            path: doc.path,
            width: doc.width,
            height: doc.height,
            resolution: doc.resolution,
            mode: doc.mode,
            bitsPerChannel: doc.bitsPerChannel,
            numberOfLayers: 0,
            selectedLayers: []
        };
        
        // レイヤー情報を収集
        try {
            const layers = await doc.layers;
            info.numberOfLayers = layers.length;
            
            // 選択されているレイヤー情報
            const selectedLayers = doc.activeLayers;
            info.selectedLayers = selectedLayers.map(layer => ({
                id: layer.id,
                name: layer.name,
                type: layer.type,
                visible: layer.visible
            }));
        } catch (layerError) {
            console.warn('レイヤー情報取得エラー:', layerError);
        }
        
        return {
            success: true,
            info: info
        };
    } catch (error) {
        console.error('ドキュメント情報取得エラー:', error);
        return {
            success: false,
            error: error.message
        };
    }
}