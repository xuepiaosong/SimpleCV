#!/usr/bin/python

import os, sys
from SimpleCV import * 
from nose.tools import with_setup

testimage = "sampleimages/9dots4lines.png"
testimage2 = "sampleimages/aerospace.jpg"
testimageclr = "sampleimages/statue_liberty.jpg"
testbarcode = "sampleimages/barcode.png"
testoutput = "sampleimages/9d4l.jpg"

def setup_context():
  img = Image(testimage)
  
def destroy_context():
  img = ""

@with_setup(setup_context, destroy_context)
def test_loadsave():
  img = Image(testimage)
  img.save(testoutput)  
  if (os.path.isfile(testoutput)):
    os.remove(testoutput)
    return 1
  else: 
    return 0
  
def test_bitmap():
  img = Image(testimage)
  bmp = img.getBitmap();
  if bmp.width > 0:
    return 1
  else:
    return 0

def test_matrix():
  img = Image(testimage)
  m = img.getMatrix()
  if (m.rows == img.getBitmap().width):
    return 1
  return 0 
  
def test_scale():
  img = Image(testimage)
  thumb = img.scale(30,30)
  thumb.save(testoutput)

def test_getitem():
  img = Image(testimage)
  colors = img[1,1]
  if (colors[0] == 255 and colors[1] == 255 and colors[2] == 255):
    return 1
  else: 
    return 0

def test_getslice():
  img = Image(testimage)
  section = img[1:10,1:10]
  section.save(testoutput)
  return 1


def test_setitem():
  img = Image(testimage)
  img[1,1] = (0, 0, 0)
  newimg = Image(img.getBitmap())
  colors = newimg[1,1]
  if (colors[0] == 0 and colors[1] == 0 and colors[2] == 0):
    return 1
  else:
    return 0

def test_setslice():
  img = Image(testimage)
  img[1:10,1:10] = (0,0,0) #make a black box
  newimg = Image(img.getBitmap())
  section = newimg[1:10,1:10]
  for i in range(5):
    colors = section[i,0]
    if (colors[0] != 0 or colors[1] != 0 or colors[2] != 0):
      return 0  
  return 1

def test_findCorners():
  img = Image(testimage2)
  corners = img.findCorners(25)
  if (len(corners) == 0):
    return 0 
  corners.draw()
  img.save(testoutput)
  
def test_meancolor():
  img = Image(testimage2)
  roi = img[1:50,1:50]
  
  r, g, b = roi.meanColor()

  if (r >= 0 and r <= 255 and g >= 0 and g <= 255 and b >= 0 and b <= 255):
    return 1 

def test_smooth():
  img = Image(testimage2)
  img.smooth()
  img.smooth('bilateral', (3,3), 4, 1)
  img.smooth('blur', (3, 3))
  img.smooth('median', (3, 3))
  img.smooth('gaussian', (5,5), 0) 

def test_size():
  img = Image(testimage2)
  (width, height) = img.size()
  if type(width) == "int" and type(height) == "int" and width > 0 and height > 0:
    return 1
  else:
    return 0

def test_drawing():
  img = Image(testimageclr)
  img.drawCircle((5, 5), 3)
  img.drawLine((5, 5), (5, 8))
  
def test_channels():  
  img = Image(testimageclr)
  (r, g, b) = img.channels(True)
  (red, green, blue) = img.channels()

def test_histogram():
  img = Image(testimage2)
  h = img.histogram(25)

  for i in h:
    if type(i) != "int":
      return 0

  return 1

def test_blobs():
  if not BLOBS_ENABLED:
    return None 
  img = Image(testimage2)
  blobs = img.findBlobs()

  blobs[0].draw((0, 255, 0))
  img.save(testoutput)

  return 1

def test_barcode():
  if not ZXING_ENABLED:
    return None

  nocode = Image(testimage).findBarcode()
  if nocode: #we should find no barcode in our test image 
    return 0
  code = Image(testbarcode).findBarcode() 
  
  if code.points:
    return 1

#def test_lossy_store():
#  img = Image(testimage2)
#
#  small_image = img.scale(img.width / 15, img.height / 15) 
  
  





"""
def test_Harris(img):
  for (x,y) in cv.GoodFeaturesToTrack(img, eig_image, temp_image, 10, 0.04, 1.0, useHarris = True):
    cv.Circle(img, (x,y), 4, 0);
    print "good feature at", x,y

def test_Canny():
  img = cv.LoadImageM("sampleimages/9dots4lines.png", cv.CV_LOAD_IMAGE_GRAYSCALE)
  eig_image = cv.CreateMat(img.rows, img.cols, cv.CV_32FC1)
  temp_image = cv.CreateMat(img.rows, img.cols, cv.CV_32FC1)
  cv.Canny(img, temp_image, 10, 100, 11);
  cv.SaveImage("sampleimages/9d4lfeatures.png", temp_image);

def main(argv):
  test_getslice()

if (__name__ == "__main__"):
  main(sys.argv)

"""

test_drawing()
