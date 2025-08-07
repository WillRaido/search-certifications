import requests
import csv
import json
from bs4 import BeautifulSoup
import time
from urllib.parse import quote

def search_github_credly_directory(name):
    """Busca usuario en el directorio de GitHub en Credly por nombre"""
    try:
        # URL del directorio de GitHub en Credly con filtro por nombre
        search_url = "https://www.credly.com/organizations/github/directory"
        params = {'filter[user_name]': name}
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"  Buscando en: {search_url}?filter%5Buser_name%5D={quote(name)}")
        
        response = requests.get(search_url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar resultados en el directorio
            user_cards = soup.find_all(['div', 'article'], class_=lambda x: x and any(word in x.lower() for word in ['user', 'profile', 'card', 'member']))
            
            if not user_cards:
                # Buscar enlaces de perfil alternativos
                profile_links = soup.find_all('a', href=lambda x: x and '/users/' in x)
                if profile_links:
                    user_cards = [link.parent for link in profile_links]
            
            if user_cards:
                # Tomar el primer resultado
                user_card = user_cards[0]
                
                # Buscar enlace al perfil
                profile_link = user_card.find('a', href=lambda x: x and '/users/' in x)
                if profile_link:
                    profile_url = profile_link['href']
                    if not profile_url.startswith('http'):
                        profile_url = "https://www.credly.com" + profile_url
                    
                    # Obtener certificaciones del perfil
                    return get_user_certifications(profile_url, headers)
                
            # Si no encontramos en el directorio, intentar búsqueda directa por URL
            direct_url = f"https://www.credly.com/organizations/github/directory?filter%5Buser_name%5D={quote(name)}"
            print(f"  Intentando URL directa: {direct_url}")
            
            # Verificar si hay algún resultado en la página
            page_text = soup.get_text().lower()
            if 'no results' in page_text or 'no se encontraron' in page_text:
                return {'found': False, 'badges': [], 'total': 0}
            
            # Buscar cualquier badge o certificación en la página
            badges = extract_badges_from_page(soup)
            if badges:
                return {
                    'found': True,
                    'profile_url': direct_url,
                    'badges': badges,
                    'total': len(badges)
                }
        
        return {'found': False, 'badges': [], 'total': 0}
        
    except Exception as e:
        print(f"  Error buscando {name}: {str(e)}")
        return {'found': False, 'badges': [], 'total': 0, 'error': str(e)}

def get_user_certifications(profile_url, headers):
    """Obtiene certificaciones de un perfil específico"""
    try:
        print(f"  Obteniendo certificaciones de: {profile_url}")
        response = requests.get(profile_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            badges = extract_badges_from_page(soup)
            
            return {
                'found': True,
                'profile_url': profile_url,
                'badges': badges,
                'total': len(badges)
            }
    except Exception as e:
        print(f"  Error obteniendo certificaciones: {str(e)}")
    
    return {'found': False, 'badges': [], 'total': 0}

def extract_badges_from_page(soup):
    """Extrae badges/certificaciones de una página"""
    badges = []
    
    # Buscar diferentes tipos de elementos que contengan badges
    badge_selectors = [
        {'class': lambda x: x and 'badge' in x.lower()},
        {'class': lambda x: x and 'credential' in x.lower()},
        {'class': lambda x: x and 'cert' in x.lower()},
        {'title': lambda x: x and any(word in x.lower() for word in ['github', 'certified', 'badge'])},
    ]
    
    for selector in badge_selectors:
        elements = soup.find_all(['div', 'a', 'span', 'h3', 'h4'], **selector)
        
        for element in elements:
            badge_text = element.get_text().strip()
            if badge_text and len(badge_text) > 5 and len(badge_text) < 200:
                # Filtrar solo badges relacionados con GitHub
                if any(keyword in badge_text.lower() for keyword in ['github', 'git', 'actions', 'copilot', 'foundations']):
                    badges.append(badge_text)
    
    # Remover duplicados manteniendo orden
    unique_badges = []
    for badge in badges:
        if badge not in unique_badges:
            unique_badges.append(badge)
    
    return unique_badges[:10]  # Máximo 10 badges

def main():
    # Leer archivo CSV (solo necesita nombre)
    people = []
    try:
        with open('people.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                people.append({
                    'name': row['name'].strip()
                })
    except FileNotFoundError:
        print("❌ Archivo people.csv no encontrado")
        # Crear archivo de ejemplo
        with open('people.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['name'])
            writer.writerow(['William Quintero'])
            writer.writerow(['Tu Nombre'])
        print("✅ Archivo people.csv creado con ejemplos")
        return

    print(f"🔍 Verificando {len(people)} personas en GitHub Credly Directory...")
    print("🌐 URL base: https://www.credly.com/organizations/github/directory")
    
    results = []
    
    for i, person in enumerate(people, 1):
        print(f"\n[{i}/{len(people)}] Buscando: {person['name']}")
        
        # Buscar certificaciones en el directorio de GitHub
        cert_info = search_github_credly_directory(person['name'])
        
        result = {
            'name': person['name'],
            'found': cert_info['found'],
            'total_certifications': cert_info['total'],
            'certifications': cert_info['badges']
        }
        
        if cert_info.get('profile_url'):
            result['profile_url'] = cert_info['profile_url']
        
        if cert_info.get('error'):
            result['error'] = cert_info['error']
            
        results.append(result)
        
        # Mostrar resultado inmediato
        if cert_info['found']:
            print(f"  ✅ Encontrado - {cert_info['total']} certificaciones")
            for badge in cert_info['badges'][:3]:  # Mostrar primeras 3
                print(f"    • {badge}")
        else:
            print(f"  ❌ No encontrado en el directorio de GitHub")
        
        # Pausa para no sobrecargar el servidor
        time.sleep(3)
    
    # Guardar resultados
    with open('results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Crear reporte simple
    with open('report.txt', 'w', encoding='utf-8') as f:
        f.write("🏆 REPORTE DE CERTIFICACIONES GITHUB - CREDLY\n")
        f.write("=" * 50 + "\n\n")
        
        found = sum(1 for r in results if r['found'])
        total_certs = sum(r['total_certifications'] for r in results)
        
        f.write(f"📊 RESUMEN:\n")
        f.write(f"Personas verificadas: {len(results)}\n")
        f.write(f"Perfiles encontrados: {found}\n")
        f.write(f"Total certificaciones: {total_certs}\n\n")
        
        f.write("📄 DETALLE:\n")
        for result in results:
            status = "✅ ENCONTRADO" if result['found'] else "❌ NO ENCONTRADO"
            f.write(f"\n{result['name']}: {status}\n")
            
            if result['found']:
                f.write(f"  Certificaciones: {result['total_certifications']}\n")
                if result.get('profile_url'):
                    f.write(f"  URL: {result['profile_url']}\n")
                
                for cert in result['certifications']:
                    f.write(f"  • {cert}\n")
    
    # Mostrar resumen final
    print(f"\n🎯 RESUMEN FINAL:")
    print(f"Personas verificadas: {len(results)}")
    print(f"Perfiles encontrados: {found}")  
    print(f"Total certificaciones: {total_certs}")
    
    print(f"\n📄 Archivos generados:")
    print(f"  • results.json - Datos completos")
    print(f"  • report.txt - Reporte legible")
    
    if found > 0:
        print(f"\n✅ Personas con certificaciones GitHub:")
        for result in results:
            if result['found']:
                print(f"  • {result['name']}: {result['total_certifications']} certificaciones")

if __name__ == "__main__":
    main()
