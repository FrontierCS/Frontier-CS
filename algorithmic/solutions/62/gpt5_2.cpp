#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int N = n + 1; // last is buffer
    vector<vector<int>> st(N + 1); // 1..n+1
    for (int i = 1; i <= n; ++i) {
        st[i].resize(m);
        for (int j = 0; j < m; ++j) cin >> st[i][j];
    }
    st[N] = {}; // buffer initially empty
    
    vector<pair<int,int>> ops;
    ops.reserve(1000000); // reserve some, will grow if needed
    
    auto moveBall = [&](int x, int y) {
        // x != y, st[x] not empty, st[y] not full
        int c = st[x].back();
        st[x].pop_back();
        st[y].push_back(c);
        ops.emplace_back(x, y);
    };
    
    auto countColorOn = [&](int pile, int col) {
        int cnt = 0;
        for (int v : st[pile]) if (v == col) ++cnt;
        return cnt;
    };
    
    auto topIsColor = [&](int pile, int col) -> bool {
        if (st[pile].empty()) return false;
        return st[pile].back() == col;
    };
    
    for (int cur = 1; cur <= n; ++cur) {
        int t = cur; // target pile for color cur
        int buffer = N;
        int tCount = countColorOn(t, cur);
        
        // Process until target has all m balls of color cur
        while (tCount < m) {
            // Step 1: move all available top-cur from other active piles to t while t has space
            bool movedAny = true;
            while (movedAny && (int)st[t].size() < m) {
                movedAny = false;
                for (int p = cur; p <= N && (int)st[t].size() < m; ++p) {
                    if (p == t) continue;
                    while (!st[p].empty() && st[p].back() == cur && (int)st[t].size() < m) {
                        moveBall(p, t);
                        ++tCount;
                        movedAny = true;
                    }
                }
            }
            if (tCount == m) break;
            
            // Step 2: if top of t is not cur, try to move it away to some space (excluding processed piles)
            if (!st[t].empty() && st[t].back() != cur) {
                int y = -1;
                for (int q = cur; q <= N; ++q) {
                    if (q == t) continue;
                    if ((int)st[q].size() < m) { y = q; break; }
                }
                if (y != -1) {
                    // Note: if we move out a cur, decrement tCount (though we ensured top != cur)
                    moveBall(t, y);
                    // continue to next loop iteration
                    continue;
                }
                // else no space except possibly on t itself; we'll proceed to peeling
            }
            
            // Step 3: If t is full but not done, free one slot by moving from t to some y
            if ((int)st[t].size() == m) {
                int y = -1;
                for (int q = cur; q <= N; ++q) {
                    if (q == t) continue;
                    if ((int)st[q].size() < m) { y = q; break; }
                }
                if (y != -1) {
                    // if moving out a cur
                    if (!st[t].empty() && st[t].back() == cur) --tCount;
                    moveBall(t, y);
                    continue;
                }
                // Should not happen due to invariant of total free slots across active piles.
            }
            
            // Step 4: Find a pile containing color cur to peel
            int chosen = -1;
            int bestDepth = INT_MAX;
            for (int p = cur; p <= N; ++p) {
                if (p == t) continue;
                int sz = (int)st[p].size();
                int depth = -1;
                for (int idx = sz - 1; idx >= 0; --idx) {
                    if (st[p][idx] == cur) { depth = sz - 1 - idx; break; }
                }
                if (depth != -1 && depth < bestDepth) {
                    bestDepth = depth;
                    chosen = p;
                }
            }
            if (chosen == -1) {
                // No pile (other than t) contains cur; If tCount < m, this implies impossible, but the problem guarantees a valid solution exists.
                // As a fallback, try to create space or move from t; but we should not reach here.
                break;
            }
            
            // Step 5: Peel chosen until top is cur
            while (!st[chosen].empty() && st[chosen].back() != cur) {
                int y = -1;
                // Prefer space not t and not chosen
                for (int q = cur; q <= N; ++q) {
                    if (q == chosen || q == t) continue;
                    if ((int)st[q].size() < m) { y = q; break; }
                }
                if (y == -1) {
                    // Allow t if it has space
                    if ((int)st[t].size() < m) {
                        y = t;
                    } else {
                        // t is full. The only free might be on chosen itself.
                        // Transfer free from chosen to some z by moving z->chosen, then chosen->z
                        int z = -1;
                        for (int q = cur; q <= N; ++q) {
                            if (q == chosen || q == t) continue;
                            if (!st[q].empty()) { z = q; break; }
                        }
                        if (z != -1) {
                            // chosen must have space if no y found (free at chosen)
                            moveBall(z, chosen);
                            y = z;
                        } else {
                            // Only active piles are t and chosen. In this stage, all remaining balls should be color cur,
                            // so the while condition would have failed earlier. Safeguard: break to avoid infinite loop.
                            break;
                        }
                    }
                }
                moveBall(chosen, y);
            }
            // Now chosen top is cur (if exists), move it to t
            if (!st[chosen].empty() && st[chosen].back() == cur) {
                if ((int)st[t].size() == m) {
                    // Free one slot
                    int y = -1;
                    for (int q = cur; q <= N; ++q) {
                        if (q == t) continue;
                        if ((int)st[q].size() < m) { y = q; break; }
                    }
                    if (y != -1) {
                        if (!st[t].empty() && st[t].back() == cur) --tCount;
                        moveBall(t, y);
                    }
                }
                if ((int)st[t].size() < m) {
                    moveBall(chosen, t);
                    ++tCount;
                }
            }
        }
    }
    
    cout << ops.size() << '\n';
    for (auto &pr : ops) {
        cout << pr.first << ' ' << pr.second << '\n';
    }
    return 0;
}