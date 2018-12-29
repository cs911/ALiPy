import copy
import numpy as np
from sklearn.datasets import load_iris
from sklearn.preprocessing import OneHotEncoder
from acepy.query_strategy.query_type import QueryTypeAURO
from acepy.query_strategy.multi_label import LabelRankingModel
from acepy.index.multi_label_tools import get_Xy_in_multilabel
from acepy import ToolBox

X, y = load_iris(return_X_y=True)
mlb = OneHotEncoder()
mult_y = mlb.fit_transform(y.reshape((-1,1)))
mult_y = np.asarray(mult_y.todense())
mult_y[mult_y == 0] = -1

acebox = ToolBox(X=X, y=mult_y, query_type='PartLabels')
acebox.split_AL(test_ratio=0.2, initial_label_rate=0.05, all_class=False)

# query type strategy
AURO_results = []

for round in range(10):

    train_idx, test_idx, label_ind, unlab_ind = acebox.get_split(round)
    # Get intermediate results saver for one fold experiment
    saver = acebox.get_stateio(round)
    query_y = mult_y.copy()
    AURO_strategy = QueryTypeAURO(X=X, y=mult_y)
    # base model
    model = LabelRankingModel()

    for iter in range(100):

        select_ins, select_y1, select_y2 = AURO_strategy.select(label_ind, unlab_ind, query_y)

        # relevance
        y1 = mult_y[select_ins, select_y1]
        y2 = mult_y[select_ins, select_y2]
        if y1 == -1.0 and y2 == -1.0:
            query_y[select_ins, select_y1] = -1
            query_y[select_ins, select_y2] = -1
        elif y1 >= y2:
            query_y[select_ins, select_y1] = 1
            query_y[select_ins, select_y2] = 0.5
        else:
            query_y[select_ins, select_y1] = 0.5
            query_y[select_ins, select_y2] = 1

        # record results
        label_ind.update([(select_ins, select_y1), (select_ins, select_y2)])
        unlab_ind.difference_update([(select_ins, select_y1), (select_ins, select_y2)])

        if iter % 3 == 0:
            # train/test
            X_tr, y_tr, _ = get_Xy_in_multilabel(label_ind, X=X, y=query_y)
            model.fit(X=X_tr, y=y_tr)
            pres, pred = model.predict(X[test_idx])

            perf = acebox.calc_performance_metric(y_true=mult_y[test_idx], y_pred=pred, performance_metric='hamming_loss')

            # save
            st = acebox.State(select_index=[(select_ins, select_y1), (select_ins, select_y2)], performance=perf)
            saver.add_state(st)


    AURO_results.append(copy.copy(saver))

analyser = acebox.get_experiment_analyser()
analyser.add_method(method_name='AURO', method_results=AURO_results)
analyser.plot_learning_curves()
