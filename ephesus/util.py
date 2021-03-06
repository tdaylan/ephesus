import sys
import os

import numpy as np

from tqdm import tqdm

import time as timemodu

#from numba import jit, prange
import h5py
import fnmatch

import astropy
import astropy as ap
from astropy.io import fits
from astropy.coordinates import SkyCoord
from astropy.io import fits

import pandas as pd

import multiprocessing
from functools import partial

import scipy as sp
import scipy.interpolate

import astroquery
import astroquery.mast

import matplotlib.pyplot as plt

# own modules
import tdpy
from tdpy.util import summgene
import lygos
import miletos
import hattusa


def anim_tmptdete(timefull, lcurfull, meantimetmpt, lcurtmpt, pathimag, listindxtimeposimaxm, corrprod, corr, strgextn='', colr=None):
    
    numbtimefull = timefull.size
    numbtimekern = lcurtmpt.size
    numbtimefullruns = numbtimefull - numbtimekern
    indxtimefullruns = np.arange(numbtimefullruns)
    
    listpath = []
    cmnd = 'convert -delay 20'
    
    numbtimeanim = min(200, numbtimefullruns)
    indxtimefullrunsanim = np.random.choice(indxtimefullruns, size=numbtimeanim, replace=False)
    indxtimefullrunsanim = np.sort(indxtimefullrunsanim)

    for tt in indxtimefullrunsanim:
        
        path = pathimag + 'lcur%s_%08d.pdf' % (strgextn, tt)
        listpath.append(path)
        if not os.path.exists(path):
            plot_tmptdete(timefull, lcurfull, tt, meantimetmpt, lcurtmpt, path, listindxtimeposimaxm, corrprod, corr)
        cmnd += ' %s' % path
    
    pathanim = pathimag + 'lcur%s.gif' % strgextn
    cmnd += ' %s' % pathanim
    print('cmnd')
    print(cmnd)
    os.system(cmnd)
    cmnd = 'rm'
    for path in listpath:
        cmnd += ' ' + path
    os.system(cmnd)


def plot_tmptdete(timefull, lcurfull, tt, meantimetmpt, lcurtmpt, path, listindxtimeposimaxm, corrprod, corr):
    
    numbtimekern = lcurtmpt.size
    indxtimekern = np.arange(numbtimekern)
    numbtimefull = lcurfull.size
    numbtimefullruns = numbtimefull - numbtimekern
    indxtimefullruns = np.arange(numbtimefullruns)
    difftime = timefull[1] - timefull[0]
    
    figr, axis = plt.subplots(5, 1, figsize=(8, 11))
    
    # plot the whole light curve
    proc_axiscorr(timefull, lcurfull, axis[0], listindxtimeposimaxm)
    
    # plot zoomed-in light curve
    minmindx = max(0, tt - int(numbtimekern / 4))
    maxmindx = min(numbtimefullruns - 1, tt + int(5. * numbtimekern / 4))
    indxtime = np.arange(minmindx, maxmindx + 1)
    print('indxtime')
    summgene(indxtime)
    proc_axiscorr(timefull, lcurfull, axis[1], listindxtimeposimaxm, indxtime=indxtime)
    
    # plot template
    axis[2].plot(timefull[0] + meantimetmpt + tt * difftime, lcurtmpt, color='b', marker='v')
    axis[2].set_ylabel('Template')
    axis[2].set_xlim(axis[1].get_xlim())

    # plot correlation
    axis[3].plot(timefull[0] + meantimetmpt + tt * difftime, corrprod[tt, :], color='red', marker='o')
    axis[3].set_ylabel('Correlation')
    axis[3].set_xlim(axis[1].get_xlim())
    
    # plot the whole total correlation
    print('indxtimefullruns')
    summgene(indxtimefullruns)
    print('timefull')
    summgene(timefull)
    print('corr')
    summgene(corr)
    axis[4].plot(timefull[indxtimefullruns], corr, color='m', marker='o', ms=1, rasterized=True)
    axis[4].set_ylabel('Total correlation')
    
    titl = 'C = %.3g' % corr[tt]
    axis[0].set_title(titl)

    limtydat = axis[0].get_ylim()
    axis[0].fill_between(timefull[indxtimekern+tt], limtydat[0], limtydat[1], alpha=0.4)
    print('Writing to %s...' % path)
    plt.savefig(path)
    plt.close()
    

def proc_axiscorr(time, lcur, axis, listindxtimeposimaxm, indxtime=None, colr='k', timeoffs=2457000):
    
    if indxtime is None:
        indxtimetemp = np.arange(time.size)
    else:
        indxtimetemp = indxtime
    axis.plot(time[indxtimetemp], lcur[indxtimetemp], ls='', marker='o', color=colr, rasterized=True, ms=0.5)
    maxmydat = axis.get_ylim()[1]
    for kk in range(len(listindxtimeposimaxm)):
        if listindxtimeposimaxm[kk] in indxtimetemp:
            axis.plot(time[listindxtimeposimaxm[kk]], maxmydat, marker='v', color='b')
    #print('timeoffs')
    #print(timeoffs)
    #axis.set_xlabel('Time [BJD-%d]' % timeoffs)
    axis.set_ylabel('Relative flux')
    

def srch_flar(time, lcur, typeverb=1, strgextn='', numbkern=3, minmscalfalltmpt=None, maxmscalfalltmpt=None, \
                                                                    pathimag=None, boolplot=True, boolanim=False, thrs=None):

    minmtime = np.amin(time)
    timeflartmpt = 0.
    amplflartmpt = 1.
    scalrisetmpt = 0. / 24.
    difftime = np.amin(time[1:] - time[:-1])
    
    print('time')
    summgene(time)
    print('difftime')
    print(difftime)
    if minmscalfalltmpt is None:
        minmscalfalltmpt = 3 * difftime
    
    if maxmscalfalltmpt is None:
        maxmscalfalltmpt = 3. / 24.
    
    if typeverb > 1:
        print('lcurtmpt')
        summgene(lcurtmpt)
    
    indxscalfall = np.arange(numbkern)
    listscalfalltmpt = np.linspace(minmscalfalltmpt, maxmscalfalltmpt, numbkern)
    print('listscalfalltmpt')
    print(listscalfalltmpt)
    listcorr = []
    listlcurtmpt = [[] for k in indxscalfall]
    meantimetmpt = [[] for k in indxscalfall]
    for k in indxscalfall:
        numbtimekern = 3 * int(listscalfalltmpt[k] / difftime)
        print('numbtimekern')
        print(numbtimekern)
        meantimetmpt[k] = np.arange(numbtimekern) * difftime
        print('meantimetmpt[k]')
        summgene(meantimetmpt[k])
        if numbtimekern == 0:
            raise Exception('')
        listlcurtmpt[k] = hattusa.retr_lcurmodl_flarsing(meantimetmpt[k], timeflartmpt, amplflartmpt, scalrisetmpt, listscalfalltmpt[k])
        if not np.isfinite(listlcurtmpt[k]).all():
            raise Exception('')
        
    corr, listindxtimeposimaxm, timefull, lcurfull = corr_tmpt(time, lcur, meantimetmpt, listlcurtmpt, thrs=thrs, boolanim=boolanim, boolplot=boolplot, \
                                                                                            typeverb=typeverb, strgextn=strgextn, pathimag=pathimag)

    #corr, listindxtimeposimaxm, timefull, rflxfull = ephesus.corr_tmpt(gdat.timethis, gdat.rflxthis, gdat.listtimetmpt, gdat.listdflxtmpt, \
    #                                                                    thrs=gdat.thrstmpt, boolanim=gdat.boolanimtmpt, boolplot=gdat.boolplottmpt, \
     #                                                               typeverb=gdat.typeverb, strgextn=gdat.strgextnthis, pathimag=gdat.pathtargimag)
                
    return corr, listindxtimeposimaxm, meantimetmpt, timefull, lcurfull


#@jit(nopython=True, parallel=True, fastmath=True, nogil=True)
def corr_arryprod(lcurtemp, lcurtmpt, numbkern):
    
    # correlate
    corrprod = [[] for k in range(numbkern)]
    for k in range(numbkern):
        corrprod[k] = lcurtmpt[k] * lcurtemp[k]
    
    return corrprod


#@jit(parallel=True)
def corr_copy(indxtimefullruns, lcurstan, indxtimekern, numbkern):
    """
    Make a matrix with rows as the shifted and windowed copies of the time series.
    """
    print('corr_copy()')
    listlcurtemp = [[] for k in range(numbkern)]
    for k in range(numbkern):
        numbtimefullruns = indxtimefullruns[k].size
        numbtimekern = indxtimekern[k].size
        listlcurtemp[k] = np.empty((numbtimefullruns, numbtimekern))
        print('k')
        print(k)
        print('numbtimefullruns')
        print(numbtimefullruns)
        print('numbtimekern')
        print(numbtimekern)

        for t in range(numbtimefullruns):
            listlcurtemp[k][t, :] = lcurstan[indxtimefullruns[k][t]+indxtimekern[k]]
        print('listlcurtemp[k]')
        summgene(listlcurtemp[k])
    print('')
    return listlcurtemp


