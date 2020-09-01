import numpy as np

def make_layer(pca, edits):
    amounts = np.zeros(pca["comp"].shape[:1], dtype=np.float32)
    edits_len = edits.shape[0]
    stdevs = pca["stdev"]
    stdevs_len = stdevs.shape[0]
    if edits_len > stdevs_len:
        raise ValueError("too many edits ({}) - PCA size is {}".format(edits_len, stdevs_len))
  
    padding = stdevs_len - edits_len
    edits_padded = edits
    
    if padding > 0:
        edits_padded = np.concatenate([edits, np.zeros(padding, dtype=edits.dtype)])
    
    amounts[:len(list(edits_padded))] = edits_padded * stdevs
    
    scaled_directions = amounts.reshape(-1, 1, 1, 1) * pca["comp"]
  
    layer = pca["global_mean"] + np.sum(scaled_directions, axis=0)

    return layer
