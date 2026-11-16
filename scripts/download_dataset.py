import os
import sys
import io
import time
import zipfile
import urllib.request
import pyarrow.parquet as pq
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
os.makedirs(DATASET_DIR, exist_ok=True)

TARGET_PER_CLASS = 100

def log(msg):
    print(f"[{time.strftime('%X')}] {msg}", flush=True)

def safe_download(url, dest_path):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, 'wb') as out:
        out.write(resp.read())

# ---------------------------------------------------------
# 1. DOWNLOAD RICE DATASET FROM PROJECT-AGML PARQUET
# ---------------------------------------------------------
def prepare_rice():
    log("Preparing Rice dataset...")
    rice_url = "https://huggingface.co/datasets/Project-AgML/rice_leaf_disease_classification_india/resolve/main/data/train-00000-of-00001.parquet"
    parquet_path = os.path.join(DATASET_DIR, "rice_temp.parquet")
    if not os.path.exists(parquet_path):
        log(f"Downloading Rice parquet from {rice_url}...")
        safe_download(rice_url, parquet_path)
    
    table = pq.read_table(parquet_path)
    labels = table['label'].to_pylist()
    images = table['image'].to_pylist()
    
    # 0: Bacterialblight, 1: Blast, 2: Brownspot, 3: Tungro
    class_map = {
        0: "Rice___Bacterial_Blight",
        1: "Rice___Blast",
        2: "Rice___Brown_Spot",
        3: "Rice___Tungro"
    }
    
    counts = {v: 0 for v in class_map.values()}
    for lbl, img_data in zip(labels, images):
        cname = class_map.get(lbl)
        if not cname or counts[cname] >= TARGET_PER_CLASS:
            continue
        cdir = os.path.join(DATASET_DIR, cname)
        os.makedirs(cdir, exist_ok=True)
        img_bytes = img_data['bytes']
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_path = os.path.join(cdir, f"rice_{counts[cname]:03d}.jpg")
        img.save(img_path, "JPEG", quality=90)
        counts[cname] += 1
    
    log(f"Rice dataset prepared: {counts}")
    if os.path.exists(parquet_path):
        os.remove(parquet_path)

# ---------------------------------------------------------
# 2. DOWNLOAD COTTON DATASET FROM PROJECT-AGML PARQUET
# ---------------------------------------------------------
def prepare_cotton():
    log("Preparing Cotton dataset...")
    cotton_url = "https://huggingface.co/datasets/Project-AgML/cotton_leaf_disease_classification/resolve/main/raw/train-00000-of-00001.parquet"
    parquet_path = os.path.join(DATASET_DIR, "cotton_temp.parquet")
    if not os.path.exists(parquet_path):
        log(f"Downloading Cotton parquet from {cotton_url}...")
        safe_download(cotton_url, parquet_path)
        
    table = pq.read_table(parquet_path)
    labels = table['label'].to_pylist()
    images = table['image'].to_pylist()
    
    # 0: Alternaria_Leaf, 1: Bacterial_Blight, 2: Fusarium_Wilt, 3: Healthy_Leaf, 4: Verticillium_Wilt
    class_map = {
        0: "Cotton___Alternaria_Leaf_Spot",
        1: "Cotton___Bacterial_Blight",
        2: "Cotton___Fusarium_Wilt",
        3: "Cotton___Healthy"
    }
    
    counts = {v: 0 for v in class_map.values()}
    for lbl, img_data in zip(labels, images):
        cname = class_map.get(lbl)
        if not cname or counts[cname] >= TARGET_PER_CLASS:
            continue
        cdir = os.path.join(DATASET_DIR, cname)
        os.makedirs(cdir, exist_ok=True)
        img_bytes = img_data['bytes']
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_path = os.path.join(cdir, f"cotton_{counts[cname]:03d}.jpg")
        img.save(img_path, "JPEG", quality=90)
        counts[cname] += 1
        
    log(f"Cotton dataset prepared: {counts}")
    if os.path.exists(parquet_path):
        os.remove(parquet_path)

# ---------------------------------------------------------
# 3. DOWNLOAD WHEAT DATASET FROM AADIUM REPO
# ---------------------------------------------------------
def prepare_wheat():
    log("Preparing Wheat dataset...")
    base_raw = "https://raw.githubusercontent.com/aadium/wheat-disease-detection/master/cropDiseaseDataset"
    
    class_map = {
        "Wheat_Leaf_Rust": "Wheat___Leaf_Rust",
        "Wheat_Loose_Smut": "Wheat___Loose_Smut",
        "Wheat_crown_root_rot": "Wheat___Crown_Root_Rot",
        "Wheat_healthy": "Wheat___Healthy"
    }
    
    import json
    for gh_folder, target_class in class_map.items():
        cdir = os.path.join(DATASET_DIR, target_class)
        os.makedirs(cdir, exist_ok=True)
        api_url = f"https://api.github.com/repos/aadium/wheat-disease-detection/contents/cropDiseaseDataset/{gh_folder}"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            files_list = json.loads(resp.read().decode())
        
        count = 0
        for item in files_list:
            if count >= TARGET_PER_CLASS:
                break
            fname = item['name']
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            download_url = item['download_url']
            dest_img = os.path.join(cdir, f"wheat_{count:03d}.jpg")
            try:
                safe_download(download_url, dest_img)
                # verify image
                with Image.open(dest_img) as im:
                    im.verify()
                count += 1
            except Exception as e:
                if os.path.exists(dest_img):
                    os.remove(dest_img)
        log(f"Wheat class {target_class}: {count} images saved")

