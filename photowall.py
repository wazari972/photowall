#!/usr/bin/env python

import os
import tempfile
import pipes
import subprocess
import time
import random
import shutil

try:
  from wand.image import Image
  from wand.display import display
except ImportError as e:
  # cd /usr/lib/
  # ln -s libMagickWand-6.Q16.so libMagickWand.so
  print("Couldn't import Wand package.")
  print("Please refer to #http://dahlia.kr/wand/ to install it.")
  import traceback; traceback.print_exc()
  raise e

try:
  import magic
  mime = magic.Magic()
except ImportError:
  mime = None
  #https://github.com/ahupp/python-magic
  print("WARNING: python-magic not installed, some magic won't work")

try:
  from docopt import docopt
except ImportError:
  print("Couldn't import Docopt package.")
  print("Please refer to#https://github.com/docopt/docopt to install it.")
  print("/!\\ Option parsing not possible, defaulting to hardcoded values/!\\")

def to_bool(val):
  if val is None:
    return false
  return val == 1
  
def to_int(val):
  return int(val)
  
def to_str(val):
  return val

def to_path(val):
  return val

OPT_TO_KEY = {
 '--do-wrap'        : ("DO_WRAP", to_bool),
 '--line-height': ("LINE_HEIGHT", to_int),
 '--nb-lines'        : ('LINES', to_int),
 '--no-caption'        : ("WANT_NO_CAPTION", to_bool),
 '--pick-random': ("PICK_RANDOM", to_bool),
 '--put-random'        : ("PUT_RANDOM", to_bool),
 '--no-resize'        : ("DO_NOT_RESIZE", to_bool),
 '--sleep'        : ('SLEEP_TIME', to_int),
 '--width'        : ('WIDTH', to_int),
 '<path>'        : ('PATH', to_path),
 '<target>'        : ('TARGET', to_path),
 '--polaroid'        : ("DO_POLAROID", to_bool),
 '--format'        : ("IMG_FORMAT_SUFFIX", to_str),
 '--crop-size'        : ("CROP_SIZE", to_int),
 '--help'        : ("HELP", to_bool)
}

KEY_TO_OPT = dict([(key, (opt, ttype)) for opt, (key, ttype) in OPT_TO_KEY.items()])

PARAMS = {
"PATH" : "/home/kevin/mount/téléphone",
"TARGET" : "/tmp/final.png",
#define the size of the picture
"WIDTH" : 1000,

#define how many lines do we want
"LINES": 2,

"LINE_HEIGHT": 200,

#minimum width of cropped image. Below that, we black it out
#only for POLAROID
"CROP_SIZE": 100,

"IMG_FORMAT_SUFFIX": ".png",

# True if end-of-line photos are wrapped to the next line
"DO_WRAP": False,
# True if we want a black background and white frame, plus details
"DO_POLAROID": True,

"WANT_NO_CAPTION": True,

# False if we want to add pictures randomly
"PUT_RANDOM": False,

"DO_NOT_RESIZE": False,

### Directory options ###

# False if we pick directory images sequentially, false if we take them randomly
"PICK_RANDOM": False,

## Random wall options ##
"SLEEP_TIME": 0,

"HELP": False
}

DEFAULTS = dict([(key, value) for key, value in PARAMS.items()])
DEFAULTS_docstr = dict([(KEY_TO_OPT[key][0], value) for key, value in PARAMS.items()])

usage = """Photo Wall generator.

Usage: 
  photowall.py <path> <target> [options]

Arguments:
  <path>        The path where photos are picked up from. [default: %(<path>)s]
  <target>      The path where the target photo is written. Except in POLAROID+RANDOM mode, the image will be blanked out first. [default: %(<target>)s]

Options:
  --polaroid              Use polaroid-like images for the wall
  --pick-random           Pick images randomly in the <path> folder. [default: %(--pick-random)s]
  --help                  Display this message

Size options:
  --nb-lines <nb>         Number on lines of the target image. [default: %(--nb-lines)d]
  --line-height <height>  Set the height of a single image. [default: %(--line-height)d]
  --width <width>         Set final image width. [default: %(--width)d]
  --no-resize             Resize images before putting in the wall. [default: %(--no-resize)s]

Polaroid mode options:
  --crop-size <crop>      Minimum size to allow cropping an image, if it doesn't fit [default: %(--crop-size)s]
  --no-caption            Disable caption. [default: %(--no-caption)s] 
  --put-random            Put images randomly instead of linearily. [default: %(--put-random)s]
  --sleep <time>          If --put-random, time (in seconds) to go asleep before adding a new image. [default: %(--sleep)d]

Collage mode options:
  --do-wrap               Finish images on the next line? [default: %(--do-wrap)s]

  """ % DEFAULTS_docstr


class UpdateCallback:
  def newExec(self):
    pass
  
  def newImage(self, row=0, col=0, filename=""):
    print("%d.%d > %s" % (row, col, filename))
    
  def updLine(self, row, tmpLine):
    #print("--- %d ---" % row)
    pass
  
  def newFinal(self, name):
    pass
  
  def finished(self, name):
    print("==========")

  def stopRequested(self):
    return False
  
  def checkPause(self):
    pass

