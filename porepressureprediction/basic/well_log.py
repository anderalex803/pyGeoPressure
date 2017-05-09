# -*- coding: utf-8 -*-
"""
class Log for well log data

Created on Fri Apr 18 2017
"""
from __future__ import division, print_function, absolute_import

__author__ = "yuhao"

import numpy as np


class Log(object):
    """
    class for well log
    """
    def __init__(self, file_name=None):
        self.name = ""
        self.units = ""
        self.descr = ""
        self.data = list()
        self.depth = list()
        self.log_start = None
        self.log_stop = None
        self.depth_start = None
        self.depth_stop = None
        self.log_start_idx = None
        self.log_stop_idx = None
        if file_name is not None:
            self.read_od(file_name)

    def __len__(self):
        return len(self.data)

    def _info(self):
        return "Log Name: {}\n".format(self.name) +\
               "Attribute Name: {}\n".format(self.descr) +\
               "Log Units: {}\n".format(self.units) +\
               "Depth range: {} - {} - {}\n".format(
                   self.depth[0], self.depth[-1], 0.1)

    def __str__(self):
        return self._info()

    def __repr__(self):
        return self._info()

    @property
    def start(self):
        if self.log_start is None:
            for dep, dat in zip(self.depth, self.data):
                if dat is not np.nan:
                    self.log_start = dep
                    break
        return self.log_start

    @property
    def start_idx(self):
        for i, dat in enumerate(self.data):
            # if dat is not np.nan:
            if np.isfinite(dat):
                self.log_start_idx = i
                break
        return self.log_start_idx

    @property
    def stop(self):
        if self.log_stop is None:
            for dep, dat in zip(reversed(self.depth), reversed(self.data)):
                if dat is not np.nan:
                    self.log_stop = dep
                    break
        return self.log_stop

    @property
    def stop_idx(self):
        for i, dat in reversed(list(enumerate(self.data))):
            if dat is not np.nan:
                self.log_stop_idx = i + 1
                # so when used in slice, +1 will not needed.
                break
        return self.log_stop_idx

    @property
    def top(self):
        return self.depth[0]

    @property
    def bottom(self):
        return self.depth[-1]

    def read_od(self, file_name):
        try:
            with open(file_name, "r") as fin:
                info_list = fin.readline().split('\t')
                temp_list = info_list[-1].split('(')
                self.descr = temp_list[0]
                self.units = temp_list[1][:-2]
                for line in fin:
                    tempList = line.split()
                    self.depth.append(round(float(tempList[0]), 1))
                    if tempList[1] == "1e30":
                        self.data.append(np.nan)
                    else:
                        self.data.append(float(tempList[1]))
        except Exception as inst:
            print('{}: '.format(self.name))
            print(inst.args)

    def write_od(self, file_name):
        try:
            with open(file_name, 'w') as fout:
                split_list = self.descr.split(' ')
                description = '_'.join(split_list)
                fout.write("Depth(m)\t" + description + "(" + self.units + ")\n")
                for d, v in zip(self.depth, self.data):
                    d = str(d)
                    v = str(v) if np.isfinite(v) else "1e30"
                    fout.write("\t".join([d, v]) + "\n")
        except Exception as inst:
            print(inst.args)

    def get_depth_idx(self, d):
        if d > self.bottom or d < self.top:
            return None
        else:
            return int((d - self.top) // 0.1)

    def get_data(self, depth):
        depth_idx = list()
        for de in depth:
            depth_idx.append(self.get_depth_idx(de))
        log_depth = np.array(self.depth)
        log_data = np.array(self.data)
        mask = log_depth < 0
        for idx in depth_idx:
            if idx is not None:
                mask[idx] = True
        return log_data[mask]

def rolling_window(a, window):
    a = np.array(a)
    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
    strides = a.strides + (a.strides[-1],)
    rolled = np.lib.stride_tricks.as_strided(
        a, shape=shape, strides=strides)
    return rolled


def despike(curve, curve_sm, max_clip):
    spikes = np.where(curve - curve_sm > max_clip)[0]
    spukes = np.where(curve_sm - curve > max_clip)[0]
    out = np.copy(curve)
    out[spikes] = curve_sm[spikes] + max_clip
    out[spukes] = curve_sm[spukes] - max_clip
    return out


def smooth_log(log, window=3003):
    """
    Parameter
    ---------
    log : Log object
        log to smooth
    window : scalar
        window size of the median filter

    Return
    ------
    smoothed log : Log object
        smoothed log
    """
    # data2smooth = copy.copy(log.data)
    # data2smooth = log.data[log.start_idx:log.stop_idx]
    mask = np.isfinite(log.data)
    data = np.array(log.data)
    data2smooth = data[mask]
    print(data2smooth)
    data_sm = np.median(rolling_window(data2smooth, window), -1)
    data_sm = np.pad(data_sm, window // 2, mode="edge")
    print(data_sm)
    # log_sm = np.array(copy.copy(log.data))
    # log_sm[log.start_idx:log.stop_idx] = data_sm
    log_sm = np.full_like(data, np.nan)
    log_sm[mask] = data_sm
    print(type(log_sm))
    print(np.any(data_sm))
    logSmoothed = Log()
    logSmoothed.name = log.name + "_sm"
    logSmoothed.units = log.units
    logSmoothed.descr = log.descr
    logSmoothed.depth = log.depth
    logSmoothed.data = log_sm
    return logSmoothed


def truncate_log(log, top, bottom):
    """
    Remove unreliable values in the top and bottom section of well log

    Parameters
    ----------
    log : Log object
    top, bottom : scalar
        depth value

    Returns
    -------
    trunc_log : Log object
    """
    depth = np.array(log.depth)
    data = np.array(log.data)
    if top != 0:
        mask = depth < top
        data[mask] = np.nan
    if bottom != 0:
        mask = depth > bottom
        data[mask] = np.nan
    trunc_log = Log()
    trunc_log.name = log.name + '_trunc'
    trunc_log.units = log.units
    trunc_log.descr = log.descr
    trunc_log.depth = depth
    trunc_log.data = data
    return trunc_log


def shale(log, vsh_log, thresh=0.35):
    """
    Discern shale intervals

    log : Log
        log to discern
    vsh_log : Log
        shale volume log
    thresh : scalar
        percentage threshold, 0 < thresh < 1
    """
    shale_mask = np.isfinite(vsh_log.depth)
    shale_mask[vsh_log.start_idx: vsh_log.stop_idx] = True
    mask_thresh = np.array(vsh_log.data) < thresh
    mask = shale_mask * mask_thresh
    data = np.array(log.data)
    data[mask] = np.nan
    log_sh = Log()
    log_sh.name = log.name + "_sh"
    log_sh.units = log.units
    log_sh.descr = log.descr
    log_sh.depth = log.depth
    log_sh.data = data
    return log_sh


def interpolate_log(log):
    "log curve interpolation"
    depth = np.array(log.depth)
    data = np.array(log.data)
    # interpolation function
    mask_finite = np.isfinite(data)
    func = interpolate.interp1d(depth[mask_finite], data[mask_finite])
    mask = np.isnan(depth)
    mask[log.start_idx: log.stop_idx] = True
    mask_nan = np.isnan(data)
    mask = mask * mask_nan
    data[mask] = func(depth[mask])
    interp_log = Log()
    interp_log.name = log.name + '_interp'
    interp_log.units = log.units
    interp_log.descr = log.descr
    interp_log.depth = depth
    interp_log.data = data
    return interp_log