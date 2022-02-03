import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from flask import Flask, request, jsonify
import re
import json
import requests
from bs4 import BeautifulSoup
import urllib.request
import cv2

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


f = open('train_data.json',)
json_file = json.load(f)

def get_nut_link(dish):
    link_result = []
    dish = "+".join(dish.split(" "))+"+nutrition"
    url = 'https://google.com/search?q='+dish
    # Perform the request
    try:
        r = requests.get(url)
        html =  r.text

        try:
            soup = BeautifulSoup(html, 'html.parser')
            for link in soup.findAll('a'):
                if re.search("https://www.myfitnesspal.com",str(link.get('href'))) and str(link.get('href')).find("nutrition-facts-calories") in (0,-1):
                    link_result.append(link.get('href'))
        except:
            pass
        if len(link_result) == 0:
            link_result.append("Nutritions Not Available")
    except:
        link_result.append("Nutritions Not Available")
    return link_result[0]

def categorize_nutrients(list_of_nutrients):
    fat = {}
    Carbs={}
    Protein = {}
    for i in list_of_nutrients:
        if i.split("->")[0].strip() in ['Carbs','Dietary Fiber','Sugar']:
            if i.split("->")[1].strip() == "g" or i.split("->")[1].strip() == "%":
                Carbs[i.split("->")[0].strip()] = "0"+i.split("->")[1].strip()
            else:
                Carbs[i.split("->")[0].strip()] = i.split("->")[1].strip()
                
        elif i.split("->")[0].strip() in ['Fat','Saturated','Polyunsaturated','Monounsaturated','Trans']:
            if i.split("->")[1].strip() == "g" or i.split("->")[1].strip() == "%":
                fat[i.split("->")[0].strip()] = "0"+i.split("->")[1].strip()
            else:
                fat[i.split("->")[0].strip()] = i.split("->")[1].strip()
        else:
            if i.split("->")[1].strip() == "g" or i.split("->")[1].strip() == "%":
                Protein[i.split("->")[0].strip()] = "0"+i.split("->")[1].strip()
            else:
                Protein[i.split("->")[0].strip()] = i.split("->")[1].strip()
                
    final_dict= {"Carbohydrates":Carbs,"Fat":fat,"Protein":Protein}
    return final_dict

def get_nutrients(dish):
    web_link = get_nut_link(dish) # get link of scraping food website 
    web_link = web_link.replace("/url?q=","").strip()
    if web_link == "Nutritions Not Available":
        return web_link
    else:
        try:
            # get data from website
            request = urllib.request.Request(web_link)

            # Set a normal User Agent header, otherwise Google will block the request.
            request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36')
            raw_response = urllib.request.urlopen(request).read()

            # Read the repsonse as a utf-8 string
            html = raw_response.decode("utf-8")
            soup = BeautifulSoup(html, 'html.parser')
            try:
                cal = str(soup.findAll('span', {'class':'title-cgZqW'})[0]).split('>')[1].split('<')[0] # get cal data
            except:
                cal = "50"
            mydivs = soup.find_all("div", {"class": "NutritionalInfoContainer-3XIjH"})
            main_list = mydivs[0].findAll('div', {'class':'jss95 jss96'})+ mydivs[0].findAll('div', {'class':'jss95'}) + mydivs[0].findAll('div', {'class':'jss97'})+ mydivs[0].findAll('div', {'class':'jss96'})

            nutrients_list = []
            for i in list(set(main_list)):
                nutrients_list.append(str(i).replace('<div class="jss95">',"").replace('<div class="jss95 jss96">','').replace('<div class="jss95 jss97 jss96">','').replace("<span>"," -> ").replace('</span></div>','').replace('--<!-- --> <!-- -->','').replace('<!-- --> <!-- -->',''))

            categorized_mod_list = categorize_nutrients(nutrients_list)
            categorized_mod_list['Calories'] = cal+"g"
        except:
            categorized_mod_list = "Nutritions Not Available"
        return categorized_mod_list
    
def prd(query):
    result=[]
    for i,j in zip([rc.lower() for rc in json_file['name_recipe']],json_file['recipe']):
        if re.search(query.lower(),i):
            result.append(j)
        if len(result) > 4:
            break

    if len(result) == 0 and len(query.split()) > 1:
        for item in query.split():
            for i,j in zip([rc.lower() for rc in json_file['name_recipe']],json_file['recipe']):
                if re.search(item.lower(),i):
                    result.append(j)
    if len(result) == 0:
        result.append("Please try again with different food item!")
                    
    # remove duplicates
    result = [i for n, i in enumerate(result) if i not in result[n + 1:]]
    return result[:5]
