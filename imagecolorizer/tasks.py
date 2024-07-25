import threading
from time import sleep
from .models import UploadedImage
from .colorize_models import colorize_image

# Semaphore to limit the number of concurrent processes
semaphore = threading.Semaphore(value=1)
queue_lock = threading.Lock()
processing_queue = []
PROCESSING_TIME = 3  # Processing time per image in seconds

def process_image(image_id):
    with semaphore:
        image_instance = UploadedImage.objects.get(id=image_id)
        image_path = image_instance.image.path
        
        # Kuyruktan çıkar ve işle
        with queue_lock:
            processing_queue.remove(image_instance)
            for i, img in enumerate(processing_queue):
                img.queue_position = i + 1
                img.save()

        # Simulate some delay
        sleep(PROCESSING_TIME)
        
        # Call the colorize function to process the image
        colorized_image_path = colorize_image(image_path)
        
        # Save the result
        image_instance.result = f'{colorized_image_path}'
        image_instance.processed = True
        image_instance.queue_position = None
        image_instance.save()
        print(f'Processed image {image_instance.id}')
