#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;

    int s, b;
    bool smallIsRow;
    if (n <= m) { s = n; b = m; smallIsRow = true; }
    else { s = m; b = n; smallIsRow = false; }

    vector<vector<unsigned char>> used(s, vector<unsigned char>(s, 0));
    vector<vector<int>> neighbors(b);

    // Baseline: one neighbor per big vertex (costs no small-pair usage)
    if (s >= 1) {
        for (int j = 0; j < b; ++j) {
            neighbors[j].push_back(j % s);
        }
    }

    long long P = 1LL * s * (s - 1) / 2;
    long long usedPairs = 0;

    if (s >= 2) {
        bool changed = true;
        int round = 0;
        while (changed && usedPairs < P) {
            changed = false;
            for (int j = 0; j < b && usedPairs < P; ++j) {
                auto &S = neighbors[j];
                int deg = (int)S.size();
                if (deg >= s) continue;

                int start = (j + round) % s;
                bool added = false;
                for (int step = 0; step < s; ++step) {
                    int cand = (start + step) % s;
                    bool present = false;
                    for (int y : S) { if (y == cand) { present = true; break; } }
                    if (present) continue;

                    bool ok = true;
                    for (int y : S) {
                        if (used[cand][y]) { ok = false; break; }
                    }
                    if (ok) {
                        for (int y : S) { used[cand][y] = 1; used[y][cand] = 1; }
                        S.push_back(cand);
                        usedPairs += deg;
                        added = true;
                        break;
                    }
                }
                if (added) changed = true;
            }
            ++round;
        }
    }

    vector<pair<int,int>> result;
    result.reserve(n * m);

    if (smallIsRow) {
        // Small side = rows, big side = columns
        for (int j = 0; j < b; ++j) {
            int c = j + 1;
            for (int rIdx : neighbors[j]) {
                int r = rIdx + 1;
                result.emplace_back(r, c);
            }
        }
    } else {
        // Small side = columns, big side = rows
        for (int j = 0; j < b; ++j) {
            int r = j + 1;
            for (int cIdx : neighbors[j]) {
                int c = cIdx + 1;
                result.emplace_back(r, c);
            }
        }
    }

    cout << result.size() << "\n";
    for (auto &p : result) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}