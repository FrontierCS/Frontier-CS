#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, si, sj;
    if (!(cin >> N >> si >> sj)) return 0;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    auto isRoad = [&](int i, int j) -> bool {
        return (0 <= i && i < N && 0 <= j && j < N && grid[i][j] != '#');
    };

    // If start is isolated or invalid input, output empty route
    if (!isRoad(si, sj)) {
        cout << "\n";
        return 0;
    }

    // Iterative DFS to traverse all reachable road cells and return to start
    vector<vector<char>> visited(N, vector<char>(N, 0));
    struct Node { int i, j, k; }; // k is next direction to try
    vector<Node> st;
    st.push_back({si, sj, 0});
    visited[si][sj] = 1;

    const int di[4] = {-1, 0, 1, 0};
    const int dj[4] = {0, 1, 0, -1};
    const char dc[4] = {'U', 'R', 'D', 'L'};

    string ans;
    while (!st.empty()) {
        Node &cur = st.back();
        bool advanced = false;
        while (cur.k < 4) {
            int d = cur.k++;
            int ni = cur.i + di[d];
            int nj = cur.j + dj[d];
            if (isRoad(ni, nj) && !visited[ni][nj]) {
                ans.push_back(dc[d]);
                visited[ni][nj] = 1;
                st.push_back({ni, nj, 0});
                advanced = true;
                break;
            }
        }
        if (!advanced) {
            if (st.size() == 1) break; // back at start, done
            // backtrack to parent
            int ci = st.back().i, cj = st.back().j;
            st.pop_back();
            int pi = st.back().i, pj = st.back().j;
            if (pi == ci - 1 && pj == cj) ans.push_back('U');
            else if (pi == ci + 1 && pj == cj) ans.push_back('D');
            else if (pi == ci && pj == cj - 1) ans.push_back('L');
            else if (pi == ci && pj == cj + 1) ans.push_back('R');
            else {
                // Should not happen; if it does, output current ans safely.
                break;
            }
        }
    }

    cout << ans << "\n";
    return 0;
}