def corr_tmpt(time, lcur, meantimetmpt, listlcurtmpt, typeverb=2, thrs=None, strgextn='', pathimag=None, boolplot=True, boolanim=False):
    
    timeoffs = np.amin(time) // 1000
    timeoffs *= 1000
    time -= timeoffs
    
    if typeverb > 1:
        timeinit = timemodu.time()
    
    print('corr_tmpt()')
    print('time')
    summgene(time)
    
    if lcur.ndim > 1:
        raise Exception('')
    
    for lcurtmpt in listlcurtmpt:
        if not np.isfinite(lcurtmpt).all():
            raise Exception('')

    if not np.isfinite(lcur).all():
        raise Exception('')

    numbtime = lcur.size
    
    numbkern = len(listlcurtmpt)
    indxkern = np.arange(numbkern)
    
    # count gaps
    difftime = time[1:] - time[:-1]
    minmdifftime = np.amin(difftime)
    difftimesort = np.sort(difftime)[::-1]
    print('difftimesort')
    for k in range(difftimesort.size):
        print(difftimesort[k] / minmdifftime)
        if k == 20:
             break
    
    boolthrsauto = thrs is None
    
    print('temp: setting boolthrsauto')
    thrs = 1.
    boolthrsauto = False
    
    # number of time samples in the kernel
    numbtimekern = np.empty(numbkern, dtype=int)
    indxtimekern = [[] for k in indxkern]
    
    # take out the mean
    listlcurtmptstan = [[] for k in indxkern]
    for k in indxkern:
        listlcurtmptstan[k] = np.copy(listlcurtmpt[k])
        listlcurtmptstan[k] -= np.mean(listlcurtmptstan[k])
        numbtimekern[k] = listlcurtmptstan[k].size
        indxtimekern[k] = np.arange(numbtimekern[k])

    minmtimechun = 3 * 3. / 24. / 60. # [days]
    print('minmdifftime * 24 * 60')
    print(minmdifftime * 24 * 60)
    listlcurfull = []
    indxtimebndr = np.where(difftime > minmtimechun)[0]
    indxtimebndr = np.concatenate([np.array([0]), indxtimebndr, np.array([numbtime - 1])])
    numbchun = indxtimebndr.size - 1
    indxchun = np.arange(numbchun)
    corrchun = [[[] for k in indxkern] for l in indxchun]
    listindxtimeposimaxm = [[[] for k in indxkern] for l in indxchun]
    listlcurchun = [[] for l in indxchun]
    listtimechun = [[] for l in indxchun]
    print('indxtimebndr')
    print(indxtimebndr)
    print('numbchun')
    print(numbchun)
    for l in indxchun:
        
        print('Chunk %d...' % l)
        
        minmindxtimeminm = 0
        minmtime = time[indxtimebndr[l]+1]
        print('minmtime')
        print(minmtime)
        print('indxtimebndr[l]')
        print(indxtimebndr[l])
        maxmtime = time[indxtimebndr[l+1]]
        print('maxmtime')
        print(maxmtime)
        numb = int(round((maxmtime - minmtime) / minmdifftime))
        print('numb')
        print(numb)
        
        if numb == 0:
            print('Skipping due to chunk with single point...')
            continue

        timechun = np.linspace(minmtime, maxmtime, numb)
        listtimechun[l] = timechun
        print('timechun')
        summgene(timechun)
        
        if float(indxtimebndr[l+1] - indxtimebndr[l]) / numb < 0.8:
            print('Skipping due to undersampled chunk...')
            continue

        numbtimefull = timechun.size
        print('numbtimefull')
        print(numbtimefull)
        
        indxtimechun = np.arange(indxtimebndr[l], indxtimebndr[l+1] + 1)
        
        print('time[indxtimechun]')
        summgene(time[indxtimechun])
        
        # interpolate
        lcurchun = scipy.interpolate.interp1d(time[indxtimechun], lcur[indxtimechun])(timechun)
        
        if indxtimechun.size != timechun.size:
            print('time[indxtimechun]')
            if timechun.size < 50:
                for timetemp in time[indxtimechun]:
                    print(timetemp)
            summgene(time[indxtimechun])
            print('timechun')
            if timechun.size < 50:
                for timetemp in timechun:
                    print(timetemp)
            summgene(timechun)
            #raise Exception('')

        # take out the mean
        lcurchun -= np.mean(lcurchun)
        
        listlcurchun[l] = lcurchun
        
        # size of the full grid minus the kernel size
        numbtimefullruns = np.empty(numbkern, dtype=int)
        indxtimefullruns = [[] for k in indxkern]
        
        # find the correlation
        for k in indxkern:
            print('Kernel %d...' % k)
            
            if numb < numbtimekern[k]:
                print('Skipping due to chunk shorther than the kernel...')
                continue
            
            # find the total correlation (along the time delay axis)
            corrchun[l][k] = scipy.signal.correlate(lcurchun, listlcurtmptstan[k], mode='valid')
            print('corrchun[l][k]')
            summgene(corrchun[l][k])
        
            numbtimefullruns[k] = numbtimefull - numbtimekern[k] + 1
            indxtimefullruns[k] = np.arange(numbtimefullruns[k])
        
            print('numbtimekern[k]')
            print(numbtimekern[k])
            print('numbtimefullruns[k]')
            print(numbtimefullruns[k])

            if boolthrsauto:
                perclowrcorr = np.percentile(corr[k],  1.)
                percupprcorr = np.percentile(corr[k], 99.)
                indx = np.where((corr[k] < percupprcorr) & (corr[k] > perclowrcorr))[0]
                medicorr = np.median(corr[k])
                thrs = np.std(corr[k][indx]) * 7. + medicorr

            if not np.isfinite(corrchun[l][k]).all():
                raise Exception('')

            # determine the threshold on the maximum correlation
            if typeverb > 1:
                print('thrs')
                print(thrs)

            # find triggers
            listindxtimeposi = np.where(corrchun[l][k] > thrs)[0]
            if typeverb > 1:
                print('listindxtimeposi')
                summgene(listindxtimeposi)
            
            # cluster triggers
            listtemp = []
            listindxtimeposiptch = []
            for kk in range(len(listindxtimeposi)):
                listtemp.append(listindxtimeposi[kk])
                if kk == len(listindxtimeposi) - 1 or listindxtimeposi[kk] != listindxtimeposi[kk+1] - 1:
                    listindxtimeposiptch.append(np.array(listtemp))
                    listtemp = []
            
            if typeverb > 1:
                print('listindxtimeposiptch')
                summgene(listindxtimeposiptch)

            listindxtimeposimaxm[l][k] = np.empty(len(listindxtimeposiptch), dtype=int)
            for kk in range(len(listindxtimeposiptch)):
                indxtemp = np.argmax(corrchun[l][k][listindxtimeposiptch[kk]])
                listindxtimeposimaxm[l][k][kk] = listindxtimeposiptch[kk][indxtemp]
            
            if typeverb > 1:
                print('listindxtimeposimaxm[l][k]')
                summgene(listindxtimeposimaxm[l][k])
            
            if boolplot or boolanim:
                strgextntotl = strgextn + '_kn%02d' % k
        
            if boolplot:
                if numbtimefullruns[k] <= 0:
                    continue
                numbdeteplot = min(len(listindxtimeposimaxm[l][k]), 10)
                figr, axis = plt.subplots(2, 1, figsize=(8, 8), sharex=True)
                
                #proc_axiscorr(time[indxtimechun], lcur[indxtimechun], axis[0], listindxtimeposimaxm[l][k])
                proc_axiscorr(timechun, lcurchun, axis[0], listindxtimeposimaxm[l][k])
                
                axis[1].plot(timechun[indxtimefullruns[k]], corrchun[l][k], color='m', ls='', marker='o', ms=1, rasterized=True)
                axis[1].set_ylabel('C')
                axis[1].set_xlabel('Time [BJD-%d]' % timeoffs)
                
                path = pathimag + 'lcurflar_ch%02d%s.pdf' % (l, strgextntotl)
                plt.subplots_adjust(left=0.2, bottom=0.2, hspace=0)
                print('Writing to %s...' % path)
                plt.savefig(path)
                plt.close()
                
                for n in range(numbdeteplot):
                    figr, axis = plt.subplots(figsize=(8, 4), sharex=True)
                    for i in range(numbdeteplot):
                        indxtimeplot = indxtimekern[k] + listindxtimeposimaxm[l][k][i]
                        proc_axiscorr(timechun, lcurchun, axis, listindxtimeposimaxm[l][k], indxtime=indxtimeplot, timeoffs=timeoffs)
                    path = pathimag + 'lcurflar_ch%02d%s_det.pdf' % (l, strgextntotl)
                    print('Writing to %s...' % path)
                    plt.savefig(path)
                    plt.close()
                
            print('Done with the plot...')
            if False and boolanim:
                path = pathimag + 'lcur%s.gif' % strgextntotl
                if not os.path.exists(path):
                    anim_tmptdete(timefull, lcurfull, meantimetmpt[k], listlcurtmpt[k], pathimag, \
                                                                listindxtimeposimaxm[l][k], corrprod[k], corrchun[l][k], strgextn=strgextntotl)
                else:
                    print('Skipping animation for kernel %d...' % k)
    if typeverb > 1:
        print('Delta T (corr_tmpt, rest): %g' % (timemodu.time() - timeinit))

    return corrchun, listindxtimeposimaxm, listtimechun, listlcurchun


def read_qlop(path, pathcsvv=None, stdvcons=None):
    
    print('Reading QLP light curve from %s...' % path)
    objtfile = h5py.File(path, 'r')
    time = objtfile['LightCurve/BJD'][()] + 2457000.
    tmag = objtfile['LightCurve/AperturePhotometry/Aperture_002/RawMagnitude'][()]
    flux = 10**(-(tmag - np.nanmedian(tmag)) / 2.5)
    flux /= np.nanmedian(flux) 
    arry = np.empty((flux.size, 3))
    arry[:, 0] = time
    arry[:, 1] = flux
    if stdvcons is None:
        stdvcons = 1e-3
        print('Assuming a constant photometric precision of %g for the QLP light curve.' % stdvcons)
    stdv = np.zeros_like(flux) + stdvcons
    arry[:, 2] = stdv
    
    # filter out bad data
    indx = np.where((objtfile['LightCurve/QFLAG'][()] == 0) & np.isfinite(flux) & np.isfinite(time) & np.isfinite(stdv))[0]
    arry = arry[indx, :]
    if not np.isfinite(arry).all():
        print('arry')
        summgene(arry)
        raise Exception('Light curve is not finite')
    if arry.shape[0] == 0:
        print('arry')
        summgene(arry)
        raise Exception('Light curve has no data points')

    if pathcsvv is not None:
        print('Writing to %s...' % pathcsvv)
        np.savetxt(pathcsvv, arry, delimiter=',')

    return arry


# transits

def retr_indxtimetran(time, epoc, peri, dura, booloutt=False, boolseco=False):
    
    '''
    
    Duration is in hours.

    '''
    if not np.isfinite(time).all():
        raise Exception('')
    
    if not np.isfinite(dura).all():
        raise Exception('')
    
    listindxtimetran = []
    
    if np.isfinite(peri):
        intgminm = np.floor((np.amin(time) - epoc - dura / 48.) / peri)
        intgmaxm = np.ceil((np.amax(time) - epoc - dura / 48.) / peri)
        arry = np.arange(intgminm, intgmaxm + 1)
    else:
        arry = np.arange(1)

    if boolseco:
        offs = 0.5
    else:
        offs = 0.

    for n in arry:
        timeinit = epoc + (n + offs) * peri - dura / 48.
        timefinl = epoc + (n + offs) * peri + dura / 48.
        indxtimetran = np.where((time > timeinit) & (time < timefinl))[0]
        listindxtimetran.append(indxtimetran)
    indxtimetran = np.concatenate(listindxtimetran)
    indxtimetran = np.unique(indxtimetran)
    
    if booloutt:
        indxtimeretr = np.setdiff1d(np.arange(time.size), indxtimetran)
    else:
        indxtimeretr = indxtimetran
    
    return indxtimeretr
    

def retr_timeedge(time, lcur, timebrek, \
                  # Boolean flag to add breaks at discontinuties
                  booladdddiscbdtr, \
                  timescal, \
                 ):
    
    difftime = time[1:] - time[:-1]
    indxtimebrek = np.where(difftime > timebrek)[0]
    
    if booladdddiscbdtr:
        listindxtimebrekaddi = []
        for k in range(3, len(time) - 3):
            diff = lcur[k] - lcur[k-1]
            if abs(diff) > 5 * np.std(lcur[k-3:k]) and abs(diff) > 5 * np.std(lcur[k:k+3]):
                listindxtimebrekaddi.append(k)
                #print('k')
                #print(k)
                #print('diff')
                #print(diff)
                #print('np.std(lcur[k:k+3])')
                #print(np.std(lcur[k:k+3]))
                #print('np.std(lcur[k-3:k])')
                #print(np.std(lcur[k-3:k]))
                #print('')
        listindxtimebrekaddi = np.array(listindxtimebrekaddi, dtype=int)
        indxtimebrek = np.concatenate([indxtimebrek, listindxtimebrekaddi])
        indxtimebrek = np.unique(indxtimebrek)

    timeedge = [0, np.inf]
    for k in indxtimebrek:
        timeedgeprim = (time[k] + time[k+1]) / 2.
        timeedge.append(timeedgeprim)
    timeedge = np.array(timeedge)
    timeedge = np.sort(timeedge)

    return timeedge


