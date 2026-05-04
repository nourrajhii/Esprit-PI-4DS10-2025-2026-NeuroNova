import torch
from diffusers import StableDiffusionImg2ImgPipeline
import gradio as gr
from PIL import Image
import requests
import time
import os
import json
import base64
from datetime import datetime

# -----------------------------
# CONFIGURATION API TRIPO3D
# -----------------------------
API_KEY = "tsk_dZ7wLa-PIwzFlfRgpoIhRy_eMbk2C8F9suwMdpCP0Mr"
BASE_URL = "https://api.tripo3d.ai/v2/openapi"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# -----------------------------
# CHARGEMENT MODÈLE 2D
# -----------------------------
print("🚀 Chargement du modèle Stable Diffusion avec LoRA villa...")
model_id = "runwayml/stable-diffusion-v1-5"

pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
    model_id,
    torch_dtype=torch.float32
)

print("📦 Chargement du LoRA villa...")
pipe.load_lora_weights("lora-villa")
pipe = pipe.to("cpu")
print("✅ Modèles chargés!")

generated_image = None
current_model_file = None

# -----------------------------
# FONCTIONS API TRIPO3D
# -----------------------------

def upload_to_tripo3d(image_path):
    upload_url = f"{BASE_URL}/upload/sts"
    
    with open(image_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            upload_url,
            headers={"Authorization": f"Bearer {API_KEY}"},
            files=files,
            timeout=30
        )
    
    if response.status_code != 200:
        return None, f"Erreur HTTP {response.status_code}"
    
    result = response.json()
    
    if result.get('code') != 0:
        return None, f"Erreur API: {result.get('message')}"
    
    image_token = result.get('data', {}).get('image_token')
    return image_token, None

def create_task(image_token):
    task_url = f"{BASE_URL}/task"
    
    payload = {
        "type": "image_to_model",
        "model_version": "v2.5-20250123",
        "file": {"type": "png", "file_token": image_token},
        "texture": True,
        "face_limit": 50000
    }
    
    response = requests.post(task_url, headers=headers, json=payload, timeout=30)
    
    if response.status_code != 200:
        return None, f"Erreur HTTP {response.status_code}"
    
    result = response.json()
    
    if result.get('code') != 0:
        return None, f"Erreur API: {result.get('message')}"
    
    task_id = result.get('data', {}).get('task_id')
    return task_id, None

