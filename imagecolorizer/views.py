from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from .forms import ImageUploadForm
from .models import Users, UploadedImage, ProcessedImage
from .tasks import process_image, queue_lock, processing_queue, PROCESSING_TIME
import threading
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .models import UserCredits, Gallery
from django.views.decorators.http import require_POST
from django.db import transaction
import hashlib
from django.shortcuts import render, redirect
from .forms import ImageUploadForm
from django.contrib.auth.models import User
import threading

def index(request):
    user_id = request.session.get('user_id')
    
    # Kullanıcı session varsa homepage'e yönlendir
    if user_id:
        return redirect('homepage')  
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image_instance = form.save()
            
            with queue_lock:
                processing_queue.append(image_instance)
                image_instance.queue_position = len(processing_queue)
                image_instance.save()

            threading.Thread(target=process_image, args=(image_instance.id,)).start()
            return redirect('editor', image_instance.id)
    else:
        form = ImageUploadForm()
    return render(request, 'index.html', {'form': form})


def iyzico_payment(request):
    # Implement your iyzico payment logic here
    # This might involve creating a payment request, redirecting to iyzico's payment page, etc.
    # For example:
    # iyzico_payment_url = create_iyzico_payment_request()
    # return redirect(iyzico_payment_url)
    pass


def editor(request, image_id):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    user_credits = UserCredits.objects.get(user_id=user_id)
    # Kullanıcı session yoksa index.html sayfasına yönlendirin
    if not user_id:
        return redirect('index') 
    image_instance = UploadedImage.objects.get(id=image_id)
    if image_instance.processed:
        return render(request, 'editor.html', {'image': image_instance, "credits" : user_credits.remaining_credits, 'user': user })
    else:
        with queue_lock:
            position = image_instance.queue_position
            estimated_wait_time = (position - 1) * PROCESSING_TIME  # Estimated wait time in seconds
        return render(request, 'waiting.html', {'position': position, 'estimated_wait_time': estimated_wait_time})
    
def mygallery(request):
    user_id = request.session.get('user_id')
    # Kullanıcı session yoksa index.html sayfasına yönlendirin
    if not user_id:
        return redirect('index') 
    
    user = User.objects.get(id=user_id)
    gallery_items = Gallery.objects.filter(user=user).order_by('-created_at')
    return render(request, 'gallery.html', {'gallery_items': gallery_items, 'name': user.first_name, 'surname': user.last_name})

    

def account(request):
    user_id = request.session.get('user_id')
    # Kullanıcı session yoksa index.html sayfasına yönlendirin
    if not user_id:
        return redirect('index') 
    
    user = User.objects.get(id=user_id)
    return render(request, 'account.html', {'user': user, 'name': user.first_name, 'surname': user.last_name})

def check_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user_exists = User.objects.filter(email=email).exists()
        return JsonResponse({'exists': user_exists})
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def signup(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        name = request.POST.get('name')
        surname = request.POST.get('surname')

        if email and password and name and surname:
            # Email'in zaten var olup olmadığını kontrol edin
            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'Email already exists'})
            
            # Yeni kullanıcıyı oluşturun
            user = User.objects.create_user(
                username=email,  # Email'i username olarak kullanıyoruz
                email=email,
                password=password,
                first_name=name,
                last_name=surname
            )
            
            # Eğer ek profil bilgileri eklemeniz gerekiyorsa, custom user model veya profile modeli kullanmanız gerekebilir.
            # user.profile.save()
            user = authenticate(username=email, password=password)
            if user is not None:
                login(request, user)
                request.session['user_id'] = user.id
            return JsonResponse({'success': True, 'message': 'Account created successfully', 'redirect_url': 'homepage'})
        else:
            return JsonResponse({'success': False, 'message': 'All fields are required'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = User.objects.get(email=email)
            print(user.email)
            is_password_correct = check_password(password, user.password)
            if is_password_correct:
                request.session['user_id'] = user.id 
                return JsonResponse({'success': True, 'message': 'Logged in successfully', 'redirect_url': 'homepage'})
            else:
                return JsonResponse({'success': False, 'message': 'Wrong Password'})
        except User.DoesNotExist:
            print(f"User not found for email: {email}")
            return JsonResponse({'success': False, 'message': 'User does not exist'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

import hashlib
from django.shortcuts import render, redirect
from .forms import ImageUploadForm
from django.contrib.auth.models import User
import threading

# Hash hesaplama fonksiyonu
def compute_hash(image_file):
    hash_sha256 = hashlib.sha256()
    for chunk in image_file.chunks():
        hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def homepage(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('index')
    
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_image = request.FILES['image']
            image_hash = compute_hash(uploaded_image)
            
            # Hash'e göre veritabanında aynı görüntüyü arayın
            existing_image = UploadedImage.objects.filter(image_hash=image_hash).first()
            if existing_image:
                # Görsel varsa, kuyruğa eklemeden doğrudan işleme başla
                image_instance = existing_image
            else:
                # Yeni görsel işleme al
                image_instance = form.save(commit=False)
                image_instance.image_hash = image_hash
                image_instance.save()  # Bu, sinyali tetikleyecek ve ProcessedImage'i oluşturacak/güncelleyecek
                
                with queue_lock:
                    processing_queue.append(image_instance)
                    image_instance.queue_position = len(processing_queue)
                    image_instance.save()

                threading.Thread(target=process_image, args=(image_instance.id,)).start()

            return redirect('editor', image_instance.id)
    else:
        form = ImageUploadForm()

    user = User.objects.get(id=user_id)
    print(f'username: {user}')
    return render(request, 'homepage.html', {'form': form, 'name': user.first_name, 'surname': user.last_name})


def logout(request):
    auth_logout(request)
    return redirect('index')

def settings(request):
    user_id = request.session.get('user_id')
    # Kullanıcı session yoksa index.html sayfasına yönlendirin
    if not user_id:
        return redirect('index') 
    
    user = User.objects.get(id=user_id)

    return render(request, 'settings.html', {'name': user.first_name, 'surname': user.last_name})


def sologin(request):
    print(request.user.email)
    print(request.user.id)
    request.session['user_id'] = request.user.id
    return redirect('homepage') 



@require_POST
def decrease_credit(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    if user_id:
        image_url = request.POST.get('image_url')
        if not image_url:
            return JsonResponse({'success': False, 'error': 'Image URL is required'})

        user_credits = UserCredits.objects.get(user=user)
        
        # Önce galeriye eklenmiş mi diye kontrol et
        existing_image = Gallery.objects.filter(user=user, image_url=image_url).exists()

        if existing_image:
            # Resim daha önce indirilmişse
            return JsonResponse({
                'success': True, 
                'remaining_credits': user_credits.remaining_credits,
                'total_credits': user_credits.total_credits,
                'new_download': False
            })
        
        # Yeni indirme ve kredi kontrolü
        if user_credits.remaining_credits > 0:
            with transaction.atomic():
                user_credits.remaining_credits -= 1
                user_credits.save()
                Gallery.objects.create(user=user, image_url=image_url)
            return JsonResponse({
                'success': True, 
                'remaining_credits': user_credits.remaining_credits,
                'total_credits': user_credits.total_credits,
                'new_download': True
            })
        else:
            return JsonResponse({'success': False, 'error': 'Insufficient credits'})

    return JsonResponse({'success': False, 'error': 'User not authenticated'})