from scipy.ndimage import map_coordinates
import sol4_utils as ut
import sol4_add as ad
import matplotlib.pyplot as plt
import numpy as np
import functools
from scipy.signal import convolve2d

def harris_corner_detector(im):
    der = np.array([[1,0,-1]])

    I_x = convolve2d(im, der, mode='same')
    I_y = convolve2d(im, np.transpose(der), mode='same')

    M = np.array([np.square(I_x), np.multiply(I_x, I_y), np.square(I_y)])
    M = np.array(list(map(functools.partial(ut.blur_spatial_rev, 3), M)))
    R = np.multiply(M[0], M[2]) - np.square(M[1]) - 0.04 * np.square((M[0] + M[2]))

    return np.transpose(np.nonzero(ad.non_maximum_suppression(R)))

def sample_descriptor(im, pos, desc_rad):
    K = 1 + (2 * desc_rad)
    desc = np.zeros((K, K, pos.shape[0]), dtype=np.float32)
    for idx in range(len(pos)):
        x, y = pos[idx][0].astype(np.float32) / 4, pos[idx][1].astype(np.float32) / 4
        X, Y = np.meshgrid(np.linspace(x - desc_rad, x + desc_rad, K, dtype=np.float32),
                             np.linspace(y - desc_rad, y + desc_rad, K, dtype=np.float32))

        XY = [X.reshape(K ** 2, ), Y.reshape(K ** 2, )]
        iter_mat = map_coordinates(im, np.array(XY), order=1, prefilter=False).reshape(K, K)
        mu = np.mean(iter_mat)
        desc[:, :, idx] = (iter_mat - mu) / np.linalg.norm(iter_mat - mu)
        if np.any(np.isnan(desc[:, :, idx])):
            continue
    return desc
#
# # NOT REQUIRED
# # def im_to_points(im):
# #     return
#
#
def find_features(pyr):
    pos = ad.spread_out_corners(pyr[0], 7, 7, 12)
    return pos, sample_descriptor(pyr[2], pos, 3)


def match_features(desc1, desc2, min_score):

    flat1 = np.reshape(desc1, (-1, desc1.shape[2])).transpose().astype(dtype=np.float32)
    flat2 = np.reshape(desc2, (-1, desc2.shape[2])).transpose().astype(dtype=np.float32)

    score_desc1 = np.zeros([flat1.shape[0], 2, 2])
    score_desc2 = np.zeros([flat2.shape[0], 2, 2])

    to_iter = np.dstack(np.meshgrid(np.arange(flat1.shape[0]), np.arange(flat2.shape[0]))).reshape(-1, 2)

    for (i1, i2) in to_iter:

        product = np.inner(flat1[i1], flat2[i2])
        if product <= min_score:
            continue

        if product >= score_desc1[i1, 1, 0]:
            if product >= score_desc1[i1, 0, 0]:
                score_desc1[i1, 1, :] = score_desc1[i1, 0, :]
                score_desc1[i1, 0, :] = product, i2
            else:
                score_desc1[i1, 1, :] = product, i2

        if product >= score_desc2[i2, 1, 0]:
            if product >= score_desc2[i2, 0, 0]:
                score_desc2[i2, 1, :] = score_desc2[i2, 0, :]
                score_desc2[i2, 0, :] = product, i1
            else:
                score_desc2[i2, 1, :] = product, i1

    ret_desc1 = []
    ret_desc2 = []

    for (i1, i2) in to_iter:
        if ((score_desc1[i1, 0, 1] == i2 or score_desc1[i1, 1, 1] == i2)) and \
                ((score_desc2[i2, 0, 1] == i1 or score_desc2[i2, 1, 1] == i1)):
            for i, j in np.dstack(np.meshgrid(np.arange(2), np.arange(2))).reshape(-1, 2):
                if score_desc1[i1, i, 0] == score_desc2[i2, j, 0]:
                    ret_desc1.append(i1)
                    ret_desc2.append(i2)
                    break

    return np.array(ret_desc1), np.array(ret_desc2)

# --------------------------3.3-----------------------------#


    #############################################################
    # compute accumulated homographies between successive images
    #############################################################    #############################################################
    # compute accumulated homographies between successive images
    #############################################################
# def apply_homography(pos1, H12):
#     def apply_single_homography(H12, pair):
#         coordin = np.array([pair[0], pair[1], 1])
#         product = np.dot(H12, coordin)
#         return product[:2] / product[2]
#     return np.apply_along_axis(functools.partial(apply_single_homography, H12), 1, pos1)

