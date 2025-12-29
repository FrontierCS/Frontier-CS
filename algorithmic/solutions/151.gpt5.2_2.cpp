#include <bits/stdc++.h>
using namespace std;

struct State {
    int i, j, d;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> g(N);
    for (int i = 0; i < N; i++) cin >> g[i];

    auto isRoad = [&](int i, int j) -> bool {
        return 0 <= i && i < N && 0 <= j && j < N && g[i][j] != '#';
    };

    const int di[4] = {-1, 0, 1, 0};
    const int dj[4] = {0, 1, 0, -1};
    const char dc[4] = {'U', 'R', 'D', 'L'};
    auto opp = [&](char c) -> char {
        if (c == 'U') return 'D';
        if (c == 'D') return 'U';
        if (c == 'L') return 'R';
        return 'L'; // 'R'
    };

    vector<vector<unsigned char>> vis(N, vector<unsigned char>(N, 0));
    vector<State> st;
    vector<char> fromMove; // move used to enter this node from parent; root is '?'

    st.push_back({si, sj, 0});
    fromMove.push_back('?');
    vis[si][sj] = 1;

    string ans;
    ans.reserve(N * N * 2);

    while (!st.empty()) {
        State &cur = st.back();
        if (cur.d < 4) {
            int dir = cur.d++;
            int ni = cur.i + di[dir];
            int nj = cur.j + dj[dir];
            if (isRoad(ni, nj) && !vis[ni][nj]) {
                vis[ni][nj] = 1;
                ans.push_back(dc[dir]);
                st.push_back({ni, nj, 0});
                fromMove.push_back(dc[dir]);
            }
        } else {
            char mv = fromMove.back();
            st.pop_back();
            fromMove.pop_back();
            if (!st.empty()) ans.push_back(opp(mv));
        }
    }

    cout << ans << "\n";
    return 0;
}