def response_recipe(query):
    x = prd(query)

    recipe_copy = x.copy()
    dish_name = ""
    for idx, rcp_name in enumerate(recipe_copy):
        rcp_name_2 = " ".join(rcp_name['Recipe'].split(" ",4)[:4])
        # rcp_name['Recipe'] = " ".join(rcp_name['Recipe'].split(" ",4)[:4])
        if rcp_name_2 == rcp_name_2.split(','):
            if rcp_name_2 == rcp_name['Recipe'].split('/'):
                if rcp_name_2 == rcp_name_2.split('-'):
                    dish_name = rcp_name_2
                else:
                    dish_name = rcp_name_2.split('-')[0]
            else:
                 dish_name = rcp_name_2.split('/')[0]
        else:
            dish_name = rcp_name_2.split(',')[0]

        dish_name = re.sub('[^A-Za-z0-9]+', ' ', dish_name)
        nut = get_nutrients(dish_name)
    #     print(nut)
        if nut == "Nutritions Not Available":
            response_recipe = get_nutrients(query)
            if response_recipe == "Nutritions Not Available":
                x[idx]['Nutrients'] = "Not Available"
            else:
                x[idx]['Nutrients'] = response_recipe
        else:
            x[idx]['Nutrients'] = nut
    return x
    
# def predict_class(model, images, show = True):
#   # picking 44 food items and generating separate data folders for the same
#   food_list = ['apple_pie','baby_back_ribs','baklava','beef_carpaccio','beef_tartare','beet_salad','beignets','bibimbap','bread_pudding','breakfast_burrito','bruschetta','caesar_salad','cannoli','caprese_salad','carrot_cake','ceviche','cheesecake','cheese_plate','chicken_curry','chicken_quesadilla','chicken_wings','chocolate_cake','chocolate_mousse','churros','clam_chowder','club_sandwich','crab_cakes','creme_brulee','croque_madame','cup_cakes','deviled_eggs','donuts','dumplings','edamame','eggs_benedict','escargots','falafel','filet_mignon','fish_and_chips','foie_gras','french_fries','french_onion_soup','french_toast','fried_calamari']

#   for img in images:
#     img = image.load_img(img, target_size=(299, 299))
#     img = image.img_to_array(img)                    
#     img = np.expand_dims(img, axis=0)         
#     img /= 255.                                      

#     pred = model.predict(img)
#     index = np.argmax(pred)
#     food_list.sort()
#     pred_value = food_list[index]
#     pred_value = re.sub('[^A-Za-z]+', ' ', pred_value)
#     return pred_value

def predict_class(model, images, show = True):
    # picking 44 food items and generating separate data folders for the same
    food_list = ['apple_pie','baby_back_ribs','baklava','beef_carpaccio','beef_tartare','beet_salad','beignets','bibimbap','bread_pudding','breakfast_burrito','bruschetta','caesar_salad','cannoli','caprese_salad','carrot_cake','ceviche','cheesecake','cheese_plate','chicken_curry','chicken_quesadilla','chicken_wings','chocolate_cake','chocolate_mousse','churros','clam_chowder','club_sandwich','crab_cakes','creme_brulee','croque_madame','cup_cakes','deviled_eggs','donuts','dumplings','edamame','eggs_benedict','escargots','falafel','filet_mignon','fish_and_chips','foie_gras','french_fries','french_onion_soup','french_toast','fried_calamari']
    # img = cv2.imread(images)
    img = cv2.resize(images, (299, 299)) 
    img = image.img_to_array(img,dtype = float)               
    img = np.expand_dims(img, axis=0)         
    img /= 255.                                      

    pred = model.predict(img)
    index = np.argmax(pred)
    food_list.sort()
    pred_value = food_list[index]
    pred_value = re.sub('[^A-Za-z]+', ' ', pred_value)
    return pred_value

model_best = load_model("best_model_44class_epoch23_78%.hdf5",compile = False)



@app.route('/Detect_the_food',methods=['POST'])
def main():
    img_params =request.files['image'].read()
    npimg = np.fromstring(img_params, np.uint8)
    #load image
    Image_name = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    # ImgFile = request.files['file']
    # ImgFile.save('img.jpg')
    # images = ['img.jpg']
    output =predict_class(model_best, Image_name, True)

    return jsonify({'Predicted Dish':output,'Recipe':response_recipe(output)})

    

if __name__ == "__main__":    
    app.run(host='0.0.0.0', port=6000)

