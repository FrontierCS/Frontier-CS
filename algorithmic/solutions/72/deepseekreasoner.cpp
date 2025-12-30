#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    int len;
    bool vert;
};

int n;
vector<Vehicle> veh;

uint64_t encode(const vector<int>& pos) {
    uint64_t key = 0;
    for (int i = 1; i <= n; ++i) {
        key = (key << 6) | (pos[i] & 0x3F);
    }
    return key;
}

void decode(uint64_t key, vector<int>& pos) {
    for (int i = n; i >= 1; --i) {
        int shift = 6 * (n - i);
        pos[i] = (key >> shift) & 0x3F;
    }
}

bool occupied_by_other(int r, int c, int exclude_id, const vector<int>& pos) {
    for (int j = 1; j <= n; ++j) {
        if (j == exclude_id) continue;
        int rj = pos[j] / 6, cj = pos[j] % 6;
        if (!veh[j].vert) {
            if (r == rj && c >= cj && c < cj + veh[j].len) return true;
        } else {
            if (c == cj && r >= rj && r < rj + veh[j].len) return true;
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int board[6][6];
    int max_id = 0;
    for (int i = 0; i < 6; ++i) {
        for (int j = 0; j < 6; ++j) {
            cin >> board[i][j];
            max_id = max(max_id, board[i][j]);
        }
    }
    n = max_id;
    veh.resize(n + 1);
    vector<int> init_pos(n + 1);

    for (int id = 1; id <= n; ++id) {
        int min_r = 6, max_r = -1, min_c = 6, max_c = -1;
        for (int i = 0; i < 6; ++i) {
            for (int j = 0; j < 6; ++j) {
                if (board[i][j] == id) {
                    min_r = min(min_r, i);
                    max_r = max(max_r, i);
                    min_c = min(min_c, j);
                    max_c = max(max_c, j);
                }
            }
        }
        if (min_r == max_r) {
            veh[id].vert = false;
            veh[id].len = max_c - min_c + 1;
            init_pos[id] = min_r * 6 + min_c;
        } else {
            veh[id].vert = true;
            veh[id].len = max_r - min_r + 1;
            init_pos[id] = min_r * 6 + min_c;