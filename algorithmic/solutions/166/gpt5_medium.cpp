#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<vector<long long>> h(N, vector<long long>(N));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) cin >> h[i][j];
    }

    // Build serpentine path
    vector<pair<int,int>> path;
    path.reserve(N*N);
    for (int i = 0; i < N; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; ++j) path.emplace_back(i, j);
        } else {
            for (int j = N-1; j >= 0; --j) path.emplace_back(i, j);
        }
    }

    vector<string> ops;
    long long load = 0;

    auto move_between = [&](pair<int,int> a, pair<int,int> b){
        int di = b.first - a.first;
        int dj = b.second - a.second;
        if (di == 1 && dj == 0) ops.emplace_back("D");
        else if (di == -1 && dj == 0) ops.emplace_back("U");
        else if (di == 0 && dj == 1) ops.emplace_back("R");
        else if (di == 0 && dj == -1) ops.emplace_back("L");
    };

    // Start at (0,0)
    pair<int,int> cur = {0,0};

    // Process first cell
    {
        int i = cur.first, j = cur.second;
        if (h[i][j] > 0) {
            long long d = h[i][j];
            ops.emplace_back("+" + to_string(d));
            load += d;
            h[i][j] = 0;
        } else if (h[i][j] < 0 && load > 0) {
            long long d = min(load, -h[i][j]);
            if (d > 0) {
                ops.emplace_back("-" + to_string(d));
                load -= d;
                h[i][j] += d;
            }
        }
    }

    // Forward pass
    for (size_t k = 1; k < path.size(); ++k) {
        pair<int,int> nxt = path[k];
        move_between(cur, nxt);
        cur = nxt;
        int i = cur.first, j = cur.second;
        if (h[i][j] > 0) {
            long long d = h[i][j];
            ops.emplace_back("+" + to_string(d));
            load += d;
            h[i][j] = 0;
        } else if (h[i][j] < 0 && load > 0) {
            long long d = min(load, -h[i][j]);
            if (d > 0) {
                ops.emplace_back("-" + to_string(d));
                load -= d;
                h[i][j] += d;
            }
        }
    }

    // Reverse pass: unload remaining soil to negatives
    // Process current cell first (last cell of path)
    {
        int i = cur.first, j = cur.second;
        if (h[i][j] < 0 && load > 0) {
            long long d = min(load, -h[i][j]);
            if (d > 0) {
                ops.emplace_back("-" + to_string(d));
                load -= d;
                h[i][j] += d;
            }
        }
    }

    for (int idx = (int)path.size() - 2; idx >= 0; --idx) {
        pair<int,int> nxt = path[idx];
        move_between(cur, nxt);
        cur = nxt;
        int i = cur.first, j = cur.second;
        if (h[i][j] < 0 && load > 0) {
            long long d = min(load, -h[i][j]);
            if (d > 0) {
                ops.emplace_back("-" + to_string(d));
                load -= d;
                h[i][j] += d;
            }
        }
    }

    // Output operations
    for (auto &s : ops) cout << s << '\n';
    return 0;
}