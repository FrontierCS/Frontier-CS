#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    vector<int> px(N), py(N), pt(N);
    for (int i = 0; i < N; i++) {
        cin >> px[i] >> py[i] >> pt[i];
    }
    int M;
    cin >> M;
    vector<int> hx(M), hy(M);
    for (int i = 0; i < M; i++) {
        cin >> hx[i] >> hy[i];
    }
    vector<vector<bool>> passable(31, vector<bool>(31, true));
    int DX[4] = {-1, 1, 0, 0};
    int DY[4] = {0, 0, -1, 1};
    vector<int> target_y(M);
    if (M == 1) {
        target_y[0] = 15;
    } else {
        int spacing = 29 / (M - 1);
        for (int i = 0; i < M; i++) {
            target_y[i] = 1 + i * spacing;
        }
    }
    for (int turn = 0; turn < 300; turn++) {
        string actions(M, '.');
        for (int i = 0; i < M; i++) {
            int cx = hx[i], cy = hy[i];
            int goalx = 30, goaly = target_y[i];
            if (cx == goalx && cy == goaly) {
                // try block up
                int btx = cx - 1;
                int bty = cy;
                bool occ = false;
                for (int j = 0; j < N; j++) {
                    if (px[j] == btx && py[j] == bty) {
                        occ = true;
                        break;
                    }
                }
                if (!occ) {
                    for (int j = 0; j < M; j++) {
                        if (hx[j] == btx && hy[j] == bty) {
                            occ = true;
                            break;
                        }
                    }
                }
                if (occ) {
                    actions[i] = '.';
                    continue;
                }
                bool npet = false;
                for (int k = 0; k < 4; k++) {
                    int ax = btx + DX[k];
                    int ay = bty + DY[k];
                    if (ax >= 1 && ax <= 30 && ay >= 1 && ay <= 30) {
                        for (int j = 0; j < N; j++) {
                            if (px[j] == ax && py[j] == ay) {
                                npet = true;
                                break;
                            }
                        }
                        if (npet) break;
                    }
                }
                if (npet) {
                    actions[i] = '.';
                } else {
                    actions[i] = 'u';
                }
            } else {
                // move towards
                int delx = goalx - cx;
                int dely = goaly - cy;
                char ch = '.';
                if (delx != 0) {
                    ch = (delx > 0 ? 'D' : 'U');
                } else if (dely != 0) {
                    ch = (dely > 0 ? 'R' : 'L');
                }
                actions[i] = ch;
            }
        }
        cout << actions << endl;
        cout.flush();
        vector<string> pet_moves(N);
        for (int i = 0; i < N; i++) {
            cin >> pet_moves[i];
        }
        // simulate humans
        set<pair<int, int>> will_block;
        // collect blocks
        for (int i = 0; i < M; i++) {
            char act = actions[i];
            if (islower(act)) {
                int d = -1;
                if (act == 'u') d = 0;
                else if (act == 'd') d = 1;
                else if (act == 'l') d = 2;
                else if (act == 'r') d = 3;
                int tx = hx[i] + DX[d];
                int ty = hy[i] + DY[d];
                if (tx < 1 || tx > 30 || ty < 1 || ty > 30) continue;
                // check occ
                bool occ = false;
                for (int j = 0; j < N; j++) {
                    if (px[j] == tx && py[j] == ty) {
                        occ = true;
                        break;
                    }
                }
                if (!occ) {
                    for (int j = 0; j < M; j++) {
                        if (hx[j] == tx && hy[j] == ty) {
                            occ = true;
                            break;
                        }
                    }
                }
                if (occ) continue;
                // check near pet
                bool npet = false;
                for (int k = 0; k < 4; k++) {
                    int ax = tx + DX[k];
                    int ay = ty + DY[k];
                    if (ax >= 1 && ax <= 30 && ay >= 1 && ay <= 30) {
                        bool found = false;
                        for (int j = 0; j < N; j++) {
                            if (px[j] == ax && py[j] == ay) {
                                found = true;
                                break;
                            }
                        }
                        if (found) {
                            npet = true;
                            break;
                        }
                    }
                }
                if (npet) continue;
                will_block.insert({tx, ty});
            }
        }
        // now moves
        vector<int> new_hx(M), new_hy(M);
        for (int i = 0; i < M; i++) {
            char act = actions[i];
            bool is_move = isupper(act);
            int nd = -1;
            if (is_move) {
                if (act == 'U') nd = 0;
                else if (act == 'D') nd = 1;
                else if (act == 'L') nd = 2;
                else if (act == 'R') nd = 3;
            }
            if (!is_move || nd == -1) {
                new_hx[i] = hx[i];
                new_hy[i] = hy[i];
                continue;
            }
            int tx = hx[i] + DX[nd];
            int ty = hy[i] + DY[nd];
            bool can = (tx >= 1 && tx <= 30 && ty >= 1 && ty <= 30 &&
                        passable[tx][ty] &&
                        will_block.find({tx, ty}) == will_block.end());
            if (can) {
                new_hx[i] = tx;
                new_hy[i] = ty;
            } else {
                new_hx[i] = hx[i];
                new_hy[i] = hy[i];
            }
        }
        hx = new_hx;
        hy = new_hy;
        // apply blocks
        for (auto p : will_block) {
            passable[p.first][p.second] = false;
        }
        // pets
        for (int i = 0; i < N; i++) {
            int cx = px[i], cy = py[i];
            string mv = pet_moves[i];
            if (mv == ".") continue;
            for (char c : mv) {
                int nd = -1;
                if (c == 'U') nd = 0;
                else if (c == 'D') nd = 1;
                else if (c == 'L') nd = 2;
                else if (c == 'R') nd = 3;
                if (nd == -1) continue;
                int nx = cx + DX[nd];
                int ny = cy + DY[nd];
                if (nx >= 1 && nx <= 30 && ny >= 1 && ny <= 30 && passable[nx][ny]) {
                    cx = nx;
                    cy = ny;
                }
            }
            px[i] = cx;
            py[i] = cy;
        }
    }
    return 0;
}