import os
import zipfile
from io import BytesIO
from django.http import HttpResponse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from .models import Territory, ThreeGenImage

def upload(request):
    """
    View to handle uploading three generation images for a doctor.
    
    Args:
        request (HttpRequest): The HTTP request object.
        
    Returns:
        HttpResponse: The HTTP response object, render upload template.
    """
    if request.method == 'POST':
        try:
            # Extract form data
            territory_id = request.POST.get('territory')
            dr_rpl_id = request.POST.get('dr_rpl_id')
            dr_name = request.POST.get('dr_name')
            dr_image = request.FILES.get('dr_image')
            dr_parents_image = request.FILES.get('dr_parents_image')
            dr_children_image = request.FILES.get('dr_children_image')

            # Validate required fields
            if not (territory_id and dr_rpl_id and dr_name):
                messages.error(request, "Territory, Doctor RPL ID, and Doctor Name are required.")
                return redirect('upload')

            # Get the Territory instance
            try:
                territory = Territory.objects.get(id=territory_id)
            except Territory.DoesNotExist:
                messages.error(request, "Invalid Territory selected.")
                return redirect('upload')

            # Create ThreeGenImage instance
            three_gen_image = ThreeGenImage(
                territory=territory,
                dr_rpl_id=dr_rpl_id,
                dr_name=dr_name,
                dr_image=dr_image,
                dr_parents_image=dr_parents_image,
                dr_children_image=dr_children_image
            )

            # Validate and save
            try:
                three_gen_image.full_clean()  # Run model validation (including two-doctor limit)
                three_gen_image.save()
                messages.success(request, f"Images for {dr_name} (RPL ID: {dr_rpl_id}) uploaded successfully.")
                return redirect('upload')
            except ValidationError as e:
                messages.error(request, f"Validation error: {str(e)}")
                return redirect('upload')
            except Exception as e:
                messages.error(request, f"Error saving images: {str(e)}")
                return redirect('upload')

        except Exception as e:
            print('Error:', str(e))
    # For GET request, render the form
    territories = Territory.objects.all()
    return render(request, 'base.html', {'territories': territories})

def download(request):
    """
    Download the entire dr_images folder as a ZIP file, preserving the directory structure.
    """
    dr_images_path = os.path.join(settings.MEDIA_ROOT, 'dr_images')
    
    # Check if dr_images directory exists
    if not os.path.exists(dr_images_path):
        messages.error(request, "No images found in dr_images directory.")
        return redirect('upload')

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Walk through the dr_images directory
        for root, _, files in os.walk(dr_images_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Compute the relative path for the ZIP file
                relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                zip_file.write(file_path, relative_path)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="dr_images.zip"'
    return response
