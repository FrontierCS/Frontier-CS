#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>

using namespace std;

int main() {
    int N = 20;
    int cur[20][20];
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> cur[i][j];
        }
    }

    vector<string> ans;
    int load = 0;
    int x = 0, y = 0;

    // Snake order for the first pass
    vector<pair<int, int>> order;
    for (int i = 0; i < N; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; ++j) order.emplace_back(i, j);
        } else {
            for (int j = N - 1; j >= 0; --j) order.emplace_back(i, j);
        }
    }

    // First pass: traverse in snake order
    for (size_t idx = 0; idx < order.size(); ++idx) {
        int nx = order[idx].first, ny = order[idx].second;
        if (idx > 0) {
            // move to the next cell (adjacent in snake order)
            if (nx > x) { ans.push_back("D"); x++; }
            else if (nx < x) { ans.push_back("U"); x--; }
            else if (ny > y) { ans.push_back("R"); y++; }
            else if (ny < y) { ans.push_back("L"); y--; }
        }
        // process current cell
        int val = cur[x][y];
        if (val > 0) {
            ans.push_back("+" + to_string(val));
            load += val;
            cur[x][y] = 0;
        } else if (val < 0) {
            int need = -val;
            if (load >= need) {
                ans.push_back("-" + to_string(need));
                load -= need;
                cur[x][y] = 0;
            }
        }
    }

    // Collect remaining negative cells
    vector<pair<int, int>> negs;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (cur[i][j] < 0) negs.emplace_back(i, j);
        }
    }

    // Second pass: visit remaining negatives with greedy nearest neighbor
    while (!negs.empty()) {
        // find the nearest negative cell
        int best = 0;
        int best_dist = abs(negs[0].first - x) + abs(negs[0].second - y);
        for (size_t i = 1; i < negs.size(); ++i) {
            int d = abs(negs[i].first - x) + abs(negs[i].second - y);
            if (d < best_dist) {
                best_dist = d;
                best = i;
            }
        }
        int tx = negs[best].first, ty = negs[best].second;
        // move horizontally first, then vertically
        while (y != ty) {
            if (ty > y) { ans.push_back("R"); y++; }
            else { ans.push_back("L"); y--; }
        }
        while (x != tx) {
            if (tx > x) { ans.push_back("D"); x++; }
            else { ans.push_back("U"); x--; }
        }
        // unload the required amount
        int need = -cur[tx][ty];
        ans.push_back("-" + to_string(need));
        load -= need;
        cur[tx][ty] = 0;
        negs.erase(negs.begin() + best);
    }

    // Output the sequence
    for (const string& s : ans) {
        cout << s << "\n";
    }

    return 0;
}