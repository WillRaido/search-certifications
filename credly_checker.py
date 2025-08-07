import requests
import csv
import json
from bs4 import BeautifulSoup
import time

def search_credly_user(name, email):
    """Busca usuario en Credly y obtiene sus certificaciones"""
    try:
        # Buscar por nombre en Credly
        search_url = "https://www.credly.com/users/search"
        params = {'q': name}
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar enlaces de perfil
            profile_links = soup.find_all('a', href=lambda x: x and '/users/' in x)
            
            if profile_links:
                profile_url = "https://www.credly.com" + profile_links[0]['href']
                
                # Obtener certificaciones del perfil
                profile_response = requests.get(profile_url, headers=headers, timeout=10)
                profile_soup = BeautifulSoup(profile_response.text, 'html.parser')
                
                # Buscar badges/certificaciones
                badges = []
                badge_elements = profile_soup.find_all(['div', 'a'], class_=lambda x: x and ('badge' in x.lower() or 'credential' in x.lower()))
                
                for badge in badge_elements[:10]:  # Máximo 10 badges
                    badge_text = badge.get_text().strip()
                    if badge_text and len(badge_text) > 5:
                        badges.append(badge_text[:100])  # Limitar texto
                
                return {
                    'found': True,
                    'profile_url': profile_url,
                    'badges': badges,
                    'total': len(badges)
                }
        
        return {'found': False, 'badges': [], 'total': 0}
        
    except Exception as e:
        print(f"Error buscando {name}: {str(e)}")
        return {'found': False, 'badges': [], 'total': 0, 'error': str(e)}

def main():
    # Leer archivo CSV
    people = []
    try:
        with open('people.csv', 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                people.append({
                    'name': row['name'].strip(),
                    'email': row['email'].strip()
                })
    except FileNotFoundError:
        print("❌ Archivo people.csv no encontrado")
        return

    print(f"🔍 Verificando {len(people)} personas...")
    
    results = []
    
    for person in people:
        print(f"Buscando: {person['name']}")
        
        # Buscar certificaciones
        cert_info = search_credly_user(person['name'], person['email'])
        
        result = {
            'name': person['name'],
            'email': person['email'],
            'found': cert_info['found'],
            'total_certifications': cert_info['total'],
            'certifications': cert_info['badges']
        }
        
        if cert_info.get('profile_url'):
            result['profile_url'] = cert_info['profile_url']
            
        results.append(result)
        
        # Pausa para no sobrecargar el servidor
        time.sleep(2)
    
    # Guardar resultados
    with open('results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Mostrar resumen
    found = sum(1 for r in results if r['found'])
    total_certs = sum(r['total_certifications'] for r in results)
    
    print(f"\n📊 RESUMEN:")
    print(f"Personas verificadas: {len(results)}")
    print(f"Perfiles encontrados: {found}")
    print(f"Total certificaciones: {total_certs}")
    
    for result in results:
        status = "✅" if result['found'] else "❌"
        print(f"{status} {result['name']}: {result['total_certifications']} certificaciones")

if __name__ == "__main__":
    main()
