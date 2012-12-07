# -*- coding: utf-8 -*-
""" PyCorrFit
    Paul Müller, Biotec - TU Dresden

    Module frontend
    The frontend displays the GUI (Graphic User Interface). All necessary 
    functions and modules are called from here.

    Dimensionless representation:
    unit of time        : 1 ms
    unit of inverse time: 10³ /s
    unit of distance    : 100 nm
    unit of Diff.coeff  : 10 µm²/s
    unit of inverse area: 100 /µm²
    unit of inv. volume : 1000 /µm³
"""
# Use DEMO for contrast-rich screenshots.
# This enlarges axis text and draws black lines instead of grey ones.
DEMO = False

# Generic modules
import os
import wx                               # GUI interface wxPython
import wx.lib.plot as plot              # Plotting in wxPython
import numpy as np                      # NumPy
import sys                              # System stuff

# PyCorrFit modules
import doc
import edclasses                    # Cool stuf like better floatspin
import leastsquaresfit as fit       # For fitting
import models as mdls

## On Windows XP I had problems with the unicode Characters.
# I found this at 
# http://stackoverflow.com/questions/5419/python-unicode-and-the-windows-console
# and it helped:
reload(sys)
sys.setdefaultencoding('utf-8')


class FittingPanel(wx.Panel):
    """
    Those are the Panels that show the fitting dialogs with the Plots.
    """

    def __init__(self, parent, counter, modelid, active_parms, tau):
        """ Initialize with given parameters. """
        
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

        self.parent = parent
        self.filename = "None"

        ## If this value is set to True, the trace and traceavg variables
        ## will not be used. Instead tracecc a list, of traces will be used.
        self.IsCrossCorrelation = False
        ## Setting up variables for plotting
        self.trace = None        # The intensity trace, tuple
        self.traceavg = None     # Average trace intensity
        self.tracecc = None      # List of traces (in CC mode only)
        self.bgselected = None   # integer, index for parent.Background
        self.bgcorrect = 1.      # Background correction factor for dataexp
        self.startcrop = None    # Where cropping of dataexp starts
        self.endcrop = None      # Where cropping of dataexp ends
        self.dataexp = None      # Experimental data (cropped)
        self.dataexpfull = None  # Experimental data (not cropped)
        self.datacorr = None     # Calculated data
        self.resid = None        # Residuals

        # Fitting:
        #self.Fitbox=[ fitbox, weightedfitdrop, fittext, fittext2, fittextvar,
        #                fitspin, buttonfit ]
        # chi squared - is also an indicator, if something had been fitted
        self.FitKnots = 5 # number of knots for spline fit or similiar
        self.chi2 = None
        # Counts number of Pages already created:
        self.counter = counter

        # Model we are using
        self.modelid = modelid
        modelpack = mdls.modeldict[modelid]

        # The string of the model in the menu
        self.model = modelpack[1]
        # Some more useless text about the model
        self.modelname = modelpack[2]

        # Function for fitting
        self.active_fct = modelpack[3]

        # Parameter verification function.
        # This checks parameters concerning their physical meaningfullness :)
        self.check_parms = mdls.verification[modelid]

        # Active Parameters we are using for the fitting
        # [0] labels
        # [1] values
        # [2] bool values to fit
        # [3] labels human readable (optional)
        # [4] factors human readable (optional)
        self.active_parms = active_parms

        # Some timescale
        self.taufull = tau
        self.tau = 1*self.taufull

        ### Splitter window
        # Sizes
        size = parent.notebook.GetSize()
        tabsize = 33
        size[1] = size[1] - tabsize
        self.sizepanelx = 250
        canvasx = size[0]-self.sizepanelx
        sizepanel = (self.sizepanelx, size[1])
        sizecanvas = (canvasx, size[1])
        self.sp = wx.SplitterWindow(self, size=size, style=wx.SP_3DSASH)
        # This is necessary to prevent "Unsplit" of the SplitterWindow:
        self.sp.SetMinimumPaneSize(1)
        
        ## Settings Section (left side)
        self.panelsettings = wx.Panel(self.sp, size=sizepanel)

        ## Setting up Plot (correlation + chi**2)
        self.spcanvas = wx.SplitterWindow(self.sp, size=sizecanvas,
                                          style=wx.SP_3DSASH)
        # This is necessary to prevent "Unsplit" of the SplitterWindow:
        self.spcanvas.SetMinimumPaneSize(1)
        # y difference in pixels between Auocorrelation and Residuals
        cupsizey = size[1]*4/5

        # Calculate initial data
        self.calculate_corr()

        # Draw the settings section
        self.settings()

        # Upper Plot for plotting of Correlation Function
        self.canvascorr = plot.PlotCanvas(self.spcanvas)
        self.canvascorr.setLogScale((True, False))  
        self.canvascorr.SetEnableZoom(True)
        self.PlotAll()
        self.canvascorr.SetSize((canvasx, cupsizey))


        # Lower Plot for plotting of the residuals
        self.canvaserr = plot.PlotCanvas(self.spcanvas)
        self.canvaserr.setLogScale((True, False))
        self.canvaserr.SetEnableZoom(True)
        self.canvaserr.SetSize((canvasx, size[1]-cupsizey))
        self.spcanvas.SplitHorizontally(self.canvascorr, self.canvaserr,
                                        cupsizey)

        self.sp.SplitVertically(self.panelsettings, self.spcanvas,
                                self.sizepanelx)

        ## Check out the DEMO option and make change the plot:
        try:
            if DEMO == True:
                self.canvascorr.SetFontSizeAxis(16)
                self.canvaserr.SetFontSizeAxis(16)
        except:
            # Don't raise any unnecessary erros
            pass

        # Bind resizing to resizing function.
        wx.EVT_SIZE(self, self.OnSize)

    def apply_parameters(self, event=None):
        """ Read the values from the form and write it to the
            pages parameters.
            This function is called when the "Apply" button is hit.
        """
        # Read parameters from form and update self.active_parms[1]
        for i in np.arange(len(self.active_parms[1])):
            self.active_parms[1][i] = self.spincontrol[i].GetValue()
            self.active_parms[2][i] = self.checkboxes[i].GetValue()
        self.active_parms[1] = self.check_parms(1*self.active_parms[1])
        # If parameters have been changed because of the check_parms
        # function, write them back.
        for i in np.arange(len(self.active_parms[1])):
            self.spincontrol[i].SetValue(self.active_parms[1][i])


    def apply_parameters_reverse(self, event=None):
        """ Read the values from the pages parameters and write
            it to the form.
        """
        # Write parameters to the form on the Page
        self.active_parms[1] = self.check_parms(self.active_parms[1])
        for i in np.arange(len(self.active_parms[1])):
            self.spincontrol[i].SetValue(self.active_parms[1][i])
            self.checkboxes[i].SetValue(self.active_parms[2][i])



    def calculate_corr(self):
        """ Calculate correlation function
            Returns an array of tuples (tau, correlation)
            *self.active_f*: A function that is being calculated using
            *self.active_parms*: A list of parameters
    
            Uses variables:
            *self.datacorr*: Plotting data (tuples) of the correlation curve
            *self.dataexp*: Plotting data (tuples) of the experimental curve
            *self.tau*: "tau"-values for plotting (included) in dataexp.
    
            Returns:
            Nothing. Recalculation of the mentioned global variables is done.
        """
        parameters = self.active_parms[1]
        # calculate correlation values
        y = self.active_fct(parameters, self.tau)
        # Create new plotting data
        self.datacorr = np.zeros((len(self.tau), 2))
        self.datacorr[:, 0] = self.tau
        self.datacorr[:, 1] = y

    def CorrectDataexp(self, dataexp):
        """ Background correction
            Background correction with *self.bgcorrect*.
            Overwrites *self.dataexp*.
            For details see:
            Incollection (Thomps:bookFCS2002)
            Thompson, N. Lakowicz, J.; Geddes, C. D. & Lakowicz, J. R. (ed.)
            Fluorescence Correlation Spectroscopy
            Topics in Fluorescence Spectroscopy, Springer US, 2002, 1, 337-378
        """
        # Make a copy. Do not overwrite the original.
        if dataexp is not None:
            modified = 1 * dataexp
            if self.bgselected is not None:
                # self.bgselected - background, needs to be imported via Tools
                if self.traceavg is not None:
                    S = self.traceavg
                    B = self.parent.Background[self.bgselected][0]
                    # Calculate correction factor
                    self.bgcorrect = (S/(S-B))**2
                    # self.dataexp should be set, since we have self.trace
                    modified[:,1] = modified[:,1] * self.bgcorrect
            return modified
        else:
            return None

    def Fit_enable_fitting(self):
        """ Enable the fitting button and the weighted fit control"""
        #self.Fitbox=[ fitbox, weightedfitdrop, fittext, fittext2, fittextvar,
        #                fitspin, buttonfit ]
        self.Fitbox[0].Enable()
        self.Fitbox[1].Enable()
        self.Fitbox[-1].Enable()

    def Fit_create_instance(self, noplots=False):
        """ *noplots* prohibits plotting (e.g. splines) """
        ### If you change anything here, make sure you
        ### take a look at the global fit tool!
        ## Start fitting class and fill with information.
        Fitting = fit.Fit()
        # Verbose mode?
        if noplots is False:
            Fitting.verbose = self.parent.MenuVerbose.IsChecked()
        Fitting.uselatex = self.parent.MenuUseLatex.IsChecked()
        Fitting.check_parms = self.check_parms
        Fitting.dataexpfull = self.CorrectDataexp(self.dataexpfull)

        if self.Fitbox[1].GetSelection() == -1:
            # User edited knot number
            Knots = self.Fitbox[1].GetValue()
            Knots = filter(lambda x: x.isdigit(), Knots)
            if Knots == "":
                Knots = "5"
            List = self.Fitbox[1].GetItems()
            List[1] = "Spline ("+Knots+" knots)"
            Fitting.fittype = "spline"+Knots
            self.Fitbox[1].SetItems(List)
            self.Fitbox[1].SetSelection(1)
            self.FitKnots = Knots

        if self.Fitbox[1].GetSelection() == 1:
            Knots = self.Fitbox[1].GetValue()
            Knots = filter(lambda x: x.isdigit(), Knots)
            self.FitKnots = Knots
            Fitting.fittype = "spline"+Knots
            self.parent.StatusBar.SetStatusText("You can change the number"+
               " of knots. Check 'Preference>Verbose Mode' to view the spline.")
        elif self.Fitbox[1].GetSelection() == 2:
            Fitting.fittype = "model function"
            self.parent.StatusBar.SetStatusText("This is iterative. Press"+
                 " 'Fit' multiple times. If it does not converge, use splines.")
        else:
            self.parent.StatusBar.SetStatusText("")
        Fitting.function = self.active_fct
        Fitting.interval = [self.startcrop, self.endcrop]
        Fitting.values = 1*self.active_parms[1]
        Fitting.valuestofit = 1*self.active_parms[2]
        Fitting.weights = self.Fitbox[5].GetValue()
        Fitting.ApplyParameters()
        return Fitting

        
    def Fit_function(self, event=None):
        """ Call the fit function. """
        # Make a busy cursor
        wx.BeginBusyCursor()
        # Apply parameters
        # This also applies the background correction, if present
        self.apply_parameters()
        # Create instance of fitting class
        Fitting = self.Fit_create_instance()
        try:
            Fitting.least_square()
        except ValueError:
            # I sometimes had this on Windows. It is caused by fitting to
            # a .SIN file without selection proper channels first.
            print "There was an Error fitting. Please make sure that you\n"+\
                  "are fitting in a proper channel domain."
            wx.EndBusyCursor()
            return
        parms = Fitting.valuesoptim
        self.chi2 = Fitting.chi
        for i in np.arange(len(parms)):
            self.active_parms[1][i] = parms[i]
            self.spincontrol[i].SetValue(parms[i])
        # Plot everthing
        self.PlotAll()
        # Return cursor to normal
        wx.EndBusyCursor()


    def Fit_WeightedFitCheck(self, event=None):
        """ Enable Or disable variance calculation, dependent on 
            "Weighted Fit" checkbox
        """
        #self.Fitbox=[ fitbox, weightedfitdrop, fittext, fittext2, fittextvar,
        #                fitspin, buttonfit ]
        weighted = (self.Fitbox[1].GetSelection() != 0)
        if weighted is True:
            self.Fitbox[2].Enable()
            self.Fitbox[3].Enable()
            self.Fitbox[4].Enable()
            self.Fitbox[5].Enable()
        else:
            self.Fitbox[2].Disable()
            self.Fitbox[3].Disable()
            self.Fitbox[4].Disable()
            self.Fitbox[5].Disable()


    def MakeStaticBoxSizer(self, boxlabel):
        """ Create a Box with check boxes (fit yes/no) and possibilities to 
            change initial values for fitting.

            Parameters:
            *boxlabel*: The name of the box (is being displayed)
            *self.active_parms[0]*: A list of things to put into the box

            Returns:
            *sizer*: The static Box
            *check*: The (un)set checkboxes
            *spin*: The spin text fields
        """
        box = wx.StaticBox(self.panelsettings, label=boxlabel)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        check = list()
        spin = list()
        for label in self.active_parms[0]:
            sizerh = wx.BoxSizer(wx.HORIZONTAL)
            checkbox = wx.CheckBox(self.panelsettings, label=label)
            # We needed to "from wx.lib.agw import floatspin" to get this:
            spinctrl = edclasses.FloatSpin(self.panelsettings, digits=10,
                                           increment=.01)
            sizerh.Add(spinctrl)
            sizerh.Add(checkbox)
            sizer.Add(sizerh)
            # Put everything into lists to be able to refer to it later
            check.append(checkbox)
            spin.append(spinctrl)
        return sizer, check, spin


    def OnSize(self, event):
        """ Resize the fitting Panel, when Window is resized. """
        size = self.parent.notebook.GetSize()
        tabsize = 33
        size[1] = size[1] - tabsize
        self.sp.SetSize(size)


    def PlotAll(self, event=None):
        """
        This function plots the whole correlation and residuals canvas.
        We do:
        - Channel selection
        - Background correction
        - Apply Parameters (separate function)
        - Drawing of plots
        """
        if self.dataexpfull is not None:
            if self.startcrop == self.endcrop:
                # self.bgcorrect is background correction
                self.dataexp = 1*self.dataexpfull
                self.taufull = self.dataexpfull[:,0]
                self.tau = 1*self.taufull
                self.startcrop = 0
                self.endcrop = len(self.taufull)
            else:
                self.dataexp = 1*self.dataexpfull[self.startcrop:self.endcrop]
                self.taufull = self.dataexpfull[:,0]
                self.tau = 1*self.dataexp[:,0]
                # If startcrop is larger than the lenght of dataexp,
                # We will not have an array. Prevent that.
                if len(self.tau) == 0:
                    self.tau = 1*self.taufull
                    self.dataexp = 1*self.dataexpfull
            try:
                self.taufull[self.startcrop]
                self.taufull[self.endcrop-1]
            except:
                self.startcrop = 0
                self.endcrop = len(self.taufull)
                self.tau = 1*self.taufull
                self.dataexp = 1*self.dataexpfull
        else:
            # We have to check if the startcrop and endcrop parameters are
            # inside the taufull array.
            try:
                # Raises IndexError if index out of bounds
                self.taufull[self.startcrop]
                # Raises TypeError if self.endcrop is not an int.
                self.taufull[self.endcrop-1]
            except (IndexError, TypeError):
                self.tau = 1*self.taufull
                self.endcrop = len(self.taufull)
                self.startcrop = 0
            else:
                self.tau = 1*self.taufull[self.startcrop:self.endcrop]

        ## ## Channel selection
        ## # Crops the array *self.dataexpfull* from *start* (int) to *end* (int)
        ## # and assigns the result to *self.dataexp*. If *start* and *end* are 
        ## # equal (or not given), *self.dataexp* will be equal to 
        ## # *self.dataexpfull*.
        ## self.parent.OnFNBPageChanged(e=None, Page=self)

        ## Calculate trace average
        if self.trace is not None:
            # Average of the current pages trace
            self.traceavg = self.trace[:,1].mean()
        # Perform Background correction
        self.dataexp = self.CorrectDataexp(self.dataexp)
        ## Apply parameters
        self.apply_parameters()
        # Calculate correlation function from parameters
        self.calculate_corr()
        ## Drawing of correlation plot
        # Plots self.dataexp and the calcualted correlation function 
        # self.datacorr into the upper canvas.
        # Create a line @ y=zero:

        zerostart = self.tau[0]
        zeroend = self.tau[-1]
        datazero = [[zerostart, 0], [zeroend,0]]

        ## Check out the DEMO option and make change the plot:
        try:
            if DEMO == True:
                width = 4
                colexp = "black"
                colfit = "red"
            else:
                width = 1
                colexp = "grey"
                colfit = "blue"
        except:
            # Don't raise any unnecessary erros
            width = 1   
            colexp = "grey"  
            colfit = "blue"

        linezero = plot.PolyLine(datazero, colour='orange',  width=width)
        if self.dataexp is not None:
            ## Plot Correlation curves
            # Plot both, experimental and calculated data
            linecorr = plot.PolyLine(self.datacorr, legend='', colour=colfit,
                                     width=width)
            lineexp = plot.PolyLine(self.dataexp, legend='', colour=colexp,
                                    width=width)
            # Draw linezero first, so it is in the background
            PlotCorr = plot.PlotGraphics([linezero, lineexp, linecorr], 
                                xLabel='Lag time τ [ms]', yLabel='G(τ)')
            self.canvascorr.Draw(PlotCorr)
            ## Plot residuals
            self.resid = np.zeros((len(self.tau), 2))
            self.resid[:, 0] = self.tau
            self.resid[:, 1] = self.dataexp[:, 1] - self.datacorr[:, 1]
            lineres = plot.PolyLine(self.resid, legend='', colour=colfit,
                                    width=width)
            PlotRes = plot.PlotGraphics([linezero, lineres], 
                                   xLabel='Lag time τ [ms]', yLabel='Residuals')
            self.canvaserr.Draw(PlotRes)

            # Also check if chi squared has been calculated. This is not the
            # case when a session has been loaded. Do it.
            # (Usually it is done right after fitting)
            if self.chi2 is None:
                Fitting = self.Fit_create_instance(noplots=True)
                Fitting.parmoptim = Fitting.fitparms
                self.chi2 = Fitting.get_chi_squared()
        else:
            linecorr = plot.PolyLine(self.datacorr, legend='', colour='blue',
                                     width=1)
            PlotCorr = plot.PlotGraphics([linezero, linecorr],
                       xLabel='Lag time τ [ms]', yLabel='G(τ)')
            self.canvascorr.Draw(PlotCorr)
        self.parent.OnFNBPageChanged()

    def settings(self):
        """ Here we define, what should be displayed at the left side
            of the window.
            Parameters:
        """
        # Title
     
        # Create empty tab title
        self.tabtitle = wx.TextCtrl(self.panelsettings, value="", 
                                    size=(self.sizepanelx, -1))
        # Create StaticBoxSizer
        box1, check, spin = self.MakeStaticBoxSizer("Fit parameters")
        # Make the check boxes and spin-controls available everywhere
        self.checkboxes = check
        self.spincontrol = spin
        # Show what is inside active_parms
        labels = self.active_parms[0]
        parameters = self.active_parms[1]
        parameterstofit = self.active_parms[2]
        # Set initial values given by user/programmer for Diffusion Model
        for i in np.arange(len(labels)):
            self.checkboxes[i].SetValue(parameterstofit[i]) 
            self.spincontrol[i].SetValue(parameters[i])
            self.spincontrol[i].increment()

        # Put everything together
        self.panelsettings.sizer = wx.BoxSizer(wx.VERTICAL)
        self.panelsettings.sizer.Add(self.tabtitle)
        self.panelsettings.sizer.Add(box1)

        # Add button "Apply"
        buttonapply = wx.Button(self.panelsettings, label="Apply")
        self.Bind(wx.EVT_BUTTON, self.PlotAll, buttonapply)
        # Add it to the parameters box
        box1.Add(buttonapply)
        ## Add fitting Box
        fitbox = wx.StaticBox(self.panelsettings, label="Data fitting")
        fitsizer = wx.StaticBoxSizer(fitbox, wx.VERTICAL)
        # Add a checkbox for weighted fitting
        weightedfitdrop = wx.ComboBox(self.panelsettings)
        self.weightlist = ["No weights", "Spline (5 knots)", "Model function"]
        weightedfitdrop.SetItems(self.weightlist)
        weightedfitdrop.SetSelection(0)
        fitsizer.Add(weightedfitdrop)
         # WeightedFitCheck() Enables or Disables the variance part
        weightedfitdrop.Bind(wx.EVT_COMBOBOX, self.Fit_WeightedFitCheck)
        # Add the variance part.
        # In order to do a weighted fit, we need to calculate the variance
        # at each point of the experimental data array.
        # In order to do that, we need to know how many data points from left
        # and right of the interesting data point we want to include in that
        # calculation.
        fittext = wx.StaticText(self.panelsettings, 
                                label="Calculation of Variance.")
        fitsizer.Add(fittext)
        fittext2 = wx.StaticText(self.panelsettings, 
                                 label="Include n points from left and right,")
        fitsizer.Add(fittext2)
        fitsizerspin = wx.BoxSizer(wx.HORIZONTAL)
        fittextvar = wx.StaticText(self.panelsettings, label="n = ")
        fitspin = wx.SpinCtrl(self.panelsettings, -1, initial=3, min=1, max=100)
        fitsizerspin.Add(fittextvar)
        fitsizerspin.Add(fitspin)
        fitsizer.Add(fitsizerspin)

        # Add button "Fit", but not active
        buttonfit = wx.Button(self.panelsettings, label="Fit")
        self.Bind(wx.EVT_BUTTON, self.Fit_function, buttonfit)
        fitsizer.Add(buttonfit)
        self.panelsettings.sizer.Add(fitsizer)

        # Squeeze everything into the sizer
        self.panelsettings.SetSizer(self.panelsettings.sizer)
        # This is also necessary in Windows
        self.panelsettings.Layout()
        self.panelsettings.Show()

        # Make all the stuff available for everyone
        self.Fitbox = [ fitbox, weightedfitdrop, fittext, fittext2, fittextvar,
                        fitspin, buttonfit ]
        # Disable Fitting since no data has been loaded yet
        for element in self.Fitbox:
            element.Disable()


