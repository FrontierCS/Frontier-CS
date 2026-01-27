#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, si, sj;
    if (!(cin >> N >> si >> sj)) return 0;
    vector<string> c(N);
    for (int i = 0; i < N; ++i) cin >> c[i];

    auto inb = [&](int x, int y){ return 0 <= x && x < N && 0 <= y && y < N; };
    vector<vector<char>> road(N, vector<char>(N, 0));
    vector<vector<int>> w(N, vector<int>(N, 0));
    int r = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (c[i][j] != '#') {
                road[i][j] = 1;
                w[i][j] = c[i][j] - '0';
                r++;
            }
        }
    }

    // Directions: 0:U, 1:D, 2:L, 3:R
    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};
    const int rev[4] = {1, 0, 3, 2};

    // Precompute neighbor order for each cell based on neighbor weight (ascending)
    vector<array<int,4>> dirs(N*N);
    vector<int> dircnt(N*N, 0);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (!road[i][j]) continue;
            vector<pair<int,int>> v;
            for (int d = 0; d < 4; ++d) {
                int ni = i + dx[d], nj = j + dy[d];
                if (!inb(ni, nj) || !road[ni][nj]) continue;
                v.emplace_back(w[ni][nj], d);
            }
            sort(v.begin(), v.end(), [](const pair<int,int>& a, const pair<int,int>& b){
                if (a.first != b.first) return a.first < b.first;
                return a.second < b.second;
            });
            int id = i * N + j;
            dircnt[id] = (int)v.size();
            for (int k = 0; k < (int)v.size(); ++k) dirs[id][k] = v[k].second;
        }
    }

    vector<vector<char>> vis(N, vector<char>(N, 0));
    vis[si][sj] = 1;

    struct State {
        int x, y;
        int di;    // next direction index to try
        int dpar;  // direction from parent to here; -1 for root
    };

    vector<State> st;
    st.reserve(r + 5);
    st.push_back({si, sj, 0, -1});

    string ans;
    ans.reserve(max(2*r, 1));

    while (!st.empty()) {
        State &cur = st.back();
        int id = cur.x * N + cur.y;
        bool moved = false;
        while (cur.di < dircnt[id]) {
            int d = dirs[id][cur.di++];
            int nx = cur.x + dx[d], ny = cur.y + dy[d];
            if (!inb(nx, ny) || !road[nx][ny] || vis[nx][ny]) continue;
            ans.push_back(dc[d]);
            vis[nx][ny] = 1;
            st.push_back({nx, ny, 0, d});
            moved = true;
            break;
        }
        if (moved) continue;
        if (cur.dpar == -1) break; // root finished
        ans.push_back(dc[rev[cur.dpar]]);
        st.pop_back();
    }

    cout << ans << '\n';
    return 0;
}