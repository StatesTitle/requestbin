import requests
import urllib
from flask import session, redirect, url_for, escape, request, render_template, make_response, Response

from requestbin import app, db

def update_recent_bins(name):
    if 'recent' not in session:
        session['recent'] = []
    if name in session['recent']:
        session['recent'].remove(name)
    session['recent'].insert(0, name)
    if len(session['recent']) > 10:
        session['recent'] = session['recent'][:10]
    session.modified = True


def expand_recent_bins():
    if 'recent' not in session:
        session['recent'] = []
    recent = []
    for name in session['recent']:
        try:
            recent.append(db.lookup_bin(name))
        except KeyError:
            session['recent'].remove(name)
            session.modified = True
    return recent

@app.endpoint('views.home')
def home():
    return render_template('home.html', recent=expand_recent_bins())


@app.endpoint('views.bin')
def bin(name, rest=None):
    try:
        bin = db.lookup_bin(name)
    except KeyError:
        return "Not found\n", 404
    if request.query_string == 'inspect':
        if bin.private and session.get(bin.name) != bin.secret_key:
            return "Private bin\n", 403
        update_recent_bins(name)
        return render_template('bin.html',
            bin=bin,
            base_url=request.scheme+'://'+request.host)
    else:
        db.create_request(bin, request)
        #return make_response("ok\n")
        return _proxy(name, rest)


proxy_host = 'st-resware-requestbin.herokuapp.com'
#proxy_host = 'localhost:4000'
def _proxy(name, rest):
    new_headers = {}
    excluded_headers = ['host', 'content-length', 'transfer-encoding', 'connection']
    for key, value in request.headers:
        if key.lower() not in excluded_headers:
            new_headers[key] = value
    new_url = request.url.replace(proxy_host, '52.36.64.165').replace('/' + name, '')
    print("proxying from", request.url, 'to', new_url, name)
    print("req", request.get_data(), new_headers)
    resp = requests.request(
        method=request.method,
        url=new_url,
        headers=new_headers,
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False)

    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items()
               if name.lower() not in excluded_headers]

    response = Response(resp.content, resp.status_code, headers)
    print(resp.content)
    return response


@app.endpoint('views.docs')
def docs(name):
    doc = db.lookup_doc(name)
    if doc:
        return render_template('doc.html',
                content=doc['content'],
                title=doc['title'],
                recent=expand_recent_bins())
    else:
        return "Not found", 404
