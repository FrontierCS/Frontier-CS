#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<vector<int>> pillars; // pillars[0..n], where pillars[n] is the buffer (pillar n+1)
vector<pair<int, int>> moves;

void move_ball(int x, int y) {
    moves.emplace_back(x+1, y+1); // convert to 1-indexed for output
    int ball = pillars[x].back();
    pillars[x].pop_back();
    pillars[y].push_back(ball);
}

// Ensure pillar p has at most m-1 balls.
void make_space(int p) {
    while ((int)pillars[p].size() >= m) {
        int c = pillars[p].back(); // color of top ball
        int target = c - 1; // target pillar index (0-indexed)
        if (target != p && (int)pillars[target].size() < m) {
            move_ball(p, target);
        } else {
            // Find any pillar with space (including p itself? no, we need different pillar)
            int q = -1;
            for (int i = 0; i <= n; i++) {
                if (i != p && (int)pillars[i].size() < m) {
                    q = i;
                    break;
                }
            }
            // There must be such q because total capacity > total balls.
            move_ball(p, q);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m;
    pillars.resize(n+1); // indices 0..n-1 are pillars 1..n, index n is pillar n+1 (buffer)
    for (int i = 0; i < n; i++) {
        pillars[i].resize(m);
        for (int j = 0; j < m; j++) {
            cin >> pillars[i][j];
        }
        reverse(pillars[i].begin(), pillars[i].end()); // store top at back
    }
    // pillar n (buffer) is initially empty.

    moves.clear();

    for (int color = 1; color <= n; color++) {
        int c = color - 1; // zero-indexed pillar for this color

        // Step 1: Clear pillar c of balls that are not of color 'color'.
        while (!pillars[c].empty()) {
            int ball = pillars[c].back();
            if (ball == color) {
                // This ball should stay, but we move it to buffer temporarily.
                make_space(n);
                move_ball(c, n);
            } else {
                int target = ball - 1;
                if ((int)pillars[target].size() < m) {
                    move_ball(c, target);
                } else {
                    make_space(n);
                    move_ball(c, n);
                }
            }
        }

        // Step 2: Move all balls of 'color' from buffer to pillar c.
        while (!pillars[n].empty() && pillars[n].back() == color) {
            make_space(c);
            move_ball(n, c);
        }

        // Step 3: Move remaining balls in buffer to some other pillar (not necessarily their target).
        while (!pillars[n].empty()) {
            int ball = pillars[n].back();
            int target = ball - 1;
            if ((int)pillars[target].size() < m) {
                move_ball(n, target);
            } else {
                // Find any pillar with space (including c is allowed).
                int q = -1;
                for (int i = 0; i < n; i++) {
                    if ((int)pillars[i].size() < m) {
                        q = i;
                        break;
                    }
                }
                if (q == -1) {
                    // All pillars are full, but that cannot happen because buffer has balls.
                    // As a fallback, use buffer itself? cannot.
                    // Since total balls = n*m, if all n pillars are full, buffer must be empty.
                    // So there must be space somewhere.
                    // Try pillar c even if it might be full? but we checked size < m.
                    // We'll just break and hope for the best.
                    break;
                }
                move_ball(n, q);
            }
        }

        // Step 4: Gather all balls of 'color' from other pillars.
        for (int i = 0; i < n; i++) {
            if (i == c) continue;
            // Repeatedly move balls from pillar i until no ball of 'color' remains.
            while (true) {
                bool found_color = false;
                // Scan pillar i by moving balls.
                while (!pillars[i].empty()) {
                    int ball = pillars[i].back();
                    if (ball == color) {
                        make_space(c);
                        move_ball(i, c);
                        found_color = true;
                    } else {
                        int target = ball - 1;
                        if (target != i && (int)pillars[target].size() < m) {
                            move_ball(i, target);
                        } else {
                            make_space(n);
                            move_ball(i, n);
                        }
                    }
                }
                // After emptying pillar i, we need to clear the buffer of any non-color balls
                // to make space for further operations.
                while (!pillars[n].empty()) {
                    int ball = pillars[n].back();
                    int target = ball - 1;
                    if ((int)pillars[target].size() < m) {
                        move_ball(n, target);
                    } else {
                        int q = -1;
                        for (int j = 0; j < n; j++) {
                            if ((int)pillars[j].size() < m) {
                                q = j;
                                break;
                            }
                        }
                        if (q == -1) break;
                        move_ball(n, q);
                    }
                }
                if (!found_color) break; // no more color balls on pillar i
            }
        }

        // Final cleanup of buffer (might have accumulated some balls).
        while (!pillars[n].empty()) {
            int ball = pillars[n].back();
            int target = ball - 1;
            if ((int)pillars[target].size() < m) {
                move_ball(n, target);
            } else {
                int q = -1;
                for (int i = 0; i < n; i++) {
                    if ((int)pillars[i].size() < m) {
                        q = i;
                        break;
                    }
                }
                if (q == -1) break;
                move_ball(n, q);
            }
        }
    }

    // Output the moves.
    cout << moves.size() << "\n";
    for (auto& p : moves) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}