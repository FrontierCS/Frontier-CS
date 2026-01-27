#include <bits/stdc++.h>
using namespace std;

struct Node { int i, j, d; };

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, si, sj;
    if(!(cin >> N >> si >> sj)) return 0;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    auto inb = [&](int i, int j){ return 0 <= i && i < N && 0 <= j && j < N; };
    auto road = [&](int i, int j){ return grid[i][j] != '#'; };

    vector<vector<char>> vis(N, vector<char>(N, 0));
    string ans;
    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char mv[4] = {'U', 'D', 'L', 'R'};

    vector<Node> st;
    st.push_back({si, sj, 0});
    vis[si][sj] = 1;

    while (!st.empty()) {
        Node &cur = st.back();
        bool progressed = false;
        while (cur.d < 4) {
            int nd = cur.d++;
            int ni = cur.i + di[nd];
            int nj = cur.j + dj[nd];
            if (inb(ni, nj) && road(ni, nj) && !vis[ni][nj]) {
                ans.push_back(mv[nd]);
                st.push_back({ni, nj, 0});
                vis[ni][nj] = 1;
                progressed = true;
                break;
            }
        }
        if (!progressed) {
            Node last = st.back();
            st.pop_back();
            if (!st.empty()) {
                Node parent = st.back();
                int dii = parent.i - last.i;
                int djj = parent.j - last.j;
                if (dii == -1 && djj == 0) ans.push_back('U');
                else if (dii == 1 && djj == 0) ans.push_back('D');
                else if (dii == 0 && djj == -1) ans.push_back('L');
                else if (dii == 0 && djj == 1) ans.push_back('R');
            }
        }
    }

    cout << ans << '\n';
    return 0;
}