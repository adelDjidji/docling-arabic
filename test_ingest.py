"""
Test direct de l'endpoint /ingest avec le fichier PDF
"""
import requests
import json
import os

BASE_URL = "http://127.0.0.1:8001"
PDF_FILE = "برنامج_الرياضيات_3AS.pdf"

def test_ingest():
    """Test l'endpoint /ingest avec le fichier PDF"""
    print("\n" + "="*70)
    print("📄 Test de l'endpoint /ingest")
    print("="*70)
    print(f"URL: {BASE_URL}/ingest")
    print(f"Fichier: {PDF_FILE}")
    
    if not os.path.exists(PDF_FILE):
        print(f"❌ Erreur: Le fichier {PDF_FILE} n'existe pas")
        return False
    
    file_size = os.path.getsize(PDF_FILE)
    print(f"Taille du fichier: {file_size / 1024:.2f} KB")
    
    try:
        print(f"\n📤 Envoi du fichier...")
        with open(PDF_FILE, 'rb') as f:
            files = {'file': (PDF_FILE, f, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/ingest",
                files=files,
                timeout=600  # 10 minutes timeout pour le traitement
            )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Sauvegarder la réponse complète
            with open('response.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print("✅ Réponse sauvegardée dans response.json")
            
            if result.get('success'):
                print("\n✅ Succès!")
                print(f"Total chunks: {result.get('total_chunks', 'N/A')}")
                print(f"Sections détectées: {result.get('sections_count', 'N/A')}")
                print(f"Sections uniques: {result.get('unique_sections_in_chunks', 'N/A')}")
                
                if result.get('chunks'):
                    print(f"\n📊 Premier chunk:")
                    first_chunk = result['chunks'][0]
                    print(f"  Page: {first_chunk.get('meta', {}).get('page', 'N/A')}")
                    print(f"  Section: {first_chunk.get('meta', {}).get('section', 'N/A')[:80]}...")
                    print(f"  Texte (100 premiers caractères): {first_chunk.get('text', '')[:100]}...")
                
                return True
            else:
                print("\n❌ Échec de la conversion")
                print(f"Erreur: {result.get('error', 'Unknown error')}")
                
                if 'traceback' in result:
                    print(f"\n📋 Traceback complet:")
                    print(result['traceback'])
                
                # Sauvegarder aussi les erreurs
                with open('error_response.json', 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print("\n❌ Détails de l'erreur sauvegardés dans error_response.json")
                
                return False
        else:
            print(f"\n❌ Erreur HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"Erreur: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"Response: {response.text[:1000]}")
            return False
        
    except requests.exceptions.Timeout:
        print("❌ Erreur: Timeout - Le traitement prend trop de temps")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Erreur de connexion: {e}")
        print("   Assurez-vous que le serveur est démarré sur le port 8001")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 Test de l'API Docling Arabic - Endpoint /ingest")
    print("="*70)
    
    success = test_ingest()
    
    if success:
        print("\n✅ Test réussi!")
    else:
        print("\n❌ Test échoué")
        exit(1)
