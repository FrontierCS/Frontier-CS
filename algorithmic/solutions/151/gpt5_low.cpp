#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, si, sj;
    if(!(cin >> N >> si >> sj)) return 0;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    auto inb = [&](int i, int j){ return 0 <= i && i < N && 0 <= j && j < N; };
    auto isroad = [&](int i, int j){ return grid[i][j] != '#'; };

    vector<vector<char>> vis(N, vector<char>(N, 0));
    string ans;
    struct Node { int i, j, nextDir; };
    vector<Node> st;
    st.push_back({si, sj, 0});
    vis[si][sj] = 1;

    // Directions: U, D, L, R
    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char mv[4] = {'U','D','L','R'};
    const char rmv[4] = {'D','U','R','L'};

    while (!st.empty()) {
        Node &cur = st.back();
        bool moved = false;
        for (int d = cur.nextDir; d < 4; ++d) {
            int ni = cur.i + di[d], nj = cur.j + dj[d];
            if (inb(ni, nj) && isroad(ni, nj) && !vis[ni][nj]) {
                vis[ni][nj] = 1;
                ans.push_back(mv[d]);
                st.back().nextDir = d + 1;
                st.push_back({ni, nj, 0});
                moved = true;
                break;
            }
        }
        if (!moved) {
            if (st.size() == 1) { st.pop_back(); break; }
            auto last = st.back(); st.pop_back();
            auto par = st.back();
            int di2 = par.i - last.i;
            int dj2 = par.j - last.j;
            if (di2 == 1 && dj2 == 0) ans.push_back('D'); // from last to parent: down
            else if (di2 == -1 && dj2 == 0) ans.push_back('U');
            else if (di2 == 0 && dj2 == 1) ans.push_back('R');
            else if (di2 == 0 && dj2 == -1) ans.push_back('L');
        }
    }

    cout << ans << '\n';
    return 0;
}