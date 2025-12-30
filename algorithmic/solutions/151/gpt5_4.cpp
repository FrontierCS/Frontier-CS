#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, si, sj;
    if (!(cin >> N >> si >> sj)) return 0;
    vector<string> grid(N);
    for (int i = 0; i < N; i++) cin >> grid[i];

    vector<vector<char>> visited(N, vector<char>(N, 0));
    auto inb = [&](int i, int j){ return i >= 0 && i < N && j >= 0 && j < N; };
    auto isRoad = [&](int i, int j){ return inb(i,j) && grid[i][j] != '#'; };

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};
    const int opp[4] = {1, 0, 3, 2};

    string route;
    if (!isRoad(si, sj)) {
        cout << "\n";
        return 0;
    }

    struct Node {
        int i, j;
        int nextdir;
        int parentdir; // direction from parent to this node, -1 for root
    };

    vector<Node> st;
    st.push_back({si, sj, 0, -1});
    visited[si][sj] = 1;

    while (!st.empty()) {
        auto &e = st.back();
        bool moved = false;
        while (e.nextdir < 4) {
            int d = e.nextdir++;
            int ni = e.i + di[d], nj = e.j + dj[d];
            if (isRoad(ni, nj) && !visited[ni][nj]) {
                visited[ni][nj] = 1;
                route.push_back(dc[d]);
                st.push_back({ni, nj, 0, d});
                moved = true;
                break;
            }
        }
        if (!moved) {
            if (e.parentdir != -1) {
                route.push_back(dc[opp[e.parentdir]]);
            }
            st.pop_back();
        }
    }

    cout << route << "\n";
    return 0;
}