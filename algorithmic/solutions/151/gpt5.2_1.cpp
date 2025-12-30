#include <bits/stdc++.h>
using namespace std;

struct Frame {
    int v;
    int di;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> c(N);
    for (int i = 0; i < N; i++) cin >> c[i];

    vector<vector<int>> id(N, vector<int>(N, -1));
    vector<pair<int,int>> pos;
    pos.reserve(N * N);

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (c[i][j] != '#') {
                id[i][j] = (int)pos.size();
                pos.push_back({i, j});
            }
        }
    }

    int start = id[si][sj];
    int R = (int)pos.size();
    vector<char> route;
    if (R == 0) {
        cout << "\n";
        return 0;
    }

    static const int di4[4] = {-1, 1, 0, 0};
    static const int dj4[4] = {0, 0, -1, 1};
    static const char dc4[4] = {'U', 'D', 'L', 'R'};

    vector<unsigned char> vis(R, 0);
    vector<Frame> st;
    st.reserve(R);

    vis[start] = 1;
    st.push_back({start, 0});

    auto move_char = [&](int from, int to) -> char {
        auto [fi, fj] = pos[from];
        auto [ti, tj] = pos[to];
        if (ti == fi - 1 && tj == fj) return 'U';
        if (ti == fi + 1 && tj == fj) return 'D';
        if (ti == fi && tj == fj - 1) return 'L';
        if (ti == fi && tj == fj + 1) return 'R';
        return '?';
    };

    while (!st.empty()) {
        Frame &fr = st.back();
        int v = fr.v;
        auto [i, j] = pos[v];

        bool advanced = false;
        while (fr.di < 4) {
            int d = fr.di++;
            int ni = i + di4[d], nj = j + dj4[d];
            if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
            int u = id[ni][nj];
            if (u < 0) continue;
            if (vis[u]) continue;
            vis[u] = 1;
            route.push_back(dc4[d]);
            st.push_back({u, 0});
            advanced = true;
            break;
        }

        if (!advanced) {
            st.pop_back();
            if (!st.empty()) {
                int p = st.back().v;
                char back = move_char(v, p);
                route.push_back(back);
            }
        }
    }

    cout << string(route.begin(), route.end()) << "\n";
    return 0;
}