def bdtr_tser( \
              # time grid
              time, \
              # dependent variable
              lcur, \
              
              # epoc, period, and duration of mask
              epocmask=None, perimask=None, duramask=None, \
              
              # verbosity level
              typeverb=1, \
              
              # minimum gap to break the time-series into regions
              timebrek=None, \
              
              # Boolean flag to add breaks at vertical discontinuties
              booladdddiscbdtr=False, \
              
              # baseline detrend type
              ## 'medi':
              ## 'spln':
              typebdtr=None, \
              
              # order of the spline
              ordrspln=None, \
              # time scale of the spline detrending
              timescalbdtrspln=None, \
              # time scale of the median detrending
              timescalbdtrmedi=None, \
             ):
    
    if typebdtr is None:
        typebdtr = 'spln'
    if timebrek is None:
        timebrek = 0.1 # [day]
    if ordrspln is None:
        ordrspln = 3
    if timescalbdtrspln is None:
        timescalbdtrspln = 0.5
    if timescalbdtrmedi is None:
        timescalbdtrmedi = 0.5 # [hour]
    
    if typebdtr == 'spln':
        timescal = timescalbdtrspln
    else:
        timescal = timescalbdtrmedi
    if typeverb > 0:
        print('Detrending the light curve with at a time scale of %.g days...' % timescal)
        if epocmask is not None:
            print('Using a specific ephemeris to mask out transits while detrending...')
        
    # determine the times at which the light curve will be broken into pieces
    timeedge = retr_timeedge(time, lcur, timebrek, booladdddiscbdtr, timescal)

    numbedge = len(timeedge)
    numbregi = numbedge - 1
    indxregi = np.arange(numbregi)
    lcurbdtrregi = [[] for i in indxregi]
    indxtimeregi = [[] for i in indxregi]
    indxtimeregioutt = [[] for i in indxregi]
    listobjtspln = [[] for i in indxregi]
    for i in indxregi:
        if typeverb > 1:
            print('i')
            print(i)
        # find times inside the region
        indxtimeregi[i] = np.where((time >= timeedge[i]) & (time <= timeedge[i+1]))[0]
        timeregi = time[indxtimeregi[i]]
        lcurregi = lcur[indxtimeregi[i]]
        
        # mask out the transits
        if epocmask is not None and len(epocmask) > 0:
            # find the out-of-transit times
            indxtimetran = []
            for k in range(epocmask.size):
                indxtimetran.append(retr_indxtimetran(timeregi, epocmask[k], perimask[k], duramask[k]))
            indxtimetran = np.concatenate(indxtimetran)
            indxtimeregioutt[i] = np.setdiff1d(np.arange(timeregi.size), indxtimetran)
        else:
            indxtimeregioutt[i] = np.arange(timeregi.size)
        
        if typebdtr == 'medi':
            listobjtspln = None
            size = int(timescalbdtrmedi / np.amin(timeregi[1:] - timeregi[:-1]))
            if size == 0:
                print('timescalbdtrmedi')
                print(timescalbdtrmedi)
                print('np.amin(timeregi[1:] - timeregi[:-1])')
                print(np.amin(timeregi[1:] - timeregi[:-1]))
                print('lcurregi')
                summgene(lcurregi)
                raise Exception('')
            lcurbdtrregi[i] = 1. + lcurregi - scipy.ndimage.median_filter(lcurregi, size=size)
        
        if typebdtr == 'spln':
            if typeverb > 1:
                print('lcurregi[indxtimeregioutt[i]]')
                summgene(lcurregi[indxtimeregioutt[i]])
            # fit the spline
            if lcurregi[indxtimeregioutt[i]].size > 0:
                if timeregi[indxtimeregioutt[i]].size < 4:
                    print('Warning! Only %d points available for spline! This will result in a trivial baseline-detrended light curve (all 1s).' \
                                                                                                                % timeregi[indxtimeregioutt[i]].size)
                    listobjtspln[i] = None
                    lcurbdtrregi[i] = np.ones_like(lcurregi)
                else:
                    minmtime = np.amin(timeregi[indxtimeregioutt[i]])
                    maxmtime = np.amax(timeregi[indxtimeregioutt[i]])
                    numbknot = int((maxmtime - minmtime) / timescalbdtrspln)
                    
                    timeknot = np.linspace(minmtime, maxmtime, numbknot)
                    
                    if numbknot >= 2:
                        print('%d knots used. Knot separation: %.3g hours' % (timeknot.size, 24 * (timeknot[1] - timeknot[0])))
                        timeknot = timeknot[1:-1]
                    
                        objtspln = scipy.interpolate.LSQUnivariateSpline(timeregi[indxtimeregioutt[i]], lcurregi[indxtimeregioutt[i]], timeknot, k=ordrspln)
                        lcurbdtrregi[i] = lcurregi - objtspln(timeregi) + 1.
                        listobjtspln[i] = objtspln
                    else:
                        lcurbdtrregi[i] = lcurregi - np.mean(lcurregi)
                        listobjtspln[i] = None
            else:
                lcurbdtrregi[i] = lcurregi
                listobjtspln[i] = None
            
            if typeverb > 1:
                print('lcurbdtrregi[i]')
                summgene(lcurbdtrregi[i])
                print('')

    return lcurbdtrregi, indxtimeregi, indxtimeregioutt, listobjtspln, timeedge


def retr_logg(radi, mass):
    
    logg = mass / radi**2

    return logg


def retr_noistess(magtinpt):
    
    nois = np.array([40., 40., 40., 90.,200.,700., 3e3, 2e4]) # [ppm]
    magt = np.array([ 2.,  4.,  6.,  8., 10., 12., 14., 16.])
    objtspln = scipy.interpolate.interp1d(magt, nois, fill_value='extrapolate')
    nois = objtspln(magtinpt)
    
    return nois


def retr_tmag(gdat, cntp):
    
    tmag = -2.5 * np.log10(cntp / 1.5e4 / gdat.listcade) + 10
    #tmag = -2.5 * np.log10(mlikfluxtemp) + 20.424
    
    #mlikmagttemp = 10**((mlikmagttemp - 20.424) / (-2.5))
    #stdvmagttemp = mlikmagttemp * stdvmagttemp / 1.09
    #gdat.stdvmagtrefr = 1.09 * gdat.stdvrefrrflx[o] / gdat.refrrflx[o]
    
    return tmag


def spaw_blsq(listperi, arrytser, minmtime, phasshft, listdcyc, listoffs, i):
    
    numbperi = len(listperi[i])
    numboffs = len(listoffs)
    indxoffs = np.arange(numboffs)
    numbdcyc = len(listdcyc)
    indxdcyc = np.arange(numbdcyc)
    
    listdept = np.zeros((numbperi, numbdcyc, numboffs))
    s2nr = np.zeros((numbperi, numbdcyc, numboffs))

    for k, peri in enumerate(listperi[i]):
        #timechec[k, 0] = timemodu.time()

        arrypcur = fold_tser(arrytser, minmtime, peri, boolsort=False, booldiagmode=False, phasshft=phasshft)
        
        #timechec[k, 1] = timemodu.time()

        vari = arrypcur[:, 2]**2
        weig = 1. / vari
        stdvdepttemp = np.sqrt(np.nanmean(vari))

        #timechec[k, 2] = timemodu.time()

        for l in indxdcyc:
            for m in indxoffs:
                
                #timechecloop[0][k, l, m] = timemodu.time()

                booltemp = (arrypcur[:, 0] + listdcyc[l] / 2. - listoffs[m]) % 1. < listdcyc[l]
                
                #timechecloop[1][k, l, m] = timemodu.time()

                indxitra = np.where(booltemp)[0]
                
                if indxitra.size == 0:
                    continue
                
                indxotra = np.where(~booltemp)[0]
                
                #timechecloop[2][k, l, m] = timemodu.time()

                #deptitra = np.nansum(arrypcur[indxitra, 1] * weig[indxitra]) / np.nansum(weig[indxitra])
                #deptotra = np.nansum(arrypcur[indxotra, 1] * weig[indxotra]) / np.nansum(weig[indxotra])
                
                deptitra = np.mean(arrypcur[indxitra, 1])
                deptotra = np.mean(arrypcur[indxotra, 1])
                
                #timechecloop[3][k, l, m] = timemodu.time()

                depttemp = deptotra - deptitra
                s2nrtemp = depttemp / stdvdepttemp
                listdept[k, l, m] = depttemp
                s2nr[k, l, m] = s2nrtemp
                
                #timechecloop[4][k, l, m] = timemodu.time()
                
    return listdept, s2nr


def exec_blsq( \
              arrytser, \
              minmdcyc=0.001, \
              # Boolean flag to enable multiprocessing
              boolmult=False, \
             ):
    
    dictblsqoutp = dict()
    
    timeinit = timemodu.time()

    numbtime = arrytser.shape[0]
    minmtime = np.amin(arrytser[:, 0])
    maxmtime = np.amax(arrytser[:, 0])
    indxtime = np.arange(numbtime)
    timeinit = timemodu.time()
    
    dictfact = retr_factconv()
    
    minmperi = 1.
    maxmperi = (maxmtime - minmtime) / 4.
    maxmperi = 1.4
    print('minmperi')
    print(minmperi)
    print('maxmperi')
    print(maxmperi)
    numbtranmaxm = (maxmtime - minmtime) / minmperi
    diffperi = (maxmtime - minmtime) / numbtranmaxm
    numbperi = int(4. * (maxmperi - minmperi) / diffperi)
    numbperi = 10000
    print('numbperi')
    print(numbperi)
    listperi = np.linspace(minmperi, maxmperi, numbperi)
    
    numbdcyc = 4
    maxmdcyc = 0.1
    listdcyc = np.linspace(minmdcyc, maxmdcyc, numbdcyc)
    
    numboffs = 3
    minmoffs = 0.
    maxmoffs = numboffs / (1 + numboffs)
    listoffs = np.linspace(minmoffs, maxmoffs, numboffs)
    
    dflx = arrytser[:, 1] - 1.
    stdvdflx = arrytser[:, 2]
    varidflx = stdvdflx**2
    
    phasshft = 0.5

    indxperi = np.arange(numbperi)
    indxdcyc = np.arange(numbdcyc)
    indxoffs = np.arange(numboffs)
    
    numbphas = 1000
    indxphas = np.arange(numbphas)
    binsphas = np.linspace(-phasshft, phasshft, numbphas + 1)
    meanphas = (binsphas[1:] + binsphas[:-1]) / 2.

    timechec = np.zeros((numbperi, 10))
    timechecloop = [np.zeros((numbperi, numbdcyc, numboffs)) for k in range(5)]

    if boolmult:
        objtpool = multiprocessing.Pool()
        numbproc = objtpool._processes
        indxproc = np.arange(numbproc)
        
        print('Generating %d processes...' % numbproc)

        listperiproc = [[] for i in indxproc]
        indxprocperi = np.linspace(0, numbproc - 1, numbperi).astype(int)
        for i in indxproc:
            indx = np.where(indxprocperi == i)[0]
            listperiproc[i] = listperi[indx]
        temp = objtpool.map(partial(spaw_blsq, listperiproc, arrytser, minmtime, phasshft, listdcyc, listoffs), indxproc)
        listdept = [temp[k][0] for k in indxproc]
        lists2nr = [temp[k][1] for k in indxproc]
        listdept = np.concatenate(listdept, 0)
        lists2nr = np.concatenate(lists2nr, 0)
    else:
        listdept, lists2nr = spaw_blsq([listperi], arrytser, minmtime, phasshft, listdcyc, listoffs, 0)
    
    indx = np.unravel_index(np.nanargmax(lists2nr), lists2nr.shape)
    
    dictblsqoutp['s2nr'] = np.nanmax(lists2nr)
    dictblsqoutp['peri'] = listperi[indx[0]]
    print('indx')
    print(indx)
    print('listdcyc')
    summgene(listdcyc)
    print('listdcyc[indx[1]]')
    print(listdcyc[indx[1]])
    dictblsqoutp['dura'] = 24. * listdcyc[indx[1]] * listperi[indx[0]] # [hours]
    dictblsqoutp['epoc'] = minmtime + listoffs[indx[2]] * listperi[indx[0]]
    dictblsqoutp['dept'] = listdept[indx]
    
    print('temp: assuming SDE == SNR')
    dictblsqoutp['sdee'] = dictblsqoutp['s2nr']

    s2nrperi = np.empty_like(listperi)
    for k in indxperi:
        indx = np.unravel_index(np.nanargmax(lists2nr[k, :, :]), lists2nr[k, :, :].shape)
        s2nrperi[k] = lists2nr[k, :, :][indx]
    
    # best-fit orbit
    cosi = 0
    rsma = retr_rsma(dictblsqoutp['peri'], dictblsqoutp['dura'], cosi)
    rrat = np.sqrt(dictblsqoutp['dept'])

    dictblsqoutp['listperi'] = listperi
    
    print('temp: assuming power is SNR')
    dictblsqoutp['listpowr'] = s2nrperi
    
    numbtimemodl = 100000
    arrytsermodl = np.empty((numbtimemodl, 3))
    arrytsermodl[:, 0] = np.linspace(minmtime, maxmtime, 100000)
    arrytsermodl[:, 1] = retr_rflxtranmodl(arrytsermodl[:, 0], [dictblsqoutp['peri']], [dictblsqoutp['epoc']], \
                                        [rrat], 1. / dictfact['rsre'], [rsma], [cosi], booltrap=False)

    arrypsermodl = fold_tser(arrytsermodl, dictblsqoutp['epoc'], dictblsqoutp['peri'], phasshft=phasshft)
    arrypserdata = fold_tser(arrytser, dictblsqoutp['epoc'], dictblsqoutp['peri'], phasshft=phasshft)
            
    dictblsqoutp['timedata'] = arrytser[:, 0]
    dictblsqoutp['rflxtserdata'] = arrytser[:, 1]
    dictblsqoutp['phasdata'] = arrypserdata[:, 0]
    dictblsqoutp['rflxpserdata'] = arrypserdata[:, 1]

    dictblsqoutp['timemodl'] = arrytsermodl[:, 0]
    dictblsqoutp['rflxtsermodl'] = arrytsermodl[:, 1]
    dictblsqoutp['phasmodl'] = arrypsermodl[:, 0]
    dictblsqoutp['rflxpsermodl'] = arrypsermodl[:, 1]
    
    print('dictblsqoutp[peri]')
    print(dictblsqoutp['peri'])
    
    #print('dt0: %.3g ms.' % (1e3 * np.mean(timechec[:, 1] - timechec[:, 0])))
    #print('dt1: %.3g ms.' % (1e3 * np.mean(timechec[:, 2] - timechec[:, 1])))
    #print('dt2: %.3g ms.' % (1e3 * np.mean(timechec[:, 3] - timechec[:, 2])))
    #for k in range(4):
    #    indx = np.where((timechecloop[k] > 0) & (timechecloop[k+1] > 0))[0]
    #    print('dtl%d: %.3g ms.' % (k, 1e3 * numbdcyc * numboffs * np.mean(timechecloop[k+1][indx] - timechecloop[k][indx])))
    
    timefinl = timemodu.time()
    timetotl = timefinl - timeinit
    timeredu = timetotl / numbtime / numbperi / numboffs / numbdcyc
    
    print('exec_blsq() took %.3g seconds in total and %g ns per observation and trial.' % (timetotl, timeredu * 1e9))

    return dictblsqoutp


