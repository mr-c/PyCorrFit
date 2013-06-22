# -*- coding: utf-8 -*-
""" PyCorrFit
    Paul Müller, Biotec - TU Dresden

    Module tools - statistics
    Provide the user with tab-separated statistics of their curves.
    Values are sorted according to the page number.

    Dimensionless representation:
    unit of time        : 1 ms
    unit of inverse time: 10³ /s
    unit of distance    : 100 nm
    unit of Diff.coeff  : 10 µm²/s
    unit of inverse area: 100 /µm²
    unit of inv. volume : 1000 /µm³
"""


import wx
import numpy as np
import os

from info import InfoClass

# Menu entry name
MENUINFO = ["&Statistics", "Show some session statistics."]

class Stat(wx.Frame):
    # This tool is derived from a wx.frame.
    def __init__(self, parent):
        # parent is the main frame of PyCorrFit
        self.parent = parent
        # Get the window positioning correctly
        pos = self.parent.GetPosition()
        pos = (pos[0]+100, pos[1]+100)
        wx.Frame.__init__(self, parent=self.parent, title="Statistics",
                 pos=pos, style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)
        ## MYID
        # This ID is given by the parent for an instance of this class
        self.MyID = None
        # Page - the currently active page of the notebook.
        self.Page = self.parent.notebook.GetCurrentPage()
        ## Content
        # We will display a dialog that conains all the settings
        # - Which model we want statistics on
        # - What kind of parameters should be printed
        #   (We will get the parameters from the current page)
        #   If on another page, the parameter is not available,
        #   do not make a mess out of it.
        # Then the user presses a button and sees/saves the table
        # with all the cool info.
        self.panel = wx.Panel(self)
        # A dropdown menu for the source Page:
        text = wx.StaticText(self.panel, 
                             label="Create a table with all the selected\n"+
                                   "variables below from pages with the\n"+
                                   "same model as the current page.")
        # Parameter settings.
        if self.parent.notebook.GetPageCount() != 0:
            self.InfoClass = InfoClass(CurPage=self.Page)
        else:
            self.Disable()
        # Create space for parameters
        self.box = wx.StaticBox(self.panel, label="values:")
        self.boxsizer = wx.StaticBoxSizer(self.box, wx.VERTICAL)
        self.Checkboxes = list()
        self.Checklabels = list()
        if self.parent.notebook.GetPageCount() != 0:
            self.OnChooseValues()
        self.btnSave = wx.Button(self.panel, wx.ID_ANY, 'Save')
        self.Bind(wx.EVT_BUTTON, self.OnSaveTable, self.btnSave)
        # Add elements to sizer
        self.topSizer = wx.BoxSizer(wx.VERTICAL)
        self.topSizer.Add(text)
        self.topSizer.Add(self.boxsizer)
        self.topSizer.Add(self.btnSave)
        # Set size of window
        self.panel.SetSizer(self.topSizer)
        self.topSizer.Fit(self)
        self.SetMinSize(self.topSizer.GetMinSizeTuple())
        ## Icon
        if parent.MainIcon is not None:
            wx.Frame.SetIcon(self, parent.MainIcon)
        self.Show(True)


    def OnChooseValues(self, event=None):
        self.InfoClass.CurPage = self.Page
        # Now that we know our Page, we may change the available
        # parameter options.
        Infodict = self.InfoClass.GetCurInfo()
        # We want to sort the information and have some prechecked values
        # in the statistics window afterwards.
        # new iteration
        keys = Infodict.keys()
        head = list()
        tail = list()
        for key in keys:
            if key == "title":
                for item in Infodict[key]:
                    if len(item) == 2:
                        if item[0] == "filename/title":
                            head.append(item)
                        else:
                            tail.append(item)
            # Append all other items
            else:
                for item in Infodict[key]:
                    if len(item) == 2:
                        tail.append(item)
        # Bring lists together
        Info = head + tail
        headcounter = 0
        headlen = len(head)
        for item in Info:
            headcounter += 1
            checkbox = wx.CheckBox(self.panel, label=item[0])
            if headcounter <= headlen:
                checkbox.SetValue(True)
            self.boxsizer.Add(checkbox)
            self.Checkboxes.append(checkbox)
            self.Checklabels.append(item[0])


    def OnClose(self, event=None):
        # This is a necessary function for PyCorrFit.
        # Do not change it.
        self.parent.toolmenu.Check(self.MyID, False)
        self.parent.ToolsOpen.__delitem__(self.MyID)
        self.Destroy()


    def OnPageChanged(self, page):
        # When parent changes
        # This is a necessary function for PyCorrFit.
        # This is stuff that should be done when the active page
        # of the notebook changes.
        self.Page = page
        self.InfoClass = InfoClass(CurPage=self.Page)
        if self.parent.notebook.GetPageCount() == 0:
            self.Disable()
            return
        self.Enable()
        for i in np.arange(len(self.Checkboxes)):
            self.boxsizer.Remove(0)
            self.Checkboxes[i].Destroy()
            #self.Checklabels[i].Destroy()
        self.Checkboxes = list()
        self.Checklabels = list()
        self.OnChooseValues()
        self.boxsizer.Layout()
        self.topSizer.Fit(self)
        self.SetMinSize(self.topSizer.GetMinSizeTuple())



    def OnSaveTable(self, event=None):
        dirname = self.parent.dirname
        dlg = wx.FileDialog(self.parent, "Choose file to save", dirname, "", 
              "Text file (*.txt)|*.txt;*.TXT",
               wx.SAVE|wx.FD_OVERWRITE_PROMPT)
        # user cannot do anything until he clicks "OK"
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()
            if filename.lower().endswith(".txt") is not True:
                filename = filename+".txt"
            dirname = dlg.GetDirectory()
            openedfile = open(filename, 'wb')
            # Get Parameterlist of all Pages with same model id as
            # Self.Page
            modelid = self.Page.modelid
            # This creates self.SaveInfo:
            self.GetWantedParameters()
            # Write header
            linestring = ""
            for atuple in self.SaveInfo[0]:
                linestring += str(atuple[0])+"\t"
            # remove trailing "\t"
            openedfile.write(linestring.strip()+"\r\n")
            # Write data         
            for item in self.SaveInfo:
                linestring = ""
                for btuple in item:
                    linestring += str(btuple[1])+"\t"
                openedfile.write(linestring.strip()+"\r\n")
            openedfile.close()
        else:
            dirname = dlg.GetDirectory()
            dlg.Destroy()
        # Give parent the current dirname
        self.parent.dirname = dirname


    def GetWantedParameters(self):
        # Get the wanted parameters from the selection.
        checked = list()
        for i in np.arange(len(self.Checkboxes)):
            if self.Checkboxes[i].IsChecked() == True:
                checked.append(self.Checklabels[i])
        # Collect all the relevant pages
        pages = list()
        for i in np.arange(self.parent.notebook.GetPageCount()):
            Page = self.parent.notebook.GetPage(i)
            if Page.modelid == self.Page.modelid:
                pages.append(Page)
        self.InfoClass.Pagelist = pages
        AllInfo = self.InfoClass.GetAllInfo()
        self.SaveInfo = list()
        # Some nasty iteration through the dictionaries.
        # Collect all checked variables.
        pagekeys = AllInfo.keys()
        # If pagenumber is larger than 10,
        # pagekeys.sort will not work, because we have strings
        # Define new compare function
        cmp_func = lambda a,b: cmp(int(a.strip().strip("#")),
                                   int(b.strip().strip("#")))
        pagekeys.sort(cmp=cmp_func)
        #for Info in pagekeys:
        #    pageinfo = list()
        #    for item in AllInfo[Info]:
        #        for subitem in AllInfo[Info][item]:
        #            if len(subitem) == 2:
        #                for label in checked:
        #                    if label == subitem[0]:
        #                        pageinfo.append(subitem)
        #
        # We want to replace the above iteration with an iteration that
        # covers missing values. This means checking for "label == subitem[0]"
        # and iteration over AllInfo with that consition.
        
        for Info in pagekeys:
            pageinfo = list()
            for label in checked:
                label_in_there = False
                for item in AllInfo[Info]:
                    for subitem in AllInfo[Info][item]:
                        if len(subitem) == 2:
                            if label == subitem[0]:
                                label_in_there = True
                                pageinfo.append(subitem)
                if label_in_there == False:
                    # No data available
                    pageinfo.append([label, "-"])
            self.SaveInfo.append(pageinfo)
