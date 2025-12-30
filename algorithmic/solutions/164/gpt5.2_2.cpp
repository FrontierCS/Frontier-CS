#include <bits/stdc++.h>
using namespace std;

static int pickDest(const vector<vector<int>>& st, int src, int curV) {
    const long long INF = (1LL << 60);
    int m = (int)st.size();
    long long bestScore = INF;
    int best = -1;
    for (int i = 0; i < m; i++) {
        if (i == src) continue;
        long long score = 0;
        if (st[i].empty()) {
            score = 0;
        } else {
            int top = st[i].back();
            long long pen = 0;
            if (top <= curV + 1) pen = 1000000000LL;
            else if (top <= curV + 5) pen = 1000000LL;
            else if (top <= curV + 20) pen = 10000LL;
            score = (long long)st[i].size() * 100 + pen;
        }
        if (score < bestScore) {
            bestScore = score;
            best = i;
        }
    }
    if (best == -1) best = (src + 1) % m;
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    int h = n / m;
    vector<vector<int>> st(m);
    for (int i = 0; i < m; i++) {
        st[i].resize(h);
        for (int j = 0; j < h; j++) cin >> st[i][j];
    }

    vector<pair<int,int>> ops;
    ops.reserve(1000);

    for (int v = 1; v <= n; v++) {
        int s = -1, idx = -1;
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < (int)st[i].size(); j++) {
                if (st[i][j] == v) {
                    s = i;
                    idx = j;
                    break;
                }
            }
            if (s != -1) break;
        }
        if (s == -1) continue; // should not happen

        if (idx != (int)st[s].size() - 1) {
            int x = st[s][idx + 1];
            int d = pickDest(st, s, v);
            ops.push_back({x, d + 1});

            vector<int> seg(st[s].begin() + (idx + 1), st[s].end());
            st[s].erase(st[s].begin() + (idx + 1), st[s].end());
            st[d].insert(st[d].end(), seg.begin(), seg.end());
        }

        // now v must be on top
        if (!st[s].empty() && st[s].back() == v) {
            ops.push_back({v, 0});
            st[s].pop_back();
        } else {
            // Fallback (should not happen): find v again and pop by moving above
            int ss = -1, id = -1;
            for (int i = 0; i < m; i++) {
                for (int j = 0; j < (int)st[i].size(); j++) {
                    if (st[i][j] == v) { ss = i; id = j; break; }
                }
                if (ss != -1) break;
            }
            if (ss == -1) continue;
            while (id != (int)st[ss].size() - 1) {
                int x = st[ss][id + 1];
                int d = pickDest(st, ss, v);
                ops.push_back({x, d + 1});
                vector<int> seg(st[ss].begin() + (id + 1), st[ss].end());
                st[ss].erase(st[ss].begin() + (id + 1), st[ss].end());
                st[d].insert(st[d].end(), seg.begin(), seg.end());
            }
            ops.push_back({v, 0});
            st[ss].pop_back();
        }
    }

    if ((int)ops.size() > 5000) ops.resize(5000);
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << "\n";
    }
    return 0;
}