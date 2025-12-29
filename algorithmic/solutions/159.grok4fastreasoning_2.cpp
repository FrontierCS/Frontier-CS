#include <bits/stdc++.h>
using namespace std;

const int MAXN = 65;
bool has_dot[MAXN][MAXN];
bool hseg[MAXN][MAXN];
bool vseg[MAXN][MAXN];
bool d1seg[MAXN][MAXN];
bool d2seg[MAXN][MAXN];
double weight[MAXN][MAXN];

struct Move {
    int x[4];
    int y[4];
};

bool check_side(int ax, int ay, int bx, int by) {
    if (ax == bx && ay == by) return true;
    int dx = bx - ax;
    int dy = by - ay;
    int adx = abs(dx);
    int ady = abs(dy);
    int minx = min(ax, bx);
    if (ady == 0) {
        int y = ay;
        for (int i = 0; i < adx; i++) {
            if (hseg[y][minx + i]) return false;
        }
        return true;
    } else if (adx == 0) {
        int x = ax;
        int miny = min(ay, by);
        for (int i = 0; i < ady; i++) {
            if (vseg[x][miny + i]) return false;
        }
        return true;
    } else if (adx == ady && adx > 0) {
        if (dx == dy) {
            int miny = min(ay, by);
            for (int i = 0; i < adx; i++) {
                if (d1seg[minx + i][miny + i]) return false;
            }
            return true;
        } else if (dx == -dy) {
            int maxy = max(ay, by);
            for (int i = 0; i < adx; i++) {
                if (d2seg[minx + i][maxy - i]) return false;
            }
            return true;
        }
    }
    return false;
}

void draw_side(int ax, int ay, int bx, int by) {
    if (ax == bx && ay == by) return;
    int dx = bx - ax;
    int dy = by - ay;
    int adx = abs(dx);
    int ady = abs(dy);
    int minx = min(ax, bx);
    if (ady == 0) {
        int y = ay;
        for (int i = 0; i < adx; i++) hseg[y][minx + i] = true;
    } else if (adx == 0) {
        int x = ax;
        int miny = min(ay, by);
        for (int i = 0; i < ady; i++) vseg[x][miny + i] = true;
    } else if (adx == ady && adx > 0) {
        if (dx == dy) {
            int miny = min(ay, by);
            for (int i = 0; i < adx; i++) d1seg[minx + i][miny + i] = true;
        } else if (dx == -dy) {
            int maxy = max(ay, by);
            for (int i = 0; i < adx; i++) d2seg[minx + i][maxy - i] = true;
        }
    }
}

bool check_perimeter_dots(int cx[4], int cy[4], int miss) {
    for (int k = 0; k < 4; k++) {
        int a = k;
        int b = (k + 1) % 4;
        int ax = cx[a], ay = cy[a];
        int bx = cx[b], by = cy[b];
        int dx = bx - ax;
        int dy = by - ay;
        int adx = abs(dx);
        int ady = abs(dy);
        if (adx == 0 && ady == 0) continue;
        int sdx = 0, sdy = 0;
        int len = 0;
        if (adx == 0) {
            sdx = 0;
            sdy = (dy > 0 ? 1 : (dy < 0 ? -1 : 0));
            len = ady;
        } else if (ady == 0) {
            sdy = 0;
            sdx = (dx > 0 ? 1 : (dx < 0 ? -1 : 0));
            len = adx;
        } else {
            sdx = (dx > 0 ? 1 : (dx < 0 ? -1 : 0));
            sdy = (dy > 0 ? 1 : (dy < 0 ? -1 : 0));
            len = adx;
        }
        for (int i = 1; i < len; i++) {
            int px = ax + i * sdx;
            int py = ay + i * sdy;
            if (has_dot[px][py]) return false;
        }
    }
    return true;
}

