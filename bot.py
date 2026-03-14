import google.generativeai as genai
import asyncio
import edge_tts
import requests
import re
import os
import datetime
import time
import platform
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
import moviepy.video.fx.all as vfx

import upload 

# ==========================================
# CONFIGURAÇÃO DE AMBIENTE E SEGURANÇA
# ==========================================
# Detecta se está no Windows (seu PC) ou Linux (GitHub Actions)
if platform.system() == 'Windows':
    os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
else:
    os.environ["IMAGEMAGICK_BINARY"] = "/usr/bin/convert"

# Puxa as chaves do cofre do GitHub Secrets
CHAVE_GEMINI = os.environ.get("GEMINI_API_KEY")
CHAVE_PEXELS = os.environ.get("PEXELS_API_KEY")

if not CHAVE_GEMINI or not CHAVE_PEXELS:
    print("[-] ERRO FATAL: Chaves de API não encontradas no ambiente virtual!")
    exit()

genai.configure(api_key=CHAVE_GEMINI)

# ==========================================
# 2. MÓDULO DE TENDÊNCIAS E DIREÇÃO DE ARTE
# ==========================================
def obter_tema_e_visual_em_alta():
    agora = datetime.datetime.now()
    hora_formatada = agora.strftime("%H:%M")
    
    if agora.hour < 12:
        contexto = "Notícias atualizadas do dia, fatos históricos incríveis ou histórias inspiradoras reais."
    elif agora.hour < 18:
        contexto = "Curiosidades fascinantes do mundo, descobertas científicas ou mistérios resolvidos."
    else:
        contexto = "Histórias intrigantes, teorias da conspiração, crimes reais (true crime) ou casos assustadores."

    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    prompt = f"""
    Aja como um Diretor de TV focado em INFORMAÇÃO e STORYTELLING.
    O público neste horário prefere: {contexto}.
    
    Gere UM tema viral e INFORMATIVO para um vídeo do TikTok. 
    REGRAS: 
    - NÃO faça vídeos promocionais. 
    - NÃO promova IAs ou produtos. 
    - NUNCA mencione o horário atual no tema. O horário é apenas para você saber o que as pessoas querem assistir agora.
    
    Você também deve sugerir 1 ou 2 palavras-chave EM INGLÊS que representem visualmente esse tema para buscarmos um vídeo de fundo.
    
    Retorne APENAS essas duas informações separadas por uma barra vertical (|).
    Exemplo 1: A verdadeira história por trás do triângulo das bermudas | ocean mystery
    """
    resposta = model.generate_content(prompt).text.strip()
    
    try:
        tema, termo_visual = resposta.split('|')
        return tema.strip(), termo_visual.strip()
    except:
        return resposta.replace('|', '').strip(), "nature"

def gerar_roteiro(tema):
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    prompt = f"""
    Aja como um Narrador de Documentários ou Jornalista. Crie um roteiro INFORMATIVO e magnético para o TikTok sobre o tema: "{tema}".
    
    REGRAS OBRIGATÓRIAS:
    1. O tom deve ser de contação de histórias (storytelling) ou jornalístico (reportagem).
    2. NUNCA promova produtos, ferramentas de IA ou faça propagandas.
    3. NUNCA faça referências a horário.
    4. O texto precisa ter entre 160 e 180 palavras (para a narração ultrapassar 60 segundos).
    5. Comece com um gancho psicológico forte que desperte curiosidade imediata.
    
    Retorne APENAS o texto narrado, sem aspas, sem emojis, sem saudações e sem marcações de cena.
    """
    resposta = model.generate_content(prompt)
    return resposta.text.strip()

# ==========================================
# 3. MÓDULO DE VOZ E LEGENDAS
# ==========================================
def formatar_tempo_vtt(tempo_em_100ns):
    ms = tempo_em_100ns / 10000
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02}.{int(ms):03}"

async def gerar_audio_e_legendas(texto, arquivo_audio, arquivo_legenda):
    voz = "pt-BR-AntonioNeural" 
    comunicar = edge_tts.Communicate(texto, voz)
    palavras_sincronizadas = []
    
    with open(arquivo_audio, "wb") as arquivo:
        async for pedaco in comunicar.stream():
            if pedaco["type"] == "audio":
                arquivo.write(pedaco["data"])
            elif pedaco["type"] == "WordBoundary":
                inicio = formatar_tempo_vtt(pedaco["offset"])
                fim = formatar_tempo_vtt(pedaco["offset"] + pedaco["duration"])
                palavras_sincronizadas.append(f"{inicio} --> {fim}\n{pedaco['text']}\n")
                
    with open(arquivo_legenda, "w", encoding="utf-8") as arquivo_vtt:
        arquivo_vtt.write("WEBVTT\n\n")
        arquivo_vtt.write("\n".join(palavras_sincronizadas))

