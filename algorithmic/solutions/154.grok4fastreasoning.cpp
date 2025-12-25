#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    cin >> N;
    vector<int> pposx(N), pposy(N), ptype(N);
    for (int i = 0; i < N; i++) {
        cin >> pposx[i] >> pposy[i] >> ptype[i];
    }
    int M;
    cin >> M;
    vector<int> hposx(M), hposy(M);
    for (int i = 0; i < M; i++) {
        cin >> hposx[i] >> hposy[i];
    }
    vector<vector<bool>> passable(31, vector<bool>(31, true));
    int DX[4] = {-1, 1, 0, 0};
    int DY[4] = {0, 0, -1, 1};
    char DCHAR[4] = {'U', 'D', 'L', 'R'};
    char BLOCKCHAR[4] = {'u', 'd', 'l', 'r'};
    int TX = 30, TY = 30;
    for (int turn = 0; turn < 300; turn++) {
        vector<char> temp_act(M, '.');
        set<pair<int, int>> temp_blocks;
        for (int i = 0; i < M; i++) {
            int x = hposx[i], y = hposy[i];
            bool at_target = (x == TX && y == TY);
            bool did_something = false;
            if (!at_target) {
                int cur_dist = abs(x - TX) + abs(y - TY);
                int best_d = cur_dist;
                int best_k = -1;
                for (int k = 0; k < 4; k++) {
                    int nx = x + DX[k], ny = y + DY[k];
                    if (nx < 1 || nx > 30 || ny < 1 || ny > 30) continue;
                    if (!passable[nx][ny]) continue;
                    int nd = abs(nx - TX) + abs(ny - TY);
                    if (nd < best_d) {
                        best_d = nd;
                        best_k = k;
                    }
                }
                if (best_k != -1 && best_d < cur_dist) {
                    temp_act[i] = DCHAR[best_k];
                    did_something = true;
                }
            }
            if (!did_something) {
                bool did_block = false;
                for (int k = 0; k < 4 && !did_block; k++) {
                    int tx = x + DX[k], ty = y + DY[k];
                    if (tx < 1 || tx > 30 || ty < 1 || ty > 30) continue;
                    bool has_occ = false;
                    for (int j = 0; j < M; j++) {
                        if (hposx[j] == tx && hposy[j] == ty) {
                            has_occ = true;
                            break;
                        }
                    }
                    if (has_occ) continue;
                    for (int j = 0; j < N; j++) {
                        if (pposx[j] == tx && pposy[j] == ty) {
                            has_occ = true;
                            break;
                        }
                    }
                    if (has_occ) continue;
                    bool adj_pet = false;
                    for (int d = 0; d < 4 && !adj_pet; d++) {
                        int ax = tx + DX[d], ay = ty + DY[d];
                        if (ax < 1 || ax > 30 || ay < 1 || ay > 30) continue;
                        for (int j = 0; j < N; j++) {
                            if (pposx[j] == ax && pposy[j] == ay) {
                                adj_pet = true;
                                break;
                            }
                        }
                    }
                    if (!adj_pet) {
                        temp_act[i] = BLOCKCHAR[k];
                        temp_blocks.insert({tx, ty});
                        did_block = true;
                    }
                }
                if (!did_block) {
                    temp_act[i] = '.';
                }
            }
        }
        // Validate moves against all temp_blocks
        for (int i = 0; i < M; i++) {
            char a = temp_act[i];
            if (a != 'U' && a != 'D' && a != 'L' && a != 'R') continue;
            int k = (a == 'U' ? 0 : a == 'D' ? 1 : a == 'L' ? 2 : 3);
            int nx = hposx[i] + DX[k], ny = hposy[i] + DY[k];
            bool valid = (nx >= 1 && nx <= 30 && ny >= 1 && ny <= 30 &&
                          passable[nx][ny] && temp_blocks.find({nx, ny}) == temp_blocks.end());
            if (!valid) {
                temp_act[i] = '.';
                // Fallback to block
                int x = hposx[i], y = hposy[i];
                bool did_block = false;
                for (int kk = 0; kk < 4 && !did_block; kk++) {
                    int tx = x + DX[kk], ty = y + DY[kk];
                    if (tx < 1 || tx > 30 || ty < 1 || ty > 30) continue;
                    bool has_occ = false;
                    for (int j = 0; j < M; j++) {
                        if (hposx[j] == tx && hposy[j] == ty) {
                            has_occ = true;
                            break;
                        }
                    }
                    if (has_occ) continue;
                    for (int j = 0; j < N; j++) {
                        if (pposx[j] == tx && pposy[j] == ty) {
                            has_occ = true;
                            break;
                        }
                    }
                    if (has_occ) continue;
                    bool adj_pet = false;
                    for (int d = 0; d < 4 && !adj_pet; d++) {
                        int ax = tx + DX[d], ay = ty + DY[d];
                        if (ax < 1 || ax > 30 || ay < 1 || ay > 30) continue;
                        for (int j = 0; j < N; j++) {
                            if (pposx[j] == ax && pposy[j] == ay) {
                                adj_pet = true;
                                break;
                            }
                        }
                    }
                    if (!adj_pet) {
                        temp_act[i] = BLOCKCHAR[kk];
                        temp_blocks.insert({tx, ty});
                        did_block = true;
                    }
                }
            }
        }
        // Output
        string out_str = "";
        for (char c : temp_act) out_str += c;
        cout << out_str << endl;
        // Apply moves
        vector<int> new_hx(M), new_hy(M);
        set<pair<int, int>> intended_blocks = temp_blocks;
        for (int i = 0; i < M; i++) {
            char a = temp_act[i];
            int nx = hposx[i], ny = hposy[i];
            bool valid_move = true;
            if (a == 'U' || a == 'D' || a == 'L' || a == 'R') {
                int k = (a == 'U' ? 0 : a == 'D' ? 1 : a == 'L' ? 2 : 3);
                nx = hposx[i] + DX[k];
                ny = hposy[i] + DY[k];
                if (nx < 1 || nx > 30 || ny < 1 || ny > 30) valid_move = false;
                else if (!passable[nx][ny]) valid_move = false;
                else if (intended_blocks.count({nx, ny})) valid_move = false;
            }
            if (!valid_move) {
                nx = hposx[i];
                ny = hposy[i];
            }
            new_hx[i] = nx;
            new_hy[i] = ny;
        }
        hposx = new_hx;
        hposy = new_hy;
        // Apply blocks
        for (auto p : intended_blocks) {
            passable[p.first][p.second] = false;
        }
        // Read and apply pet moves
        for (int i = 0; i < N; i++) {
            string mov;
            cin >> mov;
            int cx = pposx[i], cy = pposy[i];
            for (char c : mov) {
                int dk = -1;
                if (c == 'U') dk = 0;
                else if (c == 'D') dk = 1;
                else if (c == 'L') dk = 2;
                else if (c == 'R') dk = 3;
                if (dk != -1) {
                    int nx = cx + DX[dk], ny = cy + DY[dk];
                    if (nx >= 1 && nx <= 30 && ny >= 1 && ny <= 30 && passable[nx][ny]) {
                        cx = nx;
                        cy = ny;
                    }
                }
            }
            pposx[i] = cx;
            pposy[i] = cy;
        }
    }
    return 0;
}