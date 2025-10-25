// API Service for Pentagent Frontend
// WebSocket ve REST API ile backend iletişimi

class PentagentAPI {
  constructor() {
    this.ws = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 2000;
    
    // Environment-aware URL configuration
    const isDevelopment = import.meta.env.DEV;
    
    // Production: Render backend, Development: localhost
    const apiUrl = isDevelopment 
      ? 'http://localhost:8000' 
      : (import.meta.env.VITE_API_URL || 'https://pentagent-web.onrender.com');
    
    this.baseURL = apiUrl;
    
    // WebSocket URL'ini dinamik olarak belirle
    const protocol = apiUrl.startsWith('https') ? 'wss:' : 'ws:';
    const host = apiUrl.replace('http://', '').replace('https://', '');
    this.wsURL = `${protocol}//${host}/ws`;
    
    this.heartbeatInterval = null;
    this.heartbeatTimeout = null;
    this.isManualDisconnect = false;
    this.messageQueue = [];
    
    // WebSocket bağlantı durumunu logla
    console.log('🌐 PentagentAPI Configuration:');
    console.log('  Environment:', isDevelopment ? 'Development' : 'Production');
    console.log('  Base URL:', this.baseURL);
    console.log('  WebSocket URL:', this.wsURL);
  }

  // WebSocket bağlantısı kur
  connectWebSocket(onMessage, onStatusChange) {
    if (this.isManualDisconnect) {
      console.log('Manuel bağlantı kesildi, yeniden bağlanma yapılmıyor');
      return;
    }

    // Eğer zaten bağlantı varsa ve açıksa, yeni bağlantı kurma
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket zaten açık, yeni bağlantı kurulmuyor');
      return;
    }

