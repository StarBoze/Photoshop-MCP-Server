/**
 * Photoshop MCP UXP Plugin
 * websocket.js - WebSocket通信の管理
 */

/**
 * WebSocket接続を管理するクラス
 */
class WebSocketConnection {
    /**
     * WebSocketConnectionのコンストラクタ
     * @param {string} url - 接続先WebSocketサーバーのURL
     */
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 2000; // 2秒
        this.reconnectTimeoutId = null;
        
        // イベントコールバック
        this._onOpenCallback = null;
        this._onCloseCallback = null;
        this._onErrorCallback = null;
        this._onMessageCallback = null;
    }

    /**
     * WebSocketサーバーに接続
     */
    connect() {
        if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
            console.log('WebSocket: 既に接続中または接続試行中です');
            return;
        }

        this.isConnecting = true;
        this.reconnectAttempts = 0;
        
        try {
            console.log(`WebSocket: ${this.url} に接続中...`);
            this.socket = new WebSocket(this.url);
            
            this.socket.onopen = (event) => {
                console.log('WebSocket: 接続成功');
                this.isConnecting = false;
                this.reconnectAttempts = 0;
                
                if (this._onOpenCallback) {
                    this._onOpenCallback(event);
                }
            };
            
            this.socket.onclose = (event) => {
                console.log(`WebSocket: 切断 (コード: ${event.code}, 理由: ${event.reason})`);
                this.socket = null;
                
                if (this._onCloseCallback) {
                    this._onCloseCallback(event);
                }
                
                // 自動再接続（明示的に切断された場合を除く）
                if (this.isConnecting && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.scheduleReconnect();
                }
            };
            
            this.socket.onerror = (error) => {
                console.error('WebSocket: エラー発生', error);
                
                if (this._onErrorCallback) {
                    this._onErrorCallback(error);
                }
            };
            
            this.socket.onmessage = (event) => {
                if (this._onMessageCallback) {
                    this._onMessageCallback(event.data);
                }
            };
        } catch (error) {
            console.error('WebSocket: 接続エラー', error);
            this.socket = null;
            
            if (this._onErrorCallback) {
                this._onErrorCallback(error);
            }
            
            // 接続エラー時も再接続を試みる
            if (this.isConnecting && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.scheduleReconnect();
            }
        }
    }

    /**
     * WebSocketサーバーから切断
     */
    disconnect() {
        this.isConnecting = false;
        
        if (this.reconnectTimeoutId) {
            clearTimeout(this.reconnectTimeoutId);
            this.reconnectTimeoutId = null;
        }
        
        if (this.socket) {
            try {
                this.socket.close(1000, "正常切断");
            } catch (error) {
                console.error('WebSocket: 切断エラー', error);
            }
            this.socket = null;
        }
    }

    /**
     * 再接続をスケジュール
     */
    scheduleReconnect() {
        if (this.reconnectTimeoutId) {
            clearTimeout(this.reconnectTimeoutId);
        }
        
        this.reconnectAttempts++;
        const delay = this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1);
        console.log(`WebSocket: ${delay}ms後に再接続を試みます (試行回数: ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        this.reconnectTimeoutId = setTimeout(() => {
            if (this.isConnecting) {
                this.connect();
            }
        }, delay);
    }

    /**
     * メッセージを送信
     * @param {string|ArrayBuffer} data - 送信するデータ
     * @returns {boolean} - 送信成功したかどうか
     */
    send(data) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.error('WebSocket: 接続が確立されていないため送信できません');
            return false;
        }
        
        try {
            this.socket.send(data);
            return true;
        } catch (error) {
            console.error('WebSocket: 送信エラー', error);
            return false;
        }
    }

    /**
     * 接続状態を確認
     * @returns {boolean} - 接続されているかどうか
     */
    isConnected() {
        return this.socket && this.socket.readyState === WebSocket.OPEN;
    }

    /**
     * 接続オープン時のコールバックを設定
     * @param {Function} callback - コールバック関数
     */
    onOpen(callback) {
        this._onOpenCallback = callback;
    }

    /**
     * 接続クローズ時のコールバックを設定
     * @param {Function} callback - コールバック関数
     */
    onClose(callback) {
        this._onCloseCallback = callback;
    }

    /**
     * エラー発生時のコールバックを設定
     * @param {Function} callback - コールバック関数
     */
    onError(callback) {
        this._onErrorCallback = callback;
    }

    /**
     * メッセージ受信時のコールバックを設定
     * @param {Function} callback - コールバック関数
     */
    onMessage(callback) {
        this._onMessageCallback = callback;
    }
}