updateCB = UpdateCallback()

if __name__ == "__main__":
    arguments = docopt(usage, version="3.5-dev")

    if arguments["--help"]:
        print(usage)
        exit()

    param_args = dict([(OPT_TO_KEY[opt][0], OPT_TO_KEY[opt][1](value)) for opt, value in arguments.items()])

    PARAMS = dict(PARAMS, **param_args)

###########################################

def get_file_details(filename):
  try:
    link = filename
    try:
      link = os.readlink(filename)
    except OSError:
      pass
    link = pipes.quote(link)
    names = link[link.index("/miniatures/" if not PARAMS["NO_SWITCH_TO_MINI"] else "/images"):].split("/")[2:]
    theme, year, album, fname = names
    
    return "%s (%s)" % (album, theme)
  except Exception as e:
    #print("Cannot get details from {}: {}".format(filename, e))
    fname = get_file_details_dir(filename)
    fname = fname.rpartition(".")[0]
    fname = fname.replace("_", "\n")
    return fname

###########################################

class GetFileDir:
  def __init__(self, randomize):
    self.idx = 0
    self.files = os.listdir(PARAMS["PATH"])
    
    if len(self.files) == 0:
      raise EnvironmentError("No file available")
    
    self.files.sort()
    
    if randomize:
      random.shuffle(self.files)
  
  def get_next_file(self):
    to_return = self.files[self.idx]
    
    self.idx += 1 
    self.idx %= len(self.files) 
    
    return PARAMS["PATH"]+to_return
  
def get_file_details_dir(filename):
  return filename[filename.rindex("/")+1:]

###########################################
###########################################


def do_append(first, second, underneath=False):
  sign = "-" if underneath else "+"
  background = "-background black" if PARAMS["DO_POLAROID"] else ""
  command = "convert -gravity center %s %sappend %s %s %s" % (background, sign, first, second, first)
  ret = subprocess.call(command, shell=True)
  
  if ret != 0:
    raise Exception("Command failed: ", command)

def do_polaroid (image, filename=None, background="black", suffix=None):
  if suffix is None:
    suffix = PARAMS["IMG_FORMAT_SUFFIX"]
  tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
  tmp.close()
  
  print("Saving image into {}...".format(tmp.name))
  image.save(filename=tmp.name)
  print("Done")
  
  if not(PARAMS["WANT_NO_CAPTION"]) and filename:
    details = get_file_details(filename)
    caption = """-caption "%s" """ % details.replace("'", "\\'")
  else:
    caption = ""
    
  command = ("convert "
             "-bordercolor snow "+
             "-background %(bg)s "+
             "-gravity center %(caption)s "+
             "+polaroid %(name)s %(name)s") % {"bg" : background, "name":tmp.name, "caption":caption}
             
  ret = subprocess.call(command, shell=True)
  if ret != 0:
    raise Exception("Command failed: "+ command)
  
  img = Image(filename=tmp.name).clone()
  
  os.unlink(tmp.name)
  
  img.resize(width=image.width, height=image.height)

  return img

def do_blank_image(height, width, filename, color="black"):
  print("Create blank ({}) image {}*{} --> {}".format(color, width, height, filename))
        
  command = "convert -size %dx%d xc:%s %s" % (width, height, color, filename)

  ret = subprocess.call(command, shell=True)

  if ret != 0:
    raise Exception("Command failed: "+ command)

def do_polaroid_and_random_composite(target_filename, target, image, filename):
  PERCENT_IN = 100
  
  image = do_polaroid(image, filename, background="transparent", suffix=".png")

  tmp = tempfile.NamedTemporaryFile(delete=False, suffix=PARAMS["IMG_FORMAT_SUFFIX"])
  image.save(filename=tmp.name)

  height = random.randint(0, int(target.height- image.height))
  width = random.randint(0, int(target.width - image.width))
  
  geometry = "{}{}{}{}".format("+" if width >= 0 else "", width, "+" if height >= 0 else "", height)
  print("{}".format(geometry))

  command = "composite -geometry %s -compose Over  %s %s %s" % (geometry, tmp.name, target_filename, target_filename)

  ret = os.system(command)
  os.unlink(tmp.name)
  
  if ret != 0:
    raise Exception("failed")

