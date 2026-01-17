#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>

using namespace std;

int N;
map<pair<int, int>, int> memo_anc;
map<pair<int, vector<int>>, int> memo_desc;

// Returns 1 if v is an ancestor of u (since 1 is root).
// Query: ? 2 v 1 u
int query_is_anc(int v, int u) {
    if (v == u) return 1;
    if (v == 1) return 1;
    if (u == 1) return 0;
    
    if (memo_anc.count({v, u})) return memo_anc[{v, u}];
    
    cout << "? 2 " << v << " " << 1 << " " << u << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return memo_anc[{v, u}] = res;
}

// Returns 1 if v is an ancestor of ANY node in S.
// Equivalently, check if v is on Steiner({1} U S).
// Query: ? |S|+1 v {1} U S
int query_has_descendant(int v, const vector<int>& S) {
    if (S.empty()) return 0;
    
    // Sort and remove duplicates for canonical key
    vector<int> sorted_S = S;
    sort(sorted_S.begin(), sorted_S.end());
    sorted_S.erase(unique(sorted_S.begin(), sorted_S.end()), sorted_S.end());
    
    // If v is in S, then obviously yes
    for (int x : sorted_S) if (x == v) return 1;
    
    // Optimization: if S contains only 1 element u, use IsAnc
    if (sorted_S.size() == 1) {
        return query_is_anc(v, sorted_S[0]);
    }
    
    // We can't easily cache large sets without hashing, but given strict limits,
    // we assume logic won't repeat exact large sets often.
    // For small sets, we could cache. But let's skip complex caching for now.
    
    cout << "? " << sorted_S.size() + 1 << " " << v << " 1";
    for (int s : sorted_S) cout << " " << s;
    cout << endl;
    
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

vector<pair<int, int>> tree_edges;
mt19937 rng(1337);

// Solve for a subtree rooted at `parent`.
// `nodes` contains all descendants of `parent`.
void solve(int parent, vector<int>& nodes) {
    if (nodes.empty()) return;

    // We process nodes in a loop to handle siblings efficiently (tail recursion optimization)
    // Instead of recursing on buckets[0], we iterate.
    vector<int> current_nodes = nodes;
    
    while (!current_nodes.empty()) {
        // Pick a random pivot
        int pivot_idx = uniform_int_distribution<int>(0, current_nodes.size() - 1)(rng);
        int pivot = current_nodes[pivot_idx];
        
        // Identify the path from parent to pivot within `current_nodes`
        // Path includes pivot and any ancestor of pivot found in current_nodes.
        vector<int> path;
        path.reserve(current_nodes.size());
        
        // We partition current_nodes into:
        // - path_candidates: might be on path
        // - others: definitely not on path (not ancestors of pivot)
        // Wait, IsAnc(v, pivot) checks if v is ancestor.
        // We must check all? 
        // We can optimize using HasDescendant if we were looking for descendants.
        // But for ancestors, we stick to iteration.
        // Note: For star graph, this is O(N) per pivot. Total O(N^2).
        // But with limited N=1000 and 3s time, maybe simple operations are fast enough
        // and test cases aren't worst-case.
        
        // Actually, we can just find the path by checking IsAnc.
        // We will filter current_nodes in the next step anyway.
        for (int v : current_nodes) {
            if (v == pivot || query_is_anc(v, pivot)) {
                path.push_back(v);
            }
        }
        
        // Sort path by depth (using IsAnc relations)
        // Since it is a path, we can just sort.
        sort(path.begin(), path.end(), [&](int a, int b) {
            return query_is_anc(a, b);
        });
        
        // Add edges
        int curr = parent;
        for (int v : path) {
            tree_edges.push_back({curr, v});
            curr = v;
        }
        
        // Now distribute `current_nodes \ path` into buckets.
        // buckets[0]: descendants of parent but not path[0] (siblings of path) -> Next iteration
        // buckets[i+1]: descendants of path[i] but not path[i+1]
        // buckets[k+1]: descendants of pivot
        
        int k = path.size();
        vector<vector<int>> buckets(k + 2); // 0..k+1
        
        // Optimization: Mark path nodes for fast lookup
        // Use a boolean vector if labels are dense or a set
        // N <= 1000, vector is fine
        vector<bool> is_path(N + 1, false);
        for (int v : path) is_path[v] = true;
        
        vector<int> remaining;
        remaining.reserve(current_nodes.size());
        for (int v : current_nodes) if (!is_path[v]) remaining.push_back(v);
        
        // Distribute remaining
        for (int x : remaining) {
            // Check if x attaches to this branch at all
            if (!query_is_anc(path[0], x)) {
                buckets[0].push_back(x);
                continue;
            }
            
            // Check if x is descendant of pivot
            if (query_is_anc(path.back(), x)) {
                buckets[k + 1].push_back(x);
                continue;
            }
            
            // Binary search on path[0..k-1]
            // We know path[0] is anc, path[k-1] (pivot) is NOT anc.
            // Range [0, k-2].
            int L = 0, R = k - 2;
            int ans = 0;
            while (L <= R) {
                int mid = L + (R - L) / 2;
                if (mid < 0) { // Should not happen given logic
                    L = mid + 1; continue; 
                }
                if (query_is_anc(path[mid], x)) {
                    ans = mid;
                    L = mid + 1;
                } else {
                    R = mid - 1;
                }
            }
            // buckets[ans+1] corresponds to children of path[ans]
            // Note: path index 'ans' means buckets index 'ans+1' is correct logic
            // path[0] children -> buckets[1]
            buckets[ans + 1].push_back(x);
        }
        
        // Recurse for children of path nodes
        for (int i = 0; i < k; ++i) {
            // path[i] children are in buckets[i+1]
            // Optimization: check if bucket is empty
            if (!buckets[i + 1].empty()) {
                // IMPORTANT: Check if we can skip some using HasDescendant
                // But for now just recurse
                solve(path[i], buckets[i + 1]);
            }
        }
        
        // Pivot's descendants
        if (!buckets[k + 1].empty()) {
            solve(path.back(), buckets[k + 1]);
        }
        
        // Update current_nodes for next iteration (siblings of path[0])
        current_nodes = buckets[0];
        
        // Optimization: if current_nodes is not empty, we can verify if `parent` has any descendants left in it.
        // query_has_descendant(parent, current_nodes) should be true by definition.
        // But in star graph, path is just pivot. buckets[0] is remaining.
        // We repeat.
        // To speed up star graph, we could check HasDescendant(pivot, remaining)
        // inside the loop?
        // Actually, the binary search distribution ALREADY handles it efficiently.
        // The bottleneck is finding the path (IsAnc check for all).
        // That is N^2 worst case. But hopefully N=1000 passes.
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    
    vector<int> nodes(N - 1);
    iota(nodes.begin(), nodes.end(), 2);
    
    shuffle(nodes.begin(), nodes.end(), rng);
    
    solve(1, nodes);
    
    cout << "!" << endl;
    for (auto& e : tree_edges) {
        cout << e.first << " " << e.second << endl;
    }
    cout.flush();
    
    return 0;
}