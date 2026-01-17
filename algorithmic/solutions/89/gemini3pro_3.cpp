/**
 * Solution for Tree Reconstruction via Steiner-Membership Queries.
 * 
 * Strategy:
 * We use a recursive approach to build the tree.
 * The function solve(root, candidates) attaches the subtree formed by 'candidates' to 'root'.
 * To handle worst-case scenarios like Star Graph efficiently, we process candidates in batches.
 * 
 * In each step of solve(root, candidates):
 * 1. Select a small batch of 'pivots' P from candidates.
 * 2. Filter candidates into 'active' and 'passive'.
 *    - 'active': nodes that lie on the Steiner Tree of {root} U P.
 *    - 'passive': nodes that do not.
 *    This uses O(|candidates|) queries but effectively separates nodes relevant to P from the rest.
 *    In a Star graph, 'active' will be roughly P, and 'passive' the rest.
 *    In a Line graph, 'active' will be the path to the deepest pivot.
 * 3. Use standard Randomized Path Decomposition to reconstruct the tree for 'active' nodes.
 *    Since 'active' is either small (Star) or structured (Line), this is efficient.
 * 4. Recurse with 'passive' nodes (which attach to 'root' but via other branches not covered by P).
 * 
 * Complexity: O(N * sqrt(N)) roughly.
 * For N=1000, this results in ~30,000 queries, well within the scoring limits for near-full points.
 */

#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <map>

using namespace std;

int N;
vector<pair<int, int>> edges;
mt19937 rng(1337);

// Query the judge
// Returns 1 if v is in Steiner(S), 0 otherwise.
int query(int v, const vector<int>& S) {
    if (S.empty()) return 0; // Should not happen based on logic
    cout << "? " << S.size() << " " << v;
    for (int x : S) {
        cout << " " << x;
    }
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Check if u is ancestor of v (assuming root is 1, but used relatively)
// Effectively checks if u is on path between 'root' and v.
bool is_ancestor(int root, int u, int v) {
    // Check(u, {root, v})
    return query(u, {root, v});
}

// Standard Randomized Path Decomposition to build tree for 'nodes' attaching to 'root'
void build_tree_recursive(int root, vector<int>& nodes) {
    if (nodes.empty()) return;

    // 1. Pick a random pivot
    int pivot_idx = uniform_int_distribution<int>(0, nodes.size() - 1)(rng);
    int pivot = nodes[pivot_idx];

    // 2. Identify path from root to pivot
    // Path includes nodes u such that u is ancestor of pivot relative to root
    vector<int> path;
    vector<int> remaining;
    
    // Optimization: check ancestry.
    // Since 'nodes' are known to be in the relevant subtree/set, we scan them.
    for (int u : nodes) {
        if (u == pivot) {
            path.push_back(u);
        } else {
            if (is_ancestor(root, u, pivot)) {
                path.push_back(u);
            } else {
                remaining.push_back(u);
            }
        }
    }

    // 3. Sort path by depth (distance from root)
    // u < v if u is ancestor of v
    sort(path.begin(), path.end(), [&](int a, int b) {
        return is_ancestor(root, a, b);
    });

    // 4. Add edges for the path
    int curr = root;
    for (int u : path) {
        edges.push_back({curr, u});
        curr = u;
    }

    // 5. Distribute remaining nodes to the path edges
    // For each w in remaining, find the deepest node on path that is its ancestor.
    // This is the attachment point.
    // We can binary search on the path: root -> p1 -> p2 ... -> pk
    // Check mid.
    
    // We need to group remaining nodes by attachment point.
    // attachment[i] stores nodes attached to path[i].
    // attachment[-1] stores nodes attached to root (shouldn't happen if filtered correctly, but logic allows).
    
    vector<vector<int>> buckets(path.size() + 1); 
    // buckets[0] for root, buckets[i+1] for path[i]
    
    // To minimize queries, construct the full chain including root
    vector<int> chain;
    chain.push_back(root);
    for(int u : path) chain.push_back(u);
    
    for (int w : remaining) {
        // Binary search for deepest ancestor in chain
        int L = 0, R = chain.size() - 1;
        int ans = 0;
        while (L <= R) {
            int mid = (L + R) / 2;
            if (mid == 0) {
                // Root is always ancestor
                ans = max(ans, mid);
                L = mid + 1;
            } else {
                if (is_ancestor(chain[mid], root, w)) { // Note order: chain[mid] on path root->w? No, query is Check(chain[mid], {root, w})
                    ans = mid;
                    L = mid + 1;
                } else {
                    R = mid - 1;
                }
            }
        }
        // w attaches to chain[ans]
        // But we need to map ans to recursive call.
        // If ans < chain.size()-1, it attaches to chain[ans] but NOT chain[ans+1].
        // This means it branches off at chain[ans].
        // So we recurse on (chain[ans], subset).
        
        // Wait, chain[ans] is the parent in the path sense?
        // Yes, w is in the subtree of chain[ans] (relative to flow away from root)
        // and not in subtree of chain[ans+1].
        
        // However, we added edges root->p1->...->pk.
        // If w attaches to p_i, we call build_tree(p_i, {w...}).
        // But wait, build_tree adds edges from p_i to children.
        // Yes.
        
        // Map chain index to bucket index.
        // chain[0]=root -> index 0?
        // chain[i] -> index i.
        // We will call recursion later.
        if (ans == 0) buckets[0].push_back(w); // Attaches to root
        else buckets[ans].push_back(w); // Attaches to path[ans-1]
    }

    // 6. Recurse
    // bucket[0] -> recurse(root, bucket[0]) -- Wait, root already has edge to path[0].
    // Nodes in bucket[0] are other branches from root.
    build_tree_recursive(root, buckets[0]);
    
    for (int i = 0; i < path.size(); i++) {
        build_tree_recursive(path[i], buckets[i+1]);
    }
}

// Hybrid solver
void solve(int root, vector<int>& candidates) {
    while (!candidates.empty()) {
        int B = sqrt(candidates.size());
        if (B < 2) B = 2; 
        if (B > candidates.size()) B = candidates.size();
        
        // Pick pivots
        vector<int> pivots;
        for (int i = 0; i < B; i++) {
            pivots.push_back(candidates[candidates.size() - 1 - i]);
        }
        
        // Filter active vs passive
        vector<int> S;
        S.push_back(root);
        for (int p : pivots) S.push_back(p);
        
        vector<int> active;
        vector<int> passive;
        
        // Pivots are always active
        for (int p : pivots) active.push_back(p);
        
        // Check others
        for (int i = 0; i < (int)candidates.size() - B; i++) {
            int w = candidates[i];
            if (query(w, S)) {
                active.push_back(w);
            } else {
                passive.push_back(w);
            }
        }
        
        // Build tree for active nodes
        build_tree_recursive(root, active);
        
        // Continue with passive
        candidates = passive;
    }
}

int main() {
    cin >> N;
    if (N == 1) { // Edge case N=1, though constraints say N<=1000, usually N>=2 for tree edges
        cout << "!" << endl;
        return 0;
    }

    vector<int> candidates;
    for (int i = 2; i <= N; i++) candidates.push_back(i);

    // Shuffle candidates to avoid worst-case input order effects
    shuffle(candidates.begin(), candidates.end(), rng);

    solve(1, candidates);

    cout << "!" << endl;
    for (auto& e : edges) {
        cout << e.first << " " << e.second << endl;
    }
    cout << flush;

    return 0;
}