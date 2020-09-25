from enum import Enum
import networkx as nx
import numpy as np
import pandas as pd
import scipy.stats as sps
import itertools as itt
from testsuite.hierarchical_hotnet_wrapper import HierarchicalHotNetWrapper
from testsuite.clustex2_wrapper import ClustEx2Wrapper
from testsuite.diamond_wrapper import DIAMOnDWrapper
from testsuite.gxna_wrapper import GXNAWrapper


# todo: add one member for each condition
class ConditionSelector(Enum):
    """Enum specifying for which condition the tests should be run."""
    ALS = 'GSE112680'
    LC = 'GSE30219'
    UC = 'GSE75214'
    HD = 'GSE3790'

    def __str__(self):
        return self.value


class GGINetworkSelector(Enum):
    """Enum specifying on which GGI network the tests should be run."""
    BIOGRID = 'BIOGRID'
    HPRD = 'HPRD'
    STRING = 'STRING'
    APID = 'APID'
    IID = 'IID'

    def __str__(self):
        return self.value


class NetworkGeneratorSelector(Enum):
    """Enum specifying which random generator should be used."""
    ORIGINAL = 'ORIGINAL'
    REWIRED = 'REWIRED'
    SHUFFLED = 'SHUFFLED'
    SCALE_FREE = 'SCALE_FREE'
    UNIFORM = 'UNIFORM'

    def __str__(self):
        return self.value


# todo: add one member for each algorithm
class AlgorithmSelector(Enum):
    """Enum specifying which network enrichment algorithm should be used."""
    DIAMOND = 'DIAMOND'
    GXNA = 'GXNA'
    CLUSTEX2 = 'CLUSTEX2'
    HOTNET = 'HOTNET'

    def __str__(self):
        return self.value


def load_ggi_network(ggi_network_selector, expression_data):
    """Loads the selected GGI network and removes all genes not contained in the expression data.

    Parameters
    ----------
    ggi_network_selector : GGINetworkSelector
        Specifies which GGI network should be loaded.
    expression_data : pd.DataFrame
        Expression data (indices are sample IDs, column names are gene IDs).

    Returns
    -------
    ggi_network : nx.Graph
        The selected GGI network as a networkx graph without genes not contained in the expression data.
    """
    ggi_network = nx.read_graphml(f'../data/networks/{str(ggi_network_selector)}.graphml', node_type=int)
    gene_ids = nx.get_node_attributes(ggi_network, 'GeneID')
    selected_genes = set(expression_data.columns)
    selected_nodes = [node for node in ggi_network.nodes() if gene_ids[node] in selected_genes]
    ggi_network = ggi_network.subgraph(selected_nodes).copy()
    return nx.convert_node_labels_to_integers(ggi_network)


def load_phenotypes(condition_selector):
    """Loads the phenotypes for the selected condition.

    Parameters
    ----------
    condition_selector : ConditionSelector
        Specifies for which condition the phenotypes should be loaded.

    Returns
    -------
    phenotypes : phenotypes : np.array, shape (n_samples,)
        Phenotype data (indices are sample IDs).
    """
    return np.load(f'../data/conditions/{str(condition_selector)}/phenotypes.npy')


def load_expression_data(condition_selector):
    """Loads the expression data for the selected condition.

    Parameters
    ----------
    condition_selector : ConditionSelector
        Specifies for which condition the phenotypes should be loaded.

    Returns
    -------
    expression_data : pd.DataFrame
        Expression data (indices are sample IDs, column names are gene IDs).
    """
    return pd.read_csv(f'../data/conditions/{str(condition_selector)}/expression_data.csv.zip', index_col=0)


def get_pathways(condition_selector):
    """Returns the names of the KEGG pathways associated to the selected condition.

    Parameters
    ----------
    condition_selector : ConditionSelector
        Specifies for which condition the associated pathways should be loaded.

    Returns
    -------
    pathways : list of str
        Names of phenotype-related KEGG pathways.
    """
    if condition_selector == ConditionSelector.ALS:
        return ['hsa05014']
    elif condition_selector == ConditionSelector.LC:
        return ['hsa05223']
    elif condition_selector == ConditionSelector.UC:
        return ['hsa04060', 'hsa04630', 'hsa05321']
    elif condition_selector == ConditionSelector.HD:
        return ['hsa05016']


