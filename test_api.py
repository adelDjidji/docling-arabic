"""
Script de test pour l'API Docling Arabic
"""
import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test l'endpoint /health"""
    print("\n" + "="*70)
    print("🔍 Test de l'endpoint /health")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ Erreur: Le serveur n'est pas démarré ou n'est pas accessible")
        print("   Assurez-vous que le serveur est en cours d'exécution sur le port 8000")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_ingest(pdf_path):
    """Test l'endpoint /ingest avec un fichier PDF"""
    print("\n" + "="*70)
    print("📄 Test de l'endpoint /ingest")
    print("="*70)
    
    if not os.path.exists(pdf_path):
        print(f"❌ Erreur: Le fichier {pdf_path} n'existe pas")
        return False
    
    try:
        print(f"📤 Envoi du fichier: {pdf_path}")
        with open(pdf_path, 'rb') as f:
            files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/ingest",
                files=files,
                timeout=300  # 5 minutes timeout pour le traitement
            )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Succès!")
            print(f"Total chunks: {result.get('total_chunks', 'N/A')}")
            print(f"Sections détectées: {result.get('sections_count', 'N/A')}")
            print(f"Sections uniques: {result.get('unique_sections_in_chunks', 'N/A')}")
            
            if result.get('success'):
                print("\n📊 Résumé:")
                print(f"  - Méthode: {result.get('method', 'N/A')}")
                print(f"  - Chunks totaux: {result.get('total_chunks', 0)}")
                if result.get('chunks'):
                    print(f"  - Premier chunk (extrait):")
                    first_chunk = result['chunks'][0]
                    print(f"    Page: {first_chunk.get('meta', {}).get('page', 'N/A')}")
                    print(f"    Section: {first_chunk.get('meta', {}).get('section', 'N/A')[:60]}...")
                    print(f"    Texte: {first_chunk.get('text', '')[:100]}...")
            else:
                print("\n❌ Échec de la conversion")
                print(f"Erreur: {result.get('error', 'Unknown error')}")
                if 'traceback' in result:
                    print(f"\nTraceback:\n{result['traceback']}")
                return False
        else:
            print(f"\n❌ Erreur HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"Erreur: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"Response: {response.text[:500]}")
            return False
        
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Erreur: Timeout - Le traitement prend trop de temps")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import os
    
    print("\n" + "="*70)
    print("🧪 Tests de l'API Docling Arabic")
    print("="*70)
    
    # Test 1: Health check
    if not test_health():
        print("\n❌ Le test de santé a échoué. Arrêt des tests.")
        sys.exit(1)
    
    # Test 2: Ingest avec un fichier PDF
    # Chercher un fichier PDF dans le répertoire
    pdf_files = [
        "برنامج_الرياضيات_3AS.pdf",
        "برنامج_الرياضيات_3AS_صحيح.pdf"
    ]
    
    pdf_path = None
    for pdf_file in pdf_files:
        if os.path.exists(pdf_file):
            pdf_path = pdf_file
            break
    
    if pdf_path:
        success = test_ingest(pdf_path)
        if success:
            print("\n✅ Tous les tests sont passés!")
            sys.exit(0)
        else:
            print("\n❌ Le test d'ingestion a échoué")
            sys.exit(1)
    else:
        print("\n⚠️  Aucun fichier PDF trouvé pour le test")
        print("   Utilisez: python test_api.py <chemin_vers_pdf>")
        if len(sys.argv) > 1:
            pdf_path = sys.argv[1]
            success = test_ingest(pdf_path)
            sys.exit(0 if success else 1)
