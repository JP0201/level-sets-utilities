# %%
from level_sets.distance_calculator import calculate_min_distance_index
from scipy.spatial import distance_matrix
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import KFold
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from subgraph.counter import count_unique_subgraphs, _reference_subgraphs
from tqdm import tqdm
import networkx as nx
import numpy as np
import pandas as pd
import warnings
import xgboost as xgb
from level_sets.metrics import width_to_height, get_angle
warnings.simplefilter(action='ignore', category=Warning)
# %%
def image_to_histogram(descriptors, kmeans):
    hist = np.zeros(num_clusters)
    labels = kmeans.predict(descriptors)
    for label in labels:
        hist[label] += 1
    return hist


def process_sublist(sublist_descriptors, sublist_add_features, kmeans):
    # Convert each descriptor to histogram
    histograms = [image_to_histogram(desc, kmeans) for desc in sublist_descriptors]
    
    # Concatenate histograms with the additional features
    full = [np.concatenate((hist, add_feat)) for hist, add_feat in zip(histograms, sublist_add_features)]
    
    return full

def get_wyh_and_angle(data):
    pixels = [a for a in eval(data.get("pixel_indices"))] if ")," in data.get("pixel_indices") else [eval(data.get("pixel_indices"))]
    img_size = max(max(a[0] for a in pixels), max(a[1] for a in pixels))
    img = np.zeros((img_size+1, img_size+1))
    rows, cols = zip(*pixels)
    img[rows, cols] = 1
    w_t_h = width_to_height(img)
    angl = get_angle(img)
    return w_t_h, angl
# %%
# Start modelling
folders = ["dotted", "fibrous"]#os.listdir("../graphical_models_full/fuzzy_sets_10")[:10] #os.listdir("../graphical_models_full/fuzzy_sets_10")
graph_files = [f"../graphical_models_full/fuzzy_sets_10/{folder}/{dir}" for folder in folders for dir in os.listdir(f"../graphical_models_full/fuzzy_sets_10/{folder}")]

features_names = ['compactness', 'elongation', 'width_to_height', 'angle', 'intensity']
node_counts = pd.DataFrame(np.zeros((len(graph_files),len(features_names))), columns=features_names)

# Read graphs
feats = [[] for _ in folders]
connected_subgraphs = [[] for _ in folders]

for i, file in enumerate(tqdm(graph_files)):
    graph = nx.read_graphml(file)
    clas = file.split("/")[-1].split("_")[0]
    temp_df = pd.DataFrame(np.zeros((len(graph.nodes()),len(features_names))), columns=features_names)
    for node, data in graph.nodes(data=True):
        temp_df.loc[int(node), 'compactness'] = data['compactness']
        temp_df.loc[int(node), 'elongation'] = data['elongation']
        if 'width_to_height' in data.keys():
            temp_df.loc[int(node), 'width_to_height'] = data['width_to_height']
            temp_df.loc[int(node), 'angle'] = data['angle']
        else:
            wth, angl = get_wyh_and_angle(data)
            temp_df.loc[int(node), 'width_to_height'] = wth
            temp_df.loc[int(node), 'angle'] = angl
        temp_df.loc[int(node), 'intensity'] = data['intensity']
    subgraph_counts = count_unique_subgraphs(graph,4)
    sorted_sg = dict(sorted(subgraph_counts.items()))

    # Extract the values in the desired order
    values = []
    for key in sorted_sg.keys():
        sub_dict = sorted_sg[key]
        for sub_key in sorted(sub_dict):
            values.append(sub_dict[sub_key])

    # Convert the list of values to a numpy array with shape (9, 1)
    graphlets = np.array(values).reshape(-1, )
    loc = folders.index(clas)
    feats[loc] += [np.array(temp_df)]
    connected_subgraphs[loc] += [graphlets]


# %%
flattened_feats = [arr for sublist in feats for arr in sublist]
all_descriptors = np.vstack(flattened_feats)

num_clusters = 240  # (best value seems to be 240)

# Step 1: Create a visual vocabulary
kmeans = KMeans(n_clusters=num_clusters, random_state=0).fit(all_descriptors)

# Step 2: Represent each image as a histogram of visual words
lists_of_full = [
    process_sublist(
        sublist_descriptors,
        sublist_add_features,
        kmeans
    ) for sublist_descriptors, sublist_add_features in zip(
        feats,
        connected_subgraphs
    )
]

X = []
y = []

for class_index, sublist in enumerate(lists_of_full):
    X.extend(sublist)
    y.extend([class_index] * len(sublist))

# Step 3: Train classifiers

classifiers = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42),
    "XGBoost": xgb.XGBClassifier(objective="binary:logistic", random_state=42),
    "SVM": SVC(),
    "KNN": KNeighborsClassifier()
}
accs = {
    "Logistic Regression": [],
    "Random Forest": [],
    "XGBoost": [],
    "SVM": [],
    "KNN": []
}
kf = KFold(n_splits=5, shuffle=True, random_state=42)
for train_index, test_index in kf.split(X):
    X_train, X_test = [X[i] for i in train_index], [X[i] for i in test_index]
    y_train, y_test = [y[i] for i in train_index], [y[i] for i in test_index]
    for name, clf in classifiers.items():
        clf.fit(X_train, y_train)
        # print("Test accuracy:", clf.score(X_test, y_test))
        accs[name].append(clf.score(X_test, y_test))

# %%

LR = LogisticRegression(max_iter=1000, fit_intercept=False)
LR.fit(X_train, y_train)
print(LR.score(X_test, y_test))

# %%
import statsmodels.api as sm

# Adding a constant to the X_train to account for the intercept
X_train_const = sm.add_constant(X_train)
X_train_const = pd.DataFrame(X_train_const)
model = sm.Logit(y_train, X_train_const)
result = model.fit()

print(result.summary())

# %%
