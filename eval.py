import tensorflow as tf
import numpy as np
import os
import subprocess
from utils import get_logger
import data_helpers
import utils
from configure import FLAGS
from sklearn.metrics import classification_report
import time

def eval():
    log_file_name = time.strftime("%Y-%m-%d-%H%M%S", time.localtime()) + FLAGS.test_log_file
    log_path = os.path.join("log", log_file_name)
    logger = get_logger(log_path)
    with tf.device('/cpu:0'):
        x_text, y, x_id = data_helpers.load_data_and_labels(FLAGS.test_path)

    # Map data into vocabulary
    text_path = os.path.join(FLAGS.checkpoint_dir, "..", "vocab")  # ..是往上走一层的意思
    text_vocab_processor = tf.contrib.learn.preprocessing.VocabularyProcessor.restore(text_path)
    x = np.array(list(text_vocab_processor.transform(x_text))) # 将文字转为id

    checkpoint_file = tf.train.latest_checkpoint(FLAGS.checkpoint_dir)
    logger.info("checkpoint dir:{}\t".format(FLAGS.checkpoint_dir))
    logger.info("checkpoint file:{}\t".format(checkpoint_file))

    graph = tf.Graph()
    with graph.as_default():
        session_conf = tf.ConfigProto(
            allow_soft_placement=FLAGS.allow_soft_placement,
            log_device_placement=FLAGS.log_device_placement)
        session_conf.gpu_options.allow_growth = FLAGS.gpu_allow_growth
        sess = tf.Session(config=session_conf)
        with sess.as_default():
            # Load the saved meta graph and restore variables
            saver = tf.train.import_meta_graph("{}.meta".format(checkpoint_file))
            saver.restore(sess, checkpoint_file)

            # Get the placeholders from the graph by name
            input_text = graph.get_operation_by_name("input_text").outputs[0]
            # input_y = graph.get_operation_by_name("input_y").outputs[0]
            emb_dropout_keep_prob = graph.get_operation_by_name("emb_dropout_keep_prob").outputs[0]
            rnn_dropout_keep_prob = graph.get_operation_by_name("rnn_dropout_keep_prob").outputs[0]
            dropout_keep_prob = graph.get_operation_by_name("dropout_keep_prob").outputs[0]

            # Tensors we want to evaluate
            predictions = graph.get_operation_by_name("output/predictions").outputs[0]

            # Generate batches for one epoch
            batches = data_helpers.batch_iter(list(x), FLAGS.batch_size, 1, shuffle=False)

            # Collect the predictions here
            preds = []
            for x_batch in batches:
                pred = sess.run(predictions, {input_text: x_batch,
                                              emb_dropout_keep_prob: 1.0,
                                              rnn_dropout_keep_prob: 1.0,
                                              dropout_keep_prob: 1.0})
                preds.append(pred)
            preds = np.concatenate(preds)
            truths = np.argmax(y, axis=1)

            prediction_path = os.path.join(FLAGS.checkpoint_dir, "..", "predictions.txt")
            truth_path = os.path.join(FLAGS.checkpoint_dir, "..", "ground_truths.txt")
            prediction_file = open(prediction_path, 'w')
            truth_file = open(truth_path, 'w')
            for i in range(len(preds)):
                prediction_file.write("{}\t{}\n".format(x_id[i], utils.label2class[preds[i]]))
                truth_file.write("{}\t{}\n".format(x_id[i], utils.label2class[truths[i]]))
            prediction_file.close()
            truth_file.close()
            # 打印每种关系的PRF
            target_names = utils.class2label.keys();
            labels = list(utils.label2class.keys());
            repo = classification_report(truths, preds,
                                         target_names=target_names, labels=labels)
            logger.info(repo)

            # perl_path = os.path.join(os.path.curdir,
            #                          "SemEval2010_task8_all_data",
            #                          "SemEval2010_task8_scorer-v1.2",
            #                          "semeval2010_task8_scorer-v1.2.pl")
            # process = subprocess.Popen(["perl", perl_path, prediction_path, truth_path], stdout=subprocess.PIPE)
            # for line in str(process.communicate()[0].decode("utf-8")).split("\\n"):
            #     print(line)


def main(_):
    eval()


if __name__ == "__main__":
    tf.app.run()