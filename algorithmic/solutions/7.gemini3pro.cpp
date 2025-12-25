#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <tuple>

using namespace std;

// Structure to represent an edge in the graph
struct Edge {
    int to;
    int weight;
};

// Structure to represent a node in the graph
struct Node {
    vector<Edge> out;
};

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int L, R;
    if (!(cin >> L >> R)) return 0;

    vector<Node> nodes;
    
    // Add Sink node at index 0 (will be output as ID 1)
    // The sink node has 0 outgoing edges and represents the end of a valid path
    nodes.push_back(Node{}); 

    // Build H-chain
    // H[i] is a node that accepts all binary strings of length i.
    // H[0] is the Sink node (index 0).
    // H[i] has edges with weight 0 and 1 to H[i-1].
    // Since R <= 10^6 < 2^20, the maximum bit length needed is 20.
    vector<int> H(21);
    H[0] = 0; 
    for (int i = 1; i <= 20; ++i) {
        int idx = nodes.size();
        nodes.push_back(Node{});
        nodes[idx].out.push_back({H[i-1], 0});
        nodes[idx].out.push_back({H[i-1], 1});
        H[i] = idx;
    }

    // Start node creation
    int start_node = nodes.size();
    nodes.push_back(Node{});

    // Helper lambda to calculate bit length of an integer
    auto get_len = [](int x) {
        if (x == 0) return 0;
        int len = 0;
        while ((1LL << len) <= x) len++;
        return len;
    };

    int l_len = get_len(L);
    int r_len = get_len(R);

    // Memoization map to share nodes for identical sub-ranges
    // Key: {lower bound, upper bound, height} -> Value: node index
    map<tuple<int, int, int>, int> memo;

    // Recursive function to build the DAG structure for a specific range of suffixes
    // range: [lower, upper] relative to current subtree
    // height: number of bits remaining
    auto build_range = [&](auto&& self, int lower, int upper, int height) -> int {
        // Optimization: If the requested range covers the full set of strings of this height,
        // return the pre-built H node.
        long long range_size = 1LL << height;
        if (lower == 0 && upper == range_size - 1) {
            return H[height];
        }
        
        // Base case: height 0 (should be handled by H[0] check above, but for safety)
        if (height == 0) return H[0];

        // Check memoization
        auto key = make_tuple(lower, upper, height);
        if (memo.count(key)) return memo[key];

        // Create new node
        int curr = nodes.size();
        nodes.push_back(Node{});
        memo[key] = curr;
        
        long long half = 1LL << (height - 1);
        
        // Process 0-branch (MSB is 0)
        // Intersection of [lower, upper] with [0, half-1]
        int l0 = max((long long)lower, 0LL);
        int u0 = min((long long)upper, half - 1);
        
        if (l0 <= u0) {
            // Recurse with range unchanged (relative to next bit)
            int child0 = self(self, l0, u0, height - 1);
            nodes[curr].out.push_back({child0, 0});
        }
        
        // Process 1-branch (MSB is 1)
        // Intersection of [lower, upper] with [half, 2*half-1]
        // Normalize range by subtracting half
        int l1 = max((long long)lower, half) - half;
        int u1 = min((long long)upper, 2 * half - 1) - half;
        
        if (l1 <= u1) {
            int child1 = self(self, l1, u1, height - 1);
            nodes[curr].out.push_back({child1, 1});
        }
        
        return curr;
    };

    // Iterate over all possible bit lengths in [L, R]
    for (int len = l_len; len <= r_len; ++len) {
        // Calculate the range of numbers with length 'len' that are within [L, R]
        long long min_val = 1LL << (len - 1);
        long long max_val = (1LL << len) - 1;
        
        long long A = max((long long)L, min_val);
        long long B = min((long long)R, max_val);
        
        if (A <= B) {
            // We need to match suffixes of length (len-1)
            // The leading '1' is handled by the edge from Start
            int suffix_height = len - 1;
            // Normalize range to be 0-based relative to the suffixes
            int lower = A - min_val;
            int upper = B - min_val;
            
            // Build/Get the node representing these suffixes
            int target = build_range(build_range, lower, upper, suffix_height);
            
            // Add edge from Start node with weight 1
            nodes[start_node].out.push_back({target, 1});
        }
    }

    // Output the graph
    // Format:
    // N
    // For each node 1..N: K a1 v1 a2 v2 ...
    // Note: Internal 0-based indices are converted to 1-based for output
    cout << nodes.size() << "\n";
    for (int i = 0; i < nodes.size(); ++i) {
        cout << nodes[i].out.size();
        for (auto& edge : nodes[i].out) {
            cout << " " << edge.to + 1 << " " << edge.weight;
        }
        cout << "\n";
    }

    return 0;
}