def srch_pbox(arry, \
              # folder in which plots will be generated
              pathimag=None, \
              numbplan=None, \
              strgextn='', \
              thrssdee=7.1, \
              boolpuls=False, \
              ### maximum number of transiting objects
              maxmnumbtobj=None, \
              ### input dictionary for BLS
              dictblsqinpt=dict(), \
              ticitarg=None, \
              dicttlsqinpt=None, \
              booltlsq=False, \
              # plotting
              strgplotextn='pdf', \
              figrsize=(4., 3.), \
              figrsizeydobskin=(8, 2.5), \
              alphraww=0.2, \
             ):
    """
    Search for periodic boxes in time-series data
    """
    
    print('Searching for periodic boxes in time-series data...')
    print('booltlsq')
    print(booltlsq)
    print('boolpuls')
    print(boolpuls)

    if booltlsq:
        import transitleastsquares
        if dicttlsqinpt is None:
            dicttlsqinpt = dict()
    
    # setup TLS
    # temp
    #ab, mass, mass_min, mass_max, radius, radius_min, radius_max = transitleastsquares.catalog_info(TIC_ID=int(ticitarg))
    
    liststrgvarb = ['peri', 'epoc', 'dept', 'dura', 'sdee']
    #liststrgvarb = ['peri', 'epoc', 'dept', 'dura', 'listpowr', 'listperi', 'sdee']
    
    arrysrch = np.copy(arry)
    if boolpuls:
        arrysrch[:, 1] = 2. - arrysrch[:, 1]

    j = 0
    dictsrchpboxoutp = {}
    dictsrchpboxoutp['listdictblsqoutp'] = []

    while True:
        
        if maxmnumbtobj is not None and j >= maxmnumbtobj:
            break
        
        print('j')
        print(j)

        # mask out the detected transit
        if j == 0:
            arrymeta = np.copy(arrysrch)
        else:
            arrymeta -= dictblsqoutp['rflxtsermodl']

        # transit search
        timeblsqmeta = arrymeta[:, 0]
        lcurblsqmeta = arrymeta[:, 1]
        if booltlsq:
            objtmodltlsq = transitleastsquares.transitleastsquares(timeblsqmeta, lcurblsqmeta)
            objtresu = objtmodltlsq.power(\
                                          # temp
                                          #u=ab, \
                                          **dicttlsqinpt, \
                                          #use_threads=1, \
                                         )

            # temp check how to do BLS instead of TLS
            dictblsq = dict()
            dictblsqoutp['listperi'] = objtresu.periods
            dictblsqoutp['listpowr'] = objtresu.power
            
            dictblsqoutp['peri'] = objtresu.period
            dictblsqoutp['epoc'] = objtresu.T0
            dictblsqoutp['dura'] = objtresu.duration
            dictblsqoutp['dept'] = objtresu.depth
            dictblsqoutp['sdee'] = objtresu.SDE
            
            dictblsqoutp['prfp'] = objtresu.FAP
            
            dictblsqoutp['listtimetran'] = objtresu.transit_times
            
            dictblsqoutp['timemodl'] = objtresu.model_lightcurve_time
            dictblsqoutp['phasmodl'] = objtresu.model_folded_phase
            dictblsqoutp['rflxpsermodl'] = objtresu.model_folded_model
            dictblsqoutp['rflxtsermodl'] = objtresu.model_lightcurve_model
            dictblsqoutp['phasdata'] = objtresu.folded_phase
            dictblsqoutp['rflxpserdata'] = objtresu.folded_y

        else:
            dictblsqoutp = exec_blsq(arrymeta, **dictblsqinpt)
        
        if boolpuls:
            dictblsqoutp['timemodl'] = 2. - dictblsqoutp['timemodl']
            dictblsqoutp['phasmodl'] = 2. - dictblsqoutp['phasmodl']
            dictblsqoutp['phasdata'] = 2. - dictblsqoutp['phasdata']
            dictblsqoutp['rflxpserdata'] = 2. - dictblsqoutp['rflxpserdata']
            dictblsqoutp['rflxpsermodl'] = 2. - dictblsqoutp['rflxpsermodl']
            dictblsqoutp['rflxtsermodl'] = 2. - dictblsqoutp['rflxtsermodl']
        
        if pathimag is not None:
            strgtitl = 'P=%.3g d, Dep=%.3g ppm, Dur=%.3g hr, SDE=%.3g' % \
                        (dictblsqoutp['peri'], dictblsqoutp['dept'], dictblsqoutp['dura'], dictblsqoutp['sdee'])
            # plot TLS power spectrum
            figr, axis = plt.subplots(figsize=figrsize)
            axis.axvline(dictblsqoutp['peri'], alpha=0.4, lw=3)
            axis.set_xlim(np.min(dictblsqoutp['listperi']), np.max(dictblsqoutp['listperi']))
            for n in range(2, 10):
                axis.axvline(n * dictblsqoutp['peri'], alpha=0.4, lw=1, linestyle='dashed')
                axis.axvline(dictblsqoutp['peri'] / n, alpha=0.4, lw=1, linestyle='dashed')
            axis.set_ylabel(r'SDE')
            axis.set_xlabel('Period [days]')
            axis.plot(dictblsqoutp['listperi'], dictblsqoutp['listpowr'], color='black', lw=0.5)
            axis.set_xlim(0, max(dictblsqoutp['listperi']));
            axis.set_title(strgtitl)
            plt.subplots_adjust(bottom=0.2)
            path = pathimag + 'sdee_blsq_tce%d_%s.%s' % (j, strgextn, strgplotextn)
            print('Writing to %s...' % path)
            plt.savefig(path)
            plt.close()
            
            # plot light curve + TLS model
            figr, axis = plt.subplots(figsize=figrsizeydobskin)
            if boolpuls:
                timeblsqmetatemp = 2. - timeblsqmeta
                lcurblsqmetatemp = 2. - lcurblsqmeta
            axis.plot(timeblsqmeta, lcurblsqmeta, alpha=alphraww, marker='o', ms=1, ls='', color='grey', rasterized=True)
            axis.plot(dictblsqoutp['timemodl'], dictblsqoutp['rflxtsermodl'], color='b')
            axis.set_xlabel('Time [days]')
            axis.set_ylabel('Relative flux');
            if j == 0:
                ylimtserinit = axis.get_ylim()
            else:
                axis.set_ylim(ylimtserinit)
            axis.set_title(strgtitl)
            plt.subplots_adjust(bottom=0.2)
            path = pathimag + 'rflx_blsq_tce%d_%s.%s' % (j, strgextn, strgplotextn)
            print('Writing to %s...' % path)
            plt.savefig(path)
            plt.close()

            # plot phase curve + TLS model
            figr, axis = plt.subplots(figsize=figrsizeydobskin)
            axis.plot(dictblsqoutp['phasdata'], dictblsqoutp['rflxpserdata'], marker='o', ms=1, ls='', alpha=alphraww, color='grey', rasterized=True)
            axis.plot(dictblsqoutp['phasmodl'], dictblsqoutp['rflxpsermodl'], color='b')
            axis.set_xlabel('Phase')
            axis.set_ylabel('Relative flux');
            if j == 0:
                ylimpserinit = axis.get_ylim()
            else:
                axis.set_ylim(ylimpserinit)
            axis.set_title(strgtitl)
            plt.subplots_adjust(bottom=0.2)
            path = pathimag + 'pcur_blsq_tce%d_%s.%s' % (j, strgextn, strgplotextn)
            print('Writing to %s...' % path)
            plt.savefig(path)
            plt.close()
        
        if dictblsqoutp['sdee'] > thrssdee:
            dictsrchpboxoutp['listdictblsqoutp'].append(dictblsqoutp)
        else:
            break
        j += 1
       
    # merge output BLS dictionaries of different TCEs
    for name in liststrgvarb:
        dictsrchpboxoutp[name] = []
        for k in range(len(dictsrchpboxoutp['listdictblsqoutp'])):
            dictsrchpboxoutp[name].append(dictsrchpboxoutp['listdictblsqoutp'][k][name])
        dictsrchpboxoutp[name] = np.array(dictsrchpboxoutp[name])
    
    return dictsrchpboxoutp


def retr_rascdeclfromstrgmast(strgmast):

    print('Querying the TIC using the key %s, in order to get the RA and DEC of the closest TIC source...' % strgmast)
    listdictcatl = astroquery.mast.Catalogs.query_object(strgmast, catalog='TIC')
    #listdictcatl = astroquery.mast.Catalogs.query_object(strgmast, catalog='TIC', radius='40s')
    rasctarg = listdictcatl[0]['ra']
    decltarg = listdictcatl[0]['dec']
    print('TIC, RA, and DEC of the closest match are %d, %.5g, and %.5g' % (int(listdictcatl[0]['ID']), rasctarg, decltarg))
    
    return rasctarg, decltarg

    
