#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Structure to represent an edge in the DAG
struct Edge {
    int to;
    int w;
};

// Adjacency list to store the graph. Max nodes 100.
vector<Edge> adj[105];
int node_cnt = 0;
int H[25]; // H[k] stores the node index that is the root of a full binary DAG of height k

// Function to allocate a new node
int new_node() {
    return ++node_cnt;
}

// Function to add a directed edge
void add_edge(int u, int v, int w) {
    adj[u].push_back({v, w});
}

// Lazily retrieve (or create) the node H[k]
// H[k] is the root of a DAG that generates all binary strings of length k.
// H[0] is the Sink node.
int get_H(int k) {
    if (H[k] != 0) return H[k];
    
    // Create new node for H[k]
    int u = new_node();
    H[k] = u;
    // Recursively ensure H[k-1] exists
    int target = get_H(k - 1);
    // Connect H[k] to H[k-1] with both 0 and 1
    add_edge(u, target, 0);
    add_edge(u, target, 1);
    return u;
}

// Construct a path/DAG for values >= val (suffix logic)
// 'u' is the current node
// 'bit' is the current bit index we are deciding (from MSB downwards)
// 'val' is the lower bound value
void add_chain_lower(int u, int bit, int val) {
    if (bit < 0) return;
    int bit_val = (val >> bit) & 1;
    
    if (bit_val == 1) {
        // We are constrained to 1. The '0' path would be less than val (invalid).
        if (bit == 0) {
            add_edge(u, H[0], 1);
        } else {
            int next_node = new_node();
            add_edge(u, next_node, 1);
            add_chain_lower(next_node, bit - 1, val);
        }
    } else {
        // bit_val is 0.
        // We can go '0', continuing the constraint.
        if (bit == 0) {
            add_edge(u, H[0], 0);
        } else {
            int next_tight = new_node();
            add_edge(u, next_tight, 0);
            add_chain_lower(next_tight, bit - 1, val);
        }
        // We can also go '1'. Since 1 > 0, all subsequent bits are free.
        // The remaining length is 'bit'. Target is H[bit].
        add_edge(u, get_H(bit), 1);
    }
}

// Construct a path/DAG for values <= val (suffix logic)
void add_chain_upper(int u, int bit, int val) {
    if (bit < 0) return;
    int bit_val = (val >> bit) & 1;
    
    if (bit_val == 0) {
        // Constrained to 0.
        if (bit == 0) {
            add_edge(u, H[0], 0);
        } else {
            int next_node = new_node();
            add_edge(u, next_node, 0);
            add_chain_upper(next_node, bit - 1, val);
        }
    } else {
        // bit_val is 1.
        // Can go '1' (constrained).
        if (bit == 0) {
            add_edge(u, H[0], 1);
        } else {
            int next_tight = new_node();
            add_edge(u, next_tight, 1);
            add_chain_upper(next_tight, bit - 1, val);
        }
        // Can go '0' (loose). Since 0 < 1, subsequent bits free.
        add_edge(u, get_H(bit), 0);
    }
}

// Construct DAG for range [L, R] with fixed length
void add_chain_between(int u, int bit, int L, int R) {
    if (bit < 0) return;
    int L_bit = (L >> bit) & 1;
    int R_bit = (R >> bit) & 1;

    if (L_bit == R_bit) {
        // Common prefix
        if (bit == 0) {
            add_edge(u, H[0], L_bit);
        } else {
            int next_node = new_node();
            add_edge(u, next_node, L_bit);
            add_chain_between(next_node, bit - 1, L, R);
        }
    } else {
        // Divergence point. L must be 0, R must be 1.
        
        // Lower branch: choose 0. Constraints come from L (lower bound).
        if (bit == 0) {
            add_edge(u, H[0], 0);
        } else {
            int v0 = new_node();
            add_edge(u, v0, 0);
            add_chain_lower(v0, bit - 1, L);
        }

        // Upper branch: choose 1. Constraints come from R (upper bound).
        if (bit == 0) {
            add_edge(u, H[0], 1);
        } else {
            int v1 = new_node();
            add_edge(u, v1, 1);
            add_chain_upper(v1, bit - 1, R);
        }
    }
}

// Calculate number of bits required to represent n
int get_len(int n) {
    if (n == 0) return 0;
    return 32 - __builtin_clz(n);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int L, R;
    if (!(cin >> L >> R)) return 0;

    int Source = new_node(); // Node 1 is Source
    int Sink = new_node();   // Node 2 is Sink
    H[0] = Sink;

    int lenL = get_len(L);
    int lenR = get_len(R);

    // Because we cannot have leading zeros, the MSB for any number in [L, R] is 1.
    // We handle the MSB explicitly by creating an edge '1' from Source.
    // The recursive functions handle bits from len-2 down to 0.

    if (lenL == lenR) {
        // All numbers have the same bit length
        if (lenL == 1) {
            // Range [1, 1]
            add_edge(Source, Sink, 1);
        } else {
            int v = new_node();
            add_edge(Source, v, 1);
            add_chain_between(v, lenL - 2, L, R);
        }
    } else {
        // Numbers have different lengths. We process each length group.
        
        // 1. Numbers of length lenL: Range [L, 2^lenL - 1]
        if (lenL == 1) {
            add_edge(Source, Sink, 1);
        } else {
            int vL = new_node();
            add_edge(Source, vL, 1);
            add_chain_lower(vL, lenL - 2, L);
        }
        
        // 2. Numbers of intermediate lengths: Range [2^(k-1), 2^k - 1] for k in (lenL, lenR)
        // These are full ranges of length k. Corresponds to '1' followed by any k-1 bits.
        for (int k = lenL + 1; k < lenR; ++k) {
            // Edge '1' leads to H[k-1] which generates all strings of length k-1
            add_edge(Source, get_H(k - 1), 1);
        }
        
        // 3. Numbers of length lenR: Range [2^(lenR-1), R]
        if (lenR > 1) {
            int vR = new_node();
            add_edge(Source, vR, 1);
            add_chain_upper(vR, lenR - 2, R);
        }
    }

    // Output graph
    cout << node_cnt << "\n";
    for (int i = 1; i <= node_cnt; ++i) {
        cout << adj[i].size();
        for (auto& e : adj[i]) {
            cout << " " << e.to << " " << e.w;
        }
        cout << "\n";
    }

    return 0;
}