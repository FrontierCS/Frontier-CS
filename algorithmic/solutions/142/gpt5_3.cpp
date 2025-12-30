#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if(!(cin >> n >> m)) return 0;
    int N = n + 1; // including empty pole
    vector<vector<int>> pole(N);
    // read stacks: bottom to top; we store as vector with back = top
    for (int i = 0; i < n; ++i) {
        pole[i].reserve(m);
        for (int j = 0; j < m; ++j) {
            int c; cin >> c; --c;
            pole[i].push_back(c);
        }
    }
    pole[n] = {}; // empty pole

    // Movement operation recorder
    vector<pair<int,int>> ops;
    ops.reserve(1000000);

    auto move_ball = [&](int x, int y) {
        // x, y are 0-based pole indices
        // Preconditions: x != y, pole[x] not empty, pole[y].size() < m
        int b = pole[x].back(); pole[x].pop_back();
        pole[y].push_back(b);
        ops.emplace_back(x+1, y+1); // output uses 1-based indices
    };

    // Build weight matrix for assignment: w[color][pole]
    vector<vector<int>> w(n, vector<int>(n, 0));
    for (int i = 0; i < n; ++i) {
        for (int b : pole[i]) {
            if (b >= 0 && b < n) w[b][i]++;
        }
    }

    // Hungarian algorithm for maximizing weight -> minimize cost = -w
    int sz = n;
    const int INF = 1e9;
    vector<int> u(sz+1,0), v(sz+1,0), p(sz+1,0), way(sz+1,0);
    vector<vector<int>> a(sz+1, vector<int>(sz+1,0));
    for (int i = 1; i <= sz; ++i)
        for (int j = 1; j <= sz; ++j)
            a[i][j] = -w[i-1][j-1];
    for (int i = 1; i <= sz; ++i) {
        p[0] = i;
        int j0 = 0;
        vector<int> minv(sz+1, INF);
        vector<char> used(sz+1, false);
        do {
            used[j0] = true;
            int i0 = p[j0], delta = INF, j1 = 0;
            for (int j = 1; j <= sz; ++j) if (!used[j]) {
                int cur = a[i0][j] - u[i0] - v[j];
                if (cur < minv[j]) { minv[j] = cur; way[j] = j0; }
                if (minv[j] < delta) { delta = minv[j]; j1 = j; }
            }
            for (int j = 0; j <= sz; ++j) {
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
    vector<int> targetPole(n, -1); // color -> pole
    for (int j = 1; j <= sz; ++j) {
        int i = p[j]; // row i assigned to column j
        targetPole[i-1] = j-1;
    }

    int E = n; // empty pole index

    vector<char> finalizedPole(n, false);

    // Order of colors to finalize: 0..n-1
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    for (int idx = 0; idx < n; ++idx) {
        int c = order[idx];
        int P = targetPole[c]; // target pole for color c
        // Build donors: all non-finalized poles except P (exclude E)
        for (int J = 0; J < n; ++J) {
            if (J == P) continue;
            if (finalizedPole[J]) continue;

            // Move entire J to E
            while (!pole[J].empty()) {
                move_ball(J, E);
            }
            // Process E: send c to P, others to J
            while (!pole[E].empty()) {
                int topc = pole[E].back();
                if (topc == c) {
                    while ((int)pole[P].size() == m) {
                        move_ball(P, J);
                    }
                    move_ball(E, P);
                } else {
                    move_ball(E, J);
                }
            }
            // Now J is full again, E is empty
        }
        finalizedPole[P] = true;
    }

    cout << ops.size() << "\n";
    for (auto &pr : ops) {
        cout << pr.first << " " << pr.second << "\n";
    }
    return 0;
}