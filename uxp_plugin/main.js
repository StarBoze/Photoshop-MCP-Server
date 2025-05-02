/**
 * Photoshop MCP UXP Plugin
 * main.js - プラグインのエントリーポイント
 */

const { app } = require('photoshop');
const { entrypoints } = require('uxp');

// グローバル変数
let wsConnection = null;
let logContainer = null;
let statusDot = null;
let statusText = null;
let connectButton = null;

// 初期化関数
async function init() {
    try {
        // DOM要素の参照を取得
        logContainer = document.getElementById('log-container');
        statusDot = document.getElementById('status-dot');
        statusText = document.getElementById('status-text');
        connectButton = document.getElementById('connect-button');

        // イベントリスナーの設定
        connectButton.addEventListener('click', toggleConnection);

        // WebSocket接続の初期化
        initWebSocket();

        // Photoshop APIの初期化
        await initPhotoshopAPI();

        // ログ出力
        logInfo('プラグインが初期化されました');
    } catch (error) {
        logError(`初期化エラー: ${error.message}`);
        console.error('初期化エラー:', error);
    }
}

// WebSocket接続の切り替え
function toggleConnection() {
    if (wsConnection && wsConnection.isConnected()) {
        wsConnection.disconnect();
        connectButton.textContent = '接続';
    } else {
        initWebSocket();
        connectButton.textContent = '切断';
    }
}

// WebSocket接続の初期化
function initWebSocket() {
    try {
        // WebSocket接続の作成
        wsConnection = new WebSocketConnection('ws://127.0.0.1:8765');

        // WebSocketイベントハンドラの設定
        wsConnection.onOpen(() => {
            updateConnectionStatus('connected', '接続済み');
            logInfo('WebSocketサーバーに接続しました');
        });

        wsConnection.onClose(() => {
            updateConnectionStatus('disconnected', '未接続');
            logInfo('WebSocketサーバーから切断されました');
        });

        wsConnection.onError((error) => {
            updateConnectionStatus('disconnected', 'エラー');
            logError(`WebSocketエラー: ${error}`);
        });

        wsConnection.onMessage((message) => {
            handleIncomingMessage(message);
        });

        // 接続開始
        wsConnection.connect();
        updateConnectionStatus('connecting', '接続中...');
    } catch (error) {
        logError(`WebSocket初期化エラー: ${error.message}`);
        console.error('WebSocket初期化エラー:', error);
    }
}

// 接続状態の更新
function updateConnectionStatus(status, text) {
    statusDot.className = 'status-dot ' + status;
    statusText.textContent = text;
    
    if (status === 'connected') {
        connectButton.textContent = '切断';
    } else {
        connectButton.textContent = '接続';
    }
}

// 受信メッセージの処理
async function handleIncomingMessage(message) {
    try {
        // JSONメッセージのパース
        const data = JSON.parse(message);
        logInfo(`メッセージを受信: ${data.command}`);

        // コマンドの処理
        switch (data.command) {
            case 'ping':
                wsConnection.send(JSON.stringify({ command: 'pong', id: data.id }));
                break;
                
            case 'execute_action':
                const result = await executePhotoshopAction(data.params);
                wsConnection.send(JSON.stringify({ 
                    command: 'action_result', 
                    id: data.id, 
                    result: result 
                }));
                break;
                
            case 'get_document_info':
                const docInfo = await getDocumentInfo();
                wsConnection.send(JSON.stringify({ 
                    command: 'document_info', 
                    id: data.id, 
                    info: docInfo 
                }));
                break;
                
            default:
                logWarning(`未知のコマンド: ${data.command}`);
                wsConnection.send(JSON.stringify({ 
                    command: 'error', 
                    id: data.id, 
                    error: `未知のコマンド: ${data.command}` 
                }));
        }
    } catch (error) {
        logError(`メッセージ処理エラー: ${error.message}`);
        console.error('メッセージ処理エラー:', error);
        
        if (wsConnection && wsConnection.isConnected()) {
            wsConnection.send(JSON.stringify({ 
                command: 'error', 
                error: `メッセージ処理エラー: ${error.message}` 
            }));
        }
    }
}

// ログ関数
function logInfo(message) {
    addLogEntry(message, 'info');
}

function logError(message) {
    addLogEntry(message, 'error');
}

function logWarning(message) {
    addLogEntry(message, 'warning');
}

function addLogEntry(message, type) {
    if (!logContainer) return;
    
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
    
    // ログエントリが多すぎる場合は古いものを削除
    const maxEntries = 100;
    while (logContainer.children.length > maxEntries) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

// UXPパネルのロード時に初期化を実行
entrypoints.setup({
    panels: {
        mainPanel: {
            show(node) {
                // パネルが表示されたときの処理
                if (!node.innerHTML) {
                    // 初期化が必要な場合のみ実行
                    init().catch(error => {
                        console.error('パネル初期化エラー:', error);
                    });
                }
            }
        }
    }
});