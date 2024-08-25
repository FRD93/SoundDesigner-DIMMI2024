# -*- coding: utf-8 -*-

#################################################################################
# THIS LIBRARY CONTAINS CLASSES FOR ARRAY PROCESSING.
# ©2017  Francesco Roberto Dani
# f.r.d@hotmail.it
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#################################################################################

import math
import numpy as np
import sklearn.utils
from scipy import spatial
from scipy import signal
from scipy.interpolate import UnivariateSpline


def dynamics_compander(array, threshold, slope_above, slope_below, knee_width):
    def scale_variable(variable, threshold, slope_above, slope_below, knee_width):
        if variable < threshold - knee_width / 2:
            scaled_value = variable * slope_below
        elif variable > threshold + knee_width / 2:
            scaled_value = variable * slope_above
        else:
            scaled_value = ((variable - (threshold - knee_width / 2)) / knee_width) * (slope_above - slope_below) + slope_below
        return scaled_value
    return np.array([scale_variable(value, threshold, slope_above, slope_below, knee_width) for value in array])


def resize(array, new_length, k=3):
    old_indices = np.arange(0, len(array))
    new_indices = np.linspace(0, len(array) - 1, new_length)
    spl = UnivariateSpline(old_indices, array, k=k, s=0)
    return spl(new_indices)


def wrap(number, _min, _max):
    return ((number - _min) % (_max - _min + 1)) + _min


def clip(number, _min, _max):
    return np.clip(number, _min, _max)


def wrapAt(vector, index):
    return vector[wrap(index, 0, len(vector) - 1)]


def flop(vector):
    return list(map(list, zip(*vector)))


def chunks(lst, n):
    residual = len(lst) % n
    if residual > 0:
        lst = lst[:-1 * residual]
    return np.stack([lst[i:i + n] for i in range(0, len(lst), n)])


def chunks_hop(lst, n, h):
    residual = len(lst) % n
    if residual > 0:
        lst = lst[:-1 * residual]
    return np.stack(
        [lst[i * h:(i * h) + n] for i in range(int((len(lst) - h) / h) - 1) if len(lst[i * h:(i * h) + n]) == n])


def rms_chunks(vec, n):
    return [rms(chunk) for chunk in chunks(vec, n)]


def sig_power(vec):
    return np.divide(np.sum(np.power(np.asarray(vec), 2)), len(vec))


def sig_power_chunks(vec, n):
    return [sig_power(chunk) for chunk in chunks(vec, n)]


def threshold(vec, thresh):
    """
    Threshold a list or numpy array and return an array with elementwise thresholded values.

    Args:
        vec (list or numpy array): A list or numpy array.
        thresh (float): Threshold.
    """
    return np.asarray([1 if val > thresh else 0 for val in vec])


def differentiate(vec, keep_dim=True):
    """
    Compute the first derivative of a list or numpy array.

    Args:
        vec (list or np.array): The list or numpy array to differentiate.
        keep_dim (bool): Whether to keep the input dimension or not.

    Returns:
        array (np.array): The first derivative of the list or numpy array
    """
    if keep_dim:
        return np.asarray([0] + [vec[i + 1] - vec[i] for i in range(len(vec) - 1)])
    else:
        return np.asarray([vec[i + 1] - vec[i] for i in range(len(vec) - 1)])


# print(differentiate([1, 2, 3, 0, 1, 4, 2], True))

def diff_sign(vec):
    """
    Computes the sign of a list or 1d numpy array.

    Args:
        vec (list or np.array): The list or 1d numpy array.

    Returns:
        array (np.array): The sign of the input list or 1d numpy array.
    """
    return np.asarray([1 if vec[i] > 0 else -1 if vec[i] < 0 else 0 for i in range(len(vec))])


def normalize(array):
    """
    Normalize a list or numpy array between 0.0 and 1.0.

    Args:
        array (list or np.array): The list or numpy array to be normalized.

    Returns:
        array (np.array): The normalized numpy array.
    """
    if len(array.shape) == 1:
        amax = np.amax(array)
        amin = np.amin(array)
    elif len(array.shape) == 2:
        amax = np.amax([np.amax(vec) for vec in array])
        amin = np.amin([np.amin(vec) for vec in array])
    else:
        return array
    array = np.subtract(array, amin)
    if (amax - amin) != 0:
        return array / (amax - amin)
    else:
        return array


def normalize2(array):
    """
    Normalize a list or numpy array between -1.0 and 1.0.

    Args:
        array (list or np.array): The list or numpy array to be normalized.

    Returns:
        array (np.array): The normalized numpy array.
    """
    array = np.array(array).astype(np.float32)
    amax = np.amax(array)
    amin = np.amin(array)
    array = np.subtract(array, amin)
    if (amax - amin) != 0:
        # return (array * 2.0 / (amax - amin)) - 1.0
        return np.subtract(np.divide(np.multiply(array, 2), (amax - amin)), 1.0)
    else:
        return array


