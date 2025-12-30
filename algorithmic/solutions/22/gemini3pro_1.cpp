#include <iostream>
#include <vector>
#include <algorithm>
#include <set>

using namespace std;

// Maximum number of intersections as per problem statement
const int MAXN = 100005;

// Graph representation
vector<int> adj[MAXN];
vector<int> children[MAXN];
int parent_node[MAXN];

// Leftmost and Rightmost leaf in the subtree
int L[MAXN], R[MAXN];

// ID of the root bag of the subtree in the new tree
int saved_id[MAXN];

// Structure for the new tree
struct Bag {
    vector<int> nodes;
};

vector<Bag> bags;
vector<pair<int, int>> new_edges;

// Helper to create a bag and return its 1-based index
int create_bag(const vector<int>& content) {
    Bag b;
    vector<int> sorted_content = content;
    sort(sorted_content.begin(), sorted_content.end());
    sorted_content.erase(unique(sorted_content.begin(), sorted_content.end()), sorted_content.end());
    b.nodes = sorted_content;
    bags.push_back(b);
    return bags.size(); 
}

// Helper to add an edge in the new tree
void add_edge(int u, int v) {
    new_edges.push_back({u, v});
}

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N;
    if (!(cin >> N)) return 0;

    // Reading the tree structure
    // Input format: N-1 lines, i-th line contains p_i connecting to i+1
    for (int i = 1; i < N; ++i) {
        int p;
        cin >> p;
        adj[p].push_back(i + 1);
        adj[i + 1].push_back(p);
    }

    // 1. Sort adjacency lists to respect the counter-clockwise ordering property
    // The problem states that adjacent intersections listed counter-clockwise go in increasing order (starting from parent).
    // Sorting by index achieves the correct relative order of children.
    for (int i = 1; i <= N; ++i) {
        sort(adj[i].begin(), adj[i].end());
    }

    // 2. DFS to establish parent-child relationships and build a topological order
    vector<int> topo;
    vector<int> stk;
    stk.push_back(1);
    parent_node[1] = 0;

    while (!stk.empty()) {
        int u = stk.back();
        stk.pop_back();
        topo.push_back(u);

        // We push children to stack in reverse order so they are processed in increasing order
        // adj[u] is sorted. We iterate backwards.
        for (int i = (int)adj[u].size() - 1; i >= 0; --i) {
            int v = adj[u][i];
            if (v != parent_node[u]) {
                parent_node[v] = u;
                // We want children[u] to be sorted (v1, v2, ...), but we are iterating backwards.
                // So we push_back and then reverse later, or just push_back here (resulting in reverse) and reverse later.
                children[u].push_back(v);
                stk.push_back(v);
            }
        }
    }

    // Correct the order of children arrays to be strictly increasing
    for (int i = 1; i <= N; ++i) {
        reverse(children[i].begin(), children[i].end());
    }

    // 3. Compute L[u] and R[u] (leftmost and rightmost leaves in subtree)
    // Process in reverse topological order (bottom-up)
    for (int i = N - 1; i >= 0; --i) {
        int u = topo[i];
        if (children[u].empty()) {
            L[u] = u;
            R[u] = u;
        } else {
            L[u] = L[children[u].front()];
            R[u] = R[children[u].back()];
        }
    }

    // 4. Construct the new tree (Tree Decomposition)
    // We process nodes bottom-up.
    for (int i = N - 1; i >= 0; --i) {
        int u = topo[i];
        if (children[u].empty()) {
            // Leaf in original tree
            saved_id[u] = create_bag({u});
        } else {
            int prev_root = -1;
            int prev_L = -1, prev_R = -1;

            for (int c : children[u]) {
                int sub_root = saved_id[c];
                // Create an interface bag for child c connecting u to c's subtree
                // This covers edge (u, c) and exposes L(c), R(c)
                int U_c = create_bag({u, c, L[c], R[c]});
                add_edge(U_c, sub_root);

                if (prev_root == -1) {
                    prev_root = U_c;
                    prev_L = L[c];
                    prev_R = R[c];
                } else {
                    int curr_root = U_c;
                    int curr_L = L[c];
                    int curr_R = R[c];

                    // Merge step: connect the previous accumulated structure with the current child
                    // We need to cover the ring edge (prev_R, curr_L)
                    // P connects prev structure and covers the ring edge
                    int P = create_bag({u, prev_L, prev_R, curr_L});
                    // Q connects P to the current child structure and exposes new rightmost leaf
                    int Q = create_bag({u, prev_L, curr_L, curr_R});

                    add_edge(prev_root, P);
                    add_edge(P, Q);
                    add_edge(Q, curr_root);

                    prev_root = Q;
                    prev_R = curr_R;
                }
            }
            // The root of the structure for u is the last created bag (or the only one if single child)
            // It exposes {u, L(u), R(u)}
            saved_id[u] = prev_root;
        }
    }

    // Output results
    cout << bags.size() << "\n";
    for (const auto& bag : bags) {
        cout << bag.nodes.size();
        for (int v : bag.nodes) {
            cout << " " << v;
        }
        cout << "\n";
    }
    for (const auto& edge : new_edges) {
        cout << edge.first << " " << edge.second << "\n";
    }

    return 0;
}