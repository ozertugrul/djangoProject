from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from torchvision.utils import save_image
from django.urls import reverse
import uuid
from .forms import ImageUploadForm
import os

def index(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.cleaned_data['image']

            # Generate a unique filename
            file_extension = image.name.split('.')[-1]
            filename = f"{uuid.uuid4().hex}.{file_extension}"

            # Save the image to the filesystem
            fs = FileSystemStorage(location=settings.MEDIA_ROOT)
            filename = fs.save(filename, image)
            file_url = fs.url(filename)

            # Debugging information
            print(f"Filename: {filename}")
            print(f"File URL: {file_url}")

            # Redirect to the editor page with the image URL
            return redirect(reverse('editor') + f"?image_url={file_url}")
        else:
            # If form is not valid, re-render the form with errors
            return render(request, 'index.html', {'form': form})
    else:
        form = ImageUploadForm()

    return render(request, 'index.html', {'form': form})

def editor(request):
    image_url = request.GET.get('image_url')
    
    if image_url:
        # Dosya yolunu al
        image_path = os.path.join(settings.MEDIA_ROOT, os.path.basename(image_url))
        
        # Resmi renklendir
        colorized_path = colorize_image(image_path)
        
        # Renkli resmin URL'sini oluştur
        colorized_url = settings.MEDIA_URL + os.path.basename(colorized_path)
        
        return render(request, 'editor.html', {'image_url': image_url, 'colorized_url': colorized_url})
    
    return render(request, 'editor.html')

def mygallery(request):
    return render(request, 'gallery.html')

def account(request):
    return render(request, 'account.html')

import torch
from PIL import Image
from torchvision import transforms
from .models import CWGANNN  # Model sınıfınızı import edin

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
    model.eval()

    # Görüntüyü yükleme ve ön işleme
    image = Image.open(image_path).convert('L')
    transform = transforms.Compose([
        #transforms.Resize((256, 256)),
        transforms.ToTensor(),
    ])
    image_tensor = transform(image).unsqueeze(0)

    # Görüntüyü renklendirme
    with torch.no_grad():
        colorized_image = model.generator(image_tensor)

    # Tensörü PIL görüntüsüne dönüştürme
    sample_output = colorized_image.squeeze(0).cpu()
    save_image(sample_output,image_path.replace('.jpg', '_colorized.jpg'), normalize=True)
    colorized_image = transforms.ToPILImage()(colorized_image.squeeze(0).cpu())

    # Renklendirilmiş görüntüyü kaydetme
    colorized_path = image_path.replace('.jpg', '_colorized.jpg')
    #colorized_image.save(colorized_path)

    return colorized_path