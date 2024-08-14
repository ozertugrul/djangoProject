import base64
from functools import cache
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from .forms import ImageUploadForm
from .models import UploadedImage, UserProfile
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
from PIL import Image
import io

def index(request):
    upload_directory = 'media/uploads/'  # Change this to your directory path
    top_images = find_best_images(upload_directory)
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
    return render(request, 'index.html', {'form': form, 'top_images': top_images})


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
        with open(image_instance.result, 'rb') as img_file:
            blob_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            
            input_image_path = image_instance.result  # Replace with your image file path
            watermark_image_path = "static/staticfiles/images/watermarks.png"  # Path to your watermark image
            watermark_output = add_image_watermark(input_image_path, watermark_image_path, 0)
            watermark_min_output = add_image_watermark(input_image_path, watermark_image_path, 1)
            
            img = Image.open(input_image_path)
            # Example usage

            width, height = img.size
            new_size = (int(width * 0.10), int(height * 0.10))
            low_res_img = img.resize(new_size, Image.LANCZOS)
            buffer = io.BytesIO()
            low_res_img.save(buffer, format="PNG")
            low_res_blob = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            

            return render(request, 'editor.html', {'image': image_instance, "credits": user_credits.remaining_credits, 'user': user, 'blob': blob_data, 'low_blob': watermark_min_output, "watermark_image": watermark_output})
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
        if user_exists == True:
            user = User.objects.get(email=email)
            user_profile = UserProfile.objects.get(user_id=user.id)
            if user_profile.g_check == 1:
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'exists': user_exists})
        else:
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
            user.save()
            
            user_profile = UserProfile.objects.get(user_id=user.id)
            user_profile.g_check = 0
            print(user_profile.g_check) 
            user_profile.save()
            print(user_profile.g_check)
            # Eğer ek profil bilgileri eklemeniz gerekiyorsa, custom user model veya profile modeli kullanmanız gerekebilir.
            
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

def setting(request):
    user_id = request.session.get('user_id')
    # Kullanıcı session yoksa index.html sayfasına yönlendirin
    if not user_id:
        return redirect('index') 
    
    user = User.objects.get(id=user_id)
    user_profile = UserProfile.objects.get(user_id = request.session.get('user_id'))
    return render(request, 'setting.html', {'user': user, 'user_profile': user_profile})


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
                # bu kısım
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




def add_image_watermark(input_image, watermark_image_path, resize_option):
    # Create an in-memory binary stream
    buffered = io.BytesIO()

    # Open the input image and watermark image
    with Image.open(input_image) as base_image:
        # Resize the base image if resize_option is 1
        if resize_option == 1:
            base_width, base_height = base_image.size
            new_width = int(base_width * 0.20)
            new_height = int(base_height * 0.20)
            base_image = base_image.resize((new_width, new_height), Image.LANCZOS)
        
        with Image.open(watermark_image_path).convert("RGBA") as watermark_image:
            # Resize the watermark to fit better
            watermark_image.thumbnail((400, 400), Image.LANCZOS)
            txt = Image.new("RGBA", base_image.size, (255, 255, 255, 0))

            width, height = base_image.size
            w_width, w_height = watermark_image.size

            # Rotate the watermark by 45 degrees
            angle = 0
            for i in range(0, width, 400):  # Adjusted step size to match the text box size
                for j in range(0, height, 400):
                    watermark = watermark_image.copy()
                    rotated_watermark = watermark.rotate(angle, expand=True)
                    txt.paste(rotated_watermark, (i, j), mask=rotated_watermark)

            watermarked = Image.alpha_composite(base_image.convert("RGBA"), txt)
            watermarked = watermarked.convert("RGBA")

            # Save the image to the in-memory stream in PNG format
            watermarked.save(buffered, format="PNG")

    # Encode the image as base64
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return img_str

import os
import time
import numpy as np
from PIL import Image

def calculate_colorfulness(image):
    image = image.convert("RGB")
    np_image = np.array(image)
    R, G, B = np_image[:, :, 0], np_image[:, :, 1], np_image[:, :, 2]
    rg = R - G
    yb = 0.5 * (R + G) - B
    colorfulness = np.sqrt(np.mean(rg**2) + np.mean(yb**2))
    return colorfulness

def calculate_contrast(image):
    image = image.convert("L")  # Convert to grayscale
    np_image = np.array(image)
    contrast = np.std(np_image)  # Standard deviation as contrast measure
    return contrast

def calculate_histogram_diversity(image):
    image = image.convert("RGB")
    np_image = np.array(image)
    hist, _ = np.histogram(np_image, bins=256, range=(0, 256))
    histogram_diversity = np.sum(hist > 0) / hist.size
    return histogram_diversity

def rate_image(image):
    colorfulness = calculate_colorfulness(image)
    contrast = calculate_contrast(image)
    histogram_diversity = calculate_histogram_diversity(image)
    
    colorfulness_score = np.clip(colorfulness / 255.0 * 25, 0, 25)
    contrast_score = np.clip(contrast / 255.0 * 15, 0, 15)
    histogram_score = np.clip(histogram_diversity * 10, 0, 10)
    
    total_score = colorfulness_score + contrast_score + histogram_score
    return np.clip(total_score, 0, 50)

def find_best_images(directory):
    scores = []
    
    for filename in os.listdir(directory):
        if filename.endswith("_colorized.png"):
            file_path = os.path.join(directory, filename)
            image = Image.open(file_path)
            score = rate_image(image)
            scores.append((filename, score))
    
    # Sort by score in descending order and select top 3
    scores.sort(key=lambda x: x[1], reverse=True)
    top_images = [filename for filename, score in scores[:3]]
    
    return top_images

