#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

struct Edge {
    int u, v;
    ll c;
    bool operator<(const Edge& o) const { return c < o.c; }
};

int find(vector<int>& par, int x) {
    return par[x] == x ? x : par[x] = find(par, par[x]);
}

void unions(vector<int>& par, vector<int>& rnk, int a, int b) {
    a = find(par, a);
    b = find(par, b);
    if (a == b) return;
    if (rnk[a] < rnk[b]) swap(a, b);
    par[b] = a;
    if (rnk[a] == rnk[b]) rnk[a]++;
}

ll get_cost(const vector<int>& X, const vector<int>& Y, const vector<char>& Type, int a, int b) {
    ll dx = X[a] - X[b];
    ll dy = Y[a] - Y[b];
    ll D = dx * dx + dy * dy;
    char ta = Type[a], tb = Type[b];
    if (ta == 'C' && tb == 'C') return LLONG_MAX / 2;
    bool both_robots = (ta != 'C' && tb != 'C');
    if (!both_robots) return 5LL * D;
    if (ta == 'R' && tb == 'R') return 5LL * D;
    return 4LL * D;
}

int main() {
    int N, K;
    cin >> N >> K;
    int total = N + K;
    vector<int> ID(total), XX(total), YY(total);
    vector<char> Type(total);
    for (int i = 0; i < total; i++) {
        string typ;
        cin >> ID[i] >> XX[i] >> YY[i] >> typ;
        Type[i] = typ[0];
    }
    vector<int> robots, relays;
    for (int i = 0; i < total; i++) {
        if (Type[i] == 'C') {
            relays.push_back(i);
        } else {
            robots.push_back(i);
        }
    }
    auto X = XX;
    auto Y = YY;

    // Base MST
    vector<Edge> robot_edges;
    for (size_t ii = 0; ii < robots.size(); ++ii) {
        int i = robots[ii];
        for (size_t jj = ii + 1; jj < robots.size(); ++jj) {
            int j = robots[jj];
            ll cc = get_cost(X, Y, Type, i, j);
            robot_edges.push_back({i, j, cc});
        }
    }
    sort(robot_edges.begin(), robot_edges.end());
    vector<int> par(total), rnk(total, 0);
    for (int i = 0; i < total; i++) par[i] = i;
    vector<Edge> base_mst_edges;
    ll B = 0;
    int rcomp = robots.size();
    for (auto& e : robot_edges) {
        int pu = find(par, e.u);
        int pv = find(par, e.v);
        if (pu != pv) {
            unions(par, rnk, e.u, e.v);
            base_mst_edges.push_back(e);
            B += e.c;
            rcomp--;
            if (rcomp == 1) break;
        }
    }
    vector<pair<int, int>> base_link_ids;
    for (auto& e : base_mst_edges) {
        int id1 = ID[e.u], id2 = ID[e.v];
        if (id1 > id2) swap(id1, id2);
        base_link_ids.push_back({id1, id2});
    }
    sort(base_link_ids.begin(), base_link_ids.end());

    // Full MST
    for (int i = 0; i < total; i++) par[i] = i, rnk[i] = 0;
    vector<Edge> alledges;
    for (int i = 0; i < total; i++) {
        for (int j = i + 1; j < total; j++) {
            if (!(Type[i] == 'C' && Type[j] == 'C')) {
                ll cc = get_cost(X, Y, Type, i, j);
                alledges.push_back({i, j, cc});
            }
        }
    }
    sort(alledges.begin(), alledges.end());
    vector<Edge> mst_edges;
    int comp = total;
    for (auto& e : alledges) {
        int pu = find(par, e.u);
        int pv = find(par, e.v);
        if (pu != pv) {
            unions(par, rnk, e.u, e.v);
            mst_edges.push_back(e);
            comp--;
            if (comp == 1) break;
        }
    }
    vector<vector<int>> adj(total);
    for (auto& e : mst_edges) {
        adj[e.u].push_back(e.v);
        adj[e.v].push_back(e.u);
    }
    queue<int> q;
    vector<bool> removed(total, false);
    for (int i : relays) {
        if (adj[i].size() == 1) {
            q.push(i);
        }
    }
    while (!q.empty()) {
        int c = q.front();
        q.pop();
        if (removed[c] || adj[c].size() != 1) continue;
        removed[c] = true;
        int p = adj[c][0];
        auto& lis = adj[p];
        auto it = find(lis.begin(), lis.end(), c);
        if (it != lis.end()) lis.erase(it);
        if (Type[p] == 'C' && !removed[p] && adj[p].size() == 1) {
            q.push(p);
        }
    }
    ll C = 0;
    vector<pair<int, int>> link_ids;
    for (int i = 0; i < total; i++) {
        if (removed[i]) continue;
        for (int j : adj[i]) {
            if (j > i && !removed[j]) {
                ll cc = get_cost(X, Y, Type, i, j);
                C += cc;
                int id1 = ID[i], id2 = ID[j];
                if (id1 > id2) swap(id1, id2);
                link_ids.push_back({id1, id2});
            }
        }
    }
    sort(link_ids.begin(), link_ids.end());

    // Used relays for C
    vector<int> selected;
    for (int i : relays) {
        if (!removed[i] && !adj[i].empty()) {
            selected.push_back(ID[i]);
        }
    }
    sort(selected.begin(), selected.end());

    if (C <= B) {
        // Use C
        if (selected.empty()) {
            cout << "#" << endl;
        } else {
            for (size_t s = 0; s < selected.size(); s++) {
                if (s > 0) cout << "#";
                cout << selected[s];
            }
            cout << endl;
        }
        for (size_t s = 0; s < link_ids.size(); s++) {
            if (s > 0) cout << "#";
            auto [id1, id2] = link_ids[s];
            cout << id1 << "-" << id2;
        }
        cout << endl;
    } else {
        // Use base
        cout << "#" << endl;
        for (size_t s = 0; s < base_link_ids.size(); s++) {
            if (s > 0) cout << "#";
            auto [id1, id2] = base_link_ids[s];
            cout << id1 << "-" << id2;
        }
        cout << endl;
    }
    return 0;
}