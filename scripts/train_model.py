import os
import sys
import json
import time
import shutil
import random
import numpy as np
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import tensorflow as tf
from tensorflow.keras import layers, models, callbacks
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODELS_DIR = os.path.join(BASE_DIR, "backend", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 12


def log(msg):
    print(f"[{time.strftime('%X')}] {msg}", flush=True)


# -------------------------------------------------------------
# 1. PREPARE STRATIFIED SPLITS (70% TRAIN, 15% VAL, 15% TEST)
# -------------------------------------------------------------
def create_dataset_splits():
    log("Scanning dataset directory and creating splits...")
    classes = sorted([d for d in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, d))])

    train_paths, train_labels = [], []
    val_paths, val_labels = [], []
    test_paths, test_labels = [], []

    class_to_idx = {c: i for i, c in enumerate(classes)}

    for cname in classes:
        cdir = os.path.join(DATASET_DIR, cname)
        img_files = sorted(
            [os.path.join(cdir, f) for f in os.listdir(cdir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        random.shuffle(img_files)

        n_total = len(img_files)
        n_train = int(n_total * 0.70)
        n_val = int(n_total * 0.15)
        # remainder for test

        train_set = img_files[:n_train]
        val_set = img_files[n_train:n_train + n_val]
        test_set = img_files[n_train + n_val:]

        c_idx = class_to_idx[cname]

        train_paths.extend(train_set)
        train_labels.extend([c_idx] * len(train_set))

        val_paths.extend(val_set)
        val_labels.extend([c_idx] * len(val_set))

        test_paths.extend(test_set)
        test_labels.extend([c_idx] * len(test_set))

    log(f"Dataset split summary:")
    log(f"  Total classes   : {len(classes)}")
    log(f"  Training set    : {len(train_paths)} images")
    log(f"  Validation set  : {len(val_paths)} images")
    log(f"  Test set        : {len(test_paths)} images")

    return classes, class_to_idx, (train_paths, train_labels), (val_paths, val_labels), (test_paths, test_labels)


# -------------------------------------------------------------
# 2. TF.DATA PIPELINE WITH PREPROCESSING AND AUGMENTATION
# -------------------------------------------------------------
def load_and_preprocess_image(path, label, num_classes):
    img_raw = tf.io.read_file(path)
    img = tf.image.decode_jpeg(img_raw, channels=3)
    img = tf.image.resize(img, IMAGE_SIZE)
    img = preprocess_input(img)  # MobileNetV2 normalizes to [-1, 1]
    one_hot = tf.one_hot(label, depth=num_classes)
    return img, one_hot


def create_tf_dataset(paths, labels, num_classes, is_training=False):
    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
    if is_training:
        dataset = dataset.shuffle(buffer_size=len(paths), seed=SEED)
    dataset = dataset.map(lambda p, l: load_and_preprocess_image(p, l, num_classes),
                          num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.batch(BATCH_SIZE)
    if is_training:
        dataset = dataset.prefetch(tf.data.AUTOTUNE)
    return dataset


# -------------------------------------------------------------
# 3. BUILD MOBILENETV2 MODEL ARCHITECTURE
# -------------------------------------------------------------
def build_model(num_classes):
    log("Building MobileNetV2 model architecture...")
    base_model = MobileNetV2(input_shape=(224, 224, 3), include_top=False, weights='imagenet')

    # Freeze initial base layers to stabilize transfer learning
    base_model.trainable = False

    inputs = tf.keras.Input(shape=(224, 224, 3))

    # Data Augmentation layer directly in model
    x = layers.RandomFlip("horizontal_and_vertical", seed=SEED)(inputs)
    x = layers.RandomRotation(0.10, seed=SEED)(x)
    x = layers.RandomZoom(0.10, seed=SEED)(x)

    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.35)(x)
    x = layers.Dense(256, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(1e-4))(x)
    x = layers.Dropout(0.25)(x)
    outputs = layers.Dense(num_classes, activation='softmax', dtype='float32')(x)

    model = models.Model(inputs, outputs, name="KisanSmart_MobileNetV2")
    return model, base_model


# -------------------------------------------------------------
# 4. METADATA DEFINITIONS
# -------------------------------------------------------------
METADATA = {
    "Wheat___Leaf_Rust": {
        "crop": "Wheat", "local_crop": "Gehu", "disease": "Leaf Rust", "local_disease": "Gehu ka Bhura Rataua",
        "severity": "High", "severity_pct": 85, "bachne_ka_chance": 50,
        "symptoms": "Chhote, gol se andakar narangi-bhure rang ke chhaley (pustules) patti ki upri satah par, patti ka peela padna aur sookhna.",
        "solution": "Propiconazole 25% EC @ 1 ml/L ya Tebuconazole 25.9% EC @ 1.25 ml/L ka chhidkaw karein.",
        "precaution": "Pratirodhi kismein jaise HD-2967, PBW-550 boyein. Der se buayi na karein aur nitrogen ka santulit prayog karein."
    },
    "Wheat___Loose_Smut": {
        "crop": "Wheat", "local_crop": "Gehu", "disease": "Loose Smut", "local_disease": "Gehu ka Khulla Kandooa",
        "severity": "High", "severity_pct": 80, "bachne_ka_chance": 55,
        "symptoms": "Baaliyon ki jagah kala powdery dhuen jaisa churna banna, baali ke dane puri tarah nasht ho jana.",
        "solution": "Bimaar baaliyon ko polythene bag se dhak kar ukhad lein aur khet se door jalayein.",
        "precaution": "Beej ko boyi se pehle Carboxin 37.5% + Thiram 37.5% DS @ 2.5 g/kg se beej sanshodhan karein."
    },
    "Wheat___Crown_Root_Rot": {
        "crop": "Wheat", "local_crop": "Gehu", "disease": "Crown and Root Rot", "local_disease": "Gehu ki Jad Galan",
        "severity": "Medium", "severity_pct": 65, "bachne_ka_chance": 70,
        "symptoms": "Taane ke nichle hisse aur jado par bhure dhabbe, paudha peela padna aur khokhi baaliyan (whiteheads) banna.",
        "solution": "Jadon ke paas Carbendazim 50% WP @ 2 g/L ya Trichoderma viride @ 5 g/L ka drenching karein.",
        "precaution": "Fasal chakr apnayein, gehri boyi se bachein aur khet mein paani rukne na dein."
    },
    "Wheat___Healthy": {
        "crop": "Wheat", "local_crop": "Gehu", "disease": "Healthy", "local_disease": "Swasth Gehu",
        "severity": "Low", "severity_pct": 0, "bachne_ka_chance": 100,
        "symptoms": "Pattiyan hari, chamakdar aur shuddh hain. Koi fafundi ya keet ke lakshan nahi hain.",
        "solution": "Kisi dawai ki zaroorat nahi hai. Samay par sinchai aur urea ki santulit matra dein.",
        "precaution": "Niyamit khet ki dekhbhal karein aur NPK (120:60:40) santulan banaye rakhein."
    },
    "Rice___Bacterial_Blight": {
        "crop": "Rice", "local_crop": "Dhan", "disease": "Bacterial Blight", "local_disease": "Dhan ka Jivanu Jhulsa",
        "severity": "High", "severity_pct": 85, "bachne_ka_chance": 50,
        "symptoms": "Patti ke kinaroon se shuru hone wale peele-safed dhabbe jo lehredar bante hain, subah patti par baarik boondein aana.",
        "solution": "Copper Oxychloride 50% WP @ 2.5 g/L + Streptocycline @ 0.06 g/L (6g/100L) ka ghol chhidkein.",
        "precaution": "Khet se atirikt paani nikalein, bimaar khet ka paani doosre khet mein na jaane dein, nitrogen kam karein."
    },
    "Rice___Blast": {
        "crop": "Rice", "local_crop": "Dhan", "disease": "Rice Blast", "local_disease": "Dhan ka Blast / Jhulsa",
        "severity": "High", "severity_pct": 90, "bachne_ka_chance": 45,
        "symptoms": "Aankh ya naav ke aakar ke dhabbe jinke kinaray bhure aur beech mein dhusar (grey) hote hain.",
        "solution": "Tricyclazole 75% WP @ 0.6 g/L ya Isoprothiolane 40% EC @ 1.5 ml/L ka turant chhidkaw karein.",
        "precaution": "Urea ki zyada khuraak na dein, raat mein nami zyada hone par saavdhani bartein."
    },
    "Rice___Brown_Spot": {
        "crop": "Rice", "local_crop": "Dhan", "disease": "Brown Spot", "local_disease": "Dhan ka Bhura Dhabba",
        "severity": "Medium", "severity_pct": 60, "bachne_ka_chance": 75,
        "symptoms": "Patti par til ke daane jaise chhote gol/andakar bhure dhabbe jinke charo taraf peeli ring hoti hai.",
        "solution": "Mancozeb 75% WP @ 2 g/L ya Hexaconazole 5% SC @ 2 ml/L ka chhidkaw karein.",
        "precaution": "Mitti mein potash aur zinc ki kami na hone dein. Niyamit roop se santulit khad dein."
    },
    "Rice___Tungro": {
        "crop": "Rice", "local_crop": "Dhan", "disease": "Tungro Disease", "local_disease": "Dhan ka Tungro Rog",
        "severity": "High", "severity_pct": 85, "bachne_ka_chance": 50,
        "symptoms": "Paudha bauna reh jana, pattiyaan peeli ya narangi rang ki ho jana, phoot (tillering) ruk jana.",
        "solution": "Hare tiddi (Green Leafhopper) ke niyantran ke liye Imidacloprid 17.8% SL @ 0.3 ml/L chhidkein.",
        "precaution": "Khet ke aas-paas se ghaas-phoos aur purani khunti hata dein, aage ki boyi sabke saath karein."
    },
    "Tomato___Bacterial_Spot": {
        "crop": "Tomato", "local_crop": "Tamatar", "disease": "Bacterial Spot",
        "local_disease": "Tamatar ka Jivanu Dhabba",
        "severity": "High", "severity_pct": 75, "bachne_ka_chance": 60,
        "symptoms": "Pattiyon par chhote kaale-bhure chipchipaahat bhare dhabbe jinpar peeli aabhaar hoti hai, patti jhadna.",
        "solution": "Copper Hydroxide 77% WP @ 2 g/L + Mancozeb @ 2 g/L milakar chhidkaw karein.",
        "precaution": "Fawware (overhead) sinchai se bachein, katayi-chhantayi ke auzar saaf rakhein."
    },
    "Tomato___Early_Blight": {
        "crop": "Tomato", "local_crop": "Tamatar", "disease": "Early Blight",
        "local_disease": "Tamatar ka Ageti Jhulsa",
        "severity": "Medium", "severity_pct": 70, "bachne_ka_chance": 70,
        "symptoms": "Purani nichli pattiyon par gol chakradar (concentric target) dhabbe, patti ka peela hokar sukhna.",
        "solution": "Chlorothalonil 75% WP @ 2 g/L ya Azoxystrobin 23% SC @ 1 ml/L ka chhidkaw karein.",
        "precaution": "Paudhe ko dande ka sahara (staking) dein taaki pattiyan zameen se na chhuwein, mulch lagayein."
    },
    "Tomato___Late_Blight": {
        "crop": "Tomato", "local_crop": "Tamatar", "disease": "Late Blight",
        "local_disease": "Tamatar ka Pachheti Jhulsa",
        "severity": "High", "severity_pct": 95, "bachne_ka_chance": 40,
        "symptoms": "Bade aniyamit paani jaise geelapan liye dhabbe, patti ke niche safed rui jaisi fafundi, paudha tezi se jhulashna.",
        "solution": "Metalaxyl 8% + Mancozeb 64% WP @ 2.5 g/L ya Cymoxanil + Mancozeb @ 2 g/L turant chhidkein.",
        "precaution": "Thand aur nami ke mausam mein niyamit jaanch karein, bimaar paudhe ukhad kar door phenk dein."
    },
    "Tomato___Leaf_Mold": {
        "crop": "Tomato", "local_crop": "Tamatar", "disease": "Leaf Mold", "local_disease": "Tamatar ka Patti Fafund",
        "severity": "Medium", "severity_pct": 60, "bachne_ka_chance": 75,
        "symptoms": "Patti ki upri satah par peele dhabbe aur nichli satah par zaituni-hare/bhoore makhmali fafund.",
        "solution": "Difenoconazole 25% EC @ 1 ml/L ya Copper Oxychloride @ 2.5 g/L ka chhidkaw karein.",
        "precaution": "Polyhouse ya khet mein hawa ka aawagaman behtar karein, nami 85% se kam rakhein."
    },
    "Tomato___Mosaic_Virus": {
        "crop": "Tomato", "local_crop": "Tamatar", "disease": "Mosaic Virus", "local_disease": "Tamatar ka Mosaic Rog",
        "severity": "High", "severity_pct": 85, "bachne_ka_chance": 45,
        "symptoms": "Pattiyon par hare aur peele rang ke chitey (mottling), pattiyaan sikudna aur aenthan aana.",
        "solution": "Virus ki seedhi dawai nahi hoti. Bimaar paudhe ukhad kar jala dein. Keet niyantran ke liye neem oil chhidkein.",
        "precaution": "Haath saaf karke hi doosre paudhon ko chhuwein, tambaku ka sevan karke khet mein na jayein."
    },
    "Tomato___Septoria_Leaf_Spot": {
        "crop": "Tomato", "local_crop": "Tamatar", "disease": "Septoria Leaf Spot",
        "local_disease": "Tamatar ka Septoria Dhabba",
        "severity": "Medium", "severity_pct": 65, "bachne_ka_chance": 70,
        "symptoms": "Chhote gol dhabbe jinke kinaray kaale-bhure aur beech ka hissa dhusar hota hai, baarik kaale bindu.",
        "solution": "Mancozeb 75% WP @ 2.5 g/L ya Chlorothalonil @ 2 g/L ka chhidkaw karein.",
        "precaution": "Nichli bimaar pattiyan tor kar door phenkein, patti par paani na padne dein."
    },
    "Tomato___Target_Spot": {
        "crop": "Tomato", "local_crop": "Tamatar", "disease": "Target Spot",
        "local_disease": "Tamatar ka Target Dhabba",
        "severity": "Medium", "severity_pct": 65, "bachne_ka_chance": 70,
        "symptoms": "Bhure rang ke gol dhabbe jisme kinaroon par lakshya (target) jaise ghere bante hain.",
        "solution": "Pyraclostrobin 20% WG @ 1 g/L ya Azoxystrobin @ 1 ml/L ka chhidkaw karein.",
        "precaution": "Paudhon ke beech uchit doori rakhein, khet mein hawa aur dhoop aane dein."
    },
    "Tomato___Yellow_Leaf_Curl_Virus": {
        "crop": "Tomato", "local_crop": "Tamatar", "disease": "Yellow Leaf Curl Virus",
        "local_disease": "Tamatar ka Pili Patti Murjhana",
        "severity": "High", "severity_pct": 90, "bachne_ka_chance": 40,
        "symptoms": "Pattiyon ka upar ki taraf pyale jaisa mudna, patti ka peela padna, paudha thithurna aur phool girna.",
        "solution": "Safed makkhi (Whitefly) ke niyantran ke liye Dinotefuran 20% SG @ 0.5 g/L ya Acetamiprid 20% SP @ 0.4 g/L chhidkein.",
        "precaution": "Peele chipchipe card (Yellow sticky traps) 15-20 prati acre lagayein, 50-mesh jali ka upyog karein."
    },
    "Tomato___Healthy": {
        "crop": "Tomato", "local_crop": "Tamatar", "disease": "Healthy", "local_disease": "Swasth Tamatar",
        "severity": "Low", "severity_pct": 0, "bachne_ka_chance": 100,
        "symptoms": "Pattiyan swasth, hari aur sakriya hain. Paudha vikasit aur rog-mukt hai.",
        "solution": "Kisi chemical spray ki zaroorat nahi hai. Samay par pani aur kheti ki dekhbhal jaari rakhein.",
        "precaution": "Samay par compost aur 19:19:19 NPK ki matra dein."
    },
    "Potato___Early_Blight": {
        "crop": "Potato", "local_crop": "Aalu", "disease": "Early Blight", "local_disease": "Aalu ka Ageti Jhulsa",
        "severity": "Medium", "severity_pct": 65, "bachne_ka_chance": 70,
        "symptoms": "Pattiyon par kaale-bhure chhalle numaa dhabbe, patti sukh kar papdi jaisi banna.",
        "solution": "Mancozeb 75% WP @ 2.5 g/L ya Propineb 70% WP @ 2 g/L ka chhidkaw karein.",
        "precaution": "Fasal ko nitrogen aur potash ka santulit poshan dein, sham ke samay sinchai se bachein."
    },
    "Potato___Late_Blight": {
        "crop": "Potato", "local_crop": "Aalu", "disease": "Late Blight", "local_disease": "Aalu ka Pachheti Jhulsa",
        "severity": "High", "severity_pct": 95, "bachne_ka_chance": 35,
        "symptoms": "Geelapan liye bade kaale dhabbe, patti ke niche safed fafundi, badbu aana aur 3-4 din me fasal jhulashna.",
        "solution": "Cymoxanil 8% + Mancozeb 64% WP @ 2.5 g/L ya Dimethomorph 50% WP @ 1 g/L turant chhidkein.",
        "precaution": "Bimari aane ki sambhavna par pehle hi Mancozeb ka chhidkaw karein, mitti chadha kar aalu ko dhakein."
    },
    "Potato___Healthy": {
        "crop": "Potato", "local_crop": "Aalu", "disease": "Healthy", "local_disease": "Swasth Aalu",
        "severity": "Low", "severity_pct": 0, "bachne_ka_chance": 100,
        "symptoms": "Swasth hari pattiyaan, koi dhabba ya jhulsaahat nahi hai.",
        "solution": "Chemical spray ki aavashyakta nahi hai. Routine sinchai banaye rakhein.",
        "precaution": "Khet mein pani na theharne dein, niyamit roop se jaanch karte rahein."
    },
    "Cotton___Alternaria_Leaf_Spot": {
        "crop": "Cotton", "local_crop": "Kapas", "disease": "Alternaria Leaf Spot",
        "local_disease": "Kapas ka Alternaria Dhabba",
        "severity": "Medium", "severity_pct": 65, "bachne_ka_chance": 70,
        "symptoms": "Pattiyon par gol bhure-baingani dhabbe jinke beech concentric rings banti hain, beech ka hissa gir jana.",
        "solution": "Propiconazole 25% EC @ 1 ml/L ya Pyraclostrobin 20% WG @ 1 g/L ka chhidkaw karein.",
        "precaution": "Potash ki kami na hone dein, gir chuki bimaar pattiyon ko jala dein."
    },
    "Cotton___Bacterial_Blight": {
        "crop": "Cotton", "local_crop": "Kapas", "disease": "Bacterial Blight",
        "local_disease": "Kapas ka Jivanu Jhulsa / Kona Dhabba",
        "severity": "High", "severity_pct": 85, "bachne_ka_chance": 50,
        "symptoms": "Pattiyon ki naso ke beech konedar (angular) paani jaise dhabbe, taane par kaala rang (black arm).",
        "solution": "Copper Oxychloride 50% WP @ 2.5 g/L + Streptocycline @ 0.1 g/L ka ghol chhidkein.",
        "precaution": "Beej boyi se pehle beej sanshodhan karein, bimaari pratirodhi kismein chunein."
    },
    "Cotton___Fusarium_Wilt": {
        "crop": "Cotton", "local_crop": "Kapas", "disease": "Fusarium Wilt", "local_disease": "Kapas ka Ukatha Rog",
        "severity": "High", "severity_pct": 90, "bachne_ka_chance": 45,
        "symptoms": "Pattiyon ki nasein peeli padna, patti ka murjhana, taane ke andar cheera lagane par bhura rang dikhna.",
        "solution": "Jadon ke paas Carbendazim 50% WP @ 2 g/L ka ghol dalein (drenching).",
        "precaution": "Neem khali @ 200 kg/acre dalein, fasal chakr mein anaaj wali fasalein lagayein."
    },
    "Cotton___Healthy": {
        "crop": "Cotton", "local_crop": "Kapas", "disease": "Healthy", "local_disease": "Swasth Kapas",
        "severity": "Low", "severity_pct": 0, "bachne_ka_chance": 100,
        "symptoms": "Hari chamakdar pattiyaan, mazboot shaakhayein aur tandurust fool/tende.",
        "solution": "Routine dekhbhal karein. NPK 19:19:19 ya micronutrient spray karein.",
        "precaution": "Peele/neele card lagakar ras-choosak keeto ki nigrani karein."
    },
    "Soybean___Bacterial_Blight": {
        "crop": "Soybean", "local_crop": "Soyabean", "disease": "Bacterial Blight",
        "local_disease": "Soyabean ka Jivanu Dhabba",
        "severity": "Medium", "severity_pct": 65, "bachne_ka_chance": 70,
        "symptoms": "Chhote konedaar paani jaise dhabbe jo baad mein peele-bhure ho jaate hain aur pattiyaan fati fati lagti hain.",
        "solution": "Copper Hydroxide 77% WP @ 2 g/L + Streptocycline @ 0.05 g/L ka chhidkaw karein.",
        "precaution": "Pattiyaan geeli hone par khet mein kaam na karein, do saal ka fasal chakr apnayein."
    },
    "Soybean___Frogeye_Leaf_Spot": {
        "crop": "Soybean", "local_crop": "Soyabean", "disease": "Frogeye Leaf Spot",
        "local_disease": "Soyabean ka Mendhak Aankh Dhabba",
        "severity": "Medium", "severity_pct": 65, "bachne_ka_chance": 70,
        "symptoms": "Chhote gol dhabbe jinki baahar laal-bhuri border aur beech mein halka dhoosar rang hota hai.",
        "solution": "Azoxystrobin 18.2% + Difenoconazole 11.4% SC @ 1 ml/L ka chhidkaw karein.",
        "precaution": "Pratirodhi beej boyein, fasal katayi ke baad aavshesh mitti mein dabba dein."
    },
    "Soybean___Rust": {
        "crop": "Soybean", "local_crop": "Soyabean", "disease": "Asian Soybean Rust",
        "local_disease": "Soyabean ka Rataua / Rust",
        "severity": "High", "severity_pct": 90, "bachne_ka_chance": 40,
        "symptoms": "Nichli pattiyon par baarik bhure-laal daane jaise ubhaar (pustules), pattiyaan tezi se jhadna.",
        "solution": "Tebuconazole 25.9% EC @ 1.25 ml/L ya Hexaconazole 5% EC @ 2 ml/L ka turant chhidkaw karein.",
        "precaution": "Samay par boyi karein, ghanepan se bachein aur nichli pattiyon ki hafte mein jaanch karein."
    },
    "Soybean___Healthy": {
        "crop": "Soybean", "local_crop": "Soyabean", "disease": "Healthy", "local_disease": "Swasth Soyabean",
        "severity": "Low", "severity_pct": 0, "bachne_ka_chance": 100,
        "symptoms": "Hari-bhari tikhunti pattiyaan, tandurust vikas aur bina kisi daag ke faliyan.",
        "solution": "Kisi chemical dawai ki zaroorat nahi hai. Khet ko ghaas-mukt rakhein.",
        "precaution": "Khet mein jal-nikasi (drainage) achhi rakhein, beej sanshodhan zaroor karein."
    }
}


# -------------------------------------------------------------
# 5. TRAINING ROUTINE
# -------------------------------------------------------------
def train_and_evaluate():
    log("=== Starting Training Pipeline ===")

    classes, class_to_idx, (train_p, train_l), (val_p, val_l), (test_p, test_l) = create_dataset_splits()
    num_classes = len(classes)

    # Save class indices
    idx_to_class = {i: c for c, i in class_to_idx.items()}
    class_indices_path = os.path.join(MODELS_DIR, "class_indices.json")
    with open(class_indices_path, "w", encoding="utf-8") as f:
        json.dump({
            "classes": classes,
            "class_to_idx": class_to_idx,
            "idx_to_class": idx_to_class
        }, f, indent=2)
    log(f"Saved class indices mapping to {class_indices_path}")

    # Save disease metadata
    metadata_path = os.path.join(MODELS_DIR, "disease_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(METADATA, f, indent=2, ensure_ascii=False)
    log(f"Saved disease metadata to {metadata_path}")

    # Build tf datasets
    train_ds = create_tf_dataset(train_p, train_l, num_classes, is_training=True)
    val_ds = create_tf_dataset(val_p, val_l, num_classes, is_training=False)
    test_ds = create_tf_dataset(test_p, test_l, num_classes, is_training=False)

    # Build model
    model, base_model = build_model(num_classes)

    # Phase 1: Train classification head with frozen base model
    log("Phase 1: Training classification head (base model frozen)...")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    model_keras_path = os.path.join(MODELS_DIR, "crop_disease_model.keras")
    model_h5_path = os.path.join(MODELS_DIR, "model.h5")

    cb_list = [
        callbacks.EarlyStopping(monitor='val_accuracy', patience=4, restore_best_weights=True, verbose=1),
        callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2, min_lr=1e-6, verbose=1)
    ]

    history1 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=8,
        callbacks=cb_list,
        verbose=1
    )

    # Phase 2: Fine-tuning top 30 layers of MobileNetV2
    log("Phase 2: Fine-tuning top layers of MobileNetV2 with reduced learning rate...")
    base_model.trainable = True
    for layer in base_model.layers[:-30]:
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    history2 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=6,
        callbacks=cb_list,
        verbose=1
    )

    # Save trained model in both .keras and .h5 formats
    log(f"Saving trained model to {model_keras_path}...")
    model.save(model_keras_path)

    log(f"Exporting legacy H5 model to {model_h5_path} for full compatibility...")
    try:
        model.save(model_h5_path)
    except Exception as e:
        log(f"H5 export warning: {e}")

    # -------------------------------------------------------------
    # 6. INDEPENDENT TEST SET EVALUATION
    # -------------------------------------------------------------
    log("=== Evaluating on Independent Test Set (15% Withheld) ===")
    test_loss, test_acc = model.evaluate(test_ds, verbose=1)
    log(f"Overall Test Loss    : {test_loss:.4f}")
    log(f"Overall Test Accuracy: {test_acc * 100:.2f}%")

    # Predictions on test set
    y_true = np.array(test_l)
    y_pred_probs = model.predict(test_ds, verbose=1)
    y_pred = np.argmax(y_pred_probs, axis=1)

    report_dict = classification_report(
        y_true, y_pred,
        target_names=classes,
        output_dict=True,
        zero_division=0
    )
    report_text = classification_report(
        y_true, y_pred,
        target_names=classes,
        zero_division=0
    )

    print("\n" + "=" * 80)
    print("INDEPENDENT TEST SET CLASSIFICATION REPORT (PER-CLASS METRICS)")
    print("=" * 80)
    print(report_text)
    print("=" * 80 + "\n")

    cm = confusion_matrix(y_true, y_pred).tolist()

    metrics_summary = {
        "test_loss": float(test_loss),
        "test_accuracy": float(test_acc),
        "total_test_samples": len(test_l),
        "classification_report": report_dict,
        "confusion_matrix": cm,
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    metrics_path = os.path.join(MODELS_DIR, "test_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    log(f"Saved evaluation metrics to {metrics_path}")

    log("=== Training and Evaluation Successfully Completed! ===")


if __name__ == "__main__":
    train_and_evaluate()
