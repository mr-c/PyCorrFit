# -*- coding: utf-8 -*-
""" PyCorrFit
    Paul Müller, Biotec - TU Dresden

    Module tools - info
    Open a text window with lots of information.

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

import platform





import models as mdls

class InfoClass(object):
    """ This class get's all the Info possible from a Page and
        makes it available through a dictionary with headings as keys.
    """
    def __init__(self, CurPage=None, Pagelist=None ):
        # A list of all Pages currently available:
        self.Pagelist = Pagelist
        # The current page we are looking at:
        self.CurPage = CurPage

    def GetAllInfo(self):
        """ Get a dictionary with page titles and an InfoDict as value.
        """
        MultiInfo = dict()
        for Page in self.Pagelist:
            # Page counter includes a whitespace and a ":" which we do not want.
            MultiInfo[Page.counter[:-2]] = self.GetPageInfo(Page)
        return MultiInfo

    def GetCurInfo(self):
        """ Get all the information about the current Page.
            Added for convenience. You may use GetPageInfo.
        """
        return self.GetPageInfo(self.CurPage)

    def GetCurFancyInfo(self):
        """ For convenience. """
        return self.GetFancyInfo(self.CurPage)

    def GetFancyInfo(self, Page):
        """ Get a nice string representation of the Info """
        InfoDict = self.GetPageInfo(Page)
        # Version
        Version = "PyCorrFit v."+InfoDict["version"][0]+"\n"
        # Title
        Title = "\n"
        for item in InfoDict["title"]:
            Title = Title + item[0]+": "+ item[1]+"\n"
        # Parameters
        Parameters = "\nParameters:\n"
        for item in InfoDict["parameters"]:
            Parameters = Parameters + "  "+item[0]+" = "+ str(item[1])+"\n"
        # Supplementary variables
        Supplement = "\nSupplementary variables:\n"
        try:
            for item in InfoDict["supplement"]:
                Supplement = Supplement + "  "+item[0]+" = "+ str(item[1])+"\n"
        except KeyError:
            Supplement = ""
        # Fitting
        Fitting = "\nFitting:\n"
        try:
            for item in InfoDict["fitting"]:
                Fitting = Fitting + "  "+item[0]+": "+str(item[1])+"\n"
        except KeyError:
            Fitting = ""
        # Background
        Background = "\nBackground:\n"
        try:
            for item in InfoDict["background"]:
                Background = Background + "  "+item[0]+": "+str(item[1])+"\n"
        except KeyError:
            Background = ""

        # Function doc string
        ModelDoc = "\n\nModel doc string:\n       " + InfoDict["modeldoc"][0]
        # Supplementary variables
        try:
            SupDoc = InfoDict["modelsupdoc"][0]
        except KeyError:
            SupDoc = ""

        PageInfo = Version+Title+Parameters+Supplement+Fitting+Background+\
                   ModelDoc+SupDoc
        return PageInfo

    def GetPageInfo(self, Page):
        """ Needs a Page and gets all information from it """
        # A dictionary with headings as keys and lists of singletts/tuples as 
        # values. If it is a tuple, it might me interesting for a table.
        InfoDict = dict()
        # Get model information
        model = [Page.model, Page.tabtitle.GetValue(), Page.modelid]
        parms = Page.active_parms[1]
        fct = Page.active_fct.__name__

        InfoDict["version"] = [Page.parent.version]
        
        Title = list()
        Title.append(["Function used", fct ]) 
        Title.append(["Model name", model[0] ]) 
        Title.append(["Model ID", str(model[2]) ]) 
        Title.append(["User title", model[1] ]) 
        Title.append(["Page number", Page.counter[1:-2] ]) 
        InfoDict["title"] = Title
        
        # Parameters
        Parameters = list()
        # Use this function to determine human readable parameters, if possible
        Units, Newparameters = mdls.GetHumanReadableParms(model[2], parms)
        # Add Parameters
        for i in np.arange(len(parms)):
            Parameters.append([ Units[i], Newparameters[i] ])
        InfoDict["parameters"] = Parameters

        # Add some more information if available
        # Info is a dictionary or None
        MoreInfo = mdls.GetMoreInfo(model[2], Page)
        if MoreInfo is not None:
            InfoDict["supplement"] = MoreInfo
            # Try to get the dictionary entry of a model
            try:
                # This function should return all important information
                # that can be calculated from the given parameters.
                func_info = mdls.supplement[model[2]]
            except KeyError:
                # No information available
                a=0
            else:
                InfoDict["modelsupdoc"] = [func_info .func_doc]
        

        # Fitting
        weightedfit = Page.Fitbox[1].GetValue()
        fittingbins = Page.Fitbox[5].GetValue() # from left and right
        Fitting = list()
        if Page.dataexp is not None:
            # Mode AC vs CC
            if Page.IsCrossCorrelation is True:
                Title.append(["Data type", "Cross-correlation" ]) 
            else:
                Title.append(["Data type", "Autocorrelation" ]) 
            Fitting.append([ u"\u03c7"+"²", Page.chi2 ])
            Fitting.append([ "Weighted fit", weightedfit ])
            if weightedfit is True:
                Fitting.append([ "No. channels", 2*fittingbins+1 ])
            # Fitting range:
            t1 = 1.*Page.taufull[Page.startcrop]
            t2 = 1.*Page.taufull[Page.endcrop-1]
            Fitting.append([ "Interval start [ms]", "%.4e" % t1 ])
            Fitting.append([ "Interval end [ms]", "%.4e" % t2 ])

            # Fittet parameters
            somuch = sum(Page.active_parms[2])
            if somuch >= 1:
                fitted = ""
                for i in np.arange(len(Page.active_parms[2])):
                    if Page.active_parms[2][i] is True:
                        fitted=fitted+Page.active_parms[0][i]+ ", "
                fitted = fitted[:-2] # remove trailing comma
                Fitting.append(["fit par.", fitted])
            InfoDict["fitting"] = Fitting


        # Background
        bgselected = Page.bgselected # Selected Background
        Background = list()
        if bgselected is not None:
            bgname = Page.parent.Background[bgselected][1]
            bgrate = Page.parent.Background[bgselected][0]
            Background.append([ "bg name", bgname ])
            Background.append([ "bg rate [kHz]", bgrate ])
            InfoDict["background"] = Background

        # Function doc string
        InfoDict["modeldoc"] = [Page.active_fct.func_doc]

        return InfoDict




class ShowInfo(wx.Frame):
    def __init__(self, parent):
        # parent is main frame
        self.parent = parent
        # Get the window positioning correctly
        pos = self.parent.GetPosition()
        pos = (pos[0]+100, pos[1]+100)
        wx.Frame.__init__(self, parent=self.parent, title="Info",
                 pos=pos, style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)

        
        ## MYID
        # This ID is given by the parent for an instance of this class
        self.MyID = None

        # Page
        self.Page = self.parent.notebook.GetCurrentPage()

        initial_size = wx.Size(450,300)
        initial_sizec = (initial_size[0]-6, initial_size[1]-30)
        self.SetMinSize(wx.Size(200,200))
        self.SetSize(initial_size)
         ## Content
        self.panel = wx.Panel(self)

        self.control = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE, 
                        size=initial_sizec)
        btncopy = wx.Button(self.panel, wx.ID_CLOSE, 'Copy to clipboard')
        self.Bind(wx.EVT_BUTTON, self.OnCopy, btncopy)
        

        self.topSizer = wx.BoxSizer(wx.VERTICAL)

        self.topSizer.Add(btncopy)
        self.topSizer.Add(self.control)


        self.panel.SetSizer(self.topSizer)
        self.topSizer.Fit(self)
        self.Show(True)
        wx.EVT_SIZE(self, self.OnSize)
        self.Content()

    def Content(self):
        # Fill self.control with content.
        # Parameters and models
        Page = self.Page
        InfoMan = InfoClass(CurPage=Page)
        PageInfo = InfoMan.GetCurFancyInfo()
        self.control.SetValue(PageInfo)

    def OnClose(self, event=None):
        self.parent.toolmenu.Check(self.MyID, False)
        self.parent.ToolsOpen.__delitem__(self.MyID)
        self.Destroy()

    def OnCopy(self, event):
        if not wx.TheClipboard.IsOpened():
            clipdata = wx.TextDataObject()
            clipdata.SetText(self.control.GetValue())
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(clipdata)
            wx.TheClipboard.Close()
        else:
            print "Other application has lock on clipboard."

    def OnPageChanged(self, page):
        # When parent changes
        self.Page = page
        self.Content()

    def OnSize(self, event):
        size = event.GetSize()
        sizec = wx.Size(size[0]-5, size[1]-30)
        self.panel.SetSize(size)
        self.control.SetSize(sizec)


