import argparse
import os

from ddsp.colab import colab_utils
import ddsp.training

parser = argparse.ArgumentParser()
parser.add_argument("--tfrecord_file_pattern")
parser.add_argument("--save_dir")

args = parser.parse_args()

data_provider = ddsp.training.data.TFRecordProvider(args.tfrecord_file_pattern)
dataset = data_provider.get_dataset(shuffle=False)
pickle_file_path = os.path.join(args.save_dir, "dataset_statistics.pkl")

colab_utils.save_dataset_statistics(data_provider, pickle_file_path, batch_size=1)
