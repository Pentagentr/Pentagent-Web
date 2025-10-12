// Firebase Configuration
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth, setPersistence, browserLocalPersistence } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyCY0dLD1uHXsY_E0QlY2d1wS1YyGWw7_dg",
  authDomain: "pentagent-b9007.firebaseapp.com",
  projectId: "pentagent-b9007",
  storageBucket: "pentagent-b9007.firebasestorage.app",
  messagingSenderId: "348500747735",
  appId: "1:348500747735:web:03201a7d18349809725792",
  measurementId: "G-F1B35TS475"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const auth = getAuth(app);
const db = getFirestore(app);

// Oturum açık kalmasını sağla (persistent login)
setPersistence(auth, browserLocalPersistence).catch((error) => {
  console.error("Auth persistence error:", error);
});

export { app, analytics, auth, db };
export default firebaseConfig;

