#include <bits/stdc++.h>
using namespace std;

struct Frame {
    int i, j;
    int nextDir;
    char cameDir; // direction from parent to this node; 0 for root
};

static inline char oppositeDir(char c) {
    if (c == 'U') return 'D';
    if (c == 'D') return 'U';
    if (c == 'L') return 'R';
    if (c == 'R') return 'L';
    return 0;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> g(N);
    for (int i = 0; i < N; i++) cin >> g[i];

    auto inb = [&](int i, int j) { return 0 <= i && i < N && 0 <= j && j < N; };
    auto road = [&](int i, int j) { return inb(i, j) && g[i][j] != '#'; };

    vector<vector<char>> vis(N, vector<char>(N, 0));
    vis[si][sj] = 1;

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};

    string ans;
    ans.reserve(N * N * 2);

    vector<Frame> st;
    st.push_back({si, sj, 0, 0});

    while (!st.empty()) {
        Frame &f = st.back();
        bool advanced = false;

        while (f.nextDir < 4) {
            int k = f.nextDir++;
            int ni = f.i + di[k], nj = f.j + dj[k];
            if (!road(ni, nj) || vis[ni][nj]) continue;

            vis[ni][nj] = 1;
            ans.push_back(dc[k]);
            st.push_back({ni, nj, 0, dc[k]});
            advanced = true;
            break;
        }

        if (advanced) continue;

        if (st.size() == 1) break; // back at root and done

        char back = oppositeDir(f.cameDir);
        st.pop_back();
        ans.push_back(back);
    }

    cout << ans << "\n";
    return 0;
}