def mmap(number, range1, range2):
    """
    Map a number from a range to another.

    Args:
        number (float): The number to map.
        range1: (tuple<float>): Input domain (min, max).
        range2: (tuple<float>): Output domain (min, max).

    Returns:
        number (float): The mapped number.
    """
    if (range1[1] - range1[0]) == 0 or (range2[1] - range2[0]) == 0:
        return 0
    else:
        return (((number - range1[0]) / (range1[1] - range1[0])) * (range2[1] - range2[0])) + range2[0]


def rotate(list, N):
    """
    Rotate a list by N elements and convert to numpy array.

    Args:
        list (list or np.array): The list to rotate.
        N (int): The number of elements to be rotated.

    Returns:
        list (np.array): The rotated list.
    """
    return np.concatenate((np.array(list[N:]), np.array(list[:N])), axis=0)


'''
- - FUNCTION split_list_by_boolean() - -

splits the list A whenever there are consecutive True values in the corresponding positions of list B.

- Attributes:

- - A:
- - - a N-dimensional list (or numpy array)

- - B:
- - - a 1-d boolean list (or numpy array)

- Usage:

print(split_list_by_boolean([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [True, True, False, False, True, True, True, False, True, False])
Output >>> [[1, 2], [5, 6, 7], [9]]
'''


def split_list_by_boolean(A, B):
    """
    Splits the list A whenever there are consecutive True values in the corresponding positions of list B.\n
    Example:\n
    print(split_list_by_boolean([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [True, True, False, False, True, True, True, False, True, False])\n
    Output >>> [[1, 2], [5, 6, 7], [9]]

    Args:
        A (list or np.array): The list to process.
        B (list<bool> or np.array<bool>): The boolean list.

    Returns:
        list (list): The splitted list.
    """
    result = []
    current_split = []
    for sublist, value in zip(A, B):
        if value:
            current_split.append(sublist)
        elif current_split:
            result.append(current_split)
            current_split = []
    if current_split:
        result.append(current_split)
    return result


def moving_average(data, window_size):
    """
        Compute the moving average of a 1D numpy array

        Args:
            data (np.array): The array to process.
            window_size (int): Window size.

        Returns:
            data (np.array): The averaged array.
        """
    weights = np.repeat(1.0, window_size) / window_size
    return np.convolve(data, weights, 'valid')


def resample(array, new_length):
    """
    Resample a 1D numpy array to a specified length using linear interpolation.
    If the input array has more than one column, only the first column is used.

    Parameters:
    array (numpy.ndarray): The input array.
    new_length (int): The desired length of the output array.

    Returns:
    numpy.ndarray: The resampled 1D array.
    """
    # Ensure input is a numpy array
    array = np.asarray(array)

    # If the input array has more than one column, use only the first column
    if array.ndim > 1 and array.shape[1] > 1:
        array = array[:, 0]

    # Generate the old and new indices
    old_indices = np.linspace(0, len(array) - 1, num=len(array))
    new_indices = np.linspace(0, len(array) - 1, num=new_length)

    # Perform the interpolation
    resampled_array = np.interp(new_indices, old_indices, array)

    return resampled_array

'''
- - FUNCTION stddev() - -

A function to calculate the standard
deviation of a numpy array.

- Attributes:

- - array:
- - - a 1-dimensional numpy array


- Usage:

print(stddev([1, 1, 1, 1000]))

'''


def stddev(array):
    mean = np.sum(array) / len(array)
    std = 0
    for j in range(len(array)):
        std = std + np.power((array[j] - mean), 2)
    std = np.sqrt((std / len(array)))
    return std


'''
- - FUNCTION variance() - -

A function to calculate the variance
of a numpy array.
https://it.wikipedia.org/wiki/Covarianza_(probabilità)

- Attributes:

- - array:
- - - a 1-dimensional numpy array


- Usage:

print(variance([1, 1, 20, 1, 1, 1, 1, 1]))

'''


def variance(array):
    mean = np.mean(array)
    var_ = 0
    for i, x in enumerate(array):
        var_ = var_ + np.power(x - mean, 2)
    return var_


'''
- - FUNCTION covariance() - -

A function to calculate the covariance
of 2 numpy arrays.
https://it.wikipedia.org/wiki/Covarianza_(probabilità)
http://ncalculators.com/statistics/covariance-calculator.htm

- Attributes:

- - array1:
- - - a 1-dimensional numpy array

- - array2:
- - - a 1-dimensional numpy array


- Usage:

print(covariance([65.21, 64.75, 65.26, 65.76, 65.96], [67.25, 66.39, 66.12, 65.70, 66.64]))

'''


def covariance(array1, array2):
    if len(array1) != len(array2):
        print("Size of the two arrays differ! Breaking...")
        pass
    size = len(array1) - 1
    mean1 = np.mean(array1)
    mean2 = np.mean(array2)
    covar = 0
    for i, x in enumerate(array1):
        covar = covar + ((x - mean1) * (array2[i] - mean2))
    return covar / size


