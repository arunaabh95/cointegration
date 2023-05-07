from django.shortcuts import redirect, render
from django.db.models import F, ExpressionWrapper, fields
from django.contrib import messages
from login.models import User, Pair,Transaction

from datetime import date, timedelta

from .util import execute_trade_for_time, generate_graphs


def home(request):
    return render(request, "login/index.html")

def signup(request):
    if request.method == "POST":
        fname = request.POST['fname']
        lname = request.POST['lname']
        email = request.POST['email']
        password = request.POST['pass']
        try:
            myuser = User(email=email, password=password, fname=fname, lname=lname)
            myuser.save()
            messages.success(request, "Your account has been successfully created!")
        except Exception as inst:
            messages.error(request, inst)
        else:
            return redirect("signin")
    return render(request, "login/signup.html")

def signin(request):
    if request.session.test_cookie_worked():
        request.session.delete_test_cookie()
    else:
        request.session.set_test_cookie()
        messages.error(request, 'Please enable cookie')

    if request.method != 'POST':
        return render(request, "login/signin.html")
    
    email = request.POST['email']
    password = request.POST['pass']
    try:
        user = User.objects.get(email=email, password=password)
    except:
        messages.error(request, "Wrong email or password!")
        return redirect("signin")
    else:
        request.session['fname'] = str(user.get_first_name())
        request.session['uid'] = user.id
        request.session['authenticated'] = True
        return render(request, "login/index.html")

def signout(request):
    # end session
    del request.session['fname']
    del request.session['uid']
    del request.session['authenticated']    
    messages.success(request, "You logged out successfully!")
    return redirect("home")

def pairs(request):
    if not request.session['authenticated']:
        redirect("home")
    # Fetch all unique sectors from the database
    sectors = Pair.objects.values_list('sector', flat=True).distinct()
    user_id = id(request.session.get('uid'))
    #TODO: Test what used pairs looks like
    used_pairs = set(Transaction.objects.filter(user__id=user_id).values_list('pair__stock1', 'pair__stock2'))
    print(used_pairs)
    # Create a dictionary to hold all sector-wise pairs
    sector_pairs = {}
    for sector in sectors:
        # Fetch all pairs for the current sector
        pairs = Pair.objects.filter(sector=sector).order_by('-score')
        sector_pairs[sector] = make_pair_dict(pairs, used_pairs)

    context = {
        'sectors': sectors,
        'sector_pairs': sector_pairs
    }
    return render(request, 'login/pairs.html', context)
    
def dashboard(request):
    if not request.session['authenticated']:
        return render(request, "login/signin.html")
    
    userId = request.session.get('uid')
    user = User.objects.get(id=userId)

    if request.method == 'POST':
        stocks = request.POST['pair'].split('_')
        pair = Pair.objects.get(stock1=stocks[0], stock2=stocks[1])
        transaction = Transaction(user=user, pair=pair, start_time = date.today())
        transaction.save()
        return redirect("dashboard")

    # now show all the transactions
    transactions = Transaction.objects.filter(user__id=userId)
    # loop to add end date
    for transaction in transactions:
        if not transaction.get_end_time():
            transaction.end_time = date.today()
    for transaction in transactions:
        print(transaction.get_end_time(), transaction.get_start_time(), transaction.get_stock_pair().stock1, transaction.get_stock_pair().stock2)
    
    week = timedelta(days=7)
    qs = transactions.annotate(
        duration = ExpressionWrapper(F('end_time') - F('start_time'), output_field=fields.DurationField())
    )
    transactions = qs.filter(duration__gt=week)
    data = generate_data(transactions)
    plots = generate_graphs(data)
    print(len(plots))
    return render(request, "login/dashboard.html", {'plots' : plots})

def make_pair_dict(pairs, used_pairs):
    # Convert to a list of dictionaries to pass to the template
    pair_list = []
    for pair in pairs:
        if pair.get_pairs in used_pairs:
            continue
        pair_dict = {
            'stock1': pair.stock1,
            'stock2': pair.stock2,
            'score': pair.score
        }
        pair_list.append(pair_dict)
    return pair_list

def generate_data(transactions):
    data = {}
    for transaction in transactions:
        temp = execute_trade_for_time(transaction)
        if temp is not None:
            stock1 = transaction.get_stock_pair().stock1
            stock2 = transaction.get_stock_pair().stock2
            data[stock1 + '_' + stock2] = temp
    return data
