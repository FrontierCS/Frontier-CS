#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> h(N, vector<int>(N));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) cin >> h[i][j];
    }

    vector<pair<int,int>> path;
    for (int i = 0; i < N; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; ++j) path.emplace_back(i, j);
        } else {
            for (int j = N - 1; j >= 0; --j) path.emplace_back(i, j);
        }
    }
    vector<pair<int,int>> rev_path = path;
    reverse(rev_path.begin(), rev_path.end());

    vector<string> ops;
    long long load = 0;

    auto move_dir = [](pair<int,int> a, pair<int,int> b) -> char {
        if (a.first == b.first) {
            if (a.second + 1 == b.second) return 'R';
            if (a.second - 1 == b.second) return 'L';
        } else if (a.second == b.second) {
            if (a.first + 1 == b.first) return 'D';
            if (a.first - 1 == b.first) return 'U';
        }
        return '?';
    };

    auto handle_load = [&](int i, int j) {
        if (h[i][j] > 0) {
            int d = h[i][j];
            ops.push_back("+" + to_string(d));
            load += d;
            h[i][j] = 0;
        }
    };
    auto handle_unload = [&](int i, int j) {
        if (h[i][j] < 0 && load > 0) {
            int need = -h[i][j];
            int d = (int)min<long long>(load, need);
            if (d > 0) {
                ops.push_back("-" + to_string(d));
                load -= d;
                h[i][j] += d;
            }
        }
    };

    pair<int,int> cur = path[0];
    handle_load(cur.first, cur.second);
    for (int idx = 1; idx < (int)path.size(); ++idx) {
        auto nxt = path[idx];
        char c = move_dir(cur, nxt);
        ops.emplace_back(string(1, c));
        cur = nxt;
        handle_load(cur.first, cur.second);
    }

    for (int idx = 0; idx < (int)rev_path.size(); ++idx) {
        auto cell = rev_path[idx];
        handle_unload(cell.first, cell.second);
        if (idx + 1 < (int)rev_path.size()) {
            auto nxt = rev_path[idx + 1];
            char c = move_dir(cell, nxt);
            ops.emplace_back(string(1, c));
        }
    }

    for (auto &s : ops) cout << s << '\n';
    return 0;
}