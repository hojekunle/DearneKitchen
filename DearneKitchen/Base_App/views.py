from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

from Base_App.models import Items, ItemList, Feedback, AboutUs, BookTable

# Create your views here.

def HomeView(request):
    items = Items.objects.all()
    item_categories = ItemList.objects.all()
    reviews = Feedback.objects.all()
    return render(request, 'home.html', {'items': items, 'item_categories': item_categories, 'reviews': reviews})

def AboutView(request):
    data = AboutUs.objects.all() #table.objects must match model.py class names
    return render(request, 'about.html', {'data': data})

def MenuView(request):
    items = Items.objects.all()
    item_categories = ItemList.objects.all()
    return render(request, 'menu.html', {'items': items, 'item_categories': item_categories})

def BookTableView(request):
    # Pass the API key to the template
    google_maps_api_key = settings.GOOGLE_MAPS_API_KEY

    if request.method == 'POST':
        name = request.POST.get('user_name')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('user_email');
        total_persons = request.POST.get('total_persons')
        booking_date = request.POST.get('booking_date')

        if name != '' and len(phone_number) >= 11 and email != '' and total_persons != 0 and booking_date != '':
            data = BookTable(Name = name, Phone_number = phone_number,
                              Email = email, Total_person = total_persons, 
                              Booking_date = booking_date)
            
            #print('data entered', name, email, total_persons)
            data.save()

            # Send confirmation email
            subject = 'Booking Confirmation'
            message = f"Hello {name},\n\nYour booking has been successfully received.\n" \
                      f"Booking details:\nTotal persons: {total_persons}\n" \
                      f"Booking date: {booking_date}\n\nThank you for choosing us!"
            
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]  # The email of the user

            # Send the confirmation email
            send_mail(subject, message, from_email, recipient_list)

            # Add success message
            messages.success(request, 'Booking request submitted successfully! Please check your confirmation email.')

            # Redirect or render a feedback page with success message
            return render(request, 'feedback.html', {'success': 'Booking request submitted successfully! Please check your confirmation email.'})

    # Render the book_table.html template and pass the API key to it
    return render(request, 'book_table.html', {'google_maps_api_key': google_maps_api_key})


    return render(request, 'book_table.html')

def FeedbackView(request):
    reviews = Feedback.objects.all()
    return render(request, 'feedback.html', {'reviews': reviews})