'''
- - FUNCTION correlation() - -

A function to calculate the correlation
of 2 numpy arrays.
http://www.math.uah.edu/stat/expect/Covariance.html

- Attributes:

- - array1:
- - - a 1-dimensional numpy array

- - array2:
- - - a 1-dimensional numpy array


- Usage:

print(correlation([65.21, 64.75, 65.26, 65.76, 65.96], [67.25, 66.39, 66.12, 65.70, 66.64])) # returns 0.058
print(correlation(np.random.random(100000) * 100, np.random.random(100000) * 100)) # returns -0.00185575395109

'''


def correlation(array1, array2):
    # return covariance(array1, array2) / ( stddev(array1) * stddev(array2) )
    return covariance(array1, array2) / np.sqrt(variance(array1) * variance(array2))


'''
- - FUNCTION flatness() - -

A function to calculate the flatness
of a numpy array.
https://en.wikipedia.org/wiki/Spectral_flatness

- Attributes:

- - array:
- - - a 1-dimensional numpy array


- Usage:

print(flatness([1, 1, 1, 10, 10, 10, 500, 1]))

'''


def flatness(array):
    sum_ = np.sum(array)
    ln_sum = 0
    for i, num in enumerate(array):
        ln_sum = ln_sum + math.log(array[i])
    ln_sum = ln_sum / len(array)
    return math.exp(ln_sum) / (sum_ / len(array))


'''
- - FUNCTION rms() - -

A function to calculate rms value
of a numpy array.
https://it.wikipedia.org/wiki/Valore_efficace

- Attributes:

- - array:
- - - a 1-dimensional numpy array


- Usage:

print(rms([1, 1, 5, 0, 0, 0]))

'''


def rms(array):
    return np.sqrt(np.sum(np.power(array, 2)) / len(array))


'''
- - FUNCTION crest() - -

A function to calculate the crest value
of a numpy array.
https://en.wikipedia.org/wiki/Crest_factor

- Attributes:

- - array:
- - - a 1-dimensional numpy array


- Usage:

print(crest([10000, 0, 0, 0, 0, 0, 0, 0, 0, 0]))

'''


def crest(array):
    return np.amax(np.abs(array)) / rms(array)


'''
- - FUNCTION hfc() - -

A function to calculate the high 
frequency content of a numpy array.
https://en.wikipedia.org/wiki/High_frequency_content_measure

- Attributes:

- - array:
- - - a 1-dimensional numpy array


- Usage:

print(hfc([0, 0, 0, 1, 1, 1, 1, 1, 1, 100]))

'''


def hfc(array):
    hfc_ = 0
    for i, x in enumerate(array):
        hfc_ = hfc_ + (i * abs(x))
    return hfc_


'''
- - FUNCTION centroid() - -

A function to calculate the centroid
of a numpy array.

- Attributes:

- - array:
- - - a 1-dimensional numpy array


- Usage:

print(centroid([1, 1, 1, 10, 10, 10, 500, 1]))

'''


def centroid(array):
    sum_ = np.sum(array)
    weighted_sum = 0
    for i, x in enumerate(array):
        weighted_sum = weighted_sum + ((i / len(array)) * x)
    return weighted_sum / sum_


'''
- - FUNCTION spread() - -

A function to calculate the spread
of a numpy array.

- Attributes:

- - array:
- - - a 1-dimensional numpy array


- Usage:

print(spread([1, 1, 1, 10, 10, 10, 500, 1]))

'''


def spread(array):
    mu = np.mean(array)
    rho = array / np.sum(array)
    print(rho)
    spread = 0
    for i, x in enumerate(array):
        spread = spread + (np.power((x - mu), 2) * rho[i])
    return spread


'''
- - FUNCTION buildKDTree() - -

A function to build a k-nearest neighbour tree
from given features data.


- Attributes:

- - features:
- - - an n-dimensional vector in which is stored feature data


- Usage:

features = np.array([[1, 2, 3], [2, 2, 9], [5, 2, 1], [4, 2, 0], [9, 8, 1]])
tree = buildKDTree(features)
print(tree)

'''


def buildKDTree(features):
    return spatial.KDTree(np.array(features).T)


'''
- - FUNCTION queryKDTree() - -

A function to query from a k-nearest neighbour tree
a definite number of neighbours by a given point in the space.


- Attributes:

- - kdtree:
- - - a k-nearest neighbour tree

- - point:
- - - a list of the same size as the kdtree's dimensions defining a point in that space

- - neighbours:
- - - an integer defining how many neighbours to return


- Usage:

features = np.array([[1, 2, 3], [2, 2, 9], [5, 2, 1], [4, 2, 0], [9, 8, 1]])
tree = buildKDTree(features)
indexes = queryKDTree(tree, (1, 3, 2, 4, 0), 3)
print(indexes)

'''


def queryKDTree(kdtree, point, neighbours):
    return kdtree.query(point, neighbours)[1]
