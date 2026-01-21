#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int totalPillars = n + 1;
    vector<vector<int>> pillars(totalPillars + 1); // 1..n+1
    for (int i = 1; i <= n; ++i) {
        pillars[i].reserve(m);
        for (int j = 0; j < m; ++j) {
            int c; cin >> c;
            pillars[i].push_back(c);
        }
    }
    // pillar n+1 initially empty

    const int LIMIT = 10000000;
    vector<pair<int,int>> ops;
    ops.reserve(min(LIMIT, n * m * 10 + 10));

    auto move_ball = [&](int x, int y) {
        if (x == y) return;
        if (pillars[x].empty()) return;
        if ((int)pillars[y].size() >= m) return;
        int c = pillars[x].back();
        pillars[x].pop_back();
        pillars[y].push_back(c);
        ops.emplace_back(x, y);
    };

    auto solved = [&]() -> bool {
        if (!pillars[n+1].empty()) return false;
        for (int i = 1; i <= n; ++i) {
            if ((int)pillars[i].size() != m) return false;
            for (int c : pillars[i]) if (c != i) return false;
        }
        return true;
    };

    int safetyIters = 0;
    while (!solved() && (int)ops.size() < LIMIT && safetyIters < LIMIT) {
        ++safetyIters;
        bool progress = false;

        // Step 1: greedy moves to correct pillar when target has space
        for (int i = 1; i <= n + 1 && (int)ops.size() < LIMIT; ++i) {
            if (pillars[i].empty()) continue;
            int c = pillars[i].back();
            if (c >= 1 && c <= n && i != c && (int)pillars[c].size() < m) {
                move_ball(i, c);
                progress = true;
            }
        }
        if (progress) continue;

        // Step 2: try to free wrong-top balls by pushing to buffer or other free pillar
        int buf = n + 1;
        for (int i = 1; i <= n && (int)ops.size() < LIMIT; ++i) {
            if (pillars[i].empty()) continue;
            int topc = pillars[i].back();
            if (topc == i) continue; // already correct on top
            // If its own pillar is full we couldn't move in step 1; push somewhere else
            if ((int)pillars[buf].size() < m && buf != i) {
                move_ball(i, buf);
                progress = true;
                break;
            } else {
                // buffer full or same as i: move from buffer to some pillar with space
                if (!pillars[buf].empty()) {
                    int c = pillars[buf].back();
                    int dest = -1;
                    if (c >= 1 && c <= n && (int)pillars[c].size() < m && c != buf) {
                        dest = c;
                    } else {
                        for (int j = 1; j <= n; ++j) {
                            if (j == buf) continue;
                            if ((int)pillars[j].size() < m) {
                                dest = j;
                                break;
                            }
                        }
                    }
                    if (dest != -1) {
                        move_ball(buf, dest);
                        progress = true;
                        break;
                    }
                }
                // if buffer empty or couldn't move from it, try another free pillar directly
                int dest2 = -1;
                for (int j = 1; j <= n; ++j) {
                    if (j == i) continue;
                    if ((int)pillars[j].size() < m) {
                        dest2 = j;
                        break;
                    }
                }
                if (dest2 != -1) {
                    move_ball(i, dest2);
                    progress = true;
                    break;
                }
            }
        }
        if (progress) continue;

        // Step 3: try to unload buffer to correct places
        if (!pillars[buf].empty() && (int)ops.size() < LIMIT) {
            int c = pillars[buf].back();
            int dest = -1;
            if (c >= 1 && c <= n && (int)pillars[c].size() < m) dest = c;
            else {
                for (int j = 1; j <= n; ++j) {
                    if ((int)pillars[j].size() < m && j != buf) {
                        dest = j;
                        break;
                    }
                }
            }
            if (dest != -1) {
                move_ball(buf, dest);
                continue;
            }
        }

        // Step 4: if nothing else, perform a random-ish shuffle to try to change configuration
        bool shuffled = false;
        for (int i = 1; i <= n && (int)ops.size() < LIMIT; ++i) {
            if (pillars[i].empty()) continue;
            for (int j = 1; j <= n + 1; ++j) {
                if (j == i) continue;
                if ((int)pillars[j].size() < m) {
                    move_ball(i, j);
                    shuffled = true;
                    break;
                }
            }
            if (shuffled) break;
        }
        if (!shuffled) break; // no more legal moves
    }

    if ((int)ops.size() > LIMIT) {
        ops.resize(LIMIT);
    }

    cout << ops.size() << "\n";
    for (auto &mv : ops) {
        cout << mv.first << " " << mv.second << "\n";
    }
    return 0;
}