# ---------------------------------------------------------
# 4. DOWNLOAD SOYBEAN DATASET FROM STARLY REPO
# ---------------------------------------------------------
def prepare_soybean():
    log("Preparing Soybean dataset...")
    # starly repo has Soybean_downy_train.zip, Soybean_rust_train.zip, Soybean_healthy_train.zip
    zips = {
        "Soybean___Downy_Mildew": "https://raw.githubusercontent.com/starly/Soybean_Images_MachineLearning/master/Soybean_downy_train.zip",
        "Soybean___Rust": "https://raw.githubusercontent.com/starly/Soybean_Images_MachineLearning/master/Soybean_rust_train.zip",
        "Soybean___Healthy": "https://raw.githubusercontent.com/starly/Soybean_Images_MachineLearning/master/Soybean_healthy_train.zip"
    }
    
    for cname, zurl in zips.items():
        cdir = os.path.join(DATASET_DIR, cname)
        os.makedirs(cdir, exist_ok=True)
        zpath = os.path.join(DATASET_DIR, f"{cname}.zip")
        log(f"Downloading {cname} from {zurl}...")
        safe_download(zurl, zpath)
        with zipfile.ZipFile(zpath, 'r') as zf:
            count = 0
            for name in zf.namelist():
                if count >= TARGET_PER_CLASS:
                    break
                if name.lower().endswith(('.jpg', '.jpeg', '.png')) and not name.startswith('__MACOSX'):
                    data = zf.read(name)
                    try:
                        img = Image.open(io.BytesIO(data)).convert("RGB")
                        img.save(os.path.join(cdir, f"soybean_{count:03d}.jpg"), "JPEG", quality=90)
                        count += 1
                    except Exception:
                        pass
        if os.path.exists(zpath):
            os.remove(zpath)
        log(f"Soybean class {cname}: {count} images saved")

# ---------------------------------------------------------
# 5. DOWNLOAD TOMATO & POTATO FROM PLANTVILLAGE
# ---------------------------------------------------------
def prepare_plantvillage():
    log("Preparing Tomato and Potato from PlantVillage...")
    import json
    
    # Selected classes for Potato and Tomato
    pv_classes = {
        "Potato___Early_blight": "Potato___Early_Blight",
        "Potato___Late_blight": "Potato___Late_Blight",
        "Potato___healthy": "Potato___Healthy",
        "Tomato___Bacterial_spot": "Tomato___Bacterial_Spot",
        "Tomato___Early_blight": "Tomato___Early_Blight",
        "Tomato___Late_blight": "Tomato___Late_Blight",
        "Tomato___Leaf_Mold": "Tomato___Leaf_Mold",
        "Tomato___Septoria_leaf_spot": "Tomato___Septoria_Leaf_Spot",
        "Tomato___Target_Spot": "Tomato___Target_Spot",
        "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Tomato___Yellow_Leaf_Curl_Virus",
        "Tomato___Tomato_mosaic_virus": "Tomato___Mosaic_Virus",
        "Tomato___healthy": "Tomato___Healthy"
    }
    
    for gh_folder, target_name in pv_classes.items():
        cdir = os.path.join(DATASET_DIR, target_name)
        os.makedirs(cdir, exist_ok=True)
        api_url = f"https://api.github.com/repos/spMohanty/PlantVillage-Dataset/contents/raw/color/{urllib.parse.quote(gh_folder)}"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                files_list = json.loads(resp.read().decode())
        except Exception as e:
            log(f"Error fetching directory list for {gh_folder}: {e}")
            continue
            
        count = 0
        for item in files_list:
            if count >= TARGET_PER_CLASS:
                break
            fname = item['name']
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            download_url = item['download_url']
            dest_img = os.path.join(cdir, f"{target_name.lower()}_{count:03d}.jpg")
            try:
                safe_download(download_url, dest_img)
                with Image.open(dest_img) as im:
                    im.verify()
                count += 1
            except Exception:
                if os.path.exists(dest_img):
                    os.remove(dest_img)
        log(f"{target_name}: {count} images saved")

if __name__ == "__main__":
    import urllib.parse
    log("=== Starting Dataset Preparation for 6 Crops ===")
    prepare_rice()
    prepare_cotton()
    prepare_wheat()
    prepare_soybean()
    prepare_plantvillage()
    
    log("=== Verification & Summary ===")
    all_classes = sorted(os.listdir(DATASET_DIR))
    total_imgs = 0
    print("\nCLASS-WISE IMAGE COUNTS:")
    for c in all_classes:
        p = os.path.join(DATASET_DIR, c)
        if os.path.isdir(p):
            n = len([f for f in os.listdir(p) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            total_imgs += n
            print(f"  {c:<35}: {n} images")
    print(f"\nTOTAL CLASSES: {len(all_classes)}, TOTAL IMAGES: {total_imgs}")