def monitor_directory(directory):
        top_images = find_best_images(directory)
        print("Top 3 images:", top_images)
        
        





from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import Coupon, CouponUsage, UserCredits

@login_required
@csrf_exempt
def redeem_coupon(request):
    if request.method == "POST":
        data = json.loads(request.body)
        code = data.get('code')

        coupon = get_object_or_404(Coupon, code=code)

        # Check if the user has already used this coupon
        if CouponUsage.objects.filter(user=request.user, coupon=coupon).exists():
            return JsonResponse({'success': False, 'message': 'You have already used this coupon.'}, status=400)

        if not coupon.is_valid():
            return JsonResponse({'success': False, 'message': 'This coupon has reached its limit of uses.'}, status=400)

        # Add credits to the user
        user_credits = request.user.usercredits
        user_credits.remaining_credits += coupon.credits
        user_credits.total_credits = coupon.credits
        user_credits.save()

        # Update coupon usage
        coupon.used_count += 1
        coupon.save()

        # Record the coupon usage
        CouponUsage.objects.create(user=request.user, coupon=coupon)

        return JsonResponse({'success': True, 'credits': coupon.credits})

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)


from django.contrib.auth import update_session_auth_hash
@csrf_exempt
def change_password(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        user_id = request.session.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            if check_password(current_password, user.password):
                user.password = make_password(new_password)
                user.save()
                return JsonResponse({'success': True, 'message': 'Password changed successfully', 'redirect_url': '/'})
            else:
                return JsonResponse({'success': False, 'message': 'Current password is incorrect'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

User = get_user_model()

@csrf_exempt
@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        user.delete()
        request.session['user_id'] = ""
        return JsonResponse({'success': True, 'redirect_url': '/'})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

import iyzipay
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import Payment, UserCredits

# İyzico yapılandırması
options = {
    'api_key': settings.IYZICO_API_KEY,
    'secret_key': settings.IYZICO_SECRET_KEY,
    'base_url': settings.IYZICO_BASE_URL
}

def create_payment_request(buyer, address, basket_items, callback_url):
    conversation_id = str(uuid.uuid4())
    requesta = {
        'locale': 'tr',
        'conversationId':conversation_id,
        'price': '8.99',
        'paidPrice': '9.36',
        'currency': 'TRY',
        'basketId': 'B67832',
        'paymentGroup': 'PRODUCT',
        "callbackUrl": callback_url,
        "enabledInstallments": ['2', '3', '6', '9'],
        'buyer': buyer,
        'shippingAddress': address,
        'billingAddress': address,
        'basketItems': basket_items
    }
    checkout_form_initialize = iyzipay.CheckoutFormInitialize().create(requesta, options)

    return checkout_form_initialize

@login_required
def initiate_payment(request):
    if request.method == 'POST':
        credit_amount = request.POST.get('credit_amount')
        price = {
            '10': 0.99,
            '20': 8.99,
            '50': 44.99
        }.get(credit_amount, 0)

        buyer = {
            'id': str(request.user.id),
            'name': request.user.first_name,
            'surname': request.user.last_name,
            'email': request.user.email,
            'identityNumber': '74300864791',
            'registrationAddress': 'Nidakule Göztepe, Merdivenköy Mah. Bora Sok. No:1',
            'city': 'Istanbul',
            'country': 'Turkey',
            'ip': '85.34.78.112',
            'zipCode': '34732',
        }

        address = {
            'contactName': f'{request.user.first_name} {request.user.last_name}',
            'city': 'Istanbul',
            'country': 'Turkey',
            'address': 'Nidakule Göztepe, Merdivenköy Mah. Bora Sok. No:1',
            'zipCode': '34732',
        }

        basket_items = [
            {
                'id': 'BI101',
                'name': f'{credit_amount} Credits',
                'category1': 'Credits',
                'itemType': 'VIRTUAL',
                'price': str(price)
            }

        ]

   
        callback_url = request.build_absolute_uri(reverse('payment_callback'))
        print(callback_url)
        result = create_payment_request(buyer, address, basket_items, callback_url)
        header = {'Content-Type': 'application/json'}
        content = result.read().decode('utf-8')
        json_content = json.loads(content)

        #print(type(json_content))
        print(json_content["checkoutFormContent"])
  
        if 1==2:
            return render(request, 'imagecolorizer/payment_form.html', {'form_content': json_content['checkoutFormContent']})
        else:
           
            return HttpResponse(json_content["checkoutFormContent"])
        
            #return render(request, 'imagecolorizer/error.html', {'error': result.get('errorMessage', 'An error occurred')})

    return render(request, 'account.html')



@csrf_exempt
def payment_callback(request):
    if request.method == 'POST':
            token = request.POST.get('token')
            # Verify the payment with Iyzico
            print("token****************")
            print(token)
            payload={
                'locale':'tr',
                'conversationId':'123456789',
                'token':token,
            }
            payment = iyzipay.CheckoutForm().retrieve(payload, options)
            payment_data = payment.read().decode('utf-8')

            # Parse the JSON data
            payment_json = json.loads(payment_data)

            # Check the payment status
            payment_status = payment_json.get("paymentStatus")
            print(payment_json)
            if payment_status == 'SUCCESS':
                # Payment successful, create Payment object
                print("************************************www")
                amount = payment_json.get("price")
                credits = payment_json["itemTransactions"][0].get("itemId")
                if(credits=='BI101'):
                    credits=10
                elif (credits=='BI100'):
                    credits=1
                transaction_id = payment_json.get("paymentId")
                Payment.objects.create(
                    user=request.user,
                    amount=amount,
                    credits=credits,
                    transaction_id=transaction_id
                )
    
            else:
                # Payment failed
                print("Failed")

    return redirect('homepage')  