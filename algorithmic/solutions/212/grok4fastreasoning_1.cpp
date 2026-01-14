#include <bits/stdc++.h>
using namespace std;

int n, m, L, R, Sx, Sy, Lq, s;
int qv[41];
int key_idx[41];
bool found;
vector<pair<int, int>> best_path;
vector<int> pi;
bitset<41> row_visited;
bool right_avail, left_avail;

struct State {
    int x, y;
};

bool valid(int x, int y) {
    return 1 <= x && x <= n && 1 <= y && y <= m;
}

vector<pair<int, int>> get_neighbors(int x, int y) {
    vector<pair<int, int>> res;
    int dx[4] = {-1, 0, 1, 0};
    int dy[4] = {0, 1, 0, -1};
    for (int d = 0; d < 4; d++) {
        int nx = x + dx[d], ny