from django.shortcuts import render_to_response
from django.template import RequestContext
from rango.models import Category
from rango.models import Page
from rango.forms import CategoryForm
from rango.forms import PageForm
from rango.forms import UserForm, UserProfileForm
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from datetime import datetime
from rango.bing_search import run_query
from django.contrib.auth.models import User
from rango.models import UserProfile

def about(request):
    context = RequestContext(request)
    visits = request.session.get('visits',0)
    request.session['visits'] = visits + 1    
    context_dict = {'visits': visits}   
    cat_list = get_category_list()
    context_dict['cat_list'] = cat_list
    return render_to_response('rango/about.html',context_dict,context)

def index(request):
    context = RequestContext(request)
    category_list = Category.objects.order_by('-likes')[:5]    
    context_dict = {'categories':category_list}
    for category in category_list:
        category.url = category.name.replace(' ', '_')
    
    
    if request.session.get('last_visit'):
        #last_visit = request.session.get('last_visit')
        visits = request.session.get('visits', '0')
        #if(datetime.now()-last_visit_time).days > 0:
        request.session['visits'] = visits+1
        request.session['last_visit'] = str(datetime.now())
    else:
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = 1
        
    context_dict['visits'] =  request.session['visits']
    cat_list = get_category_list()
    context_dict['cat_list'] = cat_list
    return render_to_response('rango/index.html',context_dict,context)


            

def category(request,category_name_url):
    context = RequestContext(request)
    category_name = category_name_url.replace('_',' ')
    context_dict = {'category_name': category_name}
    context_dict['cat_list'] = get_category_list()
    try:
        category = Category.objects.get(name=category_name)
        pages = Page.objects.filter(category=category)
        context_dict['pages'] = pages
        context_dict['category'] = category
        context_dict['category_name_url'] = category_name_url
    except Category.DoesNotExist:
        pass
    
    return render_to_response('rango/category.html',context_dict,context)

def add_category(request):
    context = RequestContext(request)
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save(commit=True)
            return index(request)
        else:
            print form.errors
    else:
        form = CategoryForm()
    
    return render_to_response('rango/add_category.html',{'form':form}, context)

def add_page(request, category_name_url):
    context = RequestContext(request)
    category_name = category_name_url.replace("_"," ")
    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)
            cat = Category.objects.get(name=category_name)
            page.category = cat
            page.views = 0
            page.save()
            
            return category(request,category_name_url)
        else:
            print form.errors
    else:
        form = PageForm()
    
    return render_to_response('rango/add_page.html',
                              {'category_name_url': category_name_url,
                               'category_name': category_name,
                               'form': form},
                              context)
          
def register(request):
    context = RequestContext(request)
    registered = False
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)
        
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
                
            profile.save()
            
            registered = True
        
            
        else:
            print user_form.errors, profile_form.errors
            
    else:
        user_form  = UserForm()
        profile_form =UserProfileForm()
    
    return render_to_response(
                              'rango/register.html',
                              {'user_form':user_form, 'profile_form':profile_form, 'registered':registered},
                              context)

def user_login(request):
    context = RequestContext(request)
    
    if request.method =='POST':
        username = request.POST['username']
        password = request.POST['password']
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request,user)
                return HttpResponseRedirect('/rango')
            else:
                return HttpResponse("your account is disabled")
        else:
            print "Invalid login details:{0},{1}".format(username,password)
            return HttpResponse("Invalid login details supplied.")
    else:
        return render_to_response('rango/login.html',{},context)
    
@login_required
def restricted(request):
    return HttpResponse("Since you're logged in, you can see this text!")
       
@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/rango/')

def search(request):
    context = RequestContext(request)
    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)

    return render_to_response('rango/search.html', {'result_list': result_list}, context)


def get_category_list(max_results=0, starts_with=''):
    cat_list=[]
    if starts_with:
        cat_list = Category.objects.filter(name__startswith=starts_with)
    else:
        cat_list = Category.objects.all()
    if max_results > 0:
        if len(cat_list) > max_results:
            cat_list = cat_list[:max_results]
    for cat in cat_list:
        cat.url = cat.name.replace(' ','_')
    return cat_list

def track_url(request):
    url = '/rango/'
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            try:
                page = Page.objects.get(id=page_id)
                page.views = page.views + 1
                page.save()
                url = page.url
            except:
                pass
    return HttpResponseRedirect(url)
        
def profile(request):
    context = RequestContext(request)
    u = User.objects.get(username=request.user)
    try:
        up = UserProfile.objects.get(user=u)
    except:
        up = None
    context_dict = {'cat_list':get_category_list()}
    context_dict['user'] = u
    context_dict['userprofile'] = up
    return render_to_response('rango/profile.html',  context_dict, context)

@login_required
def like_category(request):

    cat_id = None
    if request.method == 'GET' and 'category_id' in request.GET:
        cat_id = request.GET['category_id']
    else:
        print "cat_id is null"
    
    
    likes = 0
    if cat_id:
        try:
            category = Category.objects.get(id=int(cat_id))
            if category:
                likes = category.likes + 1
                category.likes = likes
                category.save()
        except:
            likes = 0
    
    return HttpResponse(likes)
 
def suggest_category(request):
    context = RequestContext(request)
    cat_list = []
    starts_with = ''
    if request.method == 'GET':
        starts_with = request.GET['suggestion']
    else:
        starts_with = request.POST['suggestion']
    
    cat_list = get_category_list(8, starts_with)
    
    return render_to_response('rango/category_list.html', {'cat_list': cat_list }, context)     