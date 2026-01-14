#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

int N;
vector<pair<int, int>> edges;
vector<vector<int>> adj;
vector<int> candidates;

// Helper to print query
int query(int v, const vector<int>& S) {
    if (S.empty()) {
        // According to problem, |S| >= 1. 
        // If S is empty, Steiner(S) is empty? 
        // The problem says s1...sk are distinct. k>=1.
        // We shouldn't make empty queries.
        // However, if we need to check if v is in Steiner({root} U subset), subset can be empty.
        // Then S = {root}.
        return (v == 1); 
    }
    cout << "? " << S.size() << " " << v;
    for (int x : S) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Check if intersection of Path(1, target) and cand is non-empty.
// Equivalent to: Is target in Steiner({1} U cand)?
// Returns list of nodes in cand that are ancestors of target.
vector<int> get_ancestors(int target, const vector<int>& cand) {
    vector<int> res;
    if (cand.empty()) return res;

    // Optimization: check whole block
    vector<int> S = cand;
    S.push_back(1);
    // If target is 1, it's always in. But target is from candidates, so target != 1.
    // Also 1 is in S.
    int q = query(target, S);
    if (q == 0) return res;

    if (cand.size() == 1) {
        return cand;
    }

    // Split
    int mid = cand.size() / 2;
    vector<int> left(cand.begin(), cand.begin() + mid);
    vector<int> right(cand.begin() + mid, cand.end());

    vector<int> r1 = get_ancestors(target, left);
    vector<int> r2 = get_ancestors(target, right);
    res.insert(res.end(), r1.begin(), r1.end());
    res.insert(res.end(), r2.begin(), r2.end());
    return res;
}

// Find the parent of 'node' in the current tree 'adj' (rooted at 1)
// We know 'node' is a new leaf to be attached to the current tree.
// Its parent is the deepest node in 'adj' that is an ancestor of 'node'.
int find_parent(int node) {
    int curr = 1;
    while (true) {
        if (adj[curr].empty()) return curr;
        
        // Binary search among children to find which one is ancestor of node
        // A child c is ancestor of node iff node in Steiner({1} U {descendants of c})?
        // Actually, simpler: node in Steiner({1} U {c}).
        // But we want to batch check children.
        // Check: Is node in Steiner({1} U {c_i, c_{i+1}, ...})?
        // Since node is below exactly one child (or none if curr is parent),
        // checking a set of children tells us if the ancestor is among them.
        
        int L = 0, R = adj[curr].size() - 1;
        int found_child = -1;
        
        // Check if any child is ancestor first?
        // With binary search we don't need a separate check if we handle range carefully.
        // But if curr is the parent, no child will match.
        
        // We can do standard binary search.
        // Range [0, size-1]. Check [0, mid]. If yes, go left. Else check [mid+1, end].
        // If neither, then curr is parent.
        
        // Optimization: Check [0, mid]. If yes, iterate.
        // Actually, if [0, mid] returns YES, the child is in [0, mid].
        // If NO, it might be in [mid+1, end] OR nowhere.
        
        int low = 0, high = adj[curr].size() - 1;
        while (low <= high) {
            if (low == high) {
                // Check single child
                vector<int> S = {1, adj[curr][low]};
                if (query(node, S)) {
                    found_child = adj[curr][low];
                }
                break;
            }
            
            int mid = low + (high - low) / 2;
            vector<int> S;
            S.push_back(1);
            for (int i = low; i <= mid; ++i) S.push_back(adj[curr][i]);
            
            if (query(node, S)) {
                high = mid;
            } else {
                low = mid + 1;
            }
        }
        
        if (found_child != -1) {
            curr = found_child;
        } else {
            return curr;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N)) return 0;
    
    adj.resize(N + 1);
    for (int i = 2; i <= N; ++i) candidates.push_back(i);
    
    // Shuffle candidates to ensure random behavior
    mt19937 rng(1337);
    shuffle(candidates.begin(), candidates.end(), rng);
    
    while (!candidates.empty()) {
        int target = candidates.back();
        // Don't remove yet, wait until we find path
        
        // 1. Identify path nodes from remaining candidates
        vector<int> rem_candidates;
        for (int x : candidates) {
            if (x != target) rem_candidates.push_back(x);
        }
        
        vector<int> path_ancestors = get_ancestors(target, rem_candidates);
        path_ancestors.push_back(target);
        
        // 2. Sort path nodes by depth
        // a is ancestor of b iff a in Steiner({1, b})
        sort(path_ancestors.begin(), path_ancestors.end(), [&](int a, int b) {
            if (a == b) return false;
            // query: ? 2 a 1 b
            // optimization: we can cache results or assume strict ordering?
            // Since they are on a path, one is ancestor of other.
            vector<int> S = {1, b};
            return query(a, S) == 1;
        });
        
        // 3. Attach the chain to the known tree
        // The first node in path_ancestors (shallowest) needs a parent in Known
        int head = path_ancestors[0];
        int p = find_parent(head);
        
        edges.push_back({p, head});
        adj[p].push_back(head);
        
        for (size_t i = 0; i < path_ancestors.size() - 1; ++i) {
            int u = path_ancestors[i];
            int v = path_ancestors[i+1];
            edges.push_back({u, v});
            adj[u].push_back(v);
        }
        
        // 4. Remove processed nodes from candidates
        // Sort path_ancestors for efficient removal or use a set/marker
        vector<int> new_candidates;
        // Mark processed
        vector<bool> is_processed(N + 1, false);
        for (int x : path_ancestors) is_processed[x] = true;
        
        for (int x : candidates) {
            if (!is_processed[x]) new_candidates.push_back(x);
        }
        candidates = new_candidates;
    }
    
    cout << "!" << endl;
    for (auto p : edges) {
        cout << p.first << " " << p.second << endl;
    }
    
    return 0;
}