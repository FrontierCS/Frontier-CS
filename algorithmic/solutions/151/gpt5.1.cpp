#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, si, sj;
    if (!(cin >> N >> si >> sj)) return 0;
    vector<string> grid(N);
    for (int i = 0; i < N; i++) cin >> grid[i];

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};
    const char revc[4] = {'D', 'U', 'R', 'L'};

    vector<vector<bool>> vis(N, vector<bool>(N, false));

    struct Frame {
        int i, j, dir, from;
    };

    string path;

    if (grid[si][sj] != '#') {
        stack<Frame> st;
        vis[si][sj] = true;
        st.push({si, sj, 0, -1});
        while (!st.empty()) {
            Frame &f = st.top();
            if (f.dir == 4) {
                if (f.from != -1) path.push_back(revc[f.from]);
                st.pop();
                continue;
            }
            int d = f.dir++;
            int ni = f.i + di[d];
            int nj = f.j + dj[d];
            if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
            if (grid[ni][nj] == '#' || vis[ni][nj]) continue;
            vis[ni][nj] = true;
            path.push_back(dc[d]);
            st.push({ni, nj, 0, d});
        }
    }

    cout << path << '\n';
    return 0;
}