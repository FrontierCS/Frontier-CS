#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    vector<int> ptype(N);
    vector<pair<int, int>> ppos(N);
    for (int i = 0; i < N; i++) {
        int x, y, t;
        cin >> x >> y >> t;
        ppos[i] = {x, y};
        ptype[i] = t;
    }
    int M;
    cin >> M;
    vector<pair<int, int>> hpos(M);
    for (int i = 0; i < M; i++) {
        int x, y;
        cin >> x >> y;
        hpos[i] = {x, y};
    }
    bool blocked[31][31];
    memset(blocked, 0, sizeof(blocked));
    int DX[4] = {-1, 1, 0, 0};
    int DY[4] = {0, 0, -1, 1};
    char BLOCK[4] = {'u', 'd', 'l', 'r'};
    for (int turn = 0; turn < 300; turn++) {
        string actions(M, '.');
        vector<pair<int, int>> block_targets(M, {-1, -1});
        for (int i = 0; i < M; i++) {
            int x = hpos[i].first, y = hpos[i].second;
            bool did = false;
            for (int d = 0; d < 4; d++) {
                int nx = x + DX[d], ny = y + DY[d];
                if (nx < 1 || nx > 30 || ny < 1 || ny > 30) continue;
                bool occupied = false;
                for (int j = 0; j < M; j++) {
                    if (hpos[j].first == nx && hpos[j].second == ny) {
                        occupied = true;
                        break;
                    }
                }
                if (occupied) continue;
                for (int j = 0; j < N; j++) {
                    if (ppos[j].first == nx && ppos[j].second == ny) {
                        occupied = true;
                        break;
                    }
                }
                if (occupied) continue;
                bool adj_pet = false;
                for (int e = 0; e < 4; e++) {
                    int ex = nx + DX[e], ey = ny + DY[e];
                    if (ex >= 1 && ex <= 30 && ey >= 1 && ey <= 30) {
                        for (int j = 0; j < N; j++) {
                            if (ppos[j].first == ex && ppos[j].second == ey) {
                                adj_pet = true;
                                break;
                            }
                        }
                        if (adj_pet) break;
                    }
                }
                if (adj_pet) continue;
                actions[i] = BLOCK[d];
                block_targets[i] = {nx, ny};
                did = true;
                break;
            }
        }
        cout << actions << endl;
        cout.flush();
        vector<string> petmoves(N);
        for (int i = 0; i < N; i++) {
            cin >> petmoves[i];
        }
        set<pair<int, int>> new_blocks;
        for (int i = 0; i < M; i++) {
            if (block_targets[i].first != -1) {
                new_blocks.insert(block_targets[i]);
            }
        }
        for (auto [bx, by] : new_blocks) {
            blocked[bx][by] = true;
        }
        for (int i = 0; i < M; i++) {
            char ac = actions[i];
            if (ac == 'u' || ac == 'd' || ac == 'l' || ac == 'r') {
                // position unchanged
            } else if (ac == '.') {
                // stay
            } else {
                // no moves implemented yet
            }
        }
        for (int i = 0; i < N; i++) {
            int x = ppos[i].first, y = ppos[i].second;
            for (char c : petmoves[i]) {
                if (c == 'U') x--;
                else if (c == 'D') x++;
                else if (c == 'L') y--;
                else if (c == 'R') y++;
                x = max(1, min(30, x));
                y = max(1, min(30, y));
            }
            ppos[i] = {x, y};
        }
    }
    return 0;
}