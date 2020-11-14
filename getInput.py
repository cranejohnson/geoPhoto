import tkinter
import os.path

try:
  from tkinter import filedialog
except ImportError:
  import tkFileDialog

window = tkinter.Tk()

w = 750 # width for the Tk root
h = 300 # height for the Tk root

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
        outfile.write("dir:"+filePath.get()+"\n")
        outfile.write("width:"+e1.get()+"\n")
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

    #filePath.insert(0, directory) #inserts new value assigned by 2nd parameter



infoBlock = tkinter.Label(text="Instructions:\n\nEnter the information below and then select the top directory of photos to process.\nAll photos below this directory will be included.\n\n")
infoBlock.grid(row=0,column=0,columnspan=2,sticky='W')


b1 = tkinter.Button(window,text ="Select Directory to Process", command=fileCallback)
b1.grid(row=1,column=0,sticky='W')

filePath = tkinter.Entry(window,state='disabled',width=50)
filePath.grid(row=1,column=1,sticky='W')


tkinter.Label(window, text="Maximum Photo Width for Output:").grid(row=3,column=0)
e1 = tkinter.Entry(window,width=5)
e1.insert(tkinter.END, '640')
e1.grid(row=3,column=1,sticky='W')


b2 = tkinter.Button(window, text ="Save and Run", command = saveCallback)
b2.grid(row=4,column=0)



window.mainloop()