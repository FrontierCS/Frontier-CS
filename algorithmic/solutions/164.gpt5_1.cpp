#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> st(m);
    for (int i = 0; i < m; ++i) {
        st[i].resize(n / m);
        for (int j = 0; j < n / m; ++j) cin >> st[i][j];
    }
    vector<pair<int,int>> pos(n + 1, {-1, -1}); // (stack, index)
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < (int)st[i].size(); ++j) {
            pos[st[i][j]] = {i, j};
        }
    }

    vector<pair<int,int>> ops;

    auto moveSegment = [&](int v, int dest) {
        auto [s, idx] = pos[v];
        // move st[s][idx..end] to st[dest]
        vector<int> seg;
        seg.reserve(st[s].size() - idx);
        for (int k = idx; k < (int)st[s].size(); ++k) seg.push_back(st[s][k]);
        st[s].resize(idx);
        for (int x : seg) {
            pos[x] = {dest, (int)st[dest].size()};
            st[dest].push_back(x);
        }
        ops.emplace_back(v, dest + 1);
    };

    auto takeOut = [&](int v) {
        auto [s, idx] = pos[v];
        // ensure v is at top
        // It should be, but guard anyway
        if (s != -1 && !st[s].empty() && st[s].back() == v) {
            st[s].pop_back();
            pos[v] = {-1, -1};
            ops.emplace_back(v, 0);
        } else {
            // Should not happen; but to avoid illegal output, try to recover by searching
            bool found = false;
            for (int i = 0; i < m && !found; ++i) {
                if (!st[i].empty() && st[i].back() == v) {
                    st[i].pop_back();
                    pos[v] = {-1, -1};
                    ops.emplace_back(v, 0);
                    found = true;
                }
            }
            if (!found) {
                // As a last resort (should not occur), do nothing.
            }
        }
    };

    auto chooseDest = [&](int source, int nextV)->int{
        int dest = -1;
        int bestVal = -1;
        // First pass: avoid burying v+1 on top if possible
        for (int pass = 0; pass < 2 && dest == -1; ++pass) {
            bool avoidNext = (pass == 0);
            int best = -1, bestIdx = -1;
            for (int i = 0; i < m; ++i) {
                if (i == source) continue;
                bool isEmpty = st[i].empty();
                int topVal = isEmpty ? n + 1 : st[i].back();
                bool isNextTop = (!isEmpty && st[i].back() == nextV);
                if (avoidNext && isNextTop) continue;
                if (topVal > best) {
                    best = topVal;
                    bestIdx = i;
                }
            }
            dest = bestIdx;
        }
        if (dest == -1) {
            // Fallback (should not happen since m>=2)
            for (int i = 0; i < m; ++i) if (i != source) { dest = i; break; }
        }
        return dest;
    };

    for (int v = 1; v <= n; ++v) {
        while (true) {
            auto [s, idx] = pos[v];
            if (s == -1) break; // already taken out (shouldn't happen)
            int h = (int)st[s].size();
            if (idx == h - 1) {
                // v is on top
                takeOut(v);
                break;
            } else {
                int above = st[s][idx + 1];
                int dest = chooseDest(s, v + 1);
                if (dest == s) {
                    // pick any other stack
                    for (int i = 0; i < m; ++i) if (i != s) { dest = i; break; }
                }
                moveSegment(above, dest);
                // Now v should be on top of its stack
                // loop continues to remove it
            }
        }
    }

    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}