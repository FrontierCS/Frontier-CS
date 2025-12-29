#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

int n;
vector<int> color;
vector<int> parent;

int ask(const vector<int>& s) {
    if (s.empty()) {
        return 0;
    }
    cout << "? " << s.size() << endl;
    for (size_t i = 0; i < s.size(); ++i) {
        cout << s[i] << (i == s.size() - 1 ? "" : " ");
    }
    cout << endl;
    int m;
    cin >> m;
    if (m == -1) exit(0);
    return m;
}

int find_neighbor(int v, const vector<int>& p) {
    if (p.empty()) return 0;
    int low = 0, high = p.size() - 1;
    while (low < high) {
        int mid = low + (high - low) / 2;
        vector<int> half;
        for (int i = low; i <= mid; ++i) {
            half.push_back(p[i]);
        }
        vector<int> s_v = half;
        s_v.push_back(v);
        if (ask(s_v) > ask(half)) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return p[low];
}

int find_connected_vertex(const vector<int>& S, const vector<int>& U) {
    int e_S = ask(S);
    int low = 0, high = U.size() - 1;

    while(low < high) {
        int mid = low + (high - low) / 2;
        vector<int> U_half;
        for (int i = low; i <= mid; ++i) {
            U_half.push_back(U[i]);
        }
        vector<int> S_union_U_half = S;
        S_union_U_half.insert(S_union_U_half.end(), U_half.begin(), U_half.end());
        
        if (ask(S_union_U_half) - e_S - ask(U_half) > 0) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return U[low];
}

void report_bipartite(const vector<int>& C0) {
    cout << "Y " << C0.size() << endl;
    for (size_t i = 0; i < C0.size(); ++i) {
        cout << C0[i] << (i == C0.size() - 1 ? "" : " ");
    }
    cout << endl;
}

void report_non_bipartite(int v, int u0, int u1) {
    vector<int> path0;
    int curr = u0;
    while(curr != 0) {
        path0.push_back(curr);
        curr = parent[curr];
    }

    vector<int> path1;
    curr = u1;
    while(curr != 0) {
        path1.push_back(curr);
        curr = parent[curr];
    }
    
    reverse(path0.begin(), path0.end());
    reverse(path1.begin(), path1.end());
    
    size_t lca_depth = 0;
    while(lca_depth < path0.size() && lca_depth < path1.size() && path0[lca_depth] == path1[lca_depth]) {
        lca_depth++;
    }
    lca_depth--;

    vector<int> cycle;
    cycle.push_back(v);
    for(size_t i = path0.size() - 1; i > lca_depth; --i) {
        cycle.push_back(path0[i]);
    }
    cycle.push_back(path0[lca_depth]);
    for(size_t i = lca_depth + 1; i < path1.size(); ++i) {
        cycle.push_back(path1[i]);
    }

    cout << "N " << cycle.size() << endl;
    for (size_t i = 0; i < cycle.size(); ++i) {
        cout << cycle[i] << (i == cycle.size() - 1 ? "" : " ");
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;

    color.assign(n + 1, -1);
    parent.assign(n + 1, 0);

    vector<int> C0, C1;
    vector<int> uncolored;

    C0.push_back(1);
    color[1] = 0;

    for (int i = 2; i <= n; ++i) {
        uncolored.push_back(i);
    }

    while (!uncolored.empty()) {
        vector<int> S = C0;
        S.insert(S.end(), C1.begin(), C1.end());
        
        int v;
        if (uncolored.size() == 1) {
            v = uncolored.front();
        } else {
            v = find_connected_vertex(S, uncolored);
        }

        auto it = find(uncolored.begin(), uncolored.end(), v);
        uncolored.erase(it);

        vector<int> C0_v = C0; C0_v.push_back(v);
        bool has_C0_neighbors = (ask(C0_v) > ask(C0));
        
        vector<int> C1_v = C1; C1_v.push_back(v);
        bool has_C1_neighbors = (ask(C1_v) > ask(C1));

        if (has_C0_neighbors && has_C1_neighbors) {
            int u0 = find_neighbor(v, C0);
            int u1 = find_neighbor(v, C1);
            report_non_bipartite(v, u0, u1);
            return 0;
        }

        if (has_C0_neighbors) {
            color[v] = 1;
            C1.push_back(v);
            parent[v] = find_neighbor(v, C0);
        } else {
            color[v] = 0;
            C0.push_back(v);
            parent[v] = find_neighbor(v, C1);
        }
    }

    report_bipartite(C0);

    return 0;
}