def retr_lcurtess( \
              # path for downloading data
              pathtarg, \
              
              # keyword string for MAST search, where the closest target's RA and DEC will be fed into the tesscut search
              strgmast=None, \
    
              # RA for tesscut search
              rasctarg=None, \
    
              # DEC for tesscut search
              decltarg=None, \
    
              # type of data: 
              ## 'SPOC': SPOC when available, lygos otherwise
              ## 'lygos': lygos-only
              ## 'lygos-best'
              typedatatess='SPOC', \
              
              ## type of SPOC light curve to be used for analysis: 'PDC', 'SAP'
              typedataspoc='PDC', \
              
              # Boolean flag to only consider SPOC data
              boolspoconly=False, \

              ## subset of sectors to retrieve
              listtsecsele=None, \
              
              ## number of pixels on a side to use with lygos
              numbside=11, \
              
              # lygos
              labltarg=None, \
              strgtarg=None, \
              dictlygoinpt=dict(), \

              ## Boolean flag to apply quality mask
              boolmaskqual=True, \
              ## Boolean flag to only use 20-sec data when SPOC light curves with both 2-min and 20-sec data exist
              boolfastonly=True, \
         
              **args, \
              
             ):
    
    print('typedatatess')
    print(typedatatess)
    
    strgmast, rasctarg, decltarg = setp_coorstrgmast(rasctarg, decltarg, strgmast)

    if not boolspoconly:
        # get the list of sectors for which TESS SPOC data are available
        listtsecffim, temp, temp = retr_listtsec(rasctarg, decltarg)

    listtsecspoc = []
        
    # get the list of sectors for which TESS SPOC TPFs are available
    print('Retrieving the list of available TESS sectors for which there is SPOC TPF data...')
    # get observation tables
    listtablobsv = retr_listtablobsv(strgmast)
    listprodspoc = []
    for k, tablobsv in enumerate(listtablobsv):
        
        listprodspoctemp = astroquery.mast.Observations.get_product_list(tablobsv)
        
        if listtablobsv['distance'][k] > 0:
            continue

        strgdesc = 'Light curves'
        listprodspoctemp = astroquery.mast.Observations.filter_products(listprodspoctemp, description=strgdesc)
        for a in range(len(listprodspoctemp)):
            boolfasttemp = listprodspoctemp[a]['obs_id'].endswith('fast')
            if not boolfasttemp:
                tsec = int(listprodspoctemp[a]['obs_id'].split('-')[1][1:])
                listtsecspoc.append(tsec) 
                listprodspoc.append(listprodspoctemp)
    
    listtsecspoc = np.array(listtsecspoc)
    listtsecspoc = np.sort(listtsecspoc)
    
    print('listtsecspoc')
    print(listtsecspoc)
    
    numbtsecspoc = listtsecspoc.size
    indxtsecspoc = np.arange(numbtsecspoc)

    if not boolspoconly:
        # merge SPOC and FFI sector lists
        listtsecmerg = np.unique(np.concatenate((listtsecffim, listtsecspoc)))
    else:
        listtsecmerg = listtsecspoc

    # filter the list of sectors using the desired list of sectors, if any
    if listtsecsele is not None:
        listtsec = np.array(listtsecsele)
        for tsec in listtsecsele:
            if tsec not in listtsecmerg:
                print('listtsecmerg')
                print(listtsecmerg)
                print('listtsecsele')
                print(listtsecsele)
                raise Exception('Selected sector is not in the list of available sectors.')
    else:
        listtsec = listtsecmerg
    
    print('listtsec')
    print(listtsec)
    
    numbtsec = len(listtsec)
    indxtsec = np.arange(numbtsec)

    listtcam = np.empty(numbtsec, dtype=int)
    listtccd = np.empty(numbtsec, dtype=int)
    
    # determine whether sectors have 2-minute cadence data
    booltpxf = retr_booltpxf(listtsec, listtsecspoc)
    print('booltpxf')
    print(booltpxf)
    
    boollygo = ~booltpxf
    listtseclygo = listtsec[boollygo]
    if typedatatess == 'lygos' or typedatatess == 'lygos-best':
        listtseclygo = listtsec
        if typedatatess == 'lygos':
            booltpxflygo = False
        if typedatatess == 'lygos-best':
            booltpxflygo = True
    if typedatatess == 'SPOC':
        booltpxflygo = False
        listtseclygo = listtsec[boollygo]
    
    print('booltpxflygo')
    print(booltpxflygo)
    print('listtseclygo')
    print(listtseclygo)
    
    listarrylcur = [[] for o in indxtsec]
    if len(listtseclygo) > 0:
        print('Will run lygos on the object...')
        dictlygooutp = lygos.main.init( \
                                       
                                       strgmast=strgmast, \
                                       labltarg=labltarg, \
                                       strgtarg=strgtarg, \
                                       listtsecsele=listtseclygo, \
                                       
                                       # lygos-specific
                                       booltpxflygo=booltpxflygo, \
                                       **dictlygoinpt, \

                                      )
        for o, tseclygo in enumerate(listtsec):
            indx = np.where(dictlygooutp['listtsec'] == tseclygo)[0]
            if indx.size > 0:
                listarrylcur[o] = dictlygooutp['listarry'][indx[0]]
                listtcam[o] = dictlygooutp['listtcam'][indx[0]]
                listtccd[o] = dictlygooutp['listtccd'][indx[0]]
    
    listarrylcursapp = None
    listarrylcurpdcc = None
    arrylcursapp = None
    arrylcurpdcc = None
    
    print('listtsecspoc')
    print(listtsecspoc)
    if len(listtsecspoc) > 0 and not booltpxflygo:
        
        # download data from MAST
        os.system('mkdir -p %s' % pathtarg)
        
        print('Downloading SPOC data products...')
        
        listhdundataspoc = [[] for o in indxtsecspoc]
        listpathdownspoc = []

        listpathdownspoclcur = []
        for k in range(len(listprodspoc)):
            manifest = astroquery.mast.Observations.download_products(listprodspoc[k], download_dir=pathtarg)
            listpathdownspoclcur.append(manifest['Local Path'][0])

        ## make sure the list of paths to sector files are time-sorted
        listpathdownspoc.sort()
        listpathdownspoclcur.sort()
        
        ## read SPOC light curves
        if typedataspoc == 'SAP':
            print('Reading the SAP light curves...')
        else:
            print('Reading the PDC light curves...')
        listarrylcursapp = [[] for o in indxtsec] 
        listarrylcurpdcc = [[] for o in indxtsec] 
        for o in indxtsec:
            if not boollygo[o]:
                
                indx = np.where(listtsec[o] == listtsecspoc)[0][0]
                path = listpathdownspoclcur[indx]
                listarrylcursapp[indx], indxtimequalgood, indxtimenanngood, listtsec[o], listtcam[o], listtccd[o] = \
                                                       read_tesskplr_file(path, typeinst='tess', strgtype='SAP_FLUX', boolmaskqual=boolmaskqual)
                listarrylcurpdcc[indx], indxtimequalgood, indxtimenanngood, listtsec[o], listtcam[o], listtccd[o] = \
                                                       read_tesskplr_file(path, typeinst='tess', strgtype='PDCSAP_FLUX', boolmaskqual=boolmaskqual)
            
                if typedataspoc == 'SAP':
                    arrylcur = listarrylcursapp[indx]
                else:
                    arrylcur = listarrylcurpdcc[indx]
                listarrylcur[o] = arrylcur
            
        if numbtsec == 0:
            print('No data have been retrieved.' % (numbtsec, strgtemp))
        else:
            if numbtsec == 1:
                strgtemp = ''
            else:
                strgtemp = 's'
            print('%d sector%s of data retrieved.' % (numbtsec, strgtemp))
        
        # merge light curves from different sectors
        arrylcursapp = np.concatenate([arry for arry in listarrylcursapp if len(arry) > 0], 0)
        arrylcurpdcc = np.concatenate([arry for arry in listarrylcurpdcc if len(arry) > 0], 0)
    
    # merge light curves from different sectors
    arrylcur = np.concatenate(listarrylcur, 0)
        
    for o, tseclygo in enumerate(listtsec):
        for k in range(3):
            if not np.isfinite(listarrylcur[o][:, k]).all():
                print('listtsec')
                print(listtsec)
                print('tseclygo')
                print(tseclygo)
                print('k')
                print(k)
                indxbadd = np.where(~np.isfinite(listarrylcur[o][:, k]))[0]
                print('listarrylcur[o][:, k]')
                summgene(listarrylcur[o][:, k])
                print('indxbadd')
                summgene(indxbadd)
                raise Exception('')
    if not np.isfinite(arrylcur).all():
        indxbadd = np.where(~np.isfinite(arrylcur))[0]
        print('arrylcur')
        summgene(arrylcur)
        print('indxbadd')
        summgene(indxbadd)
        raise Exception('')
                
    return arrylcur, arrylcursapp, arrylcurpdcc, listarrylcur, listarrylcursapp, listarrylcurpdcc, listtsec, listtcam, listtccd
   

def retr_listtablobsv(strgmast):
    
    if strgmast is None:
        raise Exception('strgmast should not be None.')

    listtablobsv = astroquery.mast.Observations.query_criteria(obs_collection='TESS', dataproduct_type='timeseries', objectname=strgmast)

    if len(listtablobsv) == 0:
        print('No SPOC data is found...')
    
    return listtablobsv


def setp_coorstrgmast(rasctarg=None, decltarg=None, strgmast=None):
    
    if strgmast is not None and (rasctarg is not None or decltarg is not None) or strgmast is None and (rasctarg is None or decltarg is None):
        raise Exception('')

    # determine RA and DEC if not already provided
    if rasctarg is None:
        rasctarg, decltarg = retr_rascdeclfromstrgmast(strgmast)
    
    # determine strgmast if not already provided
    if strgmast is None:
        strgmast = '%g %g' % (rasctarg, decltarg)

    return strgmast, rasctarg, decltarg


def retr_listtsec(rasctarg, decltarg):

    # check all available TESS (FFI) data 
    objtskyy = astropy.coordinates.SkyCoord(rasctarg, decltarg, unit='deg')
    print('Calling TESSCut to get available sectors for the RA and DEC (%.5g, %.5g)...' % (rasctarg, decltarg))
    tabltesscutt = astroquery.mast.Tesscut.get_sectors(objtskyy, radius=0)

    listtsec = np.array(tabltesscutt['sector'])
    listtcam = np.array(tabltesscutt['camera'])
    listtccd = np.array(tabltesscutt['ccd'])
   
    print('temp')
    if rasctarg == 122.989831564958:
        listtsec = np.array([7, 34])
        listtcam = np.array([1, 1])
        listtccd = np.array([3, 4])
    
    return listtsec, listtcam, listtccd


def retr_booltpxf(listtsec, listtsecspoc):

    ## number of sectors for which TESS data are available
    numbtsec = len(listtsec)
    ## Boolean flags to indicate that TPFs exist at 2-min
    booltpxf = np.zeros(numbtsec, dtype=bool)
    for k, tsec in enumerate(listtsec):
        if tsec in listtsecspoc:
            booltpxf[k] = True
    
    return booltpxf


# plotting

def plot_lspe(pathimag, arrylcur, strgextn=''):
    
    from astropy.timeseries import LombScargle
    
    time = arrylcur[:, 0]
    lcur = arrylcur[:, 1]
    maxmperi = (np.amax(time) - np.amin(time)) / 4.
    minmperi = np.amin(time[1:] - time[:-1]) * 4.
    peri = np.linspace(minmperi, maxmperi, 10000)
    freq = 1. / peri
    
    powr = LombScargle(time, lcur, nterms=2).power(freq)
    figr, axis = plt.subplots(figsize=(8, 4))
    axis.plot(peri, powr, color='k')
    
    axis.set_xlabel('Period [days]')
    axis.set_ylabel('Power')

    plt.savefig(pathimag + 'lspe_%s.pdf' % strgextn)
    plt.close()
    
    listperi = peri[np.argsort(powr)[::-1][:5]]

    return listperi


