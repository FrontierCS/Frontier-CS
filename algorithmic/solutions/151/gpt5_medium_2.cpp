#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, si, sj;
    if (!(cin >> N >> si >> sj)) return 0;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    auto passable = [&](int i, int j) {
        return i >= 0 && i < N && j >= 0 && j < N && grid[i][j] != '#';
    };

    int total = N * N;
    vector<vector<pair<int,char>>> g(total);
    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (!passable(i, j)) continue;
            int u = i * N + j;
            for (int d = 0; d < 4; ++d) {
                int ni = i + di[d], nj = j + dj[d];
                if (passable(ni, nj)) {
                    int v = ni * N + nj;
                    g[u].push_back({v, dc[d]});
                }
            }
        }
    }

    auto dirBetween = [&](int from, int to) -> char {
        int fi = from / N, fj = from % N;
        int ti = to / N, tj = to % N;
        if (ti == fi - 1 && tj == fj) return 'U';
        if (ti == fi + 1 && tj == fj) return 'D';
        if (ti == fi && tj == fj - 1) return 'L';
        if (ti == fi && tj == fj + 1) return 'R';
        return 'U'; // fallback (shouldn't happen)
    };

    int start = si * N + sj;
    vector<char> visited(total, 0);
    vector<int> iter(total, 0);
    vector<int> st;
    st.push_back(start);
    visited[start] = 1;
    string ans;
    ans.reserve(100000);

    while (!st.empty()) {
        int u = st.back();
        int &k = iter[u];
        auto &adj = g[u];
        while (k < (int)adj.size() && visited[adj[k].first]) ++k;
        if (k < (int)adj.size()) {
            int v = adj[k].first;
            char mv = adj[k].second;
            ans.push_back(mv);
            visited[v] = 1;
            st.push_back(v);
        } else {
            if (st.size() == 1) break;
            int cur = st.back(); st.pop_back();
            int par = st.back();
            char backmv = dirBetween(cur, par);
            ans.push_back(backmv);
        }
    }

    cout << ans << '\n';
    return 0;
}