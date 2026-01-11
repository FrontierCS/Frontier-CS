#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<stack<int>> pillars;
vector<pair<int,int>> moves;

void move_ball(int x, int y) {
    moves.push_back({x, y});
    int ball = pillars[x].top();
    pillars[x].pop();
    pillars[y].push(ball);
}

bool is_done() {
    map<int, int> color_pillar;
    for (int i = 1; i <= n+1; i++) {
        stack<int> s = pillars[i];
        vector<int> balls;
        while (!s.empty()) {
            balls.push_back(s.top());
            s.pop();
        }
        for (int ball : balls) {
            if (color_pillar.count(ball)) {
                if (color_pillar[ball] != i) return false;
            } else {
                color_pillar[ball] = i;
            }
        }
    }
    return true;
}

int main() {
    cin >> n >> m;
    pillars.resize(n+2);
    for (int i = 1; i <= n; i++) {
        vector<int> temp(m);
        for (int j = 0; j < m; j++) {
            cin >> temp[j];
        }
        // push in reverse so that top of stack is the top ball
        for (int j = m-1; j >= 0; j--) {
            pillars[i].push(temp[j]);
        }
    }

    int max_moves = 1e7;
    while (!is_done() && moves.size() < max_moves) {
        bool moved = false;
        for (int i = 1; i <= n+1; i++) {
            if (pillars[i].empty()) continue;
            int col = pillars[i].top();
            if (i == col) continue;
            if (pillars[col].size() < m) {
                move_ball(i, col);
                moved = true;
                break;
            } else {
                int topcol = pillars[col].top();
                if (topcol == col) {
                    if (pillars[n+1].size() < m) {
                        move_ball(col, n+1);
                        moved = true;
                        break;
                    } else {
                        for (int j = 1; j <= n+1; j++) {
                            if (j == n+1) continue;
                            if (pillars[j].size() < m) {
                                move_ball(n+1, j);
                                moved = true;
                                break;
                            }
                        }
                        if (moved) break;
                    }
                } else {
                    if (pillars[n+1].size() < m) {
                        move_ball(col, n+1);
                        moved = true;
                        break;
                    } else {
                        for (int j = 1; j <= n; j++) {
                            if (pillars[j].size() < m) {
                                move_ball(n+1, j);
                                moved = true;
                                break;
                            }
                        }
                        if (moved) break;
                    }
                }
            }
        }
        if (!moved) {
            for (int i = 1; i <= n; i++) {
                if (!pillars[i].empty() && pillars[i].top() == i && pillars[n+1].size() < m) {
                    move_ball(i, n+1);
                    moved = true;
                    break;
                }
            }
            if (!moved) {
                for (int i = 1; i <= n; i++) {
                    if (!pillars[i].empty() && pillars[n+1].size() < m) {
                        move_ball(i, n+1);
                        moved = true;
                        break;
                    }
                }
            }
        }
    }

    cout << moves.size() << endl;
    for (auto& p : moves) {
        cout << p.first << " " << p.second << endl;
    }

    return 0;
}