    // Eğer bağlantı kuruluyorsa, bekle
    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
      console.log('WebSocket zaten bağlanıyor, bekleniyor...');
      return;
    }

    // Eğer bağlantı kapalıysa, kapat
    if (this.ws && this.ws.readyState === WebSocket.CLOSED) {
      console.log('Eski WebSocket bağlantısı temizleniyor...');
      this.ws = null;
    }

    try {
      // Sadece ilk deneme ve her 3. denemede logla
      if (this.reconnectAttempts === 0 || this.reconnectAttempts % 3 === 0) {
        console.log(`🔌 WebSocket bağlanıyor... (Deneme: ${this.reconnectAttempts + 1})`);
      }
      
      // WebSocket bağlantısını kur
      this.ws = new WebSocket(this.wsURL);
      
      // Bağlantı timeout'u ekle - ARTIR ILDI (30s)
      const connectionTimeout = setTimeout(() => {
        if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
          console.log('WebSocket bağlantı timeout (30s), kapatılıyor...');
          this.ws.close();
        }
      }, 30000); // 30 saniye timeout (5s → 30s)
      
      this.ws.onopen = () => {
        clearTimeout(connectionTimeout);
        console.log('✅ WebSocket bağlantısı kuruldu!');
        console.log('✅ WebSocket URL:', this.wsURL);
        console.log('✅ WebSocket readyState:', this.ws.readyState);
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.isManualDisconnect = false;
        onStatusChange('connected');
        
        // Heartbeat başlat
        this.startHeartbeat();
        
        // Kuyruktaki mesajları gönder
        this.flushMessageQueue();
        
        // Bağlantı kurulduğunda ping gönder
        this.ping();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket mesajı alındı:', data);
          
          // Heartbeat yanıtı
          if (data.type === 'pong') {
            this.resetHeartbeatTimeout();
            return;
          }
          
          // Bağlantı durumu mesajı
          if (data.type === 'connection_status') {
            console.log('Bağlantı durumu:', data.status);
            if (data.status === 'connected') {
              onStatusChange('connected');
            }
            return;
          }
          
          onMessage(data);
        } catch (error) {
          console.error('WebSocket mesaj parse hatası:', error);
        }
      };

      this.ws.onclose = (event) => {
        clearTimeout(connectionTimeout);
        
        this.isConnected = false;
        this.stopHeartbeat();
        
        // Manuel disconnect veya normal kapanış (1000) ise reconnect yapma
        if (this.isManualDisconnect || event.code === 1000) {
          return;
        }
        
        // Sadece gerçek bağlantı sorunlarında reconnect yap
        if (event.code === 1006) {
          // İlk denemede veya son denemede logla
          if (this.reconnectAttempts === 0 || this.reconnectAttempts === this.maxReconnectAttempts - 1) {
            console.warn('⚠️ WebSocket bağlantı kesintisi, yeniden deneniyor...');
          }
          onStatusChange('disconnected');
          
          // 5 saniye bekle, sonra reconnect
          setTimeout(() => {
            if (!this.isManualDisconnect) {
              this.attemptReconnect(onMessage, onStatusChange);
            }
          }, 5000);
        }
      };

      this.ws.onerror = (error) => {
        clearTimeout(connectionTimeout);
        // Sadece kritik hataları logla
        if (this.reconnectAttempts === 0 || this.reconnectAttempts === this.maxReconnectAttempts) {
          console.error('❌ WebSocket bağlantı hatası (Deneme:', this.reconnectAttempts + 1, ')');
        }
        onStatusChange('error');
      };

    } catch (error) {
      console.error('WebSocket bağlantı hatası:', error);
      onStatusChange('error');
    }
  }

  // Heartbeat sistemi - Daha uzun interval ile stabil
  startHeartbeat() {
    this.stopHeartbeat();
    
    // İlk ping'i hemen gönder
    this.ping();
    
    // Heartbeat interval'i 60 saniye yap (daha az agresif)
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected && this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ping();
        
        // Timeout'u 10 saniye yap (daha toleranslı)
        this.heartbeatTimeout = setTimeout(() => {
          console.warn('⚠️ Heartbeat timeout (30s), bağlantı test ediliyor...');
          // Bağlantıyı test et
          if (this.ws && this.ws.readyState !== WebSocket.OPEN) {
            console.log('Bağlantı gerçekten kapalı, kapatılıyor...');
            this.ws.close();
          } else {
            console.log('Bağlantı hala açık, heartbeat devam ediyor');
          }
        }, 30000); // 30 saniye timeout (10s → 30s)
      }
    }, 60000); // 60 saniyede bir ping (daha az sık)
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  resetHeartbeatTimeout() {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  // Mesaj kuyruğu sistemi
  flushMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.sendMessage(message);
    }
  }

  // Yeniden bağlanma denemesi
  attemptReconnect(onMessage, onStatusChange) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`🔄 Yeniden bağlanma denemesi ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
      console.log(`🔄 WebSocket URL: ${this.wsURL}`);
      
      // Daha kısa delay ile hızlı retry
      const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), 10000);
      
      setTimeout(() => {
        console.log(`🔄 ${delay}ms sonra yeniden bağlanma deneniyor...`);
        this.connectWebSocket(onMessage, onStatusChange);
      }, delay);
    } else {
      console.error('❌ Maksimum yeniden bağlanma denemesi aşıldı');
      onStatusChange('failed');
    }
  }

  // WebSocket mesajı gönder
  sendMessage(message) {
    if (this.ws && this.isConnected) {
      try {
        this.ws.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('Mesaj gönderme hatası:', error);
        return false;
      }
    } else {
      console.log('WebSocket bağlantısı yok, mesaj kuyruğa alınıyor');
      this.messageQueue.push(message);
      return false;
    }
  }

  // Ping gönder
  ping() {
    this.sendMessage({ type: 'ping' });
  }

  // Scan başlat
  startScan(target, task = '') {
    this.sendMessage({
      type: 'start_scan',
      target: target,
      task: task
    });
  }

  // REST API ile scan başlat
  async startScanREST(target, task = '') {
    try {
      console.log(`REST API ile scan başlatılıyor: ${target}`);
      
      // Timeout wrapper for fetch (90s)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 90000); // 90s timeout
      
      const response = await fetch(`${this.baseURL}/api/scan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target: target,
          task: task
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);

      console.log('REST API response status:', response.status);

      if (!response.ok) {
        let errorDetail = '';
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorData.message || 'Unknown error';
        } catch {
          errorDetail = await response.text();
        }
        
        console.error('REST API error response:', errorDetail);
        
        // Error objesine detail field'ı ekle
        const error = new Error(errorDetail);
        error.detail = errorDetail;
        error.status = response.status;
        throw error;
      }

      const result = await response.json();
      console.log('REST API scan result:', result);
      return result;
    } catch (error) {
      if (error.name === 'AbortError') {
        console.error('⏱️ REST API timeout (90s):', error);
        throw new Error('Tarama başlatma zaman aşımına uğradı (90s). Lütfen tekrar deneyin.');
      }
      console.error('REST API scan hatası:', error);
      throw error;
    }
  }

  // Health check
  async healthCheck() {
    try {
      const response = await fetch(`${this.baseURL}/health`);
      return await response.json();
    } catch (error) {
      console.error('Health check hatası:', error);
      return { status: 'error', error: error.message };
    }
  }

  // Bağlantıyı kapat
  disconnect() {
    console.log('WebSocket bağlantısı manuel olarak kapatılıyor');
    this.isManualDisconnect = true;
    this.stopHeartbeat();
    
    if (this.ws) {
      // WebSocket'in durumunu kontrol et
      if (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN) {
        console.log('WebSocket bağlantısı kapatılıyor...');
        this.ws.close();
      }
      this.ws = null;
    }
    
    this.isConnected = false;
    this.messageQueue = [];
  }

  // Bağlantıyı yeniden başlat (React Strict Mode için)
  reconnect() {
    console.log('WebSocket bağlantısı yeniden başlatılıyor...');
    this.isManualDisconnect = false;
    this.reconnectAttempts = 0;
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.isConnected = false;
  }

  // ==================== RAG API METHODS ====================

  /**
   * RAG sistemi üzerinde CVE araması yap
   * @param {Object} params - Arama parametreleri
   * @param {string} params.query - Arama sorgusu
   * @param {number} params.limit - Maksimum sonuç sayısı (default: 5)
   * @param {string} params.severity - Opsiyonel severity filtresi (CRITICAL, HIGH, MEDIUM, LOW)
   * @returns {Promise<Object>} Arama sonuçları
   */
  async searchCVE({ query, limit = 5, severity = null }) {
    try {
      console.log('RAG CVE arama başlatılıyor:', { query, limit, severity });
      
      const response = await fetch(`${this.baseURL}/api/rag/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          limit,
          severity
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('RAG arama sonuçları:', result);
      return result;
    } catch (error) {
      console.error('RAG arama hatası:', error);
      throw error;
    }
  }

  /**
   * CVE ID ile direkt CVE detayı getir
   * @param {string} cveId - CVE ID (ör: CVE-2024-12345)
   * @returns {Promise<Object>} CVE detayları
   */
  async getCVEById(cveId) {
    try {
      console.log('CVE detayı getiriliyor:', cveId);
      
      const response = await fetch(`${this.baseURL}/api/rag/cve/${cveId}`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result.cve;
    } catch (error) {
      console.error('CVE getirme hatası:', error);
      throw error;
    }
  }

  /**
   * Tarama sonuçlarını analiz edip ilgili CVE'leri bul
   * @param {Object} scanResults - Tarama sonuçları
   * @param {number} limit - Maksimum sonuç sayısı (default: 5)
   * @returns {Promise<Object>} İlgili CVE'ler
   */
  async analyzeScanResults(scanResults, limit = 5) {
    try {
      console.log('Scan sonuçları analiz ediliyor:', { scanResults, limit });
      
      const response = await fetch(`${this.baseURL}/api/rag/analyze-scan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          scan_results: scanResults,
          limit
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Scan analiz sonuçları:', result);
      return result;
    } catch (error) {
      console.error('Scan analiz hatası:', error);
      throw error;
    }
  }

  /**
   * RAG servis istatistiklerini getir
   * @returns {Promise<Object>} İstatistikler
   */
  async getRagStats() {
    try {
      const response = await fetch(`${this.baseURL}/api/rag/stats`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result;
    } catch (error) {
      console.error('RAG stats hatası:', error);
      return { stats: { available: false, error: error.message } };
    }
  }
}

// Export singleton instance
export const pentagentAPI = new PentagentAPI();
export default PentagentAPI;
