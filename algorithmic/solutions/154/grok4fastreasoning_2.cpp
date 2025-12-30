#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N;
    cin >> N;
    vector<int> petx(N), pety(N), pet_type(N);
    for (int i = 0; i < N; i++) {
        cin >> petx[i] >> pety[i] >> pet_type[i];
    }
    int M;
    cin >> M;
    vector<int> humx(M), humy(M);
    for (int i = 0; i < M; i++) {
        cin >> humx[i] >> humy[i];
    }
    const int SZ = 30;
    bool passable[32][32];
    memset(passable, 0, sizeof(passable));
    for (int i = 1; i <= SZ; i++) {
        for (int j = 1; j <= SZ; j++) {
            passable[i][j] = true;
        }
    }
    int ddx[4] = {-1, 1, 0, 0};
    int ddy[4] = {0, 0, -1, 1};
    string dirs = "udlr";
    for (int t = 0; t < 300; t++) {
        string acts(M, '.');
        set<pair<int, int>> block_set;
        for (int i = 0; i < M; i++) {
            int x = humx[i], y = humy[i];
            bool did_block = false;
            for (int d = 0; d < 4; d++) {
                int tx = x + ddx[d];
                int ty = y + ddy[d];
                if (tx < 1 || tx > SZ || ty < 1 || ty > SZ) continue;
                if (!passable[tx][ty]) continue;
                // check no pet or human at tx,ty
                bool has_ph = false;
                for (int j = 0; j < N; j++) {
                    if (petx[j] == tx && pety[j] == ty) {
                        has_ph = true;
                        break;
                    }
                }
                if (!has_ph) {
                    for (int j = 0; j < M; j++) {
                        if (humx[j] == tx && humy[j] == ty) {
                            has_ph = true;
                            break;
                        }
                    }
                }
                if (has_ph) continue;
                // check no pet adjacent to tx,ty
                bool adj_pet = false;
                for (int dd = 0; dd < 4 && !adj_pet; dd++) {
                    int ax = tx + ddx[dd];
                    int ay = ty + ddy[dd];
                    if (ax < 1 || ax > SZ || ay < 1 || ay > SZ) continue;
                    for (int j = 0; j < N; j++) {
                        if (petx[j] == ax && pety[j] == ay) {
                            adj_pet = true;
                            break;
                        }
                    }
                }
                if (adj_pet) continue;
                // can block
                acts[i] = dirs[d];
                block_set.insert({tx, ty});
                did_block = true;
                break;
            }
        }
        // output
        cout << acts << '\n';
        cout.flush();
        // apply blocks
        for (auto [bx, by] : block_set) {
            passable[bx][by] = false;
        }
        // no moves in this strategy
        // read pet moves
        vector<string> pms(N);
        for (int i = 0; i < N; i++) {
            cin >> pms[i];
        }
        // apply pet moves
        for (int i = 0; i < N; i++) {
            int cx = petx[i], cy = pety[i];
            for (char dir : pms[i]) {
                if (dir == 'U') cx--;
                else if (dir == 'D') cx++;
                else if (dir == 'L') cy--;
                else if (dir == 'R') cy++;
                petx[i] = cx;
                pety[i] = cy;
            }
        }
    }
    return 0;
}