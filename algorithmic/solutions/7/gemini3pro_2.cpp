#include <iostream>
#include <vector>
#include <map>
#include <tuple>
#include <algorithm>

using namespace std;

// Represents a directed edge
struct Edge {
    int weight;
    int to;
};

// Global variables to store graph and memoization
// Node 1 is the Start node.
// Node 2 is the End node (Sink).
int node_count = 2; 
map<tuple<int, long long, long long>, int> memo;
vector<Edge> adj[105]; // Max nodes limit is 100, so 105 is safe.

// Function to get or create a node representing the range [l, r] with bit height k.
// Returns the node index.
int get_node(int k, long long l, long long r) {
    // Base case: height 0 means we have consumed all bits, so we reach the Sink.
    if (k == 0) return 2; 
    
    // Check if such a node already exists
    auto state = make_tuple(k, l, r);
    if (memo.count(state)) return memo[state];
    
    // Create new node
    int id = ++node_count;
    memo[state] = id;
    
    long long mid = 1LL << (k - 1);
    
    // Determine edges. The current range [l, r] is a subset of [0, 2^k - 1].
    // We split this range into lower half [0, mid-1] (edge '0') and upper half [mid, 2^k - 1] (edge '1').
    
    // If [l, r] overlaps with lower half
    if (l < mid) {
        long long next_r = min(r, mid - 1);
        // The values map directly to the next level
        int target = get_node(k - 1, l, next_r);
        adj[id].push_back({0, target});
    }
    
    // If [l, r] overlaps with upper half
    if (r >= mid) {
        long long next_l = max(l, mid) - mid;
        long long next_r = r - mid;
        // The values are reduced by 'mid' for the next level
        int target = get_node(k - 1, next_l, next_r);
        adj[id].push_back({1, target});
    }
    
    return id;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int L_in, R_in;
    if (!(cin >> L_in >> R_in)) return 0;

    // We process each bit length separately to ensure no leading zeros.
    // The range [L, R] is contained in [1, 10^6]. 10^6 < 2^20, so max length is 20.
    for (int len = 1; len <= 20; ++len) {
        long long lower = 1LL << (len - 1);
        long long upper = (1LL << len) - 1;
        
        long long curL = max((long long)L_in, lower);
        long long curR = min((long long)R_in, upper);
        
        if (curL > curR) continue;
        
        // Valid integers in [L, R] with length 'len'.
        // The first bit is always '1'.
        // The remaining len-1 bits form suffixes in the range [curL - lower, curR - lower].
        
        int target = get_node(len - 1, curL - lower, curR - lower);
        // Add edge from Start node (1) with weight 1
        adj[1].push_back({1, target});
    }
    
    // Output the graph in the specified format
    cout << node_count << "\n";
    for (int i = 1; i <= node_count; ++i) {
        cout << adj[i].size();
        for (const auto &e : adj[i]) {
            cout << " " << e.to << " " << e.weight;
        }
        cout << "\n";
    }
    
    return 0;
}