# SimpleCV Image Object

#load required libraries
from SimpleCV.base import *
from SimpleCV.Detection import Barcode, Blob, Corner, HaarFeature, Line, Chessboard
from SimpleCV.Features import FeatureSet
from SimpleCV.Stream import JpegStreamer

class Image:
  """
  The Image class is the heart of SimpleCV and allows you to convert to and 
  from a number of source types with ease.  It also has intelligent buffer
  management, so that modified copies of the Image required for algorithms
  such as edge detection, etc can be cached and reused when appropriate.

  Images are converted into 8-bit, 3-channel images in RGB colorspace.  It will
  automatically handle conversion from other representations into this
  standard format. 
  """
  width = 0    #width and height in px
  height = 0
  depth = 0
  filename = "" #source filename
  filehandle = "" #filehandle if used

  _barcodeReader = "" #property for the ZXing barcode reader

  #these are buffer frames for various operations on the image
  _bitmap = ""  #the bitmap (iplimage)  representation of the image
  _matrix = ""  #the matrix (cvmat) representation
  _grayMatrix = "" #the gray scale (cvmat) representation -KAS
  _graybitmap = ""  #a reusable 8-bit grayscale bitmap
  _equalizedgraybitmap = "" #the above bitmap, normalized
  _blobLabel = ""  #the label image for blobbing
  _edgeMap = "" #holding reference for edge map
  _cannyparam = (0,0) #parameters that created _edgeMap
  _pil = "" #holds a PIL object in buffer

  #when we empty the buffers, populate with this:
  _initialized_buffers = { 
    "_bitmap": "", 
    "_matrix": "", 
    "_grayMatrix": "",
    "_graybitmap": "", 
    "_equalizedgraybitmap": "",
    "_blobLabel": "",
    "_edgeMap": "",
    "_cannyparam": (0,0), 
    "_pil": ""}  
    
  #initialize the frame
  #parameters: source designation (filename)
  #todo: handle camera/capture from file cases (detect on file extension)
  def __init__(self, source = None):
    """ 
    The constructor takes a single polymorphic parameter, which it tests
    to see how it should convert into an RGB image.  Supported types include:
    
    OpenCV: iplImage and cvMat types
    Python Image Library: Image type
    Filename: All opencv supported types (jpg, png, bmp, gif, etc)
    """
    if (type(source) == cv.cvmat):
      self._matrix = source 

    elif (type(source) == np.ndarray):  #handle a numpy array conversion
      if (type(source[0,0]) == np.ndarray): #we have a 3 channel array
        #convert to an iplimage bitmap
        source = source.astype(np.uint8)
        self._bitmap = cv.CreateImageHeader((source.shape[1], source.shape[0]), cv.IPL_DEPTH_8U, 3)
        cv.SetData(self._bitmap, source.tostring(), 
          source.dtype.itemsize * 3 * source.shape[1])
      else:
        #we have a single channel array, convert to an RGB iplimage

        source = source.astype(np.uint8) 
        self._bitmap = cv.CreateImage(cv.GetSize(source), cv.IPL_DEPTH_8U, 3) 
        channel = cv.CreateImageHeader((source.shape[1], source.shape[0]), cv.IPL_DEPTH_8U, 1)
        #initialize an empty channel bitmap
        cv.SetData(channel, source.tostring(), 
          source.dtype.itemsize * source.shape[1])
        cv.Merge(source, source, source, None, self._bitmap)

    elif (type(source) == cv.iplimage):
      if (source.nChannels == 1):
        self._bitmap = cv.CreateImage(cv.GetSize(source), cv.IPL_DEPTH_8U, 3) 
        cv.Merge(source, source, source, None, self._bitmap)
      else:
        self._bitmap = source
    elif (type(source) == type(str()) and source != ''):
      self.filename = source
      self._bitmap = cv.LoadImage(self.filename, iscolor=cv.CV_LOAD_IMAGE_COLOR) 
    elif (PIL_ENABLED and source.__class__.__name__ == "JpegImageFile"):
      self._pil = source
      #from the opencv cookbook 
      #http://opencv.willowgarage.com/documentation/python/cookbook.html
      self._bitmap = cv.CreateImageHeader(self._pil.size, cv.IPL_DEPTH_8U, 3)
      cv.SetData(self._bitmap, self._pil.tostring())
      #self._bitmap = cv.iplimage(self._bitmap)

    else:
      return None 

    bm = self.getBitmap()
    self.width = bm.width
    self.height = bm.height
    self.depth = bm.depth
 
  def getEmpty(self, channels = 3):
    """
    Create a new, empty OpenCV bitmap with the specified number of channels (default 3)h
    """
    bitmap = cv.CreateImage(self.size(), cv.IPL_DEPTH_8U, channels)
    cv.SetZero(bitmap)
    return bitmap

  def getBitmap(self):
    """
    Retrieve the bitmap (iplImage) of the Image.  This is useful if you want
    to use functions from OpenCV with SimpleCV's image class
    """
    if (self._bitmap):
      return self._bitmap
    elif (self._matrix):
      self._bitmap = cv.GetImage(self._matrix)

    return self._bitmap

  def getMatrix(self):
    """
    Get the matrix (cvMat) version of the image, required for some OpenCV algorithms 
    """
    if (self._matrix):
      return self._matrix
    else:
      self._matrix = cv.GetMat(self.getBitmap()) #convert the bitmap to a matrix
      return self._matrix

  def getPIL(self):
    """ 
    Get a PIL Image object for use with the Python Image Library
    """ 
    if (not PIL_ENABLED):
      return None
    if (not self._pil):
      rgbbitmap = self.getEmpty()
      cv.CvtColor(self.getBitmap(), rgbbitmap, cv.CV_BGR2RGB)
      self._pil = pil.fromstring("RGB", self.size(), rgbbitmap.tostring())
    return self._pil

  def _getGrayscaleBitmap(self):
    if (self._graybitmap):
      return self._graybitmap

    self._graybitmap = self.getEmpty(1) 
    cv.CvtColor(self.getBitmap(), self._graybitmap, cv.CV_BGR2GRAY) 
    return self._graybitmap

  def getGrayscaleMatrix(self):
   """
   Returns the intensity grayscale matrix
   """
   if (self._grayMatrix):
     return self._grayMatrix
   else:
     self._grayMatrix = cv.GetMat(self._getGrayscaleBitmap()) #convert the bitmap to a matrix
     return self._grayMatrix
    
  def _getEqualizedGrayscaleBitmap(self):

    if (self._equalizedgraybitmap):
      return self._equalizedgraybitmap

    self._equalizedgraybitmap = self.getEmpty(1) 
    cv.EqualizeHist(self._getGrayscaleBitmap(), self._equalizedgraybitmap)

    return self._equalizedgraybitmap
    
  def save(self, filehandle_or_filename="", mode=""):
    """
    Save the image to the specified filename.  If no filename is provided then
    then it will use the filename the Image was loaded from or the last
    place it was saved to. 
    """
    if (not filehandle_or_filename):
      if (self.filename):
        filehandle_or_filename = self.filename
      else:
        filehandle_or_filename = self.filehandle


    if (type(filehandle_or_filename) != str):
      fh = filehandle_or_filename


      if (not PIL_ENABLED):
        warnings.warn("You need the python image library to save by filehandle")
        return 0

      if (type(fh) == InstanceType and fh.__class__.__name__ == "JpegStreamer"):
        fh.jpgdata = StringIO() 
        self.getPIL().save(fh.jpgdata, "jpeg") #save via PIL to a StringIO handle 
        fh.refreshtime = time.time()
        self.filename = "" 
        self.filehandle = fh

      elif (type(fh) == InstanceType and fh.__class__.__name__ == "VideoStream"):
        self.filename = "" 
        self.filehandle = fh
        fh.writeFrame(self)

      else:      
        if (not mode):
          mode = "jpeg"
      
        self.getPIL().save(fh, mode)
        self.filehandle = fh #set the filename for future save operations
        self.filename = ""
        
      return 1

    filename = filehandle_or_filename 
    if (filename):
      cv.SaveImage(filename, self.getBitmap())  
      self.filename = filename #set the filename for future save operations
      self.filehandle = ""
    elif (self.filename):
      cv.SaveImage(self.filename, self.getBitmap())
    else:
      return 0

    return 1

  def copy(self):
    """
    Return a full copy of the Image's bitmap.  Note that this is different
    from using python's implicit copy function in that only the bitmap itself
    is copied.

    Returns: IMAGE
    """
    newimg = self.getEmpty() 
    cv.Copy(self.getBitmap(), newimg)
    return Image(newimg) 
    
  #scale this image, and return a new Image object with the new dimensions 
  def scale(self, width, height):
    """
    Scale the image to a new width and height.

    Returns: IMAGE
    """
    scaled_bitmap = cv.CreateImage((width, height), 8, 3)
    cv.Resize(self.getBitmap(), scaled_bitmap)
    return Image(scaled_bitmap)

  def smooth(self, algorithm_name = 'gaussian', aperature = '', sigma = 0, spatial_sigma = 0):
    """
    Smooth the image, by default with the Gaussian blur.  If desired,
    additional algorithms and aperatures can be specified.  Optional parameters
    are passed directly to OpenCV's cv.Smooth() function.

    Returns: IMAGE
    """
    win_x = 3
    win_y = 3  #set the default aperature window size (3x3)

    if (is_tuple(aperature)):
      win_x, win_y = aperature#get the coordinates from parameter
      #TODO: make sure aperature is valid 
      #   eg Positive, odd and square for bilateral and median

    algorithm = cv.CV_GAUSSIAN #default algorithm is gaussian 

    #gauss and blur can work in-place, others need a buffer frame
    #use a string to ID rather than the openCV constant
    if algorithm_name == "blur":
      algorithm = cv.CV_BLUR
    if algorithm_name == "bilateral":
      algorithm = cv.CV_BILATERAL
      win_y = win_x #aperature must be square
    if algorithm_name == "median":
      algorithm = cv.CV_MEDIAN
      win_y = win_x #aperature must be square

    newimg = self.getEmpty(1) 
    cv.Smooth(self._getGrayscaleBitmap(), newimg, algorithm, win_x, win_y, sigma, spatial_sigma)

    return Image(newimg)

  def medianFilter(self,window=''):
    """
    Perform a median filtering operation to denoise/despeckle the image.
    The optional parameter is the window size.
    """
    return self.smooth(algorithm_name='median',aperature=window)
    
  def bilateralFilter(self,window = ''):
    """
    Perform a bilateral filtering operation to denoise/despeckle the image.
    The optional parameter is the window size.
    """
    return self.smooth(algorithm_name='bilateral',aperature=window)
    
  def invert(self):
    """
    Invert (negative) the image note that this can also be done with the
    unary minus (-) operator.

    Returns: IMAGE
    """
    return -self 

  def grayscale(self):
    """
    return a gray scale version of the image

    Returns: IMAGE
    """
    return Image(self._getGrayscaleBitmap())

  def flipHorizontal(self):
    """
    Horizontally mirror an image

    Returns: IMAGE
    """
    newimg = self.getEmpty()
    cv.Flip(self.getBitmap(), newimg, 1)
    return Image(newimg) 

  def flipVertical(self):
    """
    Vertically mirror an image

    Returns: IMAGE
    """
    newimg = self.getEmpty()
    cv.Flip(self.getBitmap(), newimg, 0)
    return Image(newimg) 
    
    
    
  def stretch(self, thresh_low = 0, thresh_high = 255):
    """
    The stretch filter works on a greyscale image, if the image
    is color, it returns a greyscale image.  The filter works by
    taking in a lower and upper threshold.  Anything below the lower
    threshold is pushed to black (0) and anything above the upper
    threshold is pushed to white (255)

    Returns: IMAGE
    """
    try:
      newimg = self.getEmpty() 
      cv.Threshold(self._getGrayscaleBitmap(), newimg, thresh_low, thresh_high, cv.CV_THRESH_TRUNC)
      return Image(newimg)
    except:
      return None
      
  def binarize(self, thresh = -1, maxv = 255, blocksize = 3, p = 5):
    """
    Do a binary threshold the image, changing all values above thresh to maxv
    and all below to black.  If a color tuple is provided, each color channel
    is thresholded separately.
    
    If threshold is -1, an adaptive sampling method is used - similar to a moving
    average.  Over each region of block*block pixels a threshold is applied
    where threshold = local_mean - p.
    """
    if (is_tuple(thresh)):
      r = self.getEmpty(1) 
      g = self.getEmpty(1)
      b = self.getEmpty(1)
      cv.Split(self.getBitmap(), b, g, r, None)

      cv.Threshold(r, r, thresh[0], maxv, cv.CV_THRESH_BINARY)
      cv.Threshold(g, g, thresh[1], maxv, cv.CV_THRESH_BINARY)
      cv.Threshold(b, b, thresh[2], maxv, cv.CV_THRESH_BINARY)

      cv.Add(r, g, r)
      cv.Add(r, b, r)
      
      return Image(r)

    elif thresh == -1:
      newbitmap = self.getEmpty(1)
      cv.AdaptiveThreshold(self._getGrayscaleBitmap(), newbitmap, float(maxv),
        cv.CV_ADAPTIVE_THRESH_MEAN_C, cv.CV_THRESH_BINARY, blocksize, float(p))
      return Image(newbitmap)
    else:
      newbitmap = self.getEmpty(1) 
      #desaturate the image, and apply the new threshold          
      cv.Threshold(self._getGrayscaleBitmap(), newbitmap, thresh, float(maxv), cv.CV_THRESH_BINARY)
      return Image(newbitmap)
  
  
  def meanColor(self):
    """
    Finds average color of all the pixels in the image.

    Returns: IMAGE
    """
    return cv.Avg(self.getMatrix())[0:3]  
  

  def findCorners(self, maxnum = 50, minquality = 0.04, mindistance = 1.0):
    """
    This will find corner Feature objects and return them as a FeatureSet
    strongest corners first.  The parameters give the number of corners to look
    for, the minimum quality of the corner feature, and the minimum distance
    between corners.

    Returns: FEATURESET 
    """
    #initialize buffer frames
    eig_image = cv.CreateImage(cv.GetSize(self.getBitmap()), cv.IPL_DEPTH_32F, 1)
    temp_image = cv.CreateImage(cv.GetSize(self.getBitmap()), cv.IPL_DEPTH_32F, 1)

    corner_coordinates = cv.GoodFeaturesToTrack(self._getGrayscaleBitmap(), eig_image, temp_image, maxnum, minquality, mindistance, None)

    corner_features = []   
    for (x,y) in corner_coordinates:
      corner_features.append(Corner(self, x, y))

    return FeatureSet(corner_features)

    
  def findBlobs(self, threshval = -1, minsize=10, maxsize=0, threshblocksize=3, threshconstant=5):
    """
    If you have the cvblob library installed, this will look for continuous
    light regions and return them as Blob features in a FeatureSet.  Parameters
    specify the binarize filter threshold value, and minimum and maximum size for blobs.  If a
    threshold value is -1, it will use an adaptive threshold.  See binarize() for
    more information about adaptive thresholding.  The threshblocksize and threshconstant
    parameters are only used for adaptive threshold.

    You can find the cv-blob python library at http://github.com/oostendo/cvblob-python

    Returns: FEATURESET
    """
    if not BLOBS_ENABLED:
      warnings.warn("You tried to use findBlobs, but cvblob is not installed.  Go to http://github.com/oostendo/cvblob-python and git clone it.")
      return None

    if (maxsize == 0):  
      maxsize = self.width * self.height / 2
    
    #create a single channel image, thresholded to parameters
    grey = self.binarize(threshval, 255, threshblocksize, threshconstant)._getGrayscaleBitmap()

    #create the label image
    self._blobLabel = cv.CreateImage(cv.GetSize(self.getBitmap()), cvb.IPL_DEPTH_LABEL, 1)

    #initialize the cvblobs blobs data structure (dict with label -> blob)
    blobs = cvb.Blobs()

    result = cvb.Label(grey, self._blobLabel, blobs)
    cvb.FilterByArea(blobs, minsize, maxsize) 

    blobs_sizesorted = sorted(blobs.values(), key=lambda x: x.area, reverse=True) 

    blobsFS = [] #create a new featureset for the blobs
    for b in blobs_sizesorted:
      blobsFS.append(Blob(self,b)) #wrapper the cvblob type in SimpleCV's blob type 

    return FeatureSet(blobsFS) 

  #this code is based on code that's based on code from
  #http://blog.jozilla.net/2008/06/27/fun-with-python-opencv-and-face-detection/
  def findHaarFeatures(self, cascadefile, scale_factor=1.2, min_neighbors=2, use_canny=cv.CV_HAAR_DO_CANNY_PRUNING):
    """
    If you want to find Haar Features (useful for face detection among other
    purposes) this will return Haar feature objects in a FeatureSet.  The
    parameters are:
    * the scaling factor for subsequent rounds of the haar cascade (default 1.2)7
    * the minimum number of rectangles that makes up an object (default 2)
    * whether or not to use Canny pruning to reject areas with too many edges (default yes, set to 0 to disable) 

    For more information, consult the cv.HaarDetectObjects documentation
   
    You will need to provide your own cascade file - these are usually found in
    /usr/local/share/opencv/haarcascades and specify a number of body parts.

    Returns: FEATURESET
    """
    storage = cv.CreateMemStorage(0)

    #lovely.  This segfaults if not present
    if (not os.path.exists(cascadefile)):
      warnings.warn("Could not find Haar Cascade file " + cascadefile)
      return None
    cascade = cv.Load(cascadefile) 
    objects = cv.HaarDetectObjects(self._getEqualizedGrayscaleBitmap(), cascade, storage, scale_factor, use_canny)
    if objects: 
      return FeatureSet([HaarFeature(self, o, cascadefile) for o in objects])
    
    return None

  def drawCircle(self, ctr, rad, color = (0,0,0), thickness = 1):
    """
    Draw a circle on the Image, parameters include:
    * the center of the circle
    * the radius in pixels
    * a color tuple (default black)
    * the thickness of the circle

    Note that this modifies the image in-place and clears all buffers.

    Returns: NONE - Inline Operation
    """
    cv.Circle(self.getBitmap(), (int(ctr[0]), int(ctr[1])), rad, reverse_tuple(color), thickness)
    self._clearBuffers("_bitmap")

  def drawLine(self, pt1, pt2, color = (0,0,0), thickness = 1):
    """
    Draw a line on the Image, parameters include
    * pt1 - the first point for the line (tuple)
    * pt1 - the second point on the line (tuple)
    * a color tuple (default black)
    * thickness of the line 
 
    Note that this modifies the image in-place and clears all buffers.

    Returns: NONE - Inline Operation
    """
    pt1 = (int(pt1[0]), int(pt1[1]))
    pt2 = (int(pt2[0]), int(pt2[1]))
    cv.Line(self.getBitmap(), pt1, pt2, reverse_tuple(color), thickness, cv.CV_AA)

    

  def size(self):
    """
    Gets width and height

    Returns: TUPLE
    """
    return cv.GetSize(self.getBitmap())

  def splitChannels(self, grayscale = True):
    """
    Split the channels of an image into RGB (not the default BGR)
    single parameter is whether to return the channels as grey images (default)
    or to return them as tinted color image 

    Returns: TUPLE - of 3 image objects
    """
    r = self.getEmpty(1) 
    g = self.getEmpty(1) 
    b = self.getEmpty(1) 
    cv.Split(self.getBitmap(), b, g, r, None)

    red = self.getEmpty() 
    green = self.getEmpty() 
    blue = self.getEmpty() 
	
    if (grayscale):
      cv.Merge(r, r, r, None, red)
      cv.Merge(g, g, g, None, green)
      cv.Merge(b, b, b, None, blue)
    else:
      cv.Merge(None, None, r, None, red)
      cv.Merge(None, g, None, None, green)
      cv.Merge(b, None, None, None, blue)

    return (Image(red), Image(green), Image(blue)) 

  def applyHLSCurve(self, hCurve, lCurve, sCurve):
    """
    Apply 3 ColorCurve corrections applied in HSL space
    Parameters are: 
    * Hue ColorCurve 
    * Lightness (brightness/value) ColorCurve
    * Saturation ColorCurve

    Returns: IMAGE
    """
  
    #TODO CHECK ROI
    #TODO CHECK CURVE SIZE
    #TODO CHECK COLORSPACE
    #TODO CHECK CURVE SIZE
    temp  = cv.CreateImage(self.size(), 8, 3)
    #Move to HLS space
    cv.CvtColor(self._bitmap,temp,cv.CV_RGB2HLS)
    tempMat = cv.GetMat(temp) #convert the bitmap to a matrix
    #now apply the color curve correction
    tempMat = np.array(self.getMatrix()).copy()
    tempMat[:,:,0] = np.take(hCurve.mCurve,tempMat[:,:,0])
    tempMat[:,:,1] = np.take(sCurve.mCurve,tempMat[:,:,1])
    tempMat[:,:,2] = np.take(lCurve.mCurve,tempMat[:,:,2])
    #Now we jimmy the np array into a cvMat
    image = cv.CreateImageHeader((tempMat.shape[1], tempMat.shape[0]), cv.IPL_DEPTH_8U, 3)
    cv.SetData(image, tempMat.tostring(), tempMat.dtype.itemsize * 3 * tempMat.shape[1])
    cv.CvtColor(image,image,cv.CV_HLS2RGB)  
    return Image(image)

  def applyRGBCurve(self, rCurve, gCurve, bCurve):
    """
    Apply 3 ColorCurve corrections applied in rgb channels 
    Parameters are: 
    * Red ColorCurve 
    * Green ColorCurve
    * Blue ColorCurve

    Returns: IMAGE
    """
    tempMat = np.array(self.getMatrix()).copy()
    tempMat[:,:,0] = np.take(bCurve.mCurve,tempMat[:,:,0])
    tempMat[:,:,1] = np.take(gCurve.mCurve,tempMat[:,:,1])
    tempMat[:,:,2] = np.take(rCurve.mCurve,tempMat[:,:,2])
    #Now we jimmy the np array into a cvMat
    image = cv.CreateImageHeader((tempMat.shape[1], tempMat.shape[0]), cv.IPL_DEPTH_8U, 3)
    cv.SetData(image, tempMat.tostring(), tempMat.dtype.itemsize * 3 * tempMat.shape[1])
    return Image(image)

  def applyIntensityCurve(self, curve):
    """
    Intensity applied to all three color channels

    Returns: Image
    """
    return self.applyRGBCurve(curve, curve, curve)
      
  def erode(self, iterations=1):
    """
    Apply a morphological erosion. An erosion has the effect of removing small bits of noise
    and smothing blobs. 
    This implementation uses the default openCV 3X3 square kernel 
    Erosion is effectively a local minima detector, the kernel moves over the image and
    takes the minimum value inside the kernel. 
    iterations - this parameters is the number of times to apply/reapply the operation
    See: http://en.wikipedia.org/wiki/Erosion_(morphology).
    See: http://opencv.willowgarage.com/documentation/cpp/image_filtering.html#cv-erode 
    Example Use: A threshold/blob image has 'salt and pepper' noise. 
    Example Code: ./examples/MorphologyExample.py

    Returns: IMAGE
    """
    retVal = self.getEmpty() 
    kern = cv.CreateStructuringElementEx(3,3,1,1,cv.CV_SHAPE_RECT)
    cv.Erode(self.getBitmap(),retVal,kern,iterations)
    return( Image(retVal) )

  def dilate(self, iterations=1):
    """
    Apply a morphological dilation. An dilation has the effect of smoothing blobs while
    intensifying the amount of noise blobs. 
    This implementation uses the default openCV 3X3 square kernel 
    Erosion is effectively a local maxima detector, the kernel moves over the image and
    takes the maxima value inside the kernel. 

    iterations - this parameters is the number of times to apply/reapply the operation

    See: http://en.wikipedia.org/wiki/Dilation_(morphology)
    See: http://opencv.willowgarage.com/documentation/cpp/image_filtering.html#cv-dilate
    Example Use: A part's blob needs to be smoother 
    Example Code: ./examples/MorphologyExample.py

    Returns: IMAGE
    """
    retVal = self.getEmpty() 
    kern = cv.CreateStructuringElementEx(3,3,1,1,cv.CV_SHAPE_RECT)
    cv.Dilate(self.getBitmap(),retVal,kern,iterations)
    return( Image(retVal) )

  def morphOpen(self):
    """
    morphologyOpen applies a morphological open operation which is effectively
    an erosion operation followed by a morphological dilation. This operation
    helps to 'break apart' or 'open' binary regions which are close together. 

    See: http://en.wikipedia.org/wiki/Opening_(morphology)
    See: http://opencv.willowgarage.com/documentation/cpp/image_filtering.html#cv-morphologyex
    Example Use: two part blobs are 'sticking' together.
    Example Code: ./examples/MorphologyExample.py

    Returns: IMAGE
    """
    retVal = self.getEmpty() 
    temp = self.getEmpty()
    kern = cv.CreateStructuringElementEx(3,3,1,1,cv.CV_SHAPE_RECT)
    cv.MorphologyEx(self.getBitmap(),retVal,temp,kern,cv.MORPH_OPEN,1)
    return( Image(retVal) )


  def morphClose(self):
    """
    morphologyClose applies a morphological close operation which is effectively
    a dilation operation followed by a morphological erosion. This operation
    helps to 'bring together' or 'close' binary regions which are close together. 

    See: http://en.wikipedia.org/wiki/Closing_(morphology)
    See: http://opencv.willowgarage.com/documentation/cpp/image_filtering.html#cv-morphologyex
    Example Use: Use when a part, which should be one blob is really two blobs.   
    Example Code: ./examples/MorphologyExample.py

    Returns: IMAGE
    """
    retVal = self.getEmpty() 
    temp = self.getEmpty()
    kern = cv.CreateStructuringElementEx(3,3,1,1,cv.CV_SHAPE_RECT)
    cv.MorphologyEx(self.getBitmap(),retVal,temp,kern,cv.MORPH_CLOSE,1)
    return( Image(retVal) )

  def morphGradient(self):
    """
    The morphological gradient is the difference betwen the morphological
    dilation and the morphological gradient. This operation extracts the 
    edges of a blobs in the image. 

    See: http://en.wikipedia.org/wiki/Morphological_Gradient
    See: http://opencv.willowgarage.com/documentation/cpp/image_filtering.html#cv-morphologyex
    Example Use: Use when you have blobs but you really just want to know the blob edges.
    Example Code: ./examples/MorphologyExample.py

    Returns: IMAGE
    """
    retVal = self.getEmpty() 
    retVal = self.getEmpty() 
    temp = self.getEmpty()
    kern = cv.CreateStructuringElementEx(3,3,1,1,cv.CV_SHAPE_RECT)
    cv.MorphologyEx(self.getBitmap(),retVal,temp,kern,cv.MORPH_GRADIENT,1)
    return( Image(retVal) )

  def histogram(self, numbins = 50):
    """
    Return a numpy array of the 1D histogram of intensity for pixels in the image
    Single parameter is how many "bins" to have.

    Returns: LIST
    """
    gray = self._getGrayscaleBitmap()

    (hist, bin_edges) = np.histogram(np.asarray(cv.GetMat(gray)), bins=numbins)
    return hist.tolist()

  def __getitem__(self, coord):
    ret = self.getMatrix()[tuple(reversed(coord))]
    if (type(ret) == cv.cvmat):
      (width, height) = cv.GetSize(ret)
      newmat = cv.CreateMat(height, width, ret.type)
      cv.Copy(ret, newmat) #this seems to be a bug in opencv
      #if you don't copy the matrix slice, when you convert to bmp you get
      #a slice-sized hunk starting at 0,0
      return Image(newmat)
    return tuple(reversed(ret))

  def __setitem__(self, coord, value):
    value = tuple(reversed(value))  #RGB -> BGR
    if (is_tuple(self.getMatrix()[tuple(reversed(coord))])):
      self.getMatrix()[coord] = value 
    else:
      cv.Set(self.getMatrix()[tuple(reversed(coord))], value)
      self._clearBuffers("_matrix") 

  def __sub__(self, other):
    newbitmap = self.getEmpty() 
    if is_number(other):
      cv.SubS(self.getBitmap(), other, newbitmap)
    else:
      cv.Sub(self.getBitmap(), other.getBitmap(), newbitmap)
    return Image(newbitmap)

  def __add__(self, other):
    newbitmap = self.getEmpty() 
    if is_number(other):
      cv.AddS(self.getBitmap(), other, newbitmap)
    else:
      cv.Add(self.getBitmap(), other.getBitmap(), newbitmap)
    return Image(newbitmap)

  def __and__(self, other):
    newbitmap = self.getEmpty() 
    if is_number(other):
      cv.AndS(self.getBitmap(), other, newbitmap)
    else:
      cv.And(self.getBitmap(), other.getBitmap(), newbitmap)
    return Image(newbitmap)

  def __or__(self, other):
    newbitmap = self.getEmpty() 
    if is_number(other):
      cv.OrS(self.getBitmap(), other, newbitmap)
    else:
      cv.Or(self.getBitmap(), other.getBitmap(), newbitmap)
    return Image(newbitmap)

  def __div__(self, other):
    newbitmap = self.getEmpty() 
    if (not is_number(other)):
      cv.Div(self.getBitmap(), other.getBitmap(), newbitmap)
    else:
      cv.ConvertScale(self.getBitmap(), newbitmap, 1.0/float(other))
    return Image(newbitmap)

  def __mul__(self, other):
    newbitmap = self.getEmpty() 
    if (not is_number(other)):
      cv.Mul(self.getBitmap(), other.getBitmap(), newbitmap)
    else:
      cv.ConvertScale(self.getBitmap(), newbitmap, float(other))
    return Image(newbitmap)

  def __pow__(self, other):
    newbitmap = self.getEmpty() 
    cv.Pow(self.getBitmap(), newbitmap, other)
    return Image(newbitmap)

  def __neg__(self):
    newbitmap = self.getEmpty() 
    cv.Not(self.getBitmap(), newbitmap)
    return Image(newbitmap)

  def max(self, other):
    """
    The maximum value of my image, and the other image, in each channel
    If other is a number, returns the maximum of that and the number

    Returns: IMAGE
    """ 
    newbitmap = self.getEmpty() 
    if is_number(other):
      cv.MaxS(self.getBitmap(), other.getBitmap(), newbitmap)
    else:
      cv.Max(self.getBitmap(), other.getBitmap(), newbitmap)
    return Image(newbitmap)

  def min(self, other):
    """
    The minimum value of my image, and the other image, in each channel
    If other is a number, returns the minimum of that and the number

    Returns: IMAGE
    """ 
    newbitmap = self.getEmpty() 
    if is_number(other):
      cv.MaxS(self.getBitmap(), other.getBitmap(), newbitmap)
    else:
      cv.Max(self.getBitmap(), other.getBitmap(), newbitmap)
    return Image(newbitmap)

  def _clearBuffers(self, clearexcept = "_bitmap"):
    for k, v in self._initialized_buffers.items():
      if k == clearexcept:
        continue
      self.__dict__[k] = v

  def findBarcode(self, zxing_path = ""):
    """
    If you have the python-zxing library installed, you can find 2d and 1d
    barcodes in your image.  These are returned as Barcode feature objects
    in a FeatureSet.  The single parameter is the ZXing_path, if you 
    don't have the ZXING_LIBRARY env parameter set.

    You can clone python-zxing at http://github.com/oostendo/python-zxing

    Returns: BARCODE
    """
    if not ZXING_ENABLED:
      return None

    if (not self._barcodeReader):
      if not zxing_path:
        self._barcodeReader = zxing.BarCodeReader()
      else:
        self._barcodeReader = zxing.BarCodeReader(zxing_path)

    tmp_filename = os.tmpnam() + ".png"
    self.save(tmp_filename)
    barcode = self._barcodeReader.decode(tmp_filename)
    os.unlink(tmp_filename)

    if barcode:
      return Barcode(self, barcode)
    else:
      return None

  #this function contains two functions -- the basic edge detection algorithm
  #and then a function to break the lines down given a threshold parameter
  def findLines(self, threshold=80, minlinelength=30, maxlinegap=10, cannyth1=50, cannyth2=100):
    """
    findLines will find line segments in your image and returns Line feature 
    objects in a FeatureSet. The parameters are:
    * threshold, which determies the minimum "strength" of the line
    * min line length -- how many pixels long the line must be to be returned
    * max line gap -- how much gap is allowed between line segments to consider them the same line 
    * cannyth1 and cannyth2 are thresholds used in the edge detection step, refer to _getEdgeMap() for details

    For more information, consult the cv.HoughLines2 documentation

    Returns: FEATURESET
    """
    em = self._getEdgeMap(cannyth1, cannyth2)
    
    lines = cv.HoughLines2(em, cv.CreateMemStorage(), cv.CV_HOUGH_PROBABILISTIC, 1.0, cv.CV_PI/180.0, threshold, minlinelength, maxlinegap)

    linesFS = FeatureSet()
    for l in lines:
      linesFS.append(Line(self, l))  
    
    return linesFS
    
  def findChessboard(self, dimensions = (5,8)):
    """
    Given an image, finds a chessboard within that image.  Returns the Chessboard featureset.
    The Chessboard is typically used for calibration because of its evenly spaced corners.
    
    The single parameter is the dimensions of the chessboard, typical one can be found in \SimpleCV\tools\CalibGrid.png
   
    returns a FeatureSet with the Chessboard feature, or none
    """
    corners = cv.FindChessboardCorners(self.getGrayscaleMatrix(), dimensions, cv.CALIB_CB_ADAPTIVE_THRESH + cv.CALIB_CB_NORMALIZE_IMAGE + cv.CALIB_CB_FAST_CHECK )
    if(len(corners[1]) == dimensions[0]*dimensions[1]):
      spCorners = cv.FindCornerSubPix(self.getGrayscaleMatrix(),corners[1],(11,11),(-1,-1), (cv.CV_TERMCRIT_ITER | cv.CV_TERMCRIT_EPS, 10, 0.01))
      return FeatureSet([ Chessboard(self, dimensions, spCorners) ])
    else:
      return None

  def edges(self, t1=50, t2=100):
    """
    Finds an edge map Image using the Canny edge detection method.  Edges will be brighter than the surrounding area.

    The t1 parameter is roughly the "strength" of the edge required, and the value between t1 and t2 is used for edge linking.  For more information:

    <http://opencv.willowgarage.com/documentation/python/imgproc_feature_detection.html>
    <http://en.wikipedia.org/wiki/Canny_edge_detector>

    Returns: IMAGE
    """
    return Image(self._getEdgeMap(t1, t2))

  def _getEdgeMap(self, t1=50, t2=100):
    """
    Return the binary bitmap which shows where edges are in the image.  The two
    parameters determine how much change in the image determines an edge, 
    and how edges are linked together.  For more information refer to:

    http://en.wikipedia.org/wiki/Canny_edge_detector
    http://opencv.willowgarage.com/documentation/python/imgproc_feature_detection.html?highlight=canny#Canny
    """ 
  
    if (self._edgeMap and self._cannyparam[0] == t1 and self._cannyparam[1] == t2):
      return self._edgeMap

    self._edgeMap = self.getEmpty(1) 
    cv.Canny(self._getGrayscaleBitmap(), self._edgeMap, t1, t2)
    self._cannyparam = (t1, t2)

    return self._edgeMap

  def rotate(self, angle, mode="fixed", point=[-1,-1], scale = 1.0):
    """
    This rotates an image around a specific point by the given angle 
    By default in "fixed" mode, the returned Image is the same dimensions as the original Image, and the contents will be scaled to fit.  In "full" mode the
    contents retain the original size, and the Image object will scale
    by default, the point is the center of the image. 
    you can also specify a scaling parameter

    Returns: IMAGE
    """
    if( point[0] == -1 or point[1] == -1 ):
      point[0] = (self.width-1)/2
      point[1] = (self.height-1)/2

    if (mode == "fixed"):
      retVal = self.getEmpty()
      rotMat = cv.CreateMat(2,3,cv.CV_32FC1);
      cv.GetRotationMatrix2D((float(point[0]),float(point[1])),float(angle),float(scale),rotMat)
      cv.WarpAffine(self.getBitmap(),retVal,rotMat)
      return( Image(retVal) ) 


    #otherwise, we're expanding the matrix to fit the image at original size
    rotMat = cv.CreateMat(2,3,cv.CV_32FC1);
    # first we create what we thing the rotation matrix should be
    cv.GetRotationMatrix2D((float(point[0]),float(point[1])),float(angle),float(scale),rotMat)
    A = np.array([0,0,1])
    B = np.array([self.width,0,1])
    C = np.array([self.width,self.height,1])
    D = np.array([0,self.height,1])
    #So we have defined our image ABC in homogenous coordinates
    #and apply the rotation so we can figure out the image size
    a = np.dot(rotMat,A)
    b = np.dot(rotMat,B)
    c = np.dot(rotMat,C)
    d = np.dot(rotMat,D)
    #I am not sure about this but I think the a/b/c/d are transposed
    #now we calculate the extents of the rotated components. 
    minY = min(a[1],b[1],c[1],d[1])
    minX = min(a[0],b[0],c[0],d[0])
    maxY = max(a[1],b[1],c[1],d[1])
    maxX = max(a[0],b[0],c[0],d[0])
    #from the extents we calculate the new size
    newWidth = np.ceil(maxX-minX)
    newHeight = np.ceil(maxY-minY)
    #now we calculate a new translation
    tX = 0
    tY = 0
    #calculate the translation that will get us centered in the new image
    if( minX < 0 ):
      tX = -1.0*minX
    elif(maxX > newWidth-1 ):
      tX = -1.0*(maxX-newWidth)

    if( minY < 0 ):
      tY = -1.0*minY
    elif(maxY > newHeight-1 ):
      tY = -1.0*(maxY-newHeight)

    #now we construct an affine map that will the rotation and scaling we want with the 
    #the corners all lined up nicely with the output image. 
    src = ((A[0],A[1]),(B[0],B[1]),(C[0],C[1]))
    dst = ((a[0]+tX,a[1]+tY),(b[0]+tX,b[1]+tY),(c[0]+tX,c[1]+tY))

    cv.GetAffineTransform(src,dst,rotMat)

    #calculate the translation of the corners to center the image
    #use these new corner positions as the input to cvGetAffineTransform
    retVal = cv.CreateImage((int(newWidth),int(newHeight)), 8, int(3))
    cv.WarpAffine(self.getBitmap(),retVal,rotMat)
    return( Image(retVal) ) 


  def shear(self, cornerpoints):
    """
    Given a set of new corner points in clockwise order, return a shear-ed Image
    that transforms the Image contents.  The returned image is the same
    dimensions.

    cornerpoints is a 2x4 array of point tuples


    Returns: IMAGE
    """
    src =  ((0,0),(self.width-1,0),(self.width-1,self.height-1))
    #set the original points
    aWarp = cv.CreateMat(2, 3, cv.CV_32FC1)
    #create the empty warp matrix
    cv.GetAffineTransform(src, cornerpoints, aWarp)

    return self.transformAffine(aWarp)

  def transformAffine(self, rotMatrix):
    """
    This helper function for shear performs an affine rotation using the supplied matrix. 
    The matrix can be a either an openCV mat or an np.ndarray type. 
    The matrix should be a 2x3

    Returns: IMAGE
    """
    retVal = self.getEmpty()
    if(type(rotMatrix) == np.ndarray ):
      rotMatrix = npArray2cvMat(rotMatrix)
    cv.WarpAffine(self.getBitmap(),retVal,rotMatrix)
    return( Image(retVal) ) 

  def warp(self, cornerpoints):
    """
    Given a new set of corner points in clockwise order, return an Image with 
    the images contents warped to the new coordinates.  The returned image
    will be the same size as the original image


    Returns: IMAGE
    """
    #original coordinates
    src = ((0,0),(self.width-1,0),(self.width-1,self.height-1),(0,self.height-1))
    
    pWarp = cv.CreateMat(3,3,cv.CV_32FC1) #create an empty 3x3 matrix
    cv.GetPerspectiveTransform(src,cornerpoints,pWarp) #figure out the warp matrix

    return self.transformPerspective(pWarp)

  def transformPerspective(self, rotMatrix):

    """
    This helper function for warp performs an affine rotation using the supplied matrix. 
    The matrix can be a either an openCV mat or an np.ndarray type. 
    The matrix should be a 3x3

    Returns: IMAGE
    """
    retVal = self.getEmpty()
    if(type(rotMatrix) == np.ndarray ):
      rotMatrix = npArray2cvMat(rotMatrix)
    cv.WarpPerspective(self.getBitmap(),retVal,rotMatrix)
    return( Image(retVal) ) 
  
  def getPixel(self, x, y):
    """
    This function returns the RGB value for a particular image pixel given a specific row and column.
    """
    retVal = None
    if( x < 0 or x >= self.width ):
      warnings.warn("getRGBPixel: X value is not valid.")
    elif( y < 0 or y >= self.height ):
      warnings.warn("getRGBPixel: Y value is not valid.")
    else:
      retVal = cv.Get2D(self.getBitmap(),x,y);
    return retVal
  
  def getGrayPixel(self, x, y):
    """
    This function returns the Gray value for a particular image pixel given a specific row and column.
    """
    retVal = None;
    if( x < 0 or x >= self.width ):
      warnings.warn("getGrayPixel: X value is not valid.") 
    elif( y < 0 or y >= self.height ):
      warnings.warn("getGrayPixel: Y value is not valid.")
    else:
      retVal = cv.Get2D(self._getGrayscaleBitmap(),x,y);
      retVal = retVal[0]
    return retVal
      
  def getVertScanline(self, column):
    """
    This function returns a single column of RGB values from the image. 
    """
    retVal = None
    if( column < 0 or column >= self.width ):
      warnings.warn("getVertRGBScanline: column value is not valid.")
    else:
      retVal = cv.GetCol(self.getBitmap(),column)
      retVal = np.array(retVal)
      retVal = retVal[:,0,:] 
    return retVal
  
  def getHorzScanline(self, row):
    """
    This function returns a single row of RGB values from the image. 
    """
    retVal = None
    if( row < 0 or row >= self.height ):
      warnings.warn("getHorzRGBScanline: row value is not valid.")
    else:
      retVal = cv.GetRow(self.getBitmap(), row)
      retVal = np.array(retVal)
      retVal = retVal[0,:,:]
    return retVal
  
  def getVertScanlineGray(self, column):
    """
    This function returns a single column of gray values from the image. 
    """
    retVal = None
    if( column < 0 or column >= self.width ):
      warnings.warn("getHorzRGBScanline: row value is not valid.")
    else:
      retVal = cv.GetCol(self._getGrayscaleBitmap(), column )
      retVal = np.array(retVal)
      #retVal = retVal.transpose()
    return retVal
  
  def getHorzScanlineGray(self, row):
    """
    This function returns a single row of RGB values from the image. 
    """
    retVal = None
    if( row < 0 or row >= self.height ):
      warnings.warn("getHorzRGBScanline: row value is not valid.")
    else:
      retVal = cv.GetRow(self._getGrayscaleBitmap(), row )
      retVal = np.array(retVal)
      retVal = retVal.transpose()
    return retVal

  def crop(self,x , y, w, h, centered=False):
    """
    Crop attempts to use the x and y position variables and the w and h width
    and height variables to crop the image. When centered is false, x and y
    define the top and left of the cropped rectangle. When centered is true
    the function uses x and y as the centroid of the cropped region.
    
    The function returns a new image. 
    """
    retVal = cv.CreateImage((w,h), cv.IPL_DEPTH_8U, 3)
    if( centered ):
      rectangle = (x-(w/2),y-(h/2),w,h)
    else:
      rectangle = (x,y,w,h)
    
    cv.SetImageROI(self.getBitmap(),rectangle)
    cv.Copy(self.getBitmap(),retVal)
    cv.ResetImageROI(self.getBitmap())
    return Image(retVal)
    
  def regionSelect(self, x1, y1, x2, y2 ):
    """
    Region select is similar to crop, but instead of taking a position and width
    and height values it simply takes to points on the image and returns the selected
    region. This is very helpful for creating interactive scripts that require
    the user to select a region. 
    """
    w = abs(x1-x2)
    h = abs(y1-y2)

    retVal = None;
    if( w <= 0 or h <= 0 or w > self.width or h > self.height ):
      warnings.warn("regionSelect: the given values will not fit in the image or are too small.")
    else:
      xf = x2 
      if( x1 < x2 ):
        xf = x1
      yf = y2
      if( y1 < y2 ):
        yf = y1
      retVal = self.crop(xf,yf,w,h)
      
    return retVal
  
