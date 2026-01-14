#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <tuple>

using namespace std;

struct Edge {
    int to;
    int weight;
};

int N_nodes = 0;
vector<vector<Edge>> adj;
int start_node;
int sink_node;
int full_nodes[25]; 

// (height, min_val, max_val) -> node_index
map<tuple<int, int, int>, int> memo;

int create_node() {
    N_nodes++;
    adj.resize(N_nodes + 1);
    return N_nodes;
}

// Construct a node representing the range [a, b] for height k
// The values represented are strings of length k corresponding to integers in [a, b]
int get_node(int k, int a, int b) {
    if (a > b) return 0;
    
    // Base case: height 0. Range must be [0, 0] to be valid path end.
    if (k == 0) {
        if (a == 0 && b == 0) return sink_node;
        return 0; 
    }
    
    // Check for full range
    long long range_size = 1LL << k;
    if (a == 0 && b == range_size - 1) {
        return full_nodes[k];
    }
    
    // Check memo
    tuple<int, int, int> state = {k, a, b};
    if (memo.count(state)) return memo[state];
    
    int u = create_node();
    long long mid = 1LL << (k - 1);
    
    // Left child: intersection of [a, b] and [0, mid-1]
    long long l_min = max((long long)a, 0LL);
    long long l_max = min((long long)b, mid - 1);
    
    if (l_min <= l_max) {
        int left_child = get_node(k - 1, (int)l_min, (int)l_max);
        if (left_child != 0) {
            adj[u].push_back({left_child, 0});
        }
    }
    
    // Right child: intersection of [a, b] and [mid, 2^k-1], shifted by -mid
    long long r_min = max((long long)a, mid) - mid;
    long long r_max = min((long long)b, range_size - 1) - mid;
    
    if (r_min <= r_max) {
        int right_child = get_node(k - 1, (int)r_min, (int)r_max);
        if (right_child != 0) {
            adj[u].push_back({right_child, 1});
        }
    }
    
    return memo[state] = u;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int L, R;
    if (!(cin >> L >> R)) return 0;

    // Initialize
    N_nodes = 0;
    adj.clear();
    memo.clear();
    
    // Create Start and Sink first
    start_node = create_node(); // ID 1
    sink_node = create_node();  // ID 2
    
    // Create pre-computed full binary tree nodes
    // full_nodes[0] is sink_node
    full_nodes[0] = sink_node;
    for (int k = 1; k <= 20; ++k) {
        int u = create_node();
        full_nodes[k] = u;
        adj[u].push_back({full_nodes[k-1], 0});
        adj[u].push_back({full_nodes[k-1], 1});
    }

    // Iterate over possible bit lengths
    // The range [L, R] might span across multiple bit lengths
    for (int len = 1; len <= 20; ++len) {
        long long range_start = 1LL << (len - 1);
        long long range_end = (1LL << len) - 1;
        
        long long cur_L = max((long long)L, range_start);
        long long cur_R = min((long long)R, range_end);
        
        if (cur_L <= cur_R) {
            // We need to represent the suffix part of the numbers.
            // The MSB is always 1 (handled by edge from Start).
            // We need to match suffixes in range [cur_L - range_start, cur_R - range_start]
            // with bit length len - 1.
            int target = get_node(len - 1, (int)(cur_L - range_start), (int)(cur_R - range_start));
            if (target != 0) {
                adj[start_node].push_back({target, 1});
            }
        }
    }

    // BFS to find reachable nodes and renumber them to be compact (1..N)
    vector<int> new_id(N_nodes + 1, 0);
    vector<bool> visited(N_nodes + 1, false);
    vector<int> q;
    
    q.push_back(start_node);
    visited[start_node] = true;
    
    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        for(auto& edge : adj[u]){
            if(!visited[edge.to]){
                visited[edge.to] = true;
                q.push_back(edge.to);
            }
        }
    }
    
    int current_id = 0;
    // Force start_node to be 1
    if (visited[start_node]) new_id[start_node] = ++current_id;
    
    // Renumber other reachable nodes
    for (int i = 1; i <= N_nodes; ++i) {
        if (i == start_node) continue;
        if (visited[i]) {
            new_id[i] = ++current_id;
        }
    }
    
    int final_n = current_id;
    cout << final_n << "\n";
    
    // Build inverse mapping for output
    vector<int> inv_map(final_n + 1);
    for(int i = 1; i <= N_nodes; ++i){
        if(visited[i]) inv_map[new_id[i]] = i;
    }
    
    // Output edges for each node 1..final_n
    for (int i = 1; i <= final_n; ++i) {
        int u = inv_map[i];
        cout << adj[u].size();
        for (auto& edge : adj[u]) {
            cout << " " << new_id[edge.to] << " " << edge.weight;
        }
        cout << "\n";
    }

    return 0;
}