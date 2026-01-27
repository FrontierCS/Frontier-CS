#include <iostream>
#include <vector>
#include <set>
#include <tuple>
#include <algorithm>
#include <map>

using namespace std;

set<tuple<int, int, int>> added_edges;
map<int, pair<int, int>> path_memo;

// get_path_structure(k) returns the first and last intermediate nodes on a path of length k.
// For a path u -> ... -> v with v-u=k, the first intermediate is u + result.first,
// and the last is u + result.second.
pair<int, int> get_path_structure(int k) {
    if (k <= 1) return {-1, -1}; // No intermediate nodes for dist 0 or 1
    if (k == 2) return {1, 1};
    if (k == 3) return {1, 2};
    if (path_memo.count(k)) return path_memo[k];

    int m = k / 2;
    pair<int, int> p1 = get_path_structure(m);
    pair<int, int> p2 = get_path_structure(k - m);

    // The new path from 0 to k is formed by bridging path(0, m) and path(m, k).
    // The first intermediate node of the new path is the first of path(0, m).
    // The last intermediate node is the last of path(m, k), which is shifted by m.
    return path_memo[k] = {p1.first, p2.second + m};
}

void solve(int l, int r) {
    if (r - l <= 3) {
        return;
    }

    int m = l + (r - l) / 2;
    solve(l, m);
    solve(r - (m-l), r); // Use symmetric ranges for structural regularity

    m = l + (r - l) / 2; // Recalculate midpoint for clarity
    
    int du = m - l;
    int dv = r - m;

    int dist_lm = (du <= 3) ? du : 3;
    int dist_mr = (dv <= 3) ? dv : 3;

    if (dist_lm + dist_mr <= 3) {
        return;
    }

    pair<int, int> p_lm_struct = get_path_structure(du);
    pair<int, int> p_mr_struct = get_path_structure(dv);
    
    int a = l + p_lm_struct.first;
    int b = l + p_lm_struct.second;
    int c = m + p_mr_struct.first;
    int d = m + p_mr_struct.second;

    if (dist_lm == 2 && dist_mr == 2) {
        added_edges.insert({b, m, c});
    } else if (dist_lm == 2 && dist_mr == 3) {
        added_edges.insert({b, m, c});
        added_edges.insert({b, c, d});
    } else if (dist_lm == 3 && dist_mr == 2) {
        added_edges.insert({b, m, c});
        added_edges.insert({a, b, c});
    } else if (dist_lm == 3 && dist_mr == 3) {
        added_edges.insert({b, m, c});
        added_edges.insert({a, b, c});
        added_edges.insert({b, c, d});
        added_edges.insert({a, c, d});
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    if (n > 0) {
        solve(0, n);
    }

    cout << added_edges.size() << endl;
    for (const auto& edge : added_edges) {
        cout << get<0>(edge) << " " << get<1>(edge) << " " << get<2>(edge) << "\n";
    }

    return 0;
}