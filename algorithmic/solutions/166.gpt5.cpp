#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> h(N, vector<int>(N));
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) cin >> h[i][j];

    int n = N * N;

    auto build_route_snake_rows = [&](bool reversed)->vector<pair<int,int>>{
        vector<pair<int,int>> route;
        route.reserve(n);
        for (int i = 0; i < N; ++i) {
            if (i % 2 == 0) {
                for (int j = 0; j < N; ++j) route.emplace_back(i, j);
            } else {
                for (int j = N-1; j >= 0; --j) route.emplace_back(i, j);
            }
        }
        if (reversed) reverse(route.begin(), route.end());
        return route;
    };
    auto build_route_snake_cols = [&](bool reversed)->vector<pair<int,int>>{
        vector<pair<int,int>> route;
        route.reserve(n);
        for (int j = 0; j < N; ++j) {
            if (j % 2 == 0) {
                for (int i = 0; i < N; ++i) route.emplace_back(i, j);
            } else {
                for (int i = N-1; i >= 0; --i) route.emplace_back(i, j);
            }
        }
        if (reversed) reverse(route.begin(), route.end());
        return route;
    };

    vector<vector<pair<int,int>>> candidates;
    candidates.push_back(build_route_snake_rows(false));
    candidates.push_back(build_route_snake_rows(true));
    candidates.push_back(build_route_snake_cols(false));
    candidates.push_back(build_route_snake_cols(true));

    long long bestMinPref = LLONG_MAX;
    int bestIdx = 0;
    int bestStart = 0;
    int bestInitDist = INT_MAX;

    for (int idx = 0; idx < (int)candidates.size(); ++idx) {
        auto &route = candidates[idx];
        vector<int> a(n);
        for (int k = 0; k < n; ++k) {
            a[k] = h[route[k].first][route[k].second];
        }
        long long sum = 0;
        long long minpref = LLONG_MAX;
        vector<int> mins;
        for (int k = 0; k < n; ++k) {
            sum += a[k];
            if (sum < minpref) {
                minpref = sum;
                mins.clear();
                mins.push_back(k+1); // start is after k
            } else if (sum == minpref) {
                mins.push_back(k+1);
            }
        }
        // choose start among mins to minimize initial Manhattan distance from (0,0)
        int bestS = 0;
        int bestD = INT_MAX;
        for (int s : mins) {
            s %= n;
            auto [ri, rj] = route[s];
            int d = abs(ri - 0) + abs(rj - 0);
            if (d < bestD) {
                bestD = d;
                bestS = s;
            }
        }
        // we want to minimize loaded reposition load (-minpref), then init dist
        if (minpref < bestMinPref) {
            bestMinPref = minpref;
            bestIdx = idx;
            bestStart = bestS;
            bestInitDist = bestD;
        } else if (minpref == bestMinPref) {
            if (bestD < bestInitDist) {
                bestIdx = idx;
                bestStart = bestS;
                bestInitDist = bestD;
            }
        }
    }

    auto route = candidates[bestIdx];

    auto moveFromTo = [&](int sr, int sc, int tr, int tc, vector<string>& ops) {
        while (sr < tr) { ops.emplace_back("D"); ++sr; }
        while (sr > tr) { ops.emplace_back("U"); --sr; }
        while (sc < tc) { ops.emplace_back("R"); ++sc; }
        while (sc > tc) { ops.emplace_back("L"); --sc; }
    };

    vector<string> ops;
    int cr = 0, cc = 0;
    int s = bestStart % n;

    // move to start
    auto [sr, sc] = route[s];
    moveFromTo(cr, cc, sr, sc, ops);
    cr = sr; cc = sc;

    long long load = 0;

    auto doCell = [&](int r, int c) {
        int val = h[r][c];
        if (val > 0) {
            ops.emplace_back("+" + to_string(val));
            load += val;
            h[r][c] = 0;
        } else if (val < 0) {
            int d = -val;
            if (d > 0) {
                ops.emplace_back("-" + to_string(d));
                load -= d;
                h[r][c] = 0;
            }
        }
    };

    // process segment s..n-1
    for (int k = s; k < n; ++k) {
        auto [r, c] = route[k];
        doCell(r, c);
        if (k + 1 < n) {
            auto [nr, nc] = route[k+1];
            moveFromTo(cr, cc, nr, nc, ops);
            cr = nr; cc = nc;
        }
    }
    // move to route[0] if needed and process 0..s-1
    if (s > 0) {
        auto [r0, c0] = route[0];
        moveFromTo(cr, cc, r0, c0, ops);
        cr = r0; cc = c0;
        for (int k = 0; k < s; ++k) {
            auto [r, c] = route[k];
            doCell(r, c);
            if (k + 1 < s) {
                auto [nr, nc] = route[k+1];
                moveFromTo(cr, cc, nr, nc, ops);
                cr = nr; cc = nc;
            }
        }
    }

    for (auto &sop : ops) cout << sop << '\n';
    return 0;
}