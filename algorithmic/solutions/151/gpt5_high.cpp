#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, si, sj;
    if (!(cin >> N >> si >> sj)) return 0;
    vector<string> grid(N);
    for (int i = 0; i < N; i++) cin >> grid[i];

    vector<vector<char>> road(N, vector<char>(N, 0));
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            road[i][j] = (grid[i][j] != '#');
        }
    }

    vector<vector<char>> visited(N, vector<char>(N, 0));
    auto inb = [&](int i, int j) { return 0 <= i && i < N && 0 <= j && j < N; };

    string ans;
    ans.reserve(N * N * 3);

    struct Node { int i, j, k; };
    vector<Node> st;
    st.push_back({si, sj, 0});

    while (!st.empty()) {
        auto &node = st.back();
        int i = node.i, j = node.j;
        if (!visited[i][j]) visited[i][j] = 1;

        bool moved = false;
        for (int dir = node.k; dir < 4; dir++) {
            int ni = i, nj = j;
            if (dir == 0) ni--;
            else if (dir == 1) ni++;
            else if (dir == 2) nj--;
            else nj++;
            if (inb(ni, nj) && road[ni][nj] && !visited[ni][nj]) {
                node.k = dir + 1;
                st.push_back({ni, nj, 0});
                ans += "UDLR"[dir];
                moved = true;
                break;
            }
        }
        if (!moved) {
            st.pop_back();
            if (!st.empty()) {
                int pi = st.back().i, pj = st.back().j;
                int di = pi - i, dj = pj - j;
                char ch;
                if (di == -1 && dj == 0) ch = 'U';
                else if (di == 1 && dj == 0) ch = 'D';
                else if (di == 0 && dj == -1) ch = 'L';
                else ch = 'R';
                ans += ch;
            }
        }
    }

    cout << ans << "\n";
    return 0;
}