def photowall(name):
  output_final = None

  previous_filename = None
  #for all the rows, 
  for row in range(PARAMS["LINES"]):    
    output_row = None
    row_width = 0
    #concatenate until the image width is reached
    img_count = 0
    while row_width < PARAMS["WIDTH"]:
      # get a new file, or the end of the previous one, if it was split
      filename = get_next_file() if previous_filename is None else previous_filename
      mimetype = None
      previous_filename = None
      
      # get a real image
      if mime is not None:
        mimetype = mime.from_file(filename)
        if "symbolic link" in str(mimetype):
          filename = os.readlink(filename)
          mimetype = mime.from_file(filename)
        
        if not "image" in str(mimetype):
          continue
      else:
        try:
          filename = os.readlink(filename)
        except OSError:
          pass
      
      updateCB.newImage(row, img_count, filename)
      img_count += 1
      # resize the image
      image = Image(filename=filename)
      with image.clone() as clone:
        factor = float(PARAMS["LINE_HEIGHT"]) / clone.height

        print("Resize image {} of a factor {}".format(filename, factor))
        clone.resize(height=PARAMS["LINE_HEIGHT"], width=int(clone.width*factor))
        
        #if the new image makes an overflow
        if row_width + clone.width  > PARAMS["WIDTH"]:
          #compute how many pixels will overflow
          overflow = row_width + clone.width - PARAMS["WIDTH"]
          will_fit = clone.width - overflow
          
          if PARAMS["DO_POLAROID"] and will_fit < PARAMS["CROP_SIZE"]:
            row_width = PARAMS["WIDTH"]
            previous_filename = filename
            print("Doesn't fit")
            continue
          
          if PARAMS["DO_WRAP"]:
            with clone.clone() as next_img:
              next_img.crop(will_fit+1, 0, width=overflow, height=PARAMS["LINE_HEIGHT"])
              tmp = tempfile.NamedTemporaryFile(delete=False, suffix=PARAMS["IMG_FORMAT_SUFFIX"])
              tmp.close()
              next_img.save(filename=tmp.name)
              previous_filename = tmp.name
          clone.crop(0, 0, width=will_fit, height=PARAMS["LINE_HEIGHT"])
        
        if PARAMS["DO_POLAROID"]:
          clone = do_polaroid(clone, filename)
        
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=PARAMS["IMG_FORMAT_SUFFIX"])
        tmp.close()
        clone.save(filename=tmp.name)
        
        row_width += clone.width
        if output_row is not None:
          do_append(output_row.name, tmp.name)
          os.unlink(tmp.name)
        else:
          output_row = tmp
        
        updateCB.updLine(row, output_row.name)
        updateCB.checkPause()
        
        if updateCB.stopRequested():
          break
    else:
      if output_final is not None:
        do_append(output_final.name, output_row.name, underneath=True)
        os.unlink(output_row.name)
      else:
        output_final = output_row
      updateCB.newFinal(output_final.name)
  
  if output_final is not None:
    shutil.move(output_final.name, name)
    updateCB.finished(name)
  else:
    updateCB.finished(None)
    
  return name 
    
def random_wall(real_target_filename):
  name = real_target_filename

  filename = name.rpartition("/")[-1]
  name, _, ext = filename.rpartition(".")

  target_filename = "{}/{}.2.{}".format(tempfile.gettempdir(), name, ext)
  
  try:
    #remove any existing tmp file
    os.unlink(target_filename)
  except OSError:
    pass
  
  if os.path.exists(target_filename):
    #if source already exist, build up on it
    os.system("cp %s %s" % (target_filename, real_target_filename))

  
  print("Target file is %s" % real_target_filename )
  target = None
  if mime is not None:
    try:
      mimetype = mime.from_file(target_filename)
      if "symbolic link" in mimetype:
        filename = os.readlink(target_filename)
        mimetype = mime.from_file(target_filename)
        
      if "image" in mimetype:
        target = Image(filename=target_filename)
      
    except IOError:
      pass

  if target is None:
    height = PARAMS["LINES"] * PARAMS["LINE_HEIGHT"]
    
    do_blank_image(height, PARAMS["WIDTH"], target_filename)
    target = Image(filename=target_filename)
  
  cnt = 0
  while True:
    updateCB.checkPause()
    if updateCB.stopRequested():
      break
      
    filename = get_next_file()
    print(filename)
    
    img = Image(filename=filename)
    with img.clone() as clone:
      if not PARAMS["DO_NOT_RESIZE"]:
        factor = float(PARAMS["LINE_HEIGHT"])/clone.height
        
        print("Resize image {} of a factor {}".format(filename, factor))
        clone.resize(width=int(clone.width*factor), height=int(clone.height*factor))

      do_polaroid_and_random_composite(target_filename, target, clone, filename)
      updateCB.checkPause()
      if updateCB.stopRequested():
        break
      updateCB.newImage(row=cnt, filename=filename)
      updateCB.newFinal(target_filename)
      os.system("cp %s %s" % (target_filename, real_target_filename))
      cnt += 1
      
    updateCB.checkPause()
    if updateCB.stopRequested():
      break  
    time.sleep(PARAMS["SLEEP_TIME"])
    updateCB.checkPause()
    if updateCB.stopRequested():
      break
      
get_next_file = None

def fix_args():
  global get_next_file
  
  if PARAMS["PATH"][-1] != "/":
    PARAMS["PATH"] += "/"  
  
  get_next_file = GetFileDir(PARAMS["PICK_RANDOM"]).get_next_file

def do_main():
  
  fix_args()
  
  updateCB.newExec()
  target = PARAMS["TARGET"]
  if not(PARAMS["PUT_RANDOM"]):
    photowall(target)
  else:
    random_wall(target)

if __name__== "__main__":
    do_main()
