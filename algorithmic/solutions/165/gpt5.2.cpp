#include <bits/stdc++.h>
using namespace std;

static int overlap_len(const string &a, const string &b) {
    int la = (int)a.size(), lb = (int)b.size();
    int mx = min(la, lb);
    for (int k = mx; k >= 1; --k) {
        bool ok = true;
        for (int i = 0; i < k; ++i) {
            if (a[la - k + i] != b[i]) { ok = false; break; }
        }
        if (ok) return k;
    }
    return 0;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    int si, sj;
    cin >> si >> sj;

    vector<string> grid(N);
    for (int i = 0; i < N; i++) cin >> grid[i];

    vector<vector<pair<int,int>>> pos(26);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            pos[grid[i][j] - 'A'].push_back({i, j});
        }
    }

    vector<string> cur(M);
    for (int i = 0; i < M; i++) cin >> cur[i];

    // Remove any string that is a substring of another (can happen after merges)
    auto remove_contained = [&]() {
        bool changed = true;
        while (changed) {
            changed = false;
            int n = (int)cur.size();
            for (int i = 0; i < n && !changed; ++i) {
                for (int j = 0; j < n && !changed; ++j) {
                    if (i == j) continue;
                    if (cur[i].find(cur[j]) != string::npos) {
                        cur.erase(cur.begin() + j);
                        changed = true;
                    }
                }
            }
        }
    };

    remove_contained();

    while (cur.size() > 1) {
        remove_contained();
        int n = (int)cur.size();
        int best_i = -1, best_j = -1;
        int best_ov = -1;
        int best_len = INT_MAX;

        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) if (i != j) {
                int ov = overlap_len(cur[i], cur[j]);
                int merged_len = (int)cur[i].size() + (int)cur[j].size() - ov;
                if (ov > best_ov || (ov == best_ov && merged_len < best_len)) {
                    best_ov = ov;
                    best_len = merged_len;
                    best_i = i;
                    best_j = j;
                }
            }
        }

        if (best_i == -1) break;

        string merged = cur[best_i] + cur[best_j].substr(best_ov);

        if (best_i > best_j) swap(best_i, best_j);
        cur.erase(cur.begin() + best_j);
        cur.erase(cur.begin() + best_i);
        cur.push_back(std::move(merged));
    }

    string S = cur.empty() ? "" : cur[0];

    vector<pair<int,int>> ops;
    ops.reserve(S.size());
    int ci = si, cj = sj;

    for (char ch : S) {
        auto &v = pos[ch - 'A'];
        int bestd = INT_MAX;
        pair<int,int> bestp = v[0];
        for (auto &p : v) {
            int d = abs(p.first - ci) + abs(p.second - cj);
            if (d < bestd) {
                bestd = d;
                bestp = p;
            }
        }
        ops.push_back(bestp);
        ci = bestp.first; cj = bestp.second;
    }

    // Ensure within 5000 operations (should be, but truncate as a safety net)
    if ((int)ops.size() > 5000) ops.resize(5000);

    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}