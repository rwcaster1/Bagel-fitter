# -*- coding: utf-8 -*-
# the friendly way to enzyme kinetics 

import pandas 
from numpy import diag, sqrt  
from scipy.optimize import curve_fit

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.pyplot as plt
from StringIO import StringIO 
from base64 import b64encode

from flask import Flask, request, render_template

app = Flask( __name__ )
app.config[ 'UPLOAD_FOLDER' ] = 'uploads' 

def allowed_file( filename ):
  return '.' in filename and filename.rsplit('.', 1)[1] in [ 'txt', 'csv', 'xlsx' ]

def kobs( s, kcat, km ): 
  return (kcat*s)/(km+s)
  #return (kcat*s)/(km+s+(s**2/ki)) 
  #Vmax/E = ( kcat * S ) / ( Km + S + ( S^2 / Ki ) ) 

def do_fit( df ):
  p0 = ( df.kobs.max(), df.s.mean() ) #df.s.mean() ) # guesses  
  popt, pcov = curve_fit( kobs, df.s, df.kobs, p0=p0 ) 
  perr = sqrt( diag( pcov ) )
  for i in [ 0, 1 ]:
    if not popt[ i ] or perr[ i ] > popt[ i ]:
      popt[ i ] = perr[ i ] = None 
    else:
      perr[ i ] = perr[ i ] / popt [ i ] 
  #return { 'kcat': '%.0f ± %.0f%%' % (popt[0], perr[0]*100), 'km': '%.4f ± %.0f%%' % (popt[1], perr[1]*100) } 
  return popt, perr 

# BglB-specific values below! 
s = [ 0.075, 0.01875, 0.0047, 0.0012, 0.0003, 0.000075, 0.000019, 0 ] 
smap2 = dict( zip( 'ABCDEFGH', s ) )  
extcoef = 113000

def assign_groups( df, smap=smap2, extcoef=extcoef ):
  'Adds substrate concentrations and calculates kobs'

  df[ 's' ] = df['well'].str[0].map( smap ) 
  df[ 'kobs' ] = df.rate * 0.0002 / ( df[ 'yield' ] * df[ 'dilution' ] * 0.25 / extcoef ) 
  # 0.25 from the procedure, 0.0002 from standard curve 
  
  return df 

print plt.style.available
plt.style.use('ggplot') 
  
@app.route( '/', methods=['GET', 'POST'] )
def upload_file():
  if request.method == 'POST':
    df = pandas.read_csv( request.files[ 'file' ] ) 
    df = assign_groups( df ) 
    grouped = df.groupby( 'sample' )
    #fits = grouped.apply( fit ) 
    plots = [ ] 
    for name, df in grouped:
      popt, perr = do_fit( df ) 
      fig, ax = plt.subplots() 
      fig.suptitle( name ) 
      ax = plt.scatter( df.s, df.kobs ) 
      img = StringIO() 
      fig.savefig( img ) 
      plt.close( fig )  
      img.seek( 0 )  
      plots.append( ( name, popt, perr, b64encode( img.read() ) ) ) 
    return render_template( 'results.html', plots=plots ) 
  else: 
    return render_template( 'index.html' ) 

if __name__ == '__main__':
  app.run( debug=True ) 
