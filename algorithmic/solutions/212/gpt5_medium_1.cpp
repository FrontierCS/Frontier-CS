#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n, m, L, R, Sx, Sy, Lq;
    long long sparam;
    vector<int> qseq;

    bool isSubseq(const vector<int>& P, const vector<int>& Q) {
        int i = 0, j = 0;
        while (i < (int)P.size() && j < (int)Q.size()) {
            if (P[i] == Q[j]) ++j;
            ++i;
        }
        return j == (int)Q.size();
    }

    bool buildPlan(bool downFirst, bool secondAsc, vector<pair<int,int>>& outPath, vector<int>& outP) {
        // Build the row order P
        vector<int> P;
        if (downFirst) {
            for (int r = Sx; r <= n; ++r) P.push_back(r);
            if (Sx > 1) {
                if (secondAsc) {
                    for (int r = 1; r <= Sx - 1; ++r) P.push_back(r);
                } else {
                    for (int r = Sx - 1; r >= 1; --r) P.push_back(r);
                }
            }
        } else {
            for (int r = Sx; r >= 1; --r) P.push_back(r);
            if (Sx < n) {
                if (secondAsc) {
                    for (int r = Sx + 1; r <= n; ++r) P.push_back(r);
                } else {
                    for (int r = n; r >= Sx + 1; --r) P.push_back(r);
                }
            }
        }

        // Feasibility check for wrapping
        bool needWrap = false;
        int endRow = downFirst ? n : 1;
        if ((downFirst && Sx > 1) || (!downFirst && Sx < n)) needWrap = true;

        int width = R - L + 1;
        if (needWrap) {
            if (width > 1) {
                int k = abs(endRow - Sx);
                int endCol = (k % 2 == 0 ? R : L);
                if (endCol == L && L == 1) return false;
                if (endCol == R && R == m) return false;
            } else { // width == 1
                if (m == 1) return false; // no outside corridor available
            }
        }

        // Now build the actual path
        vector<pair<int,int>> path;
        vector<vector<char>> vis(n + 1, vector<char>(m + 1, 0));
        auto moveTo = [&](int x, int y) -> bool {
            if (x < 1 || x > n || y < 1 || y > m) return false;
            if (vis[x][y]) return false;
            path.emplace_back(x, y);
            vis[x][y] = 1;
            return true;
        };
        auto sweepRowTo = [&](int r, int targetY, int curY) -> bool {
            if (curY == targetY) return true;
            int dy = (targetY > curY ? 1 : -1);
            for (int y = curY + dy; ; y += dy) {
                if (!moveTo(r, y)) return false;
                if (y == targetY) break;
            }
            return true;
        };

        int curX = Sx, curY = L;
        // Start
        if (!moveTo(curX, curY)) return false;
        if (width > 1) {
            if (!sweepRowTo(curX, R, curY)) return false;
            curY = R;
        }
        // First block
        if (downFirst) {
            for (int r = Sx + 1; r <= n; ++r) {
                // move vertically
                if (!moveTo(r, curY)) return false;
                curX = r;
                // sweep to other end
                if (width > 1) {
                    int target = (curY == L ? R : L);
                    if (!sweepRowTo(curX, target, curY)) return false;
                    curY = target;
                }
            }
        } else {
            for (int r = Sx - 1; r >= 1; --r) {
                if (!moveTo(r, curY)) return false;
                curX = r;
                if (width > 1) {
                    int target = (curY == L ? R : L);
                    if (!sweepRowTo(curX, target, curY)) return false;
                    curY = target;
                }
            }
        }

        // Wrap if needed
        if (needWrap) {
            bool useLeft = false;
            if (width > 1) {
                if (curY == L) useLeft = true;
                else useLeft = false;
            } else {
                // width == 1: choose any available side
                if (L > 1) useLeft = true;
                else useLeft = false; // must have m >= 2 so right exists
            }
            int outY = useLeft ? (L - 1) : (R + 1);
            if (!moveTo(curX, outY)) return false;

            int t;
            if (downFirst) {
                t = secondAsc ? 1 : (Sx - 1);
            } else {
                t = secondAsc ? (Sx + 1) : n;
            }
            // move along outside to row t
            while (curX != t) {
                int nx = (t > curX) ? (curX + 1) : (curX - 1);
                if (!moveTo(nx, outY)) return false;
                curX = nx;
            }
            // enter required area
            int entryCol = useLeft ? L : R;
            if (!moveTo(curX, entryCol)) return false;
            curY = entryCol;
            if (width > 1) {
                int target = (curY == L ? R : L);
                if (!sweepRowTo(curX, target, curY)) return false;
                curY = target;
            }
            // Traverse remaining rows in block2
            if (downFirst) {
                if (secondAsc) {
                    for (int r = 2; r <= Sx - 1; ++r) {
                        if (!moveTo(r, curY)) return false;
                        curX = r;
                        if (width > 1) {
                            int target = (curY == L ? R : L);
                            if (!sweepRowTo(curX, target, curY)) return false;
                            curY = target;
                        }
                    }
                } else {
                    for (int r = Sx - 2; r >= 1; --r) {
                        if (!moveTo(r, curY)) return false;
                        curX = r;
                        if (width > 1) {
                            int target = (curY == L ? R : L);
                            if (!sweepRowTo(curX, target, curY)) return false;
                            curY = target;
                        }
                    }
                }
            } else {
                if (secondAsc) {
                    for (int r = Sx + 2; r <= n; ++r) {
                        if (!moveTo(r, curY)) return false;
                        curX = r;
                        if (width > 1) {
                            int target = (curY == L ? R : L);
                            if (!sweepRowTo(curX, target, curY)) return false;
                            curY = target;
                        }
                    }
                } else {
                    for (int r = n - 1; r >= Sx + 1; --r) {
                        if (!moveTo(r, curY)) return false;
                        curX = r;
                        if (width > 1) {
                            int target = (curY == L ? R : L);
                            if (!sweepRowTo(curX, target, curY)) return false;
                            curY = target;
                        }
                    }
                }
            }
        }

        outPath = move(path);
        outP = move(P);
        return true;
    }

    void solve() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);
        if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> sparam)) {
            return;
        }
        qseq.resize(Lq);
        for (int i = 0; i < Lq; ++i) cin >> qseq[i];

        vector<pair<int,int>> path;
        vector<int> P;

        // Try all 4 patterns
        vector<pair<bool,bool>> tries = {
            {true, true},
            {true, false},
            {false, true},
            {false, false}
        };

        for (auto [downFirst, secondAsc] : tries) {
            vector<int> Ptest;
            // Build P order only to test subsequence first
            if (downFirst) {
                for (int r = Sx; r <= n; ++r) Ptest.push_back(r);
                if (Sx > 1) {
                    if (secondAsc) { for (int r = 1; r <= Sx - 1; ++r) Ptest.push_back(r); }
                    else { for (int r = Sx - 1; r >= 1; --r) Ptest.push_back(r); }
                }
            } else {
                for (int r = Sx; r >= 1; --r) Ptest.push_back(r);
                if (Sx < n) {
                    if (secondAsc) { for (int r = Sx + 1; r <= n; ++r) Ptest.push_back(r); }
                    else { for (int r = n; r >= Sx + 1; --r) Ptest.push_back(r); }
                }
            }
            if (!isSubseq(Ptest, qseq)) continue;

            vector<pair<int,int>> pathCand;
            vector<int> PCand;
            if (buildPlan(downFirst, secondAsc, pathCand, PCand)) {
                // double-check subsequence still holds (should)
                if (!isSubseq(PCand, qseq)) {
                    continue;
                }
                cout << "YES\n";
                cout << (int)pathCand.size() << "\n";
                for (auto &pt : pathCand) {
                    cout << pt.first << " " << pt.second << "\n";
                }
                return;
            }
        }

        cout << "NO\n";
    }
};

int main() {
    Solver solver;
    solver.solve();
    return 0;
}