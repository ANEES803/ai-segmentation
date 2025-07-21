from django.shortcuts import render

# Create your views here.
import os
import cv2
import numpy as np
import logging
from PIL import Image
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib import messages
from django.http import JsonResponse
from .models import PaintTest
from .forms import PaintTestForm
from .model_loader import load_sam_model

# Set up logging
logger = logging.getLogger(__name__)

# Load SAM model once
try:
    sam_predictor = load_sam_model()
    logger.info("SAM model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load SAM model: {e}")
    sam_predictor = None


def upload_image(request):
    """
    Handle image upload and processing with SAM model for wall segmentation and color application.
    """
    if request.method == 'POST':
        form = PaintTestForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Save the form data first
                paint_test = form.save()
                logger.info(f"Paint test created with ID: {paint_test.pk}")

                # Check if SAM model is loaded
                if sam_predictor is None:
                    messages.error(request, "AI model is not available. Please try again later.")
                    return render(request, 'upload_image.html', {'form': form})

                # Extract uploaded data
                image_field = paint_test.original_image
                x = int(paint_test.clicked_x) if paint_test.clicked_x else 0
                y = int(paint_test.clicked_y) if paint_test.clicked_y else 0
                hex_color = paint_test.color or "#ff0000"

                logger.info(f"Processing image: {image_field}, click point: ({x}, {y}), color: {hex_color}")

                # Convert hex to BGR for OpenCV
                hex_color = hex_color.lstrip('#')
                if len(hex_color) != 6:
                    hex_color = "ff0000"  # Default to red if invalid
                
                # Convert hex to BGR (OpenCV uses BGR, not RGB)
                bgr_color = tuple(int(hex_color[i:i+2], 16) for i in (4, 2, 0))
                logger.info(f"BGR color: {bgr_color}")

                # Construct full path to the uploaded image
                full_path = os.path.join(settings.MEDIA_ROOT, str(image_field))
                logger.info(f"Image path: {full_path}")

                # Check if file exists
                if not os.path.exists(full_path):
                    logger.error(f"Image file not found: {full_path}")
                    messages.error(request, "Uploaded image file not found.")
                    return render(request, 'upload_image.html', {'form': form})

                # Load and process the image
                img = cv2.imread(full_path)
                if img is None:
                    logger.error(f"Failed to load image: {full_path}")
                    messages.error(request, "Failed to load the uploaded image.")
                    return render(request, 'upload_image.html', {'form': form})

                # Get image dimensions
                height, width = img.shape[:2]
                logger.info(f"Image dimensions: {width}x{height}")

                # Validate click coordinates
                if x < 0 or x >= width or y < 0 or y >= height:
                    logger.warning(f"Click coordinates ({x}, {y}) are outside image bounds ({width}x{height})")
                    # Use center of image as fallback
                    x, y = width // 2, height // 2
                    logger.info(f"Using center coordinates: ({x}, {y})")

                # Convert BGR to RGB for SAM (SAM expects RGB)
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # Run SAM model
                logger.info("Running SAM prediction...")
                sam_predictor.set_image(img_rgb)
                
                masks, scores, logits = sam_predictor.predict(
                    point_coords=np.array([[x, y]]),
                    point_labels=np.array([1]),  # 1 for foreground point
                    multimask_output=True
                )

                logger.info(f"SAM returned {len(masks)} masks with scores: {scores}")

                # Select the best mask (highest score)
                best_mask_idx = np.argmax(scores)
                best_mask = masks[best_mask_idx]
                best_score = scores[best_mask_idx]
                
                logger.info(f"Selected mask {best_mask_idx} with score: {best_score}")
                logger.info(f"Mask covers {np.sum(best_mask)} pixels out of {best_mask.size}")

                # Create the painted image
                painted_img = img.copy()
                
                # Apply color with blending to preserve some original texture
                # Method 1: Simple replacement
                painted_img[best_mask] = bgr_color
                
                # Method 2: Blended approach (uncomment to use)
                # alpha = 0.7  # Blend factor
                # painted_img[best_mask] = (
                #     alpha * np.array(bgr_color) + 
                #     (1 - alpha) * painted_img[best_mask]
                # ).astype(np.uint8)

                # Create output filename and path
                output_filename = f"painted_{paint_test.pk}_{x}_{y}.jpg"
                output_path = os.path.join(settings.MEDIA_ROOT, output_filename)
                
                # Ensure media directory exists
                os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

                # Save the painted image
                success = cv2.imwrite(output_path, painted_img)
                if not success:
                    logger.error(f"Failed to save painted image to: {output_path}")
                    messages.error(request, "Failed to save the processed image.")
                    return render(request, 'upload_image.html', {'form': form})

                logger.info(f"Painted image saved to: {output_path}")

                # Update the model with the result image path
                paint_test.result_image = output_filename
                paint_test.save()

                messages.success(request, "Image processed successfully!")
                return redirect('view_results', pk=paint_test.pk)

            except Exception as e:
                logger.error(f"Error processing image: {str(e)}", exc_info=True)
                messages.error(request, f"An error occurred while processing the image: {str(e)}")
                return render(request, 'upload_image.html', {'form': form})
        else:
            logger.warning(f"Form validation failed: {form.errors}")
            messages.error(request, "Please correct the form errors.")
    else:
        form = PaintTestForm()

    return render(request, 'upload_image.html', {'form': form})


def view_results(request, pk):
    """
    Display the original and processed images side by side.
    """
    try:
        test = get_object_or_404(PaintTest, pk=pk)
        logger.info(f"Displaying results for paint test ID: {pk}")
        
        # Construct URLs for the images
        original_url = None
        result_url = None
        
        if test.original_image:
            original_url = settings.MEDIA_URL + str(test.original_image)
            logger.info(f"Original image URL: {original_url}")
        
        if test.result_image:
            result_url = settings.MEDIA_URL + test.result_image
            logger.info(f"Result image URL: {result_url}")
            
            # Check if result file actually exists
            result_path = os.path.join(settings.MEDIA_ROOT, test.result_image)
            if not os.path.exists(result_path):
                logger.warning(f"Result image file not found: {result_path}")
                messages.warning(request, "Processed image file not found.")
                result_url = None
        
        context = {
            'test': test,
            'original_url': original_url,
            'result_url': result_url,
            'has_result': result_url is not None
        }
        
        return render(request, 'view_results.html', context)
        
    except Exception as e:
        logger.error(f"Error displaying results: {str(e)}", exc_info=True)
        messages.error(request, "An error occurred while loading the results.")
        return redirect('upload_image')


def debug_sam_status(request):
    """
    Debug endpoint to check SAM model status.
    """
    status = {
        'sam_loaded': sam_predictor is not None,
        'media_root': settings.MEDIA_ROOT,
        'media_url': settings.MEDIA_URL,
        'media_root_exists': os.path.exists(settings.MEDIA_ROOT)
    }
    return JsonResponse(status)