# def apply_homography(pos1, H12):
#
#     expand = np.column_stack((pos1, np.ones(len(pos1))))
#     dot = np.dot(H12, expand.T).T
#     normalized = (dot.T / dot[:,2]).T
#     return np.delete(normalized, -1, axis=1)

def ransac_homography(pos1, pos2, num_iters, inlier_tol):

    apply_hom_const = functools.partial(apply_homography, pos1)
    rand_array = np.random.random_integers(0, pos1.shape[0] - 1, size=(num_iters, 4))

    def all_least_squares(cuad_rand):
        H12 = ad.least_squares_homography(pos1[cuad_rand], pos2[cuad_rand])
        if H12 is None:
            return 0
        return np.sum(np.ones(pos2.shape[0])[np.sum(np.square(apply_hom_const(H12) - pos2), axis=1) < inlier_tol])

    rand_results= np.apply_along_axis(all_least_squares, 1, rand_array)
    H12 = ad.least_squares_homography(pos1[rand_array[rand_results.argmax()]],
                                      pos2[rand_array[rand_results.argmax()]])
    true_samples= np.arange(pos1.shape[0])[np.sum(np.square(apply_hom_const(H12) - pos2), axis=1) < inlier_tol]
    H12 = ad.least_squares_homography(pos1[true_samples], pos2[true_samples])

    return H12, true_samples

    #############################################################
    # compute accumulated homographies between successive images
    #############################################################    #############################################################
    # compute accumulated homographies between successive images
    #############################################################
def display_matches(im1, im2, pos1, pos2, inliers):
    pos1, pos2 = np.array(pos1), np.array(pos2)
    ins1, ins2 = pos1[inliers], pos2[inliers]
    out1, out2 = np.delete(pos1, inliers, axis=0), np.delete(pos2, inliers, axis=0)
    plt.figure()
    plt.imshow(np.hstack((im1, im2)), 'gray')
    plt.plot([ins1[:, 1], ins2[:, 1] + im1.shape[1]], [ins1[:, 0], ins2[:, 0]], mfc='r', c='y', lw=1.1, ms=5, marker='o')
    # plt.plot([out1[:, 1], out2[:, 1] + im1.shape[1]], [out1[:, 0], out2[:, 0]], mfc='r', c='b', lw=0.4, ms=5, marker='o')
    plt.show()

# --------------------------4.1-----------------------------#

def accumulate_homographies(H_successive, m):
    #############################################################
    # compute accumulated homographies between successive images
    #############################################################

    ret_H = np.zeros(H_successive.shape)
    ret_H[m] = np.eye(3)
    for i in reversed(range(m)):
        ret_H[i] = H_successive[i].dot(ret_H[i + 1])

    ret_H[m:] = np.apply_along_axis(np.linalg.inv, 0, H_successive[m:])

    for i in range(m + 1, H_successive.shape[0]):
        ret_H[i] = ret_H[i].dot(ret_H[i - 1])

    return np.divide(ret_H, ret_H[:,2,2])

# --------------------------4.3-----------------------------#

# NOT REQUIRED
# def prepare_panorama_base(ims, Hs):
#     return


def render_panorama(ims, Hs):
    # def apply_homography(pos1, H12):
    def relevant_points(im):
        return np.array((im[0, 0], im[0,- 1], im[-1, 0],
                         im[-1, -1], im[im[0] // 2, im[1] // 2]))

    relevant_points = np.apply_along_axis(relevant_points, 0, ims)


    return

if __name__ == '__main__':

    # --------------------------end-----------------------------#
    #
    im1 = ut.read_image(ut.relpath("external/oxford1.jpg"), 1)
    # im2 = ut.read_image(ut.relpath("external/oxford2.jpg"), 1)
    #
    pyr1, _ = ut.build_gaussian_pyramid(im1, max_levels=3, filter_size=3)
    # pyr2, _ = ut.build_gaussian_pyramid(im2, max_levels=3, filter_size=3)
    #
    pos1, desc1 = find_features(pyr1)
    # pos2, desc2 = find_features(pyr2)
    #
    # match1, match2 = match_features(desc1, desc2, min_score=0.7)
    #
    # H12, inliers_ = ransac_homography(match1, match2, num_iters = 100, inlier_tol=10)
    #
    # display_matches(im1, im2, pos1, pos2, inliers_)

    plt.imshow(im1, 'gray')
    plt.scatter(pos1[:,0], pos1[:,1])
    plt.show()