def plot_lcur(pathimag, strgextn, dictmodl=None, timedata=None, lcurdata=None, \
              # break the line of the model when separation is very large
              boolbrekmodl=True, \
              timedatabind=None, lcurdatabind=None, lcurdatastdvbind=None, boolwritover=True, \
              titl='', listcolrmodl=None):
    
    if strgextn == '':
        raise Exception('')
    
    path = pathimag + 'lcur%s.pdf' % strgextn
    
    # skip plotting
    if not boolwritover and os.path.exists(path):
        return
    
    figr, axis = plt.subplots(figsize=(8, 4))
    
    # model
    if dictmodl is not None:
        if listcolrmodl is None:
            listcolrmodl = ['r', 'b', 'g', 'c', 'm', 'orange', 'olive']
        k = 0
        for attr in dictmodl:
            if boolbrekmodl:
                diftimemodl = dictmodl[attr]['time'][1:] - dictmodl[attr]['time'][:-1]
                indxtimebrek = np.where(diftimemodl > 2 * np.amin(diftimemodl))[0] + 1
                indxtimebrek = np.concatenate([np.array([0]), indxtimebrek, np.array([dictmodl[attr]['time'].size - 1])])
                numbtimebrek = indxtimebrek.size
                numbtimechun = numbtimebrek - 1

                xdat = []
                ydat = []
                for n in range(numbtimechun):
                    xdat.append(dictmodl[attr]['time'][indxtimebrek[n]:indxtimebrek[n+1]])
                    ydat.append(dictmodl[attr]['lcur'][indxtimebrek[n]:indxtimebrek[n+1]])
                    
            else:
                xdat = [dictmodl[attr]['time']]
                ydat = [dictmodl[attr]['lcur']]
            numbchun = len(xdat)
            
            for n in range(numbchun):
                axis.plot(xdat[n], ydat[n], color=listcolrmodl[k], lw=2)
            k += 1

    # raw data
    if timedata is not None:
        axis.plot(timedata, lcurdata, color='grey', ls='', marker='o', ms=1, rasterized=True)
    
    # binned data
    if timedatabind is not None:
        axis.errorbar(timedatabind, lcurdatabind, yerr=lcurdatastdvbind, color='k', ls='', marker='o', ms=2)
    
    axis.set_xlabel('Time [days]')
    axis.set_ylabel('Relative flux')
    axis.set_title(titl)
    
    plt.subplots_adjust(bottom=0.15)
    print(f'Writing to {path}...')
    plt.savefig(path)
    plt.close()


def plot_pcur(pathimag, arrylcur=None, arrypcur=None, arrypcurbind=None, phascent=0., boolhour=False, epoc=None, peri=None, strgextn='', \
                                                            boolbind=True, timespan=None, booltime=False, numbbins=100, limtxdat=None):
    
    if arrypcur is None:
        arrypcur = fold_tser(arrylcur, epoc, peri)
    if arrypcurbind is None and boolbind:
        arrypcurbind = rebn_tser(arrypcur, numbbins)
        
    # phase on the horizontal axis
    figr, axis = plt.subplots(1, 1, figsize=(8, 4))
    
    # time on the horizontal axis
    if booltime:
        lablxaxi = 'Time [hours]'
        if boolhour:
            fact = 24.
        else:
            fact = 1.
        xdat = arrypcur[:, 0] * peri * fact
        if boolbind:
            xdatbind = arrypcurbind[:, 0] * peri * fact
    else:
        lablxaxi = 'Phase'
        xdat = arrypcur[:, 0]
        if boolbind:
            xdatbind = arrypcurbind[:, 0]
    axis.set_xlabel(lablxaxi)
    
    axis.plot(xdat, arrypcur[:, 1], color='grey', alpha=0.2, marker='o', ls='', ms=0.5, rasterized=True)
    if boolbind:
        axis.plot(xdatbind, arrypcurbind[:, 1], color='k', marker='o', ls='', ms=2)
    
    axis.set_ylabel('Relative Flux')
    
    # adjust the x-axis limits
    if limtxdat is not None:
        axis.set_xlim(limtxdat)
    
    plt.subplots_adjust(hspace=0., bottom=0.25, left=0.25)
    path = pathimag + 'pcur%s.pdf' % strgextn
    print('Writing to %s...' % path)
    plt.savefig(path)
    plt.close()
            

def fold_tser(arry, epoc, peri, boolxdattime=False, boolsort=True, phasshft=0.5, booldiagmode=True):
    
    phas = (((arry[:, 0] - epoc) % peri) / peri + phasshft) % 1. - phasshft
    
    arryfold = np.empty_like(arry)
    arryfold[:, 0, ...] = phas
    arryfold[:, 1:3, ...] = arry[:, 1:3, ...]
    
    if boolsort:
        indx = np.argsort(phas)
        arryfold = arryfold[indx, :, ...]
    
    if boolxdattime:
        arryfold[:, 0, ...] *= peri

    return arryfold


def rebn_tser(arry, numbbins=None, delt=None, binsxdat=None):
    
    if not (numbbins is None and delt is None and binsxdat is not None or \
            numbbins is not None and delt is None and binsxdat is None or \
            numbbins is None and delt is not None and binsxdat is None):
        raise Exception('')
    
    if arry.shape[0] == 0:
        print('Warning! Trying to bin an empty time-series...')
        return arry
    
    xdat = arry[:, 0]
    if numbbins is not None:
        arryrebn = np.empty((numbbins, 3)) + np.nan
        binsxdat = np.linspace(np.amin(xdat), np.amax(xdat), numbbins + 1)
    if delt is not None:
        binsxdat = np.arange(np.amin(xdat), np.amax(xdat) + delt, delt)
    if delt is not None or binsxdat is not None:
        numbbins = binsxdat.size - 1
        arryrebn = np.empty((numbbins, 3)) + np.nan

    meanxdat = (binsxdat[:-1] + binsxdat[1:]) / 2.
    arryrebn[:, 0] = meanxdat

    indxbins = np.arange(numbbins)
    for k in indxbins:
        indxxdat = np.where((xdat < binsxdat[k+1]) & (xdat > binsxdat[k]))[0]
        if indxxdat.size == 0:
            arryrebn[k, 1] = np.nan
            arryrebn[k, 2] = np.nan
        else:
            arryrebn[k, 1] = np.mean(arry[indxxdat, 1])
            arryrebn[k, 2] = np.sqrt(np.nansum(arry[indxxdat, 2]**2)) / indxxdat.size
    
    return arryrebn

    
def read_tesskplr_fold(pathfold, pathwrit, boolmaskqual=True, typeinst='tess', strgtype='PDCSAP_FLUX'):
    
    '''
    Reads all TESS or Kepler light curves in a folder and returns a data cube with time, flux and flux error
    '''

    listpath = fnmatch.filter(os.listdir(pathfold), '%s*' % typeinst)
    listarry = []
    for path in listpath:
        arry = read_tesskplr_file(pathfold + path + '/' + path + '_lc.fits', typeinst=typeinst, strgtype=strgtype, boolmaskqual=boolmaskqual)
        listarry.append(arry)
    
    # merge sectors
    arry = np.concatenate(listarry, axis=0)
    
    # sort in time
    indxsort = np.argsort(arry[:, 0])
    arry = arry[indxsort, :]
    
    # save
    pathoutp = '%s/%s.csv' % (pathwrit, typeinst)
    np.savetxt(pathoutp, arry, delimiter=',')

    return arry 


def read_tesskplr_file(path, typeinst='tess', strgtype='PDCSAP_FLUX', boolmaskqual=True, boolmasknann=True):
    
    '''
    Reads a TESS or Kepler light curve file and returns a data cube with time, flux and flux error
    '''
    
    listhdun = fits.open(path)
    
    boollcur = path.endswith('_lc.fits')

    tsec = listhdun[0].header['SECTOR']
    tcam = listhdun[0].header['CAMERA']
    tccd = listhdun[0].header['CCD']
        
    if boollcur:
        time = listhdun[1].data['TIME'] + 2457000
        if typeinst == 'TESS':
            time += 2457000
        if typeinst == 'kplr':
            time += 2454833
        flux = listhdun[1].data[strgtype]
        stdv = listhdun[1].data[strgtype+'_ERR']
    
        indxtimequalgood = np.where(listhdun[1].data['QUALITY'] == 0)[0]
        if boolmaskqual:
            # filtering for good quality
            time = time[indxtimequalgood]
            flux = flux[indxtimequalgood]
            stdv = stdv[indxtimequalgood]
    
        numbtime = time.size
        arry = np.empty((numbtime, 3))
        arry[:, 0] = time
        arry[:, 1] = flux
        arry[:, 2] = stdv
        
        indxtimenanngood = np.where(~np.any(np.isnan(arry), axis=1))[0]
        if boolmasknann:
            arry = arry[indxtimenanngood, :]
    
        #print('HACKING, SKIPPING NORMALIZATION FOR SPOC DATA')
        # normalize
        arry[:, 2] /= np.median(arry[:, 1])
        arry[:, 1] /= np.median(arry[:, 1])
    
        return arry, indxtimequalgood, indxtimenanngood, tsec, tcam, tccd
    else:
        return listhdun, tsec, tcam, tccd


#def retr_fracrtsa(fracrprs, fracsars):
#    
#    fracrtsa = (fracrprs + 1.) / fracsars
#    
#    return fracrtsa
#
#
#def retr_fracsars(fracrprs, fracrtsa):
#    
#    fracsars = (fracrprs + 1.) / fracrtsa
#    
#    return fracsars


