#include <bits/stdc++.h>
using namespace std;

struct Node {
    int i, j;
    int fromDir; // direction used to come here from parent, -1 for root
    int nextDir;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> g(N);
    for (int i = 0; i < N; i++) cin >> g[i];

    auto inside = [&](int i, int j) {
        return 0 <= i && i < N && 0 <= j && j < N;
    };
    auto isRoad = [&](int i, int j) {
        return inside(i, j) && g[i][j] != '#';
    };

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char mv[4] = {'U', 'D', 'L', 'R'};
    const int opp[4] = {1, 0, 3, 2};

    vector<vector<char>> vis(N, vector<char>(N, 0));
    string ans;
    ans.reserve(N * N * 2);

    vector<Node> st;
    st.push_back({si, sj, -1, 0});
    vis[si][sj] = 1;

    while (!st.empty()) {
        Node &cur = st.back();
        if (cur.nextDir < 4) {
            int d = cur.nextDir++;
            int ni = cur.i + di[d], nj = cur.j + dj[d];
            if (isRoad(ni, nj) && !vis[ni][nj]) {
                vis[ni][nj] = 1;
                ans.push_back(mv[d]);
                st.push_back({ni, nj, d, 0});
            }
        } else {
            int fd = cur.fromDir;
            st.pop_back();
            if (fd != -1) ans.push_back(mv[opp[fd]]);
        }
    }

    cout << ans << "\n";
    return 0;
}