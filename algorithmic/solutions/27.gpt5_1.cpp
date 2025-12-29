#include <bits/stdc++.h>
using namespace std;

using ll = long long;

bool isPrime(int x) {
    if (x < 2) return false;
    if (x % 2 == 0) return x == 2;
    for (int i = 3; 1LL * i * i <= x; i += 2) {
        if (x % i == 0) return false;
    }
    return true;
}
int nextPrime(int x) {
    if (x < 2) x = 2;
    while (!isPrime(x)) ++x;
    return x;
}
int ceil_sqrt_ll(ll x) {
    if (x <= 0) return 0;
    ll r = sqrt((long double)x);
    while (r * r < x) ++r;
    while ((r - 1) * (r - 1) >= x) --r;
    return (int)r;
}

struct Solution {
    vector<pair<int,int>> cells;
};

Solution build_star(int n, int m) {
    Solution sol;
    sol.cells.reserve(n + m - 1);
    // Take all from row 1
    for (int c = 1; c <= m; ++c) sol.cells.emplace_back(1, c);
    // One from each other row
    for (int r = 2; r <= n; ++r) {
        int c = (r - 2) % m + 1;
        sol.cells.emplace_back(r, c);
    }
    return sol;
}

Solution build_geometry(int n, int m, bool pointsAreRows) {
    // P: number of "points" (nodes on the point side)
    // M: number of "lines"  (nodes on the line side)
    int P = pointsAreRows ? n : m;
    int M = pointsAreRows ? m : n;

    if (P == 0 || M == 0) return Solution();

    // Choose q prime so that q^2 >= max(P, M) (then #lines q(q+1) >= M)
    int base = max(P, M);
    int q = nextPrime(ceil_sqrt_ll(base));
    int Q = q;

    int Npoints = Q * Q;
    int Nlines = Q * (Q + 1);

    vector<int> pointIndex(Npoints, -1);
    // Distribute chosen P points uniformly over the QxQ grid:
    // i -> (x = i % Q, y = (x + i / Q) % Q)
    for (int i = 0; i < P; ++i) {
        int x = i % Q;
        int y = (x + (i / Q)) % Q;
        pointIndex[y * Q + x] = i;
    }

    // Compute weight for all lines
    vector<int> weights(Nlines, 0);

    // Non-vertical lines: y = s*x + b
    for (int s = 0; s < Q; ++s) {
        for (int b = 0; b < Q; ++b) {
            int id = s * Q + b;
            int cnt = 0;
            for (int x = 0; x < Q; ++x) {
                int y = ( (ll)s * x + b ) % Q;
                int idx = y * Q + x;
                if (pointIndex[idx] != -1) ++cnt;
            }
            weights[id] = cnt;
        }
    }
    // Vertical lines: x = b
    for (int b = 0; b < Q; ++b) {
        int id = Q * Q + b;
        int cnt = 0;
        for (int y = 0; y < Q; ++y) {
            int idx = y * Q + b;
            if (pointIndex[idx] != -1) ++cnt;
        }
        weights[id] = cnt;
    }

    // Select top M lines by weight
    vector<int> ids(Nlines);
    iota(ids.begin(), ids.end(), 0);
    // Partial sort to get top M
    nth_element(ids.begin(), ids.begin() + M, ids.end(), [&](int a, int b){
        if (weights[a] != weights[b]) return weights[a] > weights[b];
        return a < b;
    });
    ids.resize(M);
    sort(ids.begin(), ids.end(), [&](int a, int b){
        if (weights[a] != weights[b]) return weights[a] > weights[b];
        return a < b;
    });

    // Build final edges
    Solution sol;
    // Reserve approximate size
    ll sumw = 0;
    for (int id : ids) sumw += weights[id];
    sol.cells.reserve((size_t)sumw);

    for (int j = 0; j < M; ++j) {
        int id = ids[j];
        bool vertical = (id >= Q * Q);
        int s, b;
        if (!vertical) {
            s = id / Q;
            b = id % Q;
            for (int x = 0; x < Q; ++x) {
                int y = ((ll)s * x + b) % Q;
                int idx = y * Q + x;
                int p = pointIndex[idx];
                if (p != -1) {
                    if (pointsAreRows) {
                        int r = p + 1;
                        int c = j + 1;
                        sol.cells.emplace_back(r, c);
                    } else {
                        int r = j + 1;
                        int c = p + 1;
                        sol.cells.emplace_back(r, c);
                    }
                }
            }
        } else {
            b = id - Q * Q;
            for (int y = 0; y < Q; ++y) {
                int idx = y * Q + b;
                int p = pointIndex[idx];
                if (p != -1) {
                    if (pointsAreRows) {
                        int r = p + 1;
                        int c = j + 1;
                        sol.cells.emplace_back(r, c);
                    } else {
                        int r = j + 1;
                        int c = p + 1;
                        sol.cells.emplace_back(r, c);
                    }
                }
            }
        }
    }
    return sol;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;

    Solution best;
    // Star solution
    Solution star = build_star(n, m);
    best = star;

    // Geometry solutions
    Solution geo1 = build_geometry(n, m, true);   // rows as points, columns as lines
    if (geo1.cells.size() > best.cells.size()) best = move(geo1);

    Solution geo2 = build_geometry(n, m, false);  // columns as points, rows as lines
    if (geo2.cells.size() > best.cells.size()) best = move(geo2);

    cout << best.cells.size() << "\n";
    for (auto &p : best.cells) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}