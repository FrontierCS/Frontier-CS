#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
};

int N;
vector<Point> mack; // mackerels
vector<Point> sard; // sardines

// compute a - b for rectangle [L,R] x [B,T]
int score_rect(int L, int R, int B, int T) {
    int a = 0, b = 0;
    for (auto& p : mack)
        if (p.x >= L && p.x <= R && p.y >= B && p.y <= T)
            a++;
    for (auto& p : sard)
        if (p.x >= L && p.x <= R && p.y >= B && p.y <= T)
            b++;
    return a - b;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> N;
    mack.resize(N);
    sard.resize(N);
    for (int i = 0; i < N; i++)
        cin >> mack[i].x >> mack[i].y;
    for (int i = 0; i < N; i++)
        cin >> sard[i].x >> sard[i].y;

    const int G = 200;
    const int cell_w = 100000 / G;
    const int cell_h = 100000 / G;
    vector<vector<int>> net(G, vector<int>(G, 0));

    for (auto& p : mack) {
        int i = min(G-1, p.x / cell_w);
        int j = min(G-1, p.y / cell_h);
        net[i][j]++;
    }
    for (auto& p : sard) {
        int i = min(G-1, p.x / cell_w);
        int j = min(G-1, p.y / cell_h);
        net[i][j]--;
    }

    // 2D prefix sum
    vector<vector<int>> ps(G+1, vector<int>(G+1, 0));
    for (int i = 0; i < G; i++)
        for (int j = 0; j < G; j++)
            ps[i+1][j+1] = net[i][j] + ps[i][j+1] + ps[i+1][j] - ps[i][j];

    int best_sum = -1e9;
    int best_t = 0, best_b = 0, best_l = 0, best_r = 0;

    for (int t = 0; t < G; t++) {
        for (int b = t; b < G; b++) {
            vector<int> col_sum(G);
            for (int k = 0; k < G; k++)
                col_sum[k] = ps[b+1][k+1] - ps[t][k+1] - ps[b+1][k] + ps[t][k];

            // Kadane's algorithm
            int cur = 0, max_sum = -1e9;
            int start = 0, best_start = 0, best_end = -1;
            for (int i = 0; i < G; i++) {
                if (cur + col_sum[i] < col_sum[i]) {
                    cur = col_sum[i];
                    start = i;
                } else {
                    cur += col_sum[i];
                }
                if (cur > max_sum) {
                    max_sum = cur;
                    best_start = start;
                    best_end = i;
                }
            }
            if (max_sum > best_sum) {
                best_sum = max_sum;
                best_t = t;
                best_b = b;
                best_l = best_start;
                best_r = best_end;
            }
        }
    }

    int L = best_l * cell_w;
    int R = (best_r+1) * cell_w - 1;
    int B = best_t * cell_h;
    int T = (best_b+1) * cell_h - 1;
    L = max(0, L); R = min(100000, R);
    B = max(0, B); T = min(100000, T);

    // Refinement
    for (int round = 0; round < 2; round++) {
        // left edge
        {
            set<int> cand;
            cand.insert(L);
            int window = 5000;
            for (auto& p : mack)
                if (p.y >= B && p.y <= T && p.x >= L-window && p.x <= L+window)
                    cand.insert(p.x), cand.insert(p.x-1), cand.insert(p.x+1);
            for (auto& p : sard)
                if (p.y >= B && p.y <= T && p.x >= L-window && p.x <= L+window)
                    cand.insert(p.x), cand.insert(p.x-1), cand.insert(p.x+1);
            int best_score = score_rect(L, R, B, T);
            for (int x : cand) {
                if (x < 0 || x > 100000 || x >= R) continue;
                int s = score_rect(x, R, B, T);
                if (s > best_score) {
                    best_score = s;
                    L = x;
                }
            }
        }
        // right edge
        {
            set<int> cand;
            cand.insert(R);
            int window = 5000;
            for (auto& p : mack)
                if (p.y >= B && p.y <= T && p.x >= R-window && p.x <= R+window)
                    cand.insert(p.x), cand.insert(p.x-1), cand.insert(p.x+1);
            for (auto& p : sard)
                if (p.y >= B && p.y <= T && p.x >= R-window && p.x <= R+window)
                    cand.insert(p.x), cand.insert(p.x-1), cand.insert(p.x+1);
            int best_score = score_rect(L, R, B, T);
            for (int x : cand) {
                if (x < 0 || x > 100000 || x <= L) continue;
                int s = score_rect(L, x, B, T);
                if (s > best_score) {
                    best_score = s;
                    R = x;
                }
            }
        }
        // bottom edge
        {
            set<int> cand;
            cand.insert(B);
            int window = 5000;
            for (auto& p : mack)
                if (p.x >= L && p.x <= R && p.y >= B-window && p.y <= B+window)
                    cand.insert(p.y), cand.insert(p.y-1), cand.insert(p.y+1);
            for (auto& p : sard)
                if (p.x >= L && p.x <= R && p.y >= B-window && p.y <= B+window)
                    cand.insert(p.y), cand.insert(p.y-1), cand.insert(p.y+1);
            int best_score = score_rect(L, R, B, T);
            for (int y : cand) {
                if (y < 0 || y > 100000 || y >= T) continue;
                int s = score_rect(L, R, y, T);
                if (s > best_score) {
                    best_score = s;
                    B = y;
                }
            }
        }
        // top edge
        {
            set<int> cand;
            cand.insert(T);
            int window = 5000;
            for (auto& p : mack)
                if (p.x >= L && p.x <= R && p.y >= T-window && p.y <= T+window)
                    cand.insert(p.y), cand.insert(p.y-1), cand.insert(p.y+1);
            for (auto& p : sard)
                if (p.x >= L && p.x <= R && p.y >= T-window && p.y <= T+window)
                    cand.insert(p.y), cand.insert(p.y-1), cand.insert(p.y+1);
            int best_score = score_rect(L, R, B, T);
            for (int y : cand) {
                if (y < 0 || y > 100000 || y <= B) continue;
                int s = score_rect(L, R, B, y);
                if (s > best_score) {
                    best_score = s;
                    T = y;
                }
            }
        }
    }

    // ensure non-degenerate rectangle
    if (L >= R) R = min(100000, L+1);
    if (B >= T) T = min(100000, B+1);

    // output polygon (clockwise order)
    cout << 4 << "\n";
    cout << L << " " << B << "\n";
    cout << R << " " << B << "\n";
    cout << R << " " << T << "\n";
    cout << L << " " << T << "\n";

    return 0;
}