int main() {
    int N, M;
    cin >> N >> M;
    memset(has_dot, 0, sizeof(has_dot));
    memset(hseg, 0, sizeof(hseg));
    memset(vseg, 0, sizeof(vseg));
    memset(d1seg, 0, sizeof(d1seg));
    memset(d2seg, 0, sizeof(d2seg));
    for (int i = 0; i < M; i++) {
        int x, y;
        cin >> x >> y;
        has_dot[x][y] = true;
    }
    int c = (N - 1) / 2;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            int dx = i - c;
            int dy = j - c;
            weight[i][j] = dx * dx + dy * dy + 1.0;
        }
    }
    vector<Move> operations;
    const int MSZ = 20;
    while (true) {
        map<pair<int, int>, Move> possible_p1;
        // axis-aligned
        for (int x1 = 0; x1 < N; x1++) {
            for (int x2 = x1 + 1; x2 < N && x2 - x1 <= MSZ; x2++) {
                for (int y1 = 0; y1 < N; y1++) {
                    for (int y2 = y1 + 1; y2 < N && y2 - y1 <= MSZ; y2++) {
                        int cpx[4] = {x1, x2, x2, x1};
                        int cpy[4] = {y1, y1, y2, y2};
                        int count = 0;
                        int miss = -1;
                        for (int k = 0; k < 4; k++) {
                            int px = cpx[k], py = cpy[k];
                            if (has_dot[px][py]) count++;
                            else miss = k;
                        }
                        if (count == 3) {
                            if (check_perimeter_dots(cpx, cpy, miss) &&
                                check_side(cpx[0], cpy[0], cpx[1], cpy[1]) &&
                                check_side(cpx[1], cpy[1], cpx[2], cpy[2]) &&
                                check_side(cpx[2], cpy[2], cpx[3], cpy[3]) &&
                                check_side(cpx[3], cpy[3], cpx[0], cpy[0])) {
                                Move m;
                                int start = miss;
                                for (int i = 0; i < 4; i++) {
                                    int idx = (start + i) % 4;
                                    m.x[i] = cpx[idx];
                                    m.y[i] = cpy[idx];
                                }
                                pair<int, int> key = {m.x[0], m.y[0]};
                                if (possible_p1.find(key) == possible_p1.end()) {
                                    possible_p1[key] = m;
                                }
                            }
                        }
                    }
                }
            }
        }
        // 45-degree
        for (int px = 0; px < N; px++) {
            for (int py = 0; py < N; py++) {
                for (int s = 1; s <= MSZ; s++) {
                    if (px + s >= N || py + s >= N) break;
                    int p1x = px + s;
                    int p1y = py + s;
                    for (int t = 1; t <= MSZ; t++) {
                        int p2x = px + t;
                        int p2y = py - t;
                        if (p2y < 0) break;
                        int p3x = px + s + t;
                        int p3y = py + s - t;
                        if (p3x >= N || p3y < 0 || p3y >= N) continue;
                        int cpx[4] = {px, p1x, p3x, p2x};
                        int cpy[4] = {py, p1y, p3y, p2y};
                        int count = 0;
                        int miss = -1;
                        for (int k = 0; k < 4; k++) {
                            if (has_dot[cpx[k]][cpy[k]]) count++;
                            else miss = k;
                        }
                        if (count == 3) {
                            if (check_perimeter_dots(cpx, cpy, miss) &&
                                check_side(cpx[0], cpy[0], cpx[1], cpy[1]) &&
                                check_side(cpx[1], cpy[1], cpx[2], cpy[2]) &&
                                check_side(cpx[2], cpy[2], cpx[3], cpy[3]) &&
                                check_side(cpx[3], cpy[3], cpx[0], cpy[0])) {
                                Move m;
                                int start = miss;
                                for (int i = 0; i < 4; i++) {
                                    int idx = (start + i) % 4;
                                    m.x[i] = cpx[idx];
                                    m.y[i] = cpy[idx];
                                }
                                pair<int, int> key = {m.x[0], m.y[0]};
                                if (possible_p1.find(key) == possible_p1.end()) {
                                    possible_p1[key] = m;
                                }
                            }
                        }
                    }
                }
            }
        }
        if (possible_p1.empty()) break;
        double best_w = -1.0;
        pair<int, int> best_key = {N + 1, N + 1};
        for (const auto& p : possible_p1) {
            int xx = p.first.first;
            int yy = p.first.second;
            double w = weight[xx][yy];
            pair<int, int> curk = {xx, yy};
            if (w > best_w || (w == best_w && curk < best_key)) {
                best_w = w;
                best_key = curk;
            }
        }
        Move chosen = possible_p1[best_key];
        operations.push_back(chosen);
        has_dot[chosen.x[0]][chosen.y[0]] = true;
        for (int k = 0; k < 4; k++) {
            int a = k;
            int b = (k + 1) % 4;
            draw_side(chosen.x[a], chosen.y[a], chosen.x[b], chosen.y[b]);
        }
    }
    cout << operations.size() << endl;
    for (const auto& op : operations) {
        for (int i = 0; i < 4; i++) {
            cout << op.x[i] << " " << op.y[i];
            if (i < 3) cout << " ";
            else cout << endl;
        }
    }
    return 0;
}