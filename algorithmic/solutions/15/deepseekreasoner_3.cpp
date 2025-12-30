#include <bits/stdc++.h>
using namespace std;

vector<int> apply_operation(const vector<int>& p, int x, int y, vector<pair<int,int>>& moves) {
    int n = p.size();
    vector<int> q(n);
    int idx = 0;
    // suffix
    for (int i = n - y; i < n; ++i) q[idx++] = p[i];
    // middle
    for (int i = x; i < n - y; ++i) q[idx++] = p[i];
    // prefix
    for (int i = 0; i < x; ++i) q[idx++] = p[i];
    moves.emplace_back(x, y);
    return q;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
    }

    vector<pair<int,int>> moves;

    if (n == 3) {
        // Only one possible operation: x=1, y=1
        vector<int> q = p;
        // apply operation
        vector<int> r = {q[2], q[1], q[0]};
        if (r < p) {
            p = r;
            moves.emplace_back(1, 1);
        }
    } else {
        // n >= 4
        auto is_sorted = [&]() {
            for (int i = 0; i < n; ++i)
                if (p[i] != i + 1) return false;
            return true;
        };

        while (moves.size() < 4 * n && !is_sorted()) {
            // find first wrong position
            int target = -1;
            for (int i = 0; i < n; ++i) {
                if (p[i] != i + 1) {
                    target = i + 1;
                    break;
                }
            }
            // find current position of target
            int pos = -1;
            for (int i = 0; i < n; ++i) {
                if (p[i] == target) {
                    pos = i + 1;
                    break;
                }
            }

            bool moved = false;
            if (pos < target) {
                if (target - pos > 1) {
                    int x = n - target + pos;
                    int y = 1;
                    if (x > 0 && y > 0 && x + y < n) {
                        p = apply_operation(p, x, y, moves);
                        moved = true;
                    }
                } else { // target - pos == 1
                    if (pos < n - 1) {
                        // try three-move sequence
                        int x1 = pos, y1 = 1;
                        if (x1 > 0 && y1 > 0 && x1 + y1 < n) {
                            p = apply_operation(p, x1, y1, moves);
                            if (moves.size() >= 4 * n) break;
                            int x2 = 1, y2 = 1;
                            if (x2 > 0 && y2 > 0 && x2 + y2 < n) {
                                p = apply_operation(p, x2, y2, moves);
                                if (moves.size() >= 4 * n) break;
                                int x3 = n - target + 1, y3 = 1;
                                if (x3 > 0 && y3 > 0 && x3 + y3 < n) {
                                    p = apply_operation(p, x3, y3, moves);
                                    moved = true;
                                }
                            }
                        }
                    }
                }
            } else if (pos > target) {
                if (pos > 2) {
                    int y1 = n - pos + 1, x1 = 1;
                    if (x1 > 0 && y1 > 0 && x1 + y1 < n) {
                        p = apply_operation(p, x1, y1, moves);
                        if (moves.size() >= 4 * n) break;
                        int x2 = n - target + 1, y2 = 1;
                        if (x2 > 0 && y2 > 0 && x2 + y2 < n) {
                            p = apply_operation(p, x2, y2, moves);
                            moved = true;
                        }
                    }
                } else if (pos == 2 && target == 1) {
                    int x1 = 1, y1 = 2;
                    if (x1 > 0 && y1 > 0 && x1 + y1 < n) {
                        p = apply_operation(p, x1, y1, moves);
                        if (moves.size() >= 4 * n) break;
                        int x2 = 1, y2 = n - 2;
                        if (x2 > 0 && y2 > 0 && x2 + y2 < n) {
                            p = apply_operation(p, x2, y2, moves);
                            moved = true;
                        }
                    }
                }
            }

            if (!moved) {
                // fallback: any valid move
                for (int x = 1; x < n; ++x) {
                    for (int y = 1; x + y < n; ++y) {
                        p = apply_operation(p, x, y, moves);
                        moved = true;
                        break;
                    }
                    if (moved) break;
                }
            }
        }
    }

    cout << moves.size() << '\n';
    for (auto [x, y] : moves) {
        cout << x << ' ' << y << '\n';
    }

    return 0;
}