def retr_rflxtranmodl(time, peri, epoc, radiplan, radistar, rsma, cosi, ecce=0., sinw=0., booltrap=False):
    
    timeinit = timemodu.time()

    if isinstance(peri, list):
        peri = np.array(peri)

    if isinstance(epoc, list):
        epoc = np.array(epoc)

    if isinstance(radiplan, list):
        radiplan = np.array(radiplan)

    if isinstance(rsma, list):
        rsma = np.array(rsma)

    if isinstance(cosi, list):
        cosi = np.array(cosi)

    if isinstance(ecce, list):
        ecce = np.array(ecce)

    if isinstance(sinw, list):
        sinw = np.array(sinw)
    
    boolinptphys = True#False

    minmtime = np.amin(time)
    maxmtime = np.amax(time)
    numbtime = time.size
    
    dictfact = retr_factconv()
    
    if boolinptphys:
        smax = (radistar + radiplan / dictfact['rsre']) / rsma / dictfact['aurs']
    
    rs2a = radistar / smax / dictfact['aurs']
    imfa = retr_imfa(cosi, rs2a, ecce, sinw)
    sini = np.sqrt(1. - cosi**2)
    rrat = radiplan / dictfact['rsre'] / radistar
    dept = rrat**2
    
    rflxtranmodl = np.ones_like(time)
    
    if booltrap:
        durafull = retr_duratranfull(peri, rs2a, sini, rrat, imfa)
        duratotl = retr_duratrantotl(peri, rs2a, sini, rrat, imfa)
        duraineg = (duratotl - durafull) / 2.
        durafullhalf = durafull / 2.
    else:
        duratotl = retr_duratran(peri, rsma, cosi)
    duratotlhalf = duratotl / 2.

    # Boolean flag that indicates whether there is any transit
    booltran = np.isfinite(duratotl)
    
    numbplan = radiplan.size
    indxplan = np.arange(numbplan)
    
    if False:
    #if True:
        print('time')
        summgene(time)
        print('epoc')
        print(epoc)
        print('peri')
        print(peri)
        print('cosi')
        print(cosi)
        print('rsma')
        print(rsma)
        print('imfa')
        print(imfa)
        print('radistar')
        print(radistar)
        print('rrat')
        print(rrat)
        print('rs2a')
        print(rs2a)
        print('duratotl')
        print(duratotl)
        print('durafull')
        print(durafull)
        print('booltran')
        print(booltran)
        print('indxplan')
        print(indxplan)
    
    for j in indxplan:
        
        if booltran[j]:
            
            minmindxtran = int(np.floor((epoc[j] - minmtime) / peri[j]))
            maxmindxtran = int(np.ceil((maxmtime - epoc[j]) / peri[j]))
            indxtranthis = np.arange(minmindxtran, maxmindxtran + 1)
            
            for n in indxtranthis:
                timetran = epoc[j] + peri[j] * n
                timeshft = time - timetran
                timeshftnega = -timeshft
                timeshftabso = abs(timeshft)
                
                indxtimetotl = np.where(timeshftabso < duratotlhalf[j] / 24.)[0]
                if booltrap:
                    indxtimefull = indxtimetotl[np.where(timeshftabso[indxtimetotl] < durafullhalf[j] / 24.)]
                    indxtimeinre = indxtimetotl[np.where((timeshftnega[indxtimetotl] < duratotlhalf[j] / 24.) & \
                                                                                        (timeshftnega[indxtimetotl] > durafullhalf[j] / 24.))]
                    indxtimeegre = indxtimetotl[np.where((timeshft[indxtimetotl] < duratotlhalf[j] / 24.) & (timeshft[indxtimetotl] > durafullhalf[j] / 24.))]
                
                    rflxtranmodl[indxtimeinre] += dept[j] * ((timeshftnega[indxtimeinre] - duratotlhalf[j] / 24.) / duraineg[j] / 24.)
                    rflxtranmodl[indxtimeegre] += dept[j] * ((timeshft[indxtimeegre] - duratotlhalf[j] / 24.) / duraineg[j])
                    rflxtranmodl[indxtimefull] -= dept[j]
                else:
                    rflxtranmodl[indxtimetotl] -= dept[j]
                
                if False:
                #if True:
                    print('n')
                    print(n)
                    print('timetran')
                    summgene(timetran)
                    print('timeshft[indxtimetotl]')
                    summgene(timeshft[indxtimetotl])
                    print('timeshftabso[indxtimetotl]')
                    summgene(timeshftabso[indxtimetotl])
                    print('timeshftnega[indxtimetotl]')
                    summgene(timeshftnega[indxtimetotl])
                    print('duratotlhalf[j]')
                    print(duratotlhalf[j])
                    print('durafullhalf[j]')
                    print(durafullhalf[j])
                    print('indxtimetotl')
                    summgene(indxtimetotl)
                    print('indxtimefull')
                    summgene(indxtimefull)
                    print('indxtimeinre')
                    summgene(indxtimeinre)
                    print('indxtimeegre')
                    summgene(indxtimeegre)
    
    timetotl = timemodu.time() - timeinit
    timeredu = timetotl / numbtime
    print('retr_rflxtranmodl() took %.3g seconds in total and %g ns per time sample.' % (timetotl, timeredu * 1e9))

    return rflxtranmodl


def retr_massfromradi(listradiplan, strgtype='chenkipp2016', \
                      # Boolean flag indicating 
                      boolinptsamp=False, \
                      ):
    
    '''listradiplan in units of Earth radius'''

    if strgtype == 'chenkipp2016':
        import mr_forecast
        indxgood = np.where((listradiplan > 0.1) & (listradiplan < 100.))[0]
        if indxgood.size < listradiplan.size:
            print('retr_massfromradi(): planet radius inappropriate for mr_forecast. Truncating...')
            listradiplan = listradiplan[indxgood]
        
        if len(listradiplan) > 0:
            if boolinptsamp:
                listmass = mr_forecast.Rpost2M(listradiplan)
            else:
                listmass = np.empty_like(listradiplan)
                print('listradiplan')
                summgene(listradiplan)
                for k in range(len(listradiplan)):
                    listmass[k] = mr_forecast.Rpost2M(listradiplan[k, None])
                
            #listmass = mr_forecast.Rpost2M(listradiplan, unit='Jupiter', classify='Yes')
        else:
            listmass = np.ones_like(listradiplan) + np.nan

    if strgtype == 'wolf2016':
        # (Wolgang+2016 Table 1)
        listmass = (2.7 * (listradiplan * 11.2)**1.3 + np.random.randn(listradiplan.size) * 1.9) / 317.907
        listmass = np.maximum(listmass, np.zeros_like(listmass))
    
    return listmass


def retr_esmm(tmptplanequb, tmptstar, radiplan, radistar, kmag):
    
    tmptplandayy = 1.1 * tmptplanequb
    esmm = 4.29e6 * tdpy.util.retr_specbbod(tmptplandayy, 7.5) / tdpy.util.retr_specbbod(tmptstar, 7.5) * (radiplan / radistar)*2 * 10**(-kmag / 5.)

    return esmm


def retr_tsmm(radiplan, tmptplan, massplan, radistar, jmag):
    
    tsmm = 1.53 * radiplan**3 * tmptplan / massplan / radistar**2 * 10**(-jmag / 5.)
    
    return tsmm


def retr_scalheig(tmptplan, massplan, radiplan):
    
    # tied to Jupier's scale height for H/He at 110 K   
    scalheig = 27. * (tmptplan / 160.) / (massplan / radiplan**2) / 71398. # [R_J]

    return scalheig


def retr_rflxfromdmag(dmag, stdvdmag=None):
    
    rflx = 10**(-dmag / 2.5)

    if stdvdmag is not None:
        stdvrflx = np.log(10.) / 2.5 * rflx * stdvdmag
    
    return rflx, stdvrflx


def retr_lcur_mock(numbplan=100, numbnois=100, numbtime=100, dept=1e-2, nois=1e-3, numbbinsphas=1000, pathplot=None, boollabltime=False, boolflbn=False):
    
    '''
    Function to generate mock light curves.
    numbplan: number of data samples containing signal, i.e., planet transits
    numbnois: number of background data samples, i.e., without planet transits
    numbtime: number of time bins
    pathplot: path in which plots are to be generated
    boollabltime: Boolean flag to label each time bin separately (e.g., for using with LSTM)
    '''
    
    # total number of data samples
    numbdata = numbplan + numbnois
    
    indxdata = np.arange(numbdata)
    indxtime = np.arange(numbtime)
    
    minmtime = 0.
    maxmtime = 27.3

    time = np.linspace(minmtime, maxmtime, numbtime)
    
    minmperi = 1.
    maxmperi = 10.
    minmdept = 1e-3
    maxmdept = 1e-2
    minmepoc = np.amin(time)
    maxmepoc = np.amax(time)
    minmdura = 3. # [hour]
    maxmdura = 4. # [hour]

    # input data
    flux = np.zeros((numbdata, numbtime))
    
    # planet transit properties
    ## durations
    duraplan = minmdura * np.ones(numbplan) + (maxmdura - minmdura) * np.random.rand(numbplan)
    ## phas  
    epocplan = minmepoc * np.ones(numbplan) + (maxmepoc - minmepoc) * np.random.rand(numbplan)
    ## periods
    periplan = minmperi * np.ones(numbplan) + (maxmperi - minmperi) * np.random.rand(numbplan)
    ##depths
    deptplan = minmdept * np.ones(numbplan) + (maxmdept - minmdept) * np.random.rand(numbplan)

    # input signal data
    fluxplan = np.zeros((numbplan, numbtime))
    indxplan = np.arange(numbplan)
    for k in indxplan:
        phas = (time - epocplan[k]) / periplan[k]
        for n in range(-1000, 1000):
            indxphastran = np.where(abs(phas - n) < duraplan[k] / periplan[k] / 24.)[0]
            fluxplan[k, indxphastran] -= deptplan[k]
    
    # place the signal data
    flux[:numbplan, :] = fluxplan

    # label the data
    if boollabltime:
        outp = np.zeros((numbdata, numbtime))
        outp[np.where(flux == dept[0])] = 1.
    else:
        outp = np.zeros(numbdata)
        outp[:numbplan] = 1
    
    # add noise to all data
    flux += nois * np.random.randn(numbtime * numbdata).reshape((numbdata, numbtime))
    
    # adjust the units of periods from number of time bins to days
    peri = peri / 24. / 30.
    
    # assign random periods to non-planet data
    peritemp = np.empty(numbdata)
    peritemp[:numbplan] = peri
    peritemp[numbplan:] = 1. + np.random.rand(numbnois) * 9.
    peri = peritemp

    # phase-fold and bin
    if boolflbn:
        binsphas = np.linspace(0., 1., numbbinsphas + 1)
        fluxflbn = np.empty((numbdata, numbbinsphas))
        phas = np.empty((numbdata, numbtime))
        for k in indxdata:
            phas[k, :] = ((time - epoc[k]) / peri[k] + 0.25) % 1.
            for n in indxphas:
                indxtime = np.where((phas < binsphas[n+1]) & (phas > binsphas[n]))[0]
                fluxflbn[k, n] = np.mean(flux[k, indxtime])
        inpt = fluxflbn
        xdat = meanphas
    else:
        inpt = flux
        xdat = time

    if pathplot != None:
        # generate plots if pathplot is set
        print ('Plotting the data set...')
        for k in indxdata:
            figr, axis = plt.subplots() # figr is unused
            axis.plot(indxtime, inpt[k, :])
            axis.set_title(outp[k])
            if k < numbplan:
                for t in indxtime:
                    if (t - phas[k]) % peri[k] == 0:
                        axis.axvline(t, ls='--', alpha=0.3, color='grey')
            axis.set_xlabel('$t$')
            axis.set_ylabel('$f(t)$')
            path = pathplot + 'data_%04d.pdf' % k
            print('Writing to %s...' % path)
            plt.savefig(path)
            plt.close()
    
    # randomize the data set
    numpstat = np.random.get_state()
    np.random.seed(0)
    indxdatarand = np.random.choice(indxdata, size=numbdata, replace=False)
    inpt = inpt[indxdatarand, :]
    outp = outp[indxdatarand]
    peri = peri[indxdatarand]
    np.random.set_state(numpstat)

    return inpt, xdat, outp, peri, epoc


