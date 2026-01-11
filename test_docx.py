"""
Test script pour vérifier le support DOCX
"""
import requests
import json
import os

BASE_URL = "http://127.0.0.1:8001"

def test_docx_upload(docx_path):
    """Test l'upload d'un fichier DOCX"""
    print("\n" + "="*70)
    print("🧪 Test de l'upload DOCX")
    print("="*70)
    
    if not os.path.exists(docx_path):
        print(f"❌ Erreur: Le fichier {docx_path} n'existe pas")
        return False
    
    try:
        print(f"📤 Envoi du fichier: {docx_path}")
        with open(docx_path, 'rb') as f:
            files = {'file': (os.path.basename(docx_path), f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = requests.post(
                f"{BASE_URL}/ingest",
                files=files,
                timeout=300
            )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                print("\n✅ Succès!")
                print(f"Total chunks: {result.get('total_chunks', 'N/A')}")
                print(f"Sections détectées: {result.get('sections_count', 'N/A')}")
                print(f"Méthode: {result.get('method', 'N/A')}")
                
                if result.get('chunks'):
                    print(f"\n📊 Premier chunk:")
                    first_chunk = result['chunks'][0]
                    print(f"  Page: {first_chunk.get('meta', {}).get('page', 'N/A')}")
                    print(f"  Section: {first_chunk.get('meta', {}).get('section', 'N/A')[:60]}...")
                    print(f"  Texte (100 premiers caractères): {first_chunk.get('text', '')[:100]}...")
                
                return True
            else:
                print("\n❌ Échec")
                print(f"Erreur: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"\n❌ Erreur HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"Erreur: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 Test du support DOCX")
    print("="*70)
    
    # Chercher un fichier DOCX dans le répertoire
    docx_files = [f for f in os.listdir('.') if f.endswith('.docx')]
    
    if docx_files:
        docx_path = docx_files[0]
        print(f"📄 Fichier DOCX trouvé: {docx_path}")
        success = test_docx_upload(docx_path)
        exit(0 if success else 1)
    else:
        print("⚠️  Aucun fichier DOCX trouvé dans le répertoire")
        print("   Utilisez: python test_docx.py <chemin_vers_docx>")
        import sys
        if len(sys.argv) > 1:
            docx_path = sys.argv[1]
            success = test_docx_upload(docx_path)
            exit(0 if success else 1)
