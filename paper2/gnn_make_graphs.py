# %%
from os import listdir, cpu_count
from networkx import Graph, write_graphml
from images.utils import load_image
from graphical_model.utils import graphical_model
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
# %%


def make_graph(nodes, edges, attrs, d=0.005):
    g = Graph()
    edges = (edges > d) * edges
    #  Add nodes
    for index, row in nodes.iterrows():
        g.add_node(index)

    for i in range(edges.shape[0]):
        for j in range(edges.shape[1]):
            if edges[i, j] != 0:
                g.add_edge(i, j, weight=edges[i, j])

    for index, row in attrs.iterrows():
        for col, attr_value in row.items():
            g.nodes[index][col] = attr_value

    for node, data in g.nodes(data=True):
        for key, value in data.items():
            if isinstance(value, list):
                data[key] = ','.join(map(str, value))
    return g


def img_to_graph(image):
    img_size = 50
    img = load_image(
        image,
        [img_size, img_size]
    )

    nodes_ls, edges_ls, attr_ls = graphical_model(
        img=img,
        return_spp=True,
        alpha=0.5,
        set_type="level"
    )

    g1 = make_graph(nodes_ls, edges_ls, attr_ls)
    write_graphml(g1, f"../graphical_models/level_sets/{image.split('/')[-1].split('.')[0]}_graph.graphml")

    nodes_fs, edges_fs, attr_fs = graphical_model(
        img=img,
        return_spp=True,
        alpha=0.5,
        set_type="fuzzy",
        fuzzy_cutoff=10,
    )

    g2 = make_graph(nodes_fs, edges_fs, attr_fs)
    write_graphml(g2, f"../graphical_models/fuzzy_sets_10/{image.split('/')[-1].split('.')[0]}_graph.graphml")

    nodes_fs2, edges_fs2, attr_fs2 = graphical_model(
        img=img,
        return_spp=True,
        alpha=0.5,
        set_type="fuzzy",
        fuzzy_cutoff=30,
    )

    g3 = make_graph(nodes_fs2, edges_fs2, attr_fs2)
    write_graphml(g3, f"../graphical_models/fuzzy_sets_30/{image.split('/')[-1].split('.')[0]}_graph.graphml")


# %%

if __name__ == '__main__':
    images_path = "../dtd/images/"
    images = ["../dtd/images/dotted/" + file for file in listdir("../dtd/images/dotted")]
    images += ["../dtd/images/fibrous/" + file for file in listdir("../dtd/images/fibrous")]
    images = images

    n_cores = cpu_count() - 2
    print(f'Running process on {n_cores} cores')
    # with ProcessPoolExecutor(max_workers=n_cores) as executor:
    #     executor.map(img_to_graph, images)
    with ProcessPoolExecutor() as executor:
        # Setup tqdm
        future_to_image = {executor.submit(img_to_graph, image): image for image in images}
        for future in tqdm(as_completed(future_to_image), total=len(images)):
            try:
                future.result()  # retrieve results if there are any
            except Exception as e:
                print(f"Error processing image: {future_to_image[future]}. Error: {e}")


# %%
