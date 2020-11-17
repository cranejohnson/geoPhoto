import tkinter
import os.path
import imghdr
import signal

try:
  from tkinter import filedialog
except ImportError:
  import tkFileDialog

window = tkinter.Tk()

w = 750 # width for the Tk root
h = 350 # height for the Tk root

# get screen width and height
ws = window.winfo_screenwidth() # width of the screen
hs = window.winfo_screenheight() # height of the screen

# calculate x and y coordinates for the Tk root window
x = (ws/2) - (w/2)
y = (hs/2) - (h/2)

# set the dimensions of the screen
# and where it is placed
window.geometry('%dx%d+%d+%d' % (w, h, x, y))



window.title("APRFC GeoPhoto Processing")

def saveCallback():
    with open("parameters.input", 'w') as outfile:
        outfile.write("[geoPhoto]\n")
        outfile.write("dir = "+filePath.get()+"\n")
        outfile.write("width = "+e1.get()+"\n")
        quit()

def exitGui():
    os.kill(os.getppid(), signal.SIGTERM)
    quit()

def fileCallback():

    geoPhotoDir = os.getcwd()
    print(geoPhotoDir)
    try:
      baseDir = tkFileDialog.askdirectory(initialdir = os.getcwd(),title="Select top directory with pictures")
    except:
      baseDir = filedialog.askdirectory(initialdir = os.getcwd(),title="Select top directory with pictures")
    #value = input("Please enter path to top photo directory [enter for current directory]:")

    print(baseDir)
    filePath.config(state="normal")
    filePath.delete(0, tkinter.END)
    filePath.insert(0, baseDir)
    filePath.config(state="disabled")

    filelist = []
    outFileName = os.path.split(baseDir)[1]
    for subdir, dirs, files in os.walk(baseDir):
      for file in files:
          toss, file_extension = os.path.splitext(os.path.relpath(subdir+'/'+file))
          if 'geoPhotos' in subdir:
            continue
          if(imghdr.what(os.path.relpath(subdir+'/'+file)) == 'jpeg'):
            filelist.append(os.path.relpath(subdir+'/'+file,baseDir))
          else:
            print('File: '+os.path.relpath(subdir+'/'+file)+' is not and image file')

    numFiles = len(filelist)
    fileNum.config(state="normal")
    fileNum.delete(0, tkinter.END)
    fileNum.insert(0, numFiles)
    fileNum.config(state="disabled")
 


infoBlock = tkinter.Label(text="Instructions:\n\nEnter the information below and then select the top directory of photos to process.\nAll photos below this directory will be included.\n\n")
infoBlock.grid(row=0,column=0,columnspan=2,sticky='W')


b1 = tkinter.Button(window,text ="Select Directory to Process", command=fileCallback)
b1.grid(row=1,column=0,sticky='W')

filePath = tkinter.Entry(window,state='disabled',width=50)
filePath.grid(row=1,column=1,sticky='W')

b2 = tkinter.Button(window,text ="Number of files:", command=fileCallback)
b2.grid(row=2,column=0,sticky='W')


fileNum = tkinter.Entry(window,state='disabled',width=5)
fileNum.grid(row=2,column=1,sticky='W')

infoBlock = tkinter.Label(text="To keep the kmz file size under 10 mb suggest:\nwidth = 1280 for 75 files or less\nwidth = 640 for 150 files\nwidth = 350 for 500 files")
infoBlock.grid(row=3,column=0,columnspan=2,sticky='W')


tkinter.Label(window, text="Maximum Photo Width for Output:").grid(row=4,column=0)
e1 = tkinter.Entry(window,width=5)
e1.insert(tkinter.END, '640')
e1.grid(row=4,column=1,sticky='W')


b3 = tkinter.Button(window, text ="Run geoPhoto and generate: kml, kmz and html viewers", command = saveCallback)
b3.grid(row=5,column=0)

b4 = tkinter.Button(window, text ="Cancel",command=exitGui)
b4.grid(row=6,column=0)


window.mainloop()