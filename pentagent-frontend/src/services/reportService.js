import { 
  collection, 
  addDoc, 
  getDocs,
  getDoc,
  doc,
  query, 
  where, 
  orderBy, 
  limit,
  serverTimestamp 
} from 'firebase/firestore';
import { db } from '../config/firebase';

const REPORTS_COLLECTION = 'reports';

export const reportService = {
  /**
   * Yeni rapor kaydet
   */
  async saveReport(userId, reportData) {
    try {
      const reportRef = await addDoc(collection(db, REPORTS_COLLECTION), {
        userId,
        target: reportData.target,
        report_id: reportData.report_id,
        risk_score: reportData.risk_score || 0,
        vulnerabilities: reportData.vulnerabilities || { critical: 0, high: 0, medium: 0, low: 0 },
        pages: reportData.pages || 0,
        structured_data: reportData.structured_data || null,
        all_tool_outputs: reportData.all_tool_outputs || null, // Tool çıktılarını ekle
        files: reportData.files || null,
        download_url: reportData.download_url || null,
        createdAt: serverTimestamp(),
        status: 'completed'
      });
      
      return { id: reportRef.id, ...reportData };
    } catch (error) {
      console.error('Rapor kaydetme hatası:', error);
      throw error;
    }
  },

  /**
   * Kullanıcının raporlarını getir
   */
  async getUserReports(userId, limitCount = 50) {
    try {
      const q = query(
        collection(db, REPORTS_COLLECTION),
        where('userId', '==', userId),
        orderBy('createdAt', 'desc'),
        limit(limitCount)
      );
      
      const querySnapshot = await getDocs(q);
      const reports = [];
      
      querySnapshot.forEach((doc) => {
        const data = doc.data();
        reports.push({
          id: doc.id,
          ...data,
          createdAt: data.createdAt?.toDate().toISOString() || new Date().toISOString()
        });
      });
      
      return reports;
    } catch (error) {
      console.error('Raporları getirme hatası:', error);
      throw error;
    }
  },

  /**
   * Tek bir rapor getir
   */
  async getReport(reportId) {
    try {
      const reportDoc = await getDoc(doc(db, REPORTS_COLLECTION, reportId));
      if (reportDoc.exists()) {
        const data = reportDoc.data();
        return {
          id: reportDoc.id,
          ...data,
          createdAt: data.createdAt?.toDate().toISOString() || new Date().toISOString()
        };
      }
      return null;
    } catch (error) {
      console.error('Rapor getirme hatası:', error);
      throw error;
    }
  }
};

