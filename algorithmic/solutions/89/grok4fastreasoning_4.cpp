#include <bits/stdc++.h>
using namespace std;

int n_global;

int ask(int kk, int vv, const vector<int>& SS) {
    cout << "? " << kk << " " << vv;
    for (int s : SS) {
        cout << " " << s;
    }
    cout << endl;
    fflush(stdout);
    int res;
    cin >> res;
    if (res == -1) {
        exit(0);
    }
    return res;
}

vector<pair<int, int>> reconstruct(vector<int> U) {
    int m = U.size();
    if (m == 1) {
        return {};
    }
    if (m == 2) {
        int u = U[0], v = U[1];
        return {{min(u, v), max(u, v)}};
    }
    // Identify local leaves
    vector<int> local_leaves;
    for (int i = 0; i < m; ++i) {
        int v = U[i];
        vector<int> S;
        for (int j = 0; j < m; ++j) {
            if (j != i) S.push_back(U[j]);
        }
        int res = ask(m - 1, v, S);
        if (res == 0) {
            local_leaves.push_back(v);
        }
    }
    if (local_leaves.size() < 2 && m > 2) {
        // Impossible, but continue
        assert(false);
    }
    int aa = local_leaves[0];
    int bb = local_leaves.size() >= 2 ? local_leaves[1] : local_leaves[0];
    // Learn path_set
    vector<int> path_set;
    for (int z : U) {
        vector<int> SS = {aa, bb};
        int res = ask(2, z, SS);
        if (res == 1) {
            path_set.push_back(z);
        }
    }
    if (path_set.size() < 2) {
        assert(false);
    }
    // Order path_set with respect to aa
    vector<int> path_vec = path_set;
    auto comp = [&](int p1, int p2) -> bool {
        vector<int> SS1 = {aa, p2};
        int res1 = ask(2, p1, SS1);
        if (res1 == 1) return true;
        vector<int> SS2 = {aa, p1};
        int res2 = ask(2, p2, SS2);
        if (res2 == 1) return false;
        // Should not reach here
        return false;
    };
    sort(path_vec.begin(), path_vec.end(), comp);
    // Add path edges
    vector<pair<int, int>> edges;
    for (size_t i = 0; i + 1 < path_vec.size(); ++i) {
        int u = path_vec[i], v = path_vec[i + 1];
        edges.emplace_back(min(u, v), max(u, v));
    }
    // Find attachments
    unordered_set<int> on_path_set(path_vec.begin(), path_vec.end());
    vector<vector<int>> branches(path_vec.size());
    for (int vv : U) {
        if (on_path_set.count(vv)) continue;
        // Binary search for largest idx where path_vec[idx] on path vv-aa
        int low = 0, high = (int)path_vec.size() - 1;
        while (low < high) {
            int mid = low + (high - low + 1) / 2;
            int t = path_vec[mid];
            vector<int> SS = {vv, aa};
            int res = ask(2, t, SS);
            if (res == 1) {
                low = mid;
            } else {
                high = mid - 1;
            }
        }
        int k = low;
        branches[k].push_back(vv);
    }
    // Recurse on branches
    for (size_t k = 0; k < path_vec.size(); ++k) {
        if (branches[k].empty()) continue;
        vector<int> sub_U = branches[k];
        sub_U.push_back(path_vec[k]);
        sort(sub_U.begin(), sub_U.end());  // Optional, for consistency
        auto sub_edges = reconstruct(sub_U);
        for (auto e : sub_edges) {
            edges.push_back(e);
        }
    }
    return edges;
}

int main() {
    cin >> n_global;
    if (n_global == 1) {
        cout << "!" << endl;
        fflush(stdout);
        return 0;
    }
    vector<int> U(n_global);
    for (int i = 0; i < n_global; ++i) {
        U[i] = i + 1;
    }
    auto edges = reconstruct(U);
    cout << "!" << endl;
    for (auto [u, v] : edges) {
        cout << u << " " << v << endl;
    }
    fflush(stdout);
    return 0;
}