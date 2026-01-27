#include <bits/stdc++.h>
using namespace std;

pair<int, int> do_query(const vector<int>& qset, int n) {
    size_t cc = qset.size();
    if (cc == 0) return {-1, -1};
    cout << "? " << cc;
    for (int nd : qset) cout << " " << nd;
    cout << endl;
    cout.flush();
    int x, d;
    cin >> x >> d;
    if (x == -1) exit(0);
    return {x, d};
}

int find_one_marked(const vector<int>& cands, int k, const vector<vector<int>>& subt) {
    int l = 0, r = (int)cands.size() - 1;
    while (l < r) {
        int m = (l + r) / 2;
        vector<int> left_c(cands.begin() + l, cands.begin() + m + 1);
        vector<int> left_set;
        for (int idx : left_c) {
            for (int nd : subt[idx]) left_set.push_back(nd);
        }
        auto [xx, dd] = do_query(left_set, 0);
        bool has = (dd == k);
        if (has) {
            r = m;
        } else {
            l = m + 1;
        }
    }
    return cands[l];
}

void collect(int u, int par, vector<int>& list, const vector<vector<int>>& adj, const vector<int>& dist) {
    list.push_back(u);
    for (int v : adj[u]) {
        if (v != par && dist[v] == dist[u] + 1) {
            collect(v, u, list, adj, dist);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        vector<int> all_nodes(n);
        iota(all_nodes.begin(), all_nodes.end(), 1);
        auto [init_x, init_d] = do_query(all_nodes, n);
        int m = init_x;
        int k = init_d;
        vector<int> dist(n + 1, -1);
        queue<int> q;
        q.push(m);
        dist[m] = 0;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (int v : adj[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        vector<int> children;
        for (int v : adj[m]) {
            if (dist[v] == 1) {
                children.push_back(v);
            }
        }
        int D = children.size();
        vector<vector<int>> subt(D);
        for (int i = 0; i < D; i++) {
            vector<int> list;
            collect(children[i], m, list, adj, dist);
            subt[i] = list;
        }
        vector<int> all_cands(D);
        iota(all_cands.begin(), all_cands.end(), 0);
        int i1 = find_one_marked(all_cands, k, subt);
        vector<int> others;
        for (int j = 0; j < D; j++) {
            if (j != i1) others.push_back(j);
        }
        vector<int> others_set;
        for (int idx : others) {
            for (int nd : subt[idx]) others_set.push_back(nd);
        }
        auto [xx_oth, dd_oth] = do_query(others_set, n);
        bool has_sec = (dd_oth == k);
        int i2 = -1;
        if (has_sec) {
            i2 = find_one_marked(others, k, subt);
        }
        vector<int> arms;
        arms.push_back(i1);
        if (i2 != -1) arms.push_back(i2);
        vector<int> hidden;
        if (arms.size() == 1) {
            hidden.push_back(m);
        }
        for (int idx : arms) {
            const auto& sub = subt[idx];
            int maxr_ = 0;
            for (int nd : sub) maxr_ = max(maxr_, dist[nd]);
            int lo = 1, hi = maxr_;
            int max_found = 0;
            while (lo <= hi) {
                int md = (lo + hi) / 2;
                vector<int> Smd;
                for (int nd : sub) {
                    if (dist[nd] == md) Smd.push_back(nd);
                }
                bool yes = false;
                if (!Smd.empty()) {
                    auto [xx, dd] = do_query(Smd, n);
                    yes = (dd == k);
                }
                if (yes) {
                    max_found = md;
                    lo = md + 1;
                } else {
                    hi = md - 1;
                }
            }
            int a = max_found;
            vector<int> Sa;
            for (int nd : sub) {
                if (dist[nd] == a) Sa.push_back(nd);
            }
            auto [ee, dd2] = do_query(Sa, n);
            hidden.push_back(ee);
        }
        int s1 = hidden[0];
        int s2 = hidden[1];
        cout << "! " << s1 << " " << s2 << endl;
        cout.flush();
        string verdict;
        cin >> verdict;
        if (verdict == "Incorrect") {
            exit(0);
        }
    }
    return 0;
}