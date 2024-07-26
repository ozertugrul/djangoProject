from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from .forms import ImageUploadForm
from .models import Users, UploadedImage
from .tasks import process_image, queue_lock, processing_queue, PROCESSING_TIME
import threading
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

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

def editor(request, image_id):
    image_instance = UploadedImage.objects.get(id=image_id)
    if image_instance.processed:
        return render(request, 'editor.html', {'image': image_instance})
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
    
    user = get_object_or_404(Users, id=user_id)
    return render(request, 'gallery.html', {'username': user.name})

def account(request):
    user_id = request.session.get('user_id')
    # Kullanıcı session yoksa index.html sayfasına yönlendirin
    if not user_id:
        return redirect('index') 
    
    user = get_object_or_404(Users, id=user_id)
    return render(request, 'account.html', {'username': user.name})

def check_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user_exists = Users.objects.filter(email=email).exists()
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
                username=name,  # Email'i username olarak kullanıyoruz
                email=email,
                password=password,
                first_name=name,
                last_name=surname
            )
            
            # Eğer ek profil bilgileri eklemeniz gerekiyorsa, custom user model veya profile modeli kullanmanız gerekebilir.
            # user.profile.save()
            user = authenticate(username=name, password=password)
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
            user = Users.objects.get(email=email)
            is_password_correct = check_password(password, user.password)
            if is_password_correct:
                request.session['user_id'] = user.id 
                return JsonResponse({'success': True, 'message': 'Logged in successfully', 'redirect_url': 'homepage'})
            else:
                return JsonResponse({'success': False, 'message': 'Wrong Password'})
        except Users.DoesNotExist:
            print(f"User not found for email: {email}")
            return JsonResponse({'success': False, 'message': 'User does not exist'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def homepage(request):
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

    user = request.user
    print(f' username: {user}')
    return render(request, 'homepage.html', {'form': form, 'username': user.username})


def logout(request):
    auth_logout(request)
    return redirect('index')

def settings(request):
    user_id = request.session.get('user_id')
    # Kullanıcı session yoksa index.html sayfasına yönlendirin
    if not user_id:
        return redirect('index') 
    
    user = get_object_or_404(Users, id=user_id)

    return render(request, 'settings.html', {'username': user.name})


def sologin(request):
    print(request.user.email)
    print(request.user.id)
    request.session['user_id'] = request.user.id
    return redirect('homepage') 
