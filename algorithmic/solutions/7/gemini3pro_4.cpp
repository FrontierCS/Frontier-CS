#include <iostream>
#include <vector>
#include <map>
#include <tuple>
#include <algorithm>

using namespace std;

// Structure to represent an outgoing edge
struct Edge {
    int to;
    int weight;
};

// Global variables
// Node 1 is the Source, Node 2 is the Sink.
int N_nodes = 2; 
vector<Edge> adj[105]; // Adjacency list for the graph (max 100 nodes allowed)
// Memoization map to share nodes for identical sub-problems
// Key: (number of bits, min value of suffix, max value of suffix)
map<tuple<int, long long, long long>, int> memo;

// Recursive function to construct the DAG nodes
// k: number of bits to generate
// low, high: the range of integer values that the generated k-bit sequence must fall into
int get_node(int k, long long low, long long high) {
    // If the requested range is invalid, no path exists
    if (low > high) return 0;
    
    // Clamp the range to valid k-bit integer values [0, 2^k - 1]
    long long max_val = (1LL << k) - 1;
    low = max(0LL, low);
    high = min(max_val, high);
    
    if (low > high) return 0;
    
    // Base case: 0 bits remaining. We have successfully formed a valid suffix.
    // Return the unique Sink node (index 2).
    if (k == 0) return 2; 
    
    // Check memoization table
    auto key = make_tuple(k, low, high);
    if (memo.count(key)) return memo[key];
    
    long long M = 1LL << (k - 1);
    
    // Determine the required ranges for the children
    // If we pick edge '0', the remaining (k-1) bits must form a value v such that
    // 0*2^(k-1) + v is in [low, high]. So v in [low, high] intersect [0, M-1].
    long long l0 = low;
    long long h0 = min(high, M - 1);
    
    // If we pick edge '1', the remaining (k-1) bits must form a value v such that
    // 1*2^(k-1) + v is in [low, high]. So v in [low - M, high - M] intersect [0, M-1].
    // Note: low and high are relative to current k-bit frame.
    long long l1 = max(low, M) - M;
    long long h1 = high - M;
    
    // Recursively get child nodes
    int u0 = 0, u1 = 0;
    if (l0 <= h0) u0 = get_node(k - 1, l0, h0);
    if (l1 <= h1) u1 = get_node(k - 1, l1, h1);
    
    // If neither path leads to the sink, this node is not needed
    if (u0 == 0 && u1 == 0) return 0;
    
    // Allocate a new node
    int id = ++N_nodes;
    if (u0 != 0) adj[id].push_back({u0, 0});
    if (u1 != 0) adj[id].push_back({u1, 1});
    
    // Store in memo and return
    return memo[key] = id;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long L, R;
    if (!(cin >> L >> R)) return 0;
    
    // Helper lambda to calculate bit length of a positive integer
    auto get_len = [&](long long x) {
        if (x == 0) return 0;
        return 64 - __builtin_clzll(x);
    };
    
    int lenL = get_len(L);
    int lenR = get_len(R);
    
    // Iterate through each possible bit length in the range [L, R]
    // Since leading zeros are not allowed, we process each length separately.
    // Numbers of different lengths are distinct, so paths will be unique.
    for (int len = lenL; len <= lenR; ++len) {
        // Determine the sub-range of [L, R] that has exactly 'len' bits
        long long start_range = (len == lenL) ? L : (1LL << (len - 1));
        long long end_range = (len == lenR) ? R : (1LL << len) - 1;
        
        if (start_range > end_range) continue;
        
        // For a number with 'len' bits, the MSB must be '1'.
        // We add an edge '1' from Source, and the subsequent path must generate
        // the remaining len-1 bits matching the suffix value.
        long long suffix_start = start_range - (1LL << (len - 1));
        long long suffix_end = end_range - (1LL << (len - 1));
        
        int child = get_node(len - 1, suffix_start, suffix_end);
        if (child != 0) {
            adj[1].push_back({child, 1});
        }
    }
    
    // Output the result
    cout << N_nodes << "\n";
    for (int i = 1; i <= N_nodes; ++i) {
        cout << adj[i].size();
        for (auto& e : adj[i]) {
            cout << " " << e.to << " " << e.weight;
        }
        cout << "\n";
    }
    
    return 0;
}