def retr_dictexar(strgexar=None):
    
    # get NASA Exoplanet Archive data
    path = os.environ['EPHESUS_DATA_PATH'] + '/data/PSCompPars_2021.04.07_18.46.54.csv'
    print('Reading %s...' % path)
    objtexar = pd.read_csv(path, skiprows=316)
    if strgexar is None:
        indx = np.arange(objtexar['hostname'].size)
        #indx = np.where(objtexar['default_flag'].values == 1)[0]
    else:
        indx = np.where(objtexar['hostname'] == strgexar)[0]
        #indx = np.where((objtexar['hostname'] == strgexar) & (objtexar['default_flag'].values == 1))[0]
    
    dictfact = retr_factconv()
    
    if indx.size == 0:
        print('The target name, %s, was not found in the NASA Exoplanet Archive composite table.' % strgexar)
        return None
    else:
        dictexar = {}
        dictexar['namestar'] = objtexar['hostname'][indx].values
        dictexar['nameplan'] = objtexar['pl_name'][indx].values
        
        numbplanexar = len(dictexar['nameplan'])
        indxplanexar = np.arange(numbplanexar)

        listticitemp = objtexar['tic_id'][indx].values
        dictexar['tici'] = np.empty(numbplanexar, dtype=int)
        for k in indxplanexar:
            if isinstance(listticitemp[k], str):
                dictexar['tici'][k] = listticitemp[k][4:]
            else:
                dictexar['tici'][k] = 0
        
        dictexar['rascstar'] = objtexar['ra'][indx].values
        dictexar['declstar'] = objtexar['dec'][indx].values
        
        # err1 have positive values or zero
        # err2 have negative values or zero
        
        dictexar['toii'] = np.empty(numbplanexar, dtype=object)
        dictexar['facidisc'] = objtexar['disc_facility'][indx].values
        
        dictexar['inso'] = objtexar['pl_insol'][indx].values
        dictexar['peri'] = objtexar['pl_orbper'][indx].values # [days]
        dictexar['smax'] = objtexar['pl_orbsmax'][indx].values # [AU]
        dictexar['epoc'] = objtexar['pl_tranmid'][indx].values # [BJD]
        dictexar['cosi'] = np.cos(objtexar['pl_orbincl'][indx].values / 180. * np.pi)
        dictexar['duratran'] = objtexar['pl_trandur'][indx].values # [hour]
        dictexar['dept'] = objtexar['pl_trandep'][indx].values / 100. # dimensionless
        
        dictexar['boolfpos'] = np.zeros(numbplanexar, dtype=bool)
        
        dictexar['booltran'] = objtexar['tran_flag'][indx].values
        dictexar['booltran'] = dictexar['booltran'].astype(bool)
        
        for strg in ['radistar', 'massstar', 'tmptstar', 'loggstar', 'radiplan', 'massplan', 'tmptplan', 'tagestar', \
                     'vmagsyst', 'jmagsyst', 'hmagsyst', 'kmagsyst', 'metastar', 'distsyst', 'lumistar']:
            strgexar = None
            if strg.endswith('syst'):
                strgexar = 'sy_'
                if strg[:-4].endswith('mag'):
                    strgexar += '%smag' % strg[0]
                if strg[:-4] == 'dist':
                    strgexar += 'dist'
            if strg.endswith('star'):
                strgexar = 'st_'
                if strg[:-4] == 'logg':
                    strgexar += 'logg'
                if strg[:-4] == 'tage':
                    strgexar += 'age'
                if strg[:-4] == 'meta':
                    strgexar += 'met'
                if strg[:-4] == 'radi':
                    strgexar += 'rad'
                if strg[:-4] == 'mass':
                    strgexar += 'mass'
                if strg[:-4] == 'tmpt':
                    strgexar += 'teff'
                if strg[:-4] == 'lumi':
                    strgexar += 'lum'
            if strg.endswith('plan'):
                strgexar = 'pl_'
                if strg[:-4].endswith('mag'):
                    strgexar += '%smag' % strg[0]
                if strg[:-4] == 'tmpt':
                    strgexar += 'eqt'
                if strg[:-4] == 'radi':
                    strgexar += 'rade'
                if strg[:-4] == 'mass':
                    strgexar += 'bmasse'
            if strgexar is None:
                raise Exception('')
            dictexar[strg] = objtexar[strgexar][indx].values
            dictexar['stdv%s' % strg] = (objtexar['%serr1' % strgexar][indx].values - objtexar['%serr2' % strgexar][indx].values) / 2.
       
        dictexar['vesc'] = retr_vesc(dictexar['massplan'], dictexar['radiplan'])
        dictexar['masstotl'] = dictexar['massstar'] + dictexar['massplan'] / dictfact['msme']
        
        dictexar['densplan'] = objtexar['pl_dens'][indx].values # [g/cm3]
        dictexar['vsiistar'] = objtexar['st_vsin'][indx].values # [km/s]
        dictexar['projoblq'] = objtexar['pl_projobliq'][indx].values # [deg]
        
        dictexar['numbplanstar'] = np.empty(numbplanexar)
        dictexar['numbplantranstar'] = np.empty(numbplanexar)
        dictexar['boolfrst'] = np.zeros(numbplanexar, dtype=bool)
        #dictexar['booltrantotl'] = np.empty(numbplanexar, dtype=bool)
        for k, namestar in enumerate(dictexar['namestar']):
            indxexarstar = np.where(namestar == dictexar['namestar'])[0]
            if k == indxexarstar[0]:
                dictexar['boolfrst'][k] = True
            dictexar['numbplanstar'][k] = indxexarstar.size
            indxexarstartran = np.where((namestar == dictexar['namestar']) & dictexar['booltran'])[0]
            dictexar['numbplantranstar'][k] = indxexarstartran.size
            #dictexar['booltrantotl'][k] = dictexar['booltran'][indxexarstar].all()
        
        dictexar['rrat'] = dictexar['radiplan'] / dictexar['radistar'] / dictfact['rsre']
        
    return dictexar


# physics

def retr_vesc(massplan, radiplan):
    
    vesc = 11.2 * np.sqrt(massplan / radiplan) # km/s

    return vesc


def retr_rs2a(rsma, rrat):
    
    rs2a = rsma / (1. + rrat)
    
    return rs2a


def retr_rsma(peri, dura, cosi):
    
    rsma = np.sqrt(np.sin(dura * np.pi / peri / 24.)**2 + cosi**2)
    
    return rsma


def retr_duratranfull(peri, rs2a, sini, rrat, imfa):
    
    durafull = 24. * peri / np.pi * np.arcsin(rs2a / sini * np.sqrt((1. - rrat)**2 - imfa**2)) # [hours]

    return durafull 


def retr_duratrantotl(peri, rs2a, sini, rrat, imfa):
    
    duratotl = 24. * peri / np.pi * np.arcsin(rs2a / sini * np.sqrt((1. + rrat)**2 - imfa**2)) # [hours]
    
    return duratotl

    
def retr_imfa(cosi, rs2a, ecce, sinw):
    
    imfa = cosi / rs2a * (1. - ecce)**2 / (1. + ecce * sinw)

    return imfa


def retr_amplbeam(peri, massstar, masscomp):
    
    '''Calculates the beaming amplitude'''
    
    amplbeam = 2.8e-3 * peri**(-1. / 3.) * (massstar + masscomp)**(-2. / 3.) * masscomp
    
    return amplbeam


def retr_amplelli(peri, densstar, massstar, masscomp):
    
    '''Calculates the ellipsoidal variation amplitude'''
    
    amplelli = 1.89e-2 * peri**(-2.) / densstar * (1. / (1. + massstar / masscomp))
    
    return amplelli


def retr_masscomp(amplslen, peri):
    
    print('temp: this mass calculation is an approximation.')
    masscomp = amplslen / 7.15e-5 / gdat.radistar**(-2.) / peri**(2. / 3.) / (gdat.massstar)**(1. / 3.)
    
    return masscomp


def retr_amplslen(peri, radistar, masscomp, massstar):
    
    """
    Calculate the self-lensing amplitude.

    Arguments
        peri: orbital period [days]
        radistar: radius of the star [Solar radius]
        masscomp: mass of the companion [Solar mass]
        massstar: mass of the star [Solar mass]

    Returns
        amplslen: the fractional amplitude of the self-lensing
    """
    
    amplslen = 7.15e-5 * radistar**(-2.) * peri**(2. / 3.) * masscomp * (masscomp + massstar)**(1. / 3.)

    return amplslen


def retr_smaxkepl(peri, masstotl):
    
    """
    Get the semi-major axis of a Keplerian orbit (in AU) from the orbital period (in days) and total mass (in Solar masses).

    Arguments
        peri: orbital period [days]
        masstotl: total mass of the system [Solar Masses]
    Returns
        smax: the semi-major axis of a Keplerian orbit [AU]
    """
    
    smax = (7.496e-6 * masstotl * peri**2)**(1. / 3.) # [AU]
    
    return smax


def retr_duratran(peri, rsma, cosi):
    """
    Return the transit duration in the unit of the input orbital period (peri).

    Arguments
        peri: orbital period
        rsma: the sum of radii of the two bodies divided by the semi-major axis
        cosi: cosine of the inclination
    """    
    
    dura = 24. * peri / np.pi * np.arcsin(np.sqrt(rsma**2 - cosi**2)) # [hours]
    
    return dura


# massplan in M_E
# massstar in M_S
def retr_rvelsema(peri, massplan, massstar, incl, ecce):
    
    dictfact = retr_factconv()
    
    rvelsema = 203. * peri**(-1. / 3.) * massplan * np.sin(incl / 180. * np.pi) / \
                                                    (massplan + massstar * dictfact['msme'])**(2. / 3.) / np.sqrt(1. - ecce**2) # [m/s]

    return rvelsema


# semi-amplitude of radial velocity of a two-body
# masstar in M_S
# massplan in M_J
# peri in days
# incl in degrees
def retr_rvel(time, epoc, peri, massplan, massstar, incl, ecce, arguperi):
    
    phas = (time - epoc) / peri
    phas = phas % 1.
    #consgrav = 2.35e-49
    #cons = 1.898e27
    #masstotl = massplan + massstar
    #smax = 
    #ampl = np.sqrt(consgrav / masstotl / smax / (1. - ecce**2))
    #rvel = cons * ampl * mass * np.sin(np.pi * incl / 180.) * (np.cos(np.pi * arguperi / 180. + 2. * np.pi * phas) + ecce * np.cos(np.pi * arguperi / 180.))

    ampl = 203. * peri**(-1. / 3.) * massplan * np.sin(incl / 180. * np.pi) / \
                                                    (massstar + 9.548e-4 * massplan)**(2. / 3.) / np.sqrt(1. - ecce**2) # [m/s]
    rvel = ampl * (np.cos(np.pi * arguperi / 180. + 2. * np.pi * phas) + ecce * np.cos(np.pi * arguperi / 180.))

    return rvel


def retr_factconv():
    
    dictfact = dict()

    dictfact['rsrj'] = 9.731
    dictfact['rjre'] = 11.21
    dictfact['rsre'] = dictfact['rsrj'] * dictfact['rjre']
    dictfact['msmj'] = 1048.
    dictfact['mjme'] = 317.8
    dictfact['msme'] = dictfact['msmj'] * dictfact['mjme']
    dictfact['aurs'] = 215.
    dictfact['pcau'] = 206265.

    return dictfact


def retr_alphelli(u, g):
    
    alphelli = 0.15 * (15 + u) * (1 + g) / (3 - u)
    
    return alphelli


def plot_anim():

    pathbase = os.environ['PEXO_DATA_PATH'] + '/imag/'
    radistar = 0.9
    
    booldark = True
    
    boolsingside = False
    boolanim = True
                  ## 'realblac': dark background, black planet
                  ## 'realblaclcur': dark backgound, black planet, light curve
                  ## 'realcolrlcur': dark backgound, colored planet, light curve
                  ## 'cartcolr': cartoon backgound
    listtypevisu = ['realblac', 'realblaclcur', 'realcolrlcur', 'cartcolr']
    listtypevisu = ['realblac', 'cartcolr']
    path = pathbase + 'orbt'
    
    for a in range(2):
    
        radiplan = [1.6, 2.1, 2.7, 3.1]
        rsma = [0.0895, 0.0647, 0.0375, 0.03043]
        epoc = [2458572.1128, 2458572.3949, 2458571.3368, 2458586.5677]
        peri = [3.8, 6.2, 14.2, 19.6]
        cosi = [0., 0., 0., 0.]
        
        if a == 1:
            radiplan += [2.0]
            rsma += [0.88 / (215. * 0.1758)]
            epoc += [2458793.2786]
            peri += [29.54115]
            cosi += [0.]
        
        for typevisu in listtypevisu:
            
            if a == 0:
                continue
    
            pexo.main.plot_orbt( \
                                path, \
                                radiplan, \
                                rsma, \
                                epoc, \
                                peri, \
                                cosi, \
                                typevisu, \
                                radistar=radistar, \
                                boolsingside=boolsingside, \
                                boolanim=boolanim, \
                                #typefileplot='png', \
                               )
        



