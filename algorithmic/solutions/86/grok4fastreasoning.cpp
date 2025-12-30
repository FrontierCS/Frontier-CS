#include <bits/stdc++.h>
using namespace std;

vector<pair<int, int>> edges;
map<int, int> node_index; // not used

struct Comparator {
    int root;
    mutable map<pair<int, int>, int> memo;
    Comparator(int r) : root(r) {}
    bool operator()(int u, int v) const {
        if (u == v) return false;
        int uu = min(u, v);
        int vv = max(u, v);
        pair<int, int> key = {uu, vv};
        if (memo.count(key)) {
            int l = memo[key];
            return (l == u);
        }
        cout << 0 << " " << root << " " << u << " " << v << endl;
        fflush(stdout);
        int l;
        cin >> l;
        memo[key] = l;
        return (l == u);
    }
};

void build(const vector<int>& comp, int root) {
    int sz = comp.size();
    if (sz <= 1) return;
    int t = comp[1]; // arbitrary choice
    map<int, int> l_map;
    set<int> dist_l;
    for (int x : comp) {
        if (x == root || x == t) continue;
        cout << 0 << " " << root << " " << t << " " << x << endl;
        fflush(stdout);
        int v;
        cin >> v;
        l_map[x] = v;
        dist_l.insert(v);
    }
    vector<int> P;
    P.push_back(root);
    P.push_back(t);
    for (int v : dist_l) {
        P.push_back(v);
    }
    sort(P.begin(), P.end());
    P.erase(unique(P.begin(), P.end()), P.end());
    // sort P by ancestry
    Comparator comp_func(root);
    sort(P.begin(), P.end(), comp_func);
    // add edges on path
    for (size_t i = 0; i + 1 < P.size(); ++i) {
        edges.emplace_back(P[i], P[i + 1]);
    }
    // groups
    vector<vector<int>> groups(P.size());
    for (const auto& pr : l_map) {
        int x = pr.first;
        int lv = pr.second;
        auto it = find(P.begin(), P.end(), lv);
        int k = it - P.begin();
        groups[k].push_back(x);
    }
    for (size_t k = 0; k < P.size(); ++k) {
        groups[k].push_back(P[k]);
        if (groups[k].size() > 1) {
            build(groups[k], P[k]);
        }
    }
}

int main() {
    int n;
    cin >> n;
    vector<int> comp(n);
    for (int i = 0; i < n; ++i) {
        comp[i] = i + 1;
    }
    build(comp, 1);
    // output
    cout << 1;
    for (auto e : edges) {
        cout << " " << e.first << " " << e.second;
    }
    cout << endl;
    fflush(stdout);
    return 0;
}