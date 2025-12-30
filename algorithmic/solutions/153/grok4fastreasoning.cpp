#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    const int N = 400;
    const int M = 1995;
    vector<int> X(N), Y(N);
    for(int i = 0; i < N; i++) {
        cin >> X[i] >> Y[i];
    }
    vector<pair<int, int>> edges(M);
    for(int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
    }
    vector<int> D(M);
    for(int i = 0; i < M; i++) {
        int u = edges[i].first, v = edges[i].second;
        int dx = X[u] - X[v];
        int dy = Y[u] - Y[v];
        long long dsq = 1LL * dx * dx + 1LL * dy * dy;
        double dist = sqrt(dsq);
        D[i] = (int) round(dist);
    }
    // compute mst_indices using D
    vector<tuple<int, int>> edgs(M);
    for(int i = 0; i < M; i++) {
        edgs[i] = {D[i], i};
    }
    sort(edgs.begin(), edgs.end());
    vector<int> par_pre(N);
    for(int i = 0; i < N; i++) par_pre[i] = i;
    auto find_pre = [&](auto&& self, int x, vector<int>& par) -> int {
        return par[x] == x ? x : (par[x] = self(self, par[x], par));
    };
    set<int> mst_indices;
    for(auto [d, i] : edgs) {
        int u = edges[i].first, v = edges[i].second;
        int pu = find_pre(find_pre, u, par_pre);
        int pv = find_pre(find_pre, v, par_pre);
        if(pu != pv) {
            par_pre[pu] = pv;
            mst_indices.insert(i);
            if((int)mst_indices.size() == N - 1) break;
        }
    }
    // online
    vector<int> par_on(N);
    for(int i = 0; i < N; i++) par_on[i] = i;
    auto find_on = [&](auto&& self, int x, vector<int>& par) -> int {
        return par[x] == x ? x : (par[x] = self(self, par[x], par));
    };
    for(int i = 0; i < M; i++) {
        int l;
        cin >> l;
        int u = edges[i].first, v = edges[i].second;
        int pu = find_on(find_on, u, par_on);
        int pv = find_on(find_on, v, par_on);
        bool should_add = (pu != pv && mst_indices.count(i));
        if(should_add) {
            cout << 1 << endl;
            par_on[pu] = pv;
        } else {
            cout << 0 << endl;
        }
        cout.flush();
    }
    return 0;
}