#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, si, sj;
    if (!(cin >> N >> si >> sj)) return 0;
    vector<string> g(N);
    for (int i = 0; i < N; ++i) cin >> g[i];

    vector<vector<int>> vis(N, vector<int>(N, 0));
    vector<vector<int>> dirIdx(N, vector<int>(N, 0));

    const int dx[4] = {-1, 0, 1, 0}; // U, R, D, L
    const int dy[4] = {0, 1, 0, -1};
    const char mv[4] = {'U', 'R', 'D', 'L'};

    stack<pair<int,int>> st;
    st.push({si, sj});
    vis[si][sj] = 1;

    string path;
    path.reserve(100000);

    while (!st.empty()) {
        int x = st.top().first, y = st.top().second;
        int idx = dirIdx[x][y];
        while (idx < 4) {
            int nx = x + dx[idx], ny = y + dy[idx];
            if (nx < 0 || nx >= N || ny < 0 || ny >= N || g[nx][ny] == '#' || vis[nx][ny]) {
                ++idx;
            } else {
                break;
            }
        }
        if (idx < 4) {
            dirIdx[x][y] = idx + 1;
            int nx = x + dx[idx], ny = y + dy[idx];
            path.push_back(mv[idx]);
            st.push({nx, ny});
            vis[nx][ny] = 1;
            dirIdx[nx][ny] = 0;
        } else {
            st.pop();
            if (!st.empty()) {
                int px = st.top().first, py = st.top().second;
                int ddx = px - x, ddy = py - y;
                if (ddx == 1 && ddy == 0) path.push_back('D');
                else if (ddx == -1 && ddy == 0) path.push_back('U');
                else if (ddx == 0 && ddy == 1) path.push_back('R');
                else path.push_back('L');
            }
        }
    }

    cout << path << '\n';
    return 0;
}