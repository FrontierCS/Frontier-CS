#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Node for BIT: stores length and index of the LIS element
struct Node {
    int len;
    int idx;
    
    // Comparison operator for max: primarily length, then index
    bool operator<(const Node& other) const {
        if (len != other.len) return len < other.len;
        return idx < other.idx;
    }
};

// Parent pointers for reconstruction
struct Parent {
    int idx;
    int layer;
};

// Global storage for parent pointers
Parent p_arr[200005][11];

// Flattened BIT storage
// bit_tree[layer * (m_size + 1) + index]
vector<Node> bit_tree; 
int m_size;

// Helper variables for optimization
long long max_val_layer[11];
Node layer_global_max[11];

// Update BIT for a specific layer
void update(int layer, int index, Node val) {
    int offset = layer * (m_size + 1);
    for (; index <= m_size; index += index & -index) {
        if (bit_tree[offset + index] < val) {
            bit_tree[offset + index] = val;
        }
    }
}

// Query BIT for a specific layer
Node query(int layer, int index) {
    int offset = layer * (m_size + 1);
    Node res = {0, -1};
    for (; index > 0; index -= index & -index) {
        if (res < bit_tree[offset + index]) {
            res = bit_tree[offset + index];
        }
    }
    return res;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    long long x;
    if (!(cin >> n >> x)) return 0;

    vector<long long> t(n);
    long long max_t = 0;
    for (int i = 0; i < n; ++i) {
        cin >> t[i];
        if (t[i] > max_t) max_t = t[i];
    }

    // Initialize optimization helpers
    for(int k=0; k<=10; ++k) {
        max_val_layer[k] = max_t + k * x;
        layer_global_max[k] = {0, -1};
    }

    // Coordinate Compression
    vector<long long> vals;
    vals.reserve(n * 11);
    for (int i = 0; i < n; ++i) {
        long long base = t[i];
        for (int k = 0; k <= 10; ++k) {
            vals.push_back(base + k * x);
        }
    }
    sort(vals.begin(), vals.end());
    vals.erase(unique(vals.begin(), vals.end()), vals.end());

    m_size = vals.size();
    
    // Allocate BITs
    bit_tree.resize(11 * (m_size + 1), {0, -1});

    auto get_rank = [&](long long val) {
        return lower_bound(vals.begin(), vals.end(), val) - vals.begin() + 1;
    };

    Node global_best = {0, -1};
    int best_end_layer = -1;

    for (int i = 0; i < n; ++i) {
        for (int k = 0; k <= 10; ++k) {
            long long current_val = t[i] + k * x;
            int r = get_rank(current_val);
            
            Node current_best = {0, -1};
            int best_src_layer = -1;

            // Find best predecessor from layers 0 to k
            for (int p = 0; p <= k; ++p) {
                Node res;
                // Optimization: if current value is greater than any possible value in layer p,
                // we can just take the global max of layer p.
                // This avoids BIT query.
                if (current_val > max_val_layer[p]) {
                    res = layer_global_max[p];
                } else {
                    res = query(p, r - 1);
                }

                if (current_best < res) {
                    current_best = res;
                    best_src_layer = p;
                }
            }

            // Store parent info
            if (current_best.len == 0) {
                p_arr[i][k] = {-1, -1};
            } else {
                p_arr[i][k] = {current_best.idx, best_src_layer};
            }

            int new_len = current_best.len + 1;
            Node new_node = {new_len, i};

            // Update global best
            if (new_len > global_best.len) {
                global_best = new_node;
                best_end_layer = k;
            }
            
            // Update layer global max
            if (layer_global_max[k] < new_node) {
                layer_global_max[k] = new_node;
            }

            // Update BIT
            update(k, r, new_node);
        }
    }

    cout << global_best.len << "\n";

    // Reconstruct the path
    vector<pair<int, int>> lis_path;
    int curr_idx = global_best.idx;
    int curr_layer = best_end_layer;

    while (curr_idx != -1) {
        lis_path.push_back({curr_idx, curr_layer});
        Parent p = p_arr[curr_idx][curr_layer];
        curr_idx = p.idx;
        curr_layer = p.layer;
    }
    reverse(lis_path.begin(), lis_path.end());

    // Generate operations
    vector<pair<int, int>> ops;
    int current_layer_count = 0;
    
    for (auto p : lis_path) {
        int idx = p.first + 1; // 1-based index
        int layer = p.second;
        
        while (current_layer_count < layer) {
            ops.push_back({idx, (int)x});
            current_layer_count++;
        }
    }
    
    // Fill remaining operations if needed
    int used_ops = ops.size();
    for (int k = used_ops; k < 10; ++k) {
        ops.push_back({1, 0});
    }

    for (int k = 0; k < 10; ++k) {
        cout << ops[k].first << " " << n << " " << ops[k].second << "\n";
    }

    return 0;
}