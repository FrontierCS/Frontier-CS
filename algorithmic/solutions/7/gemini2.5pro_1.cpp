#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>

using namespace std;

// Adjacency list for the graph. Node indices are 1-based.
vector<pair<int, int>> adj[101];
// Keep track of the total number of nodes used.
int num_nodes = 2; // Start with nodes 1 (start) and 2 (end).

// Calculates the number of bits in the binary representation of n.
int len(long long n) {
    if (n == 0) return 1;
    return floor(log2(n)) + 1;
}

// Converts n to a binary string of a specific length l.
string to_binary(long long n, int l) {
    if (l == 0) return "";
    string bin;
    for (int i = l - 1; i >= 0; i--) {
        bin += ((n >> i) & 1) ? '1' : '0';
    }
    return bin;
}

// Adds a directed edge from u to v with weight w.
void add_edge(int u, int v, int w) {
    adj[u].push_back({v, w});
}

// Returns the node that serves as the entry point for generating k arbitrary bits.
// Node 2 is the end node, which is equivalent to generating 0 bits.
// For k > 0, we use node k+2 as the generator for k bits.
int target_for_gen_node(int k) {
    if (k == 0) return 2; // end_node
    return k + 2;
}

// Generates paths for all numbers >= val with a fixed length l, starting from start_node.
// Assumes the numbers must start with '1' (no leading zeros).
void gen_ge(long long val, int l, int start_node) {
    string s = to_binary(val, l);
    int curr = start_node;
    for (int i = 0; i < l; ++i) {
        // If the current bit in val's binary representation is '0', we can place a '1'
        // to form a larger number. The rest of the bits can be arbitrary.
        // This is not done for the first bit, as it must be '1'.
        if (i > 0 && s[i] == '0') {
            add_edge(curr, target_for_gen_node(l - 1 - i), 1);
        }
        
        // To continue generating numbers >= val, we must follow the path for val itself.
        int next_node = (i == l - 1) ? 2 : ++num_nodes;
        add_edge(curr, next_node, s[i] - '0');
        curr = next_node;
    }
}

// Generates paths for all numbers <= val with a fixed length l, starting from start_node.
// Assumes the numbers must start with '1'.
void gen_le(long long val, int l, int start_node) {
    string s = to_binary(val, l);
    int curr = start_node;
    for (int i = 0; i < l; ++i) {
        // If the current bit in val's representation is '1', we can place a '0'
        // to form a smaller number. The rest of the bits can be arbitrary.
        // Not for the first bit to avoid leading zeros.
        if (i > 0 && s[i] == '1') {
            add_edge(curr, target_for_gen_node(l - 1 - i), 0);
        }
        
        // Follow the path for val itself.
        int next_node = (i == l - 1) ? 2 : ++num_nodes;
        add_edge(curr, next_node, s[i] - '0');
        curr = next_node;
    }
}

// Generates paths for suffixes >= val with length l.
void gen_ge_suf(long long val, int l, int start_node) {
    if (l <= 0) return;
    string s = to_binary(val, l);
    int curr = start_node;
    for (int i = 0; i < l; ++i) {
        if (s[i] == '0') {
            add_edge(curr, target_for_gen_node(l - 1 - i), 1);
        }
        int next_node = (i == l - 1) ? 2 : ++num_nodes;
        add_edge(curr, next_node, s[i] - '0');
        curr = next_node;
    }
}

// Generates paths for suffixes <= val with length l.
void gen_le_suf(long long val, int l, int start_node) {
    if (l <= 0) return;
    string s = to_binary(val, l);
    int curr = start_node;
    for (int i = 0; i < l; ++i) {
        if (s[i] == '1') {
            add_edge(curr, target_for_gen_node(l - 1 - i), 0);
        }
        int next_node = (i == l - 1) ? 2 : ++num_nodes;
        add_edge(curr, next_node, s[i] - '0');
        curr = next_node;
    }
}

// Generates a single path for the number val.
void gen_path(long long val, int l, int start_node) {
    string s = to_binary(val, l);
    int curr = start_node;
    for (int i = 0; i < l; ++i) {
        int next_node = (i == l - 1) ? 2 : ++num_nodes;
        add_edge(curr, next_node, s[i] - '0');
        curr = next_node;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long L, R;
    cin >> L >> R;

    // Pre-build the generator nodes. Node i+2 generates i arbitrary bits.
    for (int i = 1; i <= 20; ++i) {
        num_nodes = max(num_nodes, i + 2);
        add_edge(i + 2, target_for_gen_node(i - 1), 0);
        add_edge(i + 2, target_for_gen_node(i - 1), 1);
    }
    
    // Reset num_nodes to be the first available index for construction.
    num_nodes = 22;

    if (L == R) {
        gen_path(L, len(L), 1);
    } else {
        int lenL = len(L);
        int lenR = len(R);

        if (lenL < lenR) {
            // Numbers with lenL bits: [L, 2^lenL - 1]
            gen_ge(L, lenL, 1);
            
            // Numbers with bits between lenL and lenR: [2^(k-1), 2^k - 1]
            for (int k = lenL + 1; k < lenR; ++k) {
                // All numbers of length k start with '1', followed by k-1 arbitrary bits.
                add_edge(1, target_for_gen_node(k - 1), 1);
            }
            
            // Numbers with lenR bits: [2^(lenR-1), R]
            gen_le(R, lenR, 1);
        } else { // lenL == lenR
            int k = lenL;
            string binL = to_binary(L, k);
            string binR = to_binary(R, k);

            int p = 0; // Find first differing bit
            while (p < k && binL[p] == binR[p]) {
                p++;
            }

            // Build path for the common prefix
            int curr = 1;
            for (int i = 0; i < p; ++i) {
                int next_node = ++num_nodes;
                add_edge(curr, next_node, binL[i] - '0');
                curr = next_node;
            }

            int common_node = curr;
            int len_suf = k - p - 1;

            // L-branch: numbers starting with common_prefix + '0'
            int l_branch_start = ++num_nodes;
            add_edge(common_node, l_branch_start, 0); // binL[p] must be '0'
            long long l_suf_val = L & ((1LL << len_suf) - 1);
            gen_ge_suf(l_suf_val, len_suf, l_branch_start);

            // R-branch: numbers starting with common_prefix + '1'
            int r_branch_start = ++num_nodes;
            add_edge(common_node, r_branch_start, 1); // binR[p] must be '1'
            long long r_suf_val = R & ((1LL << len_suf) - 1);
            gen_le_suf(r_suf_val, len_suf, r_branch_start);
        }
    }

    cout << num_nodes << endl;
    for (int i = 1; i <= num_nodes; ++i) {
        cout << adj[i].size();
        // To ensure consistent output for scoring, sort edges.
        sort(adj[i].begin(), adj[i].end());
        for (auto& edge : adj[i]) {
            cout << " " << edge.first << " " << edge.second;
        }
        cout << endl;
    }

    return 0;
}