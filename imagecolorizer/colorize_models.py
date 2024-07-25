from PIL import Image, ImageOps
import torch
from torchvision import transforms
from torchvision.utils import save_image
from .model import *
import os

def colorize_image(image_path):
    # Model yükleme
    # Mevcut dosyanın (views.py) bulunduğu dizini al
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Ağırlık dosyalarının yollarını oluştur
    generator_weights_path = os.path.join(current_dir, 'generator.pth')
    critic_weights_path = os.path.join(current_dir, 'critic.pth')
    
    # Model yükleme işlemi
    model = CWGANNN()
    model.load_weights(generator_weights_path, critic_weights_path)
   

    # Görüntüyü yükleme ve ön işleme
    image = Image.open(image_path).convert('L')
            # Ensure the image size is even
    def pad_to_multiple(image, multiple):
        width, height = image.size
        new_width = ((width + multiple - 1) // multiple) * multiple
        new_height = ((height + multiple - 1) // multiple) * multiple
        padding = (0, 0, new_width - width, new_height - height)
        return ImageOps.expand(image, padding, fill=0)
        

    padded_image = pad_to_multiple(image, 4)
    transform = transforms.Compose([
        #transforms.Resize((256, 256)),
        transforms.ToTensor(),
    ])
    image_tensor = transform(padded_image).unsqueeze(0)  # Add batch dimension


    # Görüntüyü renklendirme
    with torch.no_grad():
        model.eval()
        colorized_image = model.generator(image_tensor)

    # Tensörü PIL görüntüsüne dönüştürme
    sample_output = colorized_image.squeeze(0).cpu()
    save_image(sample_output,image_path.replace('.png', '_colorized.png'), normalize=True)


   # Renklendirilmiş görüntüyü kaydetme
    colorized_filename = os.path.basename(image_path).replace('.png', '_colorized.png')
    colorized_path = os.path.join('media', 'uploads', colorized_filename)
    
    # Tam yolu oluştur (kaydetme işlemi için)
    full_colorized_path = os.path.join(os.path.dirname(image_path), colorized_filename)
    
    return colorized_path