def wait_and_get_model(task_id):
    """Attend la fin et retourne l'URL du modèle GLB"""
    status_url = f"{BASE_URL}/task/{task_id}"
    start_time = time.time()
    
    while time.time() - start_time < 180:
        response = requests.get(status_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            time.sleep(2)
            continue
        
        result = response.json()
        
        if result.get('code') != 0:
            time.sleep(2)
            continue
        
        data = result.get('data', {})
        status = data.get('status')
        progress = data.get('progress', 0)
        
        print(f"📊 Statut: {status}, Progression: {progress}%")
        
        if status == 'success':
            output = data.get('output', {})
            model_url = output.get('model')
            
            if model_url:
                print(f"🎯 URL GLB: {model_url}")
                return model_url, None
            else:
                return None, "Aucune URL de modèle trouvée"
        
        elif status == 'failed':
            return None, "Génération échouée"
        
        time.sleep(2)
    
    return None, "Délai dépassé"

def download_glb(url, output_path):
    """Télécharge le fichier GLB"""
    try:
        response = requests.get(url, stream=True, timeout=60)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True, f"✅ Fichier sauvegardé: {os.path.basename(output_path)}"
        else:
            return False, f"Erreur HTTP {response.status_code}"
    except Exception as e:
        return False, f"Erreur: {str(e)}"

# -----------------------------
# CRÉATION DU VISUALISEUR 3D LOCAL
# -----------------------------

def create_local_3d_viewer(model_path):
    """Crée un visualiseur 3D complet qui tourne localement"""
    
    # Lire le fichier GLB et le convertir en base64 pour l'embed
    with open(model_path, 'rb') as f:
        glb_data = base64.b64encode(f.read()).decode('utf-8')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Visualisation 3D - Villa</title>
        <style>
            body {{ 
                margin: 0; 
                overflow: hidden; 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            #info {{
                position: absolute;
                top: 20px;
                left: 20px;
                background: rgba(0,0,0,0.7);
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                z-index: 100;
                pointer-events: none;
                backdrop-filter: blur(5px);
            }}
            #controls {{
                position: absolute;
                bottom: 20px;
                left: 20px;
                background: rgba(0,0,0,0.7);
                color: white;
                padding: 8px 15px;
                border-radius: 8px;
                font-size: 12px;
                z-index: 100;
                pointer-events: none;
                backdrop-filter: blur(5px);
            }}
            .instruction {{
                position: absolute;
                bottom: 20px;
                right: 20px;
                background: rgba(0,0,0,0.7);
                color: white;
                padding: 8px 15px;
                border-radius: 8px;
                font-size: 12px;
                z-index: 100;
                pointer-events: none;
                backdrop-filter: blur(5px);
            }}
        </style>
    </head>
    <body>
        <div id="info">
            <h2>🏠 Villa 3D</h2>
            <p>Modèle généré par Tripo3D AI</p>
        </div>
        <div id="controls">
            🖱️ Souris: Rotation | 🖱️ Clic droit: Pan | 📜 Molette: Zoom
        </div>
        <div class="instruction">
            ✨ Rendu en temps réel | 🌟 Qualité HD
        </div>

        <script type="importmap">
            {{
                "imports": {{
                    "three": "https://unpkg.com/three@0.128.0/build/three.module.js",
                    "three/addons/": "https://unpkg.com/three@0.128.0/examples/jsm/"
                }}
            }}
        </script>

        <script type="module">
            import * as THREE from 'three';
            import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
            import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';
            
            // Scene
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0x0a0a2a);
            scene.fog = new THREE.FogExp2(0x0a0a2a, 0.008);
            
            // Camera
            const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(3, 2, 4);
            camera.lookAt(0, 0, 0);
            
            // Renderer
            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            renderer.setPixelRatio(window.devicePixelRatio);
            document.body.appendChild(renderer.domElement);
            
            // Controls
            const controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.rotateSpeed = 1.5;
            controls.zoomSpeed = 1.2;
            controls.panSpeed = 0.8;
            controls.enableZoom = true;
            controls.enablePan = true;
            controls.target.set(0, 0.5, 0);
            
            // Lights
            const ambientLight = new THREE.AmbientLight(0x404060);
            scene.add(ambientLight);
            
            const mainLight = new THREE.DirectionalLight(0xfff5e6, 1.2);
            mainLight.position.set(5, 10, 3);
            mainLight.castShadow = true;
            mainLight.receiveShadow = true;
            mainLight.shadow.mapSize.width = 1024;
            mainLight.shadow.mapSize.height = 1024;
            scene.add(mainLight);
            
            const fillLight = new THREE.PointLight(0x4466cc, 0.4);
            fillLight.position.set(-2, 2, 4);
            scene.add(fillLight);
            
            const backLight = new THREE.PointLight(0xffaa66, 0.3);
            backLight.position.set(0, 2, -3);
            scene.add(backLight);
            
            // Helper grid
            const gridHelper = new THREE.GridHelper(10, 20, 0x88aaff, 0x335588);
            gridHelper.position.y = -0.8;
            gridHelper.material.transparent = true;
            gridHelper.material.opacity = 0.4;
            scene.add(gridHelper);
            
            // Load model from base64
            const loader = new GLTFLoader();
            const glbData = 'data:model/gltf-binary;base64,{glb_data}';
            
            loader.load(glbData, (gltf) => {{
                const model = gltf.scene;
                model.traverse((node) => {{
                    if (node.isMesh) {{
                        node.castShadow = true;
                        node.receiveShadow = true;
                    }}
                }});
                scene.add(model);
                
                // Auto-rotate animation (optional)
                let time = 0;
                function animate() {{
                    requestAnimationFrame(animate);
                    time += 0.002;
                    controls.update();
                    renderer.render(scene, camera);
                }}
                animate();
            }}, undefined, (error) => {{
                console.error('Erreur chargement:', error);
                document.getElementById('info').innerHTML = '<h2>❌ Erreur</h2><p>Impossible de charger le modèle 3D</p>';
            }});
        </script>
    </body>
    </html>
    """
    
    return html_content

# -----------------------------
# FONCTIONS PRINCIPALES
# -----------------------------

def generate_villa_2d(input_image):
    global generated_image
    
    if input_image is None:
        return None, "❌ Chargez une image", None
    
    input_image = input_image.resize((512, 512))
    
    prompt = "modern luxury villa, architectural photography, photorealistic, 8K"
    negative_prompt = "cartoon, anime, sketch, low quality"
    
    try:
        result = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=input_image,
            strength=0.65,
            num_inference_steps=40,
            guidance_scale=7.5
        ).images[0]
        
        generated_image = result
        return result, "✅ Villa 2D générée! Cliquez sur 'Convertir en 3D'", None
        
    except Exception as e:
        return None, f"❌ Erreur: {str(e)}", None

def convert_to_3d_local():
    """Convertit en 3D et affiche localement"""
    global generated_image, current_model_file
    
    if generated_image is None:
        return "❌ Générez d'abord la villa 2D", None, None, "<div style='text-align:center;padding:50px;'>⚠️ Générez d'abord la villa 2D</div>"
    
    temp_path = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    generated_image.save(temp_path)
    
    messages = []
    
    def log(msg):
        messages.append(msg)
        print(msg)
    
    try:
        log("📤 Upload...")
        token, error = upload_to_tripo3d(temp_path)
        if error:
            return f"❌ {error}", None, None, None
        log("✅ Upload OK")
        
        log("🔄 Création tâche...")
        task_id, error = create_task(token)
        if error:
            return f"❌ {error}", None, None, None
        log(f"✅ Tâche: {task_id}")
        
        log("⏳ Génération 3D (1-2 min)...")
        model_url, error = wait_and_get_model(task_id)
        
        if error:
            return f"❌ {error}", None, None, None
        
        log("📥 Téléchargement du modèle...")
        model_filename = f"villa_3d_{datetime.now().strftime('%Y%m%d_%H%M%S')}.glb"
        model_path = os.path.join(os.getcwd(), model_filename)
        
        success, download_msg = download_glb(model_url, model_path)
        
        if not success:
            return f"❌ {download_msg}", None, None, None
        
        current_model_file = model_path
        log(f"✅ {download_msg}")
        
        # Créer le visualiseur local
        log("🎮 Création du visualiseur 3D...")
        viewer_html = create_local_3d_viewer(model_path)
        
        final_message = "\n".join(messages) + f"\n\n✅ Modèle 3D prêt!\n📁 {model_filename}"
        
        return final_message, model_path, model_url, viewer_html
        
    except Exception as e:
        return f"❌ Exception: {str(e)}", None, None, None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# -----------------------------
# INTERFACE GRADIO
# -----------------------------
with gr.Blocks(theme=gr.themes.Soft(), title="Villa 3D Generator") as demo:
    
    gr.Markdown("""
    # 🏠 **Générateur Villa 2D → 3D**
    
    ### Visualisation 3D locale - Sans erreur 9008 !
    """)
    
    with gr.Row():
        with gr.Column():
            input_image = gr.Image(type="pil", label="📷 Image d'entrée", height=250)
            generate_2d_btn = gr.Button("🎨 1. Générer villa 2D", variant="primary", size="lg")
            output_2d = gr.Image(label="Villa 2D", height=200)
            status_2d = gr.Textbox(label="Statut", interactive=False)
        
        with gr.Column():
            convert_btn = gr.Button("✨ 2. Convertir en 3D", variant="secondary", size="lg")
            status_3d = gr.Textbox(label="Progression", interactive=False, lines=6)
    
    with gr.Row():
        with gr.Column(scale=2):
            output_3d = gr.HTML(label="🎮 Visualisation 3D Interactive", value="<div style='text-align:center;padding:100px;background:#f5f5f5;border-radius:12px;'>⏳ Cliquez sur 'Convertir en 3D'</div>")
        
        with gr.Column(scale=1):
            file_output = gr.File(label="📥 Télécharger le modèle GLB")
            link_output = gr.Textbox(label="🔗 Lien cloud (5min)", interactive=False)
    
    generate_2d_btn.click(
        fn=generate_villa_2d,
        inputs=input_image,
        outputs=[output_2d, status_2d, output_3d]
    )
    
    convert_btn.click(
        fn=convert_to_3d_local,
        inputs=None,
        outputs=[status_3d, file_output, link_output, output_3d]
    )
    
    gr.Markdown("""
    ---
    ### ✅ **Ce qui change avec cette version**
    
    - **Plus d'erreur 9008** : La visualisation est locale, pas besoin de studio.tripo3d.ai
    - **Modèle téléchargé** : Le fichier GLB est sauvegardé sur votre ordinateur
    - **Visualisation directe** : Le modèle 3D s'affiche dans l'interface Gradio
    - **Téléchargement possible** : Vous pouvez récupérer le fichier GLB
    
    ### 📝 **Comment utiliser**
    
    1. Chargez une image de terrain
    2. Générez la villa 2D
    3. Convertissez en 3D (1-2 minutes)
    4. Visualisez directement dans la page
    5. Téléchargez le fichier GLB pour Blender/Unity
    """)

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║              🏠 GÉNÉRATEUR VILLA 3D - VISUALISATION LOCALE           ║
    ╠═══════════════════════════════════════════════════════════════════════╣
    ║  📍 http://127.0.0.1:7860                                            ║
    ║  🎨 Génération 2D: ✅ Active                                         ║
    ║  🎮 Visualisation 3D: ✅ Locale (Three.js)                           ║
    ║  ❌ Erreur 9008: Éliminée                                            ║
    ╚═══════════════════════════════════════════════════════════════════════╝
    """)
    demo.launch(share=False, debug=True)