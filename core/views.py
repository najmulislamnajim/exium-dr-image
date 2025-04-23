import os
import zipfile
from io import BytesIO
from django.http import HttpResponse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from .models import Territory, ThreeGenImage
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

def home(reques):
    return redirect('login')

@login_required
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
            # territory_id = request.POST.get('territory')
            territory_id = int(request.user.username)
            print(territory_id)
            print(type(territory_id))
            dr_rpl_id = request.POST.get('dr_rpl_id')
            dr_name = request.POST.get('dr_name')
            dr_image = request.FILES.get('dr_image')
            dr_parents_image = request.FILES.get('dr_parents_image')
            dr_children_image = request.FILES.get('dr_children_image')

            # Validate required fields
            if not (  dr_rpl_id and dr_name):
                messages.error(request, " Doctor RPL ID, and Doctor Name are required.")
                return redirect('upload')

            if not (dr_image and dr_parents_image and dr_children_image):
                messages.error(request, "All three images are required.")
                return redirect('upload')

            # Get the Territory instance
            try:
                territory = Territory.objects.get(territory=territory_id)
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
    return render(request, 'base.html')

@login_required
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

@login_required
def territory_list(request):
    """
    Display a list of all territories with the number of doctors with uploaded data.
    """
    territories = Territory.objects.all()
    territory_data = []
    
    for territory in territories:
        doctor_count = ThreeGenImage.objects.filter(territory=territory).values('dr_rpl_id').distinct().count()
        territory_data.append({
            'id': territory.id,
            'territory': territory.territory,
            'territory_name': territory.territory_name,
            'doctor_count': doctor_count
        })
    
    return render(request, 'territory_list.html', {'territories': territory_data})

@login_required
def territory_detail(request, territory_code):
    """
    Display details of doctors and their images for a specific territory code.
    
    Args:
        request (HttpRequest): The HTTP request object.
        territory_code (str): The territory code.
        
    Returns:
        HttpResponse: The HTTP response object, render territory_detail template.
    """
    territory = get_object_or_404(Territory, territory=territory_code)
    images = ThreeGenImage.objects.filter(territory=territory)
    
    return render(request, 'territory_detail.html', {
        'territory': territory,
        'images': images
    })


@login_required
def territory_list_page(request):
    """
    Display a paginated list of all territories with the number of doctors with uploaded data.
    Handle search by territory code to redirect to the territory detail page.
    """
    # Handle search form submission
    if request.method == 'POST':
        territory_code = request.POST.get('territory_code', '').strip()
        if territory_code:
            try:
                Territory.objects.get(territory=territory_code)
                return redirect('territory_detail', territory_code=territory_code)
            except Territory.DoesNotExist:
                messages.error(request, f"Territory code '{territory_code}' not found.")
                return redirect('territory_list')

    # Get all territories
    territories = Territory.objects.all()
    
    # Set up pagination (10 territories per page)
    paginator = Paginator(territories, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prepare territory data for the template
    territory_data = [
        {
            'id': territory.id,
            'territory': territory.territory,
            'territory_name': territory.territory_name,
            'region_name': territory.region_name,
            'zone_name': territory.zone_name,
            'doctor_count': ThreeGenImage.objects.filter(territory=territory).values('dr_rpl_id').distinct().count()
        }
        for territory in page_obj
    ]
    
    return render(request, 'territory_list.html', {
        'territories': territory_data,
        'page_obj': page_obj
    })
    
    
def login_view(request):
    """
    Handle user login with territory code or admin credentials.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to territory_detail if user is not superuser and username matches a territory
            if not user.is_superuser:
                return redirect('upload')
            # Redirect superuser to territory_list
            return redirect('territory_list')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('login')
    
    return render(request, 'login.html')

@login_required
def user_logout(request):
    """
    Log out the current user and redirect to login page.
    """
    logout(request)
    return redirect('login')