#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<int> st[52];
vector<pair<int,int>> ops;

int currColor, targetIdx;
vector<int> topPosC;

inline void mv_basic(int x, int y) {
    int v = st[x].back();
    st[x].pop_back();
    st[y].push_back(v);
    ops.emplace_back(x, y);
}

inline void mv(int x, int y) {
    int v = st[x].back();
    st[x].pop_back();
    st[y].push_back(v);
    ops.emplace_back(x, y);
    if (v == currColor) {
        int &tp = topPosC[x];
        tp = -1;
        for (int i = 0; i < (int)st[x].size(); ++i)
            if (st[x][i] == currColor) tp = i;
    }
}

void process_color(int c) {
    currColor = c;
    targetIdx = c;
    topPosC.assign(n + 2, -1);

    for (int i = c; i <= n + 1; ++i) {
        for (int k = 0; k < (int)st[i].size(); ++k)
            if (st[i][k] == currColor) topPosC[i] = k;
    }

    int have = 0;
    for (int k = 0; k < (int)st[targetIdx].size(); ++k)
        if (st[targetIdx][k] == currColor) ++have;

    while (have < m) {
        // Clean non-current-color from top of target
        while (!st[targetIdx].empty() && st[targetIdx].back() != currColor) {
            int dst = -1;
            for (int j = c; j <= n + 1; ++j) {
                if (j == targetIdx) continue;
                if ((int)st[j].size() < m) {
                    dst = j;
                    break;
                }
            }
            if (dst == -1) {
                for (int j = 1; j <= n + 1; ++j) {
                    if (j == targetIdx) continue;
                    if ((int)st[j].size() < m) {
                        dst = j;
                        break;
                    }
                }
                if (dst == -1) return;
            }
            mv_basic(targetIdx, dst);
        }

        // Move top currColor from other tubes to target if possible
        bool moved = false;
        for (int i = c; i <= n + 1; ++i) {
            if (i == targetIdx) continue;
            if (!st[i].empty() && st[i].back() == currColor) {
                mv(i, targetIdx);
                ++have;
                moved = true;
                break;
            }
        }
        if (moved) continue;

        // Need to dig for currColor from inside some tube
        int s = -1;
        int bestDist = INT_MAX;
        for (int i = c; i <= n + 1; ++i) {
            if (i == targetIdx) continue;
            if (topPosC[i] != -1) {
                int dist = (int)st[i].size() - 1 - topPosC[i];
                if (dist < bestDist) {
                    bestDist = dist;
                    s = i;
                }
            }
        }
        if (s == -1) break; // should not happen

        // Remove non-currColor from top of s
        while (!st[s].empty() && st[s].back() != currColor) {
            int dst = -1;
            // Prefer tubes without currColor
            for (int j = c; j <= n + 1; ++j) {
                if (j == s || j == targetIdx) continue;
                if ((int)st[j].size() < m && topPosC[j] == -1) {
                    dst = j;
                    break;
                }
            }
            if (dst == -1) {
                for (int j = c; j <= n + 1; ++j) {
                    if (j == s || j == targetIdx) continue;
                    if ((int)st[j].size() < m) {
                        dst = j;
                        break;
                    }
                }
            }
            if (dst == -1) {
                for (int j = c; j <= n + 1; ++j) {
                    if (j == s) continue;
                    if ((int)st[j].size() < m) {
                        dst = j;
                        break;
                    }
                }
            }
            if (dst == -1) break; // should not happen
            mv_basic(s, dst);
        }
        if (!st[s].empty() && st[s].back() == currColor) {
            mv(s, targetIdx);
            ++have;
        } else {
            break; // should not happen
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> m)) return 0;
    for (int i = 1; i <= n; ++i) {
        st[i].resize(m);
        for (int j = 0; j < m; ++j) cin >> st[i][j];
    }
    st[n + 1].clear();

    for (int c = 1; c <= n; ++c) {
        process_color(c);
    }

    cout << ops.size() << '\n';
    for (auto &p : ops) cout << p.first << ' ' << p.second << '\n';
    return 0;
}