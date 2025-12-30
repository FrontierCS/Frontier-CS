#include <bits/stdc++.h>
using namespace std;

const int MAXN = 65;
bool has[MAXN][MAXN];
int w[MAXN][MAXN];
bool h_edge[MAXN][MAXN];
bool v_edge[MAXN][MAXN];
bool d1_edge[MAXN][MAXN];
bool d2_edge[MAXN][MAXN];

struct Best {
    int score = -1;
    int type = -1;
    int p1 = -1, p2 = -1, mss = -1;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int N, M;
    cin >> N >> M;
    int c = (N - 1) / 2;
    for (int x = 0; x < N; x++) {
        for (int y = 0; y < N; y++) {
            w[x][y] = (x - c) * (x - c) + (y - c) * (y - c) + 1;
        }
    }
    memset(has, 0, sizeof(has));
    memset(h_edge, 0, sizeof(h_edge));
    memset(v_edge, 0, sizeof(v_edge));
    memset(d1_edge, 0, sizeof(d1_edge));
    memset(d2_edge, 0, sizeof(d2_edge));
    for (int i = 0; i < M; i++) {
        int x, y;
        cin >> x >> y;
        has[x][y] = true;
    }
    vector<vector<pair<int, int>>> ops;
    while (true) {
        Best bst;
        // Scan axis-aligned 1x1
        for (int i = 0; i < N - 1; i++) {
            for (int j = 0; j < N - 1; j++) {
                int cnt = 0;
                int miss = -1;
                if (has[i][j]) cnt++; else if (miss == -1) miss = 0;
                if (has[i + 1][j]) cnt++; else if (miss == -1) miss = 1;
                if (has[i][j + 1]) cnt++; else if (miss == -1) miss = 2;
                if (has[i + 1][j + 1]) cnt++; else if (miss == -1) miss = 3;
                if (cnt == 3 && miss != -1) {
                    if (!h_edge[i][j] && !h_edge[i][j + 1] && !v_edge[i][j] && !v_edge[i + 1][j]) {
                        int px = i + ((miss == 1 || miss == 3) ? 1 : 0);
                        int py = j + ((miss == 2 || miss == 3) ? 1 : 0);
                        int sc = w[px][py];
                        if (sc > bst.score) {
                            bst.score = sc;
                            bst.type = 0;
                            bst.p1 = i;
                            bst.p2 = j;
                            bst.mss = miss;
                        }
                    }
                }
            }
        }
        // Scan 45-degree small
        for (int a = 1; a < N - 1; a++) {
            for (int b = 1; b < N - 1; b++) {
                int cnt = has[a - 1][b] + has[a + 1][b] + has[a][b + 1] + has[a][b - 1];
                if (cnt == 3) {
                    int miss = -1;
                    if (!has[a - 1][b]) miss = 0;
                    else if (!has[a + 1][b]) miss = 1;
                    else if (!has[a][b + 1]) miss = 2;
                    else miss = 3;
                    if (!d1_edge[a - 1][b] && !d2_edge[a][b + 1] && !d1_edge[a][b - 1] && !d2_edge[a - 1][b]) {
                        int px, py;
                        if (miss == 0) { px = a - 1; py = b; }
                        else if (miss == 1) { px = a + 1; py = b; }
                        else if (miss == 2) { px = a; py = b + 1; }
                        else { px = a; py = b - 1; }
                        int sc = w[px][py];
                        if (sc > bst.score) {
                            bst.score = sc;
                            bst.type = 1;
                            bst.p1 = a;
                            bst.p2 = b;
                            bst.mss = miss;
                        }
                    }
                }
            }
        }
        if (bst.score == -1) break;
        // Perform the move
        vector<pair<int, int>> pts(4);
        int px, py;
        if (bst.type == 0) {
            int i = bst.p1, j = bst.p2;
            int ms = bst.mss;
            if (ms == 0) {
                pts[0] = {i, j};
                pts[1] = {i + 1, j};
                pts[2] = {i + 1, j + 1};
                pts[3] = {i, j + 1};
                px = i; py = j;
            } else if (ms == 1) {
                pts[0] = {i + 1, j};
                pts[1] = {i + 1, j + 1};
                pts[2] = {i, j + 1};
                pts[3] = {i, j};
                px = i + 1; py = j;
            } else if (ms == 2) {
                pts[0] = {i, j + 1};
                pts[1] = {i + 1, j + 1};
                pts[2] = {i + 1, j};
                pts[3] = {i, j};
                px = i; py = j + 1;
            } else {
                pts[0] = {i + 1, j + 1};
                pts[1] = {i, j + 1};
                pts[2] = {i, j};
                pts[3] = {i + 1, j};
                px = i + 1; py = j + 1;
            }
            h_edge[i][j] = true;
            h_edge[i][j + 1] = true;
            v_edge[i][j] = true;
            v_edge[i + 1][j] = true;
        } else {
            int a = bst.p1, b = bst.p2;
            int ms = bst.mss;
            if (ms == 0) {
                pts[0] = {a - 1, b};
                pts[1] = {a, b + 1};
                pts[2] = {a + 1, b};
                pts[3] = {a, b - 1};
                px = a - 1; py = b;
            } else if (ms == 1) {
                pts[0] = {a + 1, b};
                pts[1] = {a, b - 1};
                pts[2] = {a - 1, b};
                pts[3] = {a, b + 1};
                px = a + 1; py = b;
            } else if (ms == 2) {
                pts[0] = {a, b + 1};
                pts[1] = {a + 1, b};
                pts[2] = {a, b - 1};
                pts[3] = {a - 1, b};
                px = a; py = b + 1;
            } else {
                pts[0] = {a, b - 1};
                pts[1] = {a - 1, b};
                pts[2] = {a, b + 1};
                pts[3] = {a + 1, b};
                px = a; py = b - 1;
            }
            d1_edge[a - 1][b] = true;
            d2_edge[a][b + 1] = true;
            d1_edge[a][b - 1] = true;
            d2_edge[a - 1][b] = true;
        }
        has[px][py] = true;
        ops.push_back(pts);
    }
    cout << ops.size() << "\n";
    for (auto& op : ops) {
        for (auto& p : op) {
            cout << p.first << " " << p.second << " ";
        }
        cout << "\n";
    }
}