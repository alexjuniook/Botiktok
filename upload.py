from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import json

def postar_no_tiktok(caminho_video, descricao):
    print("\n[*] Iniciando módulo de postagem na Nuvem (Injeção de Cookies)...")
    
    if not os.path.exists(caminho_video):
        print(f"[-] Erro: Arquivo {caminho_video} não encontrado.")
        return False

    caminho_absoluto = os.path.abspath(caminho_video)

    opcoes = Options()
    opcoes.add_argument("--headless=new")
    opcoes.add_argument("--window-size=1920,1080")
    opcoes.add_argument("--disable-dev-shm-usage")
    opcoes.add_argument("--no-sandbox")
    
    opcoes.add_argument("--disable-blink-features=AutomationControlled")
    opcoes.add_experimental_option("excludeSwitches", ["enable-automation"])
    opcoes.add_experimental_option('useAutomationExtension', False)

    servico = Service(ChromeDriverManager().install())
    navegador = webdriver.Chrome(service=servico, options=opcoes)

    try:
        print("[*] Preparando o navegador e acessando o domínio base...")
        navegador.get("https://www.tiktok.com")
        time.sleep(5)

        print("[*] Injetando a sessão de login salva no cofre...")
        cookies_str = os.environ.get("TIKTOK_COOKIES")
        
        if not cookies_str:
            print("[-] ERRO FATAL: Variável TIKTOK_COOKIES não foi encontrada no ambiente!")
            return False

        cookies = json.loads(cookies_str)
        for cookie in cookies:
            try:
                navegador.add_cookie({
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie.get('domain', '.tiktok.com'),
                    'path': cookie.get('path', '/')
                })
            except Exception as e:
                pass

        print("[+] Login fantasma realizado! Acessando a página de upload...")
        navegador.get("https://www.tiktok.com/creator-center/upload")
        
        print("\n[*] Aguardando a página carregar (15 segundos)...")
        time.sleep(15)

        # ---------------------------------------------------------
        # NOVO: DESTRUIDOR DE POPUPS E TUTORIAIS
        # ---------------------------------------------------------
        print("[*] Limpando popups e tutoriais da tela...")
        try:
            navegador.execute_script("""
                var overlays = document.querySelectorAll('[class*="react-joyride"], [class*="modal"], [class*="overlay"]');
                overlays.forEach(e => e.remove());
            """)
        except:
            pass
        # ---------------------------------------------------------

        print("[*] Buscando o campo de inserção de vídeo...")
        input_arquivo = WebDriverWait(navegador, 60).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='file' and @accept='video/*']"))
        )
        input_arquivo.send_keys(caminho_absoluto)

        print("[*] Aguardando 40 segundos para o upload completo no servidor...")
        time.sleep(40)

        print("[*] Escrevendo a legenda do vídeo...")
        caixa_texto = WebDriverWait(navegador, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".public-DraftEditor-content"))
        )
        
        # Clique forçado via JS para ignorar qualquer obstáculo invisível
        navegador.execute_script("arguments[0].click();", caixa_texto)
        time.sleep(1)
        navegador.execute_script("arguments[0].innerText = ''", caixa_texto)
        caixa_texto.send_keys(descricao)
        time.sleep(3)
        
        print("[*] Fechando o menu de hashtags...")
        caixa_texto.send_keys(Keys.ESCAPE)
        time.sleep(3)

        print("[*] Procurando botão de Publicar...")
        botoes = navegador.find_elements(By.XPATH, "//button")
        for btn in botoes:
            texto = btn.text.strip().lower()
            if "post" in texto or "publicar" in texto:
                tentativas = 0
                while (btn.get_attribute("disabled") or btn.get_attribute("aria-disabled") == "true") and tentativas < 10:
                    print("[!] O botão está bloqueado (TikTok processando). Aguardando mais 10s...")
                    time.sleep(10)
                    tentativas += 1
                
                # Clique forçado no botão de publicar para garantir
                navegador.execute_script("arguments[0].click();", btn)
                print("[+] Clique NATIVO de publicação efetuado com sucesso!")
                break
                
        print("[*] Aguardando 20 segundos para a plataforma exibir a tela de confirmação...")
        time.sleep(20) 

    except Exception as e:
        print(f"[-] Erro durante a automação visual na nuvem. Detalhes: {e}")
    finally:
        navegador.quit()
