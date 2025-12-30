#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <cstdlib>

using namespace std;

// Cache for queries to avoid redundant calls
map<vector<int>, int> memo;

// Function to perform a query
int ask(vector<int> s) {
    if (s.empty()) return 0;
    if (s.size() == 1) return 0; 
    sort(s.begin(), s.end());
    if (memo.count(s)) return memo[s];

    cout << "? " << s.size() << "\n";
    for (size_t i = 0; i < s.size(); ++i) {
        cout << s[i] << (i == s.size() - 1 ? "" : " ");
    }
    cout << endl;

    int m;
    cin >> m;
    if (m == -1) exit(0);
    return memo[s] = m;
}

// Calculates edges between set A and set B using inclusion-exclusion principle
// Edges(A U B) = Edges(A) + Edges(B) + Edges_Between(A, B)
// So, Edges_Between(A, B) = Edges(A U B) - Edges(A) - Edges(B)
int get_edges_between(const vector<int>& A, const vector<int>& B) {
    if (A.empty() || B.empty()) return 0;
    vector<int> combined = A;
    combined.insert(combined.end(), B.begin(), B.end());
    return ask(combined) - ask(A) - ask(B);
}

int N;
vector<int> parent;
vector<int> depth;
vector<int> L_curr;
vector<int> U;

// Recursively find subset of candidates that have at least one edge to target_set
vector<int> find_connected(const vector<int>& target_set, vector<int> candidates) {
    if (candidates.empty()) return {};
    
    // Check if any edge exists between target_set and candidates
    int e_cross = get_edges_between(target_set, candidates);
    if (e_cross == 0) return {};

    if (candidates.size() == 1) return candidates;

    int mid = candidates.size() / 2;
    vector<int> left_part(candidates.begin(), candidates.begin() + mid);
    vector<int> right_part(candidates.begin() + mid, candidates.end());

    vector<int> res_left = find_connected(target_set, left_part);
    vector<int> res_right = find_connected(target_set, right_part);
    
    res_left.insert(res_left.end(), res_right.begin(), res_right.end());
    return res_left;
}

// Find a single parent for vertex v in L_curr
int find_parent(int v, const vector<int>& potential_parents) {
    int l = 0, r = potential_parents.size() - 1;
    while (l < r) {
        int mid = l + (r - l) / 2;
        vector<int> left_subset;
        for(int i=l; i<=mid; ++i) left_subset.push_back(potential_parents[i]);
        
        // Check edges between v and left_subset
        vector<int> combined = left_subset;
        combined.push_back(v);
        // Edges between v and left_subset = ask(combined) - ask(left_subset) - ask({v})
        // ask({v}) is 0.
        int e = ask(combined) - ask(left_subset); 
        
        if (e > 0) {
            r = mid;
        } else {
            l = mid + 1;
        }
    }
    return potential_parents[l];
}

void output_bipartite(const vector<int>& p1) {
    cout << "Y " << p1.size() << "\n";
    for (size_t i = 0; i < p1.size(); ++i) {
        cout << p1[i] << (i == p1.size() - 1 ? "" : " ");
    }
    cout << endl;
}

void output_cycle(const vector<int>& cycle) {
    cout << "N " << cycle.size() << "\n";
    for (size_t i = 0; i < cycle.size(); ++i) {
        cout << cycle[i] << (i == cycle.size() - 1 ? "" : " ");
    }
    cout << endl;
}

// Find a single edge (u, v) within a set S where E(S) > 0
// Assumes that if we call on a set, that set has internal edges.
pair<int, int> find_edge_in_set(vector<int> s) {
    if (s.size() == 2) return {s[0], s[1]};

    int mid = s.size() / 2;
    vector<int> s1(s.begin(), s.begin() + mid);
    vector<int> s2(s.begin() + mid, s.end());

    if (ask(s1) > 0) return find_edge_in_set(s1);
    if (ask(s2) > 0) return find_edge_in_set(s2);

    // Edge is crossing s1 and s2
    // We know E(s1)=0, E(s2)=0.
    int u = -1;
    int l = 0, r = s1.size() - 1;
    while (l < r) {
        int m = l + (r - l) / 2;
        vector<int> sub(s1.begin(), s1.begin() + m + 1);
        vector<int> comb = sub;
        comb.insert(comb.end(), s2.begin(), s2.end());
        // Since E(sub)=0 and E(s2)=0, ask(comb) returns edges between sub and s2
        if (ask(comb) > 0) {
            r = m;
        } else {
            l = m + 1;
        }
    }
    u = s1[l];

    l = 0; r = s2.size() - 1;
    while (l < r) {
        int m = l + (r - l) / 2;
        vector<int> sub(s2.begin(), s2.begin() + m + 1);
        vector<int> comb = sub;
        comb.push_back(u);
        // Since E(sub)=0 and E({u})=0, ask(comb) returns edges between sub and u
        if (ask(comb) > 0) {
            r = m;
        } else {
            l = m + 1;
        }
    }
    int v = s2[l];
    return {u, v};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    parent.assign(N + 1, 0);
    depth.assign(N + 1, 0);
    vector<bool> visited(N + 1, false);

    // Start BFS from vertex 1
    L_curr.push_back(1);
    visited[1] = true;
    
    for (int i = 2; i <= N; ++i) U.push_back(i);

    // Construct BFS tree layers
    while (!U.empty()) {
        vector<int> next_layer = find_connected(L_curr, U);
        if (next_layer.empty()) break; 

        for (int v : next_layer) visited[v] = true;
        
        for (int v : next_layer) {
            int p = find_parent(v, L_curr);
            parent[v] = p;
            depth[v] = depth[p] + 1;
        }

        L_curr = next_layer;
        vector<int> new_U;
        new_U.reserve(U.size());
        for (int x : U) if (!visited[x]) new_U.push_back(x);
        U = new_U;
    }

    // Check for bipartiteness
    vector<int> s0, s1;
    for (int i = 1; i <= N; ++i) {
        if (depth[i] % 2 == 0) s0.push_back(i);
        else s1.push_back(i);
    }

    if (ask(s0) == 0 && ask(s1) == 0) {
        output_bipartite(s0);
    } else {
        vector<int> conflict_set = (ask(s0) > 0) ? s0 : s1;
        pair<int, int> edge = find_edge_in_set(conflict_set);
        int u = edge.first;
        int v = edge.second;

        vector<int> path_u, path_v;
        int curr = u;
        while (curr != 0) {
            path_u.push_back(curr);
            curr = parent[curr];
        }
        curr = v;
        while (curr != 0) {
            path_v.push_back(curr);
            curr = parent[curr];
        }

        int lca = -1;
        int idx_u = path_u.size() - 1;
        int idx_v = path_v.size() - 1;
        while (idx_u >= 0 && idx_v >= 0 && path_u[idx_u] == path_v[idx_v]) {
            lca = path_u[idx_u];
            idx_u--;
            idx_v--;
        }

        vector<int> cycle;
        for (int i = 0; i < (int)path_u.size(); ++i) {
            if (path_u[i] == lca) break;
            cycle.push_back(path_u[i]);
        }
        cycle.push_back(lca);
        vector<int> part2;
        for (int i = 0; i < (int)path_v.size(); ++i) {
            if (path_v[i] == lca) break;
            part2.push_back(path_v[i]);
        }
        reverse(part2.begin(), part2.end());
        cycle.insert(cycle.end(), part2.begin(), part2.end());

        output_cycle(cycle);
    }

    return 0;
}