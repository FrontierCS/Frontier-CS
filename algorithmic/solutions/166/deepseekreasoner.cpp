#include <bits/stdc++.h>
using namespace std;

const int N = 20;
int h[N][N];

// Add moves from (cx,cy) to (tx,ty) to ops
void add_moves(int &cx, int &cy, int tx, int ty, vector<string> &ops) {
    while (cx < tx) { ops.push_back("D"); cx++; }
    while (cx > tx) { ops.push_back("U"); cx--; }
    while (cy < ty) { ops.push_back("R"); cy++; }
    while (cy > ty) { ops.push_back("L"); cy--; }
}

// Find nearest cell with sign: 1 for positive, -1 for negative
pair<int,int> find_nearest(int cx, int cy, int sign) {
    int best_dist = 1e9;
    pair<int,int> res = {-1, -1};
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (h[i][j] * sign > 0) {
                int dist = abs(i - cx) + abs(j - cy);
                if (dist < best_dist) {
                    best_dist = dist;
                    res = {i, j};
                }
            }
        }
    }
    return res;
}

// Find the best sink to unload given current position and load
pair<int,int> find_best_sink(int cx, int cy, int load) {
    int best_i = -1, best_j = -1;
    bool found_full = false;
    int best_full_dist = 1e9;
    int best_partial_amount = -1;
    int best_partial_dist = 1e9;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (h[i][j] < 0) {
                int dist = abs(i - cx) + abs(j - cy);
                int amount = -h[i][j];
                if (amount >= load) {
                    if (!found_full || dist < best_full_dist) {
                        found_full = true;
                        best_full_dist = dist;
                        best_i = i; best_j = j;
                    }
                } else {
                    if (!found_full) {
                        if (amount > best_partial_amount ||
                            (amount == best_partial_amount && dist < best_partial_dist)) {
                            best_partial_amount = amount;
                            best_partial_dist = dist;
                            best_i = i; best_j = j;
                        }
                    }
                }
            }
        }
    }
    return {best_i, best_j};
}

int main() {
    // Input
    int n;
    cin >> n; // n is always 20
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            cin >> h[i][j];

    vector<string> ops;
    int cx = 0, cy = 0;
    int load = 0;

    while (true) {
        // Check if all heights are zero
        bool done = true;
        for (int i = 0; i < N && done; ++i)
            for (int j = 0; j < N; ++j)
                if (h[i][j] != 0) { done = false; break; }
        if (done) break;

        if (load == 0) {
            // Find nearest positive cell
            auto [i, j] = find_nearest(cx, cy, 1);
            if (i == -1) break; // should not happen
            add_moves(cx, cy, i, j, ops);
            int d = h[i][j];
            ops.push_back("+" + to_string(d));
            h[i][j] = 0;
            load += d;
        } else {
            // Find best sink and unload
            auto [i, j] = find_best_sink(cx, cy, load);
            if (i == -1) break; // should not happen
            add_moves(cx, cy, i, j, ops);
            int d = min(load, -h[i][j]);
            ops.push_back("-" + to_string(d));
            h[i][j] += d;
            load -= d;
        }
    }

    // Output
    for (const string &s : ops)
        cout << s << endl;

    return 0;
}