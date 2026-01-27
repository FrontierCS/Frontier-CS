#include <bits/stdc++.h>
using namespace std;

struct Frame {
    int i, j;
    int nextDir;
    int parentDir; // direction from parent to this node; -1 for root
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, si, sj;
    if (!(cin >> N >> si >> sj)) return 0;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    vector<vector<char>> isRoad(N, vector<char>(N, 0));
    int roadCnt = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                isRoad[i][j] = 1;
                roadCnt++;
            }
        }
    }

    vector<vector<char>> visited(N, vector<char>(N, 0));
    static const int di[4] = {-1, 1, 0, 0};
    static const int dj[4] = {0, 0, -1, 1};
    static const char dc[4] = {'U', 'D', 'L', 'R'};
    auto revdir = [](int d) {
        if (d == 0) return 1;
        if (d == 1) return 0;
        if (d == 2) return 3;
        return 2;
    };

    string ans;
    ans.reserve(2 * N * N);

    stack<Frame> st;
    visited[si][sj] = 1;
    st.push({si, sj, 0, -1});

    while (!st.empty()) {
        Frame &cur = st.top();

        bool advanced = false;
        while (cur.nextDir < 4) {
            int d = cur.nextDir++;
            int ni = cur.i + di[d];
            int nj = cur.j + dj[d];
            if (0 <= ni && ni < N && 0 <= nj && nj < N && isRoad[ni][nj] && !visited[ni][nj]) {
                ans.push_back(dc[d]);
                visited[ni][nj] = 1;
                st.push({ni, nj, 0, d});
                advanced = true;
                break;
            }
        }
        if (!advanced) {
            if (cur.parentDir == -1) {
                st.pop();
                break;
            } else {
                int r = revdir(cur.parentDir);
                ans.push_back(dc[r]);
                st.pop();
            }
        }
    }

    cout << ans << '\n';
    return 0;
}