# ==========================================
# 4. MÓDULO DE VÍDEO
# ==========================================
def baixar_video_fundo(termo_busca, arquivo_saida):
    print(f"[*] Buscando vídeo no Pexels com o termo: '{termo_busca}'")
    url = f"https://api.pexels.com/videos/search?query={termo_busca}&per_page=1&orientation=portrait"
    headers = {"Authorization": CHAVE_PEXELS}
    resposta = requests.get(url, headers=headers).json()
    
    if resposta.get('videos') and len(resposta['videos']) > 0:
        link_video = resposta['videos'][0]['video_files'][0]['link']
        video_data = requests.get(link_video).content
        with open(arquivo_saida, 'wb') as f:
            f.write(video_data)
        print("[+] Vídeo de fundo baixado com sucesso.")
    else:
        print("[-] Nenhum vídeo encontrado. Usando termo genérico 'nature'.")
        url = f"https://api.pexels.com/videos/search?query=nature&per_page=1&orientation=portrait"
        link_video = requests.get(url, headers=headers).json()['videos'][0]['video_files'][0]['link']
        with open(arquivo_saida, 'wb') as f:
            f.write(requests.get(link_video).content)

# ==========================================
# 5. MÓDULO DE EDIÇÃO
# ==========================================
def extrair_tempos_textos(arquivo_vtt):
    legendas = []
    with open(arquivo_vtt, 'r', encoding='utf-8') as f:
        conteudo = f.read().strip()
    blocos = re.split(r'\n\n+', conteudo)
    
    for bloco in blocos:
        linhas = bloco.strip().split('\n')
        if len(linhas) >= 2 and '-->' in linhas[0]:
            tempos = linhas[0].split(' --> ')
            def converter_para_segundos(t):
                h, m, s = t.split(':')
                s, ms = s.split('.')
                return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
            inicio = converter_para_segundos(tempos[0])
            fim = converter_para_segundos(tempos[1])
            texto = " ".join(linhas[1:]).strip()
            legendas.append(((inicio, fim), texto))
    return legendas

def montar_video_final(arquivo_video, arquivo_audio, arquivo_legenda, arquivo_saida):
    print(f"\n[*] Montando o vídeo final longo: {arquivo_saida}")
    video = VideoFileClip(arquivo_video)
    audio = AudioFileClip(arquivo_audio)
    
    if video.duration < audio.duration:
        video = video.fx(vfx.loop, duration=audio.duration)
    else:
        video = video.subclip(0, audio.duration)
    
    video = video.set_audio(audio)
    tempos_textos = extrair_tempos_textos(arquivo_legenda)
    clips_legenda = []
    
    for (inicio, fim), texto in tempos_textos:
        txt_clip = TextClip(texto, fontsize=90, color='yellow', font='Impact', stroke_color='black', stroke_width=3)
        txt_clip = txt_clip.set_position(('center', 'center')).set_start(inicio).set_end(fim)
        clips_legenda.append(txt_clip)
            
    video_final = CompositeVideoClip([video] + clips_legenda)
    video_final.write_videofile(arquivo_saida, fps=30, codec="libx264", audio_codec="aac", logger=None)
    
    video.close()
    audio.close()
    video_final.close()

# ==========================================
# 6. MÓDULO DE LIMPEZA
# ==========================================
def limpar_arquivos_temporarios(arquivos):
    print("\n[*] Iniciando faxina do sistema...")
    for arquivo in arquivos:
        if os.path.exists(arquivo):
            try:
                os.remove(arquivo)
                print(f"[-] Arquivo apagado: {arquivo}")
            except Exception as e:
                pass

# ==========================================
# 7. MOTOR DE EXECUÇÃO
# ==========================================
async def main():
    print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] --- INICIANDO CRIAÇÃO NA NUVEM ---")
    
    tema_de_hoje, termo_visual = obter_tema_e_visual_em_alta()
    print(f"[*] TEMA CAPTURADO: {tema_de_hoje}")
    
    nome_limpo = re.sub(r'[^a-zA-Z0-9\s]', '', tema_de_hoje)
    nome_arquivo_base = nome_limpo.replace(' ', '_')[:40] 
    arquivo_mp4_final = f"{nome_arquivo_base}.mp4"
    
    audio_temp = "audio_temp.mp3"
    legenda_temp = "legenda_temp.vtt"
    fundo_temp = "fundo_temp.mp4"
    
    await gerar_audio_e_legendas(gerar_roteiro(tema_de_hoje), audio_temp, legenda_temp)
    baixar_video_fundo(termo_visual, fundo_temp) 
    montar_video_final(fundo_temp, audio_temp, legenda_temp, arquivo_mp4_final)
    
    print("\n4. Iniciando Upload Automático...")
    texto_postagem = f"{tema_de_hoje} #curiosidades #historia #noticias"
    upload.postar_no_tiktok(arquivo_mp4_final, texto_postagem)
    
    print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] [*] Aguardando 5 minutos de segurança...")
    time.sleep(300)
    
    limpar_arquivos_temporarios([audio_temp, legenda_temp, fundo_temp, arquivo_mp4_final])
    print("[+] O disco do servidor foi limpo.")

if __name__ == "__main__":
    asyncio.run(main())