# todo: add cases for missing wrappers
def get_algorithm_wrapper(algorithm_selector):
    """Returns the appropriate algorithm based on the selection.

    Parameters
    ----------
    algorithm_selector : AlgorithmSelector
        Specifies which algorithm should be used.
    """
    if algorithm_selector == AlgorithmSelector.GXNA:
        return GXNAWrapper()
    elif algorithm_selector == AlgorithmSelector.CLUSTEX2:
        return ClustEx2Wrapper()
    elif algorithm_selector == AlgorithmSelector.DIAMOND:
        return DIAMOnDWrapper()
    elif algorithm_selector == AlgorithmSelector.HOTNET:
        return HierarchicalHotNetWrapper()


# todo: implement this method
def compute_gene_p_values(expression_data, phenotypes):
    """Computes p-values from the expression data and the phenotypes.

    Parameters
    ----------
    expression_data : pd.DataFrame
        Expression data (indices are sample IDs, column names are gene IDs).
    phenotypes : phenotypes : np.array, shape (n_samples,)
        Phenotype data (indices are sample IDs).

    Returns
    -------
    gene_p_values : dict of str: float
            The p-value of two-sided Mann-Whitney U test (keys are gene IDs).
    """
    # todo: replace this dummy implementation
    cases = expression_data.loc[phenotypes == 1, ]
    controls = expression_data.loc[phenotypes == 0, ]
    genes = expression_data.columns
    return {gene: sps.mannwhitneyu(cases[gene], controls[gene], alternative='two_sided')[1] for gene in genes}


# todo: implement this method
def extract_seed_genes(gene_p_values):
    """Extracts the seed genes from previously computed p-values.

    Parameters
    ----------
    gene_p_values : dict of str: float
            The p-value of two-sided Mann-Whitney U test (keys are gene IDs).

    Returns
    -------
    seed_genes : list of str
            List of genes with p-value < 0.001.
    """
    threshold = 0.001
    return [gene for gene, p_value in gene_p_values.items() if p_value < threshold]


def compute_sample_gene_p_values(expression_data):
    """Transforms the expression data to p-values.

        Parameters
        ----------
        expression_data : pd.DataFrame
            Expression data (indices are sample IDs, column names are gene IDs).

        Returns
        -------
        sample_gene_p_values : pd.DataFrame
            Expression data transformed to p-values assuming normality.
        """
    sample_gene_p_values = expression_data.copy()
    sample_gene_p_values = 2.0 * sps.norm.sf(np.fabs(sample_gene_p_values))
    sample_gene_p_values = pd.DataFrame(data=sample_gene_p_values, columns=expression_data.columns)
    return sample_gene_p_values



def compute_seed_statistics(ggi_network, seed_genes):
    """Computes the seed genes' LCC ratio and the mean shortest distance between the seed genes.

    Parameters
    ----------
    ggi_network : nx.Graph
        Original GGI network.
    seed_genes : list of str
        Seed genes (entries are gene IDs).

    Returns
    -------
    lcc_ratio : float
        The ratio of nodes in subgraph induced by seed genes which are contained in largest connected component.
    mean_shortest_distance : float
        The mean shortest distance between the seed genes in the GGI network.
    """
    gene_ids = nx.get_node_attributes(ggi_network, 'GeneID')
    seed_nodes = [node for node in ggi_network.nodes() if gene_ids[node] in set(seed_genes)]
    subgraph = ggi_network.subgraph(seed_nodes)
    lcc_ratio = np.max([len(comp) for comp in nx.connected_components(subgraph)]) / subgraph.number_of_nodes()
    sum_shortest_distances = 0
    num_combinations = 0
    for source, target in itt.combinations(seed_genes, 2):
        sum_shortest_distances += nx.shortest_path_length(ggi_network, source=source, target=target)
        num_combinations += 1
    mean_shortest_distance = sum_shortest_distances / num_combinations
    return lcc_ratio, mean_shortest_distance
