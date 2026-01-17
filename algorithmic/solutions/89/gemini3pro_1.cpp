#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>

using namespace std;

int N;
mt19937 rng(1337);

// Perform query: is v on Steiner(S)?
int query_steiner(int v, const vector<int>& S) {
    if (S.empty()) return 0; 
    cout << "? " << S.size() << " " << v;
    for (int x : S) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Check if u is an ancestor of v (rooted at 1)
// Equivalent to: Is u on Steiner({1, v})?
bool is_ancestor(int u, int v) {
    if (u == v) return true;
    if (u == 1) return true;
    if (v == 1) return false; 
    return query_steiner(u, {1, v});
}

// Check if v is an ancestor of ANY node in S.
// Equivalent to checking if v is in Steiner({1} U S).
// Steiner({1} U S) is the union of paths from 1 to each s in S.
// If v is in this union, it lies on a path 1->s, so v is an ancestor of s.
bool is_ancestor_of_any(int v, const vector<int>& S) {
    if (S.empty()) return false;
    vector<int> Q = S;
    Q.push_back(1);
    return query_steiner(v, Q);
}

// Efficiently extract subset of candidates that are descendants of p
void extract_descendants(int p, const vector<int>& candidates, vector<int>& desc) {
    if (candidates.empty()) return;
    // Optimization: check if any candidate is descendant
    if (!is_ancestor_of_any(p, candidates)) return;
    
    if (candidates.size() == 1) {
        desc.push_back(candidates[0]);
        return;
    }

    int mid = candidates.size() / 2;
    vector<int> left(candidates.begin(), candidates.begin() + mid);
    vector<int> right(candidates.begin() + mid, candidates.end());
    extract_descendants(p, left, desc);
    extract_descendants(p, right, desc);
}

vector<pair<int, int>> edges;
vector<bool> global_bool; // Used for efficient set difference

void solve(int root, vector<int>& nodes) {
    if (nodes.empty()) return;

    // Pick random pivot
    int pivot_idx = uniform_int_distribution<int>(0, nodes.size() - 1)(rng);
    int pivot = nodes[pivot_idx];

    // 1. Identify descendants of pivot within nodes
    vector<int> other_candidates;
    other_candidates.reserve(nodes.size());
    for(int x : nodes) if(x != pivot) other_candidates.push_back(x);

    vector<int> descendants;
    extract_descendants(pivot, other_candidates, descendants);

    // 2. Identify remainder: Rem = nodes \ ({pivot} U descendants)
    vector<int> rem;
    rem.reserve(other_candidates.size() - descendants.size());
    for(int x : descendants) global_bool[x] = true;
    for(int x : other_candidates) {
        if (!global_bool[x]) rem.push_back(x);
    }
    for(int x : descendants) global_bool[x] = false;

    // 3. Find path from root to pivot within Rem
    // path contains nodes in Rem that are ancestors of pivot
    vector<int> path;
    for (int u : rem) {
        if (is_ancestor(u, pivot)) {
            path.push_back(u);
        }
    }

    // Sort path by depth (using ancestry relation)
    sort(path.begin(), path.end(), [&](int a, int b) {
        return is_ancestor(a, b);
    });

    // Add edges for the discovered chain
    int curr = root;
    for (int node : path) {
        edges.push_back({curr, node});
        curr = node;
    }
    edges.push_back({curr, pivot});

    // 4. Distribute Rem \ Path into buckets attached to chain nodes
    vector<int> to_distribute;
    to_distribute.reserve(rem.size() - path.size());
    for(int x : path) global_bool[x] = true;
    for(int x : rem) {
        if (!global_bool[x]) to_distribute.push_back(x);
    }
    for(int x : path) global_bool[x] = false;

    // The chain includes root and path nodes. 
    // Nodes in to_distribute attach to one of these.
    vector<int> chain;
    chain.push_back(root);
    chain.insert(chain.end(), path.begin(), path.end());
    
    // Recursive distribution
    auto distribute = [&](auto&& self, int L, int R, const vector<int>& poly) -> void {
        if (poly.empty()) return;
        if (L == R) {
            solve(chain[L], const_cast<vector<int>&>(poly));
            return;
        }
        int mid = (L + R + 1) / 2; 
        
        // Nodes that are descendants of chain[mid] go to right range [mid, R]
        vector<int> right_poly;
        extract_descendants(chain[mid], poly, right_poly);
        
        vector<int> left_poly;
        left_poly.reserve(poly.size() - right_poly.size());
        for(int x : right_poly) global_bool[x] = true;
        for(int x : poly) if(!global_bool[x]) left_poly.push_back(x);
        for(int x : right_poly) global_bool[x] = false;
        
        self(self, L, mid - 1, left_poly);
        self(self, mid, R, right_poly);
    };

    distribute(distribute, 0, chain.size() - 1, to_distribute);

    // 5. Recurse on descendants of pivot
    solve(pivot, descendants);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N)) return 0;
    
    global_bool.resize(N + 1, false);

    vector<int> nodes(N - 1);
    iota(nodes.begin(), nodes.end(), 2);
    
    solve(1, nodes);

    cout << "!" << endl;
    for (auto& p : edges) {
        cout << p.first << " " << p.second << endl;
    }
    cout << flush;

    return 0;
}