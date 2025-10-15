import { db } from '../config/firebase';
import { 
  collection, 
  addDoc, 
  query, 
  where, 
  orderBy, 
  limit as firestoreLimit, 
  getDocs,
  doc,
  getDoc,
  serverTimestamp 
} from 'firebase/firestore';

/**
 * Tarama geçmişi için Firestore servisi
 */
class ScanHistoryService {
  constructor() {
    this.collectionName = 'scan_history';
  }

  /**
   * Yeni tarama kaydı oluştur
   */
  async saveScan(userId, scanData) {
    try {
      const scanRecord = {
        userId,
        target: scanData.target || 'Unknown',
        scanResults: scanData.scanResults || {},
        cveResults: scanData.cveResults || [],
        summary: scanData.summary || '',
        toolsUsed: scanData.toolsUsed || [],
        findingsCount: scanData.findingsCount || 0,
        riskLevel: scanData.riskLevel || 'unknown',
        createdAt: serverTimestamp(),
        status: 'completed'
      };

      const docRef = await addDoc(collection(db, this.collectionName), scanRecord);
      
      return {
        id: docRef.id,
        ...scanRecord,
        createdAt: new Date().toISOString()
      };
    } catch (error) {
      console.error('Tarama kaydedilemedi:', error);
      throw error;
    }
  }

  /**
   * Kullanıcının tarama geçmişini getir
   */
  async getUserScans(userId, limitCount = 20) {
    try {
      const q = query(
        collection(db, this.collectionName),
        where('userId', '==', userId),
        orderBy('createdAt', 'desc'),
        firestoreLimit(limitCount)
      );

      const querySnapshot = await getDocs(q);
      const scans = [];

      querySnapshot.forEach((doc) => {
        scans.push({
          id: doc.id,
          ...doc.data(),
          createdAt: doc.data().createdAt?.toDate?.()?.toISOString() || new Date().toISOString()
        });
      });

      return scans;
    } catch (error) {
      console.error('Tarama geçmişi getirilemedi:', error);
      throw error;
    }
  }

  /**
   * Tek bir tarama kaydını getir
   */
  async getScan(scanId) {
    try {
      const docRef = doc(db, this.collectionName, scanId);
      const docSnap = await getDoc(docRef);

      if (docSnap.exists()) {
        return {
          id: docSnap.id,
          ...docSnap.data(),
          createdAt: docSnap.data().createdAt?.toDate?.()?.toISOString() || new Date().toISOString()
        };
      } else {
        throw new Error('Tarama bulunamadı');
      }
    } catch (error) {
      console.error('Tarama getirilemedi:', error);
      throw error;
    }
  }
}

export const scanHistoryService = new ScanHistoryService();

