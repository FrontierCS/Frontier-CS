#include <bits/stdc++.h>
using namespace std;

vector<tuple<int, int, int>> ans;
vector<vector<char>> edge;

void add_edge(int a, int b, int c) {
    if (!edge[a][c]) {
        edge[a][c] = 1;
        ans.emplace_back(a, b, c);
    }
}

void add_left_edges(int l, int m) {
    for (int i = m - 2; i >= l; --i) {
        // add edge i -> m using i -> i+1 and i+1 -> m
        add_edge(i, i + 1, m);
    }
}

void add_right_edges(int m, int r) {
    for (int j = m + 2; j <= r; ++j) {
        // add edge m -> j using m -> j-1 and j-1 -> j
        add_edge(m, j - 1, j);
    }
}

void solve(int l, int r) {
    if (r - l <= 3) return;
    int m = (l + r) / 2;
    solve(l, m);
    solve(m, r);
    add_left_edges(l, m);
    add_right_edges(m, r);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    edge.assign(n + 1, vector<char>(n + 1, 0));
    // initial edges: v -> v+1
    for (int i = 0; i < n; ++i) {
        edge[i][i + 1] = 1;
    }

    solve(0, n);

    cout << ans.size() << '\n';
    for (auto [u, c, v] : ans) {
        cout << u << ' ' << c << ' ' << v << '\n';
    }
    return 0;
}