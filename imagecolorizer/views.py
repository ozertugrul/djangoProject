from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.urls import reverse
import uuid
import os
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.hashers import make_password, check_password
from .forms import UserCreationForm, ImageUploadForm
from .models import Users, UploadedImage
from .tasks import process_image, queue_lock, processing_queue, PROCESSING_TIME
import threading

def index(request):
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
    return render(request, 'gallery.html')

def account(request):
    return render(request, 'account.html')

def check_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user_exists = Users.objects.filter(email=email).exists()
        return JsonResponse({'exists': user_exists})
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = Users(
                email=form.cleaned_data['email'],
                password=make_password(form.cleaned_data['password']),
                confirm_password=make_password(form.cleaned_data['confirm_password']),
                name=form.cleaned_data['name'],
                surname=form.cleaned_data['surname']
            )
            user.save()
            return JsonResponse({'success': True, 'message': 'Account created successfully'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = Users.objects.get(email=email)
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                return JsonResponse({'success': True, 'message': 'Logged in successfully'})
            else:
                return JsonResponse({'success': False, 'message': 'Invalid credentials'})
        except Users.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User does not exist'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})