#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int N = n + 1;
    vector<vector<int>> s(N + 1); // 1..n+1
    for (int i = 1; i <= n; ++i) {
        s[i].reserve(m);
        for (int j = 0; j < m; ++j) {
            int x; cin >> x;
            s[i].push_back(x); // bottom to top
        }
    }
    // s[n+1] empty
    int E = n + 1;

    // Count occurrences per color per tube: colors 1..n, tubes 1..n
    vector<vector<int>> cnt(n + 1, vector<int>(n + 1, 0));
    for (int t = 1; t <= n; ++t) {
        for (int x : s[t]) cnt[x][t]++;
    }

    // Hungarian algorithm to assign each color to a unique tube maximizing cnt[color][tube]
    // We convert to minimization by cost = M - cnt
    int Mconst = m; // maximum cnt per tube
    int size = n;
    const int INF = 1e9;
    vector<vector<int>> a(n + 1, vector<int>(n + 1, 0));
    for (int i = 1; i <= n; ++i)
        for (int j = 1; j <= n; ++j)
            a[i][j] = Mconst - cnt[i][j];

    vector<int> u(size + 1), v(size + 1), p(size + 1), way(size + 1);
    for (int i = 1; i <= size; ++i) {
        p[0] = i;
        int j0 = 0;
        vector<int> minv(size + 1, INF);
        vector<char> used(size + 1, false);
        used[0] = true;
        do {
            used[j0] = true;
            int i0 = p[j0], delta = INF, j1 = 0;
            for (int j = 1; j <= size; ++j) if (!used[j]) {
                int cur = a[i0][j] - u[i0] - v[j];
                if (cur < minv[j]) { minv[j] = cur; way[j] = j0; }
                if (minv[j] < delta) { delta = minv[j]; j1 = j; }
            }
            for (int j = 0; j <= size; ++j) {
                if (used[j]) { u[p[j]] += delta; v[j] -= delta; }
                else minv[j] -= delta;
            }
            j0 = j1;
        } while (p[j0] != 0);
        do {
            int j1 = way[j0];
            p[j0] = p[j1];
            j0 = j1;
        } while (j0);
    }
    // p[j] = i (color) assigned to tube j
    vector<int> dest(n + 1, 0); // dest[color] = tube
    vector<int> color_of_tube(n + 1, 0);
    for (int j = 1; j <= n; ++j) {
        int i = p[j];
        dest[i] = j;
        color_of_tube[j] = i;
    }

    vector<pair<int,int>> ops;
    auto moveBall = [&](int x, int y) {
        // x must have at least 1, y must have at most m-1
        int val = s[x].back();
        s[x].pop_back();
        s[y].push_back(val);
        ops.emplace_back(x, y);
    };
    auto flushE = [&]() {
        while (!s[E].empty()) {
            int c = s[E].back();
            moveBall(E, dest[c]);
        }
    };

    // Process each assigned tube to purify it
    for (int j = 1; j <= n; ++j) {
        int col = color_of_tube[j];
        // remove all non-col from tube j
        while (true) {
            // First, move all foreign colors on top directly to their destination
            bool moved_foreign = false;
            while (!s[j].empty() && s[j].back() != col) {
                int c = s[j].back();
                moveBall(j, dest[c]);
                moved_foreign = true;
            }
            // Check if tube j is pure now
            bool allcol = true;
            for (int x : s[j]) {
                if (x != col) { allcol = false; break; }
            }
            if (allcol) break;

            // Need to evacuate top block of 'col' to E to expose deeper foreign balls
            flushE();
            while (!s[j].empty() && s[j].back() == col) {
                moveBall(j, E);
            }
            // Move now-exposed foreign balls to their destinations
            while (!s[j].empty() && s[j].back() != col) {
                int c = s[j].back();
                moveBall(j, dest[c]);
            }
            // Move back the evacuated 'col' balls from E to j
            while (!s[E].empty()) {
                moveBall(E, j);
            }
        }
    }

    // Ensure E is flushed (should already be empty)
    flushE();

    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}