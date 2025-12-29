#include <bits/stdc++.h>
using namespace std;

struct Node {
    int i, j, k;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, si, sj;
    if (!(cin >> N >> si >> sj)) {
        return 0;
    }
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    vector<vector<char>> road(N, vector<char>(N, 0));
    int r = 0;
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            if (grid[i][j] != '#') {
                road[i][j] = 1;
                ++r;
            }

    vector<vector<char>> vis(N, vector<char>(N, 0));
    vector<Node> st;
    st.reserve(r);
    st.push_back({si, sj, 0});
    vis[si][sj] = 1;

    const int di[4] = {-1, 0, 1, 0};
    const int dj[4] = {0, 1, 0, -1};
    const char mv[4] = {'U', 'R', 'D', 'L'};

    string ans;
    ans.reserve(max(2*r, 1));

    auto moveChar = [](int fi, int fj, int ti, int tj) -> char {
        if (ti == fi - 1 && tj == fj) return 'U';
        if (ti == fi + 1 && tj == fj) return 'D';
        if (ti == fi && tj == fj - 1) return 'L';
        return 'R';
    };

    while (true) {
        Node &cur = st.back();
        if (cur.k == 4) {
            if (st.size() == 1) break;
            int pi = st[st.size() - 2].i;
            int pj = st[st.size() - 2].j;
            ans.push_back(moveChar(cur.i, cur.j, pi, pj));
            st.pop_back();
            continue;
        }
        int d = cur.k;
        cur.k++;
        int ni = cur.i + di[d], nj = cur.j + dj[d];
        if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
        if (!road[ni][nj] || vis[ni][nj]) continue;
        vis[ni][nj] = 1;
        ans.push_back(mv[d]);
        st.push_back({ni, nj, 0});
    }

    cout << ans << '\n';
    return 0;
}