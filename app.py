from flask import Flask,render_template,flash,redirect,url_for,session
from flask.globals import request
from flask_mysqldb import MySQL
from flask_wtf import file
from wtforms import Form,StringField,TextAreaField,PasswordField,validators,FileField,SubmitField
from passlib.handlers.sha2_crypt import sha256_crypt
from functools import wraps
from flask_wtf import FlaskForm

from flask_wtf.file import FileField
import base64
import requests
import os
import uuid
from PIL import Image
import numpy as np 

app=Flask(__name__, static_url_path="/static", static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"))
app.secret_key='kutuphane'

app.config['SECRET_KEY']='Kutuphane'


#Sistem Kullanıcısı Giriş Decoratörü

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' in session:
            
            return f(*args, **kwargs)

        else:
            flash('Bu sayfayı görüntülemek için giriş yapınız','danger')
            return  redirect(url_for('login'))
    return decorated_function
##########################################################################################

#Aşağıdakileri yapınca Flask ile Mysql arasındaki ilişkiyi kurnuş oluyoruz.

app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='kutuphane'
app.config['MYSQL_CURSORCLASS']='DictCursor'

mysql=MySQL(app)

####################################################################################

#Sistem kullanıcısı kayıt formu 

class RegisterForm(Form):
    name=StringField('İsim Soyisim',validators=[validators.Length(min=4,max=25)])
    username=StringField('Kullanıcı Adı',validators=[validators.Length(min=5,max=35)])
    email=StringField('Email Adresi',validators=[validators.Email(message='Lütfen Geçerli Email Girin.. ')])
    password=PasswordField('Parola:',validators=[
        validators.DataRequired(message='Lütfen bir parola belirleyin'),
        validators.EqualTo(fieldname='confirm',message='Parolanız uyuşmuyor')

    ])
    confirm=PasswordField('Parola Doğrula')
##########################################################################################

#Sistem kullanızısı giriş formu 

class LoginForm(Form):
    username=StringField('Kullanıcı Adı')
    password=PasswordField('Parola')

##########################################################################################
#Kitap Form

class KitapForm(Form):
    name=StringField('Kitap ismi')
    author=StringField('Yazar ismi')
    img_url=StringField('Kapak Resim Adresi')
    

    

#############################################################################################

#Kayıt Olma 

@app.route('/register',methods=['GET','POST'])
def register():
    form = RegisterForm(request.form) 
    if request.method=='POST' and form.validate():
        name=form.name.data
        username=form.username.data
        email=form.email.data
        password=sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu='Insert into users(name,username,email,password) VALUES(%s,%s,%s,%s)'
        cursor.execute(sorgu,(name,username,email,password))
        mysql.connection.commit()
        cursor.close()
        flash('Başarıyla Kayıt Oldunuz ','success')
        return redirect(url_for('login'))

    else:
        return render_template("register.html",form=form)

###############################################################################################

#Login İşlemi

@app.route('/login',methods=['GET','POST'])
def login():
    form=LoginForm(request.form)
    if request.method=='POST':
        username=form.username.data
        password_entered=form.password.data
        cursor=mysql.connection.cursor()
        sorgu='Select * From users where username =%s'
        result=cursor.execute(sorgu,(username,))
        if result>0:
            data=cursor.fetchone()
            real_password=data['password']
            if sha256_crypt.verify(password_entered,real_password):
                flash('Başarıyla Giriş Yaptınız-Menü bölümünde kütüphane foksiyonlarını kullanabilirsiniz','success')
                #oturum Kontrolü
                session['logged_in']=True
                session['username']=username

                return redirect(url_for('index'))
            else:
                flash('Parolanızı yanlış girdiniz','danger')
                return redirect(url_for('login'))
        else:
            flash('Böyle bir Sistem kullanıcısı bulunmuyor','danger')
            return redirect(url_for('login'))

    else:
        return render_template('login.html',form=form)

################################################################################################################
#Sistemden çıkış işlemi

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

###############################################################################################################

#Başlangıç Sayfa

@app.route('/')
def index():
    return render_template('index.html') 

#################################################################################################################

@app.route('/addbook',methods=['GET','POST'])
@login_required
def addbook():
    form=KitapForm(request.form)
    if request.method=='POST' and form.validate:
        img_url=form.img_url.data
        name=form.name.data
        author=form.author.data
        ###########
        #kullanıcıdan aldığım resim adresine göre resmi indirme  bir şifre üretip uzantısıylla birlikte temp e yazma işlemi 
        try:
            response = requests.get(img_url)
        except (requests.exceptions.InvalidSchema, requests.exceptions.MissingSchema) as e:
            return "Doğru url girilmeli"

        if os.path.splitext(img_url)[1].lower() not in [".jpg", ".png", ".jpeg"]:
            return "Geçerli resim urli gir"

        if response.status_code != 200:
            return 'resim indirilemedi'
        #Resmin normal boyutunu temp e kaydediyor thumnail halini ise static url  olarak sitede  sunuyorum . (/static/testimage.jpg)

        with open(os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp"), name + os.path.splitext(img_url)[1]), "wb+") as f:
            f.write(response.content)
            image = Image.open(os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp"), name + os.path.splitext(img_url)[1]))
            size=(300,400)
            image.thumbnail(size)
            image.save('static/'+name + os.path.splitext(img_url)[1])
        #Kitap thumnail istatistiksel bilgileri 
        npimage = np.asarray(image)
        min=npimage.min()
        max=npimage.max()
        mean=npimage.mean()
        std=npimage.std()
        imgthumbnailurl='http://localhost:5000/static/'+name+os.path.splitext(img_url)[1]
        
        cursor = mysql.connection.cursor()
        sorgu='Insert into books(name,author,img_url,min,max,mean,std ) VALUES(%s,%s,%s,%s,%s,%s,%s)'
        cursor.execute(sorgu,(name,author,imgthumbnailurl,min,max,mean,std))
        mysql.connection.commit()
        cursor.close()

        flash('Kitap Başarıyla eklendi','success')
        return redirect(url_for('addbook'))

    return render_template('addbook.html',form=form)
    

    
####################################################################################################################
#Kitapları Listeleme 


@app.route('/books',methods=['GET','POST'])
def books():
    cursor=mysql.connection.cursor()
    sorgu='Select * From books'
    result=cursor.execute(sorgu)
    if result>0:
        books=cursor.fetchall()
        return render_template('books.html',books=books)
    else:
        return render_template('books.html')


#######################################################################################################################  

#Kitap Arama

@app.route('/search',methods=['GET','POST'])
def search():

    if request.method=='GET':

        return redirect(url_for('index'))

    else:
        keyword=request.form.get('keyword')
        cursor=mysql.connection.cursor()
        sorgu="Select * From books where name like '%"+keyword+"%' "
        result=cursor.execute(sorgu)
        if result==0:
            flash('Aranan kelimeye uygun kitap bulunamadı','warning')
            return redirect(url_for('books'))
        else:
            books=cursor.fetchall()
            return render_template('books.html',books=books)

######################################################################################################################
 
#Kitap Kaldırma İşlemi

@app.route('/delete/<string:id>')
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu='Delete from books where id = %s'
    cursor.execute(sorgu,(id,))
    mysql.connection.commit()

    return redirect(url_for('books'))


##########################################################################################################################






if __name__=='__main__':
    app.run(debug=True)