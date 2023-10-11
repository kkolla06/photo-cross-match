# photo_cross_match API ***** MAIN *****
import face_recognition 

from flask import Flask, request

import base64
import os
import subprocess as sp
import shutil
import requests

def read_save_imgs(pp_img_url, pp_doc_id, app_img_url, app_doc_id):   
    curr_path = os.getcwd() + '/photo_match'
    pp_path = curr_path + '/passports'
    app_path = curr_path + '/applicants'
    os.makedirs(pp_path)
    os.makedirs(app_path)
    
    for i in range(len(pp_img_url)):
        pp = requests.get(pp_img_url[i]).content
        pp_file = open(pp_path + '/' + str(pp_doc_id[i]) + '.jpg', 'wb')
        pp_file.write(pp)
        pp_file.close()
        
    for i in range(len(app_img_url)):
        app = requests.get(app_img_url[i]).content
        app_file = open(app_path + '/' + str(app_doc_id[i]) + '.jpg', 'wb')
        app_file.write(app)
        app_file.close()
        
    return app_path, pp_path


def recurse (sorted_obj, pp_doc_id, app, output, match):
    i=0
    while i < len(sorted_obj):
        dist = sorted_obj[i][1]

        if sorted_obj[i][0] not in pp_doc_id:
            prev_app = match[sorted_obj[i][0]]
            prev_dist = output[prev_app][sorted_obj[i][0]]

            if dist < prev_dist:
                match[sorted_obj[i][0]] = app
                sorted_obj = list(sorted(output[prev_app].items(), key=lambda x:x[1]))
                return recurse( sorted_obj, pp_doc_id, prev_app, output, match)
                
        else:
            match[sorted_obj[i][0]] = app
            pp_doc_id.remove(sorted_obj[i][0])
            break
            
        i+=1

    return output, match


app = Flask(__name__)

@app.route('/photo-match/matchPptFrontAndPhoto', methods=['POST'])
def receive_req():
    try:
        pp_img_url, pp_doc_id, app_img_url, app_doc_id = [], [], [], []

        for pp in request.json['passports']:
            pp_img_url.append(pp['data'])
            pp_doc_id.append(pp['doc_id'])
        
        for app in request.json['photos']:
            app_img_url.append(app['data'])
            app_doc_id.append(app['doc_id'])   
            
                
        if(pp_img_url and app_img_url): 
        
            train_path, test_path = read_save_imgs(pp_img_url, pp_doc_id, app_img_url, app_doc_id)

            photo_cross_match = sp.check_output(['face_recognition', '--tolerance', '0.7', '--show-distance', 'true', train_path, test_path])


            output = {}
            for s in photo_cross_match.decode().splitlines():
                if(s.split(' ')[0] != "WARNING:" and s.split(',')[-1] != 'None'):
                    s = s.split(',')
                    pp_id = s[0].split('/')[-1].split('.')[0]
                    app_id = s[1]
                    dist = float(s[2])

                    if(app_id not in output.keys()):
                        output[app_id] = {}

                    output[app_id][pp_id] = dist


            match = {}
            for app in output:
                sorted_obj = list(sorted(output[app].items(), key=lambda x:x[1]))

                if sorted_obj[0][0] in pp_doc_id and app not in match:
                    match[sorted_obj[0][0]] = app
                    pp_doc_id.remove(sorted_obj[0][0])

                else:
                    output, match = recurse(sorted_obj, pp_doc_id, app, output, match)


            unmatched = []        
            [unmatched.append({'doc_id_pht': ap}) if ap not in match.values() else None for ap in app_doc_id]
            [unmatched.append({'doc_id_pp': pp}) for pp in pp_doc_id]
            

            matches = []
            [matches.append({"doc_id_pp": mat, "doc_id_pht": match[mat]}) for mat in match]

            res = {"matches": matches,
                  "unmatched": unmatched}
            
            shutil.rmtree(os.getcwd() + '/photo_match')
            
        else:
            res = {"matches": [],
                  "unmatched": []}
            
        return res
    
    except Exception as e:
        print(e)
        shutil.rmtree(os.getcwd() + '/photo_match')

        return "Some Error Occurred!"


@app.route('/', methods=['GET'])
def init_():
    return 'Hello Visaero!'


if __name__ == '__main__':  
   app.run()