from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os

def postar_no_tiktok(caminho_video, descricao):
    print("\n[*] Iniciando módulo de postagem via Selenium...")
    
    if not os.path.exists(caminho_video):
        print(f"[-] Erro: Arquivo {caminho_video} não encontrado na pasta.")
        return False

    caminho_absoluto = os.path.abspath(caminho_video)

    opcoes = Options()
    caminho_perfil = os.path.abspath("./sessao_tiktok_selenium")
    opcoes.add_argument(f"user-data-dir={caminho_perfil}")
    opcoes.add_argument("--disable-blink-features=AutomationControlled")
    opcoes.add_experimental_option("excludeSwitches", ["enable-automation"])
    opcoes.add_experimental_option('useAutomationExtension', False)

    print("[*] Iniciando o Google Chrome...")
    servico = Service(ChromeDriverManager().install())
    navegador = webdriver.Chrome(service=servico, options=opcoes)

    try:
        print("[*] Acessando a página de upload...")
        navegador.get("https://www.tiktok.com/creator-center/upload")
        
        # Como você já logou antes, a sessão deve estar salva. 
        # Deixei apenas 15 segundos agora, pois a página já deve entrar logada.
        print("\n[*] Aguardando a página carregar (15 segundos)...")
        time.sleep(15)

        print("[*] Buscando o campo de inserção de vídeo...")
        input_arquivo = WebDriverWait(navegador, 60).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='file' and @accept='video/*']"))
        )
        input_arquivo.send_keys(caminho_absoluto)

        print("[*] Aguardando 30 segundos para o upload no servidor do TikTok concluir...")
        time.sleep(30)

        print("[*] Escrevendo a legenda do vídeo...")
        caixa_texto = WebDriverWait(navegador, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".public-DraftEditor-content"))
        )
        caixa_texto.click()
        time.sleep(1)
        navegador.execute_script("arguments[0].innerText = ''", caixa_texto)
        caixa_texto.send_keys(descricao)
        
        time.sleep(3)

        print("[*] Procurando botão de Publicar...")
        botoes = navegador.find_elements(By.XPATH, "//button")
        for btn in botoes:
            texto = btn.text.strip().lower()
            if "post" in texto or "publicar" in texto:
                # O PULO DO GATO: Executa o clique via JavaScript, ignorando qualquer sobreposição (como o menu de hashtags)
                navegador.execute_script("arguments[0].click();", btn)
                print("[+] Clique de publicação efetuado com sucesso (Via JS)!")
                break
                
        print("[*] Aguardando 15 segundos de tolerância para a plataforma confirmar a postagem...")
        time.sleep(15) 

    except Exception as e:
        print(f"[-] Erro durante a automação visual. Detalhes: {e